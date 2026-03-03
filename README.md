# Put-Call Parity Arbitrage Backtester

A simple procedural Python backtester that scans historical options data for **put-call parity** violations and flags potential arbitrage opportunities above a given transaction-cost threshold.

---

## Put-Call Parity (no dividends)

Under no-arbitrage, the following must hold:

$$C - P = S - K e^{-rT}$$

- **C** = call price, **P** = put price  
- **S** = spot price, **K** = strike, **r** = risk-free rate, **T** = time to expiration (years)

- **Synthetic forward:** \(C - P\)  
- **Actual forward:** \(S - K e^{-rT}\)

The script computes both sides and flags rows where \(|(C - P) - (S - K e^{-rT})|\) exceeds a chosen margin (e.g. 0.05).

---

## Requirements

- Python 3.x  
- `pandas`  
- `numpy`

```bash
pip install pandas numpy
```

---

## Data

Place a file named **`options_data.csv`** in the same directory as the script.

Expected columns:

| Column        | Description                          |
|---------------|--------------------------------------|
| `timestamp`   | Quote datetime                       |
| `expiration`  | Option expiration datetime           |
| `strike`      | Strike price \(K\)                   |
| `option_type` | `'C'` (call) or `'P'` (put)          |
| `option_price`| Option price                         |
| `spot`        | Underlying spot price \(S\)          |

The script pivots the data so that for each `(timestamp, expiration, strike, spot)` there is one row with both call and put prices.

---

## Usage

From the project directory:

```bash
python put_call_parity_backtester.py
```

The script prints the DataFrame after each major step so you can verify alignment and computed columns.

---

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Risk-free rate `r` | 0.04 | Used in \(K e^{-rT}\) |
| Transaction cost margin | 0.05 | Arbitrage flag when \(\|C-P - (S - K e^{-rT})\| >\) this value |

Edit these near the top of `main()` in `put_call_parity_backtester.py` if you want to change them.

---

## Output

The final DataFrame includes (among others):

- **T_years** — time to expiration in years  
- **PV_K** — \(K e^{-rT}\)  
- **Synthetic_Forward** — \(C - P\)  
- **Actual_Forward** — \(S - K e^{-rT}\)  
- **Parity_Diff** — Synthetic minus Actual  
- **Abs_Parity_Diff** — absolute difference  
- **Arb_Opportunity** — `True` when `Abs_Parity_Diff >` transaction cost margin  

A summary count of flagged arbitrage opportunities is printed at the end.

---

## License

Use and modify as you like.
