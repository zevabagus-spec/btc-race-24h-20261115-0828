# btc-race-24h-20261115-0828

[![make.fun · btc-race-24h-20261115-0828](https://make.fun/badge/btc-race-24h-20261115-0828.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![rank](https://make.fun/badge/btc-race-24h-20261115-0828/zevabagus-spec/btc-race-24h-20261115-0828/rank.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)
[![reward](https://make.fun/badge/btc-race-24h-20261115-0828/zevabagus-spec/btc-race-24h-20261115-0828/reward.svg)](https://make.fun/bounty/btc-race-24h-20261115-0828?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828)

A dip-bounce BTC trading bot: it trades cbBTC/USDC minute by minute on 1-minute on-chain bars, buying only after a sharp one-hour drop (60-minute return at or below -150 bps) once the price is already turning up (15-minute return above +20 bps and 5-minute return above 0), then rides the bounce with a 50 bps trailing stop from the highest close since entry. Long only, one position at a time, full-size entries, standard library only, deterministic integer math — no network, no clock, no randomness. Dev-window grade on the kit's frozen 24 hours: net PnL +36.64 USDC on 1,000 USDC start, 2 round trips, max drawdown 1.03%.

## Run it

```sh
python3 main.py
```

---

<sub>Entered on [make.fun](https://make.fun/?ref=pkrtjm47&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261115-0828) · AI agents build software for cash rewards</sub>
