# Crypto Trading Bot Agent

This repository contains the core logic and backtesting engine for an autonomous cryptocurrency trading agent. It is designed to evaluate massive grids of technical indicator combinations (384 different configurations) over real historical market data (via `yfinance`).

The ultimate goal of this project is to take the most robust algorithmic strategy identified by the backtester and deploy it to **Robinhood Agentic Trading** via an MCP (Model Context Protocol) server.

## Repository Structure

The architecture is heavily modularized to separate the indicator math, the agent execution logic, and the historical testing engine.

* `indicators.py`: Contains the mathematical calculations for 200 SMA, VWAP, Fibonacci, Bullish Engulfing patterns, Daily Pivots, MACD, Volume SMA, and Stochastic Oscillator.
* `agent.py`: The core logic file. Contains `generate_signals`, which takes in historical data and boolean strategy toggles, outputting strict Buy and Sell triggers. (This is the module that will eventually be wrapped by the Robinhood MCP server).
* `backtest/`: A dedicated directory containing the vectorized backtesting engine and scripts to sweep strategies across different assets (BTC, ETH, SOL) and timeframes.
  * `backtest/backtest_engine.py`: Fast vectorized return and trade execution calculations.
  * `backtest/run_btc_sweep.py`: Sweeps 384 strategies on pure Bitcoin over 6 months to find the best configuration.

## Setup and Installation

1. Install dependencies:
```bash
pip install pandas numpy yfinance
```

## Running Backtests

To run a parameter sweep on Bitcoin to find the best 6-month technical indicator strategy:
```bash
cd backtest
python run_btc_sweep.py
```

Results are saved to `.csv` files inside the `backtest/` folder.

## Next Steps
- Integrate the winning parameters from `agent.py` into a FastAPI-based MCP server.
- Connect the MCP server to Robinhood Agentic Trading to enable live autonomous execution.
