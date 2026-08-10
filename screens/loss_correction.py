# screens/loss_correction.py

import streamlit as st
import pandas as pd
import numpy as np

from modules.excel_reader import (
    read_loss_correction_input
)

from modules.utils import (
    generate_blocks,
    generate_time_blocks
)

from modules.metrics import (
    calculate_all_metrics
)

from modules.plotting import (
    plot_loss_correction
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
# MAIN SCREEN
# ==========================================================

def show_loss_correction():

    st.title("⛅ Loss Correction")

    st.caption(
        "Upload GHI Forecast and Actual data "
        "for one day (96 × 15-minute blocks)."
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

    editable_df = df[
        [
            "Blocks",
            "Time-Blocks",
            "GHI_Forecast",
            "Actual",
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
    # RUN CORRECTION
    # ======================================================

    if st.button(
        "🚀 Run Loss Correction",
        type="primary",
        use_container_width=True,
    ):

        actual = edited_df[
            "Actual"
        ].to_numpy(dtype=float)

        forecast = edited_df[
            "GHI_Forecast"
        ].to_numpy(dtype=float)

        # --------------------------------------------------
        # TEMPORARY
        # --------------------------------------------------
        # Replace this with the actual correction pipeline.

        corrected = forecast.copy()

        metrics = calculate_all_metrics(
            actual,
            corrected
        )

        st.session_state.loss_result = {

            "plant_type": plant_type,

            "actual": actual,

            "forecast": forecast,

            "corrected": corrected,

            "metrics": metrics,
        }

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

    metrics = result["metrics"]

    # ======================================================
    # KPI CARDS
    # ======================================================

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
    # GRAPH
    # ======================================================

    fig = plot_loss_correction(

        blocks=edited_df["Blocks"],

        actual=result["actual"],

        forecast=result["forecast"],

        corrected=result["corrected"],
    )

    st.plotly_chart(
        fig,
        use_container_width=True
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
            hide_index=True
        )
