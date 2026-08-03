import numpy as np
import pandas as pd
from datetime import datetime, timedelta

def generate_blocks(length=96):
    """
    Generate sequential block numbers.
    """
    return np.arange(1, length + 1)

def generate_time_blocks(
    length=96,
    interval_minutes=15,
):
    """
    Generate readable time block labels.
    """

    start = datetime.strptime("00:00", "%H:%M")

    return [
        f"{(start + timedelta(minutes=i*interval_minutes)).strftime('%H:%M')} - "
        f"{(start + timedelta(minutes=(i+1)*interval_minutes)).strftime('%H:%M')}"
        for i in range(length)
    ]

def array_to_dataframe(
    array,
    column_name,
):
    """
    Convert numpy array to DataFrame.
    """

    return pd.DataFrame({
        column_name: np.asarray(array)
    })

def apply_percentage(
    values,
    percentage,
):
    """
    Scale values by percentage.
    """

    return np.asarray(values) * percentage / 100

def clip_negative(values):
    """
    Replace negative values with zero.
    """

    return np.maximum(values, 0)

def apply_threshold(
    values,
    threshold,
):
    """
    Zero values below threshold.
    """

    values = np.asarray(values).copy()

    values[values < threshold] = 0

    return values

def shift_array(
    values,
    shift,
):
    """
    Circular shift.
    """

    return np.roll(values, -shift)

def symmetric_average(
    values,
    shift,
):
    """
    Create symmetric profile.
    """

    shifted = np.roll(values, -shift)

    return (values + shifted[::-1]) / 2

def reshape_daily(
    values,
    blocks_per_day=96,
):
    """
    Reshape data into daily matrix.
    """

    values = np.asarray(values)

    return values.reshape(
        len(values) // blocks_per_day,
        blocks_per_day
    )

def percentile_profile(
    matrix,
    percentile=95,
):
    """
    Daily percentile profile.
    """

    return np.percentile(
        matrix,
        percentile,
        axis=0
    )

