import streamlit as st
import pandas as pd
import re
from io import BytesIO


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="P-X Data Comparison",
    page_icon="🔍",
    layout="wide"
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown("""
<style>

    .main-title {
        font-size: 32px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .sub-title {
        color: #666;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .metric-card {
        padding: 15px;
        border-radius: 10px;
        background-color: #f7f7f7;
        border: 1px solid #e5e5e5;
    }

    .success-box {
        padding: 12px;
        border-radius: 8px;
        background-color: #eaf7ed;
        border: 1px solid #b7dfc0;
    }

    .error-box {
        padding: 12px;
        border-radius: 8px;
        background-color: #fdecec;
        border: 1px solid #efb5b5;
    }

</style>
""", unsafe_allow_html=True)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">🔍 P-X Data Comparison</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="sub-title">'
    'Upload your CSV or Excel file to automatically compare P and X columns.'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# FILE UPLOADER
# =========================================================

uploaded_file = st.file_uploader(
    "Upload CSV or Excel file",
    type=["csv", "xlsx", "xls"]
)


# =========================================================
# FUNCTIONS
# =========================================================

def load_file(uploaded_file):

    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)

    return pd.read_excel(uploaded_file)


def find_date_column(df):

    # First try exact Date
    for col in df.columns:
        if str(col).strip().lower() == "date":
            return col

    # Then look for columns containing date
    for col in df.columns:
        if "date" in str(col).lower():
            return col

    return None


def find_pairs(df):

    pairs = {}

    for col in df.columns:

        col_str = str(col)

        # Ignore DEV columns
        if col_str.upper().startswith("DEV"):
            continue

        # Find P/X + identifier
        # Examples:
        # PN12
        # XN12
        # PE10
        # XE10
        match = re.search(r'([PX])([A-Z]\d{2})', col_str)

        if match:

            side = match.group(1)
            key = match.group(2)

            pairs.setdefault(key, {})
            pairs[key].setdefault(side, [])
            pairs[key][side].append(col)

    return pairs


def compare_data(df):

    pairs = find_pairs(df)

    result_columns = []
    pair_report = []

    for key, sides in pairs.items():

        if "P" not in sides or "X" not in sides:
            continue

        p_cols = sides["P"]
        x_cols = sides["X"]

        for p_col in p_cols:

            for x_col in x_cols:

                result_col = f"{key}_Result"

                comparison = df[p_col].eq(df[x_col])

                # Add result to dataframe
                df[result_col] = comparison

                # Statistics
                total_blocks = len(comparison)
                different_blocks = (~comparison).sum()
                identical_blocks = comparison.sum()

                is_identical = different_blocks == 0

                pair_report.append({
                    "Identifier": key,
                    "P Column": p_col,
                    "X Column": x_col,
                    "Total Blocks": total_blocks,
                    "Identical Blocks": identical_blocks,
                    "Different Blocks": different_blocks,
                    "100% Identical": "Yes" if is_identical else "No"
                })

                result_columns.append(result_col)

    report_df = pd.DataFrame(pair_report)

    return df, report_df


def highlight_mismatch(row, result_columns):

    styles = pd.Series("", index=row.index)

    for result_col in result_columns:

        if result_col not in row.index:
            continue

        key = result_col.replace("_Result", "")

        # Find corresponding P/X columns from the row
        for col in row.index:

            if col == result_col:
                continue

            col_str = str(col)

            # If this column contains the corresponding P/X identifier
            if re.search(
                rf'[PX]{re.escape(key)}',
                col_str
            ):

                if row[result_col] is False or row[result_col] == False:
                    styles[col] = (
                        "background-color: #ffcccc; "
                        "color: #9c0006;"
                    )

        # Highlight result itself
        if row[result_col] is False or row[result_col] == False:
            styles[result_col] = (
                "background-color: #ff9999; "
                "color: #7f0000; "
                "font-weight: bold;"
            )
        else:
            styles[result_col] = (
                "background-color: #d9f2d9; "
                "color: #176b17;"
            )

    return styles


def convert_to_excel(df):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            sheet_name="Comparison Result",
            index=True
        )

    output.seek(0)

    return output


# =========================================================
# MAIN APPLICATION
# =========================================================

if uploaded_file:

    try:

        # -------------------------------------------------
        # Load file
        # -------------------------------------------------

        with st.spinner("Reading file..."):

            df = load_file(uploaded_file)

        st.success(
            f"File loaded successfully: {uploaded_file.name}"
        )


        # -------------------------------------------------
        # Basic information
        # -------------------------------------------------

        date_col = find_date_column(df)

        if date_col is None:

            st.error(
                "No Date column was found in the uploaded file."
            )

            st.stop()


        # Convert Date
        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        )

        # Set Date as index
        df = df.set_index(date_col)


        # -------------------------------------------------
        # Run comparison
        # -------------------------------------------------

        with st.spinner("Detecting P-X pairs and comparing data..."):

            result_df, report_df = compare_data(df)


        # -------------------------------------------------
        # Result columns
        # -------------------------------------------------

        result_columns = [
            col for col in result_df.columns
            if str(col).endswith("_Result")
        ]


        # -------------------------------------------------
        # Summary
        # -------------------------------------------------

        st.markdown("## Comparison Summary")

        total_columns = len(result_df.columns)
        total_pairs = len(report_df)

        if total_pairs > 0:

            total_different = report_df[
                "Different Blocks"
            ].sum()

            total_identical_pairs = (
                report_df["100% Identical"] == "Yes"
            ).sum()

        else:

            total_different = 0
            total_identical_pairs = 0


        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Rows / Blocks",
                len(result_df)
            )

        with col2:
            st.metric(
                "P-X Pairs",
                total_pairs
            )

        with col3:
            st.metric(
                "100% Identical",
                total_identical_pairs
            )

        with col4:
            st.metric(
                "Different Blocks",
                int(total_different)
            )


        # -------------------------------------------------
        # Overall status
        # -------------------------------------------------

        if total_pairs == 0:

            st.warning(
                "No matching P-X column pairs were detected."
            )

        elif total_different == 0:

            st.markdown(
                '<div class="success-box">'
                '<b>✓ All matched P-X columns are 100% identical.</b>'
                '</div>',
                unsafe_allow_html=True
            )

        else:

            st.markdown(
                '<div class="error-box">'
                '<b>⚠ Differences detected.</b> '
                'See the report and highlighted blocks below.'
                '</div>',
                unsafe_allow_html=True
            )


        # -------------------------------------------------
        # Pair report
        # -------------------------------------------------

        if not report_df.empty:

            st.markdown("## P-X Comparison Report")

            st.dataframe(
                report_df,
                use_container_width=True,
                hide_index=True
            )


        # -------------------------------------------------
        # Detailed Data
        # -------------------------------------------------

        st.markdown("## Detailed Comparison")

        if result_columns:

            st.caption(
                "🔴 Red cells indicate P-X mismatches. "
                "🟢 Green result cells indicate matching values."
            )

            styled_df = result_df.style.apply(
                lambda row: highlight_mismatch(
                    row,
                    result_columns
                ),
                axis=1
            )

            st.dataframe(
                styled_df,
                use_container_width=True,
                height=600
            )

        else:

            st.info(
                "No comparison result columns were generated."
            )


        # -------------------------------------------------
        # Show only mismatched blocks
        # -------------------------------------------------

        if total_different > 0:

            st.markdown("## Mismatched Blocks")

            mismatch_mask = pd.Series(
                False,
                index=result_df.index
            )

            for result_col in result_columns:

                mismatch_mask |= (
                    result_df[result_col] == False
                )

            mismatch_df = result_df[
                mismatch_mask
            ]

            st.write(
                f"Found **{len(mismatch_df)} blocks** "
                "with at least one mismatch."
            )

            st.dataframe(
                mismatch_df,
                use_container_width=True,
                height=400
            )


        # -------------------------------------------------
        # Download
        # -------------------------------------------------

        st.markdown("## Download")

        excel_file = convert_to_excel(result_df)

        st.download_button(
            label="⬇ Download Comparison Result",
            data=excel_file,
            file_name="comparison_result.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )


    except Exception as e:

        st.error(
            f"Something went wrong: {str(e)}"
        )

else:

    # -----------------------------------------------------
    # Empty state
    # -----------------------------------------------------

    st.info(
        "Upload a CSV or Excel file above to start the comparison."
    )

    st.markdown("""
    ### How it works

    1. Upload your CSV or Excel file.
    2. The app automatically detects the **Date** column.
    3. Columns starting with **DEV** are ignored.
    4. P/X pairs such as `PN12` ↔ `XN12` are detected.
    5. Each P column is compared with its X column.
    6. Result columns such as `N12_Result` are added.
    7. Mismatched blocks are highlighted.
    8. A detailed comparison report is generated.
    9. Download the complete result as Excel.
    """)
