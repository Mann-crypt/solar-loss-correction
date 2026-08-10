# screens/loss_correction.py

import streamlit as st
import pandas as pd
import numpy as np

from modules.excel_reader import read_tracking_input

from modules.calculations import (
    calculate_tracking_forecast,
)

from modules.optimization import (
    optimize_tracking_parameters,
)

from modules.metrics import (
    calculate_all_metrics,
)

from modules.plotting import (
    plot_loss_correction,
)

from modules.utils import (
    generate_blocks,
    generate_time_blocks,
)


# ==========================================================
# SESSION STATE
# ==========================================================

def reset_loss_correction_state():

    keys = [
        "loss_tracking_input",
        "loss_result",
        "loss_file_signature",
    ]

    for key in keys:

        st.session_state.pop(
            key,
            None,
        )


# ==========================================================
# COLUMN NORMALIZATION
# ==========================================================

def normalize_columns(df):
    """
    Normalize dataframe column names.

    Handles:
        spaces
        new lines
        underscores
        hyphens
        case differences
    """

    if df is None:
        return None

    df = df.copy()

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
        .str.replace("_", " ", regex=False)
        .str.replace("-", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.lower()
    )

    return df


# ==========================================================
# COLUMN FINDER
# ==========================================================

def find_column(df, possible_names):
    """
    Find a dataframe column using flexible matching.
    """

    if df is None or df.empty:
        return None

    normalized_columns = {}

    for col in df.columns:

        key = (
            str(col)
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
        )

        key = " ".join(key.split())

        normalized_columns[key] = col

    for name in possible_names:

        key = (
            str(name)
            .strip()
            .lower()
            .replace("_", " ")
            .replace("-", " ")
        )

        key = " ".join(key.split())

        if key in normalized_columns:

            return normalized_columns[key]

    return None


# ==========================================================
# FIND ACTUAL GENERATION
# ==========================================================

def extract_actual(data):
    """
    Extract actual generation.

    Priority:

    1. Fixed sheet
    2. Tracking sheet
    3. Backend Cal
    4. Backend Cal CL sheets

    This is important because Actual generation
    does not necessarily exist in Tracking.
    """

    # ------------------------------------------------------
    # 1. FIXED SHEET
    # ------------------------------------------------------

    fixed = data.get("fixed")

    if fixed is not None:

        fixed = fixed.copy()

        fixed.columns = (
            fixed.columns
            .astype(str)
            .str.strip()
            .str.replace(
                "\n",
                " ",
                regex=False
            )
        )

        actual_col = find_column(
            fixed,
            [
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Power",
                "Power (MW)",
                "Generation",
                "Actual Generation",
                "Actual_Generation",
            ],
        )

        if actual_col is not None:

            actual = pd.to_numeric(
                fixed[actual_col],
                errors="coerce",
            )

            actual = (
                actual
                .fillna(0)
                .to_numpy(dtype=float)
            )

            return actual

    # ------------------------------------------------------
    # 2. TRACKING
    # ------------------------------------------------------

    tracking = data.get("tracking")

    if tracking is not None:

        actual_col = find_column(
            tracking,
            [
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Power",
                "Power (MW)",
                "Generation",
                "Actual Generation",
                "Actual_Generation",
            ],
        )

        if actual_col is not None:

            actual = pd.to_numeric(
                tracking[actual_col],
                errors="coerce",
            )

            return (
                actual
                .fillna(0)
                .to_numpy(dtype=float)
            )

    # ------------------------------------------------------
    # 3. BACKEND CAL
    # ------------------------------------------------------

    backend = data.get("backend")

    if backend is not None:

        actual_col = find_column(
            backend,
            [
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Power",
                "Power (MW)",
                "Generation",
                "Actual Generation",
                "Actual_Generation",
            ],
        )

        if actual_col is not None:

            actual = pd.to_numeric(
                backend[actual_col],
                errors="coerce",
            )

            return (
                actual
                .fillna(0)
                .to_numpy(dtype=float)
            )

    # ------------------------------------------------------
    # 4. CLUSTER BACKEND SHEETS
    # ------------------------------------------------------

    backend_cluster = data.get(
        "backend_cluster"
    )

    if backend_cluster is not None:

        if isinstance(
            backend_cluster,
            list
        ):

            for backend_df in backend_cluster:

                actual_col = find_column(
                    backend_df,
                    [
                        "Actual",
                        "Actual Power",
                        "Actual Power (MW)",
                        "Power",
                        "Power (MW)",
                        "Generation",
                        "Actual Generation",
                    ],
                )

                if actual_col is not None:

                    actual = pd.to_numeric(
                        backend_df[actual_col],
                        errors="coerce",
                    )

                    return (
                        actual
                        .fillna(0)
                        .to_numpy(dtype=float)
                    )

    # ------------------------------------------------------
    # NOTHING FOUND
    # ------------------------------------------------------

    available = []

    for name in [
        "fixed",
        "tracking",
        "backend",
    ]:

        df = data.get(name)

        if df is not None:

            available.append(
                f"{name}: {list(df.columns)}"
            )

    raise ValueError(
        "Could not find Actual generation column.\n\n"
        + "\n".join(available)
    )


# ==========================================================
# EXTRACT GHI ARRAYS
# ==========================================================

def extract_ghi_arrays(data):
    """
    Extract GHI arrays.

    Cluster:
        CL1-GHI ... CL5-GHI

    Non-cluster:
        GHI Forecast from Fixed.
    """

    # ======================================================
    # CLUSTER
    # ======================================================

    if data.get("has_cluster", False):

        cluster_data = data.get(
            "cluster_data"
        )

        if cluster_data is None:

            raise ValueError(
                "Workbook is marked as cluster "
                "but cluster GHI data was not found."
            )

        expected_clusters = [
            "CL1-GHI",
            "CL2-GHI",
            "CL3-GHI",
            "CL4-GHI",
            "CL5-GHI",
        ]

        ghi_arrays = []

        for cluster in expected_clusters:

            col = find_column(
                cluster_data,
                [
                    cluster,
                    cluster.replace("-", " "),
                    cluster.replace("-", "_"),
                ],
            )

            if col is None:

                raise ValueError(
                    f"Missing {cluster} in cluster data."
                )

            ghi = pd.to_numeric(
                cluster_data[col],
                errors="coerce",
            )

            ghi = (
                ghi
                .fillna(0)
                .to_numpy(dtype=float)
            )

            ghi_arrays.append(ghi)

        return ghi_arrays

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    fixed = data.get("fixed")

    if fixed is None:

        raise ValueError(
            "Non-cluster workbook does not contain "
            "a Fixed sheet."
        )

    ghi_col = find_column(
        fixed,
        [
            "GHI_Forecast",
            "GHI Forecast",
            "GHI",
            "GHI Forecast 15min",
            "GHI_Forecast_15min",
        ],
    )

    if ghi_col is None:

        raise ValueError(
            "Could not find GHI forecast column "
            "in Fixed sheet."
        )

    ghi = pd.to_numeric(
        fixed[ghi_col],
        errors="coerce",
    )

    ghi = (
        ghi
        .fillna(0)
        .to_numpy(dtype=float)
    )

    ghi = np.maximum(
        ghi,
        0,
    )

    return [ghi]


# ==========================================================
# EXTRACT WEIGHT FACTORS
# ==========================================================

def extract_weight_factors(
    data,
    number_of_arrays,
):
    """
    Extract cluster weighting factors.

    For cluster:
        Use explicit weight factors if available.

    For non-cluster:
        Return [1.0].
    """

    # ------------------------------------------------------
    # NON-CLUSTER
    # ------------------------------------------------------

    if not data.get(
        "has_cluster",
        False
    ):

        return np.asarray(
            [1.0],
            dtype=float,
        )

    # ------------------------------------------------------
    # CLUSTER
    # ------------------------------------------------------

    area_weights = data.get(
        "area_weights"
    )

    if area_weights is None:

        return (
            np.ones(
                number_of_arrays,
                dtype=float,
            )
            / number_of_arrays
        )

    weight_col = find_column(
        area_weights,
        [
            "Weight",
            "Weights",
            "Weight Factor",
            "Weight Factor (%)",
            "Cluster Weight",
            "Cluster Weight (%)",
        ],
    )

    if weight_col is not None:

        values = pd.to_numeric(
            area_weights[weight_col],
            errors="coerce",
        ).dropna()

        if len(values) >= number_of_arrays:

            values = (
                values
                .iloc[:number_of_arrays]
                .to_numpy(dtype=float)
            )

            # Percentage to fraction

            if np.nanmax(
                np.abs(values)
            ) > 1:

                values = values / 100.0

            total = values.sum()

            if total > 0:

                values = values / total

            return values

    # ------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------

    return (
        np.ones(
            number_of_arrays,
            dtype=float,
        )
        / number_of_arrays
    )


# ==========================================================
# PREPARE ARRAY
# ==========================================================

def prepare_array(
    values,
    length=96,
    name="Array",
):
    """
    Clean an input array and force 96 blocks.
    """

    values = np.asarray(
        values,
        dtype=float,
    )

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=0.0,
        neginf=0.0,
    )

    values = np.maximum(
        values,
        0,
    )

    if len(values) < length:

        raise ValueError(
            f"{name} requires at least "
            f"{length} blocks. "
            f"Found {len(values)}."
        )

    return values[:length]


# ==========================================================
# MAIN SCREEN
# ==========================================================

def show_loss_correction():

    st.title(
        "⛅ Loss Correction"
    )

    st.caption(
        "Optimize Tracking Loss Correction "
        "using DHI, GHI block configuration, "
        "tracking limits and efficiency loss."
    )

    # ======================================================
    # FILE UPLOAD
    # ======================================================

    uploaded_file = st.file_uploader(
        "Upload Tracking Excel Workbook",
        type=["xlsx"],
        key="loss_correction_uploader",
    )

    if uploaded_file is None:

        st.info(
            "Upload the Excel workbook containing "
            "the required tracking data."
        )

        return

    # ======================================================
    # FILE SIGNATURE
    # ======================================================

    file_signature = (
        uploaded_file.name,
        uploaded_file.size,
    )

    if (
        st.session_state.get(
            "loss_file_signature"
        )
        != file_signature
    ):

        reset_loss_correction_state()

        st.session_state.loss_file_signature = (
            file_signature
        )

    # ======================================================
    # READ WORKBOOK
    # ======================================================

    try:

        data = read_tracking_input(
            uploaded_file
        )

    except Exception as e:

        st.error(
            f"Unable to read workbook: {e}"
        )

        return

    # ======================================================
    # WORKBOOK TYPE
    # ======================================================

    has_cluster = data.get(
        "has_cluster",
        False,
    )

    if has_cluster:

        st.success(
            "Cluster plant detected: "
            "CL1-GHI to CL5-GHI will be used."
        )

    else:

        st.info(
            "Non-cluster plant detected: "
            "normal GHI Forecast from Fixed will be used."
        )

    # ======================================================
    # EXTRACT ACTUAL
    # ======================================================

    try:

        actual = extract_actual(
            data
        )

        actual = prepare_array(
            actual,
            name="Actual generation",
        )

    except Exception as e:

        st.error(
            f"Unable to extract Actual generation: {e}"
        )

        return

    # ======================================================
    # EXTRACT GHI
    # ======================================================

    try:

        ghi_arrays = extract_ghi_arrays(
            data
        )

        ghi_arrays = [
            prepare_array(
                ghi,
                name=f"GHI {i + 1}",
            )
            for i, ghi
            in enumerate(ghi_arrays)
        ]

    except Exception as e:

        st.error(
            f"Unable to extract GHI data: {e}"
        )

        return

    # ======================================================
    # BLOCKS
    # ======================================================

    blocks = generate_blocks(
        96
    )

    time_blocks = generate_time_blocks(
        96
    )

    # ======================================================
    # AREA
    # ======================================================

    area_df = data.get(
        "area"
    )

    if area_df is None:

        st.error(
            "Area & Efficiency data "
            "could not be loaded."
        )

        return

    # ======================================================
    # WEIGHT FACTORS
    # ======================================================

    weight_factors = extract_weight_factors(
        data,
        len(ghi_arrays),
    )

    # ======================================================
    # INPUT SUMMARY
    # ======================================================

    st.subheader(
        "Input Summary"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Plant Type",
        "Cluster" if has_cluster else "Non-Cluster",
    )

    col2.metric(
        "GHI Arrays",
        len(ghi_arrays),
    )

    col3.metric(
        "Actual Peak",
        f"{actual.max():.3f}",
    )

    col4.metric(
        "Latitude",
        f"{data['latitude']:.4f}°",
    )

    # ======================================================
    # INPUT DATA
    # ======================================================

    with st.expander(
        "View Input Data"
    ):

        input_df = pd.DataFrame({

            "Block":
                blocks,

            "Time":
                time_blocks,

            "Actual":
                actual,

        })

        if has_cluster:

            for i, ghi in enumerate(
                ghi_arrays,
                start=1,
            ):

                input_df[
                    f"CL{i}-GHI"
                ] = ghi

        else:

            input_df[
                "GHI Forecast"
            ] = ghi_arrays[0]

        st.dataframe(
            input_df,
            use_container_width=True,
            hide_index=True,
        )

    # ======================================================
    # OPTIMIZATION SETTINGS
    # ======================================================

    st.subheader(
        "Optimization Settings"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        maxiter = st.number_input(
            "Maximum Iterations",
            min_value=10,
            max_value=500,
            value=100,
            step=10,
        )

    with col2:

        popsize = st.number_input(
            "Population Size",
            min_value=5,
            max_value=50,
            value=15,
            step=5,
        )

    with col3:

        seed = st.number_input(
            "Random Seed",
            min_value=0,
            max_value=9999,
            value=42,
            step=1,
        )

    # ======================================================
    # PARAMETER BOUNDS
    # ======================================================

    st.subheader(
        "Parameter Bounds"
    )

    bounds = [

        (0, 10),       # DHI

        (10, 30),      # Starting Block

        (65, 80),      # Ending Block

        (47, 53),      # Max Block

        (10, 70),      # East Limit

        (10, 70),      # West Limit

        (0, 10),       # Efficiency Loss

    ]

    bounds_df = pd.DataFrame({

        "Parameter": [

            "DHI",

            "Starting Block",

            "Ending Block",

            "Max Block",

            "East Tracking Limit",

            "West Tracking Limit",

            "Efficiency Loss",

        ],

        "Minimum": [

            x[0]
            for x in bounds

        ],

        "Maximum": [

            x[1]
            for x in bounds

        ],

    })

    st.dataframe(
        bounds_df,
        use_container_width=True,
        hide_index=True,
    )

    # ======================================================
    # RUN OPTIMIZATION
    # ======================================================

    if st.button(
        "🚀 Run Loss Correction",
        type="primary",
        use_container_width=True,
    ):

        progress = st.progress(
            0
        )

        status = st.empty()

        status.info(
            "Starting optimization..."
        )

        try:

            # ------------------------------------------------
            # IMPORTANT:
            # efficiency_loss is now optimized as x[6]
            # inside optimize_tracking_parameters.
            # ------------------------------------------------

            result = optimize_tracking_parameters(

                actual=actual,

                ghi_arrays=ghi_arrays,

                blocks=blocks,

                area_df=area_df,

                weight_factors=weight_factors,

                bounds=bounds,

                maxiter=int(maxiter),

                popsize=int(popsize),

                seed=int(seed),

            )

            progress.progress(
                100
            )

            status.success(
                "Optimization completed."
            )

            # ==================================================
            # BEST PARAMETERS
            # ==================================================

            parameters = result[
                "parameters"
            ]

            # ==================================================
            # FINAL FORECAST
            # ==================================================

            final_forecast = (
                calculate_tracking_forecast(

                    ghi_arrays=ghi_arrays,

                    weights=result["weights"],

                    blocks=blocks,

                    dhi_percent=parameters[
                        "DHI"
                    ],

                    ghi_start=parameters[
                        "Starting Block"
                    ],

                    ghi_end=parameters[
                        "Ending Block"
                    ],

                    ghi_max=parameters[
                        "Max Block"
                    ],

                    east_limit=parameters[
                        "East Tracking Limit"
                    ],

                    west_limit=parameters[
                        "West Tracking Limit"
                    ],

                )
            )

            final_forecast = np.maximum(
                final_forecast,
                0,
            )

            # ==================================================
            # METRICS
            # ==================================================

            metrics = calculate_all_metrics(
                actual,
                final_forecast,
            )

            # ==================================================
            # SAVE RESULT
            # ==================================================

            st.session_state.loss_result = {

                "parameters":
                    parameters,

                "actual":
                    actual,

                "forecast":
                    final_forecast,

                "metrics":
                    metrics,

                "weights":
                    result["weights"],

                "score":
                    result["score"],

            }

        except Exception as e:

            st.error(
                f"Optimization failed: {e}"
            )

            return

    # ======================================================
    # RESULTS
    # ======================================================

    result = st.session_state.get(
        "loss_result"
    )

    if result is None:

        return

    st.divider()

    st.subheader(
        "🎯 Optimized Loss Correction"
    )

    parameters = result[
        "parameters"
    ]

    # ======================================================
    # OPTIMIZED PARAMETERS
    # ======================================================

    st.markdown(
        "### Optimized Parameters"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "DHI",
        parameters["DHI"],
    )

    col2.metric(
        "Starting Block",
        parameters["Starting Block"],
    )

    col3.metric(
        "Ending Block",
        parameters["Ending Block"],
    )

    col4.metric(
        "Max Block",
        parameters["Max Block"],
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "East Tracking Limit",
        parameters["East Tracking Limit"],
    )

    col2.metric(
        "West Tracking Limit",
        parameters["West Tracking Limit"],
    )

    efficiency_loss = parameters.get(
        "Efficiency Loss",
        parameters.get(
            "Efficiency Loss for Tracking",
            0,
        ),
    )

    col3.metric(
        "Efficiency Loss",
        f"{efficiency_loss:.2f}%",
    )

    # ======================================================
    # METRICS
    # ======================================================

    st.markdown(
        "### Forecast Performance"
    )

    metrics = result[
        "metrics"
    ]

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "MAE",
        f"{metrics['MAE']:.3f}",
    )

    col2.metric(
        "RMSE",
        f"{metrics['RMSE']:.3f}",
    )

    col3.metric(
        "MAPE",
        f"{metrics['MAPE']:.2f}%",
    )

    col4.metric(
        "R²",
        f"{metrics['R2']:.4f}",
    )

    # ======================================================
    # SCORE
    # ======================================================

    st.metric(
        "Combined Optimization Score",
        f"{result['score']:.6f}",
    )

    # ======================================================
    # GRAPH
    # ======================================================

    st.markdown(
        "### Actual vs Forecast"
    )

    fig = plot_loss_correction(

        blocks=blocks,

        actual=result["actual"],

        forecast=result["forecast"],

    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # ======================================================
    # WEIGHTS
    # ======================================================

    with st.expander(
        "View Effective Weights"
    ):

        weights = result[
            "weights"
        ]

        if has_cluster:

            weights_df = pd.DataFrame({

                "Cluster": [

                    f"CL{i}"

                    for i in range(
                        1,
                        len(weights) + 1
                    )

                ],

                "Effective Weight":
                    weights,

            })

        else:

            weights_df = pd.DataFrame({

                "Plant":
                    ["Total Plant"],

                "Effective Weight":
                    weights,

            })

        st.dataframe(
            weights_df,
            use_container_width=True,
            hide_index=True,
        )

    # ======================================================
    # ALL METRICS
    # ======================================================

    with st.expander(
        "View All Metrics"
    ):

        metrics_df = pd.DataFrame({

            "Metric":
                list(metrics.keys()),

            "Value":
                list(metrics.values()),

        })

        st.dataframe(
            metrics_df,
            use_container_width=True,
            hide_index=True,
        )
