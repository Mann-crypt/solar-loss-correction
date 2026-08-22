# ============================================================
# PSS × FORECASTER MAPE MATRIX
# ============================================================
#
# MULTIPLE FILE UPLOADER
#
# EACH FILE = ONE PSS
#
# ACTUAL DATA:
#   SEMS
#   Green Gen-Meter
#   Green Gen-SCADA
#
# DEFAULT PRIORITY:
#   SEMS
#   ↓
#   Green Gen-Meter
#   ↓
#   Green Gen-SCADA
#
# BUT USER CAN OVERRIDE ACTUAL DATA
# INDIVIDUALLY FOR EVERY FILE.
#
#
# FORECAST COLUMN EXAMPLE:
#
# 66 KV Bhulleriyan_ALL12.5_F1
#
# PSS        = 66 KV Bhulleriyan
# Forecaster = ALL12.5_F1
#
#
# OUTPUT:
#
# PSS × Forecaster MAPE Matrix
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


ACTUAL_DISPLAY_NAMES = {
    "SEMS": "SEMS",
    "Green Gen-Meter": "Green Gen-Meter",
    "Green Gen-SCADA": "Green Gen-SCADA",
}


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    General text normalization.

    Example:

    Green Gen-Meter (OPC)
        ->
    green gen meter opc
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

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
    Makes PSS naming consistent.

    Examples:

        66 KV Bhulleriyan
        66 kV Bhulleriyan
        66K

    are treated as the same PSS.
    """

    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

    text = str(value).strip()

    # Remove HTML breaks if present
    text = re.sub(
        r"<br\s*/?>",
        " ",
        text,
        flags=re.IGNORECASE,
    )

    text = text.lower()

    # Remove all whitespace
    text = re.sub(
        r"\s+",
        "",
        text,
    )

    # KV and kV become K
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

    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass

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
        (
            ".xlsx",
            ".xls",
        )
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
# FIND TIME BLOCK
# ============================================================

def find_time_block_column(df):

    target = normalize_text(
        TIME_BLOCK_COLUMN
    )

    for column in df.columns:

        if normalize_text(
            column
        ) == target:

            return column

    return None


# ============================================================
# SET TIME BLOCK AS INDEX
# ============================================================

def set_time_block_index(df):

    time_column = find_time_block_column(
        df
    )

    if time_column is None:

        raise ValueError(
            "Time Block column not found."
        )

    df = df.copy()

    df = df.set_index(
        time_column,
        drop=True,
    )

    return df


# ============================================================
# ACTUAL COLUMN DETECTION
# ============================================================

def find_actual_column(
    df,
    actual_type,
):
    """
    Detect actual column using similar names.

    SEMS:
        SEMS
        SEMS (SEMS)

    Green Gen-Meter:
        Green Gen-Meter
        Green Gen-Meter (OPC)

    Green Gen-SCADA:
        Green Gen-SCADA
        Green Gen-SCADA (OPC)
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
        # GREEN GEN METER
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
        # GREEN GEN SCADA
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
    # Prefer a column having numeric values
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
# PARSE FORECAST COLUMN
# ============================================================

def parse_forecast_header(
    column_name
):
    """
    Forecast format:

        PSS_Forecaster

    Split ONLY on the first underscore.

    Example:

        66 KV Bhulleriyan_ALL12.5_F1

    becomes:

        PSS:
            66 KV Bhulleriyan

        Forecaster:
            ALL12.5_F1
    """

    text = str(
        column_name
    ).strip()

    if "_" not in text:

        return (
            None,
            None,
        )

    pss, forecaster = (
        text.split(
            "_",
            1,
        )
    )

    pss = pss.strip()

    forecaster = forecaster.strip()

    if not pss:

        return (
            None,
            None,
        )

    if not forecaster:

        return (
            None,
            None,
        )

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
        # Make sure forecast contains numeric data
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
    Each uploaded file contains only one PSS.

    If several spelling variations occur,
    normalized PSS is used to treat them as
    the same PSS.
    """

    if not forecasts:

        return (
            None,
            None,
        )

    pss_counts = {}

    for item in forecasts:

        normalized = item[
            "normalized_pss"
        ]

        pss_counts[
            normalized
        ] = (
            pss_counts.get(
                normalized,
                0,
            )
            + 1
        )

    normalized_pss = max(
        pss_counts,
        key=pss_counts.get,
    )

    # --------------------------------------------------------
    # Select best display name
    # --------------------------------------------------------

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

    if not display_names:

        return (
            None,
            None,
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
# DEFAULT ACTUAL SELECTION
# ============================================================

def get_default_actual(
    actuals
):
    """
    Automatic priority:

        SEMS
        ↓
        Green Gen-Meter
        ↓
        Green Gen-SCADA
    """

    for actual_type in ACTUAL_PRIORITY:

        if actuals.get(
            actual_type
        ) is not None:

            return actual_type

    return None


# ============================================================
# MAPE CALCULATION
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
                (Forecast - Actual)
                / Actual
            )
        ) × 100
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
    # Remove zero actual
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
# MAPE COLOR
# ============================================================

def mape_color(
    value,
    minimum,
    maximum,
):
    """
    Low MAPE:
        Green

    Medium MAPE:
        Yellow

    High MAPE:
        Red
    """

    if pd.isna(value):

        return ""

    value = float(value)

    # --------------------------------------------------------
    # Same value everywhere
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
        "background-color:"
        f"rgb({red},{green},{blue});"
        "color:black;"
    )


# ============================================================
# TITLE
# ============================================================

st.title(
    "📊 PSS × Forecaster MAPE Matrix"
)

st.caption(
    "Upload multiple files. Each file should contain one PSS."
)


# ============================================================
# FILE UPLOADER
# ============================================================

uploaded_files = st.file_uploader(
    "Upload multiple files",
    type=[
        "csv",
        "xlsx",
        "xls",
    ],
    accept_multiple_files=True,
)


# ============================================================
# STOP IF NO FILE
# ============================================================

if not uploaded_files:

    st.info(
        "Upload one or more files to begin."
    )

    st.stop()


# ============================================================
# MAPE SETTINGS
# ============================================================

st.subheader(
    "MAPE Settings"
)

setting_col1, setting_col2 = (
    st.columns(2)
)

with setting_col1:

    exclude_zero = st.checkbox(
        "Exclude Actual = 0",
        value=True,
    )

with setting_col2:

    minimum_actual = st.number_input(
        "Minimum Actual Value",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )


# ============================================================
# READ + DETECT FILES
# ============================================================

st.subheader(
    "📂 File Processing"
)

processing_rows = []

file_data = {}

progress = st.progress(
    0
)

status_text = st.empty()


# ============================================================
# PROCESS EVERY FILE
# ============================================================

for index, uploaded_file in enumerate(
    uploaded_files
):

    filename = uploaded_file.name

    status_text.write(
        f"⏳ Reading `{filename}`..."
    )

    try:

        # ----------------------------------------------------
        # READ
        # ----------------------------------------------------

        df = read_file(
            uploaded_file
        )

        # ----------------------------------------------------
        # CLEAN
        # ----------------------------------------------------

        df = clean_dataframe(
            df
        )

        # ----------------------------------------------------
        # TIME BLOCK
        # ----------------------------------------------------

        df = set_time_block_index(
            df
        )

        # ----------------------------------------------------
        # ACTUALS
        # ----------------------------------------------------

        actuals = detect_actuals(
            df
        )

        # ----------------------------------------------------
        # FORECASTS
        # ----------------------------------------------------

        forecasts = detect_forecasts(
            df
        )

        if not forecasts:

            raise ValueError(
                "No Forecast columns detected."
            )

        # ----------------------------------------------------
        # PSS
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # KEEP FORECASTS FOR THIS PSS
        # ----------------------------------------------------

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
                "PSS found, but no Forecast "
                "columns were associated with it."
            )

        # ----------------------------------------------------
        # AVAILABLE ACTUALS
        # ----------------------------------------------------

        available_actuals = []

        for actual_type in ACTUAL_PRIORITY:

            if actuals.get(
                actual_type
            ) is not None:

                available_actuals.append(
                    actual_type
                )

        if not available_actuals:

            raise ValueError(
                "No Actual column found. "
                "Expected SEMS, Green Gen-Meter "
                "or Green Gen-SCADA."
            )

        # ----------------------------------------------------
        # DEFAULT ACTUAL
        # ----------------------------------------------------

        default_actual = get_default_actual(
            actuals
        )

        # ----------------------------------------------------
        # SAVE FILE DATA
        # ----------------------------------------------------

        file_data[index] = {
            "filename": filename,
            "df": df,
            "pss": pss_name,
            "normalized_pss": normalized_pss,
            "actuals": actuals,
            "available_actuals": available_actuals,
            "default_actual": default_actual,
            "forecasts": forecasts,
        }

        # ----------------------------------------------------
        # STATUS ROW
        # ----------------------------------------------------

        processing_rows.append(
            {
                "File": filename,
                "Status": "Success",
                "PSS": pss_name,
                "Actual Available": ", ".join(
                    available_actuals
                ),
                "Forecasts Found": len(
                    forecasts
                ),
                "Message": "PSS found",
            }
        )

    except Exception as error:

        processing_rows.append(
            {
                "File": filename,
                "Status": "Error",
                "PSS": "-",
                "Actual Available": "-",
                "Forecasts Found": 0,
                "Message": str(error),
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


progress.empty()
status_text.empty()


# ============================================================
# PROCESSING TABLE
# ============================================================

processing_df = pd.DataFrame(
    processing_rows
)

st.dataframe(
    processing_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# CHECK SUCCESSFUL FILES
# ============================================================

if not file_data:

    st.error(
        "No valid files were detected."
    )

    st.stop()


# ============================================================
# ACTUAL DATA SELECTION
# ============================================================

st.subheader(
    "🎯 Select Actual Data for Each File / PSS"
)

st.caption(
    "The default selection follows SEMS → Green Gen-Meter → Green Gen-SCADA. "
    "You can override it individually for every file."
)


# ============================================================
# SESSION STATE
# ============================================================

if (
    "actual_selection"
    not in st.session_state
):

    st.session_state.actual_selection = {}


# ============================================================
# CREATE SELECTION UI
# ============================================================

for index, data in file_data.items():

    filename = data[
        "filename"
    ]

    pss_name = data[
        "pss"
    ]

    available_actuals = data[
        "available_actuals"
    ]

    default_actual = data[
        "default_actual"
    ]

    # --------------------------------------------------------
    # Unique key
    # --------------------------------------------------------

    selection_key = (
        f"actual_selection_{index}"
    )

    # --------------------------------------------------------
    # Initialize
    # --------------------------------------------------------

    if selection_key not in st.session_state:

        st.session_state[
            selection_key
        ] = default_actual

    # --------------------------------------------------------
    # Display
    # --------------------------------------------------------

    col_file, col_pss, col_actual = (
        st.columns(
            [
                2.5,
                2,
                2,
            ]
        )
    )

    with col_file:

        st.write(
            f"**{filename}**"
        )

    with col_pss:

        st.write(
            pss_name
        )

    with col_actual:

        selected_actual = st.selectbox(
            "Actual",
            options=available_actuals,
            index=available_actuals.index(
                st.session_state[
                    selection_key
                ]
            ),
            key=selection_key,
            label_visibility="collapsed",
        )


# ============================================================
# SHOW CURRENT SELECTIONS
# ============================================================

st.divider()

st.write(
    "**Selected Actual Sources:**"
)

selection_summary = []

for index, data in file_data.items():

    selection_key = (
        f"actual_selection_{index}"
    )

    selected_actual = (
        st.session_state.get(
            selection_key,
            data["default_actual"],
        )
    )

    selection_summary.append(
        {
            "File": data[
                "filename"
            ],
            "PSS": data[
                "pss"
            ],
            "Actual Used": selected_actual,
        }
    )

st.dataframe(
    pd.DataFrame(
        selection_summary
    ),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# MAPE CALCULATION BUTTON
# ============================================================

calculate_button = st.button(
    "🚀 Calculate MAPE",
    type="primary",
    use_container_width=True,
)


if not calculate_button:

    st.stop()


# ============================================================
# CALCULATE MAPE
# ============================================================

results = []

calculation_errors = []

calc_progress = st.progress(
    0
)

calc_status = st.empty()


# ============================================================
# PROCESS EACH FILE
# ============================================================

for count, (
    index,
    data,
) in enumerate(
    file_data.items()
):

    filename = data[
        "filename"
    ]

    pss_name = data[
        "pss"
    ]

    df = data[
        "df"
    ]

    actuals = data[
        "actuals"
    ]

    forecasts = data[
        "forecasts"
    ]

    # --------------------------------------------------------
    # GET USER SELECTED ACTUAL
    # --------------------------------------------------------

    selection_key = (
        f"actual_selection_{index}"
    )

    selected_actual = (
        st.session_state.get(
            selection_key,
            data["default_actual"],
        )
    )

    actual_column = actuals.get(
        selected_actual
    )

    calc_status.write(
        f"⚙️ Calculating `{filename}` using `{selected_actual}`..."
    )

    try:

        if actual_column is None:

            raise ValueError(
                f"Selected Actual '{selected_actual}' "
                "was not found."
            )

        actual_series = df[
            actual_column
        ]

        # ----------------------------------------------------
        # EACH FORECASTER
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

        calculation_errors.append(
            f"{filename}: {error}"
        )

    calc_progress.progress(
        int(
            (
                count + 1
            )
            / len(file_data)
            * 100
        )
    )


calc_progress.empty()
calc_status.empty()


# ============================================================
# CALCULATION ERRORS
# ============================================================

if calculation_errors:

    st.warning(
        "Some files could not be calculated:"
    )

    for error in calculation_errors:

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
# REMOVE INVALID MAPE
# ============================================================

result_df = result_df[
    result_df["MAPE"].notna()
].copy()


if result_df.empty:

    st.error(
        "MAPE could not be calculated. "
        "Check Actual and Forecast data."
    )

    st.stop()


# ============================================================
# SAME PSS + FORECASTER
# ============================================================
#
# If the same PSS/Forecaster appears in multiple uploaded
# files, average the MAPE.
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
# CREATE PIVOT MATRIX
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
# GET COLOR RANGE
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
# pandas newer versions:
#
# Styler.map()
#
# NOT:
#
# Styler.applymap()
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

st.divider()

st.subheader(
    "📊 PSS × Forecaster MAPE Matrix"
)

st.dataframe(
    styled_matrix,
    use_container_width=True,
)


# ============================================================
# DOWNLOAD MATRIX
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
# DOWNLOAD BUTTON
# ============================================================

st.download_button(
    label="📥 Download MAPE Matrix",
    data=excel_output,
    file_name=(
        "PSS_Forecaster_MAPE_Matrix.xlsx"
    ),
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    ),
    use_container_width=True,
)
