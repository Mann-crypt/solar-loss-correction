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
    efficiency_loss=None,
    bounds=None,
    maxiter=100,
    popsize=15,
    seed=42,
    callback=None,
):
    """
    Optimize Tracking Loss Correction parameters.

    Optimized parameters:

        DHI
        GHI Starting Block
        GHI Ending Block
        GHI Max Block
        East Tracking Limit
        West Tracking Limit
        Efficiency Loss

    Parameters
    ----------
    efficiency_loss : optional
        Kept for compatibility with the screen.
        When Efficiency Loss is included in bounds,
        the optimizer uses x[6].

    bounds
        Expected order:

        [
            (DHI_min, DHI_max),
            (start_min, start_max),
            (end_min, end_max),
            (max_min, max_max),
            (east_min, east_max),
            (west_min, west_max),
            (loss_min, loss_max),
        ]

    Returns
    -------
    dict
        parameters
        score
        weights
        result
    """

    # ======================================================
    # CLEAN INPUT
    # ======================================================

    actual = np.asarray(
        actual,
        dtype=float,
    )

    blocks = np.asarray(
        blocks,
        dtype=float,
    )

    # ======================================================
    # VALIDATION
    # ======================================================

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
                "GHI array length does not "
                "match Blocks."
            )

    if bounds is None:

        raise ValueError(
            "Optimization bounds are required."
        )

    if len(bounds) != 7:

        raise ValueError(
            "Tracking optimization requires "
            "7 parameter bounds: "
            "DHI, Starting Block, Ending Block, "
            "Max Block, East Limit, West Limit "
            "and Efficiency Loss."
        )

    # ======================================================
    # DETERMINE PLANT TYPE
    # ======================================================

    has_cluster = (
        len(ghi_arrays) > 1
    )

    # ======================================================
    # OBJECTIVE FUNCTION
    # ======================================================

    def objective(x):

        # --------------------------------------------------
        # PARAMETERS
        # --------------------------------------------------

        DHI = int(
            round(x[0])
        )

        start = int(
            round(x[1])
        )

        end = int(
            round(x[2])
        )

        max_block = int(
            round(x[3])
        )

        east = int(
            round(x[4])
        )

        west = int(
            round(x[5])
        )

        loss = float(
            x[6]
        )

        # --------------------------------------------------
        # VALIDATE BLOCK CONFIGURATION
        # --------------------------------------------------

        if not (
            start < max_block < end
        ):

            return 1e9

        # --------------------------------------------------
        # CALCULATE EFFECTIVE WEIGHTS
        # --------------------------------------------------

        try:

            weights = (
                calculate_loss_corrected_weights(

                    area_df=area_df,

                    efficiency_loss=loss,

                    weight_factors=weight_factors,

                    has_cluster=has_cluster,

                )
            )

        except Exception:

            return 1e9

        # --------------------------------------------------
        # VALIDATE WEIGHTS
        # --------------------------------------------------

        if len(weights) != len(
            ghi_arrays
        ):

            return 1e9

        # --------------------------------------------------
        # CALCULATE FORECAST
        # --------------------------------------------------

        try:

            prediction = (
                calculate_tracking_forecast(

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
            )

        except Exception:

            return 1e9

        # --------------------------------------------------
        # DAYLIGHT MASK
        # --------------------------------------------------

        mask = (
            actual > 0
        )

        act = actual[mask]

        pred = prediction[mask]

        if len(act) == 0:

            return 1e9

        if act.max() <= 0:

            return 1e9

        # --------------------------------------------------
        # BLOCK ERROR
        # --------------------------------------------------

        block_error_value = (

            np.mean(
                np.abs(
                    act - pred
                )
            )

            / act.max()

        )

        # --------------------------------------------------
        # PEAK ERROR
        # --------------------------------------------------

        peak_error_value = (

            abs(
                act.max()
                - pred.max()
            )

            / act.max()

        )

        # --------------------------------------------------
        # ENERGY ERROR
        # --------------------------------------------------

        if act.sum() == 0:

            return 1e9

        energy_error_value = (

            abs(
                act.sum()
                - pred.sum()
            )

            / act.sum()

        )

        # --------------------------------------------------
        # COMBINED SCORE
        # --------------------------------------------------

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

        # --------------------------------------------------
        # VALIDATE SCORE
        # --------------------------------------------------

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

    best_DHI = int(
        round(best[0])
    )

    best_start = int(
        round(best[1])
    )

    best_end = int(
        round(best[2])
    )

    best_max = int(
        round(best[3])
    )

    best_east = int(
        round(best[4])
    )

    best_west = int(
        round(best[5])
    )

    best_loss = float(
        best[6]
    )

    # ======================================================
    # FINAL WEIGHTS
    # ======================================================

    final_weights = (
        calculate_loss_corrected_weights(

            area_df=area_df,

            efficiency_loss=best_loss,

            weight_factors=weight_factors,

            has_cluster=has_cluster,

        )
    )

    # ======================================================
    # FINAL PARAMETERS
    # ======================================================

    parameters = {

        "DHI":
            best_DHI,

        "Starting Block":
            best_start,

        "Ending Block":
            best_end,

        "Max Block":
            best_max,

        "East Limit":
            best_east,

        "West Limit":
            best_west,

        "Efficiency Loss":
            best_loss,

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
