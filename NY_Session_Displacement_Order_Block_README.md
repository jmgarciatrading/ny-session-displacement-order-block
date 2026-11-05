# NY Window Displacement Order Block

`NY_Session_Displacement_Order_Block.pine` is a standalone TradingView Pine
Script v6 overlay that keeps one structural-origin order-block box from the New
York calendar day of the chart's latest available bar.

## Detection rule

A bullish order block requires:

1. A bearish anchor candle.
2. One immediately following bullish displacement candle.
3. The displacement candle closes above the anchor's high.

A bearish order block is the exact inverse: a bullish anchor followed by one
bearish displacement candle that closes below the anchor's low.

The anchor is always the candle immediately before displacement. The indicator
does not scan backward for a different candle. Detection happens only after the
displacement candle closes, so it does not use future data.

## Time window

Set the start and end hour/minute under **New York Time Window**. The interval is
start-inclusive and end-exclusive. An end earlier than the start creates an
overnight window; equal start and end means all day.

Both candles (the order block and its displacement candle) must open
inside the window and belong to the New York date of the chart's latest
available bar. Other dates are not drawn. For example, once the chart advances
to Monday, Friday's box is removed immediately. If Monday has no qualifying
order block yet, no box is shown.

The timezone is fixed to `America/New_York`, so TradingView applies New York
daylight-saving changes automatically. The inputs are intended for intraday
charts.

## Display and colors

The first qualifying order block in a directional move remains visible while it
is unmitigated. Later same-direction continuation blocks do not replace it. A
zone becomes mitigated when a later candle's high-low range first touches it;
after that, the next valid block may replace it. A valid opposite-direction
block starts a new directional move and may also replace the displayed block.

The box uses the full high-to-low range of its anchor candle and extends to the
right. Use **Bullish Order Block** and **Bearish Order Block** to choose each box
color and transparency.

## Prior swing marker

Each displayed bearish OB gets a small down arrow above the nearest confirmed
swing high strictly before its anchor. Each bullish OB gets a small up arrow
below the nearest confirmed swing low. If the OB candle is itself a confirmed
swing, it is deliberately skipped and the preceding swing is marked instead.

`Swing Strength` controls how many bars must appear on each side of a pivot; it
defaults to 2. Only a swing from the active New York chart day is eligible. The
marker is deleted and rebuilt together with its associated order-block box.

TradingView-hosted compilation and visual inspection are still required because
this workspace does not include TradingView's Pine compiler or chart renderer.
