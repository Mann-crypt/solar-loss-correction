# modules/calculations.py

import numpy as np
import pandas as pd


# ==========================================================
# BASIC MATH HELPERS
# ==========================================================

def sin_deg(angle):
    """
    Sine of an angle given in degrees.
    """
    return np.sin(np.radians(angle))


def cos_deg(angle):
    """
    Cosine of an angle given in degrees.
    """
    return np.cos(np.radians(angle))


def clip_zero(values):
    """
    Replace negative values with zero.
    """
    values = np.asarray(values, dtype=float)

    return np.maximum(values, 0.0)


# ==========================================================
# SOLAR DECLINATION
# ==========================================================

def calculate_declination_angle(day_of_year):
    """
    Calculate solar declination angle in degrees.

    Uses the common approximation:

        δ = 23.45 * sin(360 * (284 + n) / 365)

    Parameters
    ----------
    day_of_year : int or array-like
        Day number of the year.

    Returns
    -------
    numpy.ndarray or float
    """

    n = np.asarray(
        day_of_year,
        dtype=float,
    )

    return 23.45 * np.sin(
        np.radians(
            360.0 * (284.0 + n) / 365.0
        )
    )


# ==========================================================
# SOLAR ELEVATION
# ==========================================================

def calculate_elevation_angle(
    latitude,
    declination,
    hour_angle,
):
    """
    Calculate solar elevation angle.

    Formula:

        sin(elevation)
        =
        sin(latitude) sin(declination)
        +
        cos(latitude) cos(declination) cos(hour_angle)

    All angles are in degrees.
    """

    latitude = np.asarray(
        latitude,
        dtype=float,
    )

    declination = np.asarray(
        declination,
        dtype=float,
    )

    hour_angle = np.asarray(
        hour_angle,
        dtype=float,
    )

    sin_elevation = (
        sin_deg(latitude)
        * sin_deg(declination)
        +
        cos_deg(latitude)
        * cos_deg(declination)
        * cos_deg(hour_angle)
    )

    sin_elevation = np.clip(
        sin_elevation,
        -1.0,
        1.0,
    )

    return np.degrees(
        np.arcsin(sin_elevation)
    )


# ==========================================================
# POA CALCULATION
# ==========================================================

def calculate_poa(
    dni,
    dhi,
    ghi,
    zenith_angle,
    panel_angle=0,
):
    """
    Calculate Plane of Array irradiance.

    Simplified single-axis formulation used by the project.

    Direct component:

        DNI * cos(theta - alpha)

    Diffuse component:

        DHI

    Returns POA in the same irradiance unit as the inputs.
    """

    dni = np.asarray(
        dni,
        dtype=float,
    )

    dhi = np.asarray(
        dhi,
        dtype=float,
    )

    ghi = np.asarray(
        ghi,
        dtype=float,
    )

    zenith_angle = np.asarray(
        zenith_angle,
        dtype=float,
    )

    panel_angle = np.asarray(
        panel_angle,
        dtype=float,
    )

    projection = calculate_projection(
        zenith_angle,
        panel_angle,
    )

    poa = (
        dni * projection
        + dhi
    )

    return np.maximum(
        poa,
        0.0,
    )


# ==========================================================
# PROJECTION
# ==========================================================

def calculate_projection(
    zenith_angle,
    panel_angle,
):
    """
    Calculate the cosine projection factor.

        projection = cos(zenith - panel_angle)
    """

    zenith_angle = np.asarray(
        zenith_angle,
        dtype=float,
    )

    panel_angle = np.asarray(
        panel_angle,
        dtype=float,
    )

    projection = np.cos(
        np.radians(
            zenith_angle - panel_angle
        )
    )

    return np.maximum(
        projection,
        0.0,
    )


# ==========================================================
# DHI
# ==========================================================

def calculate_dhi(
    ghi,
    dhi_percent,
):
    """
    Calculate DHI from GHI.

        DHI = GHI * DHI%

    dhi_percent is supplied as a percentage.
    """

    ghi = np.asarray(
        ghi,
        dtype=float,
    )

    dhi_percent = float(
        dhi_percent
    )

    dhi = (
        ghi
        * dhi_percent
        / 100.0
    )

    return np.maximum(
        dhi,
        0.0,
    )


# ==========================================================
# DNI
# ==========================================================

def calculate_dni(
    ghi,
    dhi,
    zenith_angle=None,
    cos_zenith=None,
):
    """
    Calculate DNI.

    If cos_zenith is supplied:

        DNI = (GHI - DHI) / cos(zenith)

    If zenith_angle is supplied, its cosine is calculated.

    Small cosine values are protected against division by zero.
    """

    ghi = np.asarray(
        ghi,
        dtype=float,
    )

    dhi = np.asarray(
        dhi,
        dtype=float,
    )

    if cos_zenith is None:

        if zenith_angle is None:

            raise ValueError(
                "Either zenith_angle or "
                "cos_zenith must be supplied."
            )

        cos_zenith = np.cos(
            np.radians(
                zenith_angle
            )
        )

    cos_zenith = np.asarray(
        cos_zenith,
        dtype=float,
    )

    cos_zenith = np.clip(
        cos_zenith,
        1e-6,
        None,
    )

    dni = (
        ghi - dhi
    ) / cos_zenith

    return np.maximum(
        dni,
        0.0,
    )


# ==========================================================
# TRACKING ANGLES
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
    Calculate solar zenith and tracker panel angle
    from the optimized block configuration.

    Parameters
    ----------
    blocks : array-like
        15-minute block numbers.

    ghi_start : int
        Starting block.

    ghi_end : int
        Ending block.

    ghi_max : int
        Block corresponding to maximum solar elevation.

    east_limit : float
        Maximum tracker angle on the east side.

    west_limit : float
        Maximum tracker angle on the west side.

    Returns
    -------
    zenith, panel
    """

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    ghi_start = float(
        ghi_start
    )

    ghi_end = float(
        ghi_end
    )

    ghi_max = float(
        ghi_max
    )

    east_limit = float(
        east_limit
    )

    west_limit = float(
        west_limit
    )

    # ------------------------------------------------------
    # Safety validation
    # ------------------------------------------------------

    if not (
        ghi_start
        < ghi_max
        < ghi_end
    ):

        raise ValueError(
            "GHI Start must be less than "
            "GHI Max and GHI Max must be "
            "less than GHI End."
        )

    # ------------------------------------------------------
    # Slopes
    #
    # These are the same relationships used in the
    # original tracking optimization.
    # ------------------------------------------------------

    denominator_1 = (
        ghi_start
        - 1
        - ghi_max
    )

    denominator_2 = (
        ghi_end
        + 1
        - ghi_max
    )

    if (
        denominator_1 == 0
        or denominator_2 == 0
    ):

        raise ValueError(
            "Invalid GHI block configuration."
        )

    m1 = (
        90.0
        / denominator_1
    )

    m2 = (
        90.0
        / denominator_2
    )

    # ------------------------------------------------------
    # Zenith
    # ------------------------------------------------------

    zenith = np.where(

        blocks <= ghi_max,

        np.minimum(
            89.0,
            m1
            * (
                blocks
                - ghi_max
            ),
        ),

        np.minimum(
            89.0,
            m2
            * (
                blocks
                - ghi_max
            ),
        ),
    )

    # ------------------------------------------------------
    # Panel angle
    # ------------------------------------------------------

    panel = np.where(

        blocks < ghi_max,

        np.minimum(
            zenith,
            abs(east_limit),
        ),

        np.where(

            (
                (blocks > ghi_max)
                &
                (zenith > west_limit)
            ),

            west_limit,

            zenith,
        ),
    )

    return (
        zenith,
        panel,
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
    Calculate tracking power forecast.

    Main calculation:

        DHI = GHI * DHI%

        DNI = (GHI - DHI) / cos(panel angle)

        Power =
            DNI * effective area / 1,000,000

    For cluster plants:

        Power =
            sum(
                DNI_cluster
                * effective_weight_cluster
            )

    For non-cluster plants:

        one GHI array + one effective weight.

    Returns
    -------
    numpy.ndarray
        Forecast power in MW.
    """

    # ======================================================
    # CLEAN INPUTS
    # ======================================================

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    if len(ghi_arrays) == 0:

        raise ValueError(
            "No GHI arrays supplied."
        )

    weights = np.asarray(
        weights,
        dtype=float,
    )

    if len(weights) != len(
        ghi_arrays
    ):

        raise ValueError(
            "Number of weights must "
            "match number of GHI arrays."
        )

    cleaned_ghi = []

    for i, ghi in enumerate(
        ghi_arrays
    ):

        ghi = np.asarray(
            ghi,
            dtype=float,
        )

        if len(ghi) != len(
            blocks
        ):

            raise ValueError(
                f"GHI array {i + 1} "
                "length does not match blocks."
            )

        ghi = np.nan_to_num(
            ghi,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        ghi = np.maximum(
            ghi,
            0.0,
        )

        cleaned_ghi.append(
            ghi
        )

    weights = np.nan_to_num(
        weights,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    weights = np.maximum(
        weights,
        0.0,
    )

    # ======================================================
    # TRACKING ANGLES
    # ======================================================

    zenith, panel = (
        calculate_tracking_angles(

            blocks=blocks,

            ghi_start=ghi_start,

            ghi_end=ghi_end,

            ghi_max=ghi_max,

            east_limit=east_limit,

            west_limit=west_limit,
        )
    )

    # ======================================================
    # COSINE OF PANEL ANGLE
    # ======================================================

    cos_panel = np.cos(
        np.radians(
            panel
        )
    )

    # Same protection used in the original calculation.
    cos_panel = np.clip(
        cos_panel,
        1e-6,
        None,
    )

    # ======================================================
    # FORECAST
    # ======================================================

    prediction = np.zeros(
        len(blocks),
        dtype=float,
    )

    for ghi, weight in zip(
        cleaned_ghi,
        weights,
    ):

        # --------------------------------------------------
        # DHI
        # --------------------------------------------------

        dhi = (
            ghi
            * float(dhi_percent)
            / 100.0
        )

        # --------------------------------------------------
        # DNI
        #
        # Important:
        # This follows the original tracking calculation,
        # where the panel-angle cosine is used.
        # --------------------------------------------------

        dni = (
            ghi - dhi
        ) / cos_panel

        dni = np.maximum(
            dni,
            0.0,
        )

        # --------------------------------------------------
        # Power
        #
        # Effective weight has units corresponding to
        # m² × efficiency.
        #
        # Irradiance × effective area / 1,000,000
        # gives MW.
        # --------------------------------------------------

        prediction += (
            dni
            * float(weight)
        ) / 1_000_000.0

    # ======================================================
    # CLEAN RESULT
    # ======================================================

    prediction = np.nan_to_num(
        prediction,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    prediction = np.maximum(
        prediction,
        0.0,
    )

    return prediction


# ==========================================================
# RT FORECAST
# ==========================================================

def calculate_rt_forecast(
    ghi,
    panel_angle,
    efficiency,
    area,
    dhi_percent=0,
):
    """
    Generic fixed/RT power forecast.

    This function is kept for compatibility with the
    earlier solar forecasting screens.

    Parameters
    ----------
    ghi : array-like
        GHI values.

    panel_angle : array-like
        Panel angle relative to the incoming radiation.

    efficiency : float
        Efficiency in percentage.

    area : float
        Total panel area in m².

    dhi_percent : float
        DHI percentage.

    Returns
    -------
    numpy.ndarray
        Power forecast in MW.
    """

    ghi = np.asarray(
        ghi,
        dtype=float,
    )

    panel_angle = np.asarray(
        panel_angle,
        dtype=float,
    )

    # ------------------------------------------------------
    # DHI / DNI
    # ------------------------------------------------------

    dhi = (
        ghi
        * float(dhi_percent)
        / 100.0
    )

    cos_angle = np.cos(
        np.radians(
            panel_angle
        )
    )

    cos_angle = np.clip(
        cos_angle,
        1e-6,
        None,
    )

    dni = (
        ghi - dhi
    ) / cos_angle

    # ------------------------------------------------------
    # POA
    # ------------------------------------------------------

    poa = (
        dni
        * np.maximum(
            cos_angle,
            0.0,
        )
        + dhi
    )

    # ------------------------------------------------------
    # Power
    # ------------------------------------------------------

    power = (
        poa
        * float(area)
        * float(efficiency)
        / 100.0
    ) / 1_000_000.0

    return np.maximum(
        power,
        0.0,
    )


# ==========================================================
# SYMMETRY
# ==========================================================

def calculate_symmetry(
    values,
    shift=0,
    alpha=0.5,
):
    """
    Create a symmetric profile from a solar generation curve.

    The previous implementation used:

        shifted = roll(profile, -shift)

        symmetric =
            alpha * profile
            +
            (1-alpha) * reversed(shifted)
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    if len(values) == 0:
        return values.copy()

    shift = int(shift)

    alpha = float(alpha)

    shifted = np.roll(
        values,
        -shift,
    )

    symmetric = (
        alpha * values
        +
        (1.0 - alpha)
        * shifted[::-1]
    )

    return np.maximum(
        symmetric,
        0.0,
    )


# ==========================================================
# BEST SYMMETRY SHIFT
# ==========================================================

def find_best_shift(
    values,
):
    """
    Find the shift producing the lowest RMSE
    between a curve and its symmetric version.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    if len(values) == 0:
        return 0

    best_shift = 0
    least_error = np.inf

    for shift in range(
        len(values)
    ):

        shifted = np.roll(
            values,
            -shift,
        )

        symmetric = (
            values
            + shifted[::-1]
        ) / 2.0

        error = np.sqrt(
            np.mean(
                (
                    values
                    - symmetric
                ) ** 2
            )
        )

        if error < least_error:

            least_error = error
            best_shift = shift

    return int(
        best_shift
    )


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
    Calculate effective area / weights.

    Cluster:
        One effective weight per GHI cluster.

    Non-cluster:
        One total plant effective weight.

    Effective area:

        Total Area
        ×
        Net Efficiency
        / 100

    Net Efficiency:

        Standard PV Efficiency
        -
        Efficiency Loss
    """

    if area_df is None:

        raise ValueError(
            "Area data is missing."
        )

    if area_df.empty:

        raise ValueError(
            "Area data is empty."
        )

    df = area_df.copy()

    # ======================================================
    # REQUIRED COLUMNS
    # ======================================================

    required_columns = [
        "Standard PV Efficiency (%)",
        "Total area(m2)",
    ]

    missing = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing:

        raise ValueError(
            "Missing required area columns: "
            + ", ".join(
                missing
            )
        )

    # ======================================================
    # EFFICIENCY
    # ======================================================

    df["Efficiency Losses(%)"] = (
        float(efficiency_loss)
    )

    standard_efficiency = pd.to_numeric(
        df[
            "Standard PV Efficiency (%)"
        ],
        errors="coerce",
    ).fillna(0.0)

    df["Net Efficiency (%)"] = (
        standard_efficiency
        - df[
            "Efficiency Losses(%)"
        ]
    )

    # Prevent negative efficiency

    df["Net Efficiency (%)"] = np.maximum(
        df[
            "Net Efficiency (%)"
        ],
        0.0,
    )

    # ======================================================
    # EFFECTIVE AREA
    # ======================================================

    total_area = pd.to_numeric(
        df[
            "Total area(m2)"
        ],
        errors="coerce",
    ).fillna(0.0)

    df["Effective Area"] = (
        total_area
        * df[
            "Net Efficiency (%)"
        ]
        / 100.0
    )

    total_effective_area = (
        df[
            "Effective Area"
        ].sum()
    )

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    if not has_cluster:

        return np.asarray(
            [
                total_effective_area
            ],
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

        raise ValueError(
            "Cluster weight factors "
            "must have a positive sum."
        )

    # Normalize

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
