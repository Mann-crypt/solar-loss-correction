# plotting.py

import numpy as np
import plotly.graph_objects as go

def get_blocks(length=96):
    return np.arange(1, length + 1)

def apply_default_layout(fig, title=None):
    """
    Apply a common layout to all Plotly figures.
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
        gridcolor="#E5E5E5"
    )

    fig.update_yaxes(
        showgrid=True,
        gridcolor="#E5E5E5"
    )

    return fig

plot_rt_forecast(
    blocks=df["Blocks"],
    projection=df["Projection"],
    forecast=df["RT Forecast"],
    actual=df["Actual"],
)
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
            line=dict(width=2)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=forecast,
            name="RT Forecast",
            line=dict(width=3)
        )
    )

    fig.add_trace(
        go.Scatter(
            x=blocks,
            y=actual,
            name="Actual",
            line=dict(width=3)
        )
    )

    return apply_default_layout(
        fig,
        "RT Correction"
    )



def plot_cam_curve(percentile, profile, symmetric):

  fig = go.Figure()

  fig.add_trace(
      go.Scatter(
          x = get_blocks(len(percentile)),
          y=symmetric,
          name="Sym Profile",
          line=dict(color="blue", width=4)
      )
  )

  fig.add_trace(
      go.Scatter(
          x = get_blocks(len(percentile)),
          y=profile,
          name="Profile",
          line=dict(color="green", width=4)
      )
  )

  fig.add_trace(
      go.Scatter(
          x = get_blocks(len(percentile)),
          y=percentile,
          name="95th Percentile",
          line=dict(color="red", width=4)
      )
  )

  fig.update_xaxes(title="Block")
  fig.update_yaxes(title="Power")

return apply_default_layout(
    fig,
    "CAM Curve"
)

  return apply_default_layout(
      fig,
      "CAM Curve"
  )

def plot_loss_correction(
    blocks,
    actual,
    forecast,
    corrected=None,
):
  fig = go.Figure()

  fig.add_trace(
      go.Scatter(
          x=blocks,
          y=forecast,
          name="Forecast",
          line=dict(width=3)
      )
  )
  
  fig.add_trace(
      go.Scatter(
          x=blocks,
          y=actual,
          name="Actual",
          line=dict(width=3)
      )
  )
  
  if corrected is not None:
  
      fig.add_trace(
          go.Scatter(
              x=blocks,
              y=corrected,
              name="Corrected",
              line=dict(width=3)
          )
      )
  
  return apply_default_layout(
      fig,
      "Loss Correction"
  )
