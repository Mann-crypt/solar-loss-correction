# ============================================================
# STREAMLIT APP
# AUTOMATIC ACTUAL / FORECAST COLUMN DETECTION + MAPE
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
    page_title="Automatic MAPE Analyzer",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>
    .main {
        padding-top: 1rem;
    }

    .metric-card {
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #ddd;
        text-align: center;
    }

    h1 {
        margin-bottom: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TITLE
# ============================================================

st.title("📊 Automatic Actual vs Forecast MAPE Analyzer")

st.write(
    "Upload your CSV or Excel file. The application automatically identifies "
    "Actual Generation and Forecast/Predicted columns using flexible name matching."
)


# ============================================================
# COLUMN NAME NORMALIZATION
# ============================================================

def normalize_column_name(col):
    """
    Convert column name into a standard form.

    Examples:
        Green Gen-Meter
        green_gen_meter
        Green Generation Meter

    become comparable.
    """

    col = str(col).strip().lower()

    # Replace separators
    col = re.sub(r"[_\-/]+", " ", col)

    # Remove special characters
    col = re.sub(r"[^a-z0-9 ]+", " ", col)

    # Collapse multiple spaces
    col = re.sub(r"\s+", " ", col).strip()

    return col


# ============================================================
# ACTUAL COLUMN DETECTION
# ============================================================

ACTUAL_EXACT_TERMS = {
    "actual",
    "actual power",
    "actual generation",
    "actual gen",
    "actual energy",
    "green gen meter",
    "green gen scada",
    "green generation meter",
    "green generation scada",
    "generation meter",
    "generation scada",
    "sems",
}


ACTUAL_KEYWORD_GROUPS = [
    ["actual"],
    ["actual", "power"],
    ["actual", "generation"],
    ["actual", "gen"],
    ["green", "gen"],
    ["green", "generation"],
    ["gen", "meter"],
    ["gen", "scada"],
    ["generation", "meter"],
    ["generation", "scada"],
    ["sems"],
]


def detect_actual_columns(df):

    detected = []
    scores = {}

    for original_col in df.columns:

        normalized = normalize_column_name(original_col)

        score = 0

        # Exact matches
        if normalized in ACTUAL_EXACT_TERMS:
            score += 100

        # Keyword matching
        for group in ACTUAL_KEYWORD_GROUPS:

            if all(word in normalized.split() for word in group):
                score += 20

        # Additional strong patterns
        if "actual" in normalized:
            score += 50

        if "green gen" in normalized:
            score += 40

        if "green generation" in normalized:
            score += 40

        if "sems" in normalized:
            score += 50

        if score > 0:
            detected.append(original_col)
            scores[original_col] = score

    # Sort by confidence
    detected = sorted(
        detected,
        key=lambda x: scores[x],
        reverse=True,
    )

    return detected, scores


# ============================================================
# FORECAST COLUMN DETECTION
# ============================================================

FORECAST_EXACT_TERMS = {
    "forecast",
    "forecast power",
    "forecast generation",
    "forecast gen",
    "forecasted power",
    "forecasted generation",
    "predicted power",
    "predicted generation",
    "prediction",
    "predicted",
}


FORECAST_KEYWORDS = [
    "forecast",
    "forecasted",
    "predicted",
    "prediction",
    "fcst",
    "fc",
]


def detect_forecast_columns(df):

    detected = []
    scores = {}

    for original_col in df.columns:

        normalized = normalize_column_name(original_col)

        score = 0

        if normalized in FORECAST_EXACT_TERMS:
            score += 100

        for keyword in FORECAST_KEYWORDS:

            if keyword in normalized.split():
                score += 30

        # Strong forecast patterns
        if "forecast" in normalized:
            score += 50

        if "predicted" in normalized:
            score += 50

        if "prediction" in normalized:
            score += 50

        if score > 0:
            detected.append(original_col)
            scores[original_col] = score

    detected = sorted(
        detected,
        key=lambda x: scores[x],
        reverse=True,
    )

    return detected, scores


# ============================================================
# NUMERIC CONVERSION
# ============================================================

def convert_numeric(series):

    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")

    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


# ============================================================
# MAPE
# ============================================================

def calculate_mape(actual, predicted):

    actual = convert_numeric(actual)
    predicted = convert_numeric(predicted)

    valid_mask = (
        actual.notna()
        & predicted.notna()
        & np.isfinite(actual)
        & np.isfinite(predicted)
        & (actual != 0)
    )

    if valid_mask.sum() == 0:
        return np.nan, 0

    actual_valid = actual.loc[valid_mask]
    predicted_valid = predicted.loc[valid_mask]

    ape = (
        np.abs(
            (actual_valid - predicted_valid)
            / actual_valid
        )
        * 100
    )

    # Protect against infinite values
    ape = ape.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if len(ape) == 0:
        return np.nan, 0

    return ape.mean(), len(ape)


# ============================================================
# OTHER ERROR METRICS
# ============================================================

def calculate_metrics(actual, predicted):

    actual = convert_numeric(actual)
    predicted = convert_numeric(predicted)

    valid_mask = (
        actual.notna()
        & predicted.notna()
        & np.isfinite(actual)
        & np.isfinite(predicted)
    )

    if valid_mask.sum() == 0:
        return {
            "MAPE (%)": np.nan,
            "MAE": np.nan,
            "RMSE": np.nan,
            "Bias": np.nan,
            "Valid Rows": 0,
        }

    a = actual.loc[valid_mask]
    p = predicted.loc[valid_mask]

    error = p - a

    # MAPE excludes actual = 0
    mape_mask = a != 0

    if mape_mask.sum() > 0:

        mape = (
            np.abs(
                (a[mape_mask] - p[mape_mask])
                / a[mape_mask]
            ).mean()
            * 100
        )

    else:
        mape = np.nan

    mae = np.abs(error).mean()

    rmse = np.sqrt(
        np.mean(error ** 2)
    )

    bias = error.mean()

    return {
        "MAPE (%)": mape,
        "MAE": mae,
        "RMSE": rmse,
        "Bias": bias,
        "Valid Rows": int(valid_mask.sum()),
    }


# ============================================================
# READ FILE
# ============================================================

def read_uploaded_file(uploaded_file):

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):

        try:
            df = pd.read_csv(uploaded_file)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            df = pd.read_csv(
                uploaded_file,
                encoding="latin1",
            )

        return df

    elif file_name.endswith((".xlsx", ".xls")):

        uploaded_file.seek(0)

        excel = pd.ExcelFile(uploaded_file)

        sheet = st.selectbox(
            "Select Excel sheet",
            excel.sheet_names,
        )

        return pd.read_excel(
            uploaded_file,
            sheet_name=sheet,
        )

    else:

        raise ValueError(
            "Unsupported file format. "
            "Please upload CSV or Excel."
        )


# ============================================================
# FILE UPLOAD
# ============================================================

uploaded_file = st.file_uploader(
    "Upload CSV / Excel file",
    type=["csv", "xlsx", "xls"],
)


if uploaded_file is None:

    st.info(
        "Upload a file to start automatic column detection."
    )

    st.stop()


# ============================================================
# LOAD DATA
# ============================================================

try:

    df = read_uploaded_file(uploaded_file)

except Exception as e:

    st.error(
        f"Input preparation failed: {e}"
    )

    st.stop()


# ============================================================
# BASIC CLEANUP
# ============================================================

df = df.copy()

# Remove completely empty columns
df = df.dropna(
    axis=1,
    how="all",
)

# Clean column names
df.columns = [
    str(col).strip()
    for col in df.columns
]


# ============================================================
# BASIC INFORMATION
# ============================================================

st.subheader("Dataset")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Rows",
        f"{len(df):,}",
    )

with col2:
    st.metric(
        "Columns",
        len(df.columns),
    )

with col3:
    st.metric(
        "Numeric Columns",
        sum(
            pd.api.types.is_numeric_dtype(df[c])
            for c in df.columns
        ),
    )

with col4:
    st.metric(
        "Missing Cells",
        f"{df.isna().sum().sum():,}",
    )


# ============================================================
# AUTOMATIC DETECTION
# ============================================================

actual_detected, actual_scores = detect_actual_columns(df)

forecast_detected, forecast_scores = detect_forecast_columns(df)


# ============================================================
# DETECTION UI
# ============================================================

st.subheader("Automatic Column Detection")

left, right = st.columns(2)


with left:

    st.markdown("### Actual Columns")

    if actual_detected:

        for col in actual_detected:

            score = actual_scores[col]

            st.success(
                f"✓ {col}  |  confidence: {score}"
            )

    else:

        st.warning(
            "No Actual columns were automatically detected."
        )


with right:

    st.markdown("### Forecast Columns")

    if forecast_detected:

        for col in forecast_detected:

            score = forecast_scores[col]

            st.success(
                f"✓ {col}  |  confidence: {score}"
            )

    else:

        st.warning(
            "No Forecast columns were automatically detected."
        )


# ============================================================
# MANUAL OVERRIDE
# ============================================================

st.divider()

st.subheader("Column Selection")

st.caption(
    "Automatic selections are pre-filled. You can change them if the "
    "file uses unusual column names."
)


actual_columns = st.multiselect(
    "Actual Generation Columns",
    options=list(df.columns),
    default=actual_detected,
)


forecast_columns = st.multiselect(
    "Forecast / Predicted Columns",
    options=list(df.columns),
    default=forecast_detected,
)


# ============================================================
# VALIDATION
# ============================================================

if not actual_columns:

    st.error(
        "No Actual column selected. Please select at least one Actual column."
    )

    st.stop()


if not forecast_columns:

    st.error(
        "No Forecast column selected. Please select at least one Forecast column."
    )

    st.stop()


# ============================================================
# MAPE OPTIONS
# ============================================================

st.subheader("MAPE Settings")

c1, c2, c3 = st.columns(3)


with c1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Recommended for solar generation because night-time "
            "actual generation is normally zero."
        ),
    )


with c2:

    daylight_threshold = st.number_input(
        "Actual threshold",
        min_value=0.0,
        value=0.0,
        step=1.0,
        help=(
            "Rows below this Actual value can be excluded "
            "from MAPE."
        ),
    )


with c3:

    cap_mape = st.checkbox(
        "Cap individual APE at 1000%",
        value=False,
    )


# ============================================================
# CALCULATE MAPE
# ============================================================

results = []

row_error_df = df.copy()


for forecast_col in forecast_columns:

    for actual_col in actual_columns:

        actual = convert_numeric(
            df[actual_col]
        )

        forecast = convert_numeric(
            df[forecast_col]
        )

        valid_mask = (
            actual.notna()
            & forecast.notna()
            & np.isfinite(actual)
            & np.isfinite(forecast)
        )

        # Threshold
        if daylight_threshold > 0:

            valid_mask &= (
                actual >= daylight_threshold
            )

        # Zero exclusion
        if exclude_zero:

            valid_mask &= (
                actual != 0
            )

        a = actual.loc[valid_mask]
        p = forecast.loc[valid_mask]

        if len(a) == 0:

            mape = np.nan
            mae = np.nan
            rmse = np.nan
            bias = np.nan

        else:

            error = p - a

            absolute_percentage_error = (
                np.abs(error / a) * 100
            )

            if cap_mape:

                absolute_percentage_error = np.minimum(
                    absolute_percentage_error,
                    1000,
                )

            mape = absolute_percentage_error.mean()

            mae = np.abs(error).mean()

            rmse = np.sqrt(
                np.mean(error ** 2)
            )

            bias = error.mean()

        results.append(
            {
                "Forecast Column": forecast_col,
                "Actual Column": actual_col,
                "MAPE (%)": mape,
                "MAE": mae,
                "RMSE": rmse,
                "Bias": bias,
                "Valid Rows": len(a),
            }
        )

        # Row-level APE
        ape_series = pd.Series(
            np.nan,
            index=df.index,
        )

        if len(a) > 0:

            ape_values = (
                np.abs(
                    (a - p)
                    / a
                )
                * 100
            )

            if cap_mape:

                ape_values = np.minimum(
                    ape_values,
                    1000,
                )

            ape_series.loc[a.index] = ape_values

        error_column = (
            f"APE | {forecast_col} vs {actual_col}"
        )

        row_error_df[error_column] = ape_series


# ============================================================
# RESULTS DATAFRAME
# ============================================================

results_df = pd.DataFrame(results)


# ============================================================
# SUMMARY
# ============================================================

st.divider()

st.subheader("MAPE Results")


if results_df.empty:

    st.warning(
        "No MAPE results were generated."
    )

else:

    display_df = results_df.copy()

    for col in [
        "MAPE (%)",
        "MAE",
        "RMSE",
        "Bias",
    ]:

        display_df[col] = display_df[col].round(4)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# BEST MATCH
# ============================================================

valid_results = results_df.dropna(
    subset=["MAPE (%)"]
)


if not valid_results.empty:

    best_row = valid_results.loc[
        valid_results["MAPE (%)"].idxmin()
    ]

    st.subheader("Best Forecast / Actual Combination")

    b1, b2, b3 = st.columns(3)

    with b1:

        st.metric(
            "Forecast",
            best_row["Forecast Column"],
        )

    with b2:

        st.metric(
            "Actual",
            best_row["Actual Column"],
        )

    with b3:

        st.metric(
            "MAPE",
            f"{best_row['MAPE (%)']:.2f}%",
        )


# ============================================================
# DETAILED ROW-LEVEL DATA
# ============================================================

st.divider()

st.subheader("Row-Level MAPE")

st.caption(
    "The original DataFrame is preserved and APE columns are added "
    "for every Forecast vs Actual combination."
)

st.dataframe(
    row_error_df,
    use_container_width=True,
    height=500,
)


# ============================================================
# DOWNLOAD EXCEL
# ============================================================

def create_excel_report(
    original_df,
    results_df,
    row_error_df,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        # Original data
        original_df.to_excel(
            writer,
            sheet_name="Input Data",
            index=False,
        )

        # MAPE summary
        results_df.to_excel(
            writer,
            sheet_name="MAPE Summary",
            index=False,
        )

        # Row-level results
        row_error_df.to_excel(
            writer,
            sheet_name="Row Level APE",
            index=False,
        )

    output.seek(0)

    return output


excel_file = create_excel_report(
    df,
    results_df,
    row_error_df,
)


st.download_button(
    label="📥 Download MAPE Excel Report",
    data=excel_file,
    file_name="MAPE_Analysis_Report.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
)


# ============================================================
# SHOW ALL COLUMNS
# ============================================================

with st.expander("View detected/available columns"):

    column_info = pd.DataFrame(
        {
            "Column": df.columns,
            "Normalized Name": [
                normalize_column_name(c)
                for c in df.columns
            ],
            "Detected as Actual": [
                c in actual_columns
                for c in df.columns
            ],
            "Detected as Forecast": [
                c in forecast_columns
                for c in df.columns
            ],
        }
    )

    st.dataframe(
        column_info,
        use_container_width=True,
        hide_index=True,
    )
