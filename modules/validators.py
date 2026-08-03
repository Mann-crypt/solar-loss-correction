import numpy as np
import pandas as pd

def validate_multiple_of_96(data):
    """
    Raise an error if data length is not divisible by 96.
    """

    if len(data) % 96 != 0:
        raise ValueError(
            "Input length must be divisible by 96."
        )

def validate_not_empty(data):
    """
    Raise an error if array contains no values.
    """

    if len(data) == 0:
        raise ValueError(
            "Input data is empty."
        )

def validate_positive_values(data):
    """
    Raise an error if every value is zero.
    """

    if np.max(data) <= 0:
        raise ValueError(
            "Input contains no positive values."
        )

def validate_column_exists(df, column):
    """
    Ensure a required column exists.
    """

    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' not found."
        )

def validate_sheet_exists(excel, sheet_name):
    """
    Ensure an Excel sheet exists.
    """

    if sheet_name not in excel.sheet_names:
        raise ValueError(
            f"Sheet '{sheet_name}' not found."
        )

def validate_uploaded_file(uploaded_file):
    """
    Ensure a file has been uploaded.
    """

    if uploaded_file is None:
        raise ValueError(
            "Please upload an Excel file."
        )
