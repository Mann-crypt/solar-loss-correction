# modules/optimization.py

import numpy as np
from scipy.optimize import differential_evolution

from modules.calculations import (
    calculate_tracking_forecast,
)

from modules.metrics import (
    block_error,
    peak_error,
    energy_error,
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
        bounds=bounds,
        popsize=popsize,
        maxiter=maxiter,
        seed=seed,
        polish=polish,
    )


# ==========================================================
# TRACKING LOSS CORRECTION OPTIMIZATION
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

    Parameters optimized:

        DHI
        GHI Starting Block
        GHI Ending Block
        GHI Max Block
        East Tracking Limit
        West Tracking Limit
        Efficiency Loss

    Returns:
        Dictionary containing best parameters,
        score, weights and optimizer result.
    """

    actual = np.asarray(
        actual,
        dtype=float,
    )

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    # ------------------------------------------------------
    # Validation
    # ------------------------------------------------------

    if len(actual) != len(blocks):
        raise ValueError(
            "Actual and Blocks must have same length."
        )

    if len(ghi_arrays) == 0:
        raise ValueError(
            "No GHI arrays supplied."
        )

    for ghi in ghi_arrays:

        if len(ghi) != len(blocks):
            raise ValueError(
                "GHI array length does not match Blocks."
            )

    # ======================================================
    # OBJECTIVE
    # ======================================================

    def objective(x):

        # ----------------------------------------------
        # Parameters
        # ----------------------------------------------

        DHI = int(round(x[0]))

        start = int(round(x[1]))

        end = int(round(x[2]))

        max_block = int(round(x[3]))

        east = int(round(x[4]))

        west = int(round(x[5]))

        efficiency_loss = float(x[6])

        # ----------------------------------------------
        # Block validation
        # ----------------------------------------------

        if not (
            start < max_block < end
        ):
            return 1e9

        # ----------------------------------------------
        # Calculate corrected effective weights
        # ----------------------------------------------

        try:

            from modules.calculations import (
                calculate_loss_corrected_weights
            )

            weights = calculate_loss_corrected_weights(

                area_df=area_df,

                efficiency_loss=efficiency_loss,

                weight_factors=weight_factors,
            )

        except Exception:

            return 1e9

        # ----------------------------------------------
        # Calculate tracking forecast
        # ----------------------------------------------

        try:

            prediction = calculate_tracking_forecast(

                ghi_arrays=ghi_arrays,

                weights=weights,

                blocks=blocks,

                dhi_percent=DHI,

                ghi_start=start,

                ghi_end=end,

                ghi_max=max_block,

                east_limit=east,

                west_limit=west,
            )

        except Exception:

            return 1e9

        # ----------------------------------------------
        # Daylight mask
        # ----------------------------------------------

        mask = actual > 0

        act = actual[mask]

        pred = prediction[mask]

        if len(act) == 0:
            return 1e9

        if act.max() <= 0:
            return 1e9

        # ----------------------------------------------
        # Metrics
        # ----------------------------------------------

        b_error = (
            np.mean(
                np.abs(
                    act - pred
                )
            )
            / act.max()
        )

        p_error = (
            abs(
                act.max()
                - pred.max()
            )
            / act.max()
        )

        e_error = (
            abs(
                act.sum()
                - pred.sum()
            )
            / act.sum()
        )

        # ----------------------------------------------
        # Combined score
        # ----------------------------------------------

        score = (
            0.80 * b_error
            + 0.10 * p_error
            + 0.10 * e_error
        )

        if (
            np.isnan(score)
            or np.isinf(score)
        ):
            return 1e9

        return score

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

        mutation=(0.5, 1),

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

    parameters = {

        "DHI":
            int(round(best[0])),

        "Starting Block":
            int(round(best[1])),

        "Ending Block":
            int(round(best[2])),

        "Max Block":
            int(round(best[3])),

        "East Tracking Limit":
            int(round(best[4])),

        "West Tracking Limit":
            int(round(best[5])),

        "Efficiency Loss for Tracking":
            round(float(best[6]), 2),
    }

    # ======================================================
    # FINAL WEIGHTS
    # ======================================================

    from modules.calculations import (
        calculate_loss_corrected_weights
    )

    final_weights = calculate_loss_corrected_weights(

        area_df=area_df,

        efficiency_loss=float(best[6]),

        weight_factors=weight_factors,
    )

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
