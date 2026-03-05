import json
import os
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table

from scout import load_queue


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
KARMA_FILE = os.path.join(DATA_DIR, "karma.json")

console = Console()


def load_karma():
    if os.path.exists(KARMA_FILE):
        with open(KARMA_FILE) as f:
            return json.load(f)
    return {"snapshots": [], "items": {}}


def save_karma(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(KARMA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def snapshot_karma(reddit_client):
    karma_data = load_karma()
    queue = load_queue()

    # Update account karma
    account_karma = reddit_client.get_my_karma()
    karma_data["snapshots"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **account_karma,
    })

    # Update scores for posted items
    posted = [i for i in queue if i["status"] == "posted" and i.get("reddit_id")]
    for item in posted:
        rid = item["reddit_id"]
        try:
            if item["type"] == "comment":
                score = reddit_client.get_comment_score(rid)
            else:
                score = reddit_client.get_post_score(rid)
            karma_data["items"][item["id"]] = {
                "reddit_id": rid,
                "type": item["type"],
                "subreddit": item["subreddit"],
                "score": score,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as e:
            console.print(f"[red]Error checking {rid}: {e}[/red]")

    save_karma(karma_data)
    return karma_data


def print_report(reddit_client=None):
    if reddit_client:
        karma_data = snapshot_karma(reddit_client)
    else:
        karma_data = load_karma()

    # Account karma
    if karma_data["snapshots"]:
        latest = karma_data["snapshots"][-1]
        console.print(f"\n[bold]Account Karma[/bold]")
        console.print(f"  Comment: {latest.get('comment_karma', '?')}  Link: {latest.get('link_karma', '?')}  Total: {latest.get('total', '?')}")

    # Per-item breakdown
    items = karma_data.get("items", {})
    if not items:
        console.print("\n[yellow]No posted items tracked yet.[/yellow]")
        return

    # Subreddit breakdown
    by_sub = {}
    for item_id, info in items.items():
        sub = info["subreddit"]
        if sub not in by_sub:
            by_sub[sub] = {"comments": 0, "posts": 0, "total_score": 0, "count": 0}
        by_sub[sub][f"{info['type']}s"] += 1
        by_sub[sub]["total_score"] += info.get("score", 0)
        by_sub[sub]["count"] += 1

    table = Table(title="Karma by Subreddit")
    table.add_column("Subreddit")
    table.add_column("Comments", justify="right")
    table.add_column("Posts", justify="right")
    table.add_column("Total Score", justify="right")
    table.add_column("Avg Score", justify="right")

    for sub, data in sorted(by_sub.items()):
        avg = data["total_score"] / data["count"] if data["count"] else 0
        table.add_row(
            f"r/{sub}",
            str(data["comments"]),
            str(data["posts"]),
            str(data["total_score"]),
            f"{avg:.1f}",
        )

    console.print(table)

    # Best/worst
    sorted_items = sorted(items.values(), key=lambda x: x.get("score", 0))
    if sorted_items:
        worst = sorted_items[0]
        best = sorted_items[-1]
        console.print(f"\n[green]Best:[/green] r/{best['subreddit']} ({best['type']}) score={best.get('score', 0)}")
        console.print(f"[red]Worst:[/red] r/{worst['subreddit']} ({worst['type']}) score={worst.get('score', 0)}")


def detect_downvote_trend():
    karma_data = load_karma()
    items = karma_data.get("items", {})
    if not items:
        return False

    recent = sorted(items.values(), key=lambda x: x.get("last_checked", ""))[-5:]
    negative = sum(1 for i in recent if i.get("score", 0) < 0)
    return negative >= 3
