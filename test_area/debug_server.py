#!/usr/bin/env python
"""Debug script to test execution server."""

import asyncio
import logging

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def test_execution_server():
    """Test the execution server."""
    try:
        from tale.servers.execution_server import ExecutionServer
        from tale.storage.database import Database
        from tale.storage.task_store import TaskStore

        print("Creating execution server...")
        server = ExecutionServer()

        # Check database
        print("Checking database...")
        db = Database("tale.db")
        TaskStore(db)

        # Check for tasks
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT id, status, task_text FROM tasks")
            tasks = cursor.fetchall()
            print(f"Found {len(tasks)} tasks:")
            for task in tasks:
                print(f"  - {task[0][:8]}: {task[1]} - {task[2]}")

        # Try to start the server
        print("\nStarting server...")
        await server.start()

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_execution_server())
