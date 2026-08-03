# metrics.py

import numpy as np


def mae(actual, predicted):
    """
    Mean Absolute Error
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    return np.mean(np.abs(actual - predicted))


def rmse(actual, predicted):
    """
    Root Mean Squared Error
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    return np.sqrt(np.mean((actual - predicted) ** 2))


def nrmse(actual, predicted):
    """
    Normalized RMSE
    """
    actual = np.asarray(actual, dtype=float)

    if actual.max() == 0:
        return np.nan

    return rmse(actual, predicted) / actual.max()


def mape(actual, predicted):
    """
    Mean Absolute Percentage Error
    Ignores zero actual values.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    mask = actual != 0

    if mask.sum() == 0:
        return np.nan

    return np.mean(
        np.abs(
            (actual[mask] - predicted[mask])
            / actual[mask]
        )
    ) * 100


def r2(actual, predicted):
    """
    R² Score
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    ss_res = np.sum((actual - predicted) ** 2)
    ss_tot = np.sum((actual - actual.mean()) ** 2)

    if ss_tot == 0:
        return np.nan

    return 1 - ss_res / ss_tot


def block_error(actual, predicted):
    """
    Normalized MAE used in optimization.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if actual.max() == 0:
        return np.nan

    return np.mean(
        np.abs(actual - predicted)
    ) / actual.max()


def peak_error(actual, predicted):
    """
    Peak Error
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if actual.max() == 0:
        return np.nan

    return abs(
        actual.max() - predicted.max()
    ) / actual.max()


def energy_error(actual, predicted):
    """
    Energy Error
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if actual.sum() == 0:
        return np.nan

    return abs(
        actual.sum() - predicted.sum()
    ) / actual.sum()


def shape_error(actual, predicted):
    """
    Shape Error
    Uses normalized profiles.
    """
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)

    if actual.max() == 0 or predicted.max() == 0:
        return np.nan

    actual_norm = actual / actual.max()
    predicted_norm = predicted / predicted.max()

    return np.mean(
        np.abs(actual_norm - predicted_norm)
    )


def combined_score(
    actual,
    predicted,
    block_weight=0.80,
    peak_weight=0.10,
    energy_weight=0.10,
):
    """
    Combined optimization score.
    Lower is better.
    """

    b = block_error(actual, predicted)
    p = peak_error(actual, predicted)
    e = energy_error(actual, predicted)

    return (
        block_weight * b +
        peak_weight * p +
        energy_weight * e
    )


def calculate_all_metrics(actual, predicted):
    """
    Returns all commonly used metrics.
    """

    return {
        "MAE": mae(actual, predicted),
        "RMSE": rmse(actual, predicted),
        "NRMSE": nrmse(actual, predicted),
        "MAPE": mape(actual, predicted),
        "R2": r2(actual, predicted),
        "Block Error": block_error(actual, predicted),
        "Peak Error": peak_error(actual, predicted),
        "Energy Error": energy_error(actual, predicted),
        "Shape Error": shape_error(actual, predicted),
        "Combined Score": combined_score(actual, predicted),
    }
