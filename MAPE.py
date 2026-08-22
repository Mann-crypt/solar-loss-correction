# ============================================================
# PSS × FORECASTER MAPE ANALYZER
# ============================================================
#
# MULTIPLE FILE UPLOAD
#
# IMPORTANT STRUCTURE
#
# Each file contains ONLY ONE PSS.
#
# Example PSS values inside a file:
#
#   66 KV Bhulleriyan
#   66 kV Bhulleriyan
#   66K
#
# These are treated as the same PSS.
#
#
# FORECAST COLUMNS
#
#   66 KV Bhulleriyan_ALL12.5_F1
#   66 KV Bhulleriyan_ALL12.5_F2
#
# Parsed as:
#
#   PSS        = 66 KV Bhulleriyan
#   Forecaster = ALL12.5_F1
#
#
# ACTUAL COLUMNS
#
#   Green Gen-Meter
#   Green Gen-SCADA
#   SEMS
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

st.write(
    """
    Upload multiple files. Each file represents one PSS.
    Forecast columns are automatically detected from the
    `PSS_Forecaster` naming convention.
    """
)


# ============================================================
# GENERAL TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    General text normalization.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    are normalized for comparison.
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
# PSS NORMALIZATION
# ============================================================

def normalize_pss(value):
    """
    Normalize PSS names.

    The goal is to treat formatting differences as the
    same PSS.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    all resolve to a common comparison key.

    """

    if pd.isna(value):
        return ""

    text = str(value).strip().lower()

    # Remove HTML break tags if present
    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    # Remove all whitespace
    compact = re.sub(
        r"\s+",
        "",
        text,
    )

    # Normalize KV variations
    compact = compact.replace(
        "kv",
        "k",
    )

    # --------------------------------------------------------
    # Specific normalization:
    #
    # 66 KV
    # 66 kV
    # 66K
    #
    # become 66K
    # --------------------------------------------------------

    compact = re.sub(
        r"(\d+)k",
        r"\1k",
        compact,
    )

    return compact.upper()


# ============================================================
# DISPLAY PSS NAME
# ============================================================

def clean_display_pss(value):
    """
    Creates a clean display name.

    This does NOT affect the comparison key.
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
# NORMALIZE COLUMN NAME
# ============================================================

def normalize_column_name(column):
    """
    Normalize a column name for Actual detection.
    """

    text = str(column).strip().lower()

    text = re.sub(
        r"[_\-/]+",
        " ",
        text,
    )

    text = re.sub(
        r"[^a-z0-9 ]+",
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
# NUMERIC CONVERSION
# ============================================================

def to_numeric(series):

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

    file_name = uploaded_file.name.lower()

    # --------------------------------------------------------
    # CSV
    # --------------------------------------------------------

    if file_name.endswith(".csv"):

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

    # --------------------------------------------------------
    # EXCEL
    # --------------------------------------------------------

    if file_name.endswith(
        (".xlsx", ".xls")
    ):

        uploaded_file.seek(0)

        return pd.read_excel(
            uploaded_file
        )

    raise ValueError(
        "Unsupported file type."
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
# DETECT PSS DATA COLUMN
# ============================================================

def detect_pss_data_column(df):
    """
    Attempts to identify a column containing PSS names.

    The column is expected to contain repeated values such as:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    We score object/string columns based on:
        - repeated values
        - PSS-like text
        - KV / K patterns
    """

    candidates = []

    for column in df.columns:

        series = df[column]

        # Skip numeric columns
        if pd.api.types.is_numeric_dtype(
            series
        ):
            continue

        non_null = (
            series.dropna()
            .astype(str)
            .str.strip()
        )

        if non_null.empty:
            continue

        # Number of unique values
        unique_count = (
            non_null.nunique()
        )

        # Number of populated rows
        populated = len(non_null)

        if populated == 0:
            continue

        # Repetition ratio
        repetition_ratio = (
            1
            - unique_count / populated
        )

        normalized_values = [
            normalize_pss(x)
            for x in non_null.head(500)
        ]

        pss_like_count = sum(
            (
                "K" in value
                and any(
                    char.isdigit()
                    for char in value
                )
            )
            for value in normalized_values
        )

        pss_like_ratio = (
            pss_like_count
            / len(normalized_values)
            if normalized_values
            else 0
        )

        score = (
            repetition_ratio * 50
            + pss_like_ratio * 100
        )

        candidates.append(
            {
                "Column": column,
                "Score": score,
                "Unique Values": unique_count,
                "Rows": populated,
            }
        )

    if not candidates:

        return None, pd.DataFrame()

    candidates.sort(
        key=lambda x: x["Score"],
        reverse=True,
    )

    result = pd.DataFrame(
        candidates
    )

    return (
        candidates[0]["Column"],
        result,
    )


# ============================================================
# EXTRACT PSS FROM DATA
# ============================================================

def determine_file_pss(
    df,
    pss_column=None,
):
    """
    Determine the single PSS represented by a file.

    Since one file contains only one PSS, all normalized
    values should resolve to the same PSS key.
    """

    if pss_column is None:

        return (
            None,
            pd.DataFrame(),
        )

    series = df[
        pss_column
    ].dropna()

    if series.empty:

        return (
            None,
            pd.DataFrame(),
        )

    records = []

    for value in series:

        display_value = (
            clean_display_pss(
                value
            )
        )

        normalized_value = (
            normalize_pss(
                value
            )
        )

        if not normalized_value:
            continue

        records.append(
            {
                "Original PSS": display_value,
                "Normalized PSS": normalized_value,
            }
        )

    if not records:

        return (
            None,
            pd.DataFrame(),
        )

    pss_values = pd.DataFrame(
        records
    )

    # Frequency of normalized values
    frequency = (
        pss_values[
            "Normalized PSS"
        ]
        .value_counts()
    )

    dominant_key = (
        frequency.index[0]
    )

    dominant_rows = (
        pss_values[
            pss_values[
                "Normalized PSS"
            ]
            == dominant_key
        ]
    )

    # Use most frequent original spelling
    display_pss = (
        dominant_rows[
            "Original PSS"
        ]
        .value_counts()
        .index[0]
    )

    return (
        display_pss,
        pss_values,
    )


# ============================================================
# PARSE FORECAST COLUMN
# ============================================================

def parse_forecast_column(
    column_name
):
    """
    Example:

        66 KV Bhulleriyan_ALL12.5_F1

    becomes:

        PSS        = 66 KV Bhulleriyan
        Forecaster = ALL12.5_F1

    Split ONLY at first underscore.
    """

    text = str(
        column_name
    ).strip()

    if "_" not in text:

        return (
            None,
            None,
        )

    pss_part, forecaster_part = (
        text.split(
            "_",
            1,
        )
    )

    pss_part = pss_part.strip()
    forecaster_part = (
        forecaster_part.strip()
    )

    if (
        not pss_part
        or not forecaster_part
    ):

        return (
            None,
            None,
        )

    return (
        pss_part,
        forecaster_part,
    )


# ============================================================
# DETECT FORECAST COLUMNS
# ============================================================

def detect_forecast_columns(
    df,
    file_pss,
):
    """
    Detect forecast columns using:

        PSS_Forecaster

    The PSS portion must match the PSS detected from
    the file after normalization.
    """

    results = []

    normalized_file_pss = (
        normalize_pss(
            file_pss
        )
    )

    for column in df.columns:

        pss_part, forecaster = (
            parse_forecast_column(
                column
            )
        )

        if pss_part is None:

            continue

        normalized_column_pss = (
            normalize_pss(
                pss_part
            )
        )

        # ----------------------------------------------------
        # PSS must match
        # ----------------------------------------------------

        if (
            normalized_column_pss
            != normalized_file_pss
        ):

            continue

        # ----------------------------------------------------
        # Must contain numeric data
        # ----------------------------------------------------

        numeric = to_numeric(
            df[column]
        )

        numeric_rows = int(
            numeric.notna().sum()
        )

        if numeric_rows == 0:

            continue

        results.append(
            {
                "Forecast Column": column,
                "PSS From Column": pss_part,
                "PSS": file_pss,
                "Forecaster": forecaster,
                "Numeric Rows": numeric_rows,
            }
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# ACTUAL COLUMN DETECTION
# ============================================================

def detect_actual_columns(
    df,
    exclude_columns=None,
):
    """
    Detect Actual generation columns.

    Examples:

        Green Gen-Meter
        Green Gen-SCADA
        SEMS
        Actual Power
        Actual Generation
    """

    if exclude_columns is None:

        exclude_columns = []

    results = []

    for column in df.columns:

        if column in exclude_columns:

            continue

        normalized = (
            normalize_column_name(
                column
            )
        )

        words = set(
            normalized.split()
        )

        score = 0
        reasons = []

        # ----------------------------------------------------
        # SEMS
        # ----------------------------------------------------

        if "sems" in words:

            score += 200
            reasons.append(
                "SEMS"
            )

        # ----------------------------------------------------
        # Actual
        # ----------------------------------------------------

        if "actual" in words:

            score += 150
            reasons.append(
                "Actual"
            )

        # ----------------------------------------------------
        # Green + Gen
        # ----------------------------------------------------

        if (
            "green" in words
            and "gen" in words
        ):

            score += 150
            reasons.append(
                "Green Gen"
            )

        # ----------------------------------------------------
        # Green + Generation
        # ----------------------------------------------------

        if (
            "green" in words
            and "generation" in words
        ):

            score += 150
            reasons.append(
                "Green Generation"
            )

        # ----------------------------------------------------
        # Meter
        # ----------------------------------------------------

        if "meter" in words:

            score += 50
            reasons.append(
                "Meter"
            )

        # ----------------------------------------------------
        # SCADA
        # ----------------------------------------------------

        if "scada" in words:

            score += 50
            reasons.append(
                "SCADA"
            )

        # ----------------------------------------------------
        # Generation
        # ----------------------------------------------------

        if "generation" in words:

            score += 30
            reasons.append(
                "Generation"
            )

        # ----------------------------------------------------
        # Gen
        # ----------------------------------------------------

        if "gen" in words:

            score += 30
            reasons.append(
                "Gen"
            )

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

        # ----------------------------------------------------
        # Accept strong Actual candidates
        # ----------------------------------------------------

        if score >= 100:

            results.append(
                {
                    "Actual Column": column,
                    "Score": score,
                    "Reason": ", ".join(
                        reasons
                    ),
                    "Numeric Rows": numeric_rows,
                }
            )

    results.sort(
        key=lambda x: x["Score"],
        reverse=True,
    )

    return pd.DataFrame(
        results
    )


# ============================================================
# MAPE
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
    # Zero actual
    # --------------------------------------------------------

    if exclude_zero:

        mask &= (
            actual != 0
        )

    # --------------------------------------------------------
    # No valid data
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

    return {
        "MAPE (%)": float(
            ape.mean()
        ),
        "MAE": float(
            np.abs(
                error
            ).mean()
        ),
        "RMSE": float(
            np.sqrt(
                np.mean(
                    error ** 2
                )
            )
        ),
        "Bias": float(
            error.mean()
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

    result = pd.Series(
        np.nan,
        index=actual.index,
    )

    mask = (
        actual.notna()
        & forecast.notna()
        & np.isfinite(actual)
        & np.isfinite(forecast)
    )

    if exclude_zero:

        mask &= (
            actual != 0
        )

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
        )

    result.loc[mask] = (
        np.abs(
            (
                forecast.loc[mask]
                - actual.loc[mask]
            )
            / actual.loc[mask]
        )
        * 100
    )

    return result


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_files = st.file_uploader(
    "📂 Upload Multiple CSV / Excel Files",
    type=[
        "csv",
        "xlsx",
        "xls",
    ],
    accept_multiple_files=True,
)


if not uploaded_files:

    st.info(
        "Upload your files to start the MAPE calculation."
    )

    st.stop()


# ============================================================
# MAPE SETTINGS
# ============================================================

st.subheader(
    "⚙️ MAPE Settings"
)

setting_col1, setting_col2 = (
    st.columns(2)
)

with setting_col1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Recommended for solar generation because "
            "night-time generation is normally zero."
        ),
    )


with setting_col2:

    minimum_actual = st.number_input(
        "Minimum Actual Generation",
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

file_list = pd.DataFrame(
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
    file_list,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# CALCULATE BUTTON
# ============================================================

calculate = st.button(
    "🚀 Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not calculate:

    st.info(
        "Click Calculate MAPE to process all uploaded files."
    )

    st.stop()


# ============================================================
# RESULT STORAGE
# ============================================================

mape_results = []

row_results = []

file_pss_results = []

forecast_detection_results = []

actual_detection_results = []

processing_errors = []


# ============================================================
# PROGRESS
# ============================================================

progress = st.progress(
    0
)

status = st.empty()


# ============================================================
# PROCESS FILES
# ============================================================

for index, uploaded_file in enumerate(
    uploaded_files
):

    status.write(
        f"Processing: {uploaded_file.name}"
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
                "File is empty."
            )

        # ====================================================
        # DETECT PSS COLUMN
        # ====================================================

        pss_column, pss_candidates = (
            detect_pss_data_column(
                df
            )
        )

        if pss_column is None:

            raise ValueError(
                "Could not automatically identify "
                "the PSS data column."
            )

        # ====================================================
        # DETERMINE FILE PSS
        # ====================================================

        file_pss, pss_values = (
            determine_file_pss(
                df,
                pss_column,
            )
        )

        if not file_pss:

            raise ValueError(
                "Could not determine PSS from the file."
            )

        # ====================================================
        # SAVE FILE PSS
        # ====================================================

        file_pss_results.append(
            {
                "File": uploaded_file.name,
                "PSS Column": pss_column,
                "Detected PSS": file_pss,
                "Normalized PSS": normalize_pss(
                    file_pss
                ),
                "Unique Normalized PSS Values": (
                    pss_values[
                        "Normalized PSS"
                    ]
                    .nunique()
                    if not pss_values.empty
                    else 0
                ),
            }
        )

        # ====================================================
        # DETECT FORECAST COLUMNS
        # ====================================================

        forecast_df = (
            detect_forecast_columns(
                df,
                file_pss,
            )
        )

        if forecast_df.empty:

            raise ValueError(
                f"No forecast columns found for PSS "
                f"'{file_pss}'. Expected columns like "
                f"'PSS_Forecaster'."
            )

        # ====================================================
        # SAVE FORECAST DETECTION
        # ====================================================

        forecast_temp = (
            forecast_df.copy()
        )

        forecast_temp.insert(
            0,
            "File",
            uploaded_file.name,
        )

        forecast_detection_results.append(
            forecast_temp
        )

        # ====================================================
        # DETECT ACTUAL COLUMNS
        # ====================================================

        actual_df = (
            detect_actual_columns(
                df,
                exclude_columns=[
                    pss_column
                ],
            )
        )

        if actual_df.empty:

            raise ValueError(
                "No Actual generation columns found."
            )

        # ====================================================
        # SAVE ACTUAL DETECTION
        # ====================================================

        actual_temp = (
            actual_df.copy()
        )

        actual_temp.insert(
            0,
            "File",
            uploaded_file.name,
        )

        actual_detection_results.append(
            actual_temp
        )

        # ====================================================
        # FORECAST LOOP
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

            # =================================================
            # ACTUAL LOOP
            # =================================================

            for _, actual_info in (
                actual_df.iterrows()
            ):

                actual_column = (
                    actual_info[
                        "Actual Column"
                    ]
                )

                # =============================================
                # MAPE
                # =============================================

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

                # =============================================
                # SAVE MAPE RESULT
                # =============================================

                mape_results.append(
                    {
                        "File": uploaded_file.name,
                        "PSS": file_pss,
                        "Forecaster": forecaster,
                        "Forecast Column": forecast_column,
                        "Actual Column": actual_column,
                        **metrics,
                    }
                )

                # =============================================
                # ROW LEVEL
                # =============================================

                row_data = pd.DataFrame(
                    {
                        "File": uploaded_file.name,
                        "PSS": file_pss,
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
                    }
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

                row_results.append(
                    row_data
                )

    except Exception as error:

        processing_errors.append(
            {
                "File": uploaded_file.name,
                "Error": str(error),
            }
        )

    progress.progress(
        int(
            (
                index + 1
            )
            / len(uploaded_files)
            * 100
        )
    )


status.empty()


# ============================================================
# BUILD RESULT DATAFRAME
# ============================================================

mape_df = pd.DataFrame(
    mape_results
)


# ============================================================
# ERRORS
# ============================================================

if processing_errors:

    st.warning(
        f"{len(processing_errors)} file(s) "
        "could not be completely processed."
    )

    st.dataframe(
        pd.DataFrame(
            processing_errors
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# NO RESULTS
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
        "MAPE Comparisons",
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

for col in [
    "MAPE (%)",
    "MAE",
    "RMSE",
    "Bias",
]:

    mape_display[col] = (
        mape_display[col]
        .round(4)
    )


st.dataframe(
    mape_display,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PSS × FORECASTER SUMMARY
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
] = summary_df[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
].round(4)


st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# BEST FORECASTER
# ============================================================

st.subheader(
    "🏆 Best Forecaster by PSS"
)

best_forecaster = (
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
    best_forecaster,
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
# FILE → PSS DETECTION
# ============================================================

with st.expander(
    "🔍 File / PSS Detection"
):

    file_pss_df = pd.DataFrame(
        file_pss_results
    )

    st.dataframe(
        file_pss_df,
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

        forecast_detection_df = (
            pd.concat(
                forecast_detection_results,
                ignore_index=True,
            )
        )

        st.dataframe(
            forecast_detection_df,
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

        actual_detection_df = (
            pd.concat(
                actual_detection_results,
                ignore_index=True,
            )
        )

        st.dataframe(
            actual_detection_df,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# ROW LEVEL DATA
# ============================================================

if row_results:

    row_level_df = pd.concat(
        row_results,
        ignore_index=True,
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

def create_excel_report(
    mape_detail,
    summary,
    best_forecaster,
    matrix,
    file_pss,
    forecast_detection,
    actual_detection,
    row_level,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        # -----------------------------------------------
        # MAPE DETAIL
        # -----------------------------------------------

        mape_detail.to_excel(
            writer,
            sheet_name="MAPE Detail",
            index=False,
        )

        # -----------------------------------------------
        # SUMMARY
        # -----------------------------------------------

        summary.to_excel(
            writer,
            sheet_name="PSS Forecaster Summary",
            index=False,
        )

        # -----------------------------------------------
        # BEST FORECASTER
        # -----------------------------------------------

        best_forecaster.to_excel(
            writer,
            sheet_name="Best Forecaster",
            index=False,
        )

        # -----------------------------------------------
        # MATRIX
        # -----------------------------------------------

        matrix.to_excel(
            writer,
            sheet_name="MAPE Matrix",
        )

        # -----------------------------------------------
        # FILE PSS
        # -----------------------------------------------

        file_pss.to_excel(
            writer,
            sheet_name="File PSS",
            index=False,
        )

        # -----------------------------------------------
        # FORECAST DETECTION
        # -----------------------------------------------

        if not forecast_detection.empty:

            forecast_detection.to_excel(
                writer,
                sheet_name="Forecast Detection",
                index=False,
            )

        # -----------------------------------------------
        # ACTUAL DETECTION
        # -----------------------------------------------

        if not actual_detection.empty:

            actual_detection.to_excel(
                writer,
                sheet_name="Actual Detection",
                index=False,
            )

        # -----------------------------------------------
        # ROW LEVEL
        # -----------------------------------------------

        if not row_level.empty:

            row_level.to_excel(
                writer,
                sheet_name="Row Level APE",
                index=False,
            )

    output.seek(0)

    return output


# ============================================================
# PREPARE DETECTION DATA
# ============================================================

if forecast_detection_results:

    forecast_detection_export = (
        pd.concat(
            forecast_detection_results,
            ignore_index=True,
        )
    )

else:

    forecast_detection_export = (
        pd.DataFrame()
    )


if actual_detection_results:

    actual_detection_export = (
        pd.concat(
            actual_detection_results,
            ignore_index=True,
        )
    )

else:

    actual_detection_export = (
        pd.DataFrame()
    )


file_pss_export = pd.DataFrame(
    file_pss_results
)


# ============================================================
# CREATE EXCEL
# ============================================================

excel_file = create_excel_report(
    mape_detail=mape_df,
    summary=summary_df,
    best_forecaster=best_forecaster,
    matrix=mape_matrix,
    file_pss=file_pss_export,
    forecast_detection=forecast_detection_export,
    actual_detection=actual_detection_export,
    row_level=row_level_df,
)


# ============================================================
# DOWNLOAD
# ============================================================

st.divider()

st.download_button(
    label="📥 Download Complete MAPE Report",
    data=excel_file,
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
    f"Completed MAPE calculation for "
    f"{mape_df['PSS'].nunique()} PSS, "
    f"{mape_df['Forecaster'].nunique()} Forecasters, "
    f"and {len(mape_df)} Actual-vs-Forecast comparisons."
)
