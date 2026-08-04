import pandas as pd
import numpy as np

def excel_reader(uploaded_file):
    """
    Read and clean all required sheets.
    Returns a dictionary of cleaned dataframes.
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
