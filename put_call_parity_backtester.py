import pandas as pd
import numpy as np


def main():
    # ==========================
    # 1. Load the CSV data
    # ==========================

    # Adjust parse_dates list if your datetime columns have different names
    df = pd.read_csv(
        "options_data.csv",
        parse_dates=["timestamp", "expiration"],
    )

    print("\n=== Raw data (first 10 rows) ===")
    print(df.head(10))
    print("\nData columns:", df.columns.tolist())
    print("\nNumber of rows:", len(df))

    # ==========================
    # 2. Clean & align the data
    #    Get C, P, S in same row
    # ==========================

    # Drop rows with critical missing values
    df = df.dropna(
        subset=[
            "timestamp",
            "expiration",
            "strike",
            "option_type",
            "option_price",
            "spot",
        ]
    )

    # Ensure consistent option_type values (e.g., 'C'/'P')
    df["option_type"] = df["option_type"].astype(str).str.upper().str.strip()

    # Pivot so that each row has columns for Call (C) and Put (P)
    # Index is timestamp, expiration, strike, and spot (S)
    aligned = (
        df.pivot_table(
            index=["timestamp", "expiration", "strike", "spot"],
            columns="option_type",
            values="option_price",
            aggfunc="mean",  # if multiple quotes per bucket, average them
        )
        .reset_index()
    )

    # After pivot, columns 'C' and 'P' should exist
    aligned = aligned.rename(columns={"C": "C_price", "P": "P_price"})

    print("\n=== After pivot/alignment (first 10 rows) ===")
    print(aligned.head(10))
    print("\nData columns after alignment:", aligned.columns.tolist())
    print("\nNumber of rows after alignment:", len(aligned))

    # Drop rows where either C or P is missing
    aligned = aligned.dropna(subset=["C_price", "P_price"])

    print("\n=== After dropping rows with missing C or P (first 10 rows) ===")
    print(aligned.head(10))
    print("\nNumber of rows after dropping missing C/P:", len(aligned))

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

