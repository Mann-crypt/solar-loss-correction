import streamlit as st

from pages.loss_correction import show_loss_correction
from pages.rt_correction import show_rt_correction
from pages.aeromal import show_aeromal

st.set_page_config(page_title="Solar Suite", layout="wide")

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
Forecast Correction Platform
</p>
""", unsafe_allow_html=True)

st.sidebar.divider()
