# modules/plotting.py

import numpy as np
import plotly.graph_objects as go


def get_blocks(length=96):
    """
    Generate block numbers from 1 to length.
    """
    return np.arange(1, length + 1)


def apply_default_layout(fig, title=None):
    """
    Apply common Plotly layout.
    """

    fig.update_layout(
        title=title,
        template="plotly_white",
        height=550,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.05,
            x=0
        ),
        margin=dict(
            l=30,
            r=30,
            t=50,
            b=30
        ),
    )

    fig.update_xaxes(
        showgrid=True,
    )

    fig.update_yaxes(
        showgrid=True,
    )

    return fig


# --------------------------------------------------
# RT FORECAST
# --------------------------------------------------

def plot_rt_forecast(
    blocks,
    projection,
    forecast,
    actual,
):
    """
    Plot RT correction curves.
    """

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=projection,
            name="Projection",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=forecast,
            name="RT Forecast",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=actual,
            name="Actual",
            mode="lines",
        )
    )

    return apply_default_layout(
        fig,
        "RT Correction"
    )


# --------------------------------------------------
# CAM CURVE
# --------------------------------------------------

def plot_cam_curve(
    percentile,
    profile,
    symmetric,
):
    """
    Plot CAM profile.
    """

    blocks = get_blocks(len(percentile))

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=symmetric,
            name="Sym Profile",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=profile,
            name="Profile",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=percentile,
            name="95th Percentile",
            mode="lines",
        )
    )

    fig.update_xaxes(
        title="Block"
    )

    fig.update_yaxes(
        title="Power"
    )

    return apply_default_layout(
        fig,
        "CAM Curve"
    )


# --------------------------------------------------
# LOSS CORRECTION
# --------------------------------------------------

def plot_loss_correction(
    blocks,
    actual,
    forecast,
    corrected=None,
):
    """
    Plot Forecast vs Actual vs Corrected.
    """

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=forecast,
            name="Forecast",
            mode="lines",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=actual,
            name="Actual",
            mode="lines",
        )
    )

    if corrected is not None:

        fig.add_trace(
            go.Scatter(
                x=blocks,
                y=corrected,
                name="Corrected",
                mode="lines",
            )
        )

    return apply_default_layout(
        fig,
        "Loss Correction"
    )
