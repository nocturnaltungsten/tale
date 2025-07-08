#!/usr/bin/env python
"""Test execution server polling directly."""

import asyncio
import logging

from tale.storage.database import Database
from tale.storage.task_store import TaskStore

logging.basicConfig(level=logging.INFO)


async def test_polling():
    """Test the polling logic."""
    db = Database("tale.db")
    task_store = TaskStore(db)

    # Check current tasks
    with db.get_connection() as conn:
        cursor = conn.execute("SELECT id, status, task_text FROM tasks")
        tasks = cursor.fetchall()
        print("\nCurrent tasks:")
        for task in tasks:
            print(f"  {task[0][:8]}: {task[1]} - {task[2]}")

    # Simulate polling logic
    print("\nSimulating execution server polling...")

    # Get tasks with status 'running' (what execution server looks for)
    with db.get_connection() as conn:
        cursor = conn.execute(
            "SELECT id, task_text FROM tasks WHERE status = 'running' ORDER BY created_at LIMIT 1"
        )
        running_task = cursor.fetchone()

    if running_task:
        task_id, task_text = running_task
        print(f"Found task to execute: {task_id[:8]} - {task_text}")

        # Simulate execution
        print("Simulating task execution...")
        await asyncio.sleep(1)

        # Update status to completed
        task_store.update_task_status(task_id, "completed")
        print(f"Task {task_id[:8]} marked as completed")
    else:
        print("No tasks with status 'running' found")


if __name__ == "__main__":
    asyncio.run(test_polling())
