# Breakout-Bot

This bot was made to receive webhook alerts from a private breakout strategy on tradingview. Its best feature is that it can place stop market orders for entries, and a Take Profit and Stop loss once the order is filled.

This type of bot outperforms other webhook third party bots, specially when markets have low volume since it greatly reduces slippage and latency.

Using cloud platform services like Heroku is recommended to avoid orders not being placed due to connection problems.
