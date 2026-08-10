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
            None,
        )


# ==========================================================
# COLUMN FINDER
# ==========================================================

def find_column(df, possible_names):

    if df is None:
        return None

    if df.empty:
        return None

    normalized = {
        str(col)
        .strip()
        .lower()
        .replace("\n", " ")
        .replace("_", " "): col
        for col in df.columns
    }

    for name in possible_names:

        key = (
            str(name)
            .strip()
            .lower()
            .replace("\n", " ")
            .replace("_", " ")
        )

        if key in normalized:
            return normalized[key]

    return None


# ==========================================================
# PREPARE ARRAY
# ==========================================================

def prepare_array(
    values,
    length=96,
    name="Array",
):

    if values is None:
        raise ValueError(
            f"{name} data is missing."
        )

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
# EXTRACT ACTUAL GENERATION
# ==========================================================

def extract_actual(data):

    tracking = data.get("tracking")
    backend = data.get("backend")

    # ------------------------------------------------------
    # Tracking sheet
    # ------------------------------------------------------

    if tracking is not None:

        actual_col = find_column(
            tracking,
            [
                "Act Power",
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Actual Generation",
                "Generation",
                "Power",
                "Power (MW)",
            ],
        )

        if actual_col is not None:

            actual = pd.to_numeric(
                tracking[actual_col],
                errors="coerce",
            ).fillna(0)

            return prepare_array(
                actual.to_numpy(
                    dtype=float
                ),
                96,
                "Actual generation",
            )

    # ------------------------------------------------------
    # Backend Cal fallback
    # ------------------------------------------------------

    if backend is not None:

        actual_col = find_column(
            backend,
            [
                "Actual",
                "Actual Power",
                "Actual Power (MW)",
                "Act Power",
                "Actual Generation",
                "Generation",
                "Power",
                "Power (MW)",
            ],
        )

        if actual_col is not None:

            actual = pd.to_numeric(
                backend[actual_col],
                errors="coerce",
            ).fillna(0)

            return prepare_array(
                actual.to_numpy(
                    dtype=float
                ),
                96,
                "Actual generation",
            )

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
        f"Backend Cal columns: {backend_columns}"
    )


# ==========================================================
# EXTRACT GHI ARRAYS
# ==========================================================

def extract_ghi_arrays(data):

    has_cluster = data.get(
        "has_cluster",
        False,
    )

    cluster_data = data.get(
        "cluster_data"
    )

    backend = data.get(
        "backend"
    )

    # ======================================================
    # CLUSTER PLANT
    # ======================================================

    if has_cluster:

        if (
            cluster_data is None
            or cluster_data.empty
        ):

            raise ValueError(
                "Workbook is detected as a "
                "cluster plant, but cluster GHI "
                "data is missing."
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

            actual_column = find_column(
                cluster_data,
                [
                    column,
                    column.replace(
                        "-",
                        " "
                    ),
                    column.replace(
                        "-",
                        "_"
                    ),
                ],
            )

            if actual_column is None:
                raise ValueError(
                    f"Missing cluster GHI column: "
                    f"{column}"
                )

            ghi = pd.to_numeric(
                cluster_data[actual_column],
                errors="coerce",
            ).fillna(0)

            ghi_arrays.append(
                prepare_array(
                    ghi.to_numpy(
                        dtype=float
                    ),
                    96,
                    column,
                )
            )

        return ghi_arrays

    # ======================================================
    # NON-CLUSTER PLANT
    # ======================================================

    if backend is None:

        raise ValueError(
            "Non-cluster workbook does not contain "
            "Backend Cal data."
        )

    ghi_column = find_column(
        backend,
        [
            "GHI",
            "GHI Forecast",
            "GHI_Forecast",
            "GHI Forecasted",
            "Forecast GHI",
        ],
    )

    if ghi_column is None:

        raise ValueError(
            "Could not find GHI column in "
            "Backend Cal sheet.\n\n"
            f"Backend Cal columns: "
            f"{list(backend.columns)}"
        )

    ghi = pd.to_numeric(
        backend[ghi_column],
        errors="coerce",
    ).fillna(0)

    ghi = np.maximum(
        ghi.to_numpy(dtype=float),
        0,
    )

    return [
        prepare_array(
            ghi,
            96,
            "GHI",
        )
    ]


# ==========================================================
# EXTRACT WEIGHT FACTORS
# ==========================================================

def extract_weight_factors(
    data,
    number_of_arrays,
):

    # ------------------------------------------------------
    # Non-cluster
    # ------------------------------------------------------

    if not data.get(
        "has_cluster",
        False,
    ):

        return np.ones(
            number_of_arrays,
            dtype=float,
        )

    # ------------------------------------------------------
    # Cluster
    # ------------------------------------------------------

    area_weights = data.get(
        "area_weights"
    )

    if (
        area_weights is not None
        and not area_weights.empty
    ):

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
                    .to_numpy(
                        dtype=float
                    )
                )

                if np.nanmax(
                    np.abs(values)
                ) > 1:

                    values = (
                        values / 100.0
                    )

                total = values.sum()

                if total > 0:

                    return (
                        values / total
                    )

    # ------------------------------------------------------
    # Equal weighting fallback
    # ------------------------------------------------------

    return np.ones(
        number_of_arrays,
        dtype=float,
    ) / number_of_arrays


# ==========================================================
# MAIN SCREEN
# ==========================================================

def show_loss_correction():

    st.title(
        "⛅ Tracking Loss Correction"
    )

    st.caption(
        "Optimize DHI, GHI block configuration "
        "and tracking limits against actual "
        "generation."
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
            "Upload the Tracking workbook."
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

    area_df = data["area"]

    # ======================================================
    # WEIGHT FACTORS
    # ======================================================

    weight_factors = extract_weight_factors(
        data,
        len(ghi_arrays),
    )

    # ======================================================
    # PLANT TYPE
    # ======================================================

    has_cluster = data.get(
        "has_cluster",
        False,
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
        len(blocks),
    )

    col2.metric(
        "Plant Type",
        "Cluster" if has_cluster
        else "Non-Cluster",
    )

    col3.metric(
        "GHI Arrays",
        len(ghi_arrays),
    )

    col4.metric(
        "Actual Peak",
        f"{actual.max():.3f}",
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

        for i, ghi in enumerate(
            ghi_arrays,
            start=1,
        ):

            input_df[
                f"CL{i}-GHI"
                if has_cluster
                else "GHI"
            ] = ghi

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
    # EFFICIENCY LOSS
    # ======================================================

    st.subheader(
        "Efficiency Loss"
    )

    efficiency_loss = st.number_input(
        "Tracking Efficiency Loss (%)",
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
        "These are the search ranges used by "
        "Differential Evolution."
    )
    
    # ------------------------------------------------------
    # Parameter bounds
    # ------------------------------------------------------
    
    bounds = [
        (0, 10),       # DHI
        (10, 30),      # Starting Block
        (65, 80),      # Ending Block
        (47, 53),      # Max Block
        (10, 70),      # East Tracking Limit
        (10, 70),      # West Tracking Limit
        (0, 10),       # Efficiency Loss
    ]
    
    # ------------------------------------------------------
    # Parameter names
    # ------------------------------------------------------
    
    parameter_names = [
        "DHI",
        "Starting Block",
        "Ending Block",
        "Max Block",
        "East Tracking Limit",
        "West Tracking Limit",
        "Efficiency Loss",
    ]
    
    # ------------------------------------------------------
    # Create bounds table
    # ------------------------------------------------------
    
    bounds_df = pd.DataFrame(
        {
            "Parameter": parameter_names,
            "Minimum": [
                bound[0]
                for bound in bounds
            ],
            "Maximum": [
                bound[1]
                for bound in bounds
            ],
        }
    )
    
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

            # --------------------------------------------------
            # OPTIMIZATION
            # --------------------------------------------------

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

            # --------------------------------------------------
            # BEST PARAMETERS
            # --------------------------------------------------

            parameters = result[
                "parameters"
            ]

            # --------------------------------------------------
            # FINAL FORECAST
            # --------------------------------------------------

            final_forecast = (
                calculate_tracking_forecast(

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
            )

            # --------------------------------------------------
            # METRICS
            # --------------------------------------------------

            metrics = calculate_all_metrics(

                actual,

                final_forecast,

            )

            # --------------------------------------------------
            # SAVE
            # --------------------------------------------------

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
        "🎯 Optimized Tracking Loss Correction"
    )

    parameters = result[
        "parameters"
    ]

    # ======================================================
    # PARAMETERS
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
        parameters["East Limit"],
    )

    col2.metric(
        "West Tracking Limit",
        parameters["West Limit"],
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

        if has_cluster:

            labels = [
                f"CL{i}"
                for i in range(
                    1,
                    len(
                        result["weights"]
                    ) + 1
                )
            ]

        else:

            labels = [
                "Total Plant"
            ]

        weights_df = pd.DataFrame({

            "Group":
                labels,

            "Effective Weight":
                result["weights"],

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
