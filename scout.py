import json
import os
import uuid
from datetime import datetime, timezone


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
QUEUE_FILE = os.path.join(DATA_DIR, "queue.json")


def load_queue():
    if os.path.exists(QUEUE_FILE):
        with open(QUEUE_FILE) as f:
            return json.load(f)
    return []


def save_queue(queue):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(QUEUE_FILE, "w") as f:
        json.dump(queue, f, indent=2)


def scout_all(reddit_client, config):
    queue = load_queue()
    existing_post_ids = {item["target_post_id"] for item in queue if item.get("target_post_id")}
    new_items = []

    for sub_config in config["targets"]["subreddits"]:
        sub_name = sub_config["name"]
        sorts = sub_config.get("sort", ["hot"])
        limit = sub_config.get("limit", 25)

        for sort in sorts:
            posts = reddit_client.get_posts(sub_name, sort=sort, limit=limit)
            filtered = filter_posts(posts, sub_config, existing_post_ids)
            ranked = rank_posts(filtered)

            for post in ranked:
                item = {
                    "id": str(uuid.uuid4()),
                    "type": "comment",
                    "subreddit": sub_name,
                    "target_post_id": post.id,
                    "target_post_title": post.title,
                    "target_post_body": post.selftext[:500] if post.selftext else "",
                    "target_post_url": f"https://reddit.com{post.permalink}",
                    "content": None,
                    "title": None,
                    "body": None,
                    "status": "scouted",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "posted_at": None,
                    "reddit_id": None,
                    "score": None,
                }
                new_items.append(item)
                existing_post_ids.add(post.id)

    queue.extend(new_items)
    save_queue(queue)
    return new_items


def filter_posts(posts, sub_config, existing_post_ids):
    keywords = [k.lower() for k in sub_config.get("keywords", [])]
    min_score = sub_config.get("min_score", 1)
    max_age_hours = sub_config.get("max_age_hours", 24)
    now = datetime.now(timezone.utc).timestamp()

    filtered = []
    for post in posts:
        if post.id in existing_post_ids:
            continue

        age_hours = (now - post.created_utc) / 3600
        if age_hours > max_age_hours:
            continue

        if post.score < min_score:
            continue

        if post.stickied or post.locked:
            continue

        if keywords:
            text = (post.title + " " + (post.selftext or "")).lower()
            if not any(kw in text for kw in keywords):
                continue

        filtered.append(post)

    return filtered


def rank_posts(posts):
    def score(post):
        nc = post.num_comments
        # Sweet spot: 5-50 comments (visible but not buried)
        if 5 <= nc <= 50:
            comment_score = 10
        elif nc < 5:
            comment_score = nc * 2
        else:
            comment_score = max(0, 10 - (nc - 50) // 10)

        # Higher upvoted posts = more visibility
        upvote_score = min(post.score / 10, 10)

        return comment_score + upvote_score

    posts.sort(key=score, reverse=True)
    return posts
