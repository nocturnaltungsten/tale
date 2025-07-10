#!/usr/bin/env python3
"""
Test the conversational interface directly
"""

import asyncio
import sys

sys.path.insert(0, "/Users/ahughes/dev/tale/src")

from tale.mcp.http_client import HTTPMCPClient  # noqa: E402


async def test_conversation():
    """Test a simple conversation with the UX agent"""

    client = HTTPMCPClient("http://localhost:8082")

    try:
        # Connect to the client
        await client.connect()

        # Test 1: Simple greeting
        print("=== Test 1: Simple greeting ===")
        response = await client.call_tool(
            "conversation", {"message": "Hello, how are you?"}
        )
        print(f"Response: {response}")

        # Test 2: Task detection
        print("\n=== Test 2: Task detection ===")
        response = await client.call_tool(
            "conversation",
            {
                "message": "Can you write a Python function to calculate fibonacci numbers?"
            },
        )
        print(f"Response: {response}")

        # Test 3: Context awareness
        print("\n=== Test 3: Context awareness ===")
        response = await client.call_tool(
            "conversation", {"message": "What was my last request?"}
        )
        print(f"Response: {response}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_conversation())
