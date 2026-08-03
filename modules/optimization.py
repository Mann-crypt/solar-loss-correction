import numpy as np
from scipy.optimize import differential_evolution
  
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

#-----RT Optimization-----
from modules.calculations import (
    calculate_projection,
    calculate_rt_forecast
)

from modules.metrics import (
    apply_daylight_mask,
    combined_score
)


def optimize_rt_parameters(
    actual,
    trend,
    blocks,
    bounds,
):
    """
    Optimize RT parameters.
    """
    # <-- ADD HERE
    actual = np.asarray(actual, dtype=float)
    trend = np.asarray(trend, dtype=float)
    blocks = np.asarray(blocks, dtype=float)

    if len(actual) != len(trend):
        raise ValueError("Actual and Trend must have same length.")

    if len(actual) != len(blocks):
        raise ValueError("Blocks length mismatch.")

    def objective(x):

        w, n1, n2, b = x

        n1 = int(round(n1))
        n2 = int(round(n2))
        b = int(round(b))

        if not (n1 < b < n2):
            return 1e6

        peak = np.nanmean(
            actual[
                (blocks >= b-1) &
                (blocks <= b+1)
            ]
        )
        
        if np.isnan(peak):
            return 1e9

        projection = calculate_projection(
            blocks,
            peak,
            n1,
            n2,
            b
        )

        prediction = calculate_rt_forecast(
            projection,
            trend,
            blocks,
            b,
            w
        )

        act, pred = apply_daylight_mask(
            actual,
            prediction
        )
        if len(act) == 0:
            return 1e9

        return combined_score(
            act,
            pred
        )

    return optimize_generic(
        objective,
        bounds
    )
    return {
        "result": result,
        "w": float(result.x[0]),
        "n1": int(round(result.x[1])),
        "n2": int(round(result.x[2])),
        "b": int(round(result.x[3])),
        "score": result.fun,
    }
