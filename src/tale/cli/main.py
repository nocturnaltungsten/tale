"""Main CLI entry point for tale."""

import asyncio
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from tale.orchestration.coordinator import Coordinator
from tale.storage.database import Database
from tale.storage.schema import create_tasks_table

console = Console()

# Global coordinator instance
_coordinator = None


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


@main.group()
def servers() -> None:
    """Manage MCP servers."""
    pass


@servers.command()
def start() -> None:
    """Start MCP servers."""

    async def _start_servers():
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

            global _coordinator
            if _coordinator is not None:
                console.print(
                    Panel(
                        "[yellow]Servers already running. Use 'tale servers stop' first.[/yellow]",
                        title="Warning",
                    )
                )
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Starting servers...", total=None)

                _coordinator = Coordinator(str(db_path))
                await _coordinator.start()

                progress.update(task, description="Servers started successfully!")

            console.print(
                Panel(
                    "[green]✓[/green] MCP servers started successfully\n"
                    "[dim]You can now submit tasks with 'tale submit \"your task\"'[/dim]",
                    title="Success",
                )
            )

        except Exception as e:
            console.print(
                Panel(f"[red]Error starting servers: {e}[/red]", title="Error")
            )

    asyncio.run(_start_servers())


@servers.command()
def stop() -> None:
    """Stop MCP servers."""

    async def _stop_servers():
        try:
            global _coordinator
            if _coordinator is None:
                console.print(
                    Panel(
                        "[yellow]No servers running.[/yellow]",
                        title="Info",
                    )
                )
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Stopping servers...", total=None)

                await _coordinator.stop()
                _coordinator = None

                progress.update(task, description="Servers stopped successfully!")

            console.print(
                Panel(
                    "[green]✓[/green] MCP servers stopped successfully",
                    title="Success",
                )
            )

        except Exception as e:
            console.print(
                Panel(f"[red]Error stopping servers: {e}[/red]", title="Error")
            )

    asyncio.run(_stop_servers())


@servers.command()
def server_status() -> None:
    """Show server status."""
    global _coordinator
    if _coordinator is None:
        console.print(
            Panel(
                "[dim]No servers running. Use 'tale servers start' to start them.[/dim]",
                title="Server Status",
            )
        )
        return

    try:
        server_status = _coordinator.get_server_status()
        active_tasks = _coordinator.get_active_tasks()

        table = Table(title="MCP Server Status")
        table.add_column("Server", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("PID", style="dim")

        for server_name, status in server_status.items():
            status_text = "✓ Running" if status["running"] else "✗ Stopped"
            pid_text = str(status["pid"]) if status["pid"] else "N/A"
            table.add_row(server_name, status_text, pid_text)

        console.print(table)

        if active_tasks:
            console.print(f"\n[cyan]Active Tasks:[/cyan] {len(active_tasks)}")
            for task in active_tasks[:5]:  # Show first 5 tasks
                duration = f"{task['duration']:.1f}s"
                console.print(
                    f"  • [dim]{task['task_id'][:8]}[/dim] {task['task_text']} ([yellow]{duration}[/yellow])"
                )

            if len(active_tasks) > 5:
                console.print(f"  ... and {len(active_tasks) - 5} more")
        else:
            console.print("\n[dim]No active tasks[/dim]")

    except Exception as e:
        console.print(
            Panel(f"[red]Error getting server status: {e}[/red]", title="Error")
        )


async def submit_task_via_gateway(task_text: str) -> str:
    """Submit a task via the gateway server using proper MCP protocol."""

    global _coordinator
    if not _coordinator:
        raise Exception("Coordinator not started")

    # Create MCP client connection to the already-running gateway server
    # Since the server is already running, we use a simple approach
    # The coordinator will manage the actual server-to-server communication

    # For now, directly create the task in the database
    # The coordinator will handle the execution flow
    task_id = _coordinator.task_store.create_task(task_text)

    return task_id


@main.command()
@click.argument("task_text")
@click.option("--wait", is_flag=True, help="Wait for task completion")
def submit(task_text: str, wait: bool) -> None:
    """Submit a task for execution via MCP servers."""

    async def _submit_task():
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

            global _coordinator
            if _coordinator is None:
                console.print(
                    Panel(
                        "[yellow]Servers not running. Starting them automatically...[/yellow]",
                        title="Info",
                    )
                )
                _coordinator = Coordinator(str(db_path))
                await _coordinator.start()
                # Give servers time to initialize
                await asyncio.sleep(2)

            # Submit task via gateway server (proper MCP flow)
            task_id = await submit_task_via_gateway(task_text)

            console.print(
                Panel(
                    f"[green]✓[/green] Task submitted with ID: [cyan]{task_id[:8]}[/cyan]\n"
                    f"[dim]Task: {task_text}[/dim]",
                    title="Task Submitted",
                )
            )

            # If wait flag is set, monitor execution
            if wait:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                ) as progress:
                    progress.add_task("Executing task...", total=None)

                    # Delegate to coordinator
                    result = await _coordinator.delegate_task(task_id)

                    progress.stop()

                    if result["success"]:
                        console.print(
                            Panel(
                                f"[green]✓[/green] Task completed successfully!\n\n"
                                f"[bold]Result:[/bold]\n{result.get('result', 'Task completed')}",
                                title="Task Complete",
                            )
                        )
                    else:
                        console.print(
                            Panel(
                                f"[red]✗[/red] Task failed\n\n"
                                f"[bold]Error:[/bold]\n{result.get('error', 'Unknown error')}",
                                title="Task Failed",
                            )
                        )
            else:
                # Start task execution in background
                asyncio.create_task(_coordinator.delegate_task(task_id))
                console.print(
                    Panel(
                        f"[green]Task execution started in background[/green]\n"
                        f"Use 'tale task-status {task_id[:8]}' to check progress",
                        title="Background Execution",
                    )
                )

        except Exception as e:
            console.print(
                Panel(f"[red]Error submitting task: {e}[/red]", title="Error")
            )

    asyncio.run(_submit_task())


@main.command("task-status")
@click.argument("task_id")
def task_status(task_id: str) -> None:
    """Get status of a specific task."""
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

        # Find task by partial ID
        db = Database(str(db_path))
        with db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, task_text, status, created_at, updated_at FROM tasks WHERE id LIKE ?",
                (f"{task_id}%",),
            )
            task = cursor.fetchone()

        if not task:
            console.print(
                Panel(
                    f"[red]Task with ID starting with '{task_id}' not found.[/red]",
                    title="Error",
                )
            )
            return

        task_dict = dict(task)

        # Create status display
        status_color = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }.get(task_dict["status"], "white")

        console.print(
            Panel(
                f"[bold]Task ID:[/bold] {task_dict['id'][:8]}...\n"
                f"[bold]Status:[/bold] [{status_color}]{task_dict['status'].upper()}[/{status_color}]\n"
                f"[bold]Created:[/bold] {task_dict['created_at']}\n"
                f"[bold]Updated:[/bold] {task_dict['updated_at'] or 'Never'}\n\n"
                f"[bold]Task:[/bold]\n{task_dict['task_text']}",
                title="Task Status",
            )
        )

    except Exception as e:
        console.print(
            Panel(f"[red]Error getting task status: {e}[/red]", title="Error")
        )


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
