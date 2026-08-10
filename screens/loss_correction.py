# screens/loss_correction.py

import streamlit as st
import pandas as pd
import numpy as np

from modules.excel_reader import (
    read_tracking_input,
)

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
            None
        )


# ==========================================================
# COLUMN FINDER
# ==========================================================

def find_column(df, possible_names):

    if df is None:
        return None

    normalized = {
        str(col)
        .strip()
        .lower()
        .replace("\n", " ")
        .replace("_", " ")
        for col in df.columns
    }

    original_columns = list(df.columns)

    for name in possible_names:

        target = (
            str(name)
            .strip()
            .lower()
            .replace("\n", " ")
            .replace("_", " ")
        )

        for original in original_columns:

            current = (
                str(original)
                .strip()
                .lower()
                .replace("\n", " ")
                .replace("_", " ")
            )

            if current == target:
                return original

    return None


# ==========================================================
# FIND ACTUAL GENERATION
# ==========================================================

def extract_actual(data):
    """
    Extract actual plant generation.

    Priority:
        1. Tracking -> Act Power
        2. Tracking -> other possible actual columns
        3. Backend Cal -> possible actual columns

    In the current workbook the actual column is:

        Tracking -> Act Power
    """

    tracking = data.get("tracking")
    backend = data.get("backend")

    # ======================================================
    # TRACKING
    # ======================================================

    if tracking is not None:

        tracking_actual_column = find_column(
            tracking,
            [
                "Act Power",
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Power",
                "Power (MW)",
                "Generation",
                "Actual Generation",
            ]
        )

        if tracking_actual_column is not None:

            actual = pd.to_numeric(
                tracking[tracking_actual_column],
                errors="coerce"
            )

            actual = (
                actual
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0)
                .to_numpy(dtype=float)
            )

            actual = np.maximum(
                actual,
                0
            )

            return actual

    # ======================================================
    # BACKEND CAL
    # ======================================================

    if backend is not None:

        backend_actual_column = find_column(
            backend,
            [
                "Act Power",
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Power",
                "Power (MW)",
                "Generation",
                "Actual Generation",
            ]
        )

        if backend_actual_column is not None:

            actual = pd.to_numeric(
                backend[backend_actual_column],
                errors="coerce"
            )

            actual = (
                actual
                .replace([np.inf, -np.inf], np.nan)
                .fillna(0)
                .to_numpy(dtype=float)
            )

            actual = np.maximum(
                actual,
                0
            )

            return actual

    # ======================================================
    # ERROR
    # ======================================================

    tracking_columns = (
        list(tracking.columns)
        if tracking is not None
        else []
    )

    backend_columns = (
        list(backend.columns)
        if backend is not None
        else []
    )

    raise ValueError(
        "Could not find Actual generation column.\n\n"
        f"Tracking columns: {tracking_columns}\n\n"
        f"Backend Cal columns: {backend_columns}\n\n"
        "Expected the actual generation column to be "
        "'Act Power' or a similar actual-power column."
    )


# ==========================================================
# EXTRACT GHI ARRAYS
# ==========================================================

def extract_ghi_arrays(data):
    """
    Extract GHI arrays.

    Cluster plant:
        CL1-GHI
        CL2-GHI
        CL3-GHI
        CL4-GHI
        CL5-GHI

    Non-cluster plant:
        GHI from Fixed sheet.
    """

    has_cluster = data.get(
        "has_cluster",
        False
    )

    cluster_data = data.get(
        "cluster_data"
    )

    # ======================================================
    # CLUSTER
    # ======================================================

    if has_cluster:

        if cluster_data is None:
            raise ValueError(
                "Workbook is marked as cluster plant, "
                "but cluster GHI data was not found."
            )

        expected_columns = [
            "CL1-GHI",
            "CL2-GHI",
            "CL3-GHI",
            "CL4-GHI",
            "CL5-GHI",
        ]

        ghi_arrays = []

        for column in expected_columns:

            col = find_column(
                cluster_data,
                [
                    column,
                    column.replace("-", " "),
                    column.replace("-", "_"),
                ]
            )

            if col is None:

                raise ValueError(
                    f"Cluster GHI column '{column}' "
                    "was not found."
                )

            ghi = pd.to_numeric(
                cluster_data[col],
                errors="coerce"
            )

            ghi = (
                ghi
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .fillna(0)
                .to_numpy(dtype=float)
            )

            ghi = np.maximum(
                ghi,
                0
            )

            ghi_arrays.append(
                ghi
            )

        return ghi_arrays

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    fixed = data.get(
        "fixed"
    )

    if fixed is None:

        raise ValueError(
            "Non-cluster workbook does not contain "
            "the Fixed sheet data."
        )

    ghi_column = find_column(
        fixed,
        [
            "GHI_Forecast",
            "GHI Forecast",
            "GHI",
            "GHI Forecast (W/m2)",
            "GHI_Forecast_15min",
        ]
    )

    if ghi_column is None:

        raise ValueError(
            "Could not find GHI forecast column "
            "in Fixed sheet."
        )

    ghi = pd.to_numeric(
        fixed[ghi_column],
        errors="coerce"
    )

    ghi = (
        ghi
        .replace(
            [np.inf, -np.inf],
            np.nan
        )
        .fillna(0)
        .to_numpy(dtype=float)
    )

    ghi = np.maximum(
        ghi,
        0
    )

    return [
        ghi
    ]


# ==========================================================
# EXTRACT WEIGHT FACTORS
# ==========================================================

def extract_weight_factors(
    data,
    number_of_arrays
):
    """
    Get cluster weighting factors.

    If explicit weights are available,
    use them.

    Otherwise use equal weighting.

    Non-cluster:
        [1.0]
    """

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    if number_of_arrays == 1:

        return np.asarray(
            [1.0],
            dtype=float
        )

    # ======================================================
    # CLUSTER
    # ======================================================

    cluster_data = data.get(
        "cluster_data"
    )

    if cluster_data is None:

        return (
            np.ones(
                number_of_arrays,
                dtype=float
            )
            / number_of_arrays
        )

    possible_names = [
        "Weight",
        "Weights",
        "Weight Factor",
        "Weight Factor (%)",
        "Cluster Weight",
        "Cluster Weight (%)",
    ]

    weight_column = find_column(
        cluster_data,
        possible_names
    )

    if weight_column is not None:

        values = pd.to_numeric(
            cluster_data[weight_column],
            errors="coerce"
        ).dropna()

        if len(values) >= number_of_arrays:

            values = (
                values
                .iloc[:number_of_arrays]
                .to_numpy(dtype=float)
            )

            if np.nanmax(
                np.abs(values)
            ) > 1:

                values = values / 100.0

            total = values.sum()

            if total > 0:

                return values / total

    # ======================================================
    # FALLBACK
    # ======================================================

    return (
        np.ones(
            number_of_arrays,
            dtype=float
        )
        / number_of_arrays
    )


# ==========================================================
# PREPARE ARRAY
# ==========================================================

def prepare_array(
    values,
    length=96
):
    """
    Convert data to exactly 96 blocks.
    """

    values = np.asarray(
        values,
        dtype=float
    )

    values = np.nan_to_num(
        values,
        nan=0.0,
        posinf=0.0,
        neginf=0.0
    )

    values = np.maximum(
        values,
        0
    )

    if len(values) < length:

        raise ValueError(
            f"Expected at least {length} values, "
            f"but found {len(values)}."
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
            "Area & Efficiency, Forecast Config, "
            "Backend Cal, Tracking and Fixed sheets."
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
    # EXTRACT ACTUAL
    # ======================================================

    try:

        actual = extract_actual(
            data
        )

        actual = prepare_array(
            actual
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
                ghi
            )
            for ghi in ghi_arrays
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
    # AREA DATA
    # ======================================================

    area_df = data.get(
        "area"
    )

    if area_df is None:

        st.error(
            "Area & Efficiency data was not found."
        )

        return

    # ======================================================
    # CLUSTER STATUS
    # ======================================================

    has_cluster = data.get(
        "has_cluster",
        False
    )

    # ======================================================
    # WEIGHT FACTORS
    # ======================================================

    weight_factors = extract_weight_factors(
        data,
        len(ghi_arrays)
    )

    # ======================================================
    # INPUT SUMMARY
    # ======================================================

    st.subheader(
        "Input Summary"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Blocks",
        len(blocks)
    )

    col2.metric(
        "Plant Type",
        "Cluster" if has_cluster else "Non-Cluster"
    )

    col3.metric(
        "GHI Arrays",
        len(ghi_arrays)
    )

    col4.metric(
        "Actual Peak",
        f"{actual.max():.3f}"
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
                start=1
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
            hide_index=True
        )

    # ======================================================
    # OPTIMIZATION SETTINGS
    # ======================================================

    st.subheader(
        "Optimization Settings"
    )

    col1, col2, col3, col4 = st.columns(4)

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

    with col4:

        efficiency_loss = st.number_input(

            "Efficiency Loss (%)",

            min_value=0.0,

            max_value=10.0,

            value=0.0,

            step=0.1,

        )

    # ======================================================
    # PARAMETER BOUNDS
    # ======================================================

    st.subheader(
        "Parameter Bounds"
    )

    st.caption(
        "Differential Evolution searches "
        "within these ranges."
    )

    bounds = [

        (0, 10),       # DHI

        (10, 30),      # Starting Block

        (65, 80),      # Ending Block

        (47, 53),      # Max Block

        (10, 70),      # East Limit

        (10, 70),      # West Limit

    ]

    bounds_df = pd.DataFrame({

        "Parameter": [

            "DHI",

            "Starting Block",

            "Ending Block",

            "Max Block",

            "East Tracking Limit",

            "West Tracking Limit",

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
        hide_index=True
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

            # ==================================================
            # OPTIMIZE
            # ==================================================

            result = optimize_tracking_parameters(

                actual=actual,

                ghi_arrays=ghi_arrays,

                blocks=blocks,

                area_df=area_df,

                weight_factors=weight_factors,

                efficiency_loss=efficiency_loss,

                bounds=bounds,

                maxiter=maxiter,

                popsize=popsize,

                seed=seed,

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

            final_forecast = calculate_tracking_forecast(

                ghi_arrays=ghi_arrays,

                weights=result[
                    "weights"
                ],

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
                    "East Limit"
                ],

                west_limit=parameters[
                    "West Limit"
                ],

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

                "efficiency_loss":
                    efficiency_loss,

                "actual":
                    actual,

                "forecast":
                    final_forecast,

                "metrics":
                    metrics,

                "weights":
                    result[
                        "weights"
                    ],

                "score":
                    result[
                        "score"
                    ],

                "has_cluster":
                    has_cluster,

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
        parameters["DHI"]
    )

    col2.metric(
        "Starting Block",
        parameters["Starting Block"]
    )

    col3.metric(
        "Ending Block",
        parameters["Ending Block"]
    )

    col4.metric(
        "Max Block",
        parameters["Max Block"]
    )

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "East Tracking Limit",
        parameters["East Limit"]
    )

    col2.metric(
        "West Tracking Limit",
        parameters["West Limit"]
    )

    col3.metric(
        "Efficiency Loss",
        f"{result['efficiency_loss']:.2f}%"
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
        f"{metrics['MAE']:.3f}"
    )

    col2.metric(
        "RMSE",
        f"{metrics['RMSE']:.3f}"
    )

    col3.metric(
        "MAPE",
        f"{metrics['MAPE']:.2f}%"
    )

    col4.metric(
        "R²",
        f"{metrics['R2']:.4f}"
    )

    # ======================================================
    # SCORE
    # ======================================================

    st.metric(
        "Combined Optimization Score",
        f"{result['score']:.6f}"
    )

    # ======================================================
    # GRAPH
    # ======================================================

    st.markdown(
        "### Actual vs Forecast"
    )

    fig = plot_loss_correction(

        blocks=blocks,

        actual=result[
            "actual"
        ],

        forecast=result[
            "forecast"
        ],

    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ======================================================
    # WEIGHTS
    # ======================================================

    with st.expander(
        "View Effective Weights"
    ):

        if result[
            "has_cluster"
        ]:

            cluster_names = [
                f"CL{i}"
                for i in range(
                    1,
                    len(
                        result[
                            "weights"
                        ]
                    ) + 1
                )
            ]

        else:

            cluster_names = [
                "Total Plant"
            ]

        weights_df = pd.DataFrame({

            "Cluster / Plant":
                cluster_names,

            "Effective Weight":
                result[
                    "weights"
                ],

        })

        st.dataframe(
            weights_df,
            use_container_width=True,
            hide_index=True
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
            hide_index=True
        )
