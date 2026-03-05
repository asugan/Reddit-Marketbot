import os
import subprocess
import tempfile

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from scout import load_queue, save_queue


console = Console()


def review(status_filter="generated"):
    queue = load_queue()
    items = [i for i in queue if i["status"] == status_filter]

    if not items:
        console.print(f"[yellow]No items with status '{status_filter}' to review.[/yellow]")
        return

    console.print(f"\n[bold]Found {len(items)} items to review[/bold]\n")

    for idx, item in enumerate(items):
        console.print(f"\n[dim]--- Item {idx + 1}/{len(items)} ---[/dim]")
        display_item(item)

        action = Prompt.ask(
            "\n[bold]Action[/bold]",
            choices=["a", "r", "e", "s", "q"],
            default="s",
        )

        if action == "a":
            item["status"] = "approved"
            console.print("[green]Approved[/green]")
        elif action == "r":
            item["status"] = "rejected"
            console.print("[red]Rejected[/red]")
        elif action == "e":
            item = edit_item(item)
            item["status"] = "approved"
            console.print("[green]Edited & Approved[/green]")
        elif action == "q":
            console.print("[yellow]Quitting review[/yellow]")
            save_queue(queue)
            return
        # 's' = skip, do nothing

    save_queue(queue)
    console.print("\n[bold green]Review complete![/bold green]")


def display_item(item):
    if item["type"] == "comment":
        console.print(Panel(
            f"[bold]r/{item['subreddit']}[/bold] - {item['target_post_title']}\n"
            f"[dim]{item.get('target_post_url', '')}[/dim]",
            title="Target Post",
            border_style="blue",
        ))
        console.print(Panel(
            item.get("content") or "(no content generated)",
            title="Generated Comment",
            border_style="green",
        ))
    elif item["type"] == "post":
        console.print(Panel(
            f"[bold]r/{item['subreddit']}[/bold]",
            title="Target Subreddit",
            border_style="blue",
        ))
        console.print(Panel(
            f"[bold]{item.get('title', '')}[/bold]\n\n{item.get('body', '')}",
            title="Generated Post",
            border_style="green",
        ))

    console.print("[dim][a]pprove  [r]eject  [e]dit  [s]kip  [q]uit[/dim]")


def edit_item(item):
    editor = os.environ.get("EDITOR", "nano")

    if item["type"] == "comment":
        content = item.get("content", "")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        subprocess.call([editor, tmp_path])
        with open(tmp_path) as f:
            item["content"] = f.read().strip()
        os.unlink(tmp_path)
    elif item["type"] == "post":
        content = f"TITLE: {item.get('title', '')}\n\nBODY:\n{item.get('body', '')}"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            tmp_path = f.name
        subprocess.call([editor, tmp_path])
        with open(tmp_path) as f:
            text = f.read().strip()
        os.unlink(tmp_path)

        if "TITLE:" in text and "BODY:" in text:
            parts = text.split("BODY:", 1)
            item["title"] = parts[0].replace("TITLE:", "").strip()
            item["body"] = parts[1].strip()
        else:
            lines = text.split("\n", 1)
            item["title"] = lines[0].strip()
            item["body"] = lines[1].strip() if len(lines) > 1 else ""

    return item


def show_status():
    queue = load_queue()
    if not queue:
        console.print("[yellow]Queue is empty.[/yellow]")
        return

    counts = {}
    for item in queue:
        s = item["status"]
        counts[s] = counts.get(s, 0) + 1

    table = Table(title="Queue Status")
    table.add_column("Status", style="bold")
    table.add_column("Count", justify="right")

    for status in ["scouted", "generated", "approved", "rejected", "posted", "failed"]:
        if status in counts:
            color = {
                "scouted": "blue",
                "generated": "yellow",
                "approved": "green",
                "rejected": "red",
                "posted": "cyan",
                "failed": "red",
            }.get(status, "white")
            table.add_row(f"[{color}]{status}[/{color}]", str(counts[status]))

    console.print(table)
