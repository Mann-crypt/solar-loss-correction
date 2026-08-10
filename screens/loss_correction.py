# screens/loss_correction.py

import streamlit as st
import pandas as pd
import numpy as np

from modules.excel_reader import (
    read_loss_correction_input,
)

from modules.metrics import (
    calculate_all_metrics,
)

from modules.plotting import (
    plot_loss_correction,
)

from modules.calculations import (
    calculate_declination_angle,
    calculate_elevation_angle,
    calculate_poa,
    calculate_projection,
    calculate_rt_forecast,
    calculate_symmetry,
    find_best_shift,
)


# ==========================================================
# SESSION STATE
# ==========================================================

def reset_loss_correction_state():

    keys = [
        "loss_input",
        "loss_original",
        "loss_result",
        "loss_file_signature",
    ]

    for key in keys:
        st.session_state.pop(key, None)


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def clean_input_data(df):

    df = df.copy()

    numeric_columns = [
        "GHI_Forecast",
        "Actual",
    ]

    for col in numeric_columns:

        if col in df.columns:

            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)

            df[col] = np.maximum(
                df[col],
                0
            )

    return df


def calculate_basic_parameters(df):

    """
    Calculate parameters that are already available
    from the current calculations.py.

    Additional parameters such as DHI, starting block,
    ending block and max block can be added here once
    their calculation functions are available.
    """

    actual = df["Actual"].to_numpy(dtype=float)

    forecast = df["GHI_Forecast"].to_numpy(dtype=float)

    blocks = df["Blocks"].to_numpy(dtype=float)

    # ------------------------------------------------------
    # Peak
    # ------------------------------------------------------

    peak = float(np.max(actual))

    # ------------------------------------------------------
    # Maximum block
    # ------------------------------------------------------

    max_block_index = int(
        np.argmax(actual)
    )

    max_block = int(
        blocks[max_block_index]
    )

    # ------------------------------------------------------
    # Starting / ending daylight blocks
    # ------------------------------------------------------

    daylight_mask = actual > 0

    daylight_blocks = blocks[daylight_mask]

    if len(daylight_blocks) > 0:

        starting_block = int(
            daylight_blocks[0]
        )

        ending_block = int(
            daylight_blocks[-1]
        )

    else:

        starting_block = 0
        ending_block = 0

    return {
        "peak": peak,
        "starting_block": starting_block,
        "ending_block": ending_block,
        "max_block": max_block,
    }


# ==========================================================
# MAIN SCREEN
# ==========================================================

def show_loss_correction():

    st.title("⛅ Loss Correction")

    st.caption(
        "Upload GHI Forecast and Actual data "
        "for one day using 96 × 15-minute blocks."
    )

    # ======================================================
    # FILE UPLOAD
    # ======================================================

    uploaded_file = st.file_uploader(
        "Upload input file",
        type=["csv", "xlsx"],
        key="loss_correction_uploader",
    )

    if uploaded_file is None:

        st.info(
            "Upload a CSV or Excel file containing "
            "`GHI_Forecast` and `Actual` data."
        )

        return

    # ======================================================
    # NEW FILE DETECTION
    # ======================================================

    file_signature = (
        uploaded_file.name,
        uploaded_file.size,
    )

    if (
        st.session_state.get("loss_file_signature")
        != file_signature
    ):

        reset_loss_correction_state()

        st.session_state.loss_file_signature = (
            file_signature
        )

    # ======================================================
    # READ INPUT
    # ======================================================

    try:

        df = read_loss_correction_input(
            uploaded_file
        )

    except Exception as e:

        st.error(
            f"Unable to read input file: {e}"
        )

        return

    # ======================================================
    # VALIDATE INPUT
    # ======================================================

    required_columns = [
        "GHI_Forecast",
        "Actual",
    ]

    missing_columns = [
        col
        for col in required_columns
        if col not in df.columns
    ]

    if missing_columns:

        st.error(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

        return

    # ======================================================
    # CLEAN INPUT
    # ======================================================

    df = clean_input_data(df)

    # ======================================================
    # STORE ORIGINAL
    # ======================================================

    if "loss_original" not in st.session_state:

        st.session_state.loss_original = (
            df.copy()
        )

    # ======================================================
    # INPUT DATA
    # ======================================================

    st.subheader("Input Data")

    st.caption(
        "You can directly edit GHI Forecast "
        "and Actual values."
    )

    # ------------------------------------------------------
    # Make sure Blocks exists
    # ------------------------------------------------------

    if "Blocks" not in df.columns:

        df["Blocks"] = np.arange(
            1,
            len(df) + 1
        )

    # ------------------------------------------------------
    # Make sure Time-Blocks exists
    # ------------------------------------------------------

    if "Time-Blocks" not in df.columns:

        df["Time-Blocks"] = [
            f"{(i // 4):02d}:{(i % 4) * 15:02d}"
            for i in range(len(df))
        ]

    editable_columns = [
        "Blocks",
        "Time-Blocks",
        "GHI_Forecast",
        "Actual",
    ]

    editable_df = df[
        [
            col
            for col in editable_columns
            if col in df.columns
        ]
    ].copy()

    edited_df = st.data_editor(
        editable_df,

        use_container_width=True,

        hide_index=True,

        num_rows="fixed",

        disabled=[
            "Blocks",
            "Time-Blocks",
        ],

        column_config={

            "Blocks":
                st.column_config.NumberColumn(
                    "Block",
                    format="%d"
                ),

            "Time-Blocks":
                st.column_config.TextColumn(
                    "Time"
                ),

            "GHI_Forecast":
                st.column_config.NumberColumn(
                    "GHI Forecast",
                    format="%.2f"
                ),

            "Actual":
                st.column_config.NumberColumn(
                    "Actual",
                    format="%.2f"
                ),
        },

        key="loss_input_editor",
    )

    # ======================================================
    # CLEAN EDITED VALUES
    # ======================================================

    edited_df["GHI_Forecast"] = pd.to_numeric(
        edited_df["GHI_Forecast"],
        errors="coerce"
    ).fillna(0)

    edited_df["Actual"] = pd.to_numeric(
        edited_df["Actual"],
        errors="coerce"
    ).fillna(0)

    edited_df["GHI_Forecast"] = np.maximum(
        edited_df["GHI_Forecast"],
        0
    )

    edited_df["Actual"] = np.maximum(
        edited_df["Actual"],
        0
    )

    # ======================================================
    # PLANT TYPE
    # ======================================================

    st.subheader("Plant Type")

    plant_type = st.segmented_control(
        "Select plant type",

        options=[
            "Fixed",
            "Tracking",
        ],

        default="Fixed",

        key="loss_plant_type",
    )

    # ======================================================
    # OPTIONAL INPUT PARAMETERS
    # ======================================================

    st.subheader("Correction Parameters")

    col1, col2, col3 = st.columns(3)

    with col1:

        latitude = st.number_input(
            "Latitude",
            value=28.60,
            format="%.4f",
            key="loss_latitude",
        )

    with col2:

        tilt_angle = st.number_input(
            "Tilt Angle",
            value=0.0,
            format="%.2f",
            key="loss_tilt_angle",
        )

    with col3:

        correction_weight = st.slider(
            "RT Weight",
            min_value=0.0,
            max_value=1.0,
            value=0.30,
            step=0.01,
            key="loss_rt_weight",
        )

    # ======================================================
    # RUN CORRECTION
    # ======================================================

    if st.button(
        "🚀 Run Loss Correction",
        type="primary",
        use_container_width=True,
    ):

        try:

            # ------------------------------------------------
            # INPUT ARRAYS
            # ------------------------------------------------

            actual = edited_df[
                "Actual"
            ].to_numpy(dtype=float)

            forecast = edited_df[
                "GHI_Forecast"
            ].to_numpy(dtype=float)

            blocks = edited_df[
                "Blocks"
            ].to_numpy(dtype=float)

            # ------------------------------------------------
            # BASIC PARAMETERS
            # ------------------------------------------------

            parameters = calculate_basic_parameters(
                edited_df
            )

            peak = parameters["peak"]

            starting_block = parameters[
                "starting_block"
            ]

            ending_block = parameters[
                "ending_block"
            ]

            max_block = parameters[
                "max_block"
            ]

            # ------------------------------------------------
            # SOLAR DECLINATION
            # ------------------------------------------------

            date = pd.Timestamp.today()

            declination = calculate_declination_angle(
                date
            )

            # ------------------------------------------------
            # SOLAR ELEVATION
            # ------------------------------------------------

            elevation = calculate_elevation_angle(
                latitude,
                declination
            )

            # ------------------------------------------------
            # POA
            # ------------------------------------------------

            # Avoid division by zero
            if elevation != 0:

                poa = calculate_poa(
                    forecast,
                    elevation,
                    tilt_angle,
                )

            else:

                poa = forecast.copy()

            # ------------------------------------------------
            # RT PARAMETERS
            # ------------------------------------------------

            # Use max block as the default RT pivot.
            b = max_block

            n1 = starting_block
            n2 = ending_block

            # ------------------------------------------------
            # RT PROJECTION
            # ------------------------------------------------

            projection = calculate_projection(
                blocks=blocks,
                peak=peak,
                n1=n1,
                n2=n2,
                b=b,
            )

            # ------------------------------------------------
            # RT FORECAST
            # ------------------------------------------------

            corrected = calculate_rt_forecast(
                projection=projection,
                trend=forecast,
                blocks=blocks,
                b=b,
                weight=correction_weight,
            )

            # ------------------------------------------------
            # AM SYMMETRY
            # ------------------------------------------------

            best_shift = find_best_shift(
                corrected
            )

            symmetry = calculate_symmetry(
                corrected,
                best_shift,
            )

            # ------------------------------------------------
            # METRICS
            # ------------------------------------------------

            metrics = calculate_all_metrics(
                actual,
                corrected,
            )

            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            st.session_state.loss_result = {

                "plant_type": plant_type,

                "actual": actual,

                "forecast": forecast,

                "corrected": corrected,

                "projection": projection,

                "poa": poa,

                "symmetry": symmetry,

                "metrics": metrics,

                "parameters": {

                    "Peak": peak,

                    "Starting Block":
                        starting_block,

                    "Ending Block":
                        ending_block,

                    "Max Block":
                        max_block,

                    "RT b":
                        b,

                    "RT Weight":
                        correction_weight,

                    "AM Best Shift":
                        best_shift,

                    "Declination Angle":
                        declination,

                    "Elevation Angle":
                        elevation,

                },
            }

            st.success(
                "Loss correction completed successfully."
            )

        except Exception as e:

            st.error(
                f"Loss correction failed: {e}"
            )

            st.exception(e)

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
        "Loss Correction Result"
    )

    # ======================================================
    # CALCULATED PARAMETERS
    # ======================================================

    st.subheader(
        "Calculated Parameters"
    )

    parameters = result[
        "parameters"
    ]

    parameter_columns = st.columns(4)

    parameter_items = list(
        parameters.items()
    )

    for i, (
        parameter_name,
        parameter_value
    ) in enumerate(parameter_items):

        column = parameter_columns[
            i % 4
        ]

        if isinstance(
            parameter_value,
            (float, np.floating)
        ):

            column.metric(
                parameter_name,
                f"{parameter_value:.3f}"
            )

        else:

            column.metric(
                parameter_name,
                str(parameter_value)
            )

    # ======================================================
    # DHI
    # ======================================================

    st.subheader(
        "Calculated Solar Parameters"
    )

    solar_col1, solar_col2, solar_col3 = (
        st.columns(3)
    )

    solar_col1.metric(
        "Declination",
        f"{parameters['Declination Angle']:.3f}°"
    )

    solar_col2.metric(
        "Elevation",
        f"{parameters['Elevation Angle']:.3f}°"
    )

    solar_col3.metric(
        "Plant Type",
        result["plant_type"]
    )

    # ======================================================
    # KPI CARDS
    # ======================================================

    st.subheader(
        "Performance Metrics"
    )

    metrics = result["metrics"]

    metric_items = [
        ("MAE", metrics.get("MAE")),
        ("RMSE", metrics.get("RMSE")),
        ("MAPE", metrics.get("MAPE")),
        ("R²", metrics.get("R2")),
    ]

    metric_columns = st.columns(
        len(metric_items)
    )

    for column, (
        metric_name,
        metric_value
    ) in zip(
        metric_columns,
        metric_items
    ):

        if metric_value is None:

            column.metric(
                metric_name,
                "N/A"
            )

        elif metric_name == "MAPE":

            column.metric(
                metric_name,
                f"{metric_value:.2f}%"
            )

        else:

            column.metric(
                metric_name,
                f"{metric_value:.4f}"
            )

    # ======================================================
    # FORECAST GRAPH
    # ======================================================

    st.subheader(
        "Forecast Comparison"
    )

    fig = plot_loss_correction(

        blocks=edited_df[
            "Blocks"
        ],

        actual=result[
            "actual"
        ],

        forecast=result[
            "forecast"
        ],

        corrected=result[
            "corrected"
        ],
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ======================================================
    # CORRECTION DATA
    # ======================================================

    with st.expander(
        "View Correction Data"
    ):

        result_df = pd.DataFrame({

            "Blocks":
                edited_df["Blocks"],

            "Time":
                edited_df["Time-Blocks"],

            "GHI Forecast":
                result["forecast"],

            "RT Projection":
                result["projection"],

            "Corrected Forecast":
                result["corrected"],

            "Actual":
                result["actual"],

            "AM Symmetry":
                result["symmetry"],
        })

        st.dataframe(
            result_df,
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
