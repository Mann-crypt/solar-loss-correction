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
    'Upload multiple CSV or Excel files to automatically compare P and X columns.'
    '</div>',
    unsafe_allow_html=True
)


# =========================================================
# FUNCTIONS
# =========================================================

def load_file(uploaded_file):

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".csv"):

        return pd.read_csv(uploaded_file)

    elif file_name.endswith(".xlsx"):

        return pd.read_excel(
            uploaded_file,
            engine="openpyxl"
        )

    elif file_name.endswith(".xls"):

        return pd.read_excel(
            uploaded_file
        )

    else:

        raise ValueError(
            "Unsupported file type. "
            "Please upload CSV or Excel."
        )


# =========================================================
# MAKE COLUMN NAMES UNIQUE
# =========================================================

def make_columns_unique(df):

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


# =========================================================
# FIND DATE COLUMN
# =========================================================

def find_date_column(df):

    # Exact Date column
    for col in df.columns:

        if str(col).strip().lower() == "date":

            return col


    # Any column containing Date
    for col in df.columns:

        if "date" in str(col).lower():

            return col


    return None


# =========================================================
# NORMALIZE P/X IDENTIFIER
# =========================================================

def extract_px_identifier(col):

    """
    Extracts the identifier following P or X.

    Examples:

    PN12              -> N12
    XN12              -> N12

    PE10              -> E10
    XE10              -> E10

    PSD00C1PF001      -> SD00
    XSD0_01           -> SD0
    """

    col = str(col).upper()

    # P or X followed by letters + digits
    match = re.search(
        r'([PX])([A-Z]+\d+)',
        col
    )

    if not match:
        return None, None

    side = match.group(1)

    identifier = match.group(2)

    return side, identifier


# =========================================================
# NORMALIZE IDENTIFIER
# =========================================================

def normalize_identifier(identifier):

    """
    Normalizes identifiers so that cases such as:

        PSD00
        XSD0

    can be matched through the common identifier SD0.
    """

    if identifier is None:
        return None

    identifier = identifier.upper()

    # Split letters and numbers
    match = re.match(
        r'([A-Z]+)(\d+)',
        identifier
    )

    if not match:
        return identifier

    letters = match.group(1)
    numbers = match.group(2)

    # Remove trailing zeros from numeric portion
    numbers = numbers.rstrip("0")

    # If everything was zeros, retain one zero
    if numbers == "":
        numbers = "0"

    return letters + numbers


# =========================================================
# FIND P/X PAIRS
# =========================================================

def find_pairs(df):

    p_columns = []
    x_columns = []

    for col in df.columns:

        col_str = str(col)

        # Ignore DEV columns
        if col_str.upper().startswith("DEV"):
            continue

        side, identifier = extract_px_identifier(
            col_str
        )

        if side is None:
            continue

        normalized = normalize_identifier(
            identifier
        )

        if side == "P":

            p_columns.append(
                (
                    col_str,
                    identifier,
                    normalized
                )
            )

        elif side == "X":

            x_columns.append(
                (
                    col_str,
                    identifier,
                    normalized
                )
            )


    pairs = []

    # -----------------------------------------------------
    # Match P with X
    # -----------------------------------------------------

    for p_col, p_id, p_norm in p_columns:

        for x_col, x_id, x_norm in x_columns:

            # Exact normalized match
            if p_norm == x_norm:

                pairs.append(
                    (
                        p_norm,
                        p_col,
                        x_col
                    )
                )

                continue


            # -------------------------------------------------
            # Handle partial normalized identifiers
            #
            # Example:
            #
            # PSD00 -> SD0
            # XSD0  -> SD0
            # -------------------------------------------------

            if (
                p_norm.startswith(x_norm)
                or x_norm.startswith(p_norm)
            ):

                common = (
                    x_norm
                    if len(x_norm) <= len(p_norm)
                    else p_norm
                )

                if (
                    common,
                    p_col,
                    x_col
                ) not in pairs:

                    pairs.append(
                        (
                            common,
                            p_col,
                            x_col
                        )
                    )


    return pairs


# =========================================================
# COMPARE DATA
# =========================================================

def compare_data(df):

    pairs = find_pairs(df)

    report = []

    result_columns = []

    pair_lookup = {}

    for key, p_col, x_col in pairs:

        # -------------------------------------------------
        # Result column
        # -------------------------------------------------

        result_col = f"{key}_Result"

        if result_col in df.columns:

            counter = 2

            while (
                f"{key}_{counter}_Result"
                in df.columns
            ):

                counter += 1

            result_col = (
                f"{key}_{counter}_Result"
            )


        # -------------------------------------------------
        # Compare values
        # -------------------------------------------------

        comparison = df[p_col].eq(
            df[x_col]
        )

        df[result_col] = comparison

        result_columns.append(
            result_col
        )

        pair_lookup[result_col] = (
            p_col,
            x_col
        )


        # -------------------------------------------------
        # Statistics
        # -------------------------------------------------

        total_blocks = len(
            comparison
        )

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

            "Total Blocks":
                total_blocks,

            "Identical Blocks":
                identical_blocks,

            "Different Blocks":
                different_blocks,

            "100% Identical":
                "Yes"
                if different_blocks == 0
                else "No"
        })


    report_df = pd.DataFrame(
        report
    )

    return (
        df,
        report_df,
        result_columns,
        pair_lookup
    )


# =========================================================
# HIGHLIGHT MISMATCHES
# =========================================================

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

        value = row[result_col]

        # -------------------------------------------------
        # MATCH
        # -------------------------------------------------

        if value is True:

            styles[result_col] = (
                "background-color: #d9f2d9;"
                "color: #176b17;"
                "font-weight: bold;"
            )

            continue


        # -------------------------------------------------
        # MISMATCH
        # -------------------------------------------------

        styles[result_col] = (
            "background-color: #ff9999;"
            "color: #7f0000;"
            "font-weight: bold;"
        )


        # Highlight P and X
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


# =========================================================
# CREATE EXCEL FILE
# =========================================================

def create_excel_report(
    file_summary_df,
    combined_report,
    all_results
):

    output = BytesIO()

    sheets_written = 0

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        if file_summary_df is not None:

            file_summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )

            sheets_written += 1


        # -------------------------------------------------
        # P-X REPORT
        # -------------------------------------------------

        if (
            combined_report is not None
            and not combined_report.empty
        ):

            combined_report.to_excel(
                writer,
                sheet_name="P-X Report",
                index=False
            )

            sheets_written += 1


        # -------------------------------------------------
        # MISMATCH SHEETS
        # -------------------------------------------------

        for filename, data in all_results.items():

            result_df = data["data"]

            result_columns = data[
                "result_columns"
            ]


            if not result_columns:
                continue


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


            # Safe sheet name
            safe_name = re.sub(
                r'[\[\]\:\*\?\/\\]',
                "_",
                str(filename)
            )


            sheet_name = (
                safe_name[:25]
                + "_Mismatch"
            )

            sheet_name = sheet_name[:31]


            # Handle duplicate sheet names
            existing = writer.book.sheetnames

            base_name = sheet_name
            counter = 1

            while sheet_name in existing:

                suffix = f"_{counter}"

                sheet_name = (
                    base_name[
                        :31 - len(suffix)
                    ]
                    + suffix
                )

                counter += 1


            mismatch_df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=True
            )

            sheets_written += 1


        # -------------------------------------------------
        # SAFETY SHEET
        # -------------------------------------------------

        if sheets_written == 0:

            pd.DataFrame({
                "Message": [
                    "No files were successfully processed."
                ]
            }).to_excel(
                writer,
                sheet_name="Result",
                index=False
            )


    output.seek(0)

    return output


# =========================================================
# FILE UPLOADER
# =========================================================

uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=[
        "csv",
        "xlsx",
        "xls"
    ],
    accept_multiple_files=True
)


# =========================================================
# MAIN APPLICATION
# =========================================================

if uploaded_files:

    all_reports = []

    all_results = {}

    processing_errors = []


    # =====================================================
    # PROCESS FILES
    # =====================================================

    for uploaded_file in uploaded_files:

        try:

            with st.spinner(
                f"Processing {uploaded_file.name}..."
            ):

                # -----------------------------------------
                # LOAD
                # -----------------------------------------

                df = load_file(
                    uploaded_file
                )


                # -----------------------------------------
                # DUPLICATE COLUMNS
                # -----------------------------------------

                if df.columns.duplicated().any():

                    df = make_columns_unique(
                        df
                    )


                # -----------------------------------------
                # DATE
                # -----------------------------------------

                date_col = find_date_column(
                    df
                )


                if date_col is None:

                    processing_errors.append({

                        "File":
                            uploaded_file.name,

                        "Error":
                            "Date column not found"
                    })

                    continue


                df[date_col] = pd.to_datetime(
                    df[date_col],
                    errors="coerce"
                )


                # -----------------------------------------
                # COMPARE
                # -----------------------------------------

                (
                    result_df,
                    report_df,
                    result_columns,
                    pair_lookup
                ) = compare_data(df)


                # -----------------------------------------
                # ADD FILE NAME
                # -----------------------------------------

                if not report_df.empty:

                    report_df.insert(
                        0,
                        "File",
                        uploaded_file.name
                    )

                    all_reports.append(
                        report_df
                    )


                # -----------------------------------------
                # STORE
                # -----------------------------------------

                all_results[
                    uploaded_file.name
                ] = {

                    "data":
                        result_df,

                    "result_columns":
                        result_columns,

                    "pair_lookup":
                        pair_lookup,

                    "report":
                        report_df
                }


        except Exception as e:

            processing_errors.append({

                "File":
                    uploaded_file.name,

                "Error":
                    str(e)
            })


    # =====================================================
    # ERRORS
    # =====================================================

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
            hide_index=True
        )


    # =====================================================
    # COMBINED REPORT
    # =====================================================

    if all_reports:

        combined_report = pd.concat(
            all_reports,
            ignore_index=True
        )

    else:

        combined_report = pd.DataFrame()


    # =====================================================
    # OVERALL SUMMARY
    # =====================================================

    st.markdown(
        "## Overall Summary"
    )


    total_files = len(
        all_results
    )

    total_pairs = len(
        combined_report
    )


    if not combined_report.empty:

        total_identical_pairs = int(
            (
                combined_report[
                    "100% Identical"
                ] == "Yes"
            ).sum()
        )

        total_different_blocks = int(
            combined_report[
                "Different Blocks"
            ].sum()
        )

    else:

        total_identical_pairs = 0

        total_different_blocks = 0


    c1, c2, c3, c4 = st.columns(4)


    c1.metric(
        "Files Processed",
        total_files
    )

    c2.metric(
        "P-X Pairs",
        total_pairs
    )

    c3.metric(
        "100% Identical",
        total_identical_pairs
    )

    c4.metric(
        "Different Blocks",
        total_different_blocks
    )


    # =====================================================
    # FILE SUMMARY
    # =====================================================

    file_summary = []


    for filename, data in all_results.items():

        report = data["report"]


        if report.empty:

            file_summary.append({

                "File":
                    filename,

                "P-X Pairs":
                    0,

                "100% Identical":
                    0,

                "Pairs With Differences":
                    0,

                "Different Blocks":
                    0,

                "Status":
                    "NO PAIRS"
            })

            continue


        identical = int(
            (
                report[
                    "100% Identical"
                ] == "Yes"
            ).sum()
        )


        different_pairs = int(
            (
                report[
                    "100% Identical"
                ] == "No"
            ).sum()
        )


        different_blocks = int(
            report[
                "Different Blocks"
            ].sum()
        )


        status = (
            "PASS"
            if different_blocks == 0
            else "FAIL"
        )


        file_summary.append({

            "File":
                filename,

            "P-X Pairs":
                len(report),

            "100% Identical":
                identical,

            "Pairs With Differences":
                different_pairs,

            "Different Blocks":
                different_blocks,

            "Status":
                status
        })


    file_summary_df = pd.DataFrame(
        file_summary
    )


    if not file_summary_df.empty:

        st.markdown(
            "## File Summary"
        )

        st.dataframe(
            file_summary_df,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # COMPLETE REPORT
    # =====================================================

    if not combined_report.empty:

        st.markdown(
            "## Complete P-X Comparison Report"
        )

        st.dataframe(
            combined_report,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # INDIVIDUAL FILE DETAILS
    # =====================================================

    st.markdown(
        "## Detailed File Results"
    )


    for filename, data in all_results.items():

        report = data["report"]

        result_df = data["data"]

        result_columns = data[
            "result_columns"
        ]

        pair_lookup = data[
            "pair_lookup"
        ]


        with st.expander(
            f"📄 {filename}",
            expanded=False
        ):


            if report.empty:

                st.warning(
                    "No P-X pairs were found."
                )

                continue


            file_pairs = len(
                report
            )


            file_different = int(
                report[
                    "Different Blocks"
                ].sum()
            )


            m1, m2, m3 = st.columns(3)


            m1.metric(
                "P-X Pairs",
                file_pairs
            )


            m2.metric(
                "Different Blocks",
                file_different
            )


            m3.metric(
                "Status",
                "PASS"
                if file_different == 0
                else "FAIL"
            )


            # ---------------------------------------------
            # Pair report
            # ---------------------------------------------

            st.dataframe(
                report.drop(
                    columns=["File"],
                    errors="ignore"
                ),
                use_container_width=True,
                hide_index=True
            )


            # ---------------------------------------------
            # Mismatched blocks
            # ---------------------------------------------

            mismatch_mask = pd.Series(
                False,
                index=result_df.index
            )


            for result_col in result_columns:

                mismatch_mask |= (
                    result_df[
                        result_col
                    ] == False
                )


            mismatch_df = result_df[
                mismatch_mask
            ]


            if not mismatch_df.empty:

                st.markdown(
                    "### Mismatched Blocks"
                )

                st.dataframe(
                    mismatch_df,
                    use_container_width=True,
                    height=350
                )

            else:

                st.success(
                    "No mismatched blocks."
                )


    # =====================================================
    # DOWNLOAD
    # =====================================================

    st.markdown(
        "## Download Report"
    )


    excel_file = create_excel_report(
        file_summary_df,
        combined_report,
        all_results
    )


    st.download_button(

        label="⬇ Download Complete Report",

        data=excel_file.getvalue(),

        file_name="PX_Comparison_Report.xlsx",

        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )


else:

    st.info(
        "Upload one or more CSV/Excel files "
        "to start the comparison."
    )

    st.markdown("""
### How it works

1. Upload multiple CSV or Excel files.
2. Each file is processed independently.
3. `DEV` columns are ignored.
4. P/X pairs are automatically detected.
5. Each P/X pair is compared block-by-block.
6. A summary is generated for every file.
7. All files are combined into one report.
8. Mismatched blocks are shown separately.
9. Download one Excel workbook containing the complete report.
""")
