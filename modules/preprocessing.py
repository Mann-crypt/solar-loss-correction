# preprocessing.py

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def truncate_at_first_nan(df, column="Module Type"):
    """
    Truncate the dataframe at the first NaN in the specified column.

    Parameters
    ----------
    df : pd.DataFrame
    column : str
        Column used to identify the end of valid data.

    Returns
    -------
    pd.DataFrame
    """

    if column not in df.columns:
        raise ValueError(f"Column '{column}' not found.")

    null_indices = df[df[column].isna()].index

    if len(null_indices) == 0:
        return df.copy()

    first_null_pos = df.index.get_loc(null_indices[0])

    return df.iloc[:first_null_pos].copy()

def clean_headers(df):
    """
    Remove leading/trailing spaces from column names.
    """

    df = df.copy()

    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.strip()
    )

    return df

def drop_empty_columns(df):
    """
    Remove columns that contain only NaN values.
    """
    return df.dropna(axis=1, how="all").copy()

def rename_columns(df, mapping):
    """
    Rename dataframe columns.
    """
    return df.rename(columns=mapping).copy()

def add_time_blocks(df):
    """
    Add 15-minute time block labels.
    """
    df = df.copy()

    start = datetime.strptime("00:00", "%H:%M")

    df["Time-Blocks"] = [
        f"{(start + timedelta(minutes=15*i)).strftime('%H:%M')} - "
        f"{(start + timedelta(minutes=15*(i+1))).strftime('%H:%M')}"
        for i in range(96)
    ]

    return df

def add_block_numbers(df):
    """
    Add block numbers from 1 to 96.
    """
    df = df.copy()
    df["Blocks"] = np.arange(1, len(df)+1)
    return df

def reshape_to_days(array):
    """
    Convert 1D array into (days,96).
    """
    array = np.asarray(array)

    if len(array) % 96 != 0:
        raise ValueError("Length must be divisible by 96.")

    return array.reshape(-1, 96)

def validate_96_blocks(df):
    """
    Validate dataframe length.
    """
    if len(df) % 96 != 0:
        raise ValueError(
            "Number of rows must be divisible by 96."
        )

def fill_missing_values(df, value=0):
  """
  Fill NaN values.
  """
  return df.fillna(value).copy()
