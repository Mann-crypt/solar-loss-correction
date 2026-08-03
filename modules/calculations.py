# calculations.py

import numpy as np
import pandas as pd

# ------Layer 1--------
def calculate_declination_angle(date):
    """
    Solar declination angle (degrees).
    """
    day = pd.to_datetime(date).dayofyear

    return 23.45 * np.sin(
        np.radians(
            360 * (284 + day) / 365
        )
    )


def calculate_elevation_angle(latitude, declination):
    """
    Maximum solar elevation angle.
    """
    return 90 - latitude + declination


def sin_deg(angle):
    """
    Sine of angle in degrees.
    """
    return np.sin(np.radians(angle))


def clip_zero(values):
    """
    Replace negative values with zero.
    """
    return np.maximum(values, 0)
# ------Layer 2--------
def calculate_poa(
    ghi,
    elevation_angle,
    tilt_angle
):
    """
    Plane of Array Irradiance.
    """

    sin_a = sin_deg(elevation_angle)

    sin_ab = sin_deg(elevation_angle + tilt_angle)

    return (ghi * sin_ab) / sin_a

# -------RT Correction--------
def calculate_projection(
    blocks,
    peak,
    n1,
    n2,
    b
):
    """
    RT Projection curve.
    """

    projection = peak * (
        ((n1 - blocks) * (n2 - blocks))
        /
        ((n1 - b) * (n2 - b))
    )

    return clip_zero(projection)

def calculate_rt_forecast(
    projection,
    trend,
    blocks,
    b,
    weight
):
    """
    Final RT Forecast.
    """

    return np.where(
        blocks > b,
        weight * projection + (1 - weight) * trend,
        trend
    )

# ---------AM Curve---------
def calculate_symmetry(
    profile,
    shift
):
    """
    Symmetry profile.
    """

    shifted = np.roll(profile, -shift)

    return (profile + shifted[::-1]) / 2

def find_best_shift(profile):
    """
    Find best symmetry shift.
    """

    least_error = np.inf
    best_shift = 0

    for i in range(96):

        shifted = np.roll(profile, -i)

        sym = (profile + shifted[::-1]) / 2

        error = np.sqrt(
            np.mean((profile - sym) ** 2)
        )

        if error < least_error:
            least_error = error
            best_shift = i

    return best_shift
