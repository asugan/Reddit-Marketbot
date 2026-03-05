# Reddit Creator Bot

CLI automation tool that scouts target subreddit posts, generates AI-powered comments and original posts, queues them for human review, and publishes with rate limiting.

## How It Works

```
scout → generate → review → post → karma
```

1. **Scout** - Scans target subreddits, finds suitable posts
2. **Generate** - Produces comment/post content via AI
3. **Review** - Interactive CLI to approve/reject/edit content
4. **Post** - Publishes approved content with rate limiting
5. **Karma** - Tracks score performance of posted content

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Reddit Authentication

Two options in `config.yaml`:

**Option 1: Session cookie (recommended for Google SSO users)**
1. Log into Reddit in your browser
2. Open DevTools (F12) > Application > Cookies > `reddit.com`
3. Copy the `reddit_session` cookie value into `config.yaml`

```yaml
reddit:
  reddit_session: "eyJhbGciOi..."
```

**Option 2: Username/password**
```yaml
reddit:
  username: "your_username"
  password: "your_password"
```

### AI Endpoint

OpenAI-compatible proxy must be running at `http://localhost:8317/v1`. Model: `gemini-3-flash-preview`.

## Usage

```bash
source venv/bin/activate

python3 main.py scout      # Discover targetable posts
python3 main.py generate   # Generate AI content
python3 main.py review     # Approval queue (approve/reject/edit/skip)
python3 main.py post       # Publish approved items
python3 main.py karma      # Karma report
python3 main.py run        # Full loop (scout->generate->review->post)
python3 main.py status     # Queue status
```

## Config

Configured via `config.yaml`:

| Section | Description |
|---|---|
| `reddit` | Session cookie or username/password, user agent |
| `ai` | Endpoint URL, model, timeout |
| `targets.subreddits` | Target subreddits, keyword filters, personas |
| `rate_limits` | Delays, hourly/daily limits, active hours |

### Subreddit Targeting

```yaml
targets:
  subreddits:
    - name: "python"
      sort: ["new", "hot", "rising"]
      keywords: ["beginner", "help", "question"]
      limit: 25
      min_score: 1
      max_age_hours: 24
      comment_persona: "You are an experienced Python developer..."
```

## Project Structure

```
main.py              # CLI entry point
reddit_client.py     # Reddit client via cookie/session auth (posts/comments/karma)
scout.py             # Post discovery + filtering + ranking
ai_generator.py      # Content generation via OpenAI-compat endpoint
review_queue.py      # Rich CLI approval queue
scheduler.py         # Rate limiting, random delays, anti-detection
karma_tracker.py     # Karma tracking, performance reports
config.yaml          # Configuration (gitignored)
data/                # Runtime data (gitignored)
  queue.json         # Pending items
  history.json       # Post history
  karma.json         # Karma snapshots
```

## Anti-Detection

- Gaussian-distributed random delays (2-10 min)
- Active hours restriction (default 09:00-23:00)
- Comment length variation (short/medium/long)
- Duplicate comment prevention per post
- Daily/hourly action limits
- Downvote trend detection with warnings
- Mandatory human review step

## Data Flow

```
scout → queue.json (scouted)
  → generate → queue.json (generated + content)
    → review → queue.json (approved/rejected)
      → post → queue.json (posted) + history.json
        → karma → karma.json (score snapshots)
```

## Tech Stack

- **Python 3** + **requests** (Reddit via old.reddit.com JSON API)
- **openai** SDK (routed to OpenAI-compatible endpoint)
- **rich** (CLI UI)
- **pyyaml** (config)

No Reddit API key required — authenticates via session cookie or username/password.
