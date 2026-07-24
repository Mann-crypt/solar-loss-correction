import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from scipy.optimize import differential_evolution
from sklearn.metrics import mean_absolute_percentage_error
import streamlit as st

st.set_page_config(page_title="Solar Loss Correction", layout="wide")

st.title("Kuchu Puchu🥰 - Aao Tumhari Loss Correction Kardu!!")

uploaded_file = st.file_uploader(
    "Yaha Feko",
    type=["xlsx"],
    key="excel_uploader"
)

if uploaded_file is None:
    st.info("Pehle File toh upload krr!!!")
    st.stop()

if "last_file" not in st.session_state:
    st.session_state.last_file = None

if uploaded_file is not None:
    if st.session_state.last_file != uploaded_file.name:
        st.session_state.last_file = uploaded_file.name
        st.session_state.pop("params", None)
        st.session_state.run_model = False
        
file_path = uploaded_file

# Read Fixed sheet first
df_fix = pd.read_excel(file_path, sheet_name="Fixed", header=[1])
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

# Create editable table
input_df = df_fix[["GHI_Forecast", "Actual"]].copy()

edited_df = st.data_editor(
    input_df,
    use_container_width=True,
    hide_index=True,
    num_rows="fixed"
)

# Ensure exactly 96 rows
edited_df = edited_df.iloc[:96].reset_index(drop=True)

# Update df_fix
df_fix["GHI_Forecast"] = edited_df["GHI_Forecast"].values
df_fix["Actual"] = edited_df["Actual"].values

if len(df_fix) > 96:
    st.warning(
        f"The uploaded file contains {len(df_fix)} rows. "
        "Only the first 96 blocks will be used."
    )

df_fix = df_fix.iloc[:96].copy()

plant_type = st.radio(
    "Plant Type",
    ["Fixed", "Tracking"],
    horizontal=True
)

if "run_model" not in st.session_state:
    st.session_state.run_model = False

if st.button("🚀 Dabao Magar Pyaar Se!!", use_container_width=True, type="primary"):
    st.session_state.pop("params", None)   # Delete old optimized values
    st.session_state.run_model = True

if st.session_state.run_model:

    if plant_type == "Fixed":
        df = pd.read_excel(file_path, sheet_name="Area & Efficiency", header=[1])
        df.columns = df.columns.str.strip()
        null_indices = df[df['Module Type'].isna()].index
        first_null_pos = df.index.get_loc(null_indices[0])
        df = df.iloc[:first_null_pos]

        df_st = pd.read_excel(file_path, sheet_name="Forecast Config", header=[8])
        lat = float(df_st.loc[0, "Lat"])

        df_tilt = pd.read_excel(file_path, sheet_name="Config Tilt Angle", header=[7])
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

        df_fix = pd.read_excel(file_path, sheet_name="Fixed", header=[1])
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
    elif plant_type == "Tracking":
        df = pd.read_excel(file_path, sheet_name="Area & Efficiency", header=[1])
        df.columns = df.columns.str.strip()
        null_indices = df[df['Module Type'].isna()].index
        first_null_pos = df.index.get_loc(null_indices[0])
        df = df.iloc[:first_null_pos]

        df_st = pd.read_excel(file_path, sheet_name="Forecast Config", header=[8])
        lat = float(df_st.loc[0, "Lat"])

        df_tilt = pd.read_excel(file_path, sheet_name="Config Tilt Angle", header=[7])
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

        df_fix = pd.read_excel(file_path, sheet_name="Fixed", header=[1])
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

        df_bcal = pd.read_excel(file_path, sheet_name="Backend Cal")
        df_trac = pd.read_excel(file_path, sheet_name="Tracking", header=[1])

        # ------------------ Objective Function ------------------

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

            temp = df_bcal.copy()

            temp["DHI"] = df_fix["GHI_Forecast"] * DHI / 100
            temp["GHI - DHI"] = df_fix["GHI_Forecast"] - temp["DHI"]

            temp["Zenith angle ( θ )"] = np.where(
                temp["Block No."] <= GHI_Max_Block,
                np.minimum(89, m1 * (temp["Block No."] - GHI_Max_Block)),
                np.minimum(89, m2 * (temp["Block No."] - GHI_Max_Block))
            )

            temp["Panel Angle (α)"] = np.where(
                temp["Block No."] < GHI_Max_Block,
                np.where(
                    temp["Zenith angle ( θ )"] < abs(Tracking_angle_lim_E),
                    temp["Zenith angle ( θ )"],
                    abs(Tracking_angle_lim_E)
                ),
                np.where(
                    (temp["Block No."] > GHI_Max_Block) &
                    (temp["Zenith angle ( θ )"] > Tracking_angle_lim_W),
                    Tracking_angle_lim_W,
                    temp["Zenith angle ( θ )"]
                )
            )

            temp["θ - α"] = temp["Zenith angle ( θ )"] - temp["Panel Angle (α)"]

            temp["Cos(θ)"] = np.cos(np.radians(temp["Zenith angle ( θ )"]))
            temp["Cos(α)"] = np.cos(np.radians(temp["Panel Angle (α)"]))
            temp["Cos(θ - α)"] = np.cos(np.radians(temp["θ - α"]))

            temp["DNI"] = temp["GHI - DHI"] / temp["Cos(α)"]

            prediction = (temp["DNI"] * df["Eff Area"].sum()) / 1_000_000

            mask = df_fix["Actual"] != 0

            from sklearn.metrics import mean_squared_error

            actual = df_fix["Actual"].values
            prediction = prediction.values

            # Consider only daylight blocks
            mask = df_fix["GHI_Forecast"].values > 50

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
                "🌦 Mausam Loss Correction waala hai hi nhi..",
                "😊 Jinke ghar sheeshe ke bane hote hai vo basement mai kapde change krte h...",
                "😋 Thana Thaliya?",
                "😅 Ghurrna Band Karo Noor...",
                "🛣  Iss Weekend free ho?..",
                "😁 Horaha hai bass Thoda or rukjao mere liye...",
                "😗 Muskuraiye aap MAL mai hai...",
                "🥱 Hum na hote toh Operations ka kya hota?..",
                "😎 6:30 hote hi Billu MAL se faraar..."
            ]

            quote_index = {"i": 0}      # <-- ADD THIS
            iteration = {"i": 0}

            generation = {"count": 0}
            MAX_ITER = 40

            def callback(xk, convergence):
                generation["count"] += 1

                progress.progress(generation["count"] / MAX_ITER)

                # Change quote every 5 generations
                if generation["count"] % 8 == 1:
                    quote_index["i"] = (quote_index["i"] + 1) % len(quotes)

                status.info(
                    f"{quotes[quote_index['i']]}\n\n"
                    f"Generation {generation['count']} / {MAX_ITER}"
                )

                return False

            with st.spinner("Optimizing... Please wait"):

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
            status.success("✅ Optimization Complete!")

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

            m1 = 90 / (GHI_Starting_Block - 1 - GHI_Max_Block)
            m2 = 90 / (GHI_Ending_Block + 1 - GHI_Max_Block)

            df_bcal["DHI"] = df_fix["GHI_Forecast"] * DHI / 100
            df_bcal["GHI - DHI"] = df_fix["GHI_Forecast"] - df_bcal["DHI"]

            df_bcal["Zenith angle ( θ )"] = np.where(
                df_bcal["Block No."] <= GHI_Max_Block,
                np.minimum(89, m1 * (df_bcal["Block No."] - GHI_Max_Block)),
                np.minimum(89, m2 * (df_bcal["Block No."] - GHI_Max_Block))
            )

            df_bcal["Panel Angle (α)"] = np.where(
                df_bcal["Block No."] < GHI_Max_Block,
                np.where(
                    df_bcal["Zenith angle ( θ )"] < abs(Tracking_angle_lim_E),
                    df_bcal["Zenith angle ( θ )"],
                    abs(Tracking_angle_lim_E)
                ),
                np.where(
                    (df_bcal["Block No."] > GHI_Max_Block) &
                    (df_bcal["Zenith angle ( θ )"] > Tracking_angle_lim_W),
                    Tracking_angle_lim_W,
                    df_bcal["Zenith angle ( θ )"]
                )
            )

            df_bcal["θ - α"] = df_bcal["Zenith angle ( θ )"] - df_bcal["Panel Angle (α)"]
            df_bcal["Cos(θ)"] = np.cos(np.radians(df_bcal["Zenith angle ( θ )"]))
            df_bcal["Cos(α)"] = np.cos(np.radians(df_bcal["Panel Angle (α)"]))
            df_bcal["Cos(θ - α)"] = np.cos(np.radians(df_bcal["θ - α"]))
            df_bcal["DNI"] = df_bcal["GHI - DHI"] / df_bcal["Cos(α)"]

            df_trac["Fixed Power=I*Ƞ*A"] = (
                df_bcal["DNI"] * df["Eff Area"].sum()
            ) / 1000000

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
