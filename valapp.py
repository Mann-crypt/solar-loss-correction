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

    col = str(col).upper()

    # DEV columns are never considered
    if col.startswith("DEV"):
        return None, None

    # P/X must appear after start or separator
    #
    # Examples:
    # KURxx_PN125C1PF001
    #      -> P + N125
    #
    # KUR_XN12_01
    #     -> X + N12
    #
    # KURxx_PSD00C1PF001
    #      -> P + SD00
    #
    # KUR_XSD0_01
    #     -> X + SD0

    match = re.search(
        r'(?:^|[_\-])([PX])([A-Z]+\d+)',
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

    if identifier is None:
        return None

    identifier = str(identifier).upper()

    match = re.match(
        r'([A-Z]+)(\d+)',
        identifier
    )

    if not match:
        return identifier

    letters = match.group(1)
    numbers = match.group(2)

    # Remove trailing zeros
    numbers = numbers.rstrip("0")

    if numbers == "":
        numbers = "0"

    return letters + numbers


# =========================================================
# FIND P/X PAIRS
# =========================================================

def find_pairs(df):

    p_columns = {}
    x_columns = {}

    # =====================================================
    # FIND ALL P AND X COLUMNS
    # =====================================================

    for col in df.columns:

        col_str = str(col)

        # Ignore DEV
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

            p_columns.setdefault(
                normalized,
                []
            ).append(col)

        elif side == "X":

            x_columns.setdefault(
                normalized,
                []
            ).append(col)


    pairs = []

    # =====================================================
    # MATCH P AND X
    # =====================================================

    for p_identifier, p_cols in p_columns.items():

        for x_identifier, x_cols in x_columns.items():

            # ------------------------------------------------
            # Exact match
            # ------------------------------------------------

            exact_match = (
                p_identifier == x_identifier
            )


            # ------------------------------------------------
            # Prefix match
            #
            # N125 -> N12
            # SD0  -> SD0
            # ------------------------------------------------

            prefix_match = (
                p_identifier.startswith(x_identifier)
                or
                x_identifier.startswith(p_identifier)
            )


            if not (
                exact_match
                or prefix_match
            ):
                continue


            # ------------------------------------------------
            # Choose the common identifier
            # ------------------------------------------------

            if len(p_identifier) <= len(x_identifier):

                common_identifier = p_identifier

            else:

                common_identifier = x_identifier


            # ------------------------------------------------
            # Create P-X pairs
            # ------------------------------------------------

            for p_col in p_cols:

                for x_col in x_cols:

                    pairs.append(
                        (
                            common_identifier,
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
    all_results
):

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:

        # =================================================
        # 1. OVERALL SUMMARY
        # =================================================

        if file_summary_df is not None:

            file_summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )


        # =================================================
        # 2. ONE SHEET PER FILE
        # =================================================

        for filename, data in all_results.items():

            report_df = data["report"].copy()


            # ---------------------------------------------
            # Remove File column because sheet already
            # represents that file
            # ---------------------------------------------

            report_df = report_df.drop(
                columns=["File"],
                errors="ignore"
            )


            # ---------------------------------------------
            # Create safe Excel sheet name
            # ---------------------------------------------

            sheet_name = re.sub(
                r'[\[\]\:\*\?\/\\]',
                "_",
                str(filename)
            )

            # Excel sheet name max = 31 characters
            sheet_name = sheet_name[:31]


            # ---------------------------------------------
            # Handle duplicate sheet names
            # ---------------------------------------------

            existing_sheets = (
                writer.book.sheetnames
            )

            base_name = sheet_name
            counter = 1

            while sheet_name in existing_sheets:

                suffix = f"_{counter}"

                sheet_name = (
                    base_name[
                        :31 - len(suffix)
                    ]
                    + suffix
                )

                counter += 1


            # ---------------------------------------------
            # Write file summary
            # ---------------------------------------------

            if report_df.empty:

                pd.DataFrame({
                    "Message": [
                        "No P-X pairs were found."
                    ]
                }).to_excel(
                    writer,
                    sheet_name=sheet_name,
                    index=False
                )

            else:

                report_df.to_excel(
                    writer,
                    sheet_name=sheet_name,
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
    
    st.markdown("## Detailed File Results")
    
    
    for filename, data in all_results.items():
    
        result_df = data["data"].copy()
    
        result_columns = data["result_columns"]
    
        pair_lookup = data["pair_lookup"]
    
        report = data["report"].copy()
    
    
        # =================================================
        # FILE EXPANDER
        # =================================================
    
        with st.expander(
            f"📄 {filename}",
            expanded=False
        ):
    
            # -------------------------------------------------
            # No P-X pairs
            # -------------------------------------------------
    
            if report.empty:
    
                st.warning(
                    "No valid P-X pairs were found in this file."
                )
    
                continue
    
    
            # =================================================
            # FILE SUMMARY
            # =================================================
    
            total_pairs = len(report)
    
            identical_pairs = int(
                (
                    report["100% Identical"]
                    == "Yes"
                ).sum()
            )
    
            different_pairs = int(
                (
                    report["100% Identical"]
                    == "No"
                ).sum()
            )
    
            different_blocks = int(
                report["Different Blocks"].sum()
            )
    
    
            c1, c2, c3, c4 = st.columns(4)
    
            c1.metric(
                "P-X Pairs",
                total_pairs
            )
    
            c2.metric(
                "100% Identical",
                identical_pairs
            )
    
            c3.metric(
                "Pairs With Differences",
                different_pairs
            )
    
            c4.metric(
                "Different Blocks",
                different_blocks
            )
    
    
            # =================================================
            # PAIR SUMMARY
            # =================================================
    
            st.markdown("### P-X Pair Summary")
    
            st.dataframe(
                report[
                    [
                        "Identifier",
                        "P Column",
                        "X Column",
                        "Total Blocks",
                        "Identical Blocks",
                        "Different Blocks",
                        "100% Identical"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )
    
    
            # =================================================
            # DATE-WISE P-X PAIR SUMMARY
            # =================================================
            
            st.markdown("### 📅 Date-wise P-X Pair Summary")
            
            date_col = find_date_column(result_df)
            
            if date_col is None:
            
                st.warning("Date column could not be detected.")
            
            else:
            
                result_df[date_col] = pd.to_datetime(
                    result_df[date_col],
                    errors="coerce"
                )
            
                available_dates = sorted(
                    result_df[date_col]
                    .dropna()
                    .dt.date
                    .unique()
                    .tolist()
                )
            
                if not available_dates:
            
                    st.warning("No valid dates were found.")
            
                else:
            
                    # -------------------------------------------------
                    # MULTI DATE SELECTION
                    # ALL DATES SELECTED BY DEFAULT
                    # -------------------------------------------------
            
                    selected_dates = st.multiselect(
                        "Select Date(s)",
                        options=available_dates,
                        default=available_dates,
                        key=f"summary_dates_{filename}"
                    )
            
                    if not selected_dates:
            
                        st.info("Select at least one date.")
            
                    else:
            
                        # =================================================
                        # CREATE DATE-WISE P-X SUMMARY
                        # =================================================
            
                        date_wise_summary = []
            
                        for current_date in selected_dates:
            
                            # ---------------------------------------------
                            # Data for this date
                            # ---------------------------------------------
            
                            day_df = result_df[
                                result_df[date_col].dt.date
                                == current_date
                            ].copy()
            
            
                            # ---------------------------------------------
                            # Calculate each P-X pair separately
                            # ---------------------------------------------
            
                            for result_col in result_columns:
            
                                if result_col not in pair_lookup:
                                    continue
            
                                if result_col not in day_df.columns:
                                    continue
            
            
                                p_col, x_col = pair_lookup[
                                    result_col
                                ]
            
            
                                # -----------------------------------------
                                # Comparison results
                                # -----------------------------------------
            
                                comparison = (
                                    day_df[result_col]
                                    .fillna(False)
                                    .astype(bool)
                                )
            
            
                                total_blocks = len(
                                    comparison
                                )
            
                                identical_blocks = int(
                                    comparison.sum()
                                )
            
                                different_blocks = int(
                                    (~comparison).sum()
                                )
            
            
                                # -----------------------------------------
                                # Identifier
                                # -----------------------------------------
            
                                identifier = result_col.replace(
                                    "_Result",
                                    ""
                                )
            
            
                                # -----------------------------------------
                                # Date-wise row
                                # -----------------------------------------
            
                                date_wise_summary.append({
            
                                    "Date":
                                        current_date,
            
                                    "Identifier":
                                        identifier,
            
                                    "P Column":
                                        p_col,
            
                                    "X Column":
                                        x_col,
            
                                    "Total Blocks":
                                        total_blocks,
            
                                    "Identical Blocks":
                                        identical_blocks,
            
                                    "Different Blocks":
                                        different_blocks,
            
                                    "100% Identical":
                                        (
                                            "Yes"
                                            if different_blocks == 0
                                            else "No"
                                        )
                                })
            
            
                        # =================================================
                        # DATAFRAME
                        # =================================================
            
                        date_wise_summary_df = pd.DataFrame(
                            date_wise_summary
                        )
            
            
                        # =================================================
                        # DISPLAY
                        # =================================================
            
                        if not date_wise_summary_df.empty:
            
                            st.dataframe(
                                date_wise_summary_df,
                                use_container_width=True,
                                hide_index=True
                            )
            
                        else:
            
                            st.info(
                                "No P-X comparison results available "
                                "for the selected dates."
                            )

            # =================================================
            # MISMATCHED BLOCK DRILL DOWN
            # =================================================
            
            st.markdown("### ❌ Mismatched Blocks")
            
            # =================================================
            # DATE SELECTION
            # =================================================
            
            selected_mismatch_dates = st.multiselect(
                "Select Date(s) for Mismatch Analysis",
                options=available_dates,
                default=available_dates,
                key=f"mismatch_dates_{filename}"
            )
            
            
            if selected_mismatch_dates:
            
                # =================================================
                # P-X PAIR SELECTION
                # =================================================
            
                pair_options = {}
            
                for result_col in result_columns:
            
                    if result_col not in pair_lookup:
                        continue
            
                    p_col, x_col = pair_lookup[
                        result_col
                    ]
            
                    # Show actual P-X columns
                    pair_options[result_col] = (
                        f"{p_col}  ↔  {x_col}"
                    )
            
            
                if pair_options:
            
                    selected_result_col = st.selectbox(
                        "Select P-X Pair",
                        list(pair_options.keys()),
                        format_func=lambda x:
                            pair_options[x],
                        key=f"mismatch_pair_{filename}"
                    )
            
            
                    p_col, x_col = pair_lookup[
                        selected_result_col
                    ]
            
            
                    # =================================================
                    # FILTER SELECTED DATES
                    # =================================================
            
                    selected_df = result_df[
                        result_df[date_col]
                        .dt.date
                        .isin(selected_mismatch_dates)
                    ].copy()
            
            
                    # =================================================
                    # MATCH STATUS
                    # =================================================
            
                    selected_df["Match"] = (
                        selected_df[
                            selected_result_col
                        ]
                        .fillna(False)
                        .astype(bool)
                    )
            
            
                    # =================================================
                    # METRICS
                    # =================================================
            
                    total_blocks = len(
                        selected_df
                    )
            
                    identical_blocks = int(
                        selected_df["Match"].sum()
                    )
            
                    mismatch_blocks = (
                        total_blocks
                        - identical_blocks
                    )
            
            
                    d1, d2, d3 = st.columns(3)
            
                    d1.metric(
                        "Total Blocks",
                        total_blocks
                    )
            
                    d2.metric(
                        "Identical Blocks",
                        identical_blocks
                    )
            
                    d3.metric(
                        "Mismatched Blocks",
                        mismatch_blocks
                    )
            
            
                    # =================================================
                    # ONLY MISMATCHED BLOCKS
                    # =================================================
            
                    mismatch_df = selected_df[
                        selected_df["Match"] == False
                    ].copy()
            
            
                    if not mismatch_df.empty:
            
                        st.markdown(
                            f"#### ❌ Mismatches: {p_col} ↔ {x_col}"
                        )
            
            
                        # ---------------------------------------------
                        # Keep Date + P + X
                        # ---------------------------------------------
            
                        display_df = mismatch_df[
                            [
                                date_col,
                                p_col,
                                x_col,
                                "Match"
                            ]
                        ].copy()
            
            
                        # =================================================
                        # HIGHLIGHT MISMATCHES
                        # =================================================
            
                        def highlight_mismatch_row(row):
            
                            styles = pd.Series(
                                "",
                                index=row.index
                            )
            
            
                            styles[p_col] = (
                                "background-color: #ffcccc;"
                                "color: #9c0006;"
                                "font-weight: bold;"
                            )
            
            
                            styles[x_col] = (
                                "background-color: #ffcccc;"
                                "color: #9c0006;"
                                "font-weight: bold;"
                            )
            
            
                            styles["Match"] = (
                                "background-color: #ff6666;"
                                "color: white;"
                                "font-weight: bold;"
                            )
            
            
                            return styles
            
            
                        st.dataframe(
                            display_df.style.apply(
                                highlight_mismatch_row,
                                axis=1
                            ),
                            use_container_width=True,
                            height=450
                        )
            
            
                    else:
            
                        st.success(
                            "No mismatches found for the "
                            "selected dates and P-X pair."
                        )
            
            else:
            
                st.info(
                    "Select at least one date for mismatch analysis."
                )
    # =====================================================
    # DOWNLOAD
    # =====================================================

    st.markdown(
        "## Download Report"
    )


    excel_file = create_excel_report(
        file_summary_df,
        all_results
    )


    st.download_button(
        label="⬇ Download Final Report",
    
        data=excel_file.getvalue(),
    
        file_name="PX_Comparison_Final_Report.xlsx",
    
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
        type = "primary"
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
