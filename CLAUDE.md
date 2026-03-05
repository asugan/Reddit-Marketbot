# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reddit marketing automation bot. Scouts subreddit posts, generates AI comments/posts via OpenAI-compatible endpoint, queues them for human review, then posts with rate limiting.

## Commands

```bash
source venv/bin/activate
python3 main.py scout      # Discover targetable posts
python3 main.py generate   # Generate AI content for scouted items
python3 main.py review     # Interactive approve/reject/edit queue
python3 main.py post       # Post approved items with rate limiting
python3 main.py karma      # Karma performance report
python3 main.py run        # Full pipeline: scout->generate->review->post
python3 main.py status     # Show queue counts by status
```

## Architecture

**Data flow:** `scout → generate → review → post → karma`, all mediated through `data/queue.json` with status transitions: `scouted → generated → approved/rejected → posted/failed`.

- **main.py** — CLI dispatcher, orchestrates all commands by calling into other modules
- **reddit_client.py** — PRAW wrapper (`RedditClient` class). All Reddit API calls go through here
- **scout.py** — Post discovery. Owns `data/queue.json` (load_queue/save_queue are used by other modules too). Filters by keywords, age, score, stickied/locked. Ranks by comment count sweet spot (5-50)
- **ai_generator.py** — Uses `openai` SDK pointed at localhost:8317 proxy. Generates comments with randomized length/temperature and anti-AI-detection rules
- **review_queue.py** — Rich-based interactive CLI. Opens `$EDITOR` for edits
- **scheduler.py** — Rate limiting via `data/history.json`. Enforces active hours, daily/hourly caps, min delay between actions. Uses Gaussian-distributed random delays
- **karma_tracker.py** — Tracks scores in `data/karma.json`, detects downvote trends

**Shared state:** All modules read/write JSON files in `data/` directory. `scout.py` owns `load_queue()`/`save_queue()` which other modules import.

## Key Config

`config.yaml` (gitignored) has four sections: `reddit` (API creds), `ai` (endpoint config), `targets.subreddits` (per-sub settings with personas), `rate_limits`.

AI endpoint: `http://localhost:8317/v1` with model `gemini-3-flash-preview` (OpenAI-compatible proxy from `../slideshow-creator`).

## Dependencies

Always use venv — never install with `--break-system-packages`. Dependencies: praw, openai, pyyaml, rich.
