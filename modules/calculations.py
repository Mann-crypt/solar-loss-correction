# calculations.py

import numpy as np
import pandas as pd

# ------Layer 1--------
def calculate_declination_angle(date):
    """
    Solar declination angle (degrees).
    """
    day = pd.to_datetime(date).dayofyear

    return 23.45 * np.sin(
        np.radians(
            360 * (284 + day) / 365
        )
    )


def calculate_elevation_angle(latitude, declination):
    """
    Maximum solar elevation angle.
    """
    return 90 - latitude + declination


def sin_deg(angle):
    """
    Sine of angle in degrees.
    """
    return np.sin(np.radians(angle))


def clip_zero(values):
    """
    Replace negative values with zero.
    """
    return np.maximum(values, 0)
# ------Layer 2--------
def calculate_poa(
    ghi,
    elevation_angle,
    tilt_angle
):
    """
    Plane of Array Irradiance.
    """

    sin_a = sin_deg(elevation_angle)

    sin_ab = sin_deg(elevation_angle + tilt_angle)

    return (ghi * sin_ab) / sin_a

# -------RT Correction--------
def calculate_projection(
    blocks,
    peak,
    n1,
    n2,
    b
):
    """
    RT Projection curve.
    """

    projection = peak * (
        ((n1 - blocks) * (n2 - blocks))
        /
        ((n1 - b) * (n2 - b))
    )

    return clip_zero(projection)

def calculate_rt_forecast(
    projection,
    trend,
    blocks,
    b,
    weight
):
    """
    Final RT Forecast.
    """

    return np.where(
        blocks > b,
        weight * projection + (1 - weight) * trend,
        trend
    )

# ---------AM Curve---------
def calculate_symmetry(
    profile,
    shift
):
    """
    Symmetry profile.
    """

    shifted = np.roll(profile, -shift)

    return (profile + shifted[::-1]) / 2

def find_best_shift(profile):
    """
    Find best symmetry shift.
    """

    least_error = np.inf
    best_shift = 0

    for i in range(96):

        shifted = np.roll(profile, -i)

        sym = (profile + shifted[::-1]) / 2

        error = np.sqrt(
            np.mean((profile - sym) ** 2)
        )

        if error < least_error:
            least_error = error
            best_shift = i

    return best_shift

# ==========================================================
# TRACKING LOSS CORRECTION
# ==========================================================

def calculate_tracking_angles(
    blocks,
    ghi_start,
    ghi_end,
    ghi_max,
    east_limit,
    west_limit
):
    """
    Calculate solar zenith/panel tracking angle
    using the GHI block configuration.
    """

    blocks = np.asarray(blocks, dtype=float)

    # Validate block configuration
    if (
        ghi_start >= ghi_max
        or ghi_max >= ghi_end
    ):
        raise ValueError(
            "Invalid block configuration: "
            "Start < Max < End is required."
        )

    denominator_1 = (
        ghi_start - 1 - ghi_max
    )

    denominator_2 = (
        ghi_end + 1 - ghi_max
    )

    if denominator_1 == 0 or denominator_2 == 0:
        raise ValueError(
            "Invalid block configuration."
        )

    m1 = 90 / denominator_1
    m2 = 90 / denominator_2

    zenith = np.where(
        blocks <= ghi_max,

        np.minimum(
            89,
            m1 * (blocks - ghi_max)
        ),

        np.minimum(
            89,
            m2 * (blocks - ghi_max)
        )
    )

    panel = np.where(

        blocks < ghi_max,

        np.minimum(
            zenith,
            abs(east_limit)
        ),

        np.where(
            (blocks > ghi_max)
            & (zenith > west_limit),

            west_limit,

            zenith
        )
    )

    return zenith, panel


def calculate_dhi(
    ghi,
    dhi_percent
):
    """
    Calculate DHI from GHI.
    """

    return (
        np.asarray(ghi, dtype=float)
        * dhi_percent
        / 100.0
    )


def calculate_dni(
    ghi,
    dhi,
    panel_angle
):
    """
    Calculate DNI from GHI, DHI and panel angle.
    """

    cos_alpha = np.cos(
        np.radians(panel_angle)
    )

    # Prevent division by zero
    cos_alpha = np.clip(
        cos_alpha,
        1e-6,
        None
    )

    dni = (
        np.asarray(ghi, dtype=float)
        - np.asarray(dhi, dtype=float)
    ) / cos_alpha

    return dni


def calculate_tracking_forecast(
    ghi_arrays,
    weights,
    blocks,
    dhi_percent,
    ghi_start,
    ghi_end,
    ghi_max,
    east_limit,
    west_limit
):
    """
    Calculate final tracking power forecast.

    Supports:

    Cluster:
        ghi_arrays = [
            CL1-GHI,
            CL2-GHI,
            CL3-GHI,
            CL4-GHI,
            CL5-GHI
        ]

        weights = [
            weight1,
            weight2,
            weight3,
            weight4,
            weight5
        ]

    Non-cluster:
        ghi_arrays = [
            normal_GHI
        ]

        weights = [
            total_effective_area
        ]
    """

    # ==================================================
    # VALIDATE INPUT
    # ==================================================

    if len(ghi_arrays) != len(weights):

        raise ValueError(
            "Number of GHI arrays must match "
            "number of weights."
        )

    blocks = np.asarray(
        blocks,
        dtype=float
    )

    # ==================================================
    # TRACKING ANGLES
    # ==================================================

    _, panel = calculate_tracking_angles(
        blocks=blocks,
        ghi_start=ghi_start,
        ghi_end=ghi_end,
        ghi_max=ghi_max,
        east_limit=east_limit,
        west_limit=west_limit
    )

    # ==================================================
    # COS PANEL ANGLE
    # ==================================================

    cos_alpha = np.cos(
        np.radians(panel)
    )

    cos_alpha = np.clip(
        cos_alpha,
        1e-6,
        None
    )

    # ==================================================
    # FINAL FORECAST
    # ==================================================

    forecast = np.zeros(
        len(blocks),
        dtype=float
    )

    # ==================================================
    # PROCESS EACH GHI ARRAY
    # ==================================================

    for ghi, weight in zip(
        ghi_arrays,
        weights
    ):

        ghi = np.asarray(
            ghi,
            dtype=float
        )

        if len(ghi) != len(blocks):

            raise ValueError(
                "GHI array length does not "
                "match blocks."
            )

        # ---------------------------------------------
        # DHI
        # ---------------------------------------------

        dhi = calculate_dhi(
            ghi=ghi,
            dhi_percent=dhi_percent
        )

        # ---------------------------------------------
        # DNI
        # ---------------------------------------------

        dni = calculate_dni(
            ghi=ghi,
            dhi=dhi,
            panel_angle=panel
        )

        # ---------------------------------------------
        # POWER
        # ---------------------------------------------

        forecast += (
            dni * weight
        ) / 1_000_000

    return np.maximum(
        forecast,
        0
    )
from scipy.optimize import differential_evolution


def calculate_loss_corrected_weights(
    area_df,
    efficiency_loss,
    weight_factors
):
    """
    Calculate effective area / efficiency weights.

    Cluster plant:
        weight_factors = [factor1, factor2, ..., factor5]

    Non-cluster plant:
        weight_factors = [1.0]
    """

    df = area_df.copy()

    # ---------------------------------------------
    # Efficiency correction
    # ---------------------------------------------

    df["Efficiency Losses(%)"] = float(
        efficiency_loss
    )

    df["Net Efficiency (%)"] = (
        df["Standard PV Efficiency (%)"]
        - df["Efficiency Losses(%)"]
    )

    # ---------------------------------------------
    # Effective area
    # ---------------------------------------------

    effective_area = (
        df["Total area(m2)"]
        * df["Net Efficiency (%)"]
        / 100.0
    )

    total_effective_area = (
        effective_area.sum()
    )

    # ---------------------------------------------
    # Apply weight factors
    # ---------------------------------------------

    weights = (
        total_effective_area
        * np.asarray(
            weight_factors,
            dtype=float
        )
    )

    return weights


def optimize_tracking_parameters(
    actual,
    ghi_arrays,
    blocks,
    area_df,
    weight_factors,
    efficiency_loss,
    bounds,
    maxiter=100,
    popsize=15,
    seed=42,
    callback=None
):
    """
    Optimize tracking parameters:

        DHI
        GHI Starting Block
        GHI Ending Block
        GHI Max Block
        East Tracking Limit
        West Tracking Limit

    Works for both cluster and non-cluster plants.
    """

    # ==================================================
    # CLEAN INPUT
    # ==================================================

    actual = np.asarray(
        actual,
        dtype=float
    )

    blocks = np.asarray(
        blocks,
        dtype=float
    )

    # ==================================================
    # VALIDATION
    # ==================================================

    if len(actual) != len(blocks):

        raise ValueError(
            "Actual and Blocks must have same length."
        )

    if len(ghi_arrays) == 0:

        raise ValueError(
            "At least one GHI array is required."
        )

    for ghi in ghi_arrays:

        if len(ghi) != len(blocks):

            raise ValueError(
                "GHI array length must match blocks."
            )

    # ==================================================
    # CALCULATE WEIGHTS
    # ==================================================

    weights = calculate_loss_corrected_weights(

        area_df=area_df,

        efficiency_loss=efficiency_loss,

        weight_factors=weight_factors
    )

    # ==================================================
    # VALIDATE WEIGHTS
    # ==================================================

    if len(weights) != len(ghi_arrays):

        raise ValueError(
            f"GHI arrays ({len(ghi_arrays)}) "
            f"and weights ({len(weights)}) "
            f"must have same length."
        )

    # ==================================================
    # OBJECTIVE FUNCTION
    # ==================================================

    def objective(x):

        # ---------------------------------------------
        # Parameters
        # ---------------------------------------------

        DHI = int(round(x[0]))

        start = int(round(x[1]))

        end = int(round(x[2]))

        max_block = int(round(x[3]))

        east = int(round(x[4]))

        west = int(round(x[5]))

        # ---------------------------------------------
        # Block configuration
        # ---------------------------------------------

        if not (
            start < max_block < end
        ):

            return 1e9

        # ---------------------------------------------
        # Calculate forecast
        # ---------------------------------------------

        try:

            prediction = calculate_tracking_forecast(

                ghi_arrays=ghi_arrays,

                weights=weights,

                blocks=blocks,

                dhi_percent=DHI,

                ghi_start=start,

                ghi_end=end,

                ghi_max=max_block,

                east_limit=east,

                west_limit=west
            )

        except Exception:

            return 1e9

        # ---------------------------------------------
        # Daylight mask
        # ---------------------------------------------

        mask = actual > 0

        act = actual[mask]

        pred = prediction[mask]

        if len(act) == 0:

            return 1e9

        if act.max() <= 0:

            return 1e9

        # ---------------------------------------------
        # Block error
        # ---------------------------------------------

        block_error_value = (
            np.mean(
                np.abs(
                    act - pred
                )
            )
            / act.max()
        )

        # ---------------------------------------------
        # Peak error
        # ---------------------------------------------

        peak_error_value = (
            abs(
                act.max()
                - pred.max()
            )
            / act.max()
        )

        # ---------------------------------------------
        # Energy error
        # ---------------------------------------------

        if act.sum() == 0:

            return 1e9

        energy_error_value = (
            abs(
                act.sum()
                - pred.sum()
            )
            / act.sum()
        )

        # ---------------------------------------------
        # Combined score
        # ---------------------------------------------

        score = (

            0.80
            * block_error_value

            +

            0.10
            * peak_error_value

            +

            0.10
            * energy_error_value
        )

        if (
            np.isnan(score)
            or np.isinf(score)
        ):

            return 1e9

        return score

    # ==================================================
    # DIFFERENTIAL EVOLUTION
    # ==================================================

    result = differential_evolution(

        objective,

        bounds=bounds,

        strategy="best1bin",

        maxiter=maxiter,

        popsize=popsize,

        tol=0.001,

        mutation=(0.5, 1),

        recombination=0.7,

        seed=seed,

        polish=True,

        workers=1,

        callback=callback
    )

    # ==================================================
    # BEST PARAMETERS
    # ==================================================

    best = np.round(
        result.x
    ).astype(int)

    parameters = {

        "DHI":
            int(best[0]),

        "Starting Block":
            int(best[1]),

        "Ending Block":
            int(best[2]),

        "Max Block":
            int(best[3]),

        "East Limit":
            int(best[4]),

        "West Limit":
            int(best[5]),
    }

    # ==================================================
    # RETURN
    # ==================================================

    return {

        "parameters":
            parameters,

        "score":
            float(result.fun),

        "weights":
            weights,

        "result":
            result,
    }
