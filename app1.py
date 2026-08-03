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

if "page" not in st.session_state:
    st.session_state.page = "Loss Correction"

if "aeromal_auth" not in st.session_state:
    st.session_state.aeromal_auth = False

pages = {
    "⛅ Loss Correction": "Loss Correction",
    "⏰ RT Correction": "RT Correction",
    "🐱‍🏍 Aeromal": "Aeromal"
}

for label, page in pages.items():
    if st.sidebar.button(
        label,
        use_container_width=True
    ):
        st.session_state.page = page

st.sidebar.divider()

st.sidebar.markdown("""
<div style='text-align:center;color:gray;font-size:13px'>
Developed & Maintained by<br>
<b>Manjot Singh</b><br><br>

Script Writer<br>
<b>Tushar Sharma</b><br><br>

Challenger<br>
<b>Aarav Sharma</b><br><br>

Tester<br>
<b>Jatin Chaturvedi</b><br><br>

Improviser<br>
<b>Ujala Agrahari</b><br><br>

Suggested by<br>
<b>Garima Bajetha</b>
</div>
""", unsafe_allow_html=True)

if st.session_state.aeromal_auth:

    st.sidebar.markdown("---")

    if st.sidebar.button(
        "🚪 Logout",
        use_container_width=True
    ):
        st.session_state.aeromal_auth = False
        st.rerun()

page = st.session_state.page

if page == "Loss Correction":
    show_loss_correction()

elif page == "RT Correction":
    show_rt_correction()

elif page == "Aeromal":
    show_aeromal()
