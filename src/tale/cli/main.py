"""Main CLI entry point for tale."""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from tale.mcp.http_client import HTTPMCPClient
from tale.orchestration.coordinator_http import HTTPCoordinator
from tale.storage.database import Database
from tale.storage.schema import create_tasks_table

console = Console()

# Global coordinator instance
_coordinator = None


def format_duration(created_at: str, updated_at: str = None) -> str:
    """Format duration from creation time."""
    try:
        # Parse the timestamp
        start_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        end_time = datetime.now()

        if updated_at:
            try:
                end_time = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        duration = end_time - start_time

        # Format duration nicely
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"
    except (ValueError, TypeError):
        return "unknown"


def format_age(timestamp: str) -> str:
    """Format age since timestamp."""
    try:
        time_obj = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        now = datetime.now()
        age = now - time_obj

        total_seconds = int(age.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s ago"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours}h ago"
        else:
            days = total_seconds // 86400
            return f"{days}d ago"
    except (ValueError, TypeError):
        return "unknown"


def create_task_table(tasks: list) -> Table:
    """Create a rich table for task display."""
    table = Table(title="Tasks")
    table.add_column("ID", style="cyan", width=8)
    table.add_column("Status", style="green", width=12)
    table.add_column("Task", style="white")
    table.add_column("Age", style="dim", width=10)
    table.add_column("Duration", style="dim", width=10)

    for task in tasks:
        # Truncate ID for display
        short_id = task[0][:8] if task[0] else "unknown"

        # Color-code status
        status = task[2] or "unknown"
        status_colors = {
            "pending": "yellow",
            "running": "blue",
            "completed": "green",
            "failed": "red",
        }
        status_color = status_colors.get(status, "white")
        status_display = f"[{status_color}]{status.upper()}[/{status_color}]"

        # Truncate task text if too long
        task_text = task[1][:60] + "..." if len(task[1]) > 60 else task[1]

        # Format age and duration
        age = format_age(task[3]) if task[3] else "unknown"
        duration = format_duration(task[3], task[4]) if task[3] else "unknown"

        table.add_row(short_id, status_display, task_text, age, duration)

    return table


def run_async(coro):
    """Run an async coroutine, handling cases where event loop may already exist."""
    try:
        # Try to get the running loop
        asyncio.get_running_loop()
    except RuntimeError:
        # No loop running, use asyncio.run()
        return asyncio.run(coro)
    else:
        # Loop already running (e.g., in pytest), create a task
        import concurrent.futures

        # Create a new event loop in a thread to avoid conflicts
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


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
def serve() -> None:
    """Start HTTP MCP servers (alias for 'servers start')."""

    async def _serve():
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
                task = progress.add_task("Starting HTTP servers...", total=None)

                _coordinator = HTTPCoordinator(str(db_path))
                await _coordinator.start()
                progress.update(task, description="HTTP servers started successfully!")

            console.print(
                Panel(
                    "[green]✓[/green] HTTP MCP servers started successfully\n"
                    "[green]✓[/green] Gateway server running on port 8080\n"
                    "[green]✓[/green] Execution server running on port 8081\n"
                    "[green]✓[/green] UX agent server running on port 8082\n"
                    "[dim]You can now submit tasks with 'tale submit \"your task\"'[/dim]\n"
                    "[dim]Or start a conversation with 'tale chat'[/dim]\n\n"
                    "[cyan]Press Ctrl+C to stop servers[/cyan]",
                    title="Success",
                )
            )

            # Keep servers running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                console.print("\n[dim]Shutting down servers...[/dim]")
                await _coordinator.stop()
                _coordinator = None
                console.print("[green]✓[/green] Servers stopped successfully")

        except Exception as e:
            console.print(
                Panel(f"[red]Error starting servers: {e}[/red]", title="Error")
            )

    run_async(_serve())


@main.group()
def servers() -> None:
    """Manage MCP servers."""
    pass


@servers.command()
def start() -> None:
    """Start HTTP MCP servers."""

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
                task = progress.add_task("Starting HTTP servers...", total=None)

                _coordinator = HTTPCoordinator(str(db_path))
                await _coordinator.start()
                progress.update(task, description="HTTP servers started successfully!")

            console.print(
                Panel(
                    "[green]✓[/green] HTTP MCP servers started successfully\n"
                    "[green]✓[/green] Gateway server running on port 8080\n"
                    "[green]✓[/green] Execution server running on port 8081\n"
                    "[green]✓[/green] UX agent server running on port 8082\n"
                    "[dim]You can now submit tasks with 'tale submit \"your task\"'[/dim]\n"
                    "[dim]Or start a conversation with 'tale chat'[/dim]\n\n"
                    "[cyan]Press Ctrl+C to stop servers[/cyan]",
                    title="Success",
                )
            )

            # Keep servers running
            try:
                await asyncio.Event().wait()
            except KeyboardInterrupt:
                console.print("\n[dim]Shutting down servers...[/dim]")
                await _coordinator.stop()
                _coordinator = None
                console.print("[green]✓[/green] Servers stopped successfully")

        except Exception as e:
            console.print(
                Panel(f"[red]Error starting servers: {e}[/red]", title="Error")
            )

    run_async(_start_servers())


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

    run_async(_stop_servers())


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
    """Submit a task via the gateway server using HTTP MCP protocol."""

    global _coordinator
    if not _coordinator:
        raise Exception("HTTP coordinator not started")

    # Use the HTTP coordinator's submit_task method
    task_id = await _coordinator.submit_task(task_text)
    return task_id


@main.command()
@click.argument("task_text")
@click.option("--wait", is_flag=True, help="Wait for task completion")
def submit(task_text: str, wait: bool) -> None:
    """Submit a task for execution via HTTP MCP servers."""

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
                        "[yellow]HTTP servers not running. Starting them automatically...[/yellow]",
                        title="Info",
                    )
                )
                _coordinator = HTTPCoordinator(str(db_path))
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

                    # Delegate to HTTP coordinator
                    result = await _coordinator.execute_task(task_id)

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
                asyncio.create_task(_coordinator.execute_task(task_id))
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

    run_async(_submit_task())


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
            # First try exact match
            cursor = conn.execute(
                "SELECT id, task_text, status, created_at, updated_at FROM tasks WHERE id = ?",
                (task_id,),
            )
            task = cursor.fetchone()

            if task:
                task_dict = dict(task)
            else:
                # Try partial match
                cursor = conn.execute(
                    "SELECT id, task_text, status, created_at, updated_at FROM tasks WHERE id LIKE ?",
                    (f"{task_id}%",),
                )
                matching_tasks = cursor.fetchall()

                if not matching_tasks:
                    console.print(
                        Panel(
                            f"[red]Task with ID starting with '{task_id}' not found.[/red]",
                            title="Error",
                        )
                    )
                    return
                elif len(matching_tasks) == 1:
                    task_dict = dict(matching_tasks[0])
                else:
                    # Multiple matches - show disambiguation menu
                    console.print(
                        Panel(
                            f"[yellow]Multiple tasks found starting with '{task_id}':[/yellow]",
                            title="Disambiguation Required",
                        )
                    )

                    for i, match in enumerate(matching_tasks, 1):
                        match_dict = dict(match)
                        status_color = {
                            "pending": "yellow",
                            "running": "blue",
                            "completed": "green",
                            "failed": "red",
                        }.get(match_dict["status"], "white")

                        console.print(
                            f"[bold]{i}.[/bold] {match_dict['id'][:12]}... "
                            f"[{status_color}]{match_dict['status'].upper()}[/{status_color}] "
                            f"- {match_dict['task_text'][:60]}{'...' if len(match_dict['task_text']) > 60 else ''}"
                        )

                    console.print(
                        "\n[cyan]Please use a more specific task ID to select the desired task.[/cyan]"
                    )
                    return

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
@click.option("--watch", is_flag=True, help="Watch for live updates")
def tasks(watch: bool) -> None:
    """Show all tasks with improved status visibility."""
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

        def get_tasks():
            """Get tasks from database."""
            db = Database(str(db_path))
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, task_text, status, created_at, updated_at
                    FROM tasks
                    ORDER BY created_at DESC
                """
                )
                return cursor.fetchall()

        if watch:
            # Live updating display
            def generate_display():
                tasks = get_tasks()
                if not tasks:
                    return Panel(
                        "[dim]No tasks found. Submit a task with 'tale submit \"your task\"'[/dim]",
                        title="Tasks",
                    )
                return create_task_table(tasks)

            with Live(generate_display(), refresh_per_second=2) as live:
                try:
                    while True:
                        time.sleep(0.5)
                        live.update(generate_display())
                except KeyboardInterrupt:
                    console.print("\n[dim]Stopped watching tasks.[/dim]")
        else:
            # Single display
            tasks = get_tasks()
            if not tasks:
                console.print(
                    Panel(
                        "[dim]No tasks found. Submit a task with 'tale submit \"your task\"'[/dim]",
                        title="Tasks",
                    )
                )
                return

            table = create_task_table(tasks)
            console.print(table)

    except Exception as e:
        console.print(Panel(f"[red]Error listing tasks: {e}[/red]", title="Error"))


@main.command()
def list() -> None:
    """List all tasks in the project (alias for tasks)."""
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
                SELECT id, task_text, status, created_at, updated_at
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

        table = create_task_table(tasks)
        console.print(table)

    except Exception as e:
        console.print(Panel(f"[red]Error listing tasks: {e}[/red]", title="Error"))


async def _handle_chat_command(command: str, console, project_root):
    """Handle in-chat commands like /tasks, /status, /help, /clear."""

    parts = command.strip().split()
    cmd = parts[0].lower()

    if cmd == "/help":
        console.print(
            Panel(
                """[bold]Available Chat Commands:[/bold]

/help       - Show this help message
/tasks      - List all tasks
/status <id> - Show task status (partial ID supported)
/clear      - Clear conversation history
/exit       - Exit chat session

[dim]You can also type naturally and tasks will be detected automatically.[/dim]""",
                title="Chat Help",
            )
        )

    elif cmd == "/tasks":
        # Reuse the existing task listing logic
        try:
            db_path = project_root / "tale.db"
            if not db_path.exists():
                console.print(Panel("[red]No tale project found.[/red]", title="Error"))
                return

            from tale.storage.database import Database

            db = Database(str(db_path))
            with db.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, task_text, status, created_at
                    FROM tasks
                    ORDER BY created_at DESC
                    LIMIT 10
                    """
                )
                tasks = cursor.fetchall()

            if not tasks:
                console.print(Panel("[dim]No tasks found.[/dim]", title="Tasks"))
                return

            # Create a simple table display
            from rich.table import Table

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="cyan", width=12)
            table.add_column("Task", style="white", width=40)
            table.add_column("Status", style="green", width=12)
            table.add_column("Created", style="dim", width=20)

            for task in tasks:
                task_dict = dict(task)
                task_id = task_dict["id"][:8] + "..."
                task_text = task_dict["task_text"]
                if len(task_text) > 37:
                    task_text = task_text[:34] + "..."
                status = task_dict["status"]
                created = task_dict["created_at"][:16]  # Just date and time

                table.add_row(task_id, task_text, status, created)

            console.print(Panel(table, title="Recent Tasks"))

        except Exception as e:
            console.print(Panel(f"[red]Error: {e}[/red]", title="Error"))

    elif cmd == "/status":
        if len(parts) < 2:
            console.print(Panel("[red]Usage: /status <task_id>[/red]", title="Error"))
            return

        task_id = parts[1]

        # Reuse existing task status logic
        try:
            db_path = project_root / "tale.db"
            if not db_path.exists():
                console.print(Panel("[red]No tale project found.[/red]", title="Error"))
                return

            from tale.storage.database import Database

            db = Database(str(db_path))
            with db.get_connection() as conn:
                # First try exact match
                cursor = conn.execute(
                    "SELECT id, task_text, status, created_at, updated_at FROM tasks WHERE id = ?",
                    (task_id,),
                )
                task = cursor.fetchone()

                if task:
                    task_dict = dict(task)
                else:
                    # Try partial match
                    cursor = conn.execute(
                        "SELECT id, task_text, status, created_at, updated_at FROM tasks WHERE id LIKE ?",
                        (f"{task_id}%",),
                    )
                    matching_tasks = cursor.fetchall()

                    if not matching_tasks:
                        console.print(
                            Panel(
                                f"[red]Task not found: {task_id}[/red]", title="Error"
                            )
                        )
                        return
                    elif len(matching_tasks) > 1:
                        console.print(
                            Panel(
                                f"[red]Multiple tasks match '{task_id}'. Please be more specific.[/red]",
                                title="Error",
                            )
                        )
                        return
                    else:
                        task_dict = dict(matching_tasks[0])

                # Display task info
                console.print(
                    Panel(
                        f"[bold]Task ID:[/bold] {task_dict['id']}\n"
                        f"[bold]Status:[/bold] {task_dict['status']}\n"
                        f"[bold]Task:[/bold] {task_dict['task_text']}\n"
                        f"[bold]Created:[/bold] {task_dict['created_at']}\n"
                        f"[bold]Updated:[/bold] {task_dict['updated_at']}",
                        title="Task Status",
                    )
                )

        except Exception as e:
            console.print(Panel(f"[red]Error: {e}[/red]", title="Error"))

    elif cmd == "/clear":
        # Clear screen for chat history
        console.clear()
        console.print(
            Panel(
                "[green]✓[/green] Chat history cleared\n"
                "[dim]Previous conversation context preserved for AI[/dim]",
                title="Chat Cleared",
            )
        )

    elif cmd == "/exit":
        console.print("[dim]Goodbye![/dim]")
        return "exit"

    else:
        console.print(
            Panel(
                f"[red]Unknown command: {cmd}[/red]\n[dim]Type /help for available commands[/dim]",
                title="Error",
            )
        )


@main.command()
@click.option("--exit", is_flag=True, help="Exit after single message (for testing)")
def chat(exit: bool) -> None:
    """Start natural conversation with UX agent."""

    async def _chat_session():
        import asyncio
        import time
        import uuid

        from rich.align import Align
        from rich.columns import Columns
        from rich.live import Live
        from rich.text import Text

        try:
            # Check if project exists
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

            # Generate session ID
            session_id = str(uuid.uuid4())

            # Create UX agent client
            ux_client = HTTPMCPClient("http://localhost:8082")

            # Conversation history for rich display
            conversation_history = []

            try:
                # Connect to UX agent
                await ux_client.connect()

                console.print(
                    Panel(
                        "[green]✓[/green] Connected to UX agent\n"
                        "[dim]Type 'exit' to quit, Ctrl+C to interrupt[/dim]",
                        title="Chat Session Started",
                    )
                )

                # Chat loop
                while True:
                    try:
                        # Get user input
                        user_input = console.input("\n[cyan]You:[/cyan] ")

                        # Check for exit
                        if user_input.lower().strip() in ["exit", "quit", "bye"]:
                            console.print("[dim]Goodbye![/dim]")
                            break

                        # Handle in-chat commands
                        if user_input.startswith("/"):
                            result = await _handle_chat_command(
                                user_input, console, project_root
                            )
                            if result == "exit":
                                break
                            continue

                        # Add user message to history
                        conversation_history.append(
                            {
                                "role": "user",
                                "content": user_input,
                                "timestamp": time.time(),
                            }
                        )

                        # Create streaming response display
                        start_time = time.time()

                        # Use Live display for streaming effect
                        with Live(console=console, refresh_per_second=10) as live:
                            # Show typing indicator
                            typing_indicator = Text("Tale is thinking", style="dim")
                            dots = ""

                            # Simulate typing indicator for visual feedback
                            for i in range(6):  # Show typing for ~0.6 seconds
                                dots = "." * ((i % 3) + 1)
                                typing_indicator = Text(
                                    f"Tale is thinking{dots}", style="dim"
                                )
                                live.update(
                                    Panel(
                                        typing_indicator, title="[dim]Processing[/dim]"
                                    )
                                )
                                await asyncio.sleep(0.1)

                            # Send to UX agent
                            try:
                                response = await ux_client.call_tool(
                                    "conversation",
                                    {"message": user_input, "session_id": session_id},
                                )

                                response_time = time.time() - start_time

                                # Process response
                                if isinstance(response, dict):
                                    # Handle UX agent response format
                                    message = response.get(
                                        "reply", response.get("message", "No response")
                                    )

                                    # Simulate progressive text display for better UX
                                    words = message.split()
                                    displayed_words = []

                                    for word in words:
                                        displayed_words.append(word)
                                        current_text = " ".join(displayed_words)

                                        # Create rich display with response time
                                        response_display = Text()
                                        response_display.append(
                                            "Tale: ", style="green bold"
                                        )
                                        response_display.append(current_text)

                                        # Add response time indicator
                                        time_indicator = Text(
                                            f"Response time: {response_time:.2f}s",
                                            style="dim",
                                        )

                                        display_content = Columns(
                                            [
                                                Panel(
                                                    response_display, title="Response"
                                                ),
                                                Align.right(time_indicator),
                                            ]
                                        )

                                        live.update(display_content)
                                        await asyncio.sleep(
                                            0.05
                                        )  # Simulate typing speed

                                    # Final display with full response
                                    final_response = Text()
                                    final_response.append("Tale: ", style="green bold")
                                    final_response.append(message)

                                    # Add response time
                                    time_text = Text(
                                        f"Response time: {response_time:.2f}s",
                                        style="dim",
                                    )

                                    final_display = Columns(
                                        [
                                            Panel(final_response, title="Response"),
                                            Align.right(time_text),
                                        ]
                                    )

                                    live.update(final_display)

                                    # Add to conversation history
                                    conversation_history.append(
                                        {
                                            "role": "assistant",
                                            "content": message,
                                            "timestamp": time.time(),
                                            "response_time": response_time,
                                        }
                                    )

                                    # Check for task detection
                                    if response.get("task_detected", False):
                                        task_id = response.get("task_id")
                                        confidence = response.get("confidence", 0.0)

                                        await asyncio.sleep(
                                            0.5
                                        )  # Brief pause before showing task info

                                        if task_id:
                                            task_panel = Panel(
                                                f"[yellow]✓[/yellow] Task detected and submitted\n"
                                                f"[dim]Task ID: {task_id[:8]}...[/dim]\n"
                                                f"[dim]Confidence: {confidence:.2f}[/dim]\n"
                                                f"[dim]Use /status {task_id[:8]} to check progress[/dim]",
                                                title="Task Handoff",
                                            )
                                        else:
                                            task_panel = Panel(
                                                f"[yellow]Task detected (confidence: {confidence:.2f})[/yellow]\n"
                                                "[dim]But task submission failed[/dim]",
                                                title="Task Detection",
                                            )

                                        live.update(
                                            Columns([final_display, task_panel])
                                        )

                                        # Add task info to conversation history
                                        if task_id:
                                            conversation_history.append(
                                                {
                                                    "role": "system",
                                                    "content": f"Task submitted: {task_id}",
                                                    "timestamp": time.time(),
                                                    "task_id": task_id,
                                                    "confidence": confidence,
                                                }
                                            )

                                else:
                                    # Handle non-dict responses
                                    response_display = Text()
                                    response_display.append(
                                        "Tale: ", style="green bold"
                                    )
                                    response_display.append(str(response))

                                    time_text = Text(
                                        f"Response time: {response_time:.2f}s",
                                        style="dim",
                                    )

                                    final_display = Columns(
                                        [
                                            Panel(response_display, title="Response"),
                                            Align.right(time_text),
                                        ]
                                    )

                                    live.update(final_display)

                                    conversation_history.append(
                                        {
                                            "role": "assistant",
                                            "content": str(response),
                                            "timestamp": time.time(),
                                            "response_time": response_time,
                                        }
                                    )

                            except Exception as e:
                                error_display = Text()
                                error_display.append("Error: ", style="red bold")
                                error_display.append(str(e))

                                live.update(
                                    Panel(error_display, title="[red]Error[/red]")
                                )
                                await asyncio.sleep(1)  # Show error briefly

                        # Exit after single message if flag set
                        if exit:
                            break

                        # Show conversation history summary if more than 3 exchanges
                        if len(conversation_history) > 6:  # 3 exchanges = 6 messages
                            assistant_messages = [
                                msg
                                for msg in conversation_history
                                if msg["role"] == "assistant"
                            ]
                            if assistant_messages:
                                avg_response_time = sum(
                                    msg.get("response_time", 0)
                                    for msg in assistant_messages
                                ) / len(assistant_messages)

                                console.print(
                                    f"\n[dim]Conversation summary: {len(conversation_history)//2} exchanges, "
                                    f"avg response time: {avg_response_time:.2f}s[/dim]"
                                )

                    except KeyboardInterrupt:
                        console.print("\n[dim]Chat interrupted.[/dim]")
                        break
                    except Exception as e:
                        console.print(f"[red]Error in conversation: {e}[/red]")
                        if exit:
                            break
                        continue

            except Exception as e:
                console.print(
                    Panel(
                        f"[red]Failed to connect to UX agent: {e}[/red]\n"
                        f"[dim]Make sure UX agent is running on port 8082[/dim]\n"
                        f"[dim]Try: tale serve[/dim]",
                        title="Connection Error",
                    )
                )
                return

            finally:
                await ux_client.close()

                # Export conversation history if it exists
                if conversation_history:
                    try:
                        import json
                        from datetime import datetime

                        export_data = {
                            "session_id": session_id,
                            "timestamp": datetime.now().isoformat(),
                            "conversation": conversation_history,
                            "summary": {
                                "total_exchanges": len(conversation_history) // 2,
                                "avg_response_time": sum(
                                    msg.get("response_time", 0)
                                    for msg in conversation_history
                                    if msg["role"] == "assistant"
                                )
                                / len(
                                    [
                                        msg
                                        for msg in conversation_history
                                        if msg["role"] == "assistant"
                                    ]
                                )
                                if any(
                                    msg["role"] == "assistant"
                                    for msg in conversation_history
                                )
                                else 0,
                            },
                        }

                        export_path = (
                            project_root / f"chat_history_{session_id[:8]}.json"
                        )
                        with open(export_path, "w") as f:
                            json.dump(export_data, f, indent=2)

                        console.print(
                            f"\n[dim]Conversation exported to: {export_path.name}[/dim]"
                        )

                    except Exception as e:
                        console.print(f"[dim]Failed to export conversation: {e}[/dim]")

        except Exception as e:
            console.print(Panel(f"[red]Chat error: {e}[/red]", title="Error"))

    run_async(_chat_session())


if __name__ == "__main__":
    main()
