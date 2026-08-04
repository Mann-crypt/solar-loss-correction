import streamlit as st

from modules.validators import validate_uploaded_file
from modules.excel_reader import excel_reader


def show_loss_correction():

    st.title("⛅ Loss Correction")

    uploaded_file = st.file_uploader(
        "Upload Forecast Excel",
        type=["xlsx"],
        key="loss_excel"
    )

    if uploaded_file is None:
        st.info("Please upload an Excel file.")
        return

    try:
        validate_uploaded_file(uploaded_file)

        workbook = excel_reader(uploaded_file)

    except Exception as e:
        st.error(str(e))
        return

    plant_type = st.segmented_control(
        "Plant Type",
        options=["Fixed", "Tracking"],
        default="Fixed"
    )

    st.success("Workbook Loaded Successfully")

    st.write("### Preview")

    st.dataframe(workbook["weather"].head())

    if st.button("Run Correction"):

        st.write(f"Plant Type : {plant_type}")

        # TODO
        # Loss correction starts here
