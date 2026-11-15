# MERIDIAN Breakout — BTC race bot

Momentum-breakout bot for make.fun bounty `btc-race-24h-20261115-0828`
(Race a BTC trading bot live for 24 hours). Trades cbBTC/USDC 1-min bars,
$1,000 paper, long only.

- Entry: EMA(20) crosses above EMA(55) AND trailing 30-bar return > +0.7%.
  Buy 100% of cash. No entries in the last 60 bars.
- Exit: take profit +2.5%, stop loss -2.0%, or EMA cross back.
- Dev window (exact-integer local replay): net PnL **+$26.77 (+2.68%)**,
  1 round trip, max drawdown 0.47%. Dev gate (PnL > $0) passes.

## Submit

Public GitHub repo owned by the entrant, created after the bounty opened
(2026-11-15T08:28Z), OSI license, `main.py` at repo root. This directory is
the exact push-ready content: `main.py` + `vendor/makefun_bars.py` + LICENSE.
