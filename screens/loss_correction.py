import streamlit as st
import pandas as pd
import numpy as np

from modules.validators import validate_uploaded_file
from modules.utils import generate_blocks, generate_time_blocks
from modules.metrics import calculate_all_metrics
from modules.plotting import plot_loss_correction
from modules.excel_reader import read_loss_correction_input
from modules.utils import generate_blocks, generate_time_blocks


try:
    df = read_loss_correction_input(uploaded_file)

except Exception as e:
    st.error(f"Unable to read input file: {e}")
    return

def reset_loss_correction_state():
    """
    Clear Loss Correction session state.
    """

    keys = [
        "loss_input",
        "loss_original",
        "loss_result",
        "loss_params",
    ]

    for key in keys:
        st.session_state.pop(key, None)


def show_loss_correction():

    st.title("⛅ Loss Correction")

    st.caption(
        "Upload GHI Forecast and Actual data for one day "
        "(96 × 15-minute blocks)."
    )

    # --------------------------------------------------
    # FILE UPLOAD
    # --------------------------------------------------

    uploaded_file = st.file_uploader(
        "Upload input file",
        type=["csv", "xlsx"],
        key="loss_correction_uploader",
    )

    if uploaded_file is None:
        st.info(
            "Upload a CSV or Excel file containing "
            "`GHI_Forecast` and `Actual` columns."
        )
        return

    # --------------------------------------------------
    # NEW FILE DETECTION
    # --------------------------------------------------

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

    # --------------------------------------------------
    # READ INPUT
    # --------------------------------------------------

    try:
        df = read_loss_input(uploaded_file)

    except Exception as e:
        st.error(f"Unable to read input file: {e}")
        return

    # --------------------------------------------------
    # STORE ORIGINAL DATA
    # --------------------------------------------------

    if "loss_original" not in st.session_state:
        st.session_state.loss_original = df.copy()

    # --------------------------------------------------
    # INPUT TABLE
    # --------------------------------------------------

    st.subheader("Input Data")

    st.caption(
        "You can directly edit GHI Forecast and Actual values."
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
            "Blocks": st.column_config.NumberColumn(
                "Block",
                format="%d",
            ),
            "Time-Blocks": st.column_config.TextColumn(
                "Time",
            ),
            "GHI_Forecast": st.column_config.NumberColumn(
                "GHI Forecast",
                format="%.2f",
            ),
            "Actual": st.column_config.NumberColumn(
                "Actual",
                format="%.2f",
            ),
        },
        key="loss_input_editor",
    )

    # --------------------------------------------------
    # CLEAN EDITED DATA
    # --------------------------------------------------

    edited_df["GHI_Forecast"] = pd.to_numeric(
        edited_df["GHI_Forecast"],
        errors="coerce",
    ).fillna(0)

    edited_df["Actual"] = pd.to_numeric(
        edited_df["Actual"],
        errors="coerce",
    ).fillna(0)

    edited_df["GHI_Forecast"] = np.maximum(
        edited_df["GHI_Forecast"],
        0,
    )

    edited_df["Actual"] = np.maximum(
        edited_df["Actual"],
        0,
    )

    # --------------------------------------------------
    # CHANGE DETECTION
    # --------------------------------------------------

    original = st.session_state.loss_original[
        [
            "Blocks",
            "Time-Blocks",
            "GHI_Forecast",
            "Actual",
        ]
    ].copy()

    changed = (
        edited_df[
            ["GHI_Forecast", "Actual"]
        ].reset_index(drop=True)
        !=
        original[
            ["GHI_Forecast", "Actual"]
        ].reset_index(drop=True)
    ).any(axis=1)

    if changed.any():
        st.toast(
            f"{changed.sum()} row(s) updated",
            icon="✅",
        )

    # --------------------------------------------------
    # PLANT TYPE
    # --------------------------------------------------

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

    # --------------------------------------------------
    # RUN CORRECTION
    # --------------------------------------------------

    if st.button(
        "🚀 Run Loss Correction",
        type="primary",
        use_container_width=True,
    ):

        actual = edited_df["Actual"].to_numpy(
            dtype=float
        )

        forecast = edited_df["GHI_Forecast"].to_numpy(
            dtype=float
        )

        # --------------------------------------------------
        # TEMPORARY BASELINE
        # --------------------------------------------------
        # This is intentionally simple.
        # Replace this section with the actual Fixed /
        # Tracking correction calculation.

        corrected = forecast.copy()

        metrics = calculate_all_metrics(
            actual,
            corrected,
        )

        st.session_state.loss_result = {
            "plant_type": plant_type,
            "actual": actual,
            "forecast": forecast,
            "corrected": corrected,
            "metrics": metrics,
        }

    # --------------------------------------------------
    # RESULTS
    # --------------------------------------------------

    result = st.session_state.get(
        "loss_result"
    )

    if result is None:
        return

    st.divider()

    st.subheader("Loss Correction Result")

    col1, col2, col3, col4 = st.columns(4)

    metrics = result["metrics"]

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

    # --------------------------------------------------
    # GRAPH
    # --------------------------------------------------

    fig = plot_loss_correction(
        blocks=edited_df["Blocks"],
        actual=result["actual"],
        forecast=result["forecast"],
        corrected=result["corrected"],
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    # --------------------------------------------------
    # METRICS
    # --------------------------------------------------

    with st.expander("View All Metrics"):

        metrics_df = pd.DataFrame(
            {
                "Metric": metrics.keys(),
                "Value": metrics.values(),
            }
        )

        st.dataframe(
            metrics_df,
            use_container_width=True,
            hide_index=True,
        )

def read_loss_correction_input(uploaded_file):
    """
    Read Loss Correction input data.

    Excel:
        GHI_Forecast -> Fixed sheet
        Actual       -> Actual column from workbook

    CSV:
        GHI_Forecast and Actual must exist in the CSV.

    Returns:
        DataFrame containing:
        GHI_Forecast
        Actual
    """

    # ==================================================
    # CSV
    # ==================================================

    if uploaded_file.name.lower().endswith(".csv"):

        df = pd.read_csv(uploaded_file)

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.replace("\n", " ", regex=False)
        )

        required = [
            "GHI_Forecast",
            "Actual",
        ]

        missing = [
            col for col in required
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required column(s): "
                f"{', '.join(missing)}"
            )

        return df[required].copy()

    # ==================================================
    # EXCEL
    # ==================================================

    xls = pd.ExcelFile(uploaded_file)

    if "Fixed" not in xls.sheet_names:
        raise ValueError(
            "Excel file must contain a 'Fixed' sheet."
        )

    # --------------------------------------------------
    # GHI Forecast
    # --------------------------------------------------

    fixed = pd.read_excel(
        xls,
        sheet_name="Fixed",
    )

    fixed.columns = (
        fixed.columns
        .astype(str)
        .str.strip()
        .str.replace("\n", " ", regex=False)
    )

    if "GHI_Forecast" not in fixed.columns:
        raise ValueError(
            "'GHI_Forecast' column not found "
            "in 'Fixed' sheet."
        )

    ghi_forecast = fixed["GHI_Forecast"].copy()

    # --------------------------------------------------
    # Actual
    # --------------------------------------------------

    actual = None

    for sheet_name in xls.sheet_names:

        sheet = pd.read_excel(
            xls,
            sheet_name=sheet_name,
        )

        sheet.columns = (
            sheet.columns
            .astype(str)
            .str.strip()
            .str.replace(
                "\n",
                " ",
                regex=False,
            )
        )

        if "Actual" in sheet.columns:
            actual = sheet["Actual"].copy()
            break

    if actual is None:
        raise ValueError(
            "'Actual' column not found "
            "in Excel workbook."
        )

    # --------------------------------------------------
    # Combine
    # --------------------------------------------------

    df = pd.DataFrame({
        "GHI_Forecast": ghi_forecast,
        "Actual": actual,
    })

    # --------------------------------------------------
    # Clean
    # --------------------------------------------------

    df["GHI_Forecast"] = pd.to_numeric(
        df["GHI_Forecast"],
        errors="coerce",
    )

    df["Actual"] = pd.to_numeric(
        df["Actual"],
        errors="coerce",
    )

    df = df.fillna(0)

    df["GHI_Forecast"] = np.maximum(
        df["GHI_Forecast"],
        0,
    )

    df["Actual"] = np.maximum(
        df["Actual"],
        0,
    )

    # --------------------------------------------------
    # Validate
    # --------------------------------------------------

    if len(df) != 96:
        raise ValueError(
            f"Loss Correction requires exactly "
            f"96 blocks. Found {len(df)}."
        )

    return df.reset_index(drop=True)
