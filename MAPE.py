# ============================================================
# PSS × FORECASTER MAPE MATRIX
# ============================================================
#
# FEATURES
# ------------------------------------------------------------
# • Multiple file uploader
# • One PSS per file
# • Time Block treated as index
# • Automatic Actual-column detection
# • Automatic Forecast-column detection
# • PSS + Forecaster extracted from column names
# • PSS normalization
# • Actual source selection
# • Default priority:
#       SEMS
#       Green Gen-Meter
#       Green Gen-SCADA
# • MAPE calculation
# • PSS × Forecaster matrix
# • Green → Yellow → Red highlighting
# • Excel download
#
# EXAMPLE FORECAST COLUMN:
#
# 66 KV Bhulleriyan_ALL12.5_F1
#
# PSS        = 66 KV Bhulleriyan
# Forecaster = ALL12.5_F1
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
# PAGE CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TITLE
# ============================================================

st.title("📊 PSS × Forecaster MAPE Matrix")

st.caption(
    "Upload multiple files and calculate MAPE for each PSS × Forecaster combination."
)


# ============================================================
# CONSTANTS
# ============================================================

INDEX_COLUMN = "Time Block"


# ============================================================
# ACTUAL COLUMN TYPES
# ============================================================

ACTUAL_TYPES = {
    "SEMS": "sems",
    "Green Gen-Meter": "green gen meter",
    "Green Gen-SCADA": "green gen scada",
}


# ============================================================
# ACTUAL PRIORITY
# ============================================================

DEFAULT_PRIORITY = [
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
    Normalize PSS names.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    are treated as the same PSS.
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

    text = text.lower()

    # Remove spaces
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # Normalize KV → K
    text = text.replace(
        "kv",
        "k",
    )

    return text.upper()


# ============================================================
# DISPLAY PSS
# ============================================================

def clean_pss_display(value):
    """
    Creates a clean display name.
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
    Safely convert data to numeric.
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

    # Remove empty rows
    df = df.dropna(
        axis=0,
        how="all",
    )

    # Remove empty columns
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

    found_column = None

    target = normalize_text(
        INDEX_COLUMN
    )

    for column in df.columns:

        if normalize_text(
            column
        ) == target:

            found_column = column

            break

    if found_column is None:

        return df, None

    df = df.set_index(
        found_column,
        drop=True,
    )

    return df, found_column


# ============================================================
# FIND ACTUAL COLUMN
# ============================================================

def detect_actual_column(
    df,
    actual_type,
):
    """
    Find the actual column corresponding to:

        SEMS
        Green Gen-Meter
        Green Gen-SCADA
    """

    target = ACTUAL_TYPES[
        actual_type
    ]

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
    # Validate numeric candidates
    # --------------------------------------------------------

    for column in candidates:

        numeric = to_numeric(
            df[column]
        )

        if numeric.notna().sum() > 0:

            return column

    return None


# ============================================================
# DETECT ALL ACTUAL COLUMNS
# ============================================================

def detect_actual_columns(df):

    result = {}

    for actual_type in ACTUAL_TYPES:

        column = detect_actual_column(
            df,
            actual_type,
        )

        result[
            actual_type
        ] = column

    return result


# ============================================================
# PARSE FORECAST COLUMN
# ============================================================

def parse_forecast_column(
    column_name
):
    """
    Split ONLY at the first underscore.

    Example:

        66 KV Bhulleriyan_ALL12.5_F1

    becomes:

        PSS        = 66 KV Bhulleriyan
        Forecaster = ALL12.5_F1
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

    if not pss or not forecaster:

        return None, None

    return (
        pss,
        forecaster,
    )


# ============================================================
# DETECT FORECAST COLUMNS
# ============================================================

def detect_forecast_columns(df):

    forecasts = []

    for column in df.columns:

        # ----------------------------------------------------
        # Parse header
        # ----------------------------------------------------

        pss, forecaster = (
            parse_forecast_column(
                column
            )
        )

        if pss is None:

            continue

        # ----------------------------------------------------
        # Numeric validation
        # ----------------------------------------------------

        numeric = to_numeric(
            df[column]
        )

        if numeric.notna().sum() == 0:

            continue

        forecasts.append(
            {
                "Column": column,
                "PSS": pss,
                "Normalized PSS": normalize_pss(
                    pss
                ),
                "Forecaster": forecaster,
            }
        )

    return pd.DataFrame(
        forecasts
    )


# ============================================================
# FIND FILE PSS
# ============================================================

def identify_file_pss(
    forecast_df
):
    """
    Every uploaded file contains one PSS.

    Find the dominant normalized PSS.
    """

    if forecast_df.empty:

        return None, None

    counts = (
        forecast_df[
            "Normalized PSS"
        ]
        .value_counts()
    )

    if counts.empty:

        return None, None

    normalized_pss = (
        counts.index[0]
    )

    candidates = forecast_df[
        forecast_df[
            "Normalized PSS"
        ]
        == normalized_pss
    ]

    display_counts = (
        candidates[
            "PSS"
        ]
        .apply(
            clean_pss_display
        )
        .value_counts()
    )

    display_name = (
        display_counts.index[0]
    )

    return (
        display_name,
        normalized_pss,
    )


# ============================================================
# SELECT ACTUAL COLUMN
# ============================================================

def select_actual_column(
    actual_columns,
    actual_mode,
):
    """
    Select Actual according to user preference.

    Auto:
        SEMS
        Green Gen-Meter
        Green Gen-SCADA

    Manual:
        User-selected source only.
    """

    # --------------------------------------------------------
    # AUTO
    # --------------------------------------------------------

    if actual_mode == "Auto Priority":

        for actual_type in DEFAULT_PRIORITY:

            column = actual_columns.get(
                actual_type
            )

            if column is not None:

                return (
                    actual_type,
                    column,
                )

        return None, None

    # --------------------------------------------------------
    # MANUAL
    # --------------------------------------------------------

    selected_column = actual_columns.get(
        actual_mode
    )

    if selected_column is None:

        return None, None

    return (
        actual_mode,
        selected_column,
    )


# ============================================================
# CALCULATE MAPE
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
    # Minimum actual threshold
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
# INPUT SECTION
# ============================================================

st.subheader(
    "📂 Input Files"
)

uploaded_files = st.file_uploader(
    "Upload multiple PSS files",
    type=[
        "xlsx",
        "xls",
        "csv",
    ],
    accept_multiple_files=True,
)


# ============================================================
# STOP IF NO FILES
# ============================================================

if not uploaded_files:

    st.info(
        "Please upload one or more files."
    )

    st.stop()


# ============================================================
# SETTINGS
# ============================================================

st.subheader(
    "⚙️ Actual Data Selection"
)

actual_mode = st.radio(
    "Actual generation source",
    options=[
        "Auto Priority",
        "SEMS",
        "Green Gen-Meter",
        "Green Gen-SCADA",
    ],
    index=0,
    horizontal=True,
    help=(
        "Auto Priority selects SEMS first, then "
        "Green Gen-Meter, then Green Gen-SCADA "
        "for each file independently."
    ),
)


# ============================================================
# MAPE SETTINGS
# ============================================================

col1, col2 = st.columns(2)

with col1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
        help=(
            "Recommended for solar generation MAPE "
            "because zero-generation night blocks "
            "can make MAPE invalid."
        ),
    )

with col2:

    minimum_actual = st.number_input(
        "Minimum Actual Value",
        min_value=0.0,
        value=0.0,
        step=1.0,
        help=(
            "Optional minimum Actual value used "
            "for MAPE calculation."
        ),
    )


# ============================================================
# CALCULATE
# ============================================================

calculate = st.button(
    "🚀 Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not calculate:

    st.stop()


# ============================================================
# RESULT STORAGE
# ============================================================

all_results = []

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

for file_index, uploaded_file in enumerate(
    uploaded_files
):

    status.write(
        f"Processing: {uploaded_file.name}"
    )

    try:

        # ====================================================
        # READ FILE
        # ====================================================

        df = read_uploaded_file(
            uploaded_file
        )

        df = clean_dataframe(
            df
        )

        if df.empty:

            raise ValueError(
                "The file contains no usable data."
            )

        # ====================================================
        # TIME BLOCK INDEX
        # ====================================================

        df, index_column = (
            prepare_index(
                df
            )
        )

        if index_column is None:

            raise ValueError(
                "Time Block column not found."
            )

        # ====================================================
        # ACTUAL DETECTION
        # ====================================================

        actual_columns = (
            detect_actual_columns(
                df
            )
        )

        # ====================================================
        # SELECT ACTUAL
        # ====================================================

        (
            selected_actual_type,
            actual_column,
        ) = select_actual_column(
            actual_columns,
            actual_mode,
        )

        if actual_column is None:

            available_actuals = [
                key
                for key, value
                in actual_columns.items()
                if value is not None
            ]

            if actual_mode == "Auto Priority":

                raise ValueError(
                    "No Actual column found. "
                    "Expected SEMS, Green Gen-Meter "
                    "or Green Gen-SCADA."
                )

            raise ValueError(
                f"Selected Actual source "
                f"'{actual_mode}' was not found. "
                f"Available Actual sources: "
                f"{available_actuals}"
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

        (
            pss_name,
            normalized_pss,
        ) = identify_file_pss(
            forecast_df
        )

        if pss_name is None:

            raise ValueError(
                "Could not identify PSS "
                "from forecast column names."
            )

        # ====================================================
        # KEEP ONLY THIS FILE'S PSS
        # ====================================================

        forecast_df = forecast_df[
            forecast_df[
                "Normalized PSS"
            ]
            == normalized_pss
        ].copy()

        if forecast_df.empty:

            raise ValueError(
                f"No forecasts found for PSS "
                f"{pss_name}."
            )

        # ====================================================
        # CALCULATE EACH FORECASTER
        # ====================================================

        actual_series = df[
            actual_column
        ]

        for _, forecast_info in (
            forecast_df.iterrows()
        ):

            forecast_column = (
                forecast_info[
                    "Column"
                ]
            )

            forecaster = (
                forecast_info[
                    "Forecaster"
                ]
            )

            # -----------------------------------------------
            # MAPE
            # -----------------------------------------------

            mape = calculate_mape(
                actual=actual_series,
                forecast=df[
                    forecast_column
                ],
                exclude_zero=exclude_zero,
                minimum_actual=minimum_actual,
            )

            all_results.append(
                {
                    "PSS": pss_name,
                    "Forecaster": forecaster,
                    "MAPE": mape,
                }
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
                file_index + 1
            )
            / len(uploaded_files)
            * 100
        )
    )


status.empty()


# ============================================================
# ERROR HANDLING
# ============================================================

if processing_errors:

    error_text = "\n\n".join(
        [
            f"**{item['File']}**: {item['Error']}"
            for item in processing_errors
        ]
    )

    st.error(
        error_text
    )


# ============================================================
# NO RESULTS
# ============================================================

if not all_results:

    st.error(
        "No MAPE results could be calculated."
    )

    st.stop()


# ============================================================
# RESULT DATAFRAME
# ============================================================

result_df = pd.DataFrame(
    all_results
)


# ============================================================
# HANDLE DUPLICATE PSS + FORECASTER
# ============================================================
#
# If the same PSS/Forecaster appears in multiple files,
# calculate the average MAPE.
#

result_df = (
    result_df
    .groupby(
        [
            "PSS",
            "Forecaster",
        ],
        as_index=False,
    )[
        "MAPE"
    ]
    .mean()
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
# SORT FORECASTERS
# ============================================================

mape_matrix = (
    mape_matrix
    .sort_index(axis=1)
)


# ============================================================
# FORMAT VALUES
# ============================================================

mape_matrix = (
    mape_matrix.round(2)
)


# ============================================================
# COLOR FUNCTION
# ============================================================

def color_mape(
    value,
    min_value,
    max_value,
):
    """
    Green = Low MAPE
    Yellow = Medium MAPE
    Red = High MAPE
    """

    if pd.isna(value):

        return ""

    # --------------------------------------------------------
    # Same value everywhere
    # --------------------------------------------------------

    if max_value == min_value:

        ratio = 0.0

    else:

        ratio = (
            value - min_value
        ) / (
            max_value - min_value
        )

    ratio = max(
        0.0,
        min(
            1.0,
            ratio,
        ),
    )

    # --------------------------------------------------------
    # Green → Yellow → Red
    # --------------------------------------------------------

    if ratio <= 0.5:

        # Green to Yellow
        local = ratio * 2

        r = int(
            144
            + (
                255 - 144
            )
            * local
        )

        g = 238

        b = int(
            144
            * (
                1 - local
            )
        )

    else:

        # Yellow to Red
        local = (
            ratio - 0.5
        ) * 2

        r = 255

        g = int(
            238
            * (
                1 - local
            )
        )

        b = 0

    return (
        f"background-color: "
        f"rgb({r}, {g}, {b});"
        f"color: black;"
    )


# ============================================================
# GLOBAL MIN/MAX
# ============================================================

numeric_values = (
    mape_matrix
    .to_numpy()
    .flatten()
)

numeric_values = numeric_values[
    ~pd.isna(
        numeric_values
    )
]

if len(numeric_values) > 0:

    global_min = float(
        np.min(
            numeric_values
        )
    )

    global_max = float(
        np.max(
            numeric_values
        )
    )

else:

    global_min = 0.0
    global_max = 1.0


# ============================================================
# STYLE MATRIX
# ============================================================

styled_matrix = (
    mape_matrix
    .style
    .format(
        "{:.2f}",
        na_rep="-",
    )
    .applymap(
        lambda value: color_mape(
            value,
            global_min,
            global_max,
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
# EXCEL EXPORT
# ============================================================

output = io.BytesIO()

with pd.ExcelWriter(
    output,
    engine="openpyxl",
) as writer:

    mape_matrix.to_excel(
        writer,
        sheet_name="MAPE Matrix",
    )

output.seek(0)


# ============================================================
# DOWNLOAD
# ============================================================

st.download_button(
    label="📥 Download MAPE Matrix",
    data=output,
    file_name="PSS_Forecaster_MAPE_Matrix.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True,
)
