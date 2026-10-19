# The owner's two reels: what the media actually says (2026-10-19)

How it was obtained:
- **Download:** `yt-dlp` 2026.08.19, with no login. The public page itself is a login shell.
- **Speech:** `faster-whisper` "small" on CPU, with audio decoded by ffmpeg.
- **Frames:** extracted at 3 frames per second.
- The files stayed in the session scratchpad and were not committed.

## Reel 1: instagram.com/reel/DcOhWbqm3vK (Git Radar, @git.radar, 2026-08-19, 71.8 s)
- **Caption:** "Production-grade Rust-native trading engine with deterministic event-driven architecture
  https://github.com/nautechsystems/nautilus_trader".
- **Speech** (English, language probability 1.00):
  - "This project, Nautilus Trader, is a high performance engine that handles all the complex math and speed required
    to trade stocks or crypto at a professional level."
  - "It's built in a language called Rust…"
  - "it lets you test your strategy using historical data before you risk a single cent in the real market. It ensures
    that the exact same logic you used for your experiments works perfectly when you start trading with real money."
  - "…it has already earned 26,314 stars…"

## Reel 2: instagram.com/reel/DcgZhLyiZ3o (Filip Gajko, @iclosegreen, 2026-08-26, 6.3 s)
- **Speech:** none. Whisper finds no segments; the track is music.
- **Frames:** one title card, "6 github repos that run a hedge fund from your laptop", over a desk of trading screens.
- **Caption:** it describes six roles, does not name the repositories, and says "comment 'GIT' and i'll send you the
  list". The names go out by direct message, so they cannot be recovered from the media.
- **Roles and the most likely repositories** (inference, matching Codex's `docs/TOOLS_FROM_REELS.md` on
  `codex/forward-lane-completion`):

| Role | Most likely repository |
|---|---|
| Candle foundation model | Kronos |
| scikit-learn portfolio optimizer | skfolio |
| Rust engine | NautilusTrader |
| Market-making bots on 140+ exchanges | Hummingbot |
| Crypto bot with ML retraining | Freqtrade / FreqAI |
| Natural-language research workspace | Vibe-Trading is the closest fit |

- **The caption's one engineering claim worth keeping:** "the ai in these repos never sends orders. it forecasts, the
  optimizer sizes, the engine executes."
