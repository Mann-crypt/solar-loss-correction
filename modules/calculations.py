def calculate_loss_corrected_weights(
    area_df,
    efficiency_loss,
    weight_factors,
    has_cluster=True,
):
    """
    Calculate effective area / weights.

    Cluster:
        One weight per GHI cluster.

    Non-cluster:
        One total plant weight.
    """

    df = area_df.copy()

    # --------------------------------------------------
    # Efficiency
    # --------------------------------------------------

    df["Efficiency Losses(%)"] = (
        float(efficiency_loss)
    )

    df["Net Efficiency (%)"] = (
        pd.to_numeric(
            df["Standard PV Efficiency (%)"],
            errors="coerce",
        ).fillna(0)
        - df["Efficiency Losses(%)"]
    )

    # --------------------------------------------------
    # Prevent negative efficiency
    # --------------------------------------------------

    df["Net Efficiency (%)"] = np.maximum(
        df["Net Efficiency (%)"],
        0,
    )

    # --------------------------------------------------
    # Effective area
    # --------------------------------------------------

    df["Effective Area"] = (

        pd.to_numeric(
            df["Total area(m2)"],
            errors="coerce",
        ).fillna(0)

        *

        df["Net Efficiency (%)"]

        / 100
    )

    total_effective_area = (
        df["Effective Area"].sum()
    )

    # ==================================================
    # NON-CLUSTER
    # ==================================================

    if not has_cluster:

        return np.asarray(
            [total_effective_area],
            dtype=float,
        )

    # ==================================================
    # CLUSTER
    # ==================================================

    weight_factors = np.asarray(
        weight_factors,
        dtype=float,
    )

    if len(weight_factors) == 0:

        raise ValueError(
            "No cluster weight factors supplied."
        )

    # Normalize if required

    if np.sum(weight_factors) > 0:

        weight_factors = (
            weight_factors
            / np.sum(weight_factors)
        )

    weights = (
        total_effective_area
        * weight_factors
    )

    return np.asarray(
        weights,
        dtype=float,
    )
