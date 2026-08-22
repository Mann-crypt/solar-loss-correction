# ============================================================
# PSS × FORECASTER MAPE MATRIX
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
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):

    if value is None or pd.isna(value):
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

    if value is None or pd.isna(value):
        return ""

    text = str(value).strip()

    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = text.lower()

    # Remove spaces
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # 66 KV -> 66 K
    text = text.replace(
        "kv",
        "k",
    )

    return text.upper()


# ============================================================
# DISPLAY PSS
# ============================================================

def clean_pss_name(value):

    if value is None or pd.isna(value):
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
        "Unsupported file format."
    )


# ============================================================
# CLEAN DATAFRAME
# ============================================================

def clean_dataframe(df):

    df = df.copy()

    df = df.dropna(
        axis=0,
        how="all",
    )

    df = df.dropna(
        axis=1,
        how="all",
    )

    df.columns = [
        str(column).strip()
        for column in df.columns
    ]

    return df


# ============================================================
# SET TIME BLOCK INDEX
# ============================================================

def set_time_block_index(df):

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

    return df.set_index(
        time_column,
        drop=True,
    )


# ============================================================
# ACTUAL COLUMN DETECTION
# ============================================================

def find_actual_column(
    df,
    actual_type,
):

    candidates = []

    for column in df.columns:

        normalized = normalize_text(
            column
        )

        if actual_type == "SEMS":

            if "sems" in normalized:
                candidates.append(
                    column
                )

        elif actual_type == "Green Gen-Meter":

            if (
                "green gen meter"
                in normalized
            ):
                candidates.append(
                    column
                )

        elif actual_type == "Green Gen-SCADA":

            if (
                "green gen scada"
                in normalized
            ):
                candidates.append(
                    column
                )

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

    return {
        "SEMS": find_actual_column(
            df,
            "SEMS",
        ),
        "Green Gen-Meter": find_actual_column(
            df,
            "Green Gen-Meter",
        ),
        "Green Gen-SCADA": find_actual_column(
            df,
            "Green Gen-SCADA",
        ),
    }


# ============================================================
# FORECAST HEADER PARSER
# ============================================================

def parse_forecast_header(
    column_name
):

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

    if not pss or not forecaster:

        return None, None

    return (
        pss,
        forecaster,
    )


# ============================================================
# FORECAST DETECTION
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

def identify_pss(forecasts):

    if not forecasts:

        return None, None

    counts = {}

    for item in forecasts:

        key = item[
            "normalized_pss"
        ]

        counts[key] = (
            counts.get(
                key,
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

        name = clean_pss_name(
            item["pss"]
        )

        display_names[name] = (
            display_names.get(
                name,
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

        return None, None

    column = actuals.get(
        mode
    )

    if column is None:

        return None, None

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

    if minimum_actual > 0:

        mask &= (
            actual.abs()
            >= minimum_actual
        )

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

    ape = (
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
        ape.mean()
    )


# ============================================================
# MAPE COLOR
# ============================================================

def mape_color(
    value,
    minimum,
    maximum,
):

    if pd.isna(value):

        return ""

    value = float(value)

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

    # Green -> Yellow
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

    # Yellow -> Red
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
        "background-color:"
        f"rgb({red},{green},{blue});"
        "color:black;"
    )


# ============================================================
# UI
# ============================================================

st.title(
    "📊 PSS × Forecaster MAPE Matrix"
)

st.caption(
    "Upload multiple files. Each file should contain one PSS."
)


# ============================================================
# FILE UPLOAD
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


if not uploaded_files:

    st.info(
        "Upload files to begin."
    )

    st.stop()


# ============================================================
# ACTUAL SELECTION
# ============================================================

actual_mode = st.radio(
    "Actual Data",
    [
        "Auto Priority",
        "SEMS",
        "Green Gen-Meter",
        "Green Gen-SCADA",
    ],
    index=0,
    horizontal=True,
)


if actual_mode == "Auto Priority":

    st.caption(
        "Priority: SEMS → Green Gen-Meter → Green Gen-SCADA"
    )


# ============================================================
# MAPE OPTIONS
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
# RUN
# ============================================================

run = st.button(
    "🚀 Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not run:

    st.stop()


# ============================================================
# PROCESSING STATUS
# ============================================================

st.subheader(
    "📂 File Processing"
)

status_container = st.container()

results = []

processing_status = []


# ============================================================
# PROCESS FILES
# ============================================================

progress = st.progress(
    0
)

for file_number, uploaded_file in enumerate(
    uploaded_files
):

    filename = uploaded_file.name

    # --------------------------------------------------------
    # INITIAL STATUS
    # --------------------------------------------------------

    status_container.write(
        f"⏳ **Reading:** `{filename}`"
    )

    try:

        # ====================================================
        # READ FILE
        # ====================================================

        df = read_file(
            uploaded_file
        )

        df = clean_dataframe(
            df
        )

        # ====================================================
        # TIME BLOCK
        # ====================================================

        df = set_time_block_index(
            df
        )

        # ====================================================
        # ACTUAL DETECTION
        # ====================================================

        actuals = detect_actuals(
            df
        )

        # ====================================================
        # ACTUAL SELECTION
        # ====================================================

        (
            actual_source,
            actual_column,
        ) = select_actual(
            actuals,
            actual_mode,
        )

        if actual_column is None:

            raise ValueError(
                "No suitable Actual column found."
            )

        # ====================================================
        # FORECAST DETECTION
        # ====================================================

        forecasts = detect_forecasts(
            df
        )

        if not forecasts:

            raise ValueError(
                "No Forecast columns detected."
            )

        # ====================================================
        # PSS
        # ====================================================

        (
            pss_name,
            normalized_pss,
        ) = identify_pss(
            forecasts
        )

        if pss_name is None:

            raise ValueError(
                "PSS not found."
            )

        # ====================================================
        # KEEP ONLY THIS PSS
        # ====================================================

        forecasts = [
            item
            for item in forecasts
            if item[
                "normalized_pss"
            ]
            == normalized_pss
        ]

        if not forecasts:

            raise ValueError(
                "PSS found but no Forecast "
                "columns belong to it."
            )

        # ====================================================
        # CALCULATE
        # ====================================================

        actual_series = df[
            actual_column
        ]

        valid_forecasts = 0

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

            if not pd.isna(mape):

                valid_forecasts += 1

                results.append(
                    {
                        "PSS": pss_name,
                        "Forecaster": forecaster,
                        "MAPE": mape,
                    }
                )

        # ====================================================
        # SUCCESS STATUS
        # ====================================================

        processing_status.append(
            {
                "File": filename,
                "Status": "Success",
                "PSS": pss_name,
                "Actual Used": actual_source,
                "Forecasts Found": len(
                    forecasts
                ),
                "MAPE Calculated": valid_forecasts,
                "Message": "PSS found",
            }
        )

    except Exception as error:

        processing_status.append(
            {
                "File": filename,
                "Status": "Error",
                "PSS": "-",
                "Actual Used": "-",
                "Forecasts Found": 0,
                "MAPE Calculated": 0,
                "Message": str(error),
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


# ============================================================
# SHOW PROCESSING STATUS
# ============================================================

progress.empty()

st.dataframe(
    pd.DataFrame(
        processing_status
    ),
    use_container_width=True,
    hide_index=True,
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
# RESULT DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    results
)


# ============================================================
# MULTIPLE FILES WITH SAME PSS
# ============================================================
#
# If same PSS + Forecaster occurs in multiple files,
# average their MAPE.
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
# MATRIX
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
# COLOR RANGE
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
# STYLE
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
    "📊 PSS × Forecaster MAPE Matrix"
)

st.dataframe(
    styled_matrix,
    use_container_width=True,
)


# ============================================================
# DOWNLOAD
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

st.download_button(
    "📥 Download MAPE Matrix",
    data=excel_output,
    file_name="PSS_Forecaster_MAPE_Matrix.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True,
)
