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
# CSS
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
    'Upload a CSV or Excel file to automatically compare P and X columns.'
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

def make_columns_unique(df):

    """
    Makes duplicate column names unique.

    Example:
    A, A, B
    becomes:
    A, A_1, B
    """

    counts = {}
    new_columns = []

    for col in df.columns:

        col = str(col)

        if col not in counts:
            counts[col] = 0
            new_columns.append(col)

        else:
            counts[col] += 1
            new_columns.append(
                f"{col}_{counts[col]}"
            )

    df.columns = new_columns

    return df


def load_file(uploaded_file):

    if uploaded_file.name.lower().endswith(".csv"):
        return pd.read_csv(uploaded_file)

    return pd.read_excel(uploaded_file)


def find_date_column(df):

    # Exact Date
    for col in df.columns:

        if str(col).strip().lower() == "date":
            return col

    # Date somewhere in column name
    for col in df.columns:

        if "date" in str(col).lower():
            return col

    return None


def find_pairs(df):

    pairs = {}

    for col in df.columns:

        col = str(col)

        # Ignore DEV columns
        if col.upper().startswith("DEV"):
            continue

        # Find PN12 / XN12 / PE10 / XE10
        match = re.search(
            r'([PX])([A-Z]\d{2})',
            col
        )

        if match:

            side = match.group(1)
            key = match.group(2)

            pairs.setdefault(key, {})
            pairs[key].setdefault(side, [])
            pairs[key][side].append(col)

    return pairs


def compare_data(df):

    pairs = find_pairs(df)

    report = []
    result_columns = []

    for key, sides in pairs.items():

        if "P" not in sides or "X" not in sides:
            continue

        p_cols = sides["P"]
        x_cols = sides["X"]

        for p_col in p_cols:

            for x_col in x_cols:

                result_col = f"{key}_Result"

                comparison = df[p_col].eq(
                    df[x_col]
                )

                # If multiple P/X columns have same key,
                # don't overwrite previous result.
                if result_col in df.columns:

                    result_col = (
                        f"{key}_"
                        f"{len(result_columns) + 1}_Result"
                    )

                df[result_col] = comparison

                result_columns.append(
                    result_col
                )

                total_blocks = len(comparison)
                identical_blocks = int(
                    comparison.sum()
                )
                different_blocks = int(
                    (~comparison).sum()
                )

                report.append({
                    "Identifier": key,
                    "P Column": p_col,
                    "X Column": x_col,
                    "Total Blocks": total_blocks,
                    "Identical Blocks": identical_blocks,
                    "Different Blocks": different_blocks,
                    "100% Identical":
                        "Yes"
                        if different_blocks == 0
                        else "No"
                })

    return (
        df,
        pd.DataFrame(report),
        result_columns
    )


def highlight_mismatch(
    row,
    result_columns,
    pair_lookup
):

    styles = pd.Series(
        "",
        index=row.index
    )

    for result_col in result_columns:

        if result_col not in row.index:
            continue

        is_different = (
            row[result_col] == False
        )

        if not is_different:
            styles[result_col] = (
                "background-color: #d9f2d9;"
                "color: #176b17;"
                "font-weight: bold;"
            )

            continue

        styles[result_col] = (
            "background-color: #ff9999;"
            "color: #7f0000;"
            "font-weight: bold;"
        )

        # Highlight corresponding P/X columns
        if result_col in pair_lookup:

            p_col, x_col = pair_lookup[
                result_col
            ]

            if p_col in styles.index:
                styles[p_col] = (
                    "background-color: #ffcccc;"
                    "color: #9c0006;"
                )

            if x_col in styles.index:
                styles[x_col] = (
                    "background-color: #ffcccc;"
                    "color: #9c0006;"
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
            sheet_name="Comparison Result"
        )

    output.seek(0)

    return output


# =========================================================
# MAIN
# =========================================================

if uploaded_file:

    try:

        # -------------------------------------------------
        # LOAD
        # -------------------------------------------------

        with st.spinner("Reading file..."):

            df = load_file(
                uploaded_file
            )

        # -------------------------------------------------
        # FIX DUPLICATE COLUMN NAMES
        # -------------------------------------------------

        original_columns = len(
            df.columns
        )

        duplicate_columns = (
            df.columns.duplicated().sum()
        )

        if duplicate_columns > 0:

            st.warning(
                f"{duplicate_columns} duplicate "
                "column name(s) detected. "
                "They were automatically renamed "
                "to keep the comparison reliable."
            )

            df = make_columns_unique(df)


        st.success(
            f"File loaded: {uploaded_file.name}"
        )


        # -------------------------------------------------
        # DATE
        # -------------------------------------------------

        date_col = find_date_column(df)

        if date_col is None:

            st.error(
                "No Date column was found."
            )

            st.stop()


        df[date_col] = pd.to_datetime(
            df[date_col],
            errors="coerce"
        )

        # IMPORTANT:
        # Do NOT use Date as index for styling.
        # Keep it as a normal unique column.

        # -------------------------------------------------
        # COMPARISON
        # -------------------------------------------------

        with st.spinner(
            "Detecting P-X pairs..."
        ):

            result_df, report_df, result_columns = (
                compare_data(df)
            )


        # -------------------------------------------------
        # PAIR LOOKUP
        # -------------------------------------------------

        pair_lookup = {}

        for _, row in report_df.iterrows():

            result_col = f"{row['Identifier']}_Result"

            # Handle duplicate result names
            matching_results = [
                c for c in result_columns
                if c.startswith(
                    f"{row['Identifier']}_"
                )
                and c.endswith("_Result")
            ]

            for result_name in matching_results:

                if result_name not in pair_lookup:

                    pair_lookup[result_name] = (
                        row["P Column"],
                        row["X Column"]
                    )

                    break


        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        st.markdown(
            "## Comparison Summary"
        )

        total_pairs = len(
            report_df
        )

        total_blocks = len(
            result_df
        )

        if total_pairs:

            total_different = int(
                report_df[
                    "Different Blocks"
                ].sum()
            )

            identical_pairs = int(
                (
                    report_df[
                        "100% Identical"
                    ] == "Yes"
                ).sum()
            )

        else:

            total_different = 0
            identical_pairs = 0


        c1, c2, c3, c4 = st.columns(4)

        c1.metric(
            "Rows / Blocks",
            total_blocks
        )

        c2.metric(
            "P-X Pairs",
            total_pairs
        )

        c3.metric(
            "100% Identical",
            identical_pairs
        )

        c4.metric(
            "Different Blocks",
            total_different
        )


        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        if total_pairs == 0:

            st.warning(
                "No matching P-X pairs found."
            )

        elif total_different == 0:

            st.success(
                "✓ All matched P-X columns are "
                "100% identical."
            )

        else:

            st.error(
                f"⚠ Differences detected in "
                f"{total_different} blocks."
            )


        # -------------------------------------------------
        # REPORT
        # -------------------------------------------------

        if not report_df.empty:

            st.markdown(
                "## P-X Comparison Report"
            )

            st.dataframe(
                report_df,
                use_container_width=True,
                hide_index=True
            )


        # -------------------------------------------------
        # HIGHLIGHTED DATA
        # -------------------------------------------------

        st.markdown(
            "## Detailed Comparison"
        )

        if result_columns:

            st.caption(
                "🔴 P/X values are highlighted when "
                "they are different. "
                "🟢 Result cells indicate matching values."
            )

            styled_df = (
                result_df.style
                .apply(
                    lambda row:
                    highlight_mismatch(
                        row,
                        result_columns,
                        pair_lookup
                    ),
                    axis=1
                )
            )

            st.dataframe(
                styled_df,
                use_container_width=True,
                height=600
            )

        else:

            st.info(
                "No P-X comparison columns generated."
            )


        # -------------------------------------------------
        # ONLY MISMATCHED BLOCKS
        # -------------------------------------------------

        if total_different > 0:

            st.markdown(
                "## Mismatched Blocks"
            )

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
                f"**{len(mismatch_df)}** "
                "blocks contain at least one mismatch."
            )

            st.dataframe(
                mismatch_df,
                use_container_width=True,
                height=400
            )


        # -------------------------------------------------
        # DOWNLOAD
        # -------------------------------------------------

        st.markdown(
            "## Download"
        )

        excel_file = convert_to_excel(
            result_df
        )

        st.download_button(
            "⬇ Download Comparison Result",
            data=excel_file,
            file_name="comparison_result.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )


    except Exception as e:

        st.error(
            f"Something went wrong: {e}"
        )

        st.exception(e)


else:

    st.info(
        "Upload a CSV or Excel file above "
        "to start the comparison."
    )
