# ============================================================
# PSS × FORECASTER MAPE MATRIX
# ============================================================
#
# INPUT:
#
# Time Block
# Generated Schedule (MAL)
# Submitted Schedule (MAL)
# AVC
# Green Gen-SCADA (OPC)
# Green Gen-Meter (OPC)
# SEMS (SEMS)
# 66 KV Bhulleriyan_ECM10_F1
# 66 kV Bhulleriyan_EN1
# 66 KV Bhulleriyan_ALL12.5_F1
# 66 kV Bhulleriyan_AM_F1
# 66 kV Bhulleriyan_T1
# 66 kV Bhulleriyan_MICO_F1
# 66K_XFMV_01
# 66K_XE10_01
# 66K_GC01_E10
# 66K_XCMV_01
#
# LOGIC:
#
# Time Block = Index
#
# Actual priority:
#   1. SEMS
#   2. Green Gen-Meter
#   3. Green Gen-SCADA
#
# Forecast:
#   PSS_Forecaster
#
# Example:
#
# 66 KV Bhulleriyan_ALL12.5_F1
#
# PSS        = 66 KV Bhulleriyan
# Forecaster = ALL12.5_F1
#
# PSS normalization:
#
# 66 KV Bhulleriyan
# 66 kV Bhulleriyan
# 66K
#
# are treated as the same PSS.
#
# OUTPUT:
#
# ONLY:
#
# PSS × Forecaster MAPE Matrix
#
# Low MAPE  = Green
# Medium     = Yellow
# High MAPE  = Red
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import io
import re

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="PSS × Forecaster MAPE",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CONSTANTS
# ============================================================

TIME_BLOCK_COLUMN = "Time Block"

ACTUAL_PRIORITY = [
    "SEMS",
    "Green Gen-Meter",
    "Green Gen-SCADA",
]


# ============================================================
# NORMALIZE TEXT
# ============================================================

def normalize_text(value):
    """
    General text normalization.

    Example:

    Green Gen-SCADA (OPC)
    ->
    green gen scada opc
    """

    if value is None:
        return ""

    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# NORMALIZE PSS
# ============================================================

def normalize_pss(value):
    """
    Normalize PSS names.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    become the same normalized PSS.
    """

    if value is None:
        return ""

    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Remove HTML line breaks
    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = text.lower()

    # Remove all spaces
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # Normalize KV -> K
    text = text.replace(
        "kv",
        "k",
    )

    return text.upper()


# ============================================================
# CLEAN PSS DISPLAY NAME
# ============================================================

def clean_pss_name(value):

    if value is None:
        return ""

    text = str(value).strip()

    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def to_numeric(series):

    if pd.api.types.is_numeric_dtype(
        series
    ):

        return pd.to_numeric(
            series,
            errors="coerce",
        )

    return pd.to_numeric(
        series
        .astype(str)
        .str.replace(
            ",",
            "",
            regex=False,
        )
        .str.replace(
            "%",
            "",
            regex=False,
        )
        .str.strip(),
        errors="coerce",
    )


# ============================================================
# READ FILE
# ============================================================

def read_file(uploaded_file):

    filename = uploaded_file.name.lower()

    uploaded_file.seek(0)

    if filename.endswith(".csv"):

        try:

            return pd.read_csv(
                uploaded_file
            )

        except UnicodeDecodeError:

            uploaded_file.seek(0)

            return pd.read_csv(
                uploaded_file,
                encoding="latin1",
            )

    if filename.endswith(
        (".xlsx", ".xls")
    ):

        return pd.read_excel(
            uploaded_file
        )

    raise ValueError(
        "Only CSV, XLS and XLSX files are supported."
    )


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):

    df = df.copy()

    # Remove completely empty rows
    df = df.dropna(
        axis=0,
        how="all",
    )

    # Remove completely empty columns
    df = df.dropna(
        axis=1,
        how="all",
    )

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# SET TIME BLOCK AS INDEX
# ============================================================

def set_time_block_index(df):

    df = df.copy()

    target = normalize_text(
        TIME_BLOCK_COLUMN
    )

    time_column = None

    for column in df.columns:

        if normalize_text(
            column
        ) == target:

            time_column = column

            break

    if time_column is None:

        raise ValueError(
            "Time Block column not found."
        )

    df = df.set_index(
        time_column,
        drop=True,
    )

    return df


# ============================================================
# DETECT ACTUAL COLUMN
# ============================================================

def find_actual_column(
    df,
    actual_type,
):
    """
    Detect the requested Actual source.

    Supported:

        SEMS
        Green Gen-Meter
        Green Gen-SCADA
    """

    candidates = []

    for column in df.columns:

        normalized = normalize_text(
            column
        )

        # ----------------------------------------------------
        # SEMS
        # ----------------------------------------------------

        if actual_type == "SEMS":

            if "sems" in normalized:

                candidates.append(
                    column
                )

        # ----------------------------------------------------
        # Green Gen-Meter
        # ----------------------------------------------------

        elif actual_type == "Green Gen-Meter":

            if (
                "green gen meter"
                in normalized
            ):

                candidates.append(
                    column
                )

        # ----------------------------------------------------
        # Green Gen-SCADA
        # ----------------------------------------------------

        elif actual_type == "Green Gen-SCADA":

            if (
                "green gen scada"
                in normalized
            ):

                candidates.append(
                    column
                )

    # --------------------------------------------------------
    # Choose first numeric candidate
    # --------------------------------------------------------

    for column in candidates:

        numeric = to_numeric(
            df[column]
        )

        if numeric.notna().sum() > 0:

            return column

    return None


# ============================================================
# DETECT ALL ACTUALS
# ============================================================

def detect_actuals(df):

    actuals = {}

    for actual_type in [
        "SEMS",
        "Green Gen-Meter",
        "Green Gen-SCADA",
    ]:

        actuals[
            actual_type
        ] = find_actual_column(
            df,
            actual_type,
        )

    return actuals


# ============================================================
# PARSE FORECAST HEADER
# ============================================================

def parse_forecast_header(
    column_name
):
    """
    Split forecast header ONLY at the first underscore.

    Example:

    66 KV Bhulleriyan_ALL12.5_F1

    PSS:
        66 KV Bhulleriyan

    Forecaster:
        ALL12.5_F1
    """

    text = str(
        column_name
    ).strip()

    if "_" not in text:

        return None, None

    pss, forecaster = (
        text.split(
            "_",
            1,
        )
    )

    pss = pss.strip()

    forecaster = forecaster.strip()

    if not pss:
        return None, None

    if not forecaster:
        return None, None

    return (
        pss,
        forecaster,
    )


# ============================================================
# DETECT FORECAST COLUMNS
# ============================================================

def detect_forecasts(df):

    forecasts = []

    for column in df.columns:

        pss, forecaster = (
            parse_forecast_header(
                column
            )
        )

        if pss is None:
            continue

        # ----------------------------------------------------
        # Check numeric content
        # ----------------------------------------------------

        numeric = to_numeric(
            df[column]
        )

        if numeric.notna().sum() == 0:
            continue

        forecasts.append(
            {
                "column": column,
                "pss": pss,
                "normalized_pss": normalize_pss(
                    pss
                ),
                "forecaster": forecaster,
            }
        )

    return forecasts


# ============================================================
# IDENTIFY PSS
# ============================================================

def identify_pss(
    forecasts
):
    """
    Every file contains only one PSS.

    Find the most common normalized PSS.
    """

    if not forecasts:
        return None, None

    counts = {}

    for item in forecasts:

        normalized = item[
            "normalized_pss"
        ]

        counts[
            normalized
        ] = (
            counts.get(
                normalized,
                0,
            )
            + 1
        )

    normalized_pss = max(
        counts,
        key=counts.get,
    )

    display_names = {}

    for item in forecasts:

        if (
            item[
                "normalized_pss"
            ]
            != normalized_pss
        ):
            continue

        display_name = clean_pss_name(
            item["pss"]
        )

        display_names[
            display_name
        ] = (
            display_names.get(
                display_name,
                0,
            )
            + 1
        )

    pss_name = max(
        display_names,
        key=display_names.get,
    )

    return (
        pss_name,
        normalized_pss,
    )


# ============================================================
# SELECT ACTUAL
# ============================================================

def select_actual(
    actuals,
    mode,
):
    """
    Auto Priority:

        SEMS
        Green Gen-Meter
        Green Gen-SCADA
    """

    if mode == "Auto Priority":

        for source in ACTUAL_PRIORITY:

            column = actuals.get(
                source
            )

            if column is not None:

                return (
                    source,
                    column,
                )

        return (
            None,
            None,
        )

    column = actuals.get(
        mode
    )

    if column is None:

        return (
            None,
            None,
        )

    return (
        mode,
        column,
    )


# ============================================================
# MAPE
# ============================================================

def calculate_mape(
    actual,
    forecast,
    exclude_zero=True,
    minimum_actual=0.0,
):
    """
    MAPE:

        mean(
            abs(
                (Forecast - Actual) / Actual
            )
        ) * 100
    """

    actual = to_numeric(
        actual
    )

    forecast = to_numeric(
        forecast
    )

    # --------------------------------------------------------
    # Valid values
    # --------------------------------------------------------

    mask = (
        actual.notna()
        & forecast.notna()
        & np.isfinite(actual)
        & np.isfinite(forecast)
    )

    # --------------------------------------------------------
    # Minimum actual
    # --------------------------------------------------------

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
        )

    # --------------------------------------------------------
    # Exclude zero actual
    # --------------------------------------------------------

    if exclude_zero:

        mask &= (
            actual != 0
        )

    if mask.sum() == 0:

        return np.nan

    actual_valid = actual.loc[
        mask
    ]

    forecast_valid = forecast.loc[
        mask
    ]

    percentage_error = (
        np.abs(
            (
                forecast_valid
                - actual_valid
            )
            / actual_valid
        )
        * 100
    )

    return float(
        percentage_error.mean()
    )


# ============================================================
# MAPE COLOR FUNCTION
# ============================================================

def mape_color(
    value,
    minimum,
    maximum,
):
    """
    Low MAPE  = Green
    Mid MAPE  = Yellow
    High MAPE = Red
    """

    if pd.isna(value):

        return ""

    value = float(value)

    # --------------------------------------------------------
    # All values equal
    # --------------------------------------------------------

    if maximum <= minimum:

        ratio = 0.0

    else:

        ratio = (
            value - minimum
        ) / (
            maximum - minimum
        )

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    # --------------------------------------------------------
    # GREEN -> YELLOW
    # --------------------------------------------------------

    if ratio <= 0.5:

        position = ratio * 2

        red = int(
            144
            + (
                255 - 144
            )
            * position
        )

        green = 238

        blue = int(
            144
            * (
                1 - position
            )
        )

    # --------------------------------------------------------
    # YELLOW -> RED
    # --------------------------------------------------------

    else:

        position = (
            ratio - 0.5
        ) * 2

        red = 255

        green = int(
            238
            * (
                1 - position
            )
        )

        blue = 0

    return (
        "background-color: "
        f"rgb({red}, {green}, {blue}); "
        "color: black;"
    )


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_files = st.file_uploader(
    "Upload multiple files",
    type=[
        "xlsx",
        "xls",
        "csv",
    ],
    accept_multiple_files=True,
)


# ============================================================
# NO FILE
# ============================================================

if not uploaded_files:

    st.info(
        "Upload one or more files to calculate MAPE."
    )

    st.stop()


# ============================================================
# ACTUAL SELECTION
# ============================================================

actual_mode = st.radio(
    "Select Actual Data",
    options=[
        "Auto Priority",
        "SEMS",
        "Green Gen-Meter",
        "Green Gen-SCADA",
    ],
    index=0,
    horizontal=True,
)


# ============================================================
# AUTO PRIORITY INFORMATION
# ============================================================

if actual_mode == "Auto Priority":

    st.caption(
        "Automatic priority: SEMS → Green Gen-Meter → Green Gen-SCADA"
    )


# ============================================================
# MAPE SETTINGS
# ============================================================

col1, col2 = st.columns(2)

with col1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
    )

with col2:

    minimum_actual = st.number_input(
        "Minimum Actual Value",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )


# ============================================================
# CALCULATE BUTTON
# ============================================================

run_calculation = st.button(
    "Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not run_calculation:

    st.stop()


# ============================================================
# RESULTS
# ============================================================

results = []

errors = []


# ============================================================
# PROGRESS
# ============================================================

progress = st.progress(
    0
)

status = st.empty()


# ============================================================
# PROCESS EACH FILE
# ============================================================

for file_number, uploaded_file in enumerate(
    uploaded_files
):

    status.write(
        f"Processing {uploaded_file.name}..."
    )

    try:

        # ----------------------------------------------------
        # Read
        # ----------------------------------------------------

        df = read_file(
            uploaded_file
        )

        # ----------------------------------------------------
        # Clean
        # ----------------------------------------------------

        df = clean_dataframe(
            df
        )

        if df.empty:

            raise ValueError(
                "File is empty."
            )

        # ----------------------------------------------------
        # Time Block
        # ----------------------------------------------------

        df = set_time_block_index(
            df
        )

        # ----------------------------------------------------
        # Actual detection
        # ----------------------------------------------------

        actuals = detect_actuals(
            df
        )

        # ----------------------------------------------------
        # Actual selection
        # ----------------------------------------------------

        (
            actual_source,
            actual_column,
        ) = select_actual(
            actuals,
            actual_mode,
        )

        if actual_column is None:

            if actual_mode == "Auto Priority":

                raise ValueError(
                    "No Actual column found. "
                    "Expected SEMS, Green Gen-Meter "
                    "or Green Gen-SCADA."
                )

            raise ValueError(
                f"{actual_mode} column was not found."
            )

        # ----------------------------------------------------
        # Forecast detection
        # ----------------------------------------------------

        forecasts = detect_forecasts(
            df
        )

        if not forecasts:

            raise ValueError(
                "No Forecast column detected. "
                "Forecast columns must follow "
                "PSS_Forecaster format."
            )

        # ----------------------------------------------------
        # Identify file PSS
        # ----------------------------------------------------

        (
            pss_name,
            normalized_pss,
        ) = identify_pss(
            forecasts
        )

        if pss_name is None:

            raise ValueError(
                "Unable to identify PSS."
            )

        # ----------------------------------------------------
        # Keep only forecasts belonging to this PSS
        # ----------------------------------------------------

        forecasts = [
            item
            for item in forecasts
            if item[
                "normalized_pss"
            ]
            == normalized_pss
        ]

        # ----------------------------------------------------
        # Actual data
        # ----------------------------------------------------

        actual_series = df[
            actual_column
        ]

        # ----------------------------------------------------
        # Each Forecaster
        # ----------------------------------------------------

        for forecast in forecasts:

            forecast_column = forecast[
                "column"
            ]

            forecaster = forecast[
                "forecaster"
            ]

            mape = calculate_mape(
                actual=actual_series,
                forecast=df[
                    forecast_column
                ],
                exclude_zero=exclude_zero,
                minimum_actual=minimum_actual,
            )

            results.append(
                {
                    "PSS": pss_name,
                    "Forecaster": forecaster,
                    "MAPE": mape,
                }
            )

    except Exception as error:

        errors.append(
            f"{uploaded_file.name}: {error}"
        )

    progress.progress(
        int(
            (
                file_number + 1
            )
            / len(uploaded_files)
            * 100
        )
    )


status.empty()


# ============================================================
# ERRORS
# ============================================================

if errors:

    st.warning(
        "Some files could not be processed:"
    )

    for error in errors:

        st.write(
            f"• {error}"
        )


# ============================================================
# CHECK RESULTS
# ============================================================

if not results:

    st.error(
        "No MAPE results were calculated."
    )

    st.stop()


# ============================================================
# RESULTS DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    results
)


# ============================================================
# IF SAME PSS + FORECASTER EXISTS IN MULTIPLE FILES
# ============================================================
#
# Average the MAPE values.
#
# ============================================================

result_df = (
    result_df
    .groupby(
        [
            "PSS",
            "Forecaster",
        ],
        as_index=False,
    )
    .agg(
        MAPE=(
            "MAPE",
            "mean",
        )
    )
)


# ============================================================
# CREATE MATRIX
# ============================================================

mape_matrix = (
    result_df
    .pivot(
        index="PSS",
        columns="Forecaster",
        values="MAPE",
    )
)


# ============================================================
# SORT
# ============================================================

mape_matrix = (
    mape_matrix
    .sort_index(axis=0)
    .sort_index(axis=1)
)


# ============================================================
# ROUND
# ============================================================

mape_matrix = (
    mape_matrix.round(2)
)


# ============================================================
# FIND COLOR RANGE
# ============================================================

values = (
    mape_matrix
    .to_numpy(
        dtype=float
    )
)

valid_values = values[
    np.isfinite(values)
]

if len(valid_values) > 0:

    minimum_mape = float(
        np.min(
            valid_values
        )
    )

    maximum_mape = float(
        np.max(
            valid_values
        )
    )

else:

    minimum_mape = 0.0

    maximum_mape = 1.0


# ============================================================
# STYLE MATRIX
# ============================================================
#
# IMPORTANT:
#
# Use Styler.map()
# NOT Styler.applymap()
#
# This is compatible with newer pandas versions.
#
# ============================================================

styled_matrix = (
    mape_matrix
    .style
    .format(
        "{:.2f}",
        na_rep="-",
    )
    .map(
        lambda value:
        mape_color(
            value,
            minimum_mape,
            maximum_mape,
        )
    )
)


# ============================================================
# FINAL OUTPUT
# ============================================================

st.subheader(
    "PSS × Forecaster MAPE Matrix"
)

st.dataframe(
    styled_matrix,
    use_container_width=True,
)


# ============================================================
# EXCEL DOWNLOAD
# ============================================================

excel_output = io.BytesIO()

with pd.ExcelWriter(
    excel_output,
    engine="openpyxl",
) as writer:

    mape_matrix.to_excel(
        writer,
        sheet_name="MAPE Matrix",
    )

excel_output.seek(0)


# ============================================================
# DOWNLOAD
# ============================================================

st.download_button(
    label="📥 Download MAPE Matrix",
    data=excel_output,
    file_name="PSS_Forecaster_MAPE_Matrix.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True,
)
