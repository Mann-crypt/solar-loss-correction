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

# =========================================================
# MAIN
# =========================================================

uploaded_files = st.file_uploader(
    "Upload CSV or Excel files",
    type=["csv", "xlsx", "xls"],
    accept_multiple_files=True
)


if uploaded_files:

    all_reports = []
    all_results = {}
    processing_errors = []

    # =====================================================
    # PROCESS EVERY FILE
    # =====================================================

    for uploaded_file in uploaded_files:

        try:

            with st.spinner(
                f"Processing {uploaded_file.name}..."
            ):

                # -----------------------------------------
                # Load file
                # -----------------------------------------

                df = load_file(uploaded_file)

                # -----------------------------------------
                # Fix duplicate columns
                # -----------------------------------------

                duplicate_columns = (
                    df.columns.duplicated().sum()
                )

                if duplicate_columns > 0:
                    df = make_columns_unique(df)

                # -----------------------------------------
                # Find Date column
                # -----------------------------------------

                date_col = find_date_column(df)

                if date_col is None:

                    processing_errors.append({
                        "File": uploaded_file.name,
                        "Error": "Date column not found"
                    })

                    continue

                # Convert Date
                df[date_col] = pd.to_datetime(
                    df[date_col],
                    errors="coerce"
                )

                # -----------------------------------------
                # Compare
                # -----------------------------------------

                (
                    result_df,
                    report_df,
                    result_columns,
                    pair_lookup
                ) = compare_data(df)

                # -----------------------------------------
                # Add filename to report
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
                # Store result
                # -----------------------------------------

                all_results[
                    uploaded_file.name
                ] = {
                    "data": result_df,
                    "result_columns": result_columns,
                    "pair_lookup": pair_lookup,
                    "report": report_df
                }

        except Exception as e:

            processing_errors.append({
                "File": uploaded_file.name,
                "Error": str(e)
            })


    # =====================================================
    # PROCESSING ERRORS
    # =====================================================

    if processing_errors:

        st.warning(
            f"{len(processing_errors)} file(s) "
            "could not be processed."
        )

        st.dataframe(
            pd.DataFrame(processing_errors),
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # COMBINE REPORTS
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

    st.markdown("## Overall Summary")

    total_files = len(all_results)

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

    if all_results:

        file_summary = []

        for filename, data in all_results.items():

            report = data["report"]

            if report.empty:

                file_summary.append({
                    "File": filename,
                    "P-X Pairs": 0,
                    "100% Identical": 0,
                    "Pairs With Differences": 0,
                    "Different Blocks": 0,
                    "Status": "NO PAIRS"
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

                "File": filename,

                "P-X Pairs": len(report),

                "100% Identical": identical,

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

        st.markdown(
            "## File Summary"
        )

        st.dataframe(
            file_summary_df,
            use_container_width=True,
            hide_index=True
        )


    # =====================================================
    # COMPLETE P-X REPORT
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


            # ---------------------------------------------
            # File metrics
            # ---------------------------------------------

            file_pairs = len(report)

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
    # DOWNLOAD COMBINED REPORT
    # =====================================================
    
    st.markdown("## Download Report")
    
    output = BytesIO()
    
    # Track whether at least one sheet is written
    sheets_written = 0
    
    with pd.ExcelWriter(
        output,
        engine="openpyxl"
    ) as writer:
    
        # -------------------------------------------------
        # Summary
        # -------------------------------------------------
    
        if all_results:
    
            file_summary_df.to_excel(
                writer,
                sheet_name="Summary",
                index=False
            )
    
            sheets_written += 1
    
    
        # -------------------------------------------------
        # Complete P-X Report
        # -------------------------------------------------
    
        if not combined_report.empty:
    
            combined_report.to_excel(
                writer,
                sheet_name="P-X Report",
                index=False
            )
    
            sheets_written += 1
    
    
        # -------------------------------------------------
        # Mismatch sheets
        # -------------------------------------------------
    
        for filename, data in all_results.items():
    
            result_df = data["data"]
    
            result_columns = data[
                "result_columns"
            ]
    
            if not result_columns:
                continue
    
            # Find mismatched rows
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
    
            # Create a safe Excel sheet name
            safe_name = re.sub(
                r'[\[\]\:\*\?\/\\]',
                "_",
                str(filename)
            )
    
            # Excel allows maximum 31 characters
            sheet_name = (
                safe_name[:25] + "_Mismatch"
            )
    
            # Make sure sheet name isn't too long
            sheet_name = sheet_name[:31]
    
            # Make sure there is no duplicate sheet name
            existing_sheets = writer.book.sheetnames
    
            base_name = sheet_name
            counter = 1
    
            while sheet_name in existing_sheets:
    
                suffix = f"_{counter}"
    
                sheet_name = (
                    base_name[:31 - len(suffix)]
                    + suffix
                )
    
                counter += 1
    
    
            # Write sheet even if there are zero mismatches
            mismatch_df.to_excel(
                writer,
                sheet_name=sheet_name,
                index=True
            )
    
            sheets_written += 1
    
    
        # -------------------------------------------------
        # Safety sheet
        # -------------------------------------------------
    
        if sheets_written == 0:
    
            pd.DataFrame({
                "Message": [
                    "No files were successfully processed.",
                    "Please check the uploaded files."
                ]
            }).to_excel(
                writer,
                sheet_name="Result",
                index=False
            )
    
    
    output.seek(0)
    
    
    st.download_button(
        label="⬇ Download Complete Report",
        data=output.getvalue(),
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
