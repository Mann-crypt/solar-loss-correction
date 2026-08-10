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
    """
    Find a column using multiple possible names.
    """

    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for name in possible_names:

        key = (
            str(name)
            .strip()
            .lower()
        )

        if key in normalized:

            return normalized[key]

    return None


# ==========================================================
# FIND ACTUAL
# ==========================================================

def extract_actual(data):
    """
    Extract Actual generation from Tracking/Backend sheet.
    """

    tracking = data["tracking"]

    backend = data["backend"]

    # ------------------------------------------------------
    # Try Tracking sheet
    # ------------------------------------------------------

    col = find_column(
        tracking,
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

    if col is not None:

        actual = pd.to_numeric(
            tracking[col],
            errors="coerce",
        ).fillna(0)

        return actual.to_numpy(
            dtype=float
        )

    # ------------------------------------------------------
    # Try Backend Cal
    # ------------------------------------------------------

    col = find_column(
        backend,
        [
            "Actual",
            "Actual Power",
            "Actual Power (MW)",
            "Power",
            "Power (MW)",
            "Generation",
        ],
    )

    if col is not None:

        actual = pd.to_numeric(
            backend[col],
            errors="coerce",
        ).fillna(0)

        return actual.to_numpy(
            dtype=float
        )

    raise ValueError(
        "Could not find Actual generation column "
        "in Tracking or Backend Cal sheet."
    )


# ==========================================================
# EXTRACT CLUSTER GHI
# ==========================================================

def extract_ghi_arrays(data):
    """
    Extract CL1-GHI ... CL5-GHI arrays.
    """

    area_weights = data["area_weights"]

    possible_clusters = [

        [
            "CL1-GHI",
            "CL1 GHI",
            "CL1_GHI",
        ],

        [
            "CL2-GHI",
            "CL2 GHI",
            "CL2_GHI",
        ],

        [
            "CL3-GHI",
            "CL3 GHI",
            "CL3_GHI",
        ],

        [
            "CL4-GHI",
            "CL4 GHI",
            "CL4_GHI",
        ],

        [
            "CL5-GHI",
            "CL5 GHI",
            "CL5_GHI",
        ],
    ]

    ghi_arrays = []

    for names in possible_clusters:

        col = find_column(
            area_weights,
            names,
        )

        if col is None:
            continue

        ghi = pd.to_numeric(
            area_weights[col],
            errors="coerce",
        ).fillna(0)

        ghi_arrays.append(
            ghi.to_numpy(
                dtype=float
            )
        )

    # ------------------------------------------------------
    # Make sure we have GHI arrays
    # ------------------------------------------------------

    if len(ghi_arrays) == 0:

        raise ValueError(
            "No CL1-GHI ... CL5-GHI columns "
            "were found."
        )

    return ghi_arrays


# ==========================================================
# EXTRACT WEIGHT FACTORS
# ==========================================================

def extract_weight_factors(data, number_of_clusters):
    """
    Extract cluster weighting factors.

    If explicit cluster weights are available,
    use them.

    Otherwise use equal weighting.
    """

    area_weights = data["area_weights"]

    possible_names = [

        "Weight",

        "Weights",

        "Weight Factor",

        "Weight Factor (%)",

        "Cluster Weight",

        "Cluster Weight (%)",

    ]

    weight_col = find_column(
        area_weights,
        possible_names,
    )

    if weight_col is not None:

        values = pd.to_numeric(
            area_weights[weight_col],
            errors="coerce",
        ).dropna()

        if len(values) >= number_of_clusters:

            values = (
                values
                .iloc[:number_of_clusters]
                .to_numpy(dtype=float)
            )

            # --------------------------------------------------
            # Convert percentages to fractions
            # --------------------------------------------------

            if np.nanmax(
                np.abs(values)
            ) > 1:

                values = values / 100.0

            return values

    # ------------------------------------------------------
    # Fallback
    # ------------------------------------------------------

    return np.ones(
        number_of_clusters,
        dtype=float,
    ) / number_of_clusters


# ==========================================================
# CLEAN ARRAY
# ==========================================================

def prepare_array(
    values,
    length=96,
):
    """
    Convert input to exactly 96 blocks.
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
            f"Expected at least {length} values, "
            f"found {len(values)}."
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
            "Backend Cal and Tracking sheets."
        )

        return

    # ======================================================
    # FILE DETECTION
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
    # EXTRACT INPUTS
    # ======================================================

    try:

        actual = extract_actual(
            data
        )

        ghi_arrays = extract_ghi_arrays(
            data
        )

        actual = prepare_array(
            actual
        )

        ghi_arrays = [

            prepare_array(
                ghi
            )

            for ghi in ghi_arrays

        ]

    except Exception as e:

        st.error(
            f"Unable to extract tracking data: {e}"
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
        "GHI Clusters",
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

        for i, ghi in enumerate(
            ghi_arrays,
            start=1,
        ):

            input_df[
                f"CL{i}-GHI"
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
    # PARAMETER BOUNDS
    # ======================================================

    st.subheader(
        "Parameter Bounds"
    )

    st.caption(
        "These are the search ranges used by "
        "Differential Evolution."
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

            result = optimize_tracking_parameters(

                actual=actual,

                ghi_arrays=ghi_arrays,

                blocks=blocks,

                area_df=area_df,

                weight_factors=weight_factors,

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

            # ==================================================
            # METRICS
            # ==================================================

            metrics = calculate_all_metrics(

                actual,

                final_forecast,

            )

            # ==================================================
            # SAVE
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
        parameters[
            "East Tracking Limit"
        ],
    )

    col2.metric(
        "West Tracking Limit",
        parameters[
            "West Tracking Limit"
        ],
    )

    col3.metric(
        "Efficiency Loss for Tracking",
        f"{parameters['Efficiency Loss for Tracking']:.2f}%",
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
        "View Effective Cluster Weights"
    ):

        weights_df = pd.DataFrame({

            "Cluster": [

                f"CL{i}"

                for i in range(
                    1,
                    len(
                        result["weights"]
                    ) + 1
                )

            ],

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
                metrics.keys(),

            "Value":
                metrics.values(),

        })

        st.dataframe(
            metrics_df,
            use_container_width=True,
            hide_index=True,
        )
