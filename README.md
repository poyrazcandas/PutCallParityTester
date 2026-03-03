## Put-Call Parity Arbitrage Portfolio Simulator

A single-file Python project that:

- **Loads** historical SPY options data from `options_data.csv`
- **Builds** put–call parity arbitrage signals using bid/ask quotes
- **Simulates** a chronological options portfolio that executes 1‑contract arbitrage trades when capital allows
- **Benchmarks** against a buy‑and‑hold SPY position
- **Plots** portfolio value vs benchmark over time

---

## Requirements

- Python 3.x  
- `pandas`  
- `numpy`  
- `matplotlib`

```bash
pip install pandas numpy matplotlib
```

---

## Data

Place a file named `options_data.csv` in the same directory as the script.

The script expects CBOE‑style SPY options data with columns like:

| Column              | Description                          |
|---------------------|--------------------------------------|
| `[QUOTE_READTIME]`  | Quote timestamp (local time)         |
| `[EXPIRE_DATE]`     | Option expiration date               |
| `[STRIKE]`          | Strike price \(K\)                   |
| `[UNDERLYING_LAST]` | Underlying SPY last price \(S\)      |
| `[C_BID]` / `[C_ASK]` | Call bid / ask                    |
| `[P_BID]` / `[P_ASK]` | Put bid / ask                     |

Column names are automatically mapped by stripping spaces/brackets and lowercasing, so the script is tolerant to minor formatting differences.

---

## Arbitrage Logic

Assumptions:

- **No dividends**
- **Risk‑free rate** \(r = 0.04\)
- **1 option contract = 100 shares**
- **Transaction costs**: \$0.05 per option contract leg (one call + one put = 2 legs)

For each quote:

- **Time to expiration in years**

  \[
  T = \frac{\text{expiration} - \text{timestamp}}{365 \times 24 \times 60 \times 60}
  \]

- **Present value of strike**

  \[
  \text{PV}_K = K \, e^{-rT}
  \]

- **Simulated stock bid/ask** around the last price

  \[
  \text{Stock\_BID} = S - 0.02, \quad \text{Stock\_ASK} = S + 0.02
  \]

We treat all prices on a **per‑share** basis.  
The transaction‑cost impact per share is:

- `transaction_cost_per_share = 0.05 * 2 = 0.10`

### Condition A – Reversal (Sell Synthetic, Buy Actual)

Use call **bid**, put **ask**, and stock **ask**:

\[
\text{Arbitrage\_A\_Profit} =
\big(C_{\text{BID}} - P_{\text{ASK}}\big)
- \big(\text{Stock\_ASK} - \text{PV}_K\big)
- \text{transaction\_cost\_per\_share}
\]

### Condition B – Conversion (Buy Synthetic, Sell Actual)

Use call **ask**, put **bid**, and stock **bid**:

\[
\text{Arbitrage\_B\_Profit} =
\big(\text{Stock\_BID} - \text{PV}_K\big)
- \big(C_{\text{ASK}} - P_{\text{BID}}\big)
- \text{transaction\_cost\_per\_share}
\]

For each row the script computes:

- **`Arbitrage_A_Profit`**, **`Arbitrage_B_Profit`** (per share)
- **`Best_Profit_per_share`** = `max(Arbitrage_A_Profit, Arbitrage_B_Profit)`
- **`Best_Condition`** = `"A"` or `"B"` depending on which is better
- **`Has_Arb`** = `True` when `Best_Profit_per_share > 0`

In addition, only options with **time to expiration between 0 and ~60 days** are used in the simulation:

- `0 < T_years <= 0.165`

This avoids locking capital in far‑dated LEAPS.

---

## Chronological Portfolio Simulator

- **Starting capital**: `100000`  
- **Sorting**: all quotes are sorted chronologically by `timestamp`.  
- A daily `date` column is derived from `timestamp` for portfolio tracking.

### Trade Execution Rules

For each trading `date`:

- **1. Settle expiring trades**
  - Any active trade whose `expiration_date <= current_date` is considered matured.
  - On maturity, the simulator **releases the original capital and the expected profit**:
    - `current_cash += capital_required + expected_profit`

- **2. Scan for arbitrage opportunities**
  - Filter that day’s rows where `Has_Arb == True`.
  - Sort candidates by `Best_Profit_per_share` (highest first).
  - For each candidate:
    - Compute **`Capital_Required = spot * 100`** (1 contract = 100 shares of SPY).
    - If `Current_Cash >= Capital_Required`, open a **single 1‑lot trade**:
      - Subtract `Capital_Required` from `current_cash`.
      - Append an entry to `active_trades` containing:
        - `open_date`, `expiration_date`  
        - `direction` (`"A"` or `"B"`)  
        - `capital_required`  
        - `expected_profit = Best_Profit_per_share * 100`

- **3. Portfolio value per date**
  - `Locked_Capital = sum(trade["capital_required"] for trade in active_trades)`  
  - `Total_Portfolio_Value = Current_Cash + Locked_Capital`

The script prints a **one‑line daily summary**:

- Date, `current_cash`, `locked_capital`, `total_portfolio_value`, SPY benchmark value, number of active trades, and number of new trades opened that day.

---

## SPY Benchmark

On the **first trading date**:

- Use the initial `100000` capital to buy as many shares of SPY (the underlying spot) as possible at that day’s spot price.

For each subsequent date:

- Take the **last SPY price of that date** (`spot`) and compute:

  \[
  \text{Benchmark\_Value} = \text{Shares} \times \text{Current\_Spot\_Price}
  \]

This is a simple **buy‑and‑hold SPY benchmark**.

---

## Visualization

At the end of the simulation, the script builds a `portfolio_history` DataFrame with:

- `date`
- `current_cash`
- `locked_capital`
- `total_portfolio_value`
- `benchmark_value`
- `num_active_trades`
- `num_new_trades`

It then uses `matplotlib` to plot **two lines over time**:

- **Arbitrage Portfolio Value** (`total_portfolio_value`)
- **SPY Benchmark Value** (`benchmark_value`)

Both lines use **date on the x‑axis** and **value in dollars on the y‑axis**.

---

## Usage

From the project directory:

```bash
python put_call_parity_backtester.py
```

You will see:

- Early prints showing data loading, column mappings, and arbitrage calculations.  
- Daily portfolio summaries logging cash, locked capital, total value, benchmark, and trade counts.  
- A final pop‑up window with the **arbitrage portfolio vs SPY benchmark** chart.

---

## License

Use and modify as you like.

