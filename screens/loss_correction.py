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

    Matching is:
        - stripped
        - case-insensitive
    """

    if df is None:
        return None

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
# FIND ACTUAL GENERATION
# ==========================================================

def extract_actual(data):
    """
    Extract Actual generation.

    Search order:

        1. Tracking
        2. Backend Cal
        3. Fixed

    Returns:
        numpy array
    """

    possible_names = [

        "Actual",

        "Actual Power",

        "Actual Power (MW)",

        "Actual Generation",

        "Actual Generation (MW)",

        "Power",

        "Power (MW)",

        "Generation",

        "Generation (MW)",

    ]

    # ======================================================
    # TRACKING
    # ======================================================

    tracking = data.get("tracking")

    if tracking is not None:

        col = find_column(
            tracking,
            possible_names,
        )

        if col is not None:

            actual = pd.to_numeric(
                tracking[col],
                errors="coerce",
            ).fillna(0)

            return actual.to_numpy(
                dtype=float
            )

    # ======================================================
    # BACKEND CAL
    # ======================================================

    backend = data.get("backend")

    if backend is not None:

        col = find_column(
            backend,
            possible_names,
        )

        if col is not None:

            actual = pd.to_numeric(
                backend[col],
                errors="coerce",
            ).fillna(0)

            return actual.to_numpy(
                dtype=float
            )

    # ======================================================
    # FIXED
    # ======================================================

    xls = data.get("xls")

    if xls is not None:

        if "Fixed" in xls.sheet_names:

            fixed = pd.read_excel(
                xls,
                sheet_name="Fixed",
                header=1,
            )

            fixed.columns = (
                fixed.columns
                .astype(str)
                .str.strip()
                .str.replace(
                    "\n",
                    " ",
                    regex=False,
                )
            )

            col = find_column(
                fixed,
                possible_names,
            )

            if col is not None:

                actual = pd.to_numeric(
                    fixed[col],
                    errors="coerce",
                ).fillna(0)

                return actual.to_numpy(
                    dtype=float
                )

    raise ValueError(
        "Could not find Actual generation column. "
        "Checked Tracking, Backend Cal and Fixed sheets."
    )


# ==========================================================
# EXTRACT GHI ARRAYS
# ==========================================================

def extract_ghi_arrays(data):
    """
    Extract GHI arrays from read_tracking_input().

    Cluster:
        CL1-GHI ... CL5-GHI

    Non-cluster:
        Normal GHI array
    """

    # ======================================================
    # PREFERRED SOURCE
    # ======================================================

    ghi_arrays = data.get(
        "ghi_arrays"
    )

    if ghi_arrays is not None:

        if len(ghi_arrays) == 0:

            raise ValueError(
                "No GHI arrays were found."
            )

        return [
            np.asarray(
                ghi,
                dtype=float,
            )
            for ghi in ghi_arrays
        ]

    # ======================================================
    # FALLBACK
    # ======================================================

    cluster_data = data.get(
        "cluster_data"
    )

    if cluster_data is not None:

        expected_columns = [

            "CL1-GHI",
            "CL2-GHI",
            "CL3-GHI",
            "CL4-GHI",
            "CL5-GHI",

        ]

        arrays = []

        for col in expected_columns:

            if col in cluster_data.columns:

                values = pd.to_numeric(
                    cluster_data[col],
                    errors="coerce",
                ).fillna(0)

                arrays.append(
                    values.to_numpy(
                        dtype=float
                    )
                )

        if len(arrays) > 0:
            return arrays

    raise ValueError(
        "No GHI forecast arrays were found."
    )


# ==========================================================
# EXTRACT WEIGHT FACTORS
# ==========================================================

def extract_weight_factors(
    data,
    number_of_arrays,
):
    """
    Extract cluster weighting factors.

    If explicit weights are available,
    they are used.

    Otherwise equal weighting is used.
    """

    # ======================================================
    # NON-CLUSTER
    # ======================================================

    if number_of_arrays == 1:

        return np.asarray(
            [1.0],
            dtype=float,
        )

    # ======================================================
    # AREA WEIGHTS
    # ======================================================

    area_weights = data.get(
        "area_weights"
    )

    if area_weights is not None:

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

            if len(values) >= number_of_arrays:

                values = (
                    values
                    .iloc[:number_of_arrays]
                    .to_numpy(
                        dtype=float
                    )
                )

                # Convert percentage to fraction
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

    # ======================================================
    # EQUAL WEIGHT
    # ======================================================

    return np.ones(
        number_of_arrays,
        dtype=float,
    ) / number_of_arrays


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
            "the required Tracking Loss Correction data."
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
    # PLANT TYPE
    # ======================================================

    has_cluster = bool(
        data.get(
            "has_cluster",
            False,
        )
    )

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

        len(
            ghi_arrays
        ),

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
        "Cluster" if has_cluster
        else "Non-Cluster",
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

            cluster_names = [
                "CL1-GHI",
                "CL2-GHI",
                "CL3-GHI",
                "CL4-GHI",
                "CL5-GHI",
            ]

        else:

            cluster_names = [
                "GHI Forecast"
            ]

        for i, ghi in enumerate(
            ghi_arrays
        ):

            input_df[
                cluster_names[i]
            ] = ghi

        st.dataframe(

            input_df,

            use_container_width=True,

            hide_index=True,

        )

    # ======================================================
    # WEIGHT FACTORS
    # ======================================================

    with st.expander(
        "View GHI Weight Factors"
    ):

        weight_df = pd.DataFrame({

            "GHI Array":

                cluster_names[:len(
                    ghi_arrays
                )],

            "Weight Factor":

                weight_factors,

        })

        st.dataframe(

            weight_df,

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

            # ==============================================
            # OPTIMIZATION
            # ==============================================

            result = optimize_tracking_parameters(

                actual=actual,

                ghi_arrays=ghi_arrays,

                blocks=blocks,

                area_df=area_df,

                weight_factors=weight_factors,

                has_cluster=has_cluster,

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

            # ==============================================
            # BEST PARAMETERS
            # ==============================================

            parameters = result[
                "parameters"
            ]

            # ==============================================
            # FINAL FORECAST
            # ==============================================

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
                        "East Tracking Limit"
                    ],

                    west_limit=parameters[
                        "West Tracking Limit"
                    ],

                )
            )

            # ==============================================
            # METRICS
            # ==============================================

            metrics = calculate_all_metrics(

                actual,

                final_forecast,

            )

            # ==============================================
            # SAVE RESULT
            # ==============================================

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

            progress.progress(
                0
            )

            status.error(
                "Optimization failed."
            )

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
        "Efficiency Loss",
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
    # EFFECTIVE WEIGHTS
    # ======================================================

    with st.expander(
        "View Effective Weights"
    ):

        if has_cluster:

            weight_names = [

                f"CL{i}"

                for i in range(
                    1,
                    len(
                        result["weights"]
                    ) + 1
                )

            ]

        else:

            weight_names = [
                "Total Plant"
            ]

        weights_df = pd.DataFrame({

            "Source":
                weight_names,

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
