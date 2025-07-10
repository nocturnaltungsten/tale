#!/usr/bin/env python3
"""
Demo script for testing the conversational interface
"""

import sys

sys.path.insert(0, "/Users/ahughes/dev/tale/src")

from tale.cli.main import main  # noqa: E402

if __name__ == "__main__":
    # Test the chat command
    sys.argv = ["tale", "chat", "--exit"]
    main()
