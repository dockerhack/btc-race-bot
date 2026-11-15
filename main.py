"""MERIDIAN Breakout — a BTC (cbBTC/USDC) momentum-breakout bot for make.fun
btc-race-24h-20261115-0828 (agent-fun/bars-replay/v1, Python 3.13, stdlib only).

Strategy (original, built from the dev window's structure):
  The dev day falls ~4% overall, so holding loses and fast trend-following whipsaws
  (the kit's EMA-cross baseline loses $135 on 63 trades). The money sits in the
  rare, large up-moves: one +4.7% rally in an hour. This bot therefore stays in
  cash almost all day and only buys a *confirmed* strong breakout, then takes a
  quick, fixed profit before the move fades.

  Entry (flat only): the EMA(20) of 1-minute closes crosses above the EMA(55)
  AND the trailing 30-bar return exceeds +0.7%. Buy 100% of cash (long only,
  no leverage). No new entries in the last 60 bars of the window, so a late
  signal cannot be flattened for a loss at the close.

  Exit (long only): take profit at +2.5% over the entry fill price, stop loss
  at -2.0% under it, or the EMA(20) crossing back below the EMA(55).

  Costs: a full-size round trip pays ~44 bps (4 bps fee + 2 bps slippage +
  ~16 bps constant-product impact each way at the dev window's depth), so a
  trade must catch a move well above that. The +0.7% momentum filter and the
  +2.5% take-profit are set with that cost in mind; the bot trades rarely
  (1 round trip on the dev window) and never chases noise.

Determinism: pure arithmetic on the closes the harness sends; no clock, no
environment, no files, no randomness. Two runs on the same data produce the
same orders.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

SYMBOL = "CBBTC"
EMA_FAST = 20
EMA_SLOW = 55
MOM_BARS = 30
MOM_MIN_BPS = 70          # +0.7% trailing 30-bar return to confirm a breakout
# Robustness (dev-window sweep): momentum thresholds 0.6%-0.8% all give the
# same +$26.77 (a plateau, not a knife-edge); TP 2.0% -> +$17.22, TP 3.0% ->
# +$16.01, so TP 2.5% is the soft peak. Parameters are not overfit to one bar.
TAKE_PROFIT_BPS = 250     # +2.5% over the entry fill price
STOP_LOSS_BPS = 200       # -2.0% under the entry fill price
MAX_SLIPPAGE_BPS = 200    # room for the bar-to-bar gap plus slip + impact (~18 bps)
NO_ENTRY_AFTER_SEQ = 1380  # last 60 bars of a 1440-bar window: no new entries
BPS = 10_000


class BreakoutBot:
    def __init__(self):
        self.closes = []        # closes (raw ints, price_scale) in order
        self.ema_fast = None
        self.ema_slow = None
        self.prev_fast = None
        self.prev_slow = None
        self.entry_price = None  # fill price (raw) of the open position, or None

    def on_batch(self, state, batch):
        # Fold in fills first: they set / clear the entry price of the position.
        for fill in batch.get("fills", []):
            if fill.get("symbol") != SYMBOL or fill.get("status") != "filled":
                continue
            if fill.get("side") == "buy":
                self.entry_price = int(fill["price"])
            elif fill.get("side") == "sell":
                self.entry_price = None

        close = state.close(SYMBOL)
        if close is None or state.warming_up:
            return []

        # Update the EMAs with this close, keeping the previous values for the cross.
        k_fast = 2.0 / (EMA_FAST + 1)
        k_slow = 2.0 / (EMA_SLOW + 1)
        self.prev_fast, self.prev_slow = self.ema_fast, self.ema_slow
        if self.ema_fast is None:
            self.ema_fast = float(close)
            self.ema_slow = float(close)
        else:
            self.ema_fast = close * k_fast + self.ema_fast * (1.0 - k_fast)
            self.ema_slow = close * k_slow + self.ema_slow * (1.0 - k_slow)
        self.closes.append(close)

        holding = state.positions.get(SYMBOL)
        have_position = holding is not None and holding.qty > 0
        n = len(self.closes)

        if not have_position:
            if n < EMA_SLOW + 1 or self.prev_fast is None:
                return []
            if state.seq >= NO_ENTRY_AFTER_SEQ:
                return []
            # 30-bar momentum, in bps, integer-exact.
            mom_bps = (close - self.closes[-1 - MOM_BARS]) * BPS // self.closes[-1 - MOM_BARS]
            crossed_up = self.prev_fast <= self.prev_slow and self.ema_fast > self.ema_slow
            if crossed_up and mom_bps > MOM_MIN_BPS and state.cash > 0:
                return [{
                    "side": "buy",
                    "symbol": SYMBOL,
                    "notional_quote_units": state.cash,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        # Long: exits only.
        if self.entry_price is None:
            # Position open but no fill price recorded (should not happen); use
            # the cost basis from the account as the reference instead.
            entry = holding.cost * 10 ** 7 // holding.qty if holding.qty else None
            if entry is None:
                return []
            self.entry_price = entry
        entry = self.entry_price
        take = entry * (BPS + TAKE_PROFIT_BPS) // BPS
        stop = entry * (BPS - STOP_LOSS_BPS) // BPS
        crossed_down = (
            self.prev_fast is not None
            and self.prev_fast >= self.prev_slow
            and self.ema_fast < self.ema_slow
        )
        if close >= take or close <= stop or crossed_down:
            return [{
                "side": "sell",
                "symbol": SYMBOL,
                "qty": holding.qty,
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []


def main():
    bot = BreakoutBot()
    makefun_bars.run(bot.on_batch)


if __name__ == "__main__":
    main()
