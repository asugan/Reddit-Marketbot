import json
import os
import random
import time
from datetime import datetime, timezone


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")


class Scheduler:
    def __init__(self, config):
        self.limits = config.get("rate_limits", {})
        self.min_delay = self.limits.get("min_delay_seconds", 120)
        self.max_delay = self.limits.get("max_delay_seconds", 600)
        self.max_comments_per_hour = self.limits.get("max_comments_per_hour", 3)
        self.max_posts_per_day = self.limits.get("max_posts_per_day", 1)
        self.max_actions_per_day = self.limits.get("max_actions_per_day", 10)
        self.active_hours = self.limits.get("active_hours", [9, 23])

    def load_history(self):
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE) as f:
                return json.load(f)
        return []

    def save_history(self, history):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)

    def can_act(self):
        now = datetime.now(timezone.utc)
        local_hour = datetime.now().hour

        start_h, end_h = self.active_hours
        if not (start_h <= local_hour < end_h):
            return False, f"Outside active hours ({start_h}:00-{end_h}:00), current: {local_hour}:00"

        history = self.load_history()

        # Daily limit
        today_str = now.strftime("%Y-%m-%d")
        today_actions = [h for h in history if h["timestamp"].startswith(today_str)]
        if len(today_actions) >= self.max_actions_per_day:
            return False, f"Daily limit reached ({self.max_actions_per_day})"

        # Hourly comment limit
        one_hour_ago = now.timestamp() - 3600
        recent_comments = [
            h for h in history
            if h["type"] == "comment" and
            datetime.fromisoformat(h["timestamp"]).timestamp() > one_hour_ago
        ]
        if len(recent_comments) >= self.max_comments_per_hour:
            return False, f"Hourly comment limit reached ({self.max_comments_per_hour})"

        # Daily post limit
        today_posts = [h for h in today_actions if h["type"] == "post"]
        if len(today_posts) >= self.max_posts_per_day:
            return False, f"Daily post limit reached ({self.max_posts_per_day})"

        # Min delay since last action
        if history:
            last_ts = max(
                datetime.fromisoformat(h["timestamp"]).timestamp()
                for h in history
            )
            elapsed = now.timestamp() - last_ts
            if elapsed < self.min_delay:
                wait = int(self.min_delay - elapsed)
                return False, f"Too soon since last action (wait {wait}s)"

        return True, "OK"

    def wait_for_next_slot(self):
        can, reason = self.can_act()
        if can:
            # Random delay with Gaussian distribution
            mean = (self.min_delay + self.max_delay) / 2
            std = (self.max_delay - self.min_delay) / 4
            delay = max(self.min_delay, min(self.max_delay, random.gauss(mean, std)))
            delay = int(delay)
            return delay
        return None

    def record_action(self, action_type, item_id, subreddit, reddit_id=None):
        history = self.load_history()
        history.append({
            "type": action_type,
            "item_id": item_id,
            "subreddit": subreddit,
            "reddit_id": reddit_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.save_history(history)
