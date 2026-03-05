#!/usr/bin/env python3
import sys
import time
from datetime import datetime, timezone

import yaml
from rich.console import Console

from reddit_client import RedditClient
from scout import scout_all, load_queue, save_queue
from ai_generator import create_client, generate_comment, generate_post
from review_queue import review, show_status
from scheduler import Scheduler
from karma_tracker import print_report, detect_downvote_trend


console = Console()


def load_config():
    with open("config.yaml") as f:
        return yaml.safe_load(f)


def cmd_scout(config):
    console.print("[bold]Scouting posts...[/bold]")
    client = RedditClient(config)
    new_items = scout_all(client, config)
    console.print(f"[green]Found {len(new_items)} new posts to target[/green]")
    show_status()


def cmd_generate(config):
    console.print("[bold]Generating AI content...[/bold]")
    queue = load_queue()
    scouted = [i for i in queue if i["status"] == "scouted"]

    if not scouted:
        console.print("[yellow]No scouted items. Run 'scout' first.[/yellow]")
        return

    ai_client = create_client(config)
    model = config["ai"]["model"]
    reddit_client = RedditClient(config)

    # Build persona lookup
    personas = {}
    for sub in config["targets"]["subreddits"]:
        personas[sub["name"]] = sub.get("comment_persona", "You are a helpful community member.")

    generated = 0
    for item in scouted:
        persona = personas.get(item["subreddit"], "You are a helpful community member.")

        try:
            if item["type"] == "comment":
                existing = reddit_client.get_top_comments(item["target_post_id"], limit=5)
                content = generate_comment(ai_client, model, item, persona, existing)
                item["content"] = content
            elif item["type"] == "post":
                post_persona = next(
                    (s.get("post_persona", persona) for s in config["targets"]["subreddits"]
                     if s["name"] == item["subreddit"]),
                    persona,
                )
                title, body = generate_post(ai_client, model, item["subreddit"], post_persona)
                item["title"] = title
                item["body"] = body

            item["status"] = "generated"
            generated += 1
            save_queue(queue)
            console.print(f"[green]Generated {item['type']} for r/{item['subreddit']}[/green]")
        except Exception as e:
            console.print(f"[red]Error generating for {item['target_post_id']}: {e}[/red]")
    console.print(f"\n[bold green]Generated {generated} items[/bold green]")


def cmd_review():
    review()


def cmd_post(config):
    console.print("[bold]Posting approved items...[/bold]")
    queue = load_queue()

    if not any(i["status"] == "approved" for i in queue):
        console.print("[yellow]No approved items. Run 'review' first.[/yellow]")
        return

    if detect_downvote_trend():
        console.print("[red bold]Downvote trend detected! Consider pausing. Continue? (y/n)[/red bold]")
        if input().strip().lower() != "y":
            return

    reddit_client = RedditClient(config)
    scheduler = Scheduler(config)
    posted = 0

    for item in queue:
        if item["status"] != "approved":
            continue
        while True:
            can, reason, wait = scheduler.can_act()
            if can:
                break
            mins = wait // 60
            secs = wait % 60
            console.print(f"[yellow]Rate limited: {reason}. Waiting {mins}m{secs}s...[/yellow]")
            time.sleep(wait)

        try:
            if item["type"] == "comment":
                rid = reddit_client.post_comment(item["target_post_id"], item["content"])
                item["reddit_id"] = rid
                item["status"] = "posted"
                item["posted_at"] = datetime.now(timezone.utc).isoformat()
                scheduler.record_action("comment", item["id"], item["subreddit"], rid)
                posted += 1
                console.print(f"[green]Posted comment on r/{item['subreddit']}[/green]")

            elif item["type"] == "post":
                rid = reddit_client.create_post(item["subreddit"], item["title"], item["body"])
                item["reddit_id"] = rid
                item["status"] = "posted"
                item["posted_at"] = datetime.now(timezone.utc).isoformat()
                scheduler.record_action("post", item["id"], item["subreddit"], rid)
                posted += 1
                console.print(f"[green]Created post on r/{item['subreddit']}[/green]")

        except Exception as e:
            item["status"] = "failed"
            console.print(f"[red]Failed: {e}[/red]")

        save_queue(queue)  # Save after each item

    console.print(f"\n[bold green]Posted {posted} items[/bold green]")


def cmd_karma(config):
    try:
        reddit_client = RedditClient(config)
        print_report(reddit_client)
    except Exception:
        print_report()


def cmd_run(config):
    console.print("[bold]Running full loop: scout -> generate -> review -> post[/bold]\n")
    cmd_scout(config)
    cmd_generate(config)
    cmd_review()
    cmd_post(config)
    console.print("\n[bold green]Full loop complete![/bold green]")


def cmd_status():
    show_status()


COMMANDS = {
    "scout": cmd_scout,
    "generate": cmd_generate,
    "review": lambda _: cmd_review(),
    "post": cmd_post,
    "karma": cmd_karma,
    "run": cmd_run,
    "status": lambda _: cmd_status(),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        console.print("[bold]Reddit Creator Bot[/bold]\n")
        console.print("Commands:")
        console.print("  scout     - Discover posts to target")
        console.print("  generate  - Generate AI content for scouted posts")
        console.print("  review    - Review & approve generated content")
        console.print("  post      - Post approved content to Reddit")
        console.print("  karma     - Karma tracking report")
        console.print("  run       - Full loop (scout->generate->review->post)")
        console.print("  status    - Show queue status")
        console.print(f"\nUsage: python {sys.argv[0]} <command>")
        sys.exit(1)

    config = load_config()
    COMMANDS[sys.argv[1]](config)


if __name__ == "__main__":
    main()
