import streamlit as st

def show_loss_correction():
    st.title("⛅ Loss Correction")

    uploaded_file = st.file_uploader("Yaha Feko!!",
                                    type=["xlsx"],
                                    key="excel_uploader")
    
    validate_uploaded_file(uploaded_file)
    workbook = excel_reader(uploaded_file)
    plant_type = st.segmented_control(
        "Plant Type",
        ["Fixed", "Tracking"]
    )
    if st.button("Run Correction"):

    #st.info("Loss Correction page is under development.")
