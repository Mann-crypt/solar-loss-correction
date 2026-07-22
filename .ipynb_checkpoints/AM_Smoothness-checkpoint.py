def am_smoothness(file_path):
    import pandas as pd
    import numpy as np
    from scipy.signal import savgol_filter
    import matplotlib.pyplot as plt
    
    df = pd.read_excel(file_path)
    df.fillna(0, inplace=True)
    days = int(len(df)/96)
    df.tail()
    
    a = np.array(df["Power (MW)"])

    a = a.reshape(days, 96)

    ap = np.percentile(a, 95, axis=0)
    p = np.arange(0, 96)

    s = savgol_filter(ap, window_length=11, polyorder=3)
    least_error = np.inf
    x = len(p)
    for i in range(x):
        sh = np.roll(s, -i)
        sym = (s + sh[::-1]) / 2
        error = np.sqrt(np.mean((ap - sym)**2))
        if error < least_error:
            least_error = error
            shift = i
    sh = np.roll(s, -shift)
    sym = (s + sh[::-1]) / 2

    s = np.clip(s, 0, None)
    sym = np.clip(sym, 0, None)
    print(shift)
    df2 = pd.DataFrame({"Power" : ap})
    df2["Smooth-Pro-sym"] = sym
    df2["Smooth-Pro"] = s
    df2
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df2.to_excel(writer, sheet_name='AM_Curve')
    plt.figure(figsize=(14,6))
    plt.plot(p, sym, label='Sym Profile', color='blue', linewidth=2)
    plt.plot(p, s, label='Profile', color='Green', linewidth=2)
    plt.plot(p, ap, label='Percentile', color='red', linewidth=2)
    plt.xlim(0, 96)
    plt.legend()
    plt.grid(True)
    plt.show()

def curt_am_smoothness(file_path, IC):
    import pandas as pd
    import numpy as np
    from scipy.signal import savgol_filter
    import matplotlib.pyplot as plt
    df = pd.read_excel(file_path)
    df.fillna(0, inplace=True)
    days = int(len(df)/96)
    df.head()
    a = np.array(df["Power (MW)"])

    a = a.reshape(days, 96)

    ap = np.percentile(a, 95, axis=0)

    s = savgol_filter(ap, window_length=7, polyorder=3)
    sh = np.roll(s, -2)
    sym = (s + sh[::-1]) / 2
    def solar_cap_curve(
        y,
        peak_cap=250
    ):

        y = np.array(y, dtype=float)

        n = len(y)

        para = np.zeros(n)
        trip = int(np.max(y) * 1.5)
        # =========================================
        # SMOOTH INPUT
        # =========================================
        ys = savgol_filter(y, 7, 2)
        # =========================================
        # GRADIENT
        # =========================================
        grad = np.gradient(ys)
        # =========================================
        # LEFT ACTIVE REGION
        # =========================================
        left_peak = np.argmax(ys[:n//2])

        # strongest rising slope
        left_start = np.argmax(grad[:left_peak])

        x_left = np.arange(left_start, left_peak)
        y_left = ys[left_start:left_peak]

        # linear fit
        m1, c1 = np.polyfit(x_left, y_left, 1)

        # =========================================
        # RIGHT ACTIVE REGION
        # =========================================

        right_peak = np.argmax(ys[n//2:]) + n//2

        # =========================================
        # RIGHT FALLING REGION
        # =========================================

        threshold = 0.02 * np.max(ys)

        active_idx = np.where(ys > threshold)[0]

        right_end = active_idx[-1]

        x_right = np.arange(right_peak, right_end)
        y_right = ys[right_peak:right_end]

        # linear fit
        m2, c2 = np.polyfit(x_right, y_right, 1)
        # =========================================
        # AUTO TRIP LEVEL FROM PEAK WIDTH
        # =========================================

        target_width = 24  # desired distance between left and right peak indices

        A = (1/m2) - (1/m1)
        B = (c1/m1) - (c2/m2)

        trip = (target_width - B) / A

        peak_left_idx = int(round((trip - c1) / m1))
        peak_right_idx = int(round((trip - c2) / m2))

        trip = max(0, trip)  # safety
        if peak_right_idx - peak_left_idx <= target_width:
            if peak_cap >= trip:
                # =========================================
                # LEFT EXTRAPOLATION
                # =========================================
                for i in range(n):
                    val = m1*i + c1
                    para[i] = min(val, trip)
                    if val >= trip:
                        peak_left_idx = i
                        break

                # =========================================
                # RIGHT EXTRAPOLATION
                # =========================================

                right_curve = np.zeros(n)
                for i in range(n-1, -1, -1):
                    val = m2*i + c2
                    right_curve[i] = min(val, trip)
                    if val >= trip:
                        peak_right_idx = i
                        break
                    
                # =========================================
                # MERGE
                # =========================================

                para = np.maximum(para, right_curve)

                print("trip =", trip)
                print("left edge =", para[peak_left_idx])
                print("right edge =", para[peak_right_idx])

                # =========================================
                # SMOOTH SEMI-CIRCLE CAP
                # =========================================

                x = np.arange(peak_left_idx, peak_right_idx)

                center = (peak_left_idx + peak_right_idx) / 2
                radius = (peak_right_idx - peak_left_idx) / 2
 
                # edge height from existing profile
                left_edge = trip
                right_edge = trip

                base = max(left_edge, right_edge)

                width = peak_right_idx - peak_left_idx

                dome_height = max(20, 0.12 * trip)

                x = np.linspace(-1, 1, peak_right_idx - peak_left_idx)

                shape = np.sqrt(np.maximum(0, 1 - x**2))

                dome = trip + dome_height * shape
                dome[0] = trip
                dome[-1] = trip

                para[peak_left_idx:peak_right_idx] = dome
               
                # =========================================
                # SEMI-FINAL SMOOTHING
                # =========================================
                para = savgol_filter(para, 15, 3)
                para = np.clip(para, 0, None)

                # =========================================
                # FOLLOW GENERATION ENDS
                # =========================================

                para[:left_start] = ys[:left_start]

                para[right_end:] = ys[right_end:]

                # =========================================
                # FINAL SMOOTHING
                # =========================================
                para = savgol_filter(para, 7, 3)
                para = np.clip(para, 0, None)
                return para
            else:
                # =========================================
                # LEFT EXTRAPOLATION
                # =========================================

                for i in range(n):

                    val = m1*i + c1

                    para[i] = val

                    if val >= peak_cap:
                        peak_left_idx = i
                        break

                # =========================================
                # RIGHT EXTRAPOLATION
                # =========================================

                right_curve = np.zeros(n)

                for i in range(n-1, -1, -1):

                    val = m2*i + c2

                    right_curve[i] = val

                    if val >= peak_cap:
                        peak_right_idx = i
                        break

                # =========================================
                # MERGE
                # =========================================

                para = np.maximum(para, right_curve)
 
                # =========================================
                # FLAT PEAK
                # =========================================

                para[peak_left_idx:peak_right_idx] = peak_cap

                # =========================================
                # FINAL SMOOTHING
                # =========================================
                para = np.clip(para, 0, peak_cap)
                para = savgol_filter(para, 11, 3)
                # =========================================
                # FOLLOW GENERATION ENDS
                # =========================================

                para[:left_start] = ys[:left_start]

                para[right_end:] = ys[right_end:]
                para = np.clip(para, 0, peak_cap)
                return para


    # =========================================
    # USE
    # =========================================

    Final_Smooth = solar_cap_curve(
        ap,
        peak_cap= IC
    )
    df2 = pd.DataFrame({"Power" : ap})
    df2["Smooth-Pro"] = Final_Smooth
    df2
    with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        df2.to_excel(writer, sheet_name='AM_Curve')
    plt.figure(figsize=(14,5))

    plt.plot(ap, label="Generation")
    plt.plot(Final_Smooth, linewidth=3, label="Profile")

    plt.grid(True)
    plt.legend()
    plt.show()