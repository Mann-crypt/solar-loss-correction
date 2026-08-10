import numpy as np
import pandas as pd


# ==========================================================
# LOSS CORRECTED WEIGHTS
# ==========================================================

def calculate_loss_corrected_weights(
    area_df,
    efficiency_loss,
    weight_factors,
    has_cluster=True,
):
    """
    Calculate effective plant/cluster weights.

    Cluster:
        One effective weight per GHI cluster.

    Non-cluster:
        One total plant effective weight.
    """

    if area_df is None or area_df.empty:
        raise ValueError("Area data is missing or empty.")

    df = area_df.copy()

    # ------------------------------------------------------
    # Efficiency loss
    # ------------------------------------------------------

    efficiency_loss = float(efficiency_loss)

    df["Efficiency Losses(%)"] = efficiency_loss

    # ------------------------------------------------------
    # Standard efficiency
    # ------------------------------------------------------

    efficiency_column = None

    possible_efficiency_columns = [
        "Standard PV Efficiency (%)",
        "Standard PV Efficiency",
        "PV Efficiency (%)",
        "Efficiency (%)",
        "Efficiency",
    ]

    normalized_columns = {
        str(col)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("\n", " "): col
        for col in df.columns
    }

    for name in possible_efficiency_columns:

        key = (
            name
            .strip()
            .lower()
            .replace("_", " ")
        )

        if key in normalized_columns:
            efficiency_column = normalized_columns[key]
            break

    if efficiency_column is None:
        raise ValueError(
            "Could not find Standard PV Efficiency column. "
            f"Available columns: {list(df.columns)}"
        )

    # ------------------------------------------------------
    # Net efficiency
    # ------------------------------------------------------

    df["Net Efficiency (%)"] = (
        pd.to_numeric(
            df[efficiency_column],
            errors="coerce",
        ).fillna(0)
        - efficiency_loss
    )

    df["Net Efficiency (%)"] = np.maximum(
        df["Net Efficiency (%)"],
        0,
    )

    # ------------------------------------------------------
    # Total area
    # ------------------------------------------------------

    area_column = None

    possible_area_columns = [
        "Total area(m2)",
        "Total Area(m2)",
        "Total Area (m2)",
        "Total area",
        "Area(m2)",
        "Area (m2)",
        "Area",
    ]

    for name in possible_area_columns:

        key = (
            name
            .strip()
            .lower()
            .replace("_", " ")
        )

        if key in normalized_columns:
            area_column = normalized_columns[key]
            break

    if area_column is None:
        raise ValueError(
            "Could not find Total Area column. "
            f"Available columns: {list(df.columns)}"
        )

    # ------------------------------------------------------
    # Effective area
    # ------------------------------------------------------

    df["Effective Area"] = (
        pd.to_numeric(
            df[area_column],
            errors="coerce",
        ).fillna(0)
        * df["Net Efficiency (%)"]
        / 100.0
    )

    total_effective_area = float(
        df["Effective Area"].sum()
    )

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    if not has_cluster:

        return np.asarray(
            [total_effective_area],
            dtype=float,
        )

    # ======================================================
    # CLUSTER
    # ======================================================

    weight_factors = np.asarray(
        weight_factors,
        dtype=float,
    )

    weight_factors = np.nan_to_num(
        weight_factors,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    if len(weight_factors) == 0:

        raise ValueError(
            "No cluster weight factors supplied."
        )

    total_weight = weight_factors.sum()

    if total_weight <= 0:

        weight_factors = (
            np.ones(
                len(weight_factors),
                dtype=float,
            )
            / len(weight_factors)
        )

    else:

        weight_factors = (
            weight_factors
            / total_weight
        )

    weights = (
        total_effective_area
        * weight_factors
    )

    return np.asarray(
        weights,
        dtype=float,
    )


# ==========================================================
# TRACKING FORECAST
# ==========================================================

def calculate_tracking_forecast(
    ghi_arrays,
    weights,
    blocks,
    dhi_percent,
    ghi_start,
    ghi_end,
    ghi_max,
    east_limit,
    west_limit,
):
    """
    Calculate tracking-based generation forecast.

    Parameters
    ----------
    ghi_arrays:
        List of GHI arrays. One for non-cluster,
        multiple for cluster plants.

    weights:
        Effective area/weight for each GHI array.

    blocks:
        15-minute block numbers, normally 0-95.

    dhi_percent:
        DHI correction percentage.

    ghi_start:
        Starting GHI block.

    ghi_end:
        Ending GHI block.

    ghi_max:
        Block where GHI reaches maximum.

    east_limit:
        East tracking limit.

    west_limit:
        West tracking limit.
    """

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    if len(blocks) == 0:
        raise ValueError("Blocks are empty.")

    # ------------------------------------------------------
    # Clean GHI arrays
    # ------------------------------------------------------

    cleaned_arrays = []

    for i, ghi in enumerate(ghi_arrays):

        ghi = np.asarray(
            ghi,
            dtype=float,
        )

        if len(ghi) != len(blocks):

            raise ValueError(
                f"GHI array {i + 1} length "
                f"{len(ghi)} does not match "
                f"blocks length {len(blocks)}."
            )

        ghi = np.nan_to_num(
            ghi,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        ghi = np.maximum(
            ghi,
            0,
        )

        cleaned_arrays.append(
            ghi
        )

    # ------------------------------------------------------
    # Validate weights
    # ------------------------------------------------------

    weights = np.asarray(
        weights,
        dtype=float,
    )

    weights = np.nan_to_num(
        weights,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    if len(weights) != len(cleaned_arrays):

        raise ValueError(
            "Number of weights must match "
            "number of GHI arrays."
        )

    total_weight = weights.sum()

    if total_weight <= 0:

        weights = (
            np.ones(
                len(cleaned_arrays),
                dtype=float,
            )
            / len(cleaned_arrays)
        )

    else:

        weights = (
            weights
            / total_weight
        )

    # ======================================================
    # WEIGHTED GHI
    # ======================================================

    ghi_matrix = np.vstack(
        cleaned_arrays
    )

    weighted_ghi = np.sum(
        ghi_matrix
        * weights[:, None],
        axis=0,
    )

    # ======================================================
    # GHI CURVE CORRECTION
    # ======================================================

    ghi_start = int(
        round(ghi_start)
    )

    ghi_end = int(
        round(ghi_end)
    )

    ghi_max = int(
        round(ghi_max)
    )

    dhi_percent = float(
        dhi_percent
    )

    if not (
        0 <= ghi_start
        < ghi_max
        < ghi_end
        <= len(blocks)
    ):

        raise ValueError(
            "Invalid GHI block configuration. "
            "Required: "
            "0 <= Starting Block < Max Block "
            "< Ending Block <= number of blocks."
        )

    corrected_ghi = weighted_ghi.copy()

    # ------------------------------------------------------
    # DHI correction
    # ------------------------------------------------------

    dhi_factor = (
        1.0
        + dhi_percent / 100.0
    )

    # ------------------------------------------------------
    # Morning side
    # ------------------------------------------------------

    morning_mask = (
        blocks >= ghi_start
    ) & (
        blocks <= ghi_max
    )

    if np.any(morning_mask):

        morning_blocks = blocks[
            morning_mask
        ]

        denominator = (
            ghi_max - ghi_start
        )

        if denominator > 0:

            progress = (
                morning_blocks
                - ghi_start
            ) / denominator

            progress = np.clip(
                progress,
                0,
                1,
            )

            # Smooth increasing correction
            correction = (
                progress
                * dhi_factor
                + (1 - progress)
            )

            corrected_ghi[
                morning_mask
            ] *= correction

    # ------------------------------------------------------
    # Evening side
    # ------------------------------------------------------

    evening_mask = (
        blocks >= ghi_max
    ) & (
        blocks <= ghi_end
    )

    if np.any(evening_mask):

        evening_blocks = blocks[
            evening_mask
        ]

        denominator = (
            ghi_end - ghi_max
        )

        if denominator > 0:

            progress = (
                evening_blocks
                - ghi_max
            ) / denominator

            progress = np.clip(
                progress,
                0,
                1,
            )

            correction = (
                (1 - progress)
                * dhi_factor
                + progress
            )

            corrected_ghi[
                evening_mask
            ] *= correction

    # ======================================================
    # TRACKING FACTOR
    # ======================================================

    east_limit = float(
        east_limit
    )

    west_limit = float(
        west_limit
    )

    # Convert block position into
    # normalized solar position.
    #
    # This produces a smooth tracking
    # factor between the configured
    # east/west limits.

    tracking_factor = np.ones(
        len(blocks),
        dtype=float,
    )

    daylight_mask = (
        corrected_ghi > 0
    )

    if np.any(daylight_mask):

        daylight_blocks = blocks[
            daylight_mask
        ]

        center = (
            ghi_max
        )

        left_distance = max(
            center - ghi_start,
            1,
        )

        right_distance = max(
            ghi_end - center,
            1,
        )

        for idx, block in zip(
            np.where(daylight_mask)[0],
            daylight_blocks,
        ):

            if block <= center:

                progress = (
                    center - block
                ) / left_distance

                progress = np.clip(
                    progress,
                    0,
                    1,
                )

                tracking_angle = (
                    east_limit
                    * progress
                )

            else:

                progress = (
                    block - center
                ) / right_distance

                progress = np.clip(
                    progress,
                    0,
                    1,
                )

                tracking_angle = (
                    -west_limit
                    * progress
                )

            # Cosine projection
            tracking_factor[idx] = (
                max(
                    np.cos(
                        np.radians(
                            tracking_angle
                        )
                    ),
                    0,
                )
            )

    # ======================================================
    # FORECAST
    # ======================================================

    forecast = (
        corrected_ghi
        * tracking_factor
    )

    forecast = np.nan_to_num(
        forecast,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    forecast = np.maximum(
        forecast,
        0,
    )

    return forecast
