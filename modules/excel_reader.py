# modules/excel_reader.py

import pandas as pd
import numpy as np


def excel_reader(uploaded_file):
    """
    Read and clean all required workbook sheets.
    """

    xls = pd.ExcelFile(uploaded_file)

    # ---------------- Area & Efficiency ----------------

    area = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=1,
        usecols=range(8)
    )

    area.columns = area.columns.astype(str).str.strip()

    if area["Module Type"].isna().any():
        area = area.loc[
            :area["Module Type"].isna().idxmax() - 1
        ]

    # ---------------- Weather ----------------

    weather = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=2,
        usecols=[12, 13, 14, 15, 16]
    )

    # ---------------- Forecast Config ----------------

    config = pd.read_excel(
        xls,
        sheet_name="Forecast Config",
        header=8
    )

    latitude = float(config.loc[0, "Lat"])

    # ---------------- Tilt ----------------

    tilt = pd.read_excel(
        xls,
        sheet_name="Config Tilt Angle",
        header=7
    )

    tilt.columns = tilt.columns.astype(str).str.strip()

    if tilt["Fixed"].isna().any():
        tilt = tilt.loc[
            :tilt["Fixed"].isna().idxmax() - 1
        ]

    tilt = tilt.dropna(axis=1, how="all")

    tilt = tilt.rename(columns={
        "Unnamed: 2": "Month_Num",
        "Unnamed: 3": "Month"
    })

    return {
        "area": area,
        "weather": weather,
        "tilt": tilt,
        "latitude": latitude
    }


# ==========================================================
# LOSS CORRECTION INPUT READER
# ==========================================================

def read_loss_correction_input(uploaded_file):
    """
    Read Loss Correction input.

    Excel:
        GHI_Forecast -> Fixed sheet
        Actual       -> workbook sheet containing Actual

    CSV:
        GHI_Forecast and Actual must exist.

    Returns:
        DataFrame with exactly:
        GHI_Forecast
        Actual
    """

    filename = uploaded_file.name.lower()

    # ======================================================
    # CSV
    # ======================================================

    if filename.endswith(".csv"):

        df = pd.read_csv(uploaded_file)

        df.columns = (
            df.columns
            .astype(str)
            .str.strip()
            .str.replace("\n", " ", regex=False)
        )

        required = [
            "GHI_Forecast",
            "Actual"
        ]

        missing = [
            col
            for col in required
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                "Missing required column(s): "
                + ", ".join(missing)
            )

        df = df[required].copy()

    # ======================================================
    # EXCEL
    # ======================================================

    elif filename.endswith((".xlsx", ".xls")):

        xls = pd.ExcelFile(uploaded_file)

        # --------------------------------------------------
        # Fixed sheet
        # --------------------------------------------------

        if "Fixed" not in xls.sheet_names:
            raise ValueError(
                "Excel file must contain a 'Fixed' sheet."
            )

        fixed = pd.read_excel(
            xls,
            sheet_name="Fixed"
        )

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

        if "GHI_Forecast" not in fixed.columns:
            raise ValueError(
                "'GHI_Forecast' column not found "
                "in 'Fixed' sheet."
            )

        ghi_forecast = fixed["GHI_Forecast"].copy()

        # --------------------------------------------------
        # Find Actual
        # --------------------------------------------------

        actual = None

        for sheet_name in xls.sheet_names:

            sheet = pd.read_excel(
                xls,
                sheet_name=sheet_name
            )

            sheet.columns = (
                sheet.columns
                .astype(str)
                .str.strip()
                .str.replace(
                    "\n",
                    " ",
                    regex=False
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
            "Actual": actual
        })

    else:

        raise ValueError(
            "Unsupported file format. "
            "Upload CSV or Excel."
        )

    # ======================================================
    # CLEAN
    # ======================================================

    for column in ["GHI_Forecast", "Actual"]:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    df = df.fillna(0)

    df["GHI_Forecast"] = np.maximum(
        df["GHI_Forecast"],
        0
    )

    df["Actual"] = np.maximum(
        df["Actual"],
        0
    )

    # ======================================================
    # VALIDATE 96 BLOCKS
    # ======================================================

    if len(df) != 96:
        raise ValueError(
            f"Loss Correction requires exactly "
            f"96 blocks. Found {len(df)}."
        )

    return df.reset_index(drop=True)
