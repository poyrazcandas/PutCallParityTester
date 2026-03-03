import pandas as pd
import numpy as np


def main():
    # ==========================
    # 1. Load the CSV data
    # ==========================

    df = pd.read_csv("options_data.csv", low_memory=False)

    print("\n=== Raw data (first 10 rows) ===")
    print(df.head(10))
    print("\nData columns:", df.columns.tolist())
    print("\nNumber of rows:", len(df))

    # ==========================
    # 1b. Map vendor column names
    #     to standard names we use
    # ==========================

    canonical_map = {}
    for c in df.columns:
        canon = c.strip()
        if canon.startswith("[") and canon.endswith("]"):
            canon = canon[1:-1]
        canon = canon.strip().lower()
        canonical_map[canon] = c

    def get_col(candidates, required_name):
        for cand in candidates:
            key = cand.lower()
            if key in canonical_map:
                return canonical_map[key]
        raise ValueError(
            f"Could not find required column for '{required_name}'. "
            f"Available columns: {list(df.columns)}"
        )

    # These are tailored to the sample headers you have:
    # [QUOTE_READTIME], [EXPIRE_DATE], [STRIKE], [UNDERLYING_LAST],
    # [C_LAST], [P_LAST]
    timestamp_actual = get_col(
        ["QUOTE_READTIME", "QUOTE_DATE"],
        "timestamp",
    )
    expiration_actual = get_col(
        ["EXPIRE_DATE"],
        "expiration",
    )
    strike_actual = get_col(
        ["STRIKE"],
        "strike",
    )
    spot_actual = get_col(
        ["UNDERLYING_LAST"],
        "spot",
    )
    c_price_actual = get_col(
        ["C_LAST", "C_BID"],
        "C_price",
    )
    p_price_actual = get_col(
        ["P_LAST", "P_BID"],
        "P_price",
    )

    aligned = df[
        [
            timestamp_actual,
            expiration_actual,
            strike_actual,
            spot_actual,
            c_price_actual,
            p_price_actual,
        ]
    ].copy()

    aligned = aligned.rename(
        columns={
            timestamp_actual: "timestamp",
            expiration_actual: "expiration",
            strike_actual: "strike",
            spot_actual: "spot",
            c_price_actual: "C_price",
            p_price_actual: "P_price",
        }
    )

    aligned["timestamp"] = pd.to_datetime(aligned["timestamp"])
    aligned["expiration"] = pd.to_datetime(aligned["expiration"])

    # Ensure numeric types for math operations
    for col in ["strike", "spot", "C_price", "P_price"]:
        aligned[col] = pd.to_numeric(aligned[col], errors="coerce")

    print("\n=== After selecting, renaming, and type-casting core columns (first 10 rows) ===")
    print(aligned.head(10))
    print("\nDtypes:", aligned.dtypes)
    print("\nNumber of rows (aligned):", len(aligned))

    # Drop rows where any of the core fields are missing
    aligned = aligned.dropna(
        subset=[
            "timestamp",
            "expiration",
            "strike",
            "spot",
            "C_price",
            "P_price",
        ]
    )

    print("\n=== After dropping rows with missing core fields (first 10 rows) ===")
    print(aligned.head(10))
    print("\nNumber of rows after dropping missing:", len(aligned))

    # ==========================
    # 3. Calculate T (time to expiration in years)
    # ==========================

    seconds_in_year = 365.0 * 24 * 60 * 60
    time_delta = aligned["expiration"] - aligned["timestamp"]
    aligned["T_years"] = time_delta.dt.total_seconds() / seconds_in_year

    print("\n=== After computing T_years (first 10 rows) ===")
    print(aligned[["timestamp", "expiration", "strike", "spot", "T_years"]].head(10))

    # ==========================
    # 4. Present value of K: K * e^(-rT)
    # ==========================

    r = 0.04  # constant risk-free rate

    aligned["PV_K"] = aligned["strike"] * np.exp(-r * aligned["T_years"])

    print("\n=== After computing PV_K (first 10 rows) ===")
    print(aligned[["strike", "T_years", "PV_K"]].head(10))

    # ==========================
    # 5. Synthetic Forward: C - P
    # ==========================

    aligned["Synthetic_Forward"] = aligned["C_price"] - aligned["P_price"]

    print("\n=== After computing Synthetic_Forward (first 10 rows) ===")
    print(aligned[["C_price", "P_price", "Synthetic_Forward"]].head(10))

    # ==========================
    # 6. Actual Forward: S - PV(K)
    # ==========================

    aligned["Actual_Forward"] = aligned["spot"] - aligned["PV_K"]

    print("\n=== After computing Actual_Forward (first 10 rows) ===")
    print(aligned[["spot", "PV_K", "Actual_Forward"]].head(10))

    # ==========================
    # 7. Flag Put-Call Parity arbitrage
    #    |Synthetic - Actual| > 0.05
    # ==========================

    transaction_cost_margin = 0.05

    aligned["Parity_Diff"] = aligned["Synthetic_Forward"] - aligned["Actual_Forward"]
    aligned["Abs_Parity_Diff"] = aligned["Parity_Diff"].abs()
    aligned["Arb_Opportunity"] = aligned["Abs_Parity_Diff"] > transaction_cost_margin

    print("\n=== After flagging arbitrage opportunities (first 20 rows) ===")
    print(
        aligned[
            [
                "timestamp",
                "expiration",
                "strike",
                "spot",
                "C_price",
                "P_price",
                "T_years",
                "PV_K",
                "Synthetic_Forward",
                "Actual_Forward",
                "Parity_Diff",
                "Abs_Parity_Diff",
                "Arb_Opportunity",
            ]
        ].head(20)
    )

    num_arb = aligned["Arb_Opportunity"].sum()
    print(f"\nTotal arbitrage opportunities flagged: {num_arb}")

    # Optional: inspect only arbitrage rows
    arb_rows = aligned[aligned["Arb_Opportunity"]].copy()
    print("\n=== Sample arbitrage rows (first 20) ===")
    print(
        arb_rows[
            [
                "timestamp",
                "expiration",
                "strike",
                "spot",
                "C_price",
                "P_price",
                "Synthetic_Forward",
                "Actual_Forward",
                "Abs_Parity_Diff",
            ]
        ].head(20)
    )


if __name__ == "__main__":
    main()

