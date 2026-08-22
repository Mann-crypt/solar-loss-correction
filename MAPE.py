# ============================================================
# STREAMLIT APP
# MULTIPLE FILE PSS + FORECASTER MAPE ANALYSIS
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
# TITLE
# ============================================================

st.title("📊 PSS × Forecaster MAPE Analysis")

st.write(
    "Upload multiple files. PSS and Forecaster names are automatically "
    "identified from each filename."
)


# ============================================================
# FILE NAME PARSER
# ============================================================

def parse_file_name(file_name):
    """
    Filename rule:

        PSS_Forecaster.xlsx

    Everything before the FIRST underscore = PSS
    Everything after the FIRST underscore = Forecaster

    Example:
        66 KV   Bhulleriyan_ALL12.5_F1.xlsx

    PSS:
        66 KV   Bhulleriyan

    Forecaster:
        ALL12.5_F1
    """

    # Remove extension
    base_name = re.sub(
        r"\.(xlsx|xls|csv)$",
        "",
        file_name,
        flags=re.IGNORECASE,
    ).strip()

    # Split only at FIRST underscore
    parts = base_name.split("_", 1)

    if len(parts) != 2:

        return (
            base_name,
            "Unknown",
        )

    pss_name = parts[0].strip()
    forecaster_name = parts[1].strip()

    return (
        pss_name,
        forecaster_name,
    )


# ============================================================
# COLUMN NORMALIZATION
# ============================================================

def normalize_column_name(col):

    col = str(col).strip().lower()

    col = re.sub(
        r"[_\-/]+",
        " ",
        col,
    )

    col = re.sub(
        r"[^a-z0-9 ]+",
        " ",
        col,
    )

    col = re.sub(
        r"\s+",
        " ",
        col,
    ).strip()

    return col


# ============================================================
# ACTUAL COLUMN DETECTION
# ============================================================

ACTUAL_PATTERNS = [

    ["actual"],

    ["actual", "power"],

    ["actual", "generation"],

    ["actual", "gen"],

    ["green", "gen"],

    ["green", "generation"],

    ["green", "gen", "meter"],

    ["green", "gen", "scada"],

    ["green", "generation", "meter"],

    ["green", "generation", "scada"],

    ["gen", "meter"],

    ["gen", "scada"],

    ["generation", "meter"],

    ["generation", "scada"],

    ["sems"],
]


def detect_actual_columns(df):

    detected = []
    scores = {}

    for col in df.columns:

        normalized = normalize_column_name(col)

        words = normalized.split()

        score = 0

        # ----------------------------------------------------
        # SEMS
        # ----------------------------------------------------

        if "sems" in words:
            score += 100

        # ----------------------------------------------------
        # ACTUAL
        # ----------------------------------------------------

        if "actual" in words:
            score += 100

        # ----------------------------------------------------
        # GREEN GENERATION
        # ----------------------------------------------------

        if "green" in words and "gen" in words:
            score += 90

        if (
            "green" in words
            and "generation" in words
        ):
            score += 90

        # ----------------------------------------------------
        # METER / SCADA
        # ----------------------------------------------------

        if "meter" in words:
            score += 40

        if "scada" in words:
            score += 40

        # ----------------------------------------------------
        # GENERATION
        # ----------------------------------------------------

        if "generation" in words:
            score += 30

        if "gen" in words:
            score += 30

        if score > 0:

            detected.append(col)
            scores[col] = score

    # Highest confidence first

    detected = sorted(
        detected,
        key=lambda x: scores[x],
        reverse=True,
    )

    return detected, scores


# ============================================================
# FORECAST COLUMN DETECTION
# ============================================================

FORECAST_KEYWORDS = [
    "forecast",
    "forecasted",
    "predicted",
    "prediction",
    "fcst",
]


def detect_forecast_columns(df):

    detected = []
    scores = {}

    for col in df.columns:

        normalized = normalize_column_name(col)

        words = normalized.split()

        score = 0

        for keyword in FORECAST_KEYWORDS:

            if keyword in words:

                score += 100

        if (
            "forecast" in normalized
        ):

            score += 50

        if (
            "predicted" in normalized
        ):

            score += 50

        if score > 0:

            detected.append(col)
            scores[col] = score

    detected = sorted(
        detected,
        key=lambda x: scores[x],
        reverse=True,
    )

    return detected, scores


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
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.strip(),
        errors="coerce",
    )


# ============================================================
# MAPE
# ============================================================

def calculate_mape(
    actual,
    forecast,
    exclude_zero=True,
    threshold=0.0,
):

    actual = to_numeric(actual)
    forecast = to_numeric(forecast)

    mask = (
        actual.notna()
        & forecast.notna()
        & np.isfinite(actual)
        & np.isfinite(forecast)
    )

    # Actual threshold
    if threshold > 0:

        mask &= (
            actual >= threshold
        )

    # Exclude zero actual
    if exclude_zero:

        mask &= (
            actual != 0
        )

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

    error = f - a

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

        "MAPE (%)": mape,

        "MAE": mae,

        "RMSE": rmse,

        "Bias": bias,

        "Valid Rows": int(mask.sum()),
    }


# ============================================================
# READ FILE
# ============================================================

def read_file(uploaded_file):

    file_name = uploaded_file.name.lower()

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

    elif file_name.endswith(
        (".xlsx", ".xls")
    ):

        uploaded_file.seek(0)

        return pd.read_excel(
            uploaded_file
        )

    else:

        raise ValueError(
            "Unsupported file format."
        )


# ============================================================
# MULTIPLE FILE UPLOADER
# ============================================================

uploaded_files = st.file_uploader(
    "Upload Multiple PSS Forecaster Files",
    type=[
        "csv",
        "xlsx",
        "xls",
    ],
    accept_multiple_files=True,
)


if not uploaded_files:

    st.info(
        "Upload one or more files to start."
    )

    st.stop()


# ============================================================
# MAPE SETTINGS
# ============================================================

st.subheader("MAPE Settings")

c1, c2 = st.columns(2)

with c1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Recommended for solar generation because "
            "night-time generation is normally zero."
        ),
    )


with c2:

    actual_threshold = st.number_input(
        "Minimum Actual Generation",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )


# ============================================================
# FILE INFORMATION
# ============================================================

file_info = []

for uploaded_file in uploaded_files:

    pss_name, forecaster_name = (
        parse_file_name(
            uploaded_file.name
        )
    )

    file_info.append(
        {
            "File Name": uploaded_file.name,
            "PSS": pss_name,
            "Forecaster": forecaster_name,
        }
    )


file_info_df = pd.DataFrame(
    file_info
)


# ============================================================
# SHOW FILE MAPPING
# ============================================================

st.subheader(
    "Detected PSS / Forecaster Mapping"
)

st.dataframe(
    file_info_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# MANUAL MAPPING OPTION
# ============================================================

with st.expander(
    "Edit PSS / Forecaster names"
):

    st.caption(
        "Change these only if a filename does not follow "
        "PSS_Forecaster format."
    )

    editable_file_info = st.data_editor(
        file_info_df,
        use_container_width=True,
        hide_index=True,
        disabled=[
            "File Name"
        ],
    )


# ============================================================
# PROCESS FILES
# ============================================================

all_results = []
all_row_data = []

processing_errors = []


for file_index, uploaded_file in enumerate(
    uploaded_files
):

    try:

        # ----------------------------------------------------
        # PSS / FORECASTER
        # ----------------------------------------------------

        original_pss, original_forecaster = (
            parse_file_name(
                uploaded_file.name
            )
        )

        # Get edited mapping
        pss_name = editable_file_info.loc[
            file_index,
            "PSS"
        ]

        forecaster_name = editable_file_info.loc[
            file_index,
            "Forecaster"
        ]

        # ----------------------------------------------------
        # READ FILE
        # ----------------------------------------------------

        data = read_file(
            uploaded_file
        )

        data = data.copy()

        # Remove empty columns
        data = data.dropna(
            axis=1,
            how="all",
        )

        # Clean column names
        data.columns = [
            str(c).strip()
            for c in data.columns
        ]

        # ----------------------------------------------------
        # DETECT ACTUAL
        # ----------------------------------------------------

        actual_columns, actual_scores = (
            detect_actual_columns(
                data
            )
        )

        # ----------------------------------------------------
        # DETECT FORECAST
        # ----------------------------------------------------

        forecast_columns, forecast_scores = (
            detect_forecast_columns(
                data
            )
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not actual_columns:

            raise ValueError(
                "No Actual generation column detected."
            )

        if not forecast_columns:

            raise ValueError(
                "No Forecast column detected."
            )

        # ----------------------------------------------------
        # MAPE
        # ----------------------------------------------------

        for forecast_col in forecast_columns:

            for actual_col in actual_columns:

                metrics = calculate_mape(
                    data[actual_col],
                    data[forecast_col],
                    exclude_zero=exclude_zero,
                    threshold=actual_threshold,
                )

                all_results.append(
                    {
                        "PSS": pss_name,
                        "Forecaster": forecaster_name,
                        "File": uploaded_file.name,
                        "Forecast Column": forecast_col,
                        "Actual Column": actual_col,
                        **metrics,
                    }
                )

                # ------------------------------------------------
                # ROW LEVEL DATA
                # ------------------------------------------------

                row_df = data.copy()

                row_df.insert(
                    0,
                    "PSS",
                    pss_name,
                )

                row_df.insert(
                    1,
                    "Forecaster",
                    forecaster_name,
                )

                row_df.insert(
                    2,
                    "File",
                    uploaded_file.name,
                )

                actual_numeric = to_numeric(
                    data[actual_col]
                )

                forecast_numeric = to_numeric(
                    data[forecast_col]
                )

                ape = pd.Series(
                    np.nan,
                    index=data.index,
                )

                valid = (
                    actual_numeric.notna()
                    & forecast_numeric.notna()
                    & np.isfinite(actual_numeric)
                    & np.isfinite(forecast_numeric)
                )

                if exclude_zero:

                    valid &= (
                        actual_numeric != 0
                    )

                if actual_threshold > 0:

                    valid &= (
                        actual_numeric
                        >= actual_threshold
                    )

                ape.loc[valid] = (
                    np.abs(
                        (
                            actual_numeric.loc[valid]
                            - forecast_numeric.loc[valid]
                        )
                        / actual_numeric.loc[valid]
                    )
                    * 100
                )

                row_df[
                    "APE (%)"
                ] = ape

                row_df[
                    "Actual Column"
                ] = actual_col

                row_df[
                    "Forecast Column"
                ] = forecast_col

                all_row_data.append(
                    row_df
                )

    except Exception as e:

        processing_errors.append(
            {
                "File": uploaded_file.name,
                "Error": str(e),
            }
        )


# ============================================================
# RESULTS
# ============================================================

results_df = pd.DataFrame(
    all_results
)


# ============================================================
# ERRORS
# ============================================================

if processing_errors:

    st.warning(
        f"{len(processing_errors)} file(s) "
        "could not be processed."
    )

    st.dataframe(
        pd.DataFrame(
            processing_errors
        ),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# MAPE SUMMARY
# ============================================================

st.divider()

st.subheader(
    "PSS × Forecaster MAPE Summary"
)


if results_df.empty:

    st.error(
        "No MAPE results were generated."
    )

    st.stop()


# Round values for display
display_results = results_df.copy()

for column in [
    "MAPE (%)",
    "MAE",
    "RMSE",
    "Bias",
]:

    display_results[column] = (
        display_results[column]
        .round(4)
    )


st.dataframe(
    display_results,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# PSS × FORECASTER SUMMARY
# ============================================================

st.subheader(
    "Overall Forecaster MAPE"
)


overall_summary = (
    results_df
    .groupby(
        [
            "PSS",
            "Forecaster",
        ],
        as_index=False,
    )
    .agg(
        MAPE=("MAPE (%)", "mean"),
        MAE=("MAE", "mean"),
        RMSE=("RMSE", "mean"),
        Bias=("Bias", "mean"),
        Comparisons=("Actual Column", "count"),
    )
)


overall_summary = (
    overall_summary
    .sort_values(
        [
            "PSS",
            "MAPE",
        ]
    )
)


overall_summary[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
] = overall_summary[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
].round(4)


st.dataframe(
    overall_summary,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# BEST FORECASTER PER PSS
# ============================================================

st.subheader(
    "Best Forecaster for Each PSS"
)


best_forecaster = (
    overall_summary
    .sort_values(
        "MAPE"
    )
    .groupby(
        "PSS",
        as_index=False,
    )
    .first()
)


best_forecaster[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
] = best_forecaster[
    [
        "MAPE",
        "MAE",
        "RMSE",
        "Bias",
    ]
].round(4)


st.dataframe(
    best_forecaster,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# ROW LEVEL DATA
# ============================================================

if all_row_data:

    st.divider()

    st.subheader(
        "Row-Level APE"
    )

    row_level_df = pd.concat(
        all_row_data,
        ignore_index=True,
    )

    st.dataframe(
        row_level_df,
        use_container_width=True,
        height=500,
    )


# ============================================================
# EXCEL REPORT
# ============================================================

def create_excel_report(
    file_mapping,
    results,
    overall,
    best,
    row_level=None,
):

    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        file_mapping.to_excel(
            writer,
            sheet_name="File Mapping",
            index=False,
        )

        results.to_excel(
            writer,
            sheet_name="MAPE Detail",
            index=False,
        )

        overall.to_excel(
            writer,
            sheet_name="PSS Forecaster Summary",
            index=False,
        )

        best.to_excel(
            writer,
            sheet_name="Best Forecaster",
            index=False,
        )

        if row_level is not None:

            row_level.to_excel(
                writer,
                sheet_name="Row Level APE",
                index=False,
            )

    output.seek(0)

    return output


report = create_excel_report(
    editable_file_info,
    results_df,
    overall_summary,
    best_forecaster,
    (
        pd.concat(
            all_row_data,
            ignore_index=True,
        )
        if all_row_data
        else None
    ),
)


st.download_button(
    "📥 Download Complete MAPE Report",
    data=report,
    file_name="PSS_Forecaster_MAPE_Report.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
)


# ============================================================
# COLUMN DETECTION DETAILS
# ============================================================

with st.expander(
    "View column detection details"
):

    detection_rows = []

    for uploaded_file in uploaded_files:

        try:

            pss, forecaster = parse_file_name(
                uploaded_file.name
            )

            temp_df = read_file(
                uploaded_file
            )

            temp_df.columns = [
                str(c).strip()
                for c in temp_df.columns
            ]

            actuals, actual_scores = (
                detect_actual_columns(
                    temp_df
                )
            )

            forecasts, forecast_scores = (
                detect_forecast_columns(
                    temp_df
                )
            )

            detection_rows.append(
                {
                    "PSS": pss,
                    "Forecaster": forecaster,
                    "File": uploaded_file.name,
                    "Actual Columns": ", ".join(
                        actuals
                    ),
                    "Forecast Columns": ", ".join(
                        forecasts
                    ),
                }
            )

        except Exception as e:

            detection_rows.append(
                {
                    "PSS": pss,
                    "Forecaster": forecaster,
                    "File": uploaded_file.name,
                    "Actual Columns": "ERROR",
                    "Forecast Columns": str(e),
                }
            )

    st.dataframe(
        pd.DataFrame(
            detection_rows
        ),
        use_container_width=True,
        hide_index=True,
    )
