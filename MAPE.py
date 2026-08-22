# ============================================================
# PSS × FORECASTER MAPE ANALYZER
# ============================================================
#
# INPUT:
#
# Multiple CSV / Excel files
#
# Example column:
#
# 66 KV   Bhulleriyan_ALL12.5_F1
#
# Parsed as:
#
# PSS        = 66 KV   Bhulleriyan
# Forecaster = ALL12.5_F1
#
# The complete column is treated as Forecast data.
#
# Actual columns can have names similar to:
#
# Green Gen-Meter
# Green Gen-SCADA
# SEMS
# Actual Power
# Actual Generation
# etc.
#
# ============================================================


import io
import re

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="PSS Forecaster MAPE",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main {
        padding-top: 1rem;
    }

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    .stMetric {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 10px;
        padding: 10px;
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
    "Upload multiple files. Forecast columns are identified from "
    "column names using the PSS_Forecaster naming convention."
)


# ============================================================
# CONSTANTS
# ============================================================

ACTUAL_PRIORITY_PATTERNS = [
    "green gen meter",
    "green gen scada",
    "green generation meter",
    "green generation scada",
    "actual power",
    "actual generation",
    "actual gen",
    "actual energy",
    "actual",
    "sems",
]


ACTUAL_REQUIRED_TERMS = [
    ["green", "gen", "meter"],
    ["green", "gen", "scada"],
    ["green", "generation", "meter"],
    ["green", "generation", "scada"],
    ["actual", "power"],
    ["actual", "generation"],
    ["actual", "gen"],
    ["actual", "energy"],
    ["actual"],
    ["sems"],
]


# ============================================================
# NORMALIZE COLUMN NAME
# ============================================================

def normalize_column_name(column):
    """
    Normalize column names for comparison.

    Examples:

        Green Gen-Meter
        Green_Gen_Meter
        GREEN GEN METER

    become comparable.
    """

    text = str(column).strip().lower()

    # Replace separators
    text = re.sub(
        r"[_\-/]+",
        " ",
        text,
    )

    # Remove special characters
    text = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        text,
    )

    # Remove duplicate spaces
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
    Safely convert a Series to numeric.
    """

    if pd.api.types.is_numeric_dtype(series):

        return pd.to_numeric(
            series,
            errors="coerce",
        )

    return pd.to_numeric(
        series
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


# ============================================================
# PARSE PSS + FORECASTER
# ============================================================

def parse_pss_forecaster(column_name):
    """
    Parse:

        66 KV   Bhulleriyan_ALL12.5_F1

    into:

        PSS        = 66 KV   Bhulleriyan
        Forecaster = ALL12.5_F1

    IMPORTANT:
    Split only at the FIRST underscore.
    """

    text = str(column_name).strip()

    if "_" not in text:

        return None, None

    pss_name, forecaster_name = text.split(
        "_",
        1,
    )

    pss_name = pss_name.strip()
    forecaster_name = forecaster_name.strip()

    if not pss_name or not forecaster_name:

        return None, None

    return (
        pss_name,
        forecaster_name,
    )


# ============================================================
# DETECT FORECAST COLUMNS
# ============================================================

def detect_forecast_columns(df):
    """
    A Forecast column is identified by:

        anything_before_first_underscore
        _
        anything_after_first_underscore

    Example:

        66 KV   Bhulleriyan_ALL12.5_F1

    is a Forecast column.

    Columns without an underscore are not treated as Forecast
    columns.
    """

    detected = []

    for column in df.columns:

        pss, forecaster = (
            parse_pss_forecaster(
                column
            )
        )

        if pss is None:

            continue

        numeric = to_numeric(
            df[column]
        )

        numeric_rows = int(
            numeric.notna().sum()
        )

        # Only accept columns containing actual numeric data
        if numeric_rows == 0:

            continue

        detected.append(
            {
                "Column": column,
                "PSS": pss,
                "Forecaster": forecaster,
                "Numeric Rows": numeric_rows,
            }
        )

    return pd.DataFrame(
        detected
    )


# ============================================================
# DETECT ACTUAL COLUMNS
# ============================================================

def detect_actual_columns(df):
    """
    Detect Actual generation columns using flexible matching.

    Examples:

        Green Gen-Meter
        Green Gen-SCADA
        SEMS
        Actual Power
        Actual Generation
    """

    detected = []

    for column in df.columns:

        normalized = normalize_column_name(
            column
        )

        words = set(
            normalized.split()
        )

        score = 0
        reasons = []

        # ----------------------------------------------------
        # Exact / strong patterns
        # ----------------------------------------------------

        if normalized == "sems":

            score += 200
            reasons.append("SEMS")

        if normalized == "actual":

            score += 200
            reasons.append("Actual")

        # ----------------------------------------------------
        # Green Gen
        # ----------------------------------------------------

        if (
            "green" in words
            and "gen" in words
        ):

            score += 150
            reasons.append(
                "Green + Gen"
            )

        # ----------------------------------------------------
        # Green Generation
        # ----------------------------------------------------

        if (
            "green" in words
            and "generation" in words
        ):

            score += 150
            reasons.append(
                "Green + Generation"
            )

        # ----------------------------------------------------
        # Actual
        # ----------------------------------------------------

        if "actual" in words:

            score += 150
            reasons.append("Actual")

        # ----------------------------------------------------
        # Meter
        # ----------------------------------------------------

        if "meter" in words:

            score += 50
            reasons.append("Meter")

        # ----------------------------------------------------
        # SCADA
        # ----------------------------------------------------

        if "scada" in words:

            score += 50
            reasons.append("SCADA")

        # ----------------------------------------------------
        # SEMS
        # ----------------------------------------------------

        if "sems" in words:

            score += 200
            reasons.append("SEMS")

        # ----------------------------------------------------
        # Accept strong matches
        # ----------------------------------------------------

        if score >= 100:

            detected.append(
                {
                    "Column": column,
                    "Score": score,
                    "Reason": ", ".join(
                        reasons
                    ),
                }
            )

    detected.sort(
        key=lambda x: x["Score"],
        reverse=True,
    )

    return pd.DataFrame(
        detected
    )


# ============================================================
# READ UPLOADED FILE
# ============================================================

def read_uploaded_file(uploaded_file):

    file_name = (
        uploaded_file.name.lower()
    )

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

    # Clean column names
    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# CALCULATE MAPE
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
                Actual - Forecast
            )
            /
            abs(Actual)
        ) * 100

    Zero Actual values are excluded by default.
    """

    actual = to_numeric(
        actual
    )

    forecast = to_numeric(
        forecast
    )

    # --------------------------------------------------------
    # Basic valid mask
    # --------------------------------------------------------

    mask = (
        actual.notna()
        & forecast.notna()
        & np.isfinite(actual)
        & np.isfinite(forecast)
    )

    # --------------------------------------------------------
    # Minimum Actual
    # --------------------------------------------------------

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
        )

    # --------------------------------------------------------
    # Exclude zero Actual
    # --------------------------------------------------------

    if exclude_zero:

        mask &= (
            actual != 0
        )

    # --------------------------------------------------------
    # No valid rows
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

    mape = ape.mean()

    mae = np.abs(
        error
    ).mean()

    rmse = np.sqrt(
        np.mean(
            error ** 2
        )
    )

    bias = error.mean()

    return {
        "MAPE (%)": float(mape),
        "MAE": float(mae),
        "RMSE": float(rmse),
        "Bias": float(bias),
        "Valid Rows": int(
            mask.sum()
        ),
    }


# ============================================================
# ROW LEVEL APE
# ============================================================

def calculate_ape_series(
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

    if exclude_zero:

        mask &= (
            actual != 0
        )

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
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
# MULTIPLE FILE UPLOADER
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
        "Upload multiple CSV/Excel files to begin."
    )

    st.stop()


# ============================================================
# SETTINGS
# ============================================================

st.subheader(
    "⚙️ MAPE Settings"
)

setting1, setting2 = st.columns(2)

with setting1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Recommended for solar generation because "
            "night-time generation is normally zero."
        ),
    )


with setting2:

    minimum_actual = st.number_input(
        "Minimum Actual Value",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )


# ============================================================
# FILE INFORMATION
# ============================================================

st.subheader(
    "📁 Uploaded Files"
)

file_table = []

for uploaded_file in uploaded_files:

    file_table.append(
        {
            "File": uploaded_file.name,
            "Size (KB)": round(
                uploaded_file.size
                / 1024,
                2,
            ),
        }
    )


st.dataframe(
    pd.DataFrame(
        file_table
    ),
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
        "Click 'Calculate MAPE' after uploading your files."
    )

    st.stop()


# ============================================================
# STORAGE
# ============================================================

all_mape_results = []

all_row_results = []

all_forecast_detection = []

all_actual_detection = []

processing_errors = []


# ============================================================
# PROGRESS
# ============================================================

progress_bar = st.progress(
    0
)

status_text = st.empty()


# ============================================================
# PROCESS EVERY FILE
# ============================================================

for file_index, uploaded_file in enumerate(
    uploaded_files
):

    status_text.write(
        f"Processing {uploaded_file.name}..."
    )

    try:

        # ----------------------------------------------------
        # READ
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # DETECT FORECAST COLUMNS
        # ----------------------------------------------------

        forecast_df = (
            detect_forecast_columns(
                df
            )
        )

        # ----------------------------------------------------
        # DETECT ACTUAL COLUMNS
        # ----------------------------------------------------

        actual_df = (
            detect_actual_columns(
                df
            )
        )

        # ----------------------------------------------------
        # STORE DETECTION INFORMATION
        # ----------------------------------------------------

        if not forecast_df.empty:

            forecast_temp = (
                forecast_df.copy()
            )

            forecast_temp.insert(
                0,
                "File",
                uploaded_file.name,
            )

            all_forecast_detection.append(
                forecast_temp
            )

        if not actual_df.empty:

            actual_temp = (
                actual_df.copy()
            )

            actual_temp.insert(
                0,
                "File",
                uploaded_file.name,
            )

            all_actual_detection.append(
                actual_temp
            )

        # ----------------------------------------------------
        # VALIDATE FORECAST
        # ----------------------------------------------------

        if forecast_df.empty:

            raise ValueError(
                "No PSS_Forecaster forecast columns detected."
            )

        # ----------------------------------------------------
        # VALIDATE ACTUAL
        # ----------------------------------------------------

        if actual_df.empty:

            raise ValueError(
                "No Actual columns detected."
            )

        # ----------------------------------------------------
        # FORECAST COLUMNS
        # ----------------------------------------------------

        forecast_columns = (
            forecast_df["Column"]
            .tolist()
        )

        # ----------------------------------------------------
        # ACTUAL COLUMNS
        # ----------------------------------------------------

        actual_columns = (
            actual_df["Column"]
            .tolist()
        )

        # ----------------------------------------------------
        # FORECAST × ACTUAL
        # ----------------------------------------------------

        for forecast_column in forecast_columns:

            # Get PSS and Forecaster
            pss_name, forecaster_name = (
                parse_pss_forecaster(
                    forecast_column
                )
            )

            if pss_name is None:

                continue

            # ------------------------------------------------
            # Compare Forecast against EVERY Actual
            # ------------------------------------------------

            for actual_column in actual_columns:

                metrics = calculate_mape(
                    actual=df[
                        actual_column
                    ],
                    forecast=df[
                        forecast_column
                    ],
                    exclude_zero=exclude_zero,
                    minimum_actual=minimum_actual,
                )

                all_mape_results.append(
                    {
                        "PSS": pss_name,
                        "Forecaster": forecaster_name,
                        "Forecast Column": forecast_column,
                        "Actual Column": actual_column,
                        "File": uploaded_file.name,
                        **metrics,
                    }
                )

                # ------------------------------------------------
                # ROW LEVEL DATA
                # ------------------------------------------------

                row_result = pd.DataFrame(
                    {
                        "PSS": pss_name,
                        "Forecaster": forecaster_name,
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

                row_result[
                    "APE (%)"
                ] = calculate_ape_series(
                    df[
                        actual_column
                    ],
                    df[
                        forecast_column
                    ],
                    exclude_zero=exclude_zero,
                    minimum_actual=minimum_actual,
                )

                # Add original file name
                row_result[
                    "File"
                ] = uploaded_file.name

                all_row_results.append(
                    row_result
                )

    except Exception as e:

        processing_errors.append(
            {
                "File": uploaded_file.name,
                "Error": str(e),
            }
        )

    progress_bar.progress(
        int(
            (
                file_index + 1
            )
            / len(uploaded_files)
            * 100
        )
    )


status_text.empty()


# ============================================================
# BUILD RESULTS
# ============================================================

mape_df = pd.DataFrame(
    all_mape_results
)


# ============================================================
# PROCESSING ERRORS
# ============================================================

if processing_errors:

    st.warning(
        f"{len(processing_errors)} file(s) "
        "had processing issues."
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
        "No MAPE results could be calculated."
    )

    st.stop()


# ============================================================
# METRICS
# ============================================================

st.divider()

metric1, metric2, metric3, metric4 = (
    st.columns(4)
)

with metric1:

    st.metric(
        "Files Processed",
        len(uploaded_files),
    )

with metric2:

    st.metric(
        "PSS",
        mape_df["PSS"].nunique(),
    )

with metric3:

    st.metric(
        "Forecasters",
        mape_df[
            "Forecaster"
        ].nunique(),
    )

with metric4:

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

display_mape = (
    mape_df.copy()
)

for column in [
    "MAPE (%)",
    "MAE",
    "RMSE",
    "Bias",
]:

    display_mape[column] = (
        display_mape[column]
        .round(4)
    )


st.dataframe(
    display_mape,
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
        Actual_Comparisons=(
            "Actual Column",
            "count",
        ),
        Valid_Rows=(
            "Valid Rows",
            "sum",
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
# BEST FORECASTER FOR EACH PSS
# ============================================================

st.subheader(
    "🏆 Best Forecaster for Each PSS"
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
# PSS × FORECASTER MAPE MATRIX
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
# ACTUAL COLUMN DETECTION
# ============================================================

with st.expander(
    "🔍 Actual Column Detection"
):

    if all_actual_detection:

        actual_detection_df = (
            pd.concat(
                all_actual_detection,
                ignore_index=True,
            )
        )

        st.dataframe(
            actual_detection_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No Actual columns detected."
        )


# ============================================================
# FORECAST COLUMN DETECTION
# ============================================================

with st.expander(
    "🔍 PSS / Forecaster Column Detection"
):

    if all_forecast_detection:

        forecast_detection_df = (
            pd.concat(
                all_forecast_detection,
                ignore_index=True,
            )
        )

        st.dataframe(
            forecast_detection_df,
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.info(
            "No PSS_Forecaster columns detected."
        )


# ============================================================
# ROW LEVEL DATA
# ============================================================

if all_row_results:

    row_level_df = pd.concat(
        all_row_results,
        ignore_index=True,
    )

    with st.expander(
        "📋 Row-Level APE"
    ):

        st.dataframe(
            row_level_df,
            use_container_width=True,
            height=500,
        )

else:

    row_level_df = pd.DataFrame()


# ============================================================
# CREATE EXCEL REPORT
# ============================================================

def create_excel_report(
    mape_detail,
    summary,
    best_forecaster,
    matrix,
    actual_detection,
    forecast_detection,
    row_level,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        # ----------------------------------------------------
        # MAPE DETAIL
        # ----------------------------------------------------

        mape_detail.to_excel(
            writer,
            sheet_name="MAPE Detail",
            index=False,
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary.to_excel(
            writer,
            sheet_name="PSS Forecaster Summary",
            index=False,
        )

        # ----------------------------------------------------
        # BEST FORECASTER
        # ----------------------------------------------------

        best_forecaster.to_excel(
            writer,
            sheet_name="Best Forecaster",
            index=False,
        )

        # ----------------------------------------------------
        # MATRIX
        # ----------------------------------------------------

        matrix.to_excel(
            writer,
            sheet_name="MAPE Matrix",
        )

        # ----------------------------------------------------
        # ACTUAL DETECTION
        # ----------------------------------------------------

        if not actual_detection.empty:

            actual_detection.to_excel(
                writer,
                sheet_name="Actual Detection",
                index=False,
            )

        # ----------------------------------------------------
        # FORECAST DETECTION
        # ----------------------------------------------------

        if not forecast_detection.empty:

            forecast_detection.to_excel(
                writer,
                sheet_name="Forecast Detection",
                index=False,
            )

        # ----------------------------------------------------
        # ROW LEVEL
        # ----------------------------------------------------

        if not row_level.empty:

            row_level.to_excel(
                writer,
                sheet_name="Row Level APE",
                index=False,
            )

    output.seek(0)

    return output


# ============================================================
# PREPARE DETECTION TABLES
# ============================================================

if all_actual_detection:

    actual_detection_export = (
        pd.concat(
            all_actual_detection,
            ignore_index=True,
        )
    )

else:

    actual_detection_export = (
        pd.DataFrame()
    )


if all_forecast_detection:

    forecast_detection_export = (
        pd.concat(
            all_forecast_detection,
            ignore_index=True,
        )
    )

else:

    forecast_detection_export = (
        pd.DataFrame()
    )


# ============================================================
# CREATE REPORT
# ============================================================

excel_report = create_excel_report(
    mape_detail=mape_df,
    summary=summary_df,
    best_forecaster=best_forecaster_df,
    matrix=mape_matrix,
    actual_detection=actual_detection_export,
    forecast_detection=forecast_detection_export,
    row_level=row_level_df,
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
    f"MAPE calculation completed: "
    f"{mape_df['PSS'].nunique()} PSS, "
    f"{mape_df['Forecaster'].nunique()} Forecasters, "
    f"{len(mape_df)} Actual-vs-Forecaster comparisons."
)
