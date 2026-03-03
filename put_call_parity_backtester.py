import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def main():
    # ============================================================
    # 1. Load the CSV data
    # ============================================================

    df = pd.read_csv("options_data.csv", low_memory=False)

    print("\n=== Raw data (first 10 rows) ===")
    print(df.head(10))
    print("\nData columns:", df.columns.tolist())
    print("\nNumber of rows:", len(df))

    # ============================================================
    # 2. Map vendor column names to standard names we use
    #    and select bid/ask and underlying
    # ============================================================

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

    # Tailored to your header names:
    # [QUOTE_READTIME], [EXPIRE_DATE], [STRIKE], [UNDERLYING_LAST],
    # [C_BID], [C_ASK], [P_BID], [P_ASK]
    timestamp_col = get_col(["QUOTE_READTIME", "QUOTE_DATE"], "timestamp")
    expiration_col = get_col(["EXPIRE_DATE"], "expiration")
    strike_col = get_col(["STRIKE"], "strike")
    spot_col = get_col(["UNDERLYING_LAST"], "spot")
    c_bid_col = get_col(["C_BID"], "C_BID")
    c_ask_col = get_col(["C_ASK"], "C_ASK")
    p_bid_col = get_col(["P_BID"], "P_BID")
    p_ask_col = get_col(["P_ASK"], "P_ASK")

    aligned = df[
        [
            timestamp_col,
            expiration_col,
            strike_col,
            spot_col,
            c_bid_col,
            c_ask_col,
            p_bid_col,
            p_ask_col,
        ]
    ].copy()

    aligned = aligned.rename(
        columns={
            timestamp_col: "timestamp",
            expiration_col: "expiration",
            strike_col: "strike",
            spot_col: "spot",
            c_bid_col: "C_BID",
            c_ask_col: "C_ASK",
            p_bid_col: "P_BID",
            p_ask_col: "P_ASK",
        }
    )

    aligned["timestamp"] = pd.to_datetime(aligned["timestamp"])
    aligned["expiration"] = pd.to_datetime(aligned["expiration"])

    for col in ["strike", "spot", "C_BID", "C_ASK", "P_BID", "P_ASK"]:
        aligned[col] = pd.to_numeric(aligned[col], errors="coerce")

    print("\n=== After selecting, renaming, and type-casting core columns (first 10 rows) ===")
    print(aligned.head(10))
    print("\nDtypes:", aligned.dtypes)
    print("\nNumber of rows (aligned):", len(aligned))

    aligned = aligned.dropna(
        subset=["timestamp", "expiration", "strike", "spot", "C_BID", "C_ASK", "P_BID", "P_ASK"]
    )

    print("\n=== After dropping rows with missing core fields (first 10 rows) ===")
    print(aligned.head(10))
    print("\nNumber of rows after dropping missing:", len(aligned))

    # ============================================================
    # 3. Time to expiration and PV(K)
    # ============================================================

    seconds_in_year = 365.0 * 24 * 60 * 60
    time_delta = aligned["expiration"] - aligned["timestamp"]
    aligned["T_years"] = time_delta.dt.total_seconds() / seconds_in_year

    # Keep options with positive time to expiry but less than ~60 days
    aligned = aligned[(aligned["T_years"] > 0) & (aligned["T_years"] <= 0.165)].copy()

    r = 0.04
    aligned["PV_K"] = aligned["strike"] * np.exp(-r * aligned["T_years"])

    print("\n=== After computing T_years and PV_K (first 10 rows) ===")
    print(aligned[["timestamp", "expiration", "strike", "spot", "T_years", "PV_K"]].head(10))
    print("\nNumber of rows after removing expired:", len(aligned))

    # ============================================================
    # 4. Synthetic/Actual with bid/ask and transaction costs
    # ============================================================

    # Simulated stock bid/ask from underlying last
    aligned["Stock_BID"] = aligned["spot"] - 0.02
    aligned["Stock_ASK"] = aligned["spot"] + 0.02

    # Transaction costs: $0.05 per option contract leg (2 legs: call + put)
    # We treat prices on a per-share basis, so total is 0.10 per share.
    transaction_cost_per_share = 0.05 * 2.0

    # Condition A (Reversal): Sell Synthetic, Buy Actual
    aligned["Arbitrage_A_Profit"] = (
        (aligned["C_BID"] - aligned["P_ASK"])
        - (aligned["Stock_ASK"] - aligned["PV_K"])
        - transaction_cost_per_share
    )

    # Condition B (Conversion): Buy Synthetic, Sell Actual
    aligned["Arbitrage_B_Profit"] = (
        (aligned["Stock_BID"] - aligned["PV_K"])
        - (aligned["C_ASK"] - aligned["P_BID"])
        - transaction_cost_per_share
    )

    print("\n=== Sample arbitrage profit calculations (first 10 rows) ===")
    print(
        aligned[
            [
                "timestamp",
                "expiration",
                "strike",
                "spot",
                "C_BID",
                "C_ASK",
                "P_BID",
                "P_ASK",
                "Stock_BID",
                "Stock_ASK",
                "PV_K",
                "Arbitrage_A_Profit",
                "Arbitrage_B_Profit",
            ]
        ].head(10)
    )

    # Choose best of the two arbitrage directions
    aligned["Best_Profit_per_share"] = aligned[
        ["Arbitrage_A_Profit", "Arbitrage_B_Profit"]
    ].max(axis=1)

    conditions = [
        aligned["Arbitrage_A_Profit"] >= aligned["Arbitrage_B_Profit"],
        aligned["Arbitrage_B_Profit"] > aligned["Arbitrage_A_Profit"],
    ]
    choices = ["A", "B"]
    aligned["Best_Condition"] = np.select(conditions, choices, default="None")

    aligned["Has_Arb"] = aligned["Best_Profit_per_share"] > 0

    print("\n=== Rows with any arbitrage (first 10) ===")
    print(
        aligned[aligned["Has_Arb"]][
            [
                "timestamp",
                "expiration",
                "strike",
                "spot",
                "Best_Condition",
                "Best_Profit_per_share",
            ]
        ].head(10)
    )

    # ============================================================
    # 5. Chronological portfolio simulator
    # ============================================================

    starting_capital = 100000.0
    current_cash = starting_capital
    active_trades = []  # each: dict with expiration_date, capital_required, expected_profit, direction

    # Sort by timestamp and add a date column
    aligned = aligned.sort_values("timestamp").reset_index(drop=True)
    aligned["date"] = aligned["timestamp"].dt.date

    # SPY benchmark: buy-and-hold underlying
    daily_spot = aligned.groupby("date")["spot"].last().sort_index()
    first_date = daily_spot.index[0]
    first_spot = daily_spot.iloc[0]
    benchmark_shares = int(starting_capital // first_spot)

    print(f"\nStarting capital: {starting_capital:,.2f}")
    print(f"First date: {first_date}, first spot: {first_spot:.2f}")
    print(f"Benchmark shares (SPY): {benchmark_shares}\n")

    portfolio_history = []

    unique_dates = sorted(aligned["date"].unique())

    for current_date in unique_dates:
        # 1) Settle trades that expire today
        matured = []
        for trade in active_trades:
            if trade["expiration_date"] <= current_date:
                matured.append(trade)

        if matured:
            print(f"\n=== {current_date} — settling {len(matured)} matured trades ===")

        for trade in matured:
            current_cash += trade["capital_required"] + trade["expected_profit"]
            active_trades.remove(trade)

        locked_capital = sum(t["capital_required"] for t in active_trades)

        # 2) Scan today's options for arbitrage, highest profit first
        today_rows = aligned[aligned["date"] == current_date]
        today_candidates = today_rows[today_rows["Has_Arb"]].copy()
        today_candidates = today_candidates.sort_values(
            "Best_Profit_per_share", ascending=False
        )

        new_trades = 0
        for _, row in today_candidates.iterrows():
            capital_required = row["spot"] * 100.0
            if current_cash < capital_required:
                continue

            if row["Best_Condition"] == "A":
                profit_per_share = row["Arbitrage_A_Profit"]
            elif row["Best_Condition"] == "B":
                profit_per_share = row["Arbitrage_B_Profit"]
            else:
                continue

            expected_profit = profit_per_share * 100.0

            current_cash -= capital_required
            active_trades.append(
                {
                    "open_date": current_date,
                    "expiration_date": row["expiration"].date(),
                    "direction": row["Best_Condition"],
                    "capital_required": capital_required,
                    "expected_profit": expected_profit,
                }
            )
            new_trades += 1

        locked_capital = sum(t["capital_required"] for t in active_trades)

        # 3) Portfolio value and benchmark
        current_spot = daily_spot.loc[current_date]
        benchmark_value = benchmark_shares * current_spot
        total_value = current_cash + locked_capital

        portfolio_history.append(
            {
                "date": current_date,
                "current_cash": current_cash,
                "locked_capital": locked_capital,
                "total_portfolio_value": total_value,
                "benchmark_value": benchmark_value,
                "num_active_trades": len(active_trades),
                "num_new_trades": new_trades,
            }
        )

        print(
            f"{current_date} | cash={current_cash:,.2f} "
            f"| locked={locked_capital:,.2f} "
            f"| total={total_value:,.2f} "
            f"| benchmark={benchmark_value:,.2f} "
            f"| active_trades={len(active_trades)} "
            f"| new_trades_today={new_trades}"
        )

    # ============================================================
    # 6. Visualization: arbitrage portfolio vs SPY benchmark
    # ============================================================

    history_df = pd.DataFrame(portfolio_history)
    history_df["date"] = pd.to_datetime(history_df["date"])

    plt.figure(figsize=(10, 6))
    plt.plot(
        history_df["date"],
        history_df["total_portfolio_value"],
        label="Arbitrage Portfolio",
    )
    plt.plot(
        history_df["date"],
        history_df["benchmark_value"],
        label="SPY Benchmark (Buy & Hold)",
    )
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value ($)")
    plt.title("Put-Call Parity Arbitrage Portfolio vs SPY Benchmark")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()

