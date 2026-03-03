import pandas as pd
import numpy as np


def main():
    # ==========================
    # 1. Load the CSV data
    # ==========================

    df = pd.read_csv("options_data.csv")

    print("\n=== Raw data (first 10 rows) ===")
    print(df.head(10))
    print("\nData columns:", df.columns.tolist())
    print("\nNumber of rows:", len(df))

    # ==========================
    # 1b. Normalize column names
    #     so the rest of the script
    #     can assume standard names
    # ==========================

    cols_lower = {c.lower(): c for c in df.columns}

    def find_col(candidates, required_name):
        for cand in candidates:
            if cand in cols_lower:
                return cols_lower[cand]
        raise ValueError(
            f"Could not find required column for '{required_name}'. "
            f"Available columns: {list(df.columns)}"
        )

    timestamp_actual = find_col(
        ["timestamp", "time", "datetime", "date"],
        "timestamp",
    )
    expiration_actual = find_col(
        ["expiration", "expiry", "exp_date", "maturity", "expiration_date"],
        "expiration",
    )
    strike_actual = find_col(
        ["strike", "k", "strike_price"],
        "strike",
    )
    option_type_actual = find_col(
        ["option_type", "cp_flag", "call_put", "type"],
        "option_type",
    )
    option_price_actual = find_col(
        ["option_price", "price", "option_px"],
        "option_price",
    )
    spot_actual = find_col(
        ["spot", "underlying", "underlying_price", "s", "stock_price"],
        "spot",
    )

    rename_map = {
        timestamp_actual: "timestamp",
        expiration_actual: "expiration",
        strike_actual: "strike",
        option_type_actual: "option_type",
        option_price_actual: "option_price",
        spot_actual: "spot",
    }

    df = df.rename(columns=rename_map)

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["expiration"] = pd.to_datetime(df["expiration"])

    print("\n=== After normalizing column names (first 10 rows) ===")
    print(df.head(10))
    print("\nData columns (normalized):", df.columns.tolist())
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

