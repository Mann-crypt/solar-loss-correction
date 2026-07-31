import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy.optimize import differential_evolution
from sklearn.metrics import mean_absolute_percentage_error
import streamlit as st
import streamlit.components.v1 as components
import itertools
from datetime import datetime, timedelta

components.html("""
<script>

let timer;

function resetTimer(){
    clearTimeout(timer);
    timer = setTimeout(()=>{
        window.location.reload();
    },300000); // 5 minutes
}

["mousemove","mousedown","keydown","scroll","touchstart"].forEach(e=>{
    document.addEventListener(e,resetTimer);
});

resetTimer();

</script>
""", height=0)

st.set_page_config(page_title="Solar Suite", layout="wide")

import streamlit as st

# Sidebar CSS
st.markdown("""
<style>
[data-testid="stSidebar"] > div:first-child{
    display:flex;
    flex-direction:column;
    height:100vh;
}

.sidebar-bottom{
    margin-top:auto;
    padding-top:20px;
}
</style>
""", unsafe_allow_html=True)


# ---------------- Logo ----------------
st.sidebar.markdown("""
<h1 style='text-align:center;
background: linear-gradient(90deg,#00c6ff,#0072ff);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
font-size:40px;
font-weight:800;'>
⚡ Solar Suite
</h1>

<p style='text-align:center;color:gray;font-size:14px'>
Loss Correction Platform
</p>
""", unsafe_allow_html=True)

st.sidebar.divider()


# ---------------- Navigation ----------------
if "page" not in st.session_state:
    st.session_state.page = "Loss Correction"

if st.sidebar.button("⛅ Loss Correction", use_container_width=True):
    st.session_state.page = "Loss Correction"

if st.sidebar.button("⏰ RT Correction", use_container_width=True):
    st.session_state.page = "RT Correction"

if st.sidebar.button("🐱‍🏍 Aeromal", use_container_width=True):
    st.session_state.page = "Aeromal"


st.sidebar.divider()

# ---------------- Logout Aeromal ----------------

if st.session_state.get("aeromal_auth", False):
    if st.sidebar.button(
        "🚪 Logout",
        use_container_width=True,
        key="logout"
    ):
        st.session_state.aeromal_auth = False
        st.session_state.page = "Loss Correction"
        st.rerun()

st.sidebar.markdown("</div>", unsafe_allow_html=True)



# ---------------- Credits ----------------
st.sidebar.markdown("""
<div style='text-align:center;color:gray;font-size:13px'>
Developed and Maintained by:<br>
<b>Manjot Singh</b><br><br>

Scripter Writer:<br>
<b>Tushar Sharma</b><br><br>

Challenger:<br>
<b>Aarav Sharma</b><br><br>

Tester:<br>
<b>Jatin Chaturvedi</b><br><br>

Improviser:<br>
<b>Ujala Agrahari</b><br><br>

Suggested by:<br>
<b>Garima Bajetha</b>
</div>
""", unsafe_allow_html=True)

page = st.session_state.page
if page == "Loss Correction":
    st.title("Pakima Pakam Ravi, 3-4 Loss Correction kar chuke hai!!😎")

    uploaded_file = st.file_uploader(
        "Yaha Feko!!",
        type=["xlsx"],
        key="excel_uploader"
    )
    if uploaded_file is None:
        st.info("Pehle File toh upload karo!!!")
        st.stop()
        
    # ---------- Detect new uploaded file ----------
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = uploaded_file.name
    
    elif st.session_state.last_uploaded_file != uploaded_file.name:
    
        # Clear cached functions
        st.cache_data.clear()
    
        # Remove previous optimization
        st.session_state.pop("params", None)
        st.session_state.pop("run_model", None)
    
        # Remove all user-editable values
        for key in [
            "loss",
            "dhi",
            "start",
            "end",
            "max",
            "east",
            "west",
        ]:
            st.session_state.pop(key, None)
    
        st.session_state.last_uploaded_file = uploaded_file.name
    
        st.rerun()
    # Read workbook
    xls = pd.ExcelFile(uploaded_file)
    
    # Detect workbook type
    is_cluster = "Fixed-CL1" in xls.sheet_names
    
    if is_cluster:
        #st.success("Arey Yarrr!! phir se Cluster")
        sheet = "Fixed-CL1"
        ghi_cols = ["CL1-GHI", "CL2-GHI", "CL3-GHI", "CL4-GHI", "CL5-GHI"]
    else:
        #st.success("Arey Waah!! no Cluster")
        sheet = "Fixed"
        ghi_cols = ["GHI_Forecast"]
    
    df_fix = pd.read_excel(uploaded_file, sheet_name=sheet, header=[1])
    df_fix.columns = df_fix.columns.str.strip()
    df_fix["Actual"] = df_fix["Actual"].fillna(0)
    
    # Remove empty rows
    null_indices = df_fix[df_fix["Date"].isna()].index
    if len(null_indices) > 0:
        first_null = df_fix.index.get_loc(null_indices[0])
        df_fix = df_fix.iloc[:first_null]
    
    # Keep only first 96 blocks
    df_fix = df_fix.iloc[:96].copy()
    
    st.subheader("Input Data")
    
    input_df = df_fix[ghi_cols + ["Actual"]].copy()
    
    original_df = input_df.copy()
    
    edited_df = st.data_editor(
        input_df,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="editor"
    )
    
    edited_numeric = edited_df.copy()
    
    edited_numeric[ghi_cols] = edited_numeric[ghi_cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)
    
    edited_numeric["Actual"] = (
        pd.to_numeric(edited_numeric["Actual"], errors="coerce")
        .fillna(0)
    )
    
    changed_rows = (
        edited_numeric.ne(original_df.fillna(0))
    ).any(axis=1)
    
    if changed_rows.any():
        st.toast(
            f"✨ {changed_rows.sum()} rows updated successfully!",
            icon="✅"
        )
    
    edited_df = edited_df.iloc[:96].reset_index(drop=True)
    
    # Convert everything to numeric.
    # Any text or invalid value becomes 0.
    edited_df[ghi_cols] = edited_df[ghi_cols].apply(
        pd.to_numeric,
        errors="coerce"
    ).fillna(0)
    
    edited_df["Actual"] = (
        pd.to_numeric(edited_df["Actual"], errors="coerce")
        .fillna(0)
    )
    
    # Update df_fix only once
    df_fix.loc[:, ghi_cols] = edited_df[ghi_cols].values
    df_fix.loc[:, "Actual"] = edited_df["Actual"].values
    
    plant_type = st.pills(
        "Select Plant Type",
        [
            "🏗️ Fixed",
            "🔄 Tracking"
        ],
        default="🏗️ Fixed"
    )
    
    if "run_model" not in st.session_state:
        st.session_state.run_model = False
    
    if st.button("🚀 Dabao magar pyaar se!!", use_container_width=True, type="primary"):
        st.session_state.pop("params", None)   # Delete old optimized values
        st.session_state.run_model = True
    
    if st.session_state.run_model:
        if is_cluster:
            if plant_type == "🏗️ Fixed":
                df = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=[1], usecols=range(8))
                null_indices = df[df['Module Type'].isna()].index
                first_null_pos = df.index.get_loc(null_indices[0])
                df = df.iloc[:first_null_pos]
                df.columns = df.columns.str.strip()
                df_w = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=2, usecols=[12, 13, 14, 15, 16])
                df_st = pd.read_excel(uploaded_file, sheet_name="Forecast Config", header=[8])
                lat = float(df_st.loc[0, "Lat"])
                df_tilt = pd.read_excel(uploaded_file, sheet_name="Config Tilt Angle", header=[7])
                df_tilt.columns = df_tilt.columns.str.strip()
                null_indices = df_tilt[df_tilt['Fixed'].isna()].index
                first_null_pos = df_tilt.index.get_loc(null_indices[0])
                df_tilt = df_tilt.iloc[:first_null_pos]
                df_tilt = df_tilt.dropna(how='all', axis=1)
                df_tilt = df_tilt.rename(columns={
                    'Unnamed: 2': 'Month_Num',
                    'Unnamed: 3': 'Month',
                })
                month_lookup = df_tilt.set_index('Month')['Fixed'].to_dict()
                df_ghi = pd.read_excel(uploaded_file, sheet_name="Result", usecols=[0, 1, 2, 3, 4, 5])
                df_ghi = df_ghi.fillna(0)
                df_fix = pd.read_excel(uploaded_file, sheet_name="Fixed-CL1", header=[1])
                df_fix.columns = df_fix.columns.str.strip()
                null_indices = df_fix[df_fix['Date'].isna()].index
                first_null_pos = df_fix.index.get_loc(null_indices[0])
                df_fix = df_fix.iloc[:first_null_pos]
                
                df_fix["Date"] = pd.Timestamp.today()
                first_date = pd.Timestamp.today().replace(month=1, day=1).normalize()
                
                df_fix["Declination Angle ∆"] = 23.45 * (
                    np.sin(
                        np.radians(
                            360 * (284 + (df_fix["Date"] - first_date).dt.days + 1) / 365
                        )
                    )
                )
                df_fix["Elevation angle a"] = (90 - lat + df_fix["Declination Angle ∆"])
                df_fix["Tilt Angle b"] = df_fix["Date"].dt.strftime('%B').map(month_lookup)
                df_fix["a+b"] = df_fix["Elevation angle a"] + df_fix["Tilt Angle b"]
                df_fix["SIN(a+b)"] = np.sin(np.radians(df_fix["a+b"]))
                df_fix["Sin(a)"] = np.sin(np.radians(df_fix["Elevation angle a"]))
                df_fix["GHI*sin(a)"] = df_fix["CL1-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)"] = df_fix["CL1-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed"] = df_fix["GHI*sin(a+b)"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL2"] = df_fix["CL2-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL2"] = df_fix["CL2-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL2"] = df_fix["GHI*sin(a+b)-CL2"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL3"] = df_fix["CL3-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL3"] = df_fix["CL3-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL3"] = df_fix["GHI*sin(a+b)-CL3"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL4"] = df_fix["CL4-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL4"] = df_fix["CL4-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL4"] = df_fix["GHI*sin(a+b)-CL4"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL5"] = df_fix["CL5-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL5"] = df_fix["CL5-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL5"] = df_fix["GHI*sin(a+b)-CL5"] / df_fix["Sin(a)"]
                
                
                # Maximum possible loss
                max_loss = df["Standard PV Efficiency (%)"].min()
                
                #peak_error = abs(actual_peak - predicted_peak) / actual_peak * 100
                
                results = []
                
                for loss in np.arange(0, max_loss + 0.01, 0.1):
                
                    df["Efficiency Losses(%)"] = loss
                    df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                    df_weight = pd.DataFrame({
                        "CL-1" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-1"].values[0:1],
                        "CL-2" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-2"].values[0:1],
                        "CL-3" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-3"].values[0:1],
                        "CL-4" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-4"].values[0:1],
                        "CL-5" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-5"].values[0:1],
                    })
                
                    df_fix["CL1_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed"] * np.sum(df_weight["CL-1"])
                    ) / 1000000
                
                    df_fix["CL2_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL2"] * np.sum(df_weight["CL-2"])
                    ) / 1000000
                
                    df_fix["CL3_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL3"] * np.sum(df_weight["CL-3"])
                    ) / 1000000
                
                    df_fix["CL4_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL4"] * np.sum(df_weight["CL-4"])
                    ) / 1000000
                
                    df_fix["CL5_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL5"] * np.sum(df_weight["CL-5"])
                    ) / 1000000
                
                    df_fix["Total Power (CL1+CL2+…)"] = df_fix["CL1_Fixed Power=I*Ƞ*A"] + df_fix["CL2_Fixed Power=I*Ƞ*A"] + df_fix["CL3_Fixed Power=I*Ƞ*A"] + df_fix["CL4_Fixed Power=I*Ƞ*A"] + df_fix["CL5_Fixed Power=I*Ƞ*A"]
                    
                
                    # Peak power comparison
                    actual_peak = df_fix["Actual"].max()
                    predicted_peak = df_fix["Total Power (CL1+CL2+…)"].max()
                
                    peak_error = abs(actual_peak - predicted_peak)
                
                    results.append({
                        "Efficiency Loss (%)": loss,
                        "Actual Peak": actual_peak,
                        "Predicted Peak": predicted_peak,
                        "Peak Error": peak_error
                    })
                
                results_df = pd.DataFrame(results)
                
                # Get efficiency loss with least Peak Error
                best_loss = results_df.loc[
                    results_df["Peak Error"].idxmin(),
                    "Efficiency Loss (%)"
                ]
                
                # Assign best efficiency loss
                df["Efficiency Losses(%)"] = best_loss
                
                # Recalculate dependent columns
                df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                df_weight["CL-1"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-1"].values[0:1]
                df_weight["CL-2"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-2"].values[0:1]
                df_weight["CL-3"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-3"].values[0:1]
                df_weight["CL-4"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-4"].values[0:1]
                df_weight["CL-5"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-5"].values[0:1]
                    
                df_fix["CL1_Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed"] * np.sum(df_weight["CL-1"])
                ) / 1000000
                
                df_fix["CL2_Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed-CL2"] * np.sum(df_weight["CL-2"])
                ) / 1000000
                
                df_fix["CL3_Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed-CL3"] * np.sum(df_weight["CL-3"])
                ) / 1000000
                
                df_fix["CL4_Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed-CL4"] * np.sum(df_weight["CL-4"])
                ) / 1000000
                
                df_fix["CL5_Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed-CL5"] * np.sum(df_weight["CL-5"])
                ) / 1000000
                
                df_fix["Total Power (CL1+CL2+…)"] = df_fix["CL1_Fixed Power=I*Ƞ*A"] + df_fix["CL2_Fixed Power=I*Ƞ*A"] + df_fix["CL3_Fixed Power=I*Ƞ*A"] + df_fix["CL4_Fixed Power=I*Ƞ*A"] + df_fix["CL5_Fixed Power=I*Ƞ*A"]
                st.metric(
                    "Efficiency Loss",
                    f"{best_loss:.2f}%"
                )
                
                display_df = df[
                    [
                        "Module Type",
                        "Standard PV Efficiency (%)",
                        "Efficiency Losses(%)",
                        "Net Efficiency (%)",
                        "Total area(m2)"
                    ]
                ].copy()
                
                num_cols = display_df.select_dtypes(include="number").columns
                display_df[num_cols] = display_df[num_cols].round(2)
                
                with st.expander("🔍 View Efficiency Calculations"):
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                    
                x = np.arange(1, 97)
        
                fig = go.Figure()
        
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=df_fix["Total Power (CL1+CL2+…)"],
                        mode="lines",
                        name="Forecast",
                        line=dict(color="#3B82F6", width=3),
                    )
                )
        
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=df_fix["Actual"],
                        mode="lines",
                        name="Actual",
                        line=dict(color="#EF4444", width=3),
                    )
                )
        
                fig.update_layout(
                    title="Forecast vs Actual Power",
                    template="plotly_white",
                    height=500,
                    hovermode="x unified",
                    #xaxis=dict(
                        #title="15 Minute Block",
                        #dtick=4
                    #),
                    yaxis=dict(
                        title="Power (MW)"
                    ),
                    legend=dict(
                        orientation="h",
                        y=1.08,
                        x=0
                    ),
                    margin=dict(l=20, r=20, t=60, b=20)
                )
        
                st.plotly_chart(fig, use_container_width=True)
            elif plant_type == "🔄 Tracking":
                df = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=[1], usecols=range(8))
                null_indices = df[df['Module Type'].isna()].index
                first_null_pos = df.index.get_loc(null_indices[0])
                df = df.iloc[:first_null_pos]
                df.columns = df.columns.str.strip()
                df_w = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=2, usecols=[12, 13, 14, 15, 16])
                df_st = pd.read_excel(uploaded_file, sheet_name="Forecast Config", header=[8])
                lat = float(df_st.loc[0, "Lat"])
                df_tilt = pd.read_excel(uploaded_file, sheet_name="Config Tilt Angle", header=[7])
                df_tilt.columns = df_tilt.columns.str.strip()
                null_indices = df_tilt[df_tilt['Fixed'].isna()].index
                first_null_pos = df_tilt.index.get_loc(null_indices[0])
                df_tilt = df_tilt.iloc[:first_null_pos]
                df_tilt = df_tilt.dropna(how='all', axis=1)
                df_tilt = df_tilt.rename(columns={
                    'Unnamed: 2': 'Month_Num',
                    'Unnamed: 3': 'Month',
                })
                #month_lookup = df_tilt.set_index('Month')['Fixed'].to_dict()
                
                df_fix["Date"] = pd.Timestamp.today()
                first_date = pd.Timestamp.today().replace(month=1, day=1).normalize()
                
                df_fix["Declination Angle ∆"] = 23.45 * (
                    np.sin(
                        np.radians(
                            360 * (284 + (df_fix["Date"] - first_date).dt.days + 1) / 365
                        )
                    )
                )
                df_fix["Elevation angle a"] = (90 - lat + df_fix["Declination Angle ∆"])
                #df_fix["Tilt Angle b"] = df_fix["Date"].dt.strftime('%B').map(month_lookup)
                df_fix["a+b"] = df_fix["Elevation angle a"] + 0
                df_fix["SIN(a+b)"] = np.sin(np.radians(df_fix["a+b"]))
                df_fix["Sin(a)"] = np.sin(np.radians(df_fix["Elevation angle a"]))
                df_fix["GHI*sin(a)"] = df_fix["CL1-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)"] = df_fix["CL1-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed"] = df_fix["GHI*sin(a+b)"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL2"] = df_fix["CL2-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL2"] = df_fix["CL2-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL2"] = df_fix["GHI*sin(a+b)-CL2"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL3"] = df_fix["CL3-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL3"] = df_fix["CL3-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL3"] = df_fix["GHI*sin(a+b)-CL3"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL4"] = df_fix["CL4-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL4"] = df_fix["CL4-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL4"] = df_fix["GHI*sin(a+b)-CL4"] / df_fix["Sin(a)"]
                df_fix["GHI*sin(a)-CL5"] = df_fix["CL5-GHI"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)-CL5"] = df_fix["CL5-GHI"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed-CL5"] = df_fix["GHI*sin(a+b)-CL5"] / df_fix["Sin(a)"]
                
                
                # Maximum possible loss
                max_loss = df["Standard PV Efficiency (%)"].min()
                
                results = []
                
                for loss in np.arange(0, max_loss + 0.01, 0.1):
                
                    df["Efficiency Losses(%)"] = loss
                    df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                    df_weight = pd.DataFrame({
                        "CL-1" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-1"].values[0:1],
                        "CL-2" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-2"].values[0:1],
                        "CL-3" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-3"].values[0:1],
                        "CL-4" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-4"].values[0:1],
                        "CL-5" : ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-5"].values[0:1],
                    })
                
                    df_fix["CL1_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed"] * np.sum(df_weight["CL-1"])
                    ) / 1000000
                
                    df_fix["CL2_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL2"] * np.sum(df_weight["CL-2"])
                    ) / 1000000
                
                    df_fix["CL3_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL3"] * np.sum(df_weight["CL-3"])
                    ) / 1000000
                
                    df_fix["CL4_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL4"] * np.sum(df_weight["CL-4"])
                    ) / 1000000
                
                    df_fix["CL5_Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed-CL5"] * np.sum(df_weight["CL-5"])
                    ) / 1000000
                
                    df_fix["Total Power (CL1+CL2+…)"] = df_fix["CL1_Fixed Power=I*Ƞ*A"] + df_fix["CL2_Fixed Power=I*Ƞ*A"] + df_fix["CL3_Fixed Power=I*Ƞ*A"] + df_fix["CL4_Fixed Power=I*Ƞ*A"] + df_fix["CL5_Fixed Power=I*Ƞ*A"]
                    
                
                    # Peak power comparison
                    actual_peak = df_fix["Actual"].max()
                    predicted_peak = df_fix["Total Power (CL1+CL2+…)"].max()
                
                    peak_error = abs(actual_peak - predicted_peak)
                
                    results.append({
                        "Efficiency Loss (%)": loss,
                        "Actual Peak": actual_peak,
                        "Predicted Peak": predicted_peak,
                        "Peak Error": peak_error
                    })
                
                results_df = pd.DataFrame(results)
                
                # Get efficiency loss with least Peak Error
                best_loss = results_df.loc[
                    results_df["Peak Error"].idxmin(),
                    "Efficiency Loss (%)"
                ]
                
                # Assign best efficiency loss
                df["Efficiency Losses(%)"] = best_loss
                # Recalculate dependent columns
                df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                df_weight["CL-1"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-1"].values[0:1]
                df_weight["CL-2"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-2"].values[0:1]
                df_weight["CL-3"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-3"].values[0:1]
                df_weight["CL-4"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-4"].values[0:1]
                df_weight["CL-5"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-5"].values[0:1]
                    
                
                # ------------------ Read Data ------------------
    
                df_bcal1 = pd.read_excel(uploaded_file, sheet_name="Backend Cal CL1")
                df_bcal2 = pd.read_excel(uploaded_file, sheet_name="Backend Cal CL2")
                df_bcal3 = pd.read_excel(uploaded_file, sheet_name="Backend Cal CL3")
                df_bcal4 = pd.read_excel(uploaded_file, sheet_name="Backend Cal CL4")
                df_bcal5 = pd.read_excel(uploaded_file, sheet_name="Backend Cal CL5")
                df_trac = pd.read_excel(uploaded_file, sheet_name="Tracking", header=[1])
    
                backend_list = [
                    df_bcal1,
                    df_bcal2,
                    df_bcal3,
                    df_bcal4,
                    df_bcal5
                ]
                
                ghi_cols = [
                    "CL1-GHI",
                    "CL2-GHI",
                    "CL3-GHI",
                    "CL4-GHI",
                    "CL5-GHI"
                ]
                
                weight_cols = [
                    "CL-1",
                    "CL-2",
                    "CL-3",
                    "CL-4",
                    "CL-5"
                ]
                
                # ------------------ Objective Function ------------------
                actual = df_fix["Actual"].to_numpy(dtype=np.float64)
    
                mask = actual != 0
                actual = actual[mask]
                
                blocks = backend_list[0]["Block No."].to_numpy(dtype=np.float64)
                
                ghi_arrays = [
                    df_fix[col].to_numpy(dtype=np.float64)
                    for col in ghi_cols
                ]
                
                weight_sum = np.array([
                    df_weight["CL-1"].sum(),
                    df_weight["CL-2"].sum(),
                    df_weight["CL-3"].sum(),
                    df_weight["CL-4"].sum(),
                    df_weight["CL-5"].sum(),
                ], dtype=np.float64)
                
                def objective(x):
                    try:
                        DHI = int(round(x[0]))
                        GHI_Starting_Block = int(round(x[1]))
                        GHI_Ending_Block = int(round(x[2]))
                        GHI_Max_Block = int(round(x[3]))
                        Tracking_angle_lim_E = int(round(x[4]))
                        Tracking_angle_lim_W = int(round(x[5]))
                    
                        # Invalid combinations
                        if (
                            GHI_Starting_Block >= GHI_Max_Block
                            or GHI_Max_Block >= GHI_Ending_Block
                        ):
                            return 1e9
                    
                        m1 = 90 / (GHI_Starting_Block - 1 - GHI_Max_Block)
                        m2 = 90 / (GHI_Ending_Block + 1 - GHI_Max_Block)
                    
                        predictions = []
        
                        blocks = backend_list[0]["Block No."]
                        
                        zenith = np.where(
                            blocks <= GHI_Max_Block,
                            np.minimum(89, m1 * (blocks - GHI_Max_Block)),
                            np.minimum(89, m2 * (blocks - GHI_Max_Block))
                        )
                        
                        panel = np.where(
                            blocks < GHI_Max_Block,
                            np.minimum(zenith, abs(Tracking_angle_lim_E)),
                            np.where(
                                (blocks > GHI_Max_Block) & (zenith > Tracking_angle_lim_W),
                                Tracking_angle_lim_W,
                                zenith
                            )
                        )
                        
                        cos_alpha = np.cos(np.radians(panel))
                        
                        cos_alpha = np.clip(cos_alpha, 1e-6, None)
    
                        prediction = np.zeros_like(blocks, dtype=np.float64)
    
                        for i, ghi in enumerate(ghi_arrays):
                        
                            dhi = ghi * DHI / 100
                        
                            dni = (ghi - dhi) / cos_alpha
                        
                            prediction += (
                                dni * weight_sum[i]
                            ) / 1_000_000
                    
                        # Comparision
                    
                    
                        # Consider only daylight blocks
                        #mask = ghi_cols > 50
                    
                        prediction = prediction[mask]
                    
                        # Higher weights near peak generation
                    
                        # Weighted RMSE
                        block_error = np.mean(np.abs(actual - prediction)) / actual.max()
                    
                        # Peak error
                        peak_error = abs(actual.max() - prediction.max()) / actual.max()
                    
                        # Daily energy error
                        energy_error = abs(actual.sum() - prediction.sum()) / actual.sum()
                    
                        score = (
                            0.80 * block_error +
                            0.10 * peak_error +
                            0.10 * energy_error
                        )
                        if (
                            np.isnan(prediction).any()
                            or np.isinf(prediction).any()
                        ):
                            return 1e9
                        if actual.max() == 0:
                            return 1e9
                    
                        return score
                    except Exception as e:
                        print(e)
                        import traceback
                        traceback.print_exc()
                        raise
                
                
                # ------------------ Parameter Bounds ------------------
                
                bounds = [
                    (0, 10),      # DHI (%)
                    (10, 30),     # GHI Starting Block
                    (65, 80),     # GHI Ending Block
                    (47, 53),     # GHI Max Block
                    (10, 70),     # Tracking East Limit
                    (10, 70)      # Tracking West Limit
                ]
                
                # ------------------ Optimization ------------------
        
                import random
        
                if "params" not in st.session_state:
        
                    progress = st.progress(0)
                    status = st.empty()
        
                    quotes = [
                        "☕ Vo kehte the kya ho tum, aaj hum kehte hai tum kya ho be?",
                        "🌦 Aapka mann nahi kar raha bahar jaane ka?..",
                        "😊 Jinke ghar sheeshe ke bane hote hai vo basement mai kapde change krte h...",
                        "😋 Aromatic Rose Latte with Frothy Milk pine ka mann hor hai na...",
                        "🥛 Garmi mai daalo dudh mai Ice🧊 Dudh bangya Very Nice - Dudh Dudh Dudh Dudh...",
                        "🌟 Aapke face pr toh Modiji se bhi jyda glow hai..",
                        "😁 Horaha hai benstokes Kaan mai ghusjao insaan ke...",
                        "😗 Muskuraiye aap MAL mai hai...",
                        "🥱 Hum na hote toh Operations ka kya hota?..",
                        "😎 6:30 hote hi Billu MAL se faraar...",
                        "😇 Guruji ne ek baat kahi thi....",
                        "🎼 Karna hai kuchh kaam M se gaao...",
                        "😠 Nahi karni Loss Correction, Now what to do?...",
                        "💸 Iss Job ko chhod or chhod kar ameer ho.."
                    ]
        
                    MAX_ITER = 100
                    last_quote = {"text": None}
        
                    def random_quote():
                        available = [q for q in quotes if q != last_quote["text"]]
                        q = random.choice(available)
                        last_quote["text"] = q
                        return q
                        
                    generation = {"count": 0}
                    current_quote = {"text": random_quote()}
        
                    status.info(current_quote["text"])
        
                    def callback(xk, convergence):
        
                        generation["count"] += 1
                        progress.progress(generation["count"] / MAX_ITER)
        
                        # Change quote every 7 generations
                        if generation["count"] % 20 == 1:
                            current_quote["text"] = random_quote()
        
                        status.info(
                            f"{current_quote['text']}\n\n"
                            f"Generation {generation['count']} / {MAX_ITER}"
                        )
        
                        return False
        
                    with st.spinner("Ho raha hai aap tab tak saath waale se baat karlo...🗣"):
        
                        result = differential_evolution(
                            objective,
                            bounds=bounds,
                            strategy="best1bin",
                            maxiter=MAX_ITER,
                            popsize=15,
                            tol=0.001,
                            mutation=(0.5,1),
                            recombination=0.7,
                            seed=42,
                            polish=True,
                            workers=1,
                            callback=callback
                        )
        
                    progress.empty()
                    status.success("✅ Dekha Kitni Jaldi Hogaya!")
                    
    
                    best = np.round(result.x).astype(int)
                    
        
                    st.session_state.params = {
                        "loss": float(best_loss),
                        "DHI": int(best[0]),
                        "start": int(best[1]),
                        "end": int(best[2]),
                        "max": int(best[3]),
                        "east": int(best[4]),
                        "west": int(best[5]),
                    }
                    st.session_state.loss = st.session_state.params["loss"]
                    st.session_state.dhi = st.session_state.params["DHI"]
                    st.session_state.start = st.session_state.params["start"]
                    st.session_state.end = st.session_state.params["end"]
                    st.session_state.max = st.session_state.params["max"]
                    st.session_state.east = st.session_state.params["east"]
                    st.session_state.west = st.session_state.params["west"]
                
                #print("Error Score:", result.fun)
                #print("DHI:", dhi)
                #print("GHI Starting Block:", GHI_Starting_Block)
                #print("GHI Ending Block:", GHI_Ending_Block)
                #print("GHI Max Block:", GHI_Max_Block)
                #print("Tracking East Limit:", Tracking_angle_lim_E)
                #print("Tracking West Limit:", Tracking_angle_lim_W)
                #print("Efficiency Loss:", best_loss)
        
                if "params" in st.session_state:
                    defaults = {
                        "loss": st.session_state.params["loss"],
                        "dhi": st.session_state.params["DHI"],
                        "start": st.session_state.params["start"],
                        "end": st.session_state.params["end"],
                        "max": st.session_state.params["max"],
                        "east": st.session_state.params["east"],
                        "west": st.session_state.params["west"],
                    }
        
                    for k, v in defaults.items():
                        if k not in st.session_state:
                            st.session_state[k] = v
                    
                    st.subheader("Optimized Parameters")
        
                    best_loss = st.number_input(
                        "Efficiency Loss (%)",
                        step=0.1,
                        key="loss"
                    )
        
                    col1, col2, col3 = st.columns(3)
        
                    DHI = col1.number_input(
                        "DHI (%)",
                        step=1,
                        key="dhi"
                    )
        
                    GHI_Starting_Block = col2.number_input(
                        "Starting Block",
                        step=1,
                        key="start"
                    )
        
                    GHI_Ending_Block = col3.number_input(
                        "Ending Block",
                        step=1,
                        key="end"
                    )
        
                    col1, col2, col3 = st.columns(3)
        
                    GHI_Max_Block = col1.number_input(
                        "Max Block",
                        step=1,
                        key="max"
                    )
        
                    Tracking_angle_lim_E = col2.number_input(
                        "East Limit",
                        step=1,
                        key="east"
                    )
        
                    Tracking_angle_lim_W = col3.number_input(
                        "West Limit",
                        step=1,
                        key="west"
                    )
        
                    #best_loss = st.session_state.loss
                    #DHI = st.session_state.dhi
                    #GHI_Starting_Block = st.session_state.start
                    #GHI_Ending_Block = st.session_state.end
                    #GHI_Max_Block = st.session_state.max
                    #Tracking_angle_lim_E = st.session_state.east
                    #Tracking_angle_lim_W = st.session_state.west
        
        
                
                    # ------------------ Final Calculation Using Best Parameters ------------------
                    df["Efficiency Losses(%)"] = best_loss
    
                    # Recalculate
                    df["Net Efficiency (%)"] = (
                        df["Standard PV Efficiency (%)"]
                        - df["Efficiency Losses(%)"]
                    )
                    
                    display_df = df[
                        [
                            "Module Type",
                            "Standard PV Efficiency (%)",
                            "Efficiency Losses(%)",
                            "Net Efficiency (%)",
                            "Total area(m2)"
                        ]
                    ].copy()
                    
                    num_cols = display_df.select_dtypes(include="number").columns
                    display_df[num_cols] = display_df[num_cols].round(2)
                
                    with st.expander("🔍 View Efficiency Calculations"):
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                        )
                    
                    m1 = 90 / (GHI_Starting_Block - 1 - GHI_Max_Block)
                    m2 = 90 / (GHI_Ending_Block + 1 - GHI_Max_Block)
                    
                    blocks = backend_list[0]["Block No."]
        
                    zenith = np.where(
                        blocks <= GHI_Max_Block,
                        np.minimum(89, m1 * (blocks - GHI_Max_Block)),
                        np.minimum(89, m2 * (blocks - GHI_Max_Block))
                    )
                    
                    panel = np.where(
                        blocks < GHI_Max_Block,
                        np.minimum(zenith, abs(Tracking_angle_lim_E)),
                        np.where(
                            (blocks > GHI_Max_Block) & (zenith > Tracking_angle_lim_W),
                            Tracking_angle_lim_W,
                            zenith
                        )
                    )
                    
                    cos_alpha = np.cos(np.radians(panel))
    
                    df_weight["CL-1"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-1"].values[0:1]
                    df_weight["CL-2"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-2"].values[0:1]
                    df_weight["CL-3"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-3"].values[0:1]
                    df_weight["CL-4"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-4"].values[0:1]
                    df_weight["CL-5"] = ((df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100) * df_w["CL-5"].values[0:1]
                    
                    weights = df_weight.sum()
                    
                    forecast = np.zeros(len(df_fix))
                    
                    for ghi_col, weight_col in zip(
                            ghi_cols,
                            weight_cols):
                    
                        ghi = df_fix[ghi_col].to_numpy()
                    
                        dhi = ghi * DHI / 100
                    
                        dni = (ghi - dhi) / cos_alpha
                    
                        forecast += (
                            dni * weights[weight_col]
                        ) / 1_000_000
                    
                    df_trac["Fixed Power=I*Ƞ*A"] = forecast
                    x = np.arange(1, 97)
            
                    fig = go.Figure()
        
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=df_trac["Fixed Power=I*Ƞ*A"],
                            mode="lines",
                            name="Forecast",
                            line=dict(color="#2563EB", width=3),
                        )
                    )
        
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=df_fix["Actual"],
                            mode="lines",
                            name="Actual",
                            line=dict(color="#DC2626", width=3),
                        )
                    )
        
                    fig.update_layout(
                        title="Forecast vs Actual Power",
                        template="plotly_white",
                        height=500,
                        hovermode="x unified",
                        #xaxis=dict(
                            #title="15 Minute Block",
                            #dtick=4
                        #),
                        yaxis=dict(
                            title="Power (MW)"
                        ),
                        legend=dict(
                            orientation="h",
                            y=1.08,
                            x=0
                        ),
                        margin=dict(l=20, r=20, t=60, b=20)
                    )
        
                    st.plotly_chart(fig, use_container_width=True)
    
        else: 
            if plant_type == "🏗️ Fixed":
                df = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=[1])
                df.columns = df.columns.str.strip()
                null_indices = df[df['Module Type'].isna()].index
                first_null_pos = df.index.get_loc(null_indices[0])
                df = df.iloc[:first_null_pos]
        
                df_st = pd.read_excel(uploaded_file, sheet_name="Forecast Config", header=[8])
                lat = float(df_st.loc[0, "Lat"])
        
                df_tilt = pd.read_excel(uploaded_file, sheet_name="Config Tilt Angle", header=[7])
                df_tilt.columns = df_tilt.columns.str.strip()
                null_indices = df_tilt[df_tilt['Fixed'].isna()].index
                df_tilt["Fixed"] = df_tilt["Fixed"].fillna(0)
                first_null_pos = df_tilt.index.get_loc(null_indices[0])
                df_tilt = df_tilt.iloc[:first_null_pos]
                df_tilt = df_tilt.dropna(how='all', axis=1)
                df_tilt = df_tilt.rename(columns={
                    'Unnamed: 2': 'Month_Num',
                    'Unnamed: 3': 'Month',
                })
                month_lookup = df_tilt.set_index('Month')['Fixed'].to_dict()
        
                df_fix = pd.read_excel(uploaded_file, sheet_name="Fixed", header=[1])
                df_fix["GHI_Forecast"] = edited_df["GHI_Forecast"]
                df_fix["Actual"] = edited_df["Actual"]
                df_fix.columns = df_fix.columns.str.strip()
                null_indices = df_fix[df_fix['Date'].isna()].index
                first_null_pos = df_fix.index.get_loc(null_indices[0])
                df_fix = df_fix.iloc[:first_null_pos]
        
                df_fix["Date"] = pd.Timestamp.today()
                first_date = pd.Timestamp.today().replace(month=1, day=1).normalize()
        
                df_fix["Declination Angle ∆"] = 23.45 * (
                    np.sin(
                        np.radians(
                            360 * (284 + (df_fix["Date"] - first_date).dt.days + 1) / 365
                        )
                    )
                )
        
                df_fix["Elevation angle a"] = (90 - lat + df_fix["Declination Angle ∆"])
                df_fix["Tilt Angle b"] = df_fix["Date"].dt.strftime('%B').map(month_lookup)
                df_fix["a+b"] = df_fix["Elevation angle a"] + df_fix["Tilt Angle b"]
                df_fix["SIN(a+b)"] = np.sin(np.radians(df_fix["a+b"]))
                df_fix["Sin(a)"] = np.sin(np.radians(df_fix["Elevation angle a"]))
                df_fix["GHI*sin(a)"] = df_fix["GHI_Forecast"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)"] = df_fix["GHI_Forecast"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed"] = df_fix["GHI*sin(a+b)"] / df_fix["Sin(a)"]
        
                # Maximum possible loss
                max_loss = df["Standard PV Efficiency (%)"].min()
        
                #peak_error = abs(actual_peak - predicted_peak) / actual_peak * 100
        
                results = []
        
                for loss in np.arange(0, max_loss + 0.01, 0.1):
        
                    df["Efficiency Losses(%)"] = loss
                    df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                    df["Eff Area"] = (df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100
            
                    df_fix["Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed"] * np.sum(df["Eff Area"])
                    ) / 1000000
        
                    # Peak power comparison
                    actual_peak = df_fix["Actual"].max()
                    predicted_peak = df_fix["Fixed Power=I*Ƞ*A"].max()
        
                    peak_error = abs(actual_peak - predicted_peak)
        
                    results.append({
                        "Efficiency Loss (%)": loss,
                        "Actual Peak": actual_peak,
                        "Predicted Peak": predicted_peak,
                        "Peak Error": peak_error
                    })
                    results_df = pd.DataFrame(results)
        
                # Get efficiency loss with least Peak Error
                best_loss = results_df.loc[
                    results_df["Peak Error"].idxmin(),
                    "Efficiency Loss (%)"
                ]
        
                # Assign best efficiency loss
                df["Efficiency Losses(%)"] = best_loss
        
                # Recalculate dependent columns
                df["Net Efficiency (%)"] = (
                    df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                )
        
                df["Eff Area"] = (
                    df["Total area(m2)"] * df["Net Efficiency (%)"]
                ) / 100
        
                # Recalculate final power using the best efficiency loss
                df_fix["Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed"] * df["Eff Area"].sum()
                ) / 1_000_000
        
                print(f"Best Efficiency Loss = {best_loss:.2f}%")
                st.metric(
                    "Efficiency Loss",
                    f"{best_loss:.2f}%"
                )
                
                display_df = df[
                    [
                        "Module Type",
                        "Standard PV Efficiency (%)",
                        "Efficiency Losses(%)",
                        "Net Efficiency (%)",
                        "Total area(m2)"
                    ]
                ].copy()
                
                num_cols = display_df.select_dtypes(include="number").columns
                display_df[num_cols] = display_df[num_cols].round(2)
            
                with st.expander("🔍 View Efficiency Calculations"):
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True,
                    )
                
                num_cols = display_df.select_dtypes(include="number").columns
                display_df[num_cols] = display_df[num_cols].round(2)
                    
                x = np.arange(1, 97)
        
                fig = go.Figure()
        
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=df_fix["Fixed Power=I*Ƞ*A"],
                        mode="lines",
                        name="Forecast",
                        line=dict(color="#3B82F6", width=3),
                    )
                )
        
                fig.add_trace(
                    go.Scatter(
                        x=x,
                        y=df_fix["Actual"],
                        mode="lines",
                        name="Actual",
                        line=dict(color="#EF4444", width=3),
                    )
                )
        
                fig.update_layout(
                    title="Forecast vs Actual Power",
                    template="plotly_white",
                    height=500,
                    hovermode="x unified",
                    #xaxis=dict(
                        #title="15 Minute Block",
                        #dtick=4
                    #),
                    yaxis=dict(
                        title="Power (MW)"
                    ),
                    legend=dict(
                        orientation="h",
                        y=1.08,
                        x=0
                    ),
                    margin=dict(l=20, r=20, t=60, b=20)
                )
        
                st.plotly_chart(fig, use_container_width=True)
            elif plant_type == "🔄 Tracking":
                df = pd.read_excel(uploaded_file, sheet_name="Area & Efficiency", header=[1])
                df.columns = df.columns.str.strip()
                null_indices = df[df['Module Type'].isna()].index
                first_null_pos = df.index.get_loc(null_indices[0])
                df = df.iloc[:first_null_pos]
        
                df_st = pd.read_excel(uploaded_file, sheet_name="Forecast Config", header=[8])
                lat = float(df_st.loc[0, "Lat"])
        
                df_tilt = pd.read_excel(uploaded_file, sheet_name="Config Tilt Angle", header=[7])
                df_tilt.columns = df_tilt.columns.str.strip()
                null_indices = df_tilt[df_tilt['Fixed'].isna()].index
                first_null_pos = df_tilt.index.get_loc(null_indices[0])
                df_tilt = df_tilt.iloc[:first_null_pos]
                df_tilt = df_tilt.rename(columns={
                    'Unnamed: 2': 'Month_Num',
                    'Unnamed: 3': 'Month',
                })
                df_tilt['Month_Num'] = df_tilt['Month_Num'].fillna(0)
                df_tilt['Month'] = df_tilt['Month'].fillna(0)
                df_tilt = df_tilt.dropna(how='all', axis=1)
                #month_lookup = df_tilt.set_index('Month')['Fixed'].to_dict()
        
                df_fix = pd.read_excel(uploaded_file, sheet_name="Fixed", header=[1])
                df_fix.columns = df_fix.columns.str.strip()
                df_fix["GHI_Forecast"] = edited_df["GHI_Forecast"]
                df_fix["Actual"] = edited_df["Actual"]
                df_fix["Actual"] = df_fix["Actual"].fillna(0)
                null_indices = df_fix[df_fix['Date'].isna()].index
                first_null_pos = df_fix.index.get_loc(null_indices[0])
                df_fix = df_fix.iloc[:first_null_pos]
        
                df_fix["Date"] = pd.Timestamp.today()
                first_date = pd.Timestamp.today().replace(month=1, day=1).normalize()
        
                df_fix["Declination Angle ∆"] = 23.45 * (
                    np.sin(
                        np.radians(
                            360 * (284 + (df_fix["Date"] - first_date).dt.days + 1) / 365
                        )
                    )
                )
        
                df_fix["Elevation angle a"] = (90 - lat + df_fix["Declination Angle ∆"])
                df_fix["Tilt Angle b"] = 0
                df_fix["a+b"] = df_fix["Elevation angle a"] + df_fix["Tilt Angle b"]
                df_fix["SIN(a+b)"] = np.sin(np.radians(df_fix["a+b"]))
                df_fix["Sin(a)"] = np.sin(np.radians(df_fix["Elevation angle a"]))
                df_fix["GHI*sin(a)"] = df_fix["GHI_Forecast"] * df_fix["Sin(a)"]
                df_fix["GHI*sin(a+b)"] = df_fix["GHI_Forecast"] * df_fix["SIN(a+b)"]
                df_fix["POA fixed"] = df_fix["GHI*sin(a+b)"] / df_fix["Sin(a)"]
        
                # Maximum possible loss
                max_loss = df["Standard PV Efficiency (%)"].min()
        
                #peak_error = abs(actual_peak - predicted_peak) / actual_peak * 100
        
                results = []
        
                for loss in np.arange(0, max_loss + 0.01, 0.1):
        
                    df["Efficiency Losses(%)"] = loss
                    df["Net Efficiency (%)"] = df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                    df["Eff Area"] = (df["Total area(m2)"] * df["Net Efficiency (%)"]) / 100
            
                    df_fix["Fixed Power=I*Ƞ*A"] = (
                        df_fix["POA fixed"] * np.sum(df["Eff Area"])
                    ) / 1000000
        
                    # Peak power comparison
                    actual_peak = df_fix["Actual"].max()
                    predicted_peak = df_fix["Fixed Power=I*Ƞ*A"].max()
        
                    peak_error = abs(actual_peak - predicted_peak)
        
                    results.append({
                        "Efficiency Loss (%)": loss,
                        "Actual Peak": actual_peak,
                        "Predicted Peak": predicted_peak,
                        "Peak Error": peak_error
                    })
        
                results_df = pd.DataFrame(results)
        
                # Get efficiency loss with least Peak Error
                best_loss = results_df.loc[
                    results_df["Peak Error"].idxmin(),
                    "Efficiency Loss (%)"
                ]
        
                # Assign best efficiency loss
                df["Efficiency Losses(%)"] = best_loss
        
                # Recalculate dependent columns
                df["Net Efficiency (%)"] = (
                    df["Standard PV Efficiency (%)"] - df["Efficiency Losses(%)"]
                )
        
                df["Eff Area"] = (
                    df["Total area(m2)"] * df["Net Efficiency (%)"]
                ) / 100
        
                # Recalculate final power using the best efficiency loss
                df_fix["Fixed Power=I*Ƞ*A"] = (
                    df_fix["POA fixed"] * df["Eff Area"].sum()
                ) / 1_000_000
                # ------------------ Read Data ------------------
        
                df_bcal = pd.read_excel(uploaded_file, sheet_name="Backend Cal")
                df_trac = pd.read_excel(uploaded_file, sheet_name="Tracking", header=[1])
        
                # ------------------ Objective Function ------------------
                # ---------- Precompute once ----------
    
                actual = df_fix["Actual"].to_numpy(dtype=np.float64)
                
                mask = actual != 0
                actual = actual[mask]
                
                blocks = df_bcal["Block No."].to_numpy(dtype=np.float64)
                
                ghi_arrays = [
                    df_fix[col].to_numpy(dtype=np.float64)
                    for col in ghi_cols
                ]
                
        
                def objective(x):
        
                    DHI = int(round(x[0]))
                    GHI_Starting_Block = int(round(x[1]))
                    GHI_Ending_Block = int(round(x[2]))
                    GHI_Max_Block = int(round(x[3]))
                    Tracking_angle_lim_E = int(round(x[4]))
                    Tracking_angle_lim_W = int(round(x[5]))
        
                    # Invalid combinations
                    if (
                        GHI_Starting_Block >= GHI_Max_Block
                        or GHI_Max_Block >= GHI_Ending_Block
                    ):
                        return 1e9
        
                    m1 = 90 / (GHI_Starting_Block - 1 - GHI_Max_Block)
                    m2 = 90 / (GHI_Ending_Block + 1 - GHI_Max_Block)
        
                    ghi = ghi_arrays[0]
    
                    dhi = ghi * DHI / 100
                    
                    g_minus_d = ghi - dhi
        
        
                    zenith = np.where(
                        blocks <= GHI_Max_Block,
                        np.minimum(89, m1 * (blocks - GHI_Max_Block)),
                        np.minimum(89, m2 * (blocks - GHI_Max_Block))
                    )
        
                    panel = np.where(
                        blocks < GHI_Max_Block,
                        np.minimum(zenith, abs(Tracking_angle_lim_E)),
                        np.where(
                            (blocks > GHI_Max_Block) & (zenith > Tracking_angle_lim_W),
                            Tracking_angle_lim_W,
                            zenith
                        )
                    )
        
                    cos_alpha = np.cos(np.radians(panel))
        
                    dni = g_minus_d / cos_alpha
                    eff_area = df["Eff Area"].sum()
        
                    prediction = dni * eff_area / 1_000_000
        
                    mask = df_fix["Actual"] != 0
        
                    from sklearn.metrics import mean_squared_error
        
                    actual = df_fix["Actual"].values
        
                    # Consider only daylight blocks
                    #mask = df_fix["GHI_Forecast"].values > 50
        
                    actual = actual[mask]
                    prediction = prediction[mask]
        
                    # Higher weights near peak generation
                    weights = actual / actual.max()
        
                    # Weighted RMSE
                    block_error = np.mean(np.abs(actual - prediction)) / actual.max()
        
                    # Peak error
                    peak_error = abs(actual.max() - prediction.max()) / actual.max()
        
                    # Daily energy error
                    energy_error = abs(actual.sum() - prediction.sum()) / actual.sum()
        
                    score = (
                        0.80 * block_error +
                        0.10 * peak_error +
                        0.10 * energy_error
                    )
        
                    return score
        
        
                # ------------------ Parameter Bounds ------------------
        
                bounds = [
                    (0, 10),      # DHI (%)
                    (10, 30),     # GHI Starting Block
                    (65, 80),     # GHI Ending Block
                    (47, 53),     # GHI Max Block
                    (10, 70),     # Tracking East Limit
                    (10, 70)      # Tracking West Limit
                ]
        
                # ------------------ Optimization ------------------
        
                import random
        
                if "params" not in st.session_state:
        
                    progress = st.progress(0)
                    status = st.empty()
        
                    quotes = [
                        "☕ Vo kehte the kya ho tum, aaj hum kehte hai tum kya ho be?",
                        "🌦 Aapka mann nahi kar raha bahar jaane ka?..",
                        "😊 Jinke ghar sheeshe ke bane hote hai vo basement mai kapde change krte h...",
                        "😋 Aromatic Rose Latte with Frothy Milk pine ka mann hor hai na...",
                        "🥛 Garmi mai daalo dudh mai Ice🧊 Dudh bangya Very Nice - Dudh Dudh Dudh Dudh...",
                        "🌟 Aapke face pr toh Modiji se bhi jyda glow hai..",
                        "😁 Horaha hai benstokes Kaan mai ghusjao insaan ke...",
                        "😗 Muskuraiye aap MAL mai hai...",
                        "🥱 Hum na hote toh Operations ka kya hota?..",
                        "😎 6:30 hote hi Billu MAL se faraar...",
                        "😇 Guruji ne ek baat kahi thi....",
                        "🎼 Karna hai kuchh kaam M se gaao...",
                        "😠 Nahi karni Loss Correction, Now what to do?...",
                        "💸 Iss Job ko chhod or chhod kar ameer ho.."
                    ]
        
                    MAX_ITER = 100
                    last_quote = {"text": None}
        
                    def random_quote():
                        available = [q for q in quotes if q != last_quote["text"]]
                        q = random.choice(available)
                        last_quote["text"] = q
                        return q
                        
                    generation = {"count": 0}
                    current_quote = {"text": random_quote()}
        
                    status.info(current_quote["text"])
        
                    def callback(xk, convergence):
        
                        generation["count"] += 1
                        progress.progress(generation["count"] / MAX_ITER)
        
                        # Change quote every 7 generations
                        if generation["count"] % 20 == 1:
                            current_quote["text"] = random_quote()
        
                        status.info(
                            f"{current_quote['text']}\n\n"
                            f"Generation {generation['count']} / {MAX_ITER}"
                        )
        
                        return False
        
                    with st.spinner("Ho raha hai aap tab tak saath waale se baat karlo...🗣"):
        
                        result = differential_evolution(
                            objective,
                            bounds=bounds,
                            strategy="best1bin",
                            maxiter=MAX_ITER,
                            popsize=15,
                            tol=0.001,
                            mutation=(0.5,1),
                            recombination=0.7,
                            seed=42,
                            polish=True,
                            workers=1,
                            callback=callback
                        )
        
                    progress.empty()
                    status.success("✅ Dekha Kitni Jaldi Hogaya!")
    
                    best = np.round(result.x).astype(int)
        
                    st.session_state.params = {
                        "loss": float(best_loss),
                        "DHI": int(best[0]),
                        "start": int(best[1]),
                        "end": int(best[2]),
                        "max": int(best[3]),
                        "east": int(best[4]),
                        "west": int(best[5]),
                    }
                    st.session_state.loss = st.session_state.params["loss"]
                    st.session_state.dhi = st.session_state.params["DHI"]
                    st.session_state.start = st.session_state.params["start"]
                    st.session_state.end = st.session_state.params["end"]
                    st.session_state.max = st.session_state.params["max"]
                    st.session_state.east = st.session_state.params["east"]
                    st.session_state.west = st.session_state.params["west"]
                
                #print("Error Score:", result.fun)
                #print("DHI:", dhi)
                #print("GHI Starting Block:", GHI_Starting_Block)
                #print("GHI Ending Block:", GHI_Ending_Block)
                #print("GHI Max Block:", GHI_Max_Block)
                #print("Tracking East Limit:", Tracking_angle_lim_E)
                #print("Tracking West Limit:", Tracking_angle_lim_W)
                #print("Efficiency Loss:", best_loss)
        
                if "params" in st.session_state:
                    defaults = {
                        "loss": st.session_state.params["loss"],
                        "dhi": st.session_state.params["DHI"],
                        "start": st.session_state.params["start"],
                        "end": st.session_state.params["end"],
                        "max": st.session_state.params["max"],
                        "east": st.session_state.params["east"],
                        "west": st.session_state.params["west"],
                    }
        
                    for k, v in defaults.items():
                        if k not in st.session_state:
                            st.session_state[k] = v
                    
                    st.subheader("Optimized Parameters")
        
                    best_loss = st.number_input(
                        "Efficiency Loss (%)",
                        step=0.1,
                        key="loss"
                    )
        
                    col1, col2, col3 = st.columns(3)
        
                    DHI = col1.number_input(
                        "DHI (%)",
                        step=1,
                        key="dhi"
                    )
        
                    GHI_Starting_Block = col2.number_input(
                        "Starting Block",
                        step=1,
                        key="start"
                    )
        
                    GHI_Ending_Block = col3.number_input(
                        "Ending Block",
                        step=1,
                        key="end"
                    )
        
                    col1, col2, col3 = st.columns(3)
        
                    GHI_Max_Block = col1.number_input(
                        "Max Block",
                        step=1,
                        key="max"
                    )
        
                    Tracking_angle_lim_E = col2.number_input(
                        "East Limit",
                        step=1,
                        key="east"
                    )
        
                    Tracking_angle_lim_W = col3.number_input(
                        "West Limit",
                        step=1,
                        key="west"
                    )
        
                    #best_loss = st.session_state.loss
                    #DHI = st.session_state.dhi
                    #GHI_Starting_Block = st.session_state.start
                    #GHI_Ending_Block = st.session_state.end
                    #GHI_Max_Block = st.session_state.max
                    #Tracking_angle_lim_E = st.session_state.east
                    #Tracking_angle_lim_W = st.session_state.west
                
                    # ------------------ Final Calculation Using Best Parameters ------------------
                    # User edited efficiency loss
                    df["Efficiency Losses(%)"] = best_loss
        
                    # Recalculate
                    df["Net Efficiency (%)"] = (
                        df["Standard PV Efficiency (%)"]
                        - df["Efficiency Losses(%)"]
                    )
        
                    df["Eff Area"] = (
                        df["Total area(m2)"]
                        * df["Net Efficiency (%)"]
                    ) / 100
                    
                    display_df = df[
                        [
                            "Module Type",
                            "Standard PV Efficiency (%)",
                            "Efficiency Losses(%)",
                            "Net Efficiency (%)",
                            "Total area(m2)"
                        ]
                    ].copy()
                    
                    num_cols = display_df.select_dtypes(include="number").columns
                    display_df[num_cols] = display_df[num_cols].round(2)
                
                    with st.expander("🔍 View Efficiency Calculations"):
                        st.dataframe(
                            display_df,
                            use_container_width=True,
                            hide_index=True,
                        )
        
        
                    # ---------- Fast final calculation ----------
    
                    m1 = 90 / (GHI_Starting_Block - 1 - GHI_Max_Block)
                    m2 = 90 / (GHI_Ending_Block + 1 - GHI_Max_Block)
                    
                    ghi = df_fix["GHI_Forecast"].to_numpy(dtype=np.float64)
                    blocks = df_bcal["Block No."].to_numpy(dtype=np.float64)
                    
                    dhi = ghi * DHI / 100.0
                    ghi_minus_dhi = ghi - dhi
                    
                    zenith = np.where(
                        blocks <= GHI_Max_Block,
                        np.minimum(89.0, m1 * (blocks - GHI_Max_Block)),
                        np.minimum(89.0, m2 * (blocks - GHI_Max_Block))
                    )
                    
                    panel = np.where(
                        blocks < GHI_Max_Block,
                        np.minimum(zenith, abs(Tracking_angle_lim_E)),
                        np.where(
                            (blocks > GHI_Max_Block) & (zenith > Tracking_angle_lim_W),
                            Tracking_angle_lim_W,
                            zenith
                        )
                    )
                    
                    cos_alpha = np.cos(np.radians(panel))
                    cos_alpha = np.clip(cos_alpha, 1e-6, None)
                    
                    dni = ghi_minus_dhi / cos_alpha
                    
                    eff_area = df["Eff Area"].sum()
                    
                    forecast = dni * eff_area / 1_000_000
                    
                    df_trac["Fixed Power=I*Ƞ*A"] = forecast
        
                    x = np.arange(1, 97)
        
                    fig = go.Figure()
        
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=df_trac["Fixed Power=I*Ƞ*A"],
                            mode="lines",
                            name="Forecast",
                            line=dict(color="#2563EB", width=3),
                        )
                    )
        
                    fig.add_trace(
                        go.Scatter(
                            x=x,
                            y=df_fix["Actual"],
                            mode="lines",
                            name="Actual",
                            line=dict(color="#DC2626", width=3),
                        )
                    )
        
                    fig.update_layout(
                        title="Forecast vs Actual Power",
                        template="plotly_white",
                        height=500,
                        hovermode="x unified",
                        #xaxis=dict(
                            #title="15 Minute Block",
                            #dtick=4
                        #),
                        yaxis=dict(
                            title="Power (MW)"
                        ),
                        legend=dict(
                            orientation="h",
                            y=1.08,
                            x=0
                        ),
                        margin=dict(l=20, r=20, t=60, b=20)
                    )
        
                    st.plotly_chart(fig, use_container_width=True)

elif page == "RT Correction":
    st.title("Guruji ne kaha tha RT Correct kardo bhyii🛐!!")

    if "rt_input" not in st.session_state:
        st.session_state.rt_input = pd.DataFrame({
            "Actual": np.zeros(96),
            "Trend": np.zeros(96)
        })
    
    edited_df = st.data_editor(
        st.session_state.rt_input,
        key="rt_editor",
        use_container_width=True,
        hide_index=True,
        num_rows="fixed"
    )
    
    edited_df = edited_df.iloc[:96].reset_index(drop=True)
    
    # Detect changes
    changed_rows = (edited_df != st.session_state.rt_input).any(axis=1)
    
    if changed_rows.any():
    
        st.toast(
            f"✨ {changed_rows.sum()} rows updated successfully!",
            icon="✅"
        )
    
    # Update session state
    st.session_state.rt_input = edited_df.copy()
    
    st.session_state.rt_input = edited_df.copy()
    df = edited_df.copy()
    
    # ---------------- Time Blocks ----------------
    
    start = datetime.strptime("00:00", "%H:%M")
    
    df["Time-Blocks"] = [
        f"{(start+timedelta(minutes=15*i)).strftime('%H:%M')} - {(start+timedelta(minutes=15*(i+1))).strftime('%H:%M')}"
        for i in range(96)
    ]
    
    df["Blocks"] = np.arange(1,97)
    # ---------------- Default Parameters ----------------

    if "rt_params" not in st.session_state:
        st.session_state.rt_params = {
            "w": 0.3,
            "n1": 29,
            "n2": 72,
            "b": 39
        }
    
    actual = df["Actual"].to_numpy(dtype=float)
    trend = df["Trend"].to_numpy(dtype=float)
    blocks = df["Blocks"].to_numpy(dtype=float)
    
    mask = actual > 0.5
    
    # ---------------- Objective ----------------
    
    def objective(x):
    
        w, n1, n2, b = x
    
        n1 = int(round(n1))
        n2 = int(round(n2))
        b = int(round(b))
    
        if not (n1 < b < n2):
            return 1e6
    
        p = df.loc[
            df["Blocks"].isin([b-1, b, b+1]),
            "Actual"
        ].mean()
    
        calc = p * (
            ((n1 - blocks) * (n2 - blocks))
            /
            ((n1 - b) * (n2 - b))
        )
    
        projection = np.where(calc < 0, 0, calc)
    
        prediction = np.where(
            blocks > b,
            w * projection + (1 - w) * trend,
            trend
        )
    
        pred = projection[mask]
        act = actual[mask]
    
        block_error = np.mean(np.abs(act - pred)) / act.max()
    
        peak_error = abs(act.max() - pred.max()) / act.max()
    
        energy_error = abs(act.sum() - pred.sum()) / act.sum()
    
        return (
            0.80 * block_error +
            0.10 * peak_error +
            0.10 * energy_error
        )
    
    
    # ---------------- Optimize ----------------
    
    if st.button("🚀 Dabaiye na!!", use_container_width=True, type="primary"):
    
        with st.spinner("Optimizing..."):
    
            result = differential_evolution(
                objective,
                bounds=[
                    (0.3, 0.3),      # same as notebook
                    (5, 40),
                    (55, 95),
                    (35, 40)
                ],
                popsize=20,
                maxiter=100,
                polish=True,
                seed=42
            )
    
        w, n1, n2, b = result.x
    
        st.session_state.rt_params = {
            "w": float(w),
            "n1": int(round(n1)),
            "n2": int(round(n2)),
            "b": int(round(b))
        }
    
        st.rerun()
    
    
    # ---------------- User Inputs ----------------
    
    col1, col2 = st.columns(2)
    
    with col1:
    
        w = st.number_input(
            "Weight",
            0.0,
            1.0,
            value=float(st.session_state.rt_params["w"]),
            step=0.01
        )
    
        n2 = st.number_input(
            "n2",
            value=int(st.session_state.rt_params["n2"]),
            step=1
        )
    
    with col2:
    
        n1 = st.number_input(
            "n1",
            value=int(st.session_state.rt_params["n1"]),
            step=1
        )
    
        b = st.number_input(
            "Peak Block",
            value=int(st.session_state.rt_params["b"]),
            step=1
        )
    
    
    # ---------------- Final Calculation ----------------
    
    p = df.loc[
        df["Blocks"].isin([b-1, b, b+1]),
        "Actual"
    ].mean()
    
    calc = p * (
        ((n1 - blocks) * (n2 - blocks))
        /
        ((n1 - b) * (n2 - b))
    )
    
    projection = np.where(calc < 0, 0, calc)
    
    prediction = np.where(
        blocks > b,
        w * projection + (1 - w) * trend,
        trend
    )
    
    df["Projection"] = projection

    lookup_blocks = [
        n1,
        n2,
        n1 + 3,
        n2 - 3,
    ]
    
    lookup_names = [
        "Parabolic Power Generation Starting Block",
        "Parabolic Power Generation Ending Block",
        "Actual Generation Available Block (Lower Limit)",
        "Actual Generation Effective Block (Upper Limit)"
    ]
    
    lookup_df = pd.DataFrame({
        "Parameter": lookup_names,
        "Block": lookup_blocks
    })
    
    lookup_df["Time Block"] = lookup_df["Block"].map(
        df.set_index("Blocks")["Time-Blocks"]
    )
    
    with st.expander("📅 Important Time Blocks"):
        st.dataframe(
            lookup_df,
            use_container_width=True,
            hide_index=True
        )
    
    
    # ---------------- Graph ----------------
    
    fig=go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=df["Blocks"],
            y=df["Projection"],
            name="Projection"
        )
    )
    
    
    fig.add_trace(
        go.Scatter(
            x=df["Blocks"],
            y=df["Actual"],
            name="Actual"
        )
    )
    
    fig.update_layout(
        height=550,
        hovermode="x unified"
    )
    
    st.plotly_chart(
        fig,
        use_container_width=True
    )

elif page == "Aeromal":
    if "aeromal_auth" not in st.session_state:
        st.session_state.aeromal_auth = False

    if not st.session_state.aeromal_auth:

        st.title("🔒  Access bas bade logo ke paas hai")

        password = st.text_input(
            "Enter Password",
            type="password"
        )

        if st.button("Login", type='primary', use_container_width=True):

            if password == "asdfghjkl;'":
                st.session_state.aeromal_auth = True
                st.rerun()
            else:
                st.error("Incorrect Password")

        st.stop()

    # ---------------- Aeromal Code ----------------
    from scipy.signal import savgol_filter
        st.title("🐱‍🏍 Aeromal")
    
    # Initialize
    if "aeromal_mode" not in st.session_state:
        st.session_state.aeromal_mode = "Curtailment"
    
    c1, c2 = st.columns(2)
    
    with c1:
        if st.button(
            "⚡ Curtailment",
            use_container_width=True,
            type="primary" if st.session_state.aeromal_mode == "Curtailment" else "secondary"
        ):
            st.session_state.aeromal_mode = "Curtailment"
    
    with c2:
        if st.button(
            "☀️ No Curtailment",
            use_container_width=True,
            type="primary" if st.session_state.aeromal_mode == "No Curtailment" else "secondary"
        ):
            st.session_state.aeromal_mode = "No Curtailment"
    
    st.divider()
    
    # Selected mode
    mode = st.session_state.aeromal_mode
    
    if mode == "No Curtailment":
        st.success("☀️ No Curtailment Mode Selected")
        # Curtailment code here
    
    # ---------------- Input ----------------
    
        if "cam_input" not in st.session_state:
            st.session_state.cam_input = pd.DataFrame({
                "Power": np.zeros(96)
            })
        
        edited_df = st.data_editor(
            st.session_state.cam_input,
            key="cam_editor",
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic"
        )
        
        st.session_state.cam_input = edited_df.copy()
        
        # ---------------- Validation ----------------
        
        power = pd.to_numeric(
            edited_df.iloc[:,0],
            errors="coerce"
        ).fillna(0).to_numpy()
        
        if len(power) == 0:
            st.stop()
        
        if len(power) % 96 != 0:
            st.error("Number of rows must be divisible by 96.")
            st.stop()
        
        days = len(power) // 96
        
        # ---------------- Controls ----------------
        
        col1,col2,col3 = st.columns(3)
        
        with col1:
            window = st.number_input(
                "Window Length",
                min_value=5,
                max_value=31,
                step=2,
                value=11
            )
        
        with col2:
            power_availability = st.number_input(
                "Power Availability (%)",
                min_value=0,
                max_value=1000,
                value=100
            )
        
        # ---------------- Calculate ----------------
        
        a = power.reshape(days,96)
        
        ap = np.percentile(a,95,axis=0)
        
        s = savgol_filter(
            ap,
            window_length=window,
            polyorder=3
        )
        
        least_error = np.inf
        best_shift = 0
        
        for i in range(96):
        
            sh = np.roll(s,-i)
        
            sym = (s + sh[::-1]) / 2
        
            error = np.sqrt(
                np.mean((ap-sym)**2)
            )
        
            if error < least_error:
                least_error = error
                best_shift = i
        
        with col3:
        
            shift = st.number_input(
                "Shift",
                min_value=0,
                max_value=95,
                value=int(best_shift)
            )
        
        # ---------------- Final Curve ----------------
        
        alpha = 0.50
        
        sh = np.roll(s,-shift)
        
        sym = alpha*s + (1-alpha)*sh[::-1]
        
        thr = 0.1
        
        idx = np.where(ap>thr)[0]
        
        if len(idx)>0:
        
            start = idx[0]
            end = idx[-1]
        
            blend = 8
        
            w = np.linspace(1,0,blend)
        
            sym[start+1:start+1+blend] = (
                w*ap[start+1:start+1+blend]
                +
                (1-w)*sym[start+1:start+1+blend]
            )
        
            w = np.linspace(0,1,blend)
        
            sym[end-blend:end] = (
                w*ap[end-blend:end]
                +
                (1-w)*sym[end-blend:end]
            )
        
        s = savgol_filter(
            ap,
            window_length=window,
            polyorder=2
        )
        
        sym = savgol_filter(
            sym,
            window_length=window,
            polyorder=3
        )
        
        s = np.clip(s,0,None)
        sym = np.clip(sym,0,None)
        
        s = np.where(s<0.1,0,s)
        sym = np.where(sym<0.1,0,sym)
        
        s *= power_availability/100
        sym *= power_availability/100
        
        # ---------------- Plot ----------------
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Scatter(
                x=np.arange(96),
                y=sym,
                name="Sym Profile",
                line=dict(color="blue", width=4)
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=np.arange(96),
                y=s,
                name="Profile",
                line=dict(color="green", width=4)
            )
        )
        
        fig.add_trace(
            go.Scatter(
                x=np.arange(96),
                y=ap,
                name="95th Percentile",
                line=dict(color="red", width=4)
            )
        )
        
        fig.update_layout(
            height=550,
            hovermode="x unified",
            xaxis_title="Block",
            yaxis_title="Power",
            legend=dict(
                orientation="h",
                y=1.08,
                x=0
            ),
            margin=dict(l=20, r=20, t=60, b=20)
        )
        
        st.plotly_chart(
            fig,
            use_container_width=True
        )
        
        # ---------------- Results ----------------
        
        result = pd.DataFrame({
            "Percentile":ap,
            "Profile":s,
            "Sym Profile":sym
        })
        
        st.subheader("Generated Curve")
        
        st.dataframe(
            result,
            use_container_width=True,
            hide_index=True
        )
else:
        st.success("⚡ Curtailment Mode Selected")
        # No Curtailment code here
