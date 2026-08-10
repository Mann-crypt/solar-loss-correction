# modules/excel_reader.py

import pandas as pd
import numpy as np

from modules.utils import (
    generate_blocks,
    generate_time_blocks,
)


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
        Actual       -> Fixed sheet

    CSV:
        GHI_Forecast and Actual must exist.

    Returns:
        DataFrame with:
        Blocks
        Time-Blocks
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

        required = ["GHI_Forecast", "Actual"]

        missing = [
            col for col in required
            if col not in df.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required column(s): "
                f"{', '.join(missing)}"
            )

        df = df[required].copy()

    # ==================================================
    # EXCEL
    # ==================================================

    else:

        xls = pd.ExcelFile(uploaded_file)

        if "Fixed" not in xls.sheet_names:
            raise ValueError(
                "Excel file must contain a 'Fixed' sheet."
            )

        fixed = pd.read_excel(
            xls,
            sheet_name="Fixed",
            header=1,
        )

        fixed.columns = (
            fixed.columns
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
            if col not in fixed.columns
        ]

        if missing:
            raise ValueError(
                f"Missing required column(s) in Fixed sheet: "
                f"{', '.join(missing)}"
            )

        df = fixed[required].copy()

    # ==================================================
    # CLEAN
    # ==================================================

    for col in ["GHI_Forecast", "Actual"]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    df = df.dropna(
        subset=["GHI_Forecast", "Actual"],
        how="all",
    ).reset_index(drop=True)

    df[["GHI_Forecast", "Actual"]] = (
        df[["GHI_Forecast", "Actual"]]
        .fillna(0)
    )

    df["GHI_Forecast"] = np.maximum(
        df["GHI_Forecast"],
        0,
    )

    df["Actual"] = np.maximum(
        df["Actual"],
        0,
    )

    # ==================================================
    # VALIDATE 96 BLOCKS
    # ==================================================

    if len(df) < 96:
        raise ValueError(
            f"Loss Correction requires at least 96 blocks. "
            f"Found {len(df)}."
        )

    df = df.iloc[:96].copy()

    # ==================================================
    # ADD BLOCK INFORMATION
    # ==================================================

    df.insert(
        0,
        "Blocks",
        generate_blocks(96),
    )

    df.insert(
        1,
        "Time-Blocks",
        generate_time_blocks(96),
    )

    return df.reset_index(drop=True)
