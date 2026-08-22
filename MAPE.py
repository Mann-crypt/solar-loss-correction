# ============================================================
# PSS × FORECASTER MAPE ANALYZER
# ============================================================
#
# INPUT STRUCTURE
#
# Time Block                                  -> INDEX
# Generated Schedule (MAL)                   -> OTHER
# Submitted Schedule (MAL)                  -> OTHER
# AVC                                         -> OTHER
# Green Gen-SCADA (OPC)                     -> ACTUAL
# Green Gen-Meter (OPC)                     -> ACTUAL
# SEMS (SEMS)                                -> ACTUAL
#
# 66 KV Bhulleriyan_ECM10_F1                -> FORECAST
# 66 kV Bhulleriyan_EN1                     -> FORECAST
# 66 KV Bhulleriyan_ALL12.5_F1              -> FORECAST
# 66 kV Bhulleriyan_AM_F1                   -> FORECAST
# 66 kV Bhulleriyan_T1                      -> FORECAST
# 66 kV Bhulleriyan_MICO_F1                 -> FORECAST
# 66K_XFMV_01                               -> FORECAST
# 66K_XE10_01                               -> FORECAST
# 66K_GC01_E10                              -> FORECAST
# 66K_XCMV_01                               -> FORECAST
#
# PSS:
#
# 66 KV Bhulleriyan
# 66 kV Bhulleriyan
# 66K
#
# are treated as the SAME PSS.
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
    page_title="PSS Forecaster MAPE",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    .stMetric {
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TITLE
# ============================================================

st.title("📊 PSS × Forecaster MAPE Analyzer")

st.caption(
    "Upload multiple files. Time Block is treated as the index, "
    "Actual columns are detected automatically, and Forecast "
    "columns are identified from their PSS_Forecaster headers."
)


# ============================================================
# CONFIGURATION
# ============================================================

INDEX_COLUMN = "Time Block"


# ------------------------------------------------------------
# Actual columns
# ------------------------------------------------------------
#
# These are the actual generation columns in your file.
# Detection is case-insensitive and ignores spacing differences.
#

ACTUAL_COLUMN_PATTERNS = [
    "green gen scada",
    "green gen meter",
    "sems",
]


# ------------------------------------------------------------
# Known non-forecast columns
# ------------------------------------------------------------

NON_FORECAST_COLUMNS = {
    "time block",
    "generated schedule mal",
    "submitted schedule mal",
    "avc",
    "green gen scada opc",
    "green gen meter opc",
    "sems sems",
}


# ============================================================
# NORMALIZE GENERAL TEXT
# ============================================================

def normalize_text(value):
    """
    General text normalization.

    Example:

        Green Gen-SCADA (OPC)

    becomes:

        green gen scada opc
    """

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
    Normalizes PSS names for comparison.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    are all treated as the same PSS.
    """

    if pd.isna(value):
        return ""

    text = str(value).strip()

    # Remove HTML breaks
    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Lowercase
    text = text.lower()

    # Remove all spaces
    compact = re.sub(
        r"\s+",
        "",
        text,
    )

    # --------------------------------------------------------
    # Normalize KV
    #
    # 66kv -> 66k
    # --------------------------------------------------------

    compact = compact.replace(
        "kv",
        "k",
    )

    # --------------------------------------------------------
    # Normalize:
    #
    # 66k
    # 66kv
    #
    # --------------------------------------------------------

    compact = re.sub(
        r"(\d+)k",
        r"\1k",
        compact,
    )

    return compact.upper()


# ============================================================
# DISPLAY PSS
# ============================================================

def display_pss(value):
    """
    Returns a clean human-readable PSS name.
    """

    if pd.isna(value):
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
    """
    Safely convert column to numeric.
    """

    if pd.api.types.is_numeric_dtype(series):

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

def read_uploaded_file(uploaded_file):

    name = uploaded_file.name.lower()

    if name.endswith(".csv"):

        uploaded_file.seek(0)

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

    if name.endswith(
        (".xlsx", ".xls")
    ):

        uploaded_file.seek(0)

        return pd.read_excel(
            uploaded_file
        )

    raise ValueError(
        "Unsupported file format."
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

    # Clean headers
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# SET TIME BLOCK AS INDEX
# ============================================================

def prepare_index(df):

    df = df.copy()

    index_column = None

    # Exact match first
    for column in df.columns:

        if normalize_text(
            column
        ) == normalize_text(
            INDEX_COLUMN
        ):

            index_column = column

            break

    if index_column is None:

        return (
            df,
            None,
        )

    # Preserve Time Block as index
    df = df.set_index(
        index_column,
        drop=True,
    )

    return (
        df,
        index_column,
    )


# ============================================================
# DETECT ACTUAL COLUMNS
# ============================================================

def detect_actual_columns(df):

    detected = []

    for column in df.columns:

        normalized = normalize_text(
            column
        )

        matched_pattern = None

        # ----------------------------------------------------
        # Exact normalized matching
        # ----------------------------------------------------

        for pattern in ACTUAL_COLUMN_PATTERNS:

            if (
                pattern
                in normalized
            ):

                matched_pattern = pattern

                break

        if matched_pattern is None:

            continue

        numeric = to_numeric(
            df[column]
        )

        numeric_rows = int(
            numeric.notna().sum()
        )

        if numeric_rows == 0:

            continue

        detected.append(
            {
                "Actual Column": column,
                "Detected As": matched_pattern,
                "Numeric Rows": numeric_rows,
            }
        )

    return pd.DataFrame(
        detected
    )


# ============================================================
# PARSE FORECAST COLUMN
# ============================================================

def parse_forecast_column(
    column_name
):
    """
    Parse forecast column.

    Example:

        66 KV Bhulleriyan_ALL12.5_F1

    returns:

        PSS        = 66 KV Bhulleriyan
        Forecaster = ALL12.5_F1

    IMPORTANT:
    Split only at the FIRST underscore.
    """

    text = str(
        column_name
    ).strip()

    if "_" not in text:

        return (
            None,
            None,
        )

    pss_part, forecaster = (
        text.split(
            "_",
            1,
        )
    )

    pss_part = pss_part.strip()

    forecaster = (
        forecaster.strip()
    )

    if (
        not pss_part
        or not forecaster
    ):

        return (
            None,
            None,
        )

    return (
        pss_part,
        forecaster,
    )


# ============================================================
# DETECT FORECAST COLUMNS
# ============================================================

def detect_forecast_columns(
    df
):
    """
    Detect Forecast columns.

    A Forecast column must:

    1. Contain "_"
    2. Have a non-empty part before "_"
    3. Have a non-empty part after "_"
    4. Contain numeric data
    5. Not be a known non-forecast column
    """

    detected = []

    for column in df.columns:

        normalized_column = (
            normalize_text(
                column
            )
        )

        # ----------------------------------------------------
        # Ignore known columns
        # ----------------------------------------------------

        if (
            normalized_column
            in NON_FORECAST_COLUMNS
        ):

            continue

        # ----------------------------------------------------
        # Parse
        # ----------------------------------------------------

        pss_part, forecaster = (
            parse_forecast_column(
                column
            )
        )

        if pss_part is None:

            continue

        # ----------------------------------------------------
        # Numeric validation
        # ----------------------------------------------------

        numeric = to_numeric(
            df[column]
        )

        numeric_rows = int(
            numeric.notna().sum()
        )

        if numeric_rows == 0:

            continue

        detected.append(
            {
                "Forecast Column": column,
                "PSS From Header": pss_part,
                "Forecaster": forecaster,
                "Numeric Rows": numeric_rows,
            }
        )

    return pd.DataFrame(
        detected
    )


# ============================================================
# IDENTIFY SINGLE PSS
# ============================================================

def identify_pss_from_forecasts(
    forecast_df
):
    """
    Since each file contains only one PSS,
    identify the PSS from the forecast headers.

    Multiple spellings such as:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    are normalized to the same PSS.

    The most frequently occurring normalized PSS
    is selected.
    """

    if forecast_df.empty:

        return (
            None,
            None,
        )

    forecast_df = forecast_df.copy()

    forecast_df[
        "Normalized PSS"
    ] = forecast_df[
        "PSS From Header"
    ].apply(
        normalize_pss
    )

    counts = (
        forecast_df[
            "Normalized PSS"
        ]
        .value_counts()
    )

    if counts.empty:

        return (
            None,
            None,
        )

    dominant_normalized = (
        counts.index[0]
    )

    matching = forecast_df[
        forecast_df[
            "Normalized PSS"
        ]
        == dominant_normalized
    ]

    display_names = (
        matching[
            "PSS From Header"
        ]
        .apply(
            display_pss
        )
        .value_counts()
    )

    display_name = (
        display_names.index[0]
    )

    return (
        display_name,
        dominant_normalized,
    )


# ============================================================
# FILTER FORECASTS TO SINGLE PSS
# ============================================================

def filter_forecasts_for_pss(
    forecast_df,
    normalized_pss,
):

    forecast_df = forecast_df.copy()

    forecast_df[
        "Normalized PSS"
    ] = forecast_df[
        "PSS From Header"
    ].apply(
        normalize_pss
    )

    return forecast_df[
        forecast_df[
            "Normalized PSS"
        ]
        == normalized_pss
    ].copy()


# ============================================================
# MAPE CALCULATION
# ============================================================

def calculate_metrics(
    actual,
    forecast,
    exclude_zero=True,
    minimum_actual=0.0,
):

    actual = to_numeric(
        actual
    )

    forecast = to_numeric(
        forecast
    )

    # --------------------------------------------------------
    # Valid data
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
    # Remove zero Actual
    # --------------------------------------------------------

    if exclude_zero:

        mask &= (
            actual != 0
        )

    # --------------------------------------------------------
    # Nothing to calculate
    # --------------------------------------------------------

    if mask.sum() == 0:

        return {
            "MAPE (%)": np.nan,
            "MAE": np.nan,
            "RMSE": np.nan,
            "Bias": np.nan,
            "Valid Rows": 0,
        }

    a = actual.loc[mask]
    f = forecast.loc[mask]

    error = (
        f - a
    )

    ape = (
        np.abs(
            error / a
        )
        * 100
    )

    mae = (
        np.abs(
            error
        ).mean()
    )

    rmse = np.sqrt(
        np.mean(
            error ** 2
        )
    )

    bias = error.mean()

    mape = ape.mean()

    return {
        "MAPE (%)": float(
            mape
        ),
        "MAE": float(
            mae
        ),
        "RMSE": float(
            rmse
        ),
        "Bias": float(
            bias
        ),
        "Valid Rows": int(
            mask.sum()
        ),
    }


# ============================================================
# ROW LEVEL APE
# ============================================================

def calculate_ape(
    actual,
    forecast,
    exclude_zero=True,
    minimum_actual=0.0,
):

    actual = to_numeric(
        actual
    )

    forecast = to_numeric(
        forecast
    )

    ape = pd.Series(
        np.nan,
        index=actual.index,
        dtype=float,
    )

    mask = (
        actual.notna()
        & forecast.notna()
        & np.isfinite(actual)
        & np.isfinite(forecast)
    )

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
        )

    if exclude_zero:

        mask &= (
            actual != 0
        )

    ape.loc[mask] = (
        np.abs(
            (
                forecast.loc[mask]
                - actual.loc[mask]
            )
            / actual.loc[mask]
        )
        * 100
    )

    return ape


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_files = st.file_uploader(
    "📂 Upload Multiple Files",
    type=[
        "xlsx",
        "xls",
        "csv",
    ],
    accept_multiple_files=True,
)


if not uploaded_files:

    st.info(
        "Upload one or more files to start."
    )

    st.stop()


# ============================================================
# SETTINGS
# ============================================================

st.subheader(
    "⚙️ MAPE Settings"
)

col1, col2 = st.columns(2)

with col1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Zero Actual values are normally night-time "
            "solar generation and are excluded from MAPE."
        ),
    )

with col2:

    minimum_actual = st.number_input(
        "Minimum Actual Value",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )


# ============================================================
# FILE LIST
# ============================================================

st.subheader(
    "📁 Uploaded Files"
)

file_info = pd.DataFrame(
    [
        {
            "File": file.name,
            "Size (KB)": round(
                file.size / 1024,
                2,
            ),
        }
        for file in uploaded_files
    ]
)

st.dataframe(
    file_info,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# CALCULATE BUTTON
# ============================================================

calculate_button = st.button(
    "🚀 Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not calculate_button:

    st.info(
        "Click Calculate MAPE to process the uploaded files."
    )

    st.stop()


# ============================================================
# RESULT STORAGE
# ============================================================

mape_results = []

row_level_results = []

file_detection_results = []

forecast_detection_results = []

actual_detection_results = []

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

        # ====================================================
        # READ
        # ====================================================

        df = read_uploaded_file(
            uploaded_file
        )

        df = clean_dataframe(
            df
        )

        if df.empty:

            raise ValueError(
                "File contains no usable data."
            )

        # ====================================================
        # SET TIME BLOCK AS INDEX
        # ====================================================

        df, index_column = (
            prepare_index(
                df
            )
        )

        # ====================================================
        # ACTUAL DETECTION
        # ====================================================

        actual_df = (
            detect_actual_columns(
                df
            )
        )

        if actual_df.empty:

            raise ValueError(
                "No Actual columns detected. "
                "Expected columns similar to "
                "'Green Gen-SCADA (OPC)', "
                "'Green Gen-Meter (OPC)', "
                "or 'SEMS (SEMS)'."
            )

        # ====================================================
        # FORECAST DETECTION
        # ====================================================

        forecast_df = (
            detect_forecast_columns(
                df
            )
        )

        if forecast_df.empty:

            raise ValueError(
                "No Forecast columns detected. "
                "Expected columns such as "
                "'66 KV Bhulleriyan_ECM10_F1'."
            )

        # ====================================================
        # IDENTIFY PSS
        # ====================================================

        pss_name, normalized_pss = (
            identify_pss_from_forecasts(
                forecast_df
            )
        )

        if not pss_name:

            raise ValueError(
                "Could not identify PSS from forecast columns."
            )

        # ====================================================
        # FILTER TO FILE'S PSS
        # ====================================================

        forecast_df = (
            filter_forecasts_for_pss(
                forecast_df,
                normalized_pss,
            )
        )

        if forecast_df.empty:

            raise ValueError(
                f"No forecast columns found for PSS "
                f"{pss_name}."
            )

        # ====================================================
        # FILE DETECTION
        # ====================================================

        file_detection_results.append(
            {
                "File": uploaded_file.name,
                "Index Column": (
                    index_column
                    if index_column
                    else "Not Found"
                ),
                "Detected PSS": pss_name,
                "Normalized PSS": normalized_pss,
                "Actual Columns": len(
                    actual_df
                ),
                "Forecast Columns": len(
                    forecast_df
                ),
            }
        )

        # ====================================================
        # FORECAST DETECTION
        # ====================================================

        temp_forecast = (
            forecast_df.copy()
        )

        temp_forecast.insert(
            0,
            "File",
            uploaded_file.name,
        )

        temp_forecast.insert(
            1,
            "PSS",
            pss_name,
        )

        forecast_detection_results.append(
            temp_forecast
        )

        # ====================================================
        # ACTUAL DETECTION
        # ====================================================

        temp_actual = (
            actual_df.copy()
        )

        temp_actual.insert(
            0,
            "File",
            uploaded_file.name,
        )

        temp_actual.insert(
            1,
            "PSS",
            pss_name,
        )

        actual_detection_results.append(
            temp_actual
        )

        # ====================================================
        # FORECAST × ACTUAL
        # ====================================================

        for _, forecast_info in (
            forecast_df.iterrows()
        ):

            forecast_column = (
                forecast_info[
                    "Forecast Column"
                ]
            )

            forecaster = (
                forecast_info[
                    "Forecaster"
                ]
            )

            # ------------------------------------------------
            # Every Actual column
            # ------------------------------------------------

            for _, actual_info in (
                actual_df.iterrows()
            ):

                actual_column = (
                    actual_info[
                        "Actual Column"
                    ]
                )

                # ============================================
                # CALCULATE
                # ============================================

                metrics = calculate_metrics(
                    actual=df[
                        actual_column
                    ],
                    forecast=df[
                        forecast_column
                    ],
                    exclude_zero=exclude_zero,
                    minimum_actual=minimum_actual,
                )

                # ============================================
                # RESULT
                # ============================================

                mape_results.append(
                    {
                        "File": uploaded_file.name,
                        "PSS": pss_name,
                        "Forecaster": forecaster,
                        "Forecast Column": forecast_column,
                        "Actual Column": actual_column,
                        **metrics,
                    }
                )

                # ============================================
                # ROW LEVEL
                # ============================================

                row_data = pd.DataFrame(
                    {
                        "PSS": pss_name,
                        "Forecaster": forecaster,
                        "Forecast Column": forecast_column,
                        "Actual Column": actual_column,
                        "Actual": to_numeric(
                            df[
                                actual_column
                            ]
                        ),
                        "Forecast": to_numeric(
                            df[
                                forecast_column
                            ]
                        ),
                    },
                    index=df.index,
                )

                row_data[
                    "APE (%)"
                ] = calculate_ape(
                    df[
                        actual_column
                    ],
                    df[
                        forecast_column
                    ],
                    exclude_zero=exclude_zero,
                    minimum_actual=minimum_actual,
                )

                row_level_results.append(
                    row_data
                )

    except Exception as exc:

        errors.append(
            {
                "File": uploaded_file.name,
                "Error": str(exc),
            }
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
# RESULTS DATAFRAME
# ============================================================

mape_df = pd.DataFrame(
    mape_results
)


# ============================================================
# PROCESSING ERRORS
# ============================================================

if errors:

    st.warning(
        f"{len(errors)} file(s) had processing errors."
    )

    st.dataframe(
        pd.DataFrame(errors),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# NO RESULT
# ============================================================

if mape_df.empty:

    st.error(
        "No MAPE results were generated."
    )

    st.stop()


# ============================================================
# KPI
# ============================================================

st.divider()

k1, k2, k3, k4 = st.columns(4)

with k1:

    st.metric(
        "Files",
        len(uploaded_files),
    )

with k2:

    st.metric(
        "PSS",
        mape_df[
            "PSS"
        ].nunique(),
    )

with k3:

    st.metric(
        "Forecasters",
        mape_df[
            "Forecaster"
        ].nunique(),
    )

with k4:

    st.metric(
        "Comparisons",
        len(mape_df),
    )


# ============================================================
# MAPE DETAIL
# ============================================================

st.subheader(
    "📊 MAPE Detail"
)

mape_display = (
    mape_df.copy()
)

for column in [
    "MAPE (%)",
    "MAE",
    "RMSE",
    "Bias",
]:

    mape_display[
        column
    ] = (
        mape_display[
            column
        ].round(4)
    )


st.dataframe(
    mape_display,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# SUMMARY
# ============================================================

st.subheader(
    "📈 PSS × Forecaster Summary"
)

summary_df = (
    mape_df
    .groupby(
        [
            "PSS",
            "Forecaster",
        ],
        as_index=False,
    )
    .agg(
        MAPE=(
            "MAPE (%)",
            "mean",
        ),
        MAE=(
            "MAE",
            "mean",
        ),
        RMSE=(
            "RMSE",
            "mean",
        ),
        Bias=(
            "Bias",
            "mean",
        ),
        Valid_Rows=(
            "Valid Rows",
            "sum",
        ),
        Actual_Comparisons=(
            "Actual Column",
            "count",
        ),
    )
)

summary_df[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
] = (
    summary_df[
        [
            "MAPE",
            "MAE",
            "RMSE",
            "Bias",
        ]
    ].round(4)
)


st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# BEST FORECASTER
# ============================================================

st.subheader(
    "🏆 Best Forecaster"
)

best_forecaster_df = (
    summary_df
    .sort_values(
        "MAPE",
        ascending=True,
    )
    .groupby(
        "PSS",
        as_index=False,
    )
    .first()
)

st.dataframe(
    best_forecaster_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# MAPE MATRIX
# ============================================================

st.subheader(
    "📋 PSS × Forecaster MAPE Matrix"
)

mape_matrix = (
    summary_df
    .pivot(
        index="PSS",
        columns="Forecaster",
        values="MAPE",
    )
    .round(4)
)

st.dataframe(
    mape_matrix,
    use_container_width=True,
)


# ============================================================
# FILE DETECTION
# ============================================================

with st.expander(
    "🔍 File / PSS Detection"
):

    st.dataframe(
        pd.DataFrame(
            file_detection_results
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# FORECAST DETECTION
# ============================================================

with st.expander(
    "🔍 Forecast Column Detection"
):

    if forecast_detection_results:

        forecast_detection_all = (
            pd.concat(
                forecast_detection_results,
                ignore_index=True,
            )
        )

        st.dataframe(
            forecast_detection_all,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ACTUAL DETECTION
# ============================================================

with st.expander(
    "🔍 Actual Column Detection"
):

    if actual_detection_results:

        actual_detection_all = (
            pd.concat(
                actual_detection_results,
                ignore_index=True,
            )
        )

        st.dataframe(
            actual_detection_all,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ROW LEVEL
# ============================================================

if row_level_results:

    row_level_df = pd.concat(
        row_level_results,
        ignore_index=False,
    )

else:

    row_level_df = pd.DataFrame()


with st.expander(
    "📋 Row-Level APE"
):

    if not row_level_df.empty:

        st.dataframe(
            row_level_df,
            use_container_width=True,
            height=500,
        )

    else:

        st.info(
            "No row-level data available."
        )


# ============================================================
# EXCEL REPORT
# ============================================================

def create_excel_report():

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        # ----------------------------------------------------
        # MAPE DETAIL
        # ----------------------------------------------------

        mape_df.to_excel(
            writer,
            sheet_name="MAPE Detail",
            index=False,
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary_df.to_excel(
            writer,
            sheet_name="PSS Forecaster Summary",
            index=False,
        )

        # ----------------------------------------------------
        # BEST
        # ----------------------------------------------------

        best_forecaster_df.to_excel(
            writer,
            sheet_name="Best Forecaster",
            index=False,
        )

        # ----------------------------------------------------
        # MATRIX
        # ----------------------------------------------------

        mape_matrix.to_excel(
            writer,
            sheet_name="MAPE Matrix",
        )

        # ----------------------------------------------------
        # FILE DETECTION
        # ----------------------------------------------------

        pd.DataFrame(
            file_detection_results
        ).to_excel(
            writer,
            sheet_name="File Detection",
            index=False,
        )

        # ----------------------------------------------------
        # FORECAST DETECTION
        # ----------------------------------------------------

        if forecast_detection_results:

            pd.concat(
                forecast_detection_results,
                ignore_index=True,
            ).to_excel(
                writer,
                sheet_name="Forecast Detection",
                index=False,
            )

        # ----------------------------------------------------
        # ACTUAL DETECTION
        # ----------------------------------------------------

        if actual_detection_results:

            pd.concat(
                actual_detection_results,
                ignore_index=True,
            ).to_excel(
                writer,
                sheet_name="Actual Detection",
                index=False,
            )

        # ----------------------------------------------------
        # ROW LEVEL
        # ----------------------------------------------------

        if not row_level_df.empty:

            row_level_df.to_excel(
                writer,
                sheet_name="Row Level APE",
            )

    output.seek(0)

    return output


# ============================================================
# CREATE REPORT
# ============================================================

excel_report = (
    create_excel_report()
)


# ============================================================
# DOWNLOAD
# ============================================================

st.divider()

st.download_button(
    label="📥 Download Complete MAPE Report",
    data=excel_report,
    file_name="PSS_Forecaster_MAPE_Report.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True,
)


# ============================================================
# SUCCESS
# ============================================================

st.success(
    "MAPE calculation completed successfully."
)
