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

def read_tracking_input(uploaded_file):
    """
    Read all inputs required for Tracking Loss Correction.

    Supports two workbook structures:

    1. Cluster plant
       - CL1-GHI
       - CL2-GHI
       - CL3-GHI
       - CL4-GHI
       - CL5-GHI

    2. Non-cluster plant
       - Normal GHI Forecast from Fixed sheet

    Returns
    -------
    dict
        area
        cluster_data
        has_cluster
        latitude
        backend
        tracking
        ghi_arrays
        area_weights
    """

    xls = pd.ExcelFile(uploaded_file)

    # ==========================================================
    # AREA & EFFICIENCY
    # ==========================================================

    area = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=1,
        usecols=range(8)
    )

    area.columns = (
        area.columns
        .astype(str)
        .str.strip()
    )

    # Remove rows after first empty Module Type
    if "Module Type" in area.columns:

        null_indices = area[
            area["Module Type"].isna()
        ].index

        if len(null_indices) > 0:

            area = area.iloc[
                :area.index.get_loc(
                    null_indices[0]
                )
            ].copy()

    # ==========================================================
    # READ COMPLETE AREA & EFFICIENCY SHEET
    # ==========================================================

    area_eff_full = pd.read_excel(
        xls,
        sheet_name="Area & Efficiency",
        header=2
    )

    area_eff_full.columns = (
        area_eff_full.columns
        .astype(str)
        .str.strip()
    )

    # ==========================================================
    # CLUSTER DETECTION
    # ==========================================================

    expected_cluster_columns = [
        "CL1-GHI",
        "CL2-GHI",
        "CL3-GHI",
        "CL4-GHI",
        "CL5-GHI",
    ]

    cluster_columns_found = [
        col
        for col in expected_cluster_columns
        if col in area_eff_full.columns
    ]

    # ----------------------------------------------------------
    # Cluster plant
    # ----------------------------------------------------------

    has_cluster = (
        len(cluster_columns_found) == 5
    )

    cluster_data = None

    if has_cluster:

        cluster_data = (
            area_eff_full[
                expected_cluster_columns
            ]
            .copy()
        )

        # Convert to numeric
        for col in expected_cluster_columns:

            cluster_data[col] = pd.to_numeric(
                cluster_data[col],
                errors="coerce"
            ).fillna(0)

        # Make sure we only use 96 blocks
        cluster_data = (
            cluster_data
            .iloc[:96]
            .reset_index(drop=True)
        )

        # ------------------------------------------------------
        # GHI arrays for calculation
        # ------------------------------------------------------

        ghi_arrays = [
            cluster_data[col]
            .to_numpy(dtype=float)
            for col in expected_cluster_columns
        ]

    # ==========================================================
    # NON-CLUSTER PLANT
    # ==========================================================

    else:

        # ------------------------------------------------------
        # Read Fixed sheet
        # ------------------------------------------------------

        if "Fixed" not in xls.sheet_names:

            raise ValueError(
                "Non-cluster workbook must contain "
                "a 'Fixed' sheet."
            )

        fixed = pd.read_excel(
            xls,
            sheet_name="Fixed",
            header=1
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

        # ------------------------------------------------------
        # Find GHI column
        # ------------------------------------------------------

        possible_ghi_columns = [
            "GHI_Forecast",
            "GHI Forecast",
            "GHI",
            "GHI_Forecast_15min",
        ]

        ghi_column = None

        for col in possible_ghi_columns:

            if col in fixed.columns:

                ghi_column = col
                break

        if ghi_column is None:

            raise ValueError(
                "Non-cluster workbook does not contain "
                "a GHI forecast column in the Fixed sheet."
            )

        ghi = pd.to_numeric(
            fixed[ghi_column],
            errors="coerce"
        ).fillna(0)

        ghi = np.maximum(
            ghi.to_numpy(dtype=float),
            0
        )

        if len(ghi) < 96:

            raise ValueError(
                f"Expected at least 96 GHI blocks. "
                f"Found {len(ghi)}."
            )

        ghi = ghi[:96]

        # ------------------------------------------------------
        # Keep same structure as cluster case
        # ------------------------------------------------------

        cluster_data = None

        ghi_arrays = [
            ghi
        ]

    # ==========================================================
    # CLUSTER WEIGHT DATA
    # ==========================================================

    area_weights = None

    if has_cluster:

        # Only try usecols when the sheet actually has
        # the required cluster columns.

        cluster_weight_columns = [
            col
            for col in area_eff_full.columns
            if "CL" in col.upper()
        ]

        area_weights = (
            area_eff_full[
                cluster_weight_columns
            ]
            .copy()
        )

    # ==========================================================
    # FORECAST CONFIGURATION
    # ==========================================================

    forecast_config = pd.read_excel(
        xls,
        sheet_name="Forecast Config",
        header=8
    )

    forecast_config.columns = (
        forecast_config.columns
        .astype(str)
        .str.strip()
    )

    if "Lat" not in forecast_config.columns:

        raise ValueError(
            "Latitude column 'Lat' not found "
            "in Forecast Config."
        )

    latitude = float(
        forecast_config.loc[0, "Lat"]
    )

    # ==========================================================
    # BACKEND CALCULATION
    # ==========================================================

    if "Backend Cal" in xls.sheet_names:

        backend = pd.read_excel(
            xls,
            sheet_name="Backend Cal"
        )

    else:

        backend = None

    # ==========================================================
    # TRACKING
    # ==========================================================

    if "Tracking" in xls.sheet_names:

        tracking = pd.read_excel(
            xls,
            sheet_name="Tracking",
            header=1
        )

    else:

        tracking = None

    # ==========================================================
    # RETURN
    # ==========================================================

    return {
    "area": area,
    "cluster_data": cluster_data,
    "has_cluster": has_cluster,
    "latitude": latitude,
    "backend": backend,
    "tracking": tracking,
}
