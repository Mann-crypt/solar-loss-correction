# modules/optimization.py

import numpy as np
from scipy.optimize import differential_evolution

from modules.calculations import (
    calculate_tracking_forecast,
    calculate_loss_corrected_weights,
)


# ==========================================================
# GENERIC OPTIMIZER
# ==========================================================

def optimize_generic(
    objective,
    bounds,
    popsize=20,
    maxiter=100,
    seed=42,
    polish=True,
):
    """
    Generic Differential Evolution optimizer.
    """

    return differential_evolution(
        objective,
        bounds,
        popsize=popsize,
        maxiter=maxiter,
        seed=seed,
        polish=polish,
    )


# ==========================================================
# TRACKING LOSS CORRECTION
# ==========================================================

def optimize_tracking_parameters(
    actual,
    ghi_arrays,
    blocks,
    area_df,
    weight_factors,
    bounds,
    maxiter=100,
    popsize=15,
    seed=42,
    callback=None,
):
    """
    Optimize Tracking Loss Correction parameters.

    Optimized parameters:

        1. DHI
        2. GHI Starting Block
        3. GHI Ending Block
        4. GHI Max Block
        5. East Tracking Limit
        6. West Tracking Limit
        7. Efficiency Loss

    Works for:

        Cluster plants:
            CL1-GHI ... CL5-GHI

        Non-cluster plants:
            Normal GHI from Backend Cal
    """

    # ======================================================
    # CLEAN INPUTS
    # ======================================================

    actual = np.asarray(
        actual,
        dtype=float,
    )

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    # ------------------------------------------------------
    # Validate actual
    # ------------------------------------------------------

    if len(actual) != len(blocks):

        raise ValueError(
            "Actual and Blocks must have the same length."
        )

    # ------------------------------------------------------
    # Validate GHI arrays
    # ------------------------------------------------------

    if not ghi_arrays:

        raise ValueError(
            "No GHI arrays supplied."
        )

    cleaned_ghi_arrays = []

    for i, ghi in enumerate(ghi_arrays):

        ghi = np.asarray(
            ghi,
            dtype=float,
        )

        if len(ghi) != len(blocks):

            raise ValueError(
                f"GHI array {i + 1} length "
                "does not match Blocks."
            )

        ghi = np.nan_to_num(
            ghi,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )

        ghi = np.maximum(
            ghi,
            0,
        )

        cleaned_ghi_arrays.append(
            ghi
        )

    # ======================================================
    # VALIDATE BOUNDS
    # ======================================================

    if len(bounds) != 7:

        raise ValueError(
            "Tracking optimization requires "
            "exactly 7 parameter bounds."
        )

    # ======================================================
    # OBJECTIVE
    # ======================================================

    def objective(x):

        # --------------------------------------------------
        # Convert parameters
        # --------------------------------------------------

        dhi_percent = int(
            round(x[0])
        )

        ghi_start = int(
            round(x[1])
        )

        ghi_end = int(
            round(x[2])
        )

        ghi_max = int(
            round(x[3])
        )

        east_limit = int(
            round(x[4])
        )

        west_limit = int(
            round(x[5])
        )

        efficiency_loss = float(
            x[6]
        )

        # --------------------------------------------------
        # Validate GHI configuration
        # --------------------------------------------------

        if not (
            ghi_start
            < ghi_max
            < ghi_end
        ):

            return 1e9

        # --------------------------------------------------
        # Calculate effective weights
        # --------------------------------------------------

        try:

            weights = (
                calculate_loss_corrected_weights(

                    area_df=area_df,

                    efficiency_loss=efficiency_loss,

                    weight_factors=weight_factors,

                    has_cluster=(
                        len(cleaned_ghi_arrays) > 1
                    ),
                )
            )

        except Exception:

            return 1e9

        # --------------------------------------------------
        # Validate weights
        # --------------------------------------------------

        if len(weights) != len(
            cleaned_ghi_arrays
        ):

            return 1e9

        # --------------------------------------------------
        # Calculate forecast
        # --------------------------------------------------

        try:

            prediction = (
                calculate_tracking_forecast(

                    ghi_arrays=cleaned_ghi_arrays,

                    weights=weights,

                    blocks=blocks,

                    dhi_percent=dhi_percent,

                    ghi_start=ghi_start,

                    ghi_end=ghi_end,

                    ghi_max=ghi_max,

                    east_limit=east_limit,

                    west_limit=west_limit,
                )
            )

        except Exception:

            return 1e9

        # --------------------------------------------------
        # Validate prediction
        # --------------------------------------------------

        prediction = np.asarray(
            prediction,
            dtype=float,
        )

        if len(prediction) != len(actual):

            return 1e9

        if np.any(
            ~np.isfinite(prediction)
        ):

            return 1e9

        # ==================================================
        # DAYLIGHT MASK
        # ==================================================

        mask = (
            np.isfinite(actual)
            & np.isfinite(prediction)
            & (actual > 0)
        )

        if not np.any(mask):

            return 1e9

        act = actual[mask]

        pred = prediction[mask]

        if len(act) == 0:

            return 1e9

        actual_peak = act.max()

        actual_energy = act.sum()

        if actual_peak <= 0:

            return 1e9

        if actual_energy <= 0:

            return 1e9

        # ==================================================
        # BLOCK ERROR
        # ==================================================

        block_error_value = (
            np.mean(
                np.abs(
                    act - pred
                )
            )
            / actual_peak
        )

        # ==================================================
        # PEAK ERROR
        # ==================================================

        peak_error_value = (
            abs(
                actual_peak
                - pred.max()
            )
            / actual_peak
        )

        # ==================================================
        # ENERGY ERROR
        # ==================================================

        energy_error_value = (
            abs(
                actual_energy
                - pred.sum()
            )
            / actual_energy
        )

        # ==================================================
        # COMBINED SCORE
        # ==================================================

        score = (

            0.80
            * block_error_value

            +

            0.10
            * peak_error_value

            +

            0.10
            * energy_error_value
        )

        if (
            not np.isfinite(score)
        ):

            return 1e9

        return float(score)

    # ======================================================
    # DIFFERENTIAL EVOLUTION
    # ======================================================

    result = differential_evolution(

        objective,

        bounds=bounds,

        strategy="best1bin",

        maxiter=maxiter,

        popsize=popsize,

        tol=0.001,

        mutation=(0.5, 1.0),

        recombination=0.7,

        seed=seed,

        polish=True,

        workers=1,

        callback=callback,
    )

    # ======================================================
    # BEST PARAMETERS
    # ======================================================

    best = result.x

    dhi_percent = int(
        round(best[0])
    )

    ghi_start = int(
        round(best[1])
    )

    ghi_end = int(
        round(best[2])
    )

    ghi_max = int(
        round(best[3])
    )

    east_limit = int(
        round(best[4])
    )

    west_limit = int(
        round(best[5])
    )

    best_efficiency_loss = float(
        best[6]
    )

    # ======================================================
    # CALCULATE FINAL WEIGHTS
    # USING BEST EFFICIENCY LOSS
    # ======================================================

    final_weights = (
        calculate_loss_corrected_weights(

            area_df=area_df,

            efficiency_loss=(
                best_efficiency_loss
            ),

            weight_factors=weight_factors,

            has_cluster=(
                len(cleaned_ghi_arrays) > 1
            ),
        )
    )

    # ======================================================
    # PARAMETERS
    # ======================================================

    parameters = {

        "DHI":
            dhi_percent,

        "Starting Block":
            ghi_start,

        "Ending Block":
            ghi_end,

        "Max Block":
            ghi_max,

        "East Limit":
            east_limit,

        "West Limit":
            west_limit,

        "Efficiency Loss":
            best_efficiency_loss,
    }

    # ======================================================
    # RETURN
    # ======================================================

    return {

        "parameters":
            parameters,

        "score":
            float(result.fun),

        "weights":
            final_weights,

        "result":
            result,
    }
