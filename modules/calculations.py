# modules/calculations.py

import numpy as np
import pandas as pd


# ==========================================================
# BASIC HELPERS
# ==========================================================

def clip_zero(values):
    """
    Replace NaN/inf and negative values with zero.
    """
    values = np.asarray(values, dtype=float)

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    return np.maximum(values, 0.0)


def sin_deg(angle):
    """
    Sine where angle is supplied in degrees.
    """
    return np.sin(
        np.radians(angle)
    )


def cos_deg(angle):
    """
    Cosine where angle is supplied in degrees.
    """
    return np.cos(
        np.radians(angle)
    )


# ==========================================================
# SOLAR GEOMETRY
# ==========================================================

def declination(day_of_year):
    """
    Solar declination angle in degrees.

    Cooper equation.
    """

    day_of_year = np.asarray(
        day_of_year,
        dtype=float,
    )

    return (
        23.45
        * np.sin(
            np.radians(
                360.0
                * (284.0 + day_of_year)
                / 365.0
            )
        )
    )


def elevation_from_zenith(zenith):
    """
    Convert solar zenith angle to elevation angle.
    """

    zenith = np.asarray(
        zenith,
        dtype=float,
    )

    return 90.0 - zenith


# ==========================================================
# TRACKING ANGLE
# ==========================================================

def calculate_tracking_angles(
    blocks,
    ghi_start,
    ghi_end,
    ghi_max,
    east_limit,
    west_limit,
):
    """
    Generate the panel tracking angle for 96 blocks.

    Logic:

        Before GHI Max Block:
            panel moves from East limit toward 0.

        At GHI Max Block:
            panel angle = 0.

        After GHI Max Block:
            panel moves from 0 toward West limit.

    Parameters
    ----------
    blocks : array-like
        Block numbers.

    ghi_start : int
        Block where tracking starts.

    ghi_end : int
        Block where tracking ends.

    ghi_max : int
        Peak / maximum GHI block.

    east_limit : float
        Maximum east tracking angle.

    west_limit : float
        Maximum west tracking angle.

    Returns
    -------
    numpy.ndarray
        Tracking angle for each block.
    """

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    if not (
        ghi_start
        < ghi_max
        < ghi_end
    ):
        raise ValueError(
            "GHI Starting Block must be less "
            "than GHI Max Block and GHI Max Block "
            "must be less than GHI Ending Block."
        )

    angles = np.zeros(
        len(blocks),
        dtype=float,
    )

    # ------------------------------------------------------
    # Morning / East side
    # ------------------------------------------------------

    morning = (
        (blocks >= ghi_start)
        & (blocks <= ghi_max)
    )

    if np.any(morning):

        denominator = (
            ghi_max
            - ghi_start
        )

        if denominator > 0:

            fraction = (
                blocks[morning]
                - ghi_start
            ) / denominator

            fraction = np.clip(
                fraction,
                0.0,
                1.0,
            )

            angles[morning] = (
                east_limit
                * (1.0 - fraction)
            )

    # ------------------------------------------------------
    # Evening / West side
    # ------------------------------------------------------

    evening = (
        (blocks >= ghi_max)
        & (blocks <= ghi_end)
    )

    if np.any(evening):

        denominator = (
            ghi_end
            - ghi_max
        )

        if denominator > 0:

            fraction = (
                blocks[evening]
                - ghi_max
            ) / denominator

            fraction = np.clip(
                fraction,
                0.0,
                1.0,
            )

            angles[evening] = (
                -west_limit
                * fraction
            )

    return angles


# ==========================================================
# DHI
# ==========================================================

def calculate_dhi(
    ghi,
    dhi_percent,
):
    """
    Calculate DHI from GHI.

        DHI = GHI × DHI%

    dhi_percent is supplied as a percentage.

    Example:
        GHI = 800
        DHI = 20%

        DHI = 160
    """

    ghi = clip_zero(
        ghi
    )

    dhi_percent = float(
        dhi_percent
    )

    dhi_percent = np.clip(
        dhi_percent,
        0.0,
        100.0,
    )

    dhi = (
        ghi
        * dhi_percent
        / 100.0
    )

    return clip_zero(
        dhi
    )


# ==========================================================
# DNI
# ==========================================================

def calculate_dni(
    ghi,
    dhi,
    panel_angle=None,
    zenith_angle=None,
):
    """
    Calculate DNI from GHI and DHI.

    GHI = DNI × cos(zenith) + DHI

    Therefore:

        DNI = (GHI - DHI) / cos(zenith)

    If zenith_angle is not supplied, panel_angle
    is used only as a compatibility fallback.

    Negative values are clipped to zero.
    """

    ghi = clip_zero(
        ghi
    )

    dhi = clip_zero(
        dhi
    )

    if zenith_angle is None:

        if panel_angle is None:

            # Horizontal fallback.
            cos_zenith = np.ones(
                len(ghi),
                dtype=float,
            )

        else:

            panel_angle = np.asarray(
                panel_angle,
                dtype=float,
            )

            cos_zenith = cos_deg(
                panel_angle
            )

    else:

        zenith_angle = np.asarray(
            zenith_angle,
            dtype=float,
        )

        cos_zenith = cos_deg(
            zenith_angle
        )

    cos_zenith = np.clip(
        cos_zenith,
        0.05,
        1.0,
    )

    dni = (
        ghi - dhi
    ) / cos_zenith

    return clip_zero(
        dni
    )


# ==========================================================
# POA IRRADIANCE
# ==========================================================

def calculate_poa(
    dni,
    dhi,
    zenith_angle,
    panel_angle,
):
    """
    Calculate plane-of-array irradiance.

    Direct component:

        DNI × cos(theta - alpha)

    Diffuse component:

        DHI × (1 + cos(alpha)) / 2

    where:

        theta = solar zenith angle
        alpha = panel angle
    """

    dni = clip_zero(
        dni
    )

    dhi = clip_zero(
        dhi
    )

    zenith_angle = np.asarray(
        zenith_angle,
        dtype=float,
    )

    panel_angle = np.asarray(
        panel_angle,
        dtype=float,
    )

    # ------------------------------------------------------
    # Direct irradiance on panel
    # ------------------------------------------------------

    incidence_cos = cos_deg(
        zenith_angle
        - panel_angle
    )

    incidence_cos = np.maximum(
        incidence_cos,
        0.0,
    )

    direct_poa = (
        dni
        * incidence_cos
    )

    # ------------------------------------------------------
    # Diffuse sky component
    # ------------------------------------------------------

    diffuse_poa = (
        dhi
        * (
            1.0
            + cos_deg(panel_angle)
        )
        / 2.0
    )

    poa = (
        direct_poa
        + diffuse_poa
    )

    return clip_zero(
        poa
    )


# ==========================================================
# EFFECTIVE WEIGHTS
# ==========================================================

def calculate_loss_corrected_weights(
    area_df,
    efficiency_loss,
    weight_factors,
    has_cluster=True,
):
    """
    Calculate effective plant weights after applying
    efficiency loss.

    Cluster:
        One weight per GHI cluster.

    Non-cluster:
        One total plant weight.

    Parameters
    ----------
    area_df : pandas.DataFrame
        Area and efficiency data.

    efficiency_loss : float
        Efficiency loss in percentage points.

    weight_factors : array-like
        Cluster weighting factors.

    has_cluster : bool
        Whether workbook contains cluster plants.

    Returns
    -------
    numpy.ndarray
    """

    if area_df is None:
        raise ValueError(
            "Area data is missing."
        )

    df = area_df.copy()

    # ------------------------------------------------------
    # Required columns
    # ------------------------------------------------------

    efficiency_col = (
        "Standard PV Efficiency (%)"
    )

    area_col = (
        "Total area(m2)"
    )

    if efficiency_col not in df.columns:

        raise ValueError(
            f"Missing column: {efficiency_col}"
        )

    if area_col not in df.columns:

        raise ValueError(
            f"Missing column: {area_col}"
        )

    # ------------------------------------------------------
    # Efficiency
    # ------------------------------------------------------

    efficiency_loss = float(
        efficiency_loss
    )

    df["Efficiency Losses(%)"] = (
        efficiency_loss
    )

    df["Standard PV Efficiency (%)"] = (
        pd.to_numeric(
            df[
                "Standard PV Efficiency (%)"
            ],
            errors="coerce",
        ).fillna(0.0)
    )

    df["Net Efficiency (%)"] = (
        df[
            "Standard PV Efficiency (%)"
        ]
        - efficiency_loss
    )

    df["Net Efficiency (%)"] = np.maximum(
        df["Net Efficiency (%)"],
        0.0,
    )

    # ------------------------------------------------------
    # Area
    # ------------------------------------------------------

    df["Total area(m2)"] = (
        pd.to_numeric(
            df["Total area(m2)"],
            errors="coerce",
        ).fillna(0.0)
    )

    # ------------------------------------------------------
    # Effective area
    # ------------------------------------------------------

    df["Effective Area"] = (
        df["Total area(m2)"]
        * df["Net Efficiency (%)"]
        / 100.0
    )

    total_effective_area = (
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

    weight_factors = np.maximum(
        weight_factors,
        0.0,
    )

    total_weight = (
        weight_factors.sum()
    )

    if total_weight <= 0:

        weight_factors = (
            np.ones(
                len(weight_factors)
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
# SINGLE GHI → POWER
# ==========================================================

def calculate_single_tracking_forecast(
    ghi,
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
    Convert one GHI array into tracking generation.
    """

    ghi = clip_zero(
        ghi
    )

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    # ------------------------------------------------------
    # Tracking angle
    # ------------------------------------------------------

    panel_angle = calculate_tracking_angles(
        blocks=blocks,
        ghi_start=ghi_start,
        ghi_end=ghi_end,
        ghi_max=ghi_max,
        east_limit=east_limit,
        west_limit=west_limit,
    )

    # ------------------------------------------------------
    # Solar geometry
    # ------------------------------------------------------
    #
    # The forecasting screen works with block numbers.
    # We use a 15-minute solar-day approximation where
    # block 0 corresponds to midnight.
    #
    # This keeps the calculation independent from the
    # workbook's date/time formatting.
    # ------------------------------------------------------

    time_hours = (
        blocks / 4.0
    )

    # Solar hour angle.
    hour_angle = (
        time_hours - 12.0
    ) * 15.0

    # Default declination near equinox.
    # This provides a stable geometry when the workbook
    # does not explicitly provide zenith data.
    dec = 0.0

    latitude = 28.6

    cos_zenith = (
        sin_deg(latitude)
        * sin_deg(dec)
        +
        cos_deg(latitude)
        * cos_deg(dec)
        * cos_deg(hour_angle)
    )

    cos_zenith = np.clip(
        cos_zenith,
        -1.0,
        1.0,
    )

    zenith_angle = np.degrees(
        np.arccos(
            cos_zenith
        )
    )

    # ------------------------------------------------------
    # DHI
    # ------------------------------------------------------

    dhi = calculate_dhi(
        ghi,
        dhi_percent,
    )

    # ------------------------------------------------------
    # DNI
    # ------------------------------------------------------

    dni = calculate_dni(
        ghi=ghi,
        dhi=dhi,
        zenith_angle=zenith_angle,
    )

    # ------------------------------------------------------
    # POA
    # ------------------------------------------------------

    poa = calculate_poa(
        dni=dni,
        dhi=dhi,
        zenith_angle=zenith_angle,
        panel_angle=panel_angle,
    )

    # ------------------------------------------------------
    # Convert irradiance to generation
    # ------------------------------------------------------

    effective_area = float(
        np.asarray(
            weights,
            dtype=float,
        ).sum()
    )

    power = (
        poa
        * effective_area
        / 1000.0
    )

    return clip_zero(
        power
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
    Calculate total tracking generation.

    For a non-cluster plant:

        GHI arrays = [GHI]

        weights = [total effective area]

    For a cluster plant:

        GHI arrays = [
            CL1-GHI,
            CL2-GHI,
            ...
        ]

        weights = [
            effective CL1 area,
            effective CL2 area,
            ...
        ]

    Each cluster is calculated independently and then
    summed into total generation.
    """

    if not ghi_arrays:

        raise ValueError(
            "No GHI arrays supplied."
        )

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    weights = np.asarray(
        weights,
        dtype=float,
    )

    if len(weights) != len(
        ghi_arrays
    ):

        raise ValueError(
            "Number of weights must match "
            "number of GHI arrays."
        )

    forecasts = []

    for ghi, weight in zip(
        ghi_arrays,
        weights,
    ):

        ghi = np.asarray(
            ghi,
            dtype=float,
        )

        if len(ghi) != len(blocks):

            raise ValueError(
                "GHI array length does not "
                "match Blocks."
            )

        # Each array receives its own
        # effective-area contribution.
        forecast = (
            calculate_single_tracking_forecast(
                ghi=ghi,
                weights=[weight],
                blocks=blocks,
                dhi_percent=dhi_percent,
                ghi_start=ghi_start,
                ghi_end=ghi_end,
                ghi_max=ghi_max,
                east_limit=east_limit,
                west_limit=west_limit,
            )
        )

        forecasts.append(
            forecast
        )

    # ------------------------------------------------------
    # Total plant generation
    # ------------------------------------------------------

    total_forecast = np.sum(
        np.vstack(
            forecasts
        ),
        axis=0,
    )

    return clip_zero(
        total_forecast
    )


# ==========================================================
# RT / PROJECTION HELPERS
# ==========================================================

def calculate_rt_projection(
    actual,
    forecast,
):
    """
    Calculate actual-to-forecast projection ratio.

    Useful for applying an RT correction to a forecast.
    """

    actual = np.asarray(
        actual,
        dtype=float,
    )

    forecast = np.asarray(
        forecast,
        dtype=float,
    )

    denominator = np.sum(
        np.abs(forecast)
    )

    if denominator <= 0:

        return 1.0

    return (
        np.sum(actual)
        / denominator
    )


def apply_rt_projection(
    forecast,
    projection,
    weight=1.0,
):
    """
    Apply RT projection to forecast.

        corrected =
            forecast ×
            [1 + weight × (projection - 1)]
    """

    forecast = np.asarray(
        forecast,
        dtype=float,
    )

    projection = float(
        projection
    )

    weight = float(
        weight
    )

    weight = np.clip(
        weight,
        0.0,
        1.0,
    )

    factor = (
        1.0
        + weight
        * (projection - 1.0)
    )

    return clip_zero(
        forecast
        * factor
    )


# ==========================================================
# SYMMETRY
# ==========================================================

def apply_symmetry(
    values,
):
    """
    Mirror the first half of a daily curve onto the
    second half.

    Mainly useful for shape correction.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    n = len(values)

    if n < 2:

        return values.copy()

    result = values.copy()

    half = n // 2

    left = values[
        :half
    ]

    right_length = (
        n - half
    )

    mirrored = left[
        ::-1
    ]

    if len(mirrored) < right_length:

        mirrored = np.resize(
            mirrored,
            right_length,
        )

    result[
        half:
    ] = mirrored[
        :right_length
    ]

    return clip_zero(
        result
    )


# ==========================================================
# BEST SHIFT
# ==========================================================

def best_shift(
    actual,
    forecast,
    max_shift=10,
):
    """
    Find the time shift producing the smallest
    absolute-error score.

    Returns:
        best_shift, shifted_forecast
    """

    actual = np.asarray(
        actual,
        dtype=float,
    )

    forecast = np.asarray(
        forecast,
        dtype=float,
    )

    if len(actual) != len(
        forecast
    ):

        raise ValueError(
            "Actual and forecast must "
            "have the same length."
        )

    best_score = np.inf
    best_value = 0
    best_forecast = forecast.copy()

    for shift in range(
        -max_shift,
        max_shift + 1,
    ):

        shifted = np.roll(
            forecast,
            shift,
        )

        score = np.mean(
            np.abs(
                actual
                - shifted
            )
        )

        if score < best_score:

            best_score = score
            best_value = shift
            best_forecast = shifted.copy()

    return (
        best_value,
        best_forecast,
    )
