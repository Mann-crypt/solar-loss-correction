import pandas as pd
import numpy as np

def excel_reader(uploaded_file):
    """
    #Read and clean all required sheets.
    #Returns a dictionary of cleaned dataframes.
    """

    xls = pd.ExcelFile(uploaded_file)

    # ---------------- Area & Efficiency ----------------

    area = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=1,
        usecols=range(8)
    )

    area.columns = area.columns.str.strip()

    if area["Module Type"].isna().any():
        area = area.loc[:area["Module Type"].isna().idxmax()-1]

    # ---------------- Weather ----------------

    weather = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=2,
        usecols=[12,13,14,15,16]
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

    tilt.columns = tilt.columns.str.strip()

    if tilt["Fixed"].isna().any():
        tilt = tilt.loc[:tilt["Fixed"].isna().idxmax()-1]

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

def read_loss_correction_input(uploaded_file):
    """
    Read GHI Forecast and Actual values
    from the Fixed sheet for Loss Correction.
    """

    xls = pd.ExcelFile(uploaded_file)

    if "Fixed" not in xls.sheet_names:
        raise ValueError(
            "Required sheet 'Fixed' not found."
        )

    df = pd.read_excel(
        xls,
        sheet_name="Fixed",
        header=1,
    )

    # Clean headers
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    required = [
        "GHI_Forecast",
        "Actual",
    ]

    missing = [
        col
        for col in required
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing column(s) in Fixed sheet: "
            f"{', '.join(missing)}"
        )

    # Keep only Loss Correction inputs
    df = df[required].copy()

    # Numeric conversion
    for col in required:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce",
        )

    # Remove completely empty rows
    df = df.dropna(
        subset=required,
        how="all",
    ).reset_index(drop=True)

    # Fill partial missing values
    df[required] = df[required].fillna(0)

    # No negative GHI / Actual
    df["GHI_Forecast"] = np.maximum(
        df["GHI_Forecast"],
        0,
    )

    df["Actual"] = np.maximum(
        df["Actual"],
        0,
    )

    # Loss Correction works on one day
    if len(df) != 96:
        raise ValueError(
            f"Loss Correction requires 96 blocks. "
            f"Found {len(df)} rows."
        )

    return df
