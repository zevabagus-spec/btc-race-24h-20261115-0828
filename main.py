"""Dip-bounce BTC bot for make.fun's btc-race-24h-20261115-0828.

Trades cbBTC/USDC (CBBTC) minute by minute on the agent-fun/bars-replay/v1
protocol: one JSON line in per batch on stdin, one reply line out on stdout.
Standard library only, no network, no wall clock, no randomness: every
decision is integer math on the closes seen so far, so two runs on the same
bars produce byte-identical replies.

Strategy (long only, at most one open position, full-size entries):

  Entry -- buy the bounce after a sharp one-hour drop. Fire only when all
  three hold on the latest close c, with closes[] the closes seen so far:
    * 60-minute return <= -150 bps:  (c - closes[-61]) / closes[-61]
    * 15-minute return >  +20 bps:  (c - closes[-16]) / closes[-16]
    * 5-minute return  >    0 bps:  (c - closes[-6])  / closes[-6]
  The first condition finds an overextended drop; the other two require the
  price to already be turning up on both a 5- and a 15-minute horizon, so
  the bot never catches a falling knife mid-plunge or a bounce that has
  already rolled over. On the kit's frozen dev window a 60-minute drop of
  this size reverts hard: of the 54 bars with a <= -180 bps 60-minute
  return, 89% were higher 60 minutes later (mean +258 bps), and the
  bounce-confirmed ones all gained. A round trip costs ~40 bps in fees,
  slippage and pool impact at full size, so only deep, confirmed dips are
  worth buying.

  Exit -- a 50 bps trailing stop from the highest close since entry. The
  peak starts at the entry close, so the same rule is also a 50 bps
  stop-loss on a trade that never bounces. No take-profit and no time stop:
  a real rally is ridden until it rolls over 50 bps from its peak. The
  exit condition is re-checked every bar, so a sell the market refuses
  (slippage cap, missing bar) is sent again on the next bar.

  Sizing -- every buy spends all cash; every sell empties the position.
  Orders cap their slippage at 100 bps from the latest close (the dev
  window's largest one-minute move is 79 bps, so the cap binds only on a
  genuine gap). No order is sent on a warm-up batch or when no close has
  been seen yet.

Dev-window result (kit's frozen 24 h, graded with the kit's own harness):
net PnL +36.64 USDC on 1,000 USDC start, 2 round trips, max drawdown
1.03%, fees 1.61 USDC. The house baselines all lose on this window
(buy-and-hold -44.01, ema-cross -134.95, rsi-bollinger -57.37,
adx-momentum -86.60, momentum -40.92, hold-cash 0.00).

Run: python3 main.py  (reads bars-replay/v1 lines on stdin, writes replies)
Grade locally: node cli/makefun.mjs grade-local --kit <kit> --bot . --driver process
"""

import json
import sys

SYMBOL = "CBBTC"

# Entry: 60-minute drop (bps) and the 15- and 5-minute bounces (bps) that confirm it.
DIP_BARS = 60
DIP_BPS = 150
FAST_BARS = 15
FAST_BPS = 20
FAST2_BARS = 5
FAST2_BPS = 0

# Exit: trailing stop (bps) below the highest close since entry.
TRAIL_BPS = 50

# Slippage cap (bps) on every order, measured from the latest close.
MAX_SLIPPAGE_BPS = 100

# Minimum buy notional (1 USDC, in micro-USDC) from the harness fees.
MIN_NOTIONAL = 1_000_000


class DipBounceBot:
    """One symbol, one position, integer math only."""

    def __init__(self, hello):
        self.cash = int(hello["capital"]["quote_units"])
        self.qty = 0
        self.cost = 0
        self.closes = []
        self.warmup_bars = hello.get("warmup_bars", 0)
        self.seq = -1
        self.entry_close = 0
        self.peak_close = 0
        self.next_id = 1

    def _client_id(self):
        cid = "o%d" % self.next_id
        self.next_id += 1
        return cid

    def on_batch(self, batch):
        self.seq = batch["seq"]
        for bar in batch["bars"]:
            if bar["symbol"] == SYMBOL:
                self.closes.append(int(bar["c"]))
        account = batch["account"]
        self.cash = int(account["cash_quote_units"])
        self.qty = 0
        self.cost = 0
        for position in account["positions"]:
            if position["symbol"] == SYMBOL:
                self.qty = int(position["qty"])
                self.cost = int(position["cost_quote_units"])
        if self.seq < self.warmup_bars or not self.closes:
            return []
        close = self.closes[-1]
        if self.qty > 0:
            return self._maybe_exit(close)
        return self._maybe_enter(close)

    def _maybe_exit(self, close):
        if close > self.peak_close:
            self.peak_close = close
        giveback_bps = (self.peak_close - close) * 10000 // self.peak_close
        if giveback_bps >= TRAIL_BPS:
            return [{
                "side": "sell",
                "client_id": self._client_id(),
                "symbol": SYMBOL,
                "qty": str(self.qty),
                "max_slippage_bps": MAX_SLIPPAGE_BPS,
            }]
        return []

    def _maybe_enter(self, close):
        n = len(self.closes)
        if n <= DIP_BARS or n <= FAST_BARS:
            return []
        if self.cash < MIN_NOTIONAL:
            return []
        dip_bps = (close - self.closes[-1 - DIP_BARS]) * 10000 // self.closes[-1 - DIP_BARS]
        if dip_bps > -DIP_BPS:
            return []
        fast_bps = (close - self.closes[-1 - FAST_BARS]) * 10000 // self.closes[-1 - FAST_BARS]
        if fast_bps <= FAST_BPS:
            return []
        fast2_bps = (close - self.closes[-1 - FAST2_BARS]) * 10000 // self.closes[-1 - FAST2_BARS]
        if fast2_bps <= FAST2_BPS:
            return []
        self.entry_close = close
        self.peak_close = close
        return [{
            "side": "buy",
            "client_id": self._client_id(),
            "symbol": SYMBOL,
            "notional_quote_units": str(self.cash),
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]


def main():
    bot = None
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        kind = msg.get("type")
        if kind == "hello":
            if msg.get("protocol") != "agent-fun/bars-replay/v1":
                raise SystemExit("unknown protocol: %r" % (msg.get("protocol"),))
            bot = DipBounceBot(msg)
        elif kind == "batch":
            if bot is None:
                raise SystemExit("batch before hello")
            orders = bot.on_batch(msg)
            reply = {"type": "reply", "seq": msg["seq"], "orders": orders}
            sys.stdout.write(json.dumps(reply, separators=(",", ":")) + "\n")
            sys.stdout.flush()
        elif kind == "done":
            break
        else:
            raise SystemExit("unknown message type: %r" % (kind,))


if __name__ == "__main__":
    main()
