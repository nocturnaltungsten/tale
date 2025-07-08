"""Main CLI entry point for tale."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from tale.storage.database import Database
from tale.storage.schema import create_tasks_table
from tale.storage.task_store import TaskStore

console = Console()


def get_project_root() -> Path:
    """Get the project root directory."""
    # Look for tale.db or other project markers
    current = Path.cwd()
    while current != current.parent:
        if (current / "tale.db").exists() or (current / ".tale").exists():
            return current
        current = current.parent
    return Path.cwd()


def ensure_tale_directory() -> Path:
    """Ensure .tale directory exists in project root."""
    project_root = get_project_root()
    tale_dir = project_root / ".tale"
    tale_dir.mkdir(exist_ok=True)
    return tale_dir


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version information")
@click.pass_context
def main(ctx: click.Context, version: bool) -> None:
    """tale - Lean Autonomous Agent Architecture

    An experimental AI agent system with dual-model architecture,
    MCP-based communication, and token budget learning.
    """
    if version:
        click.echo("tale 0.1.0")
        return

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option("--force", is_flag=True, help="Force reinitialize existing project")
def init(force: bool) -> None:
    """Initialize a new tale project in the current directory."""
    try:
        project_root = Path.cwd()
        tale_dir = project_root / ".tale"
        db_path = project_root / "tale.db"

        # Check if already initialized
        if tale_dir.exists() and not force:
            console.print(
                Panel(
                    "[yellow]Project already initialized. Use --force to reinitialize.[/yellow]",
                    title="Warning",
                )
            )
            return

        # Create .tale directory
        tale_dir.mkdir(exist_ok=True)

        # Initialize database
        db = Database(str(db_path))
        with db.get_connection() as conn:
            conn.execute(create_tasks_table())
            conn.commit()

        # Create basic config
        config_path = tale_dir / "config.json"
        if not config_path.exists():
            config_content = {
                "models": {"small": "qwen2.5:7b", "large": "qwen2.5:14b"},
                "database_path": "tale.db",
                "checkpoint_dir": "checkpoints",
            }
            import json

            with open(config_path, "w") as f:
                json.dump(config_content, f, indent=2)

        console.print(
            Panel(
                f"[green]✓[/green] Initialized tale project in {project_root}\n"
                f"[green]✓[/green] Created database: {db_path}\n"
                f"[green]✓[/green] Created config: {config_path}",
                title="Success",
            )
        )

    except Exception as e:
        console.print(
            Panel(f"[red]Error initializing project: {e}[/red]", title="Error")
        )
        sys.exit(1)


@main.command()
def status() -> None:
    """Show project status and basic information."""
    try:
        project_root = get_project_root()
        tale_dir = project_root / ".tale"
        db_path = project_root / "tale.db"

        # Check if initialized
        if not tale_dir.exists():
            console.print(
                Panel(
                    "[red]No tale project found. Run 'tale init' first.[/red]",
                    title="Error",
                )
            )
            return

        # Create status table
        table = Table(title="Tale Project Status")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        # Check database
        if db_path.exists():
            try:
                db = Database(str(db_path))
                with db.get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM tasks")
                    task_count = cursor.fetchone()[0]
                table.add_row("Database", "✓ Ready", f"{task_count} tasks")
            except Exception as e:
                table.add_row("Database", "✗ Error", str(e))
        else:
            table.add_row("Database", "✗ Missing", "Run 'tale init'")

        # Check config
        config_path = tale_dir / "config.json"
        if config_path.exists():
            table.add_row("Config", "✓ Found", str(config_path))
        else:
            table.add_row("Config", "✗ Missing", "Run 'tale init'")

        # Check models (basic check)
        try:
            import subprocess

            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                models = [
                    line.split()[0]
                    for line in result.stdout.split("\n")[1:]
                    if line.strip()
                ]
                table.add_row("Ollama", "✓ Running", f"{len(models)} models available")
            else:
                table.add_row("Ollama", "✗ Error", "Failed to list models")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            table.add_row("Ollama", "✗ Not Found", "Install Ollama")
        except Exception as e:
            table.add_row("Ollama", "✗ Error", str(e))

        console.print(table)

        # Show basic project info
        console.print(f"\n[dim]Project root: {project_root}[/dim]")

    except Exception as e:
        console.print(Panel(f"[red]Error checking status: {e}[/red]", title="Error"))


@main.command()
def version() -> None:
    """Show detailed version information."""
    console.print(
        Panel(
            "[bold]tale[/bold] 0.1.0\n\n"
            "[dim]Lean Autonomous Agent Architecture[/dim]\n"
            "[dim]An experimental AI agent system[/dim]\n\n"
            "[yellow]Components:[/yellow]\n"
            "• Dual-model architecture (UX + Task models)\n"
            "• MCP-based server communication\n"
            "• SQLite storage with git checkpointing\n"
            "• Token budget learning\n\n"
            "[dim]Status: Alpha - Experimental[/dim]",
            title="Version Info",
        )
    )


@main.command()
@click.argument("task_text")
def submit(task_text: str) -> None:
    """Submit a task for execution (basic implementation)."""
    try:
        project_root = get_project_root()
        db_path = project_root / "tale.db"

        if not db_path.exists():
            console.print(
                Panel(
                    "[red]No tale project found. Run 'tale init' first.[/red]",
                    title="Error",
                )
            )
            return

        # For now, just store in database
        db = Database(str(db_path))
        task_store = TaskStore(db)
        task_id = task_store.create_task(task_text)

        console.print(
            Panel(
                f"[green]✓[/green] Task submitted with ID: [cyan]{task_id}[/cyan]\n"
                f"[dim]Task: {task_text}[/dim]\n\n"
                f"[yellow]Note:[/yellow] This is a basic implementation.\n"
                f"Full execution requires MCP servers (coming in Phase 2).",
                title="Task Submitted",
            )
        )

    except Exception as e:
        console.print(Panel(f"[red]Error submitting task: {e}[/red]", title="Error"))


@main.command()
def list() -> None:
    """List all tasks in the project."""
    try:
        project_root = get_project_root()
        db_path = project_root / "tale.db"

        if not db_path.exists():
            console.print(
                Panel(
                    "[red]No tale project found. Run 'tale init' first.[/red]",
                    title="Error",
                )
            )
            return

        db = Database(str(db_path))
        with db.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id, task_text, status, created_at
                FROM tasks
                ORDER BY created_at DESC
            """
            )
            tasks = cursor.fetchall()

        if not tasks:
            console.print(
                Panel(
                    "[dim]No tasks found. Submit a task with 'tale submit \"your task\"'[/dim]",
                    title="Tasks",
                )
            )
            return

        table = Table(title="Tasks")
        table.add_column("ID", style="cyan", width=8)
        table.add_column("Status", style="green", width=10)
        table.add_column("Task", style="white")
        table.add_column("Created", style="dim", width=16)

        for task in tasks:
            # Truncate ID for display
            short_id = task[0][:8] if task[0] else "unknown"
            # Truncate task text if too long
            task_text = task[1][:60] + "..." if len(task[1]) > 60 else task[1]
            # Format timestamp
            created = task[3][:16] if task[3] else "unknown"

            table.add_row(short_id, task[2], task_text, created)

        console.print(table)

    except Exception as e:
        console.print(Panel(f"[red]Error listing tasks: {e}[/red]", title="Error"))


if __name__ == "__main__":
    main()
