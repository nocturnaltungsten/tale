"""Tests for the constants module."""

import pytest

from src.constants import (
    CLI_INIT_DELAY,
    DEFAULT_HTTP_TIMEOUT,
    ERROR_RETRY_DELAY,
    EXECUTION_PORT,
    GATEWAY_PORT,
    MAX_TASK_RETRIES,
    MONITOR_INTERVAL,
    POLLING_INTERVAL,
    RESTART_DELAY,
    SERVER_START_DELAY,
    TASK_EXECUTION_TIMEOUT,
    TASK_TEXT_TRUNCATE,
    UX_AGENT_PORT,
)


@pytest.mark.unit
class TestConstants:
    """Test all constants have correct types and values."""

    def test_http_timeout_constants(self):
        """Test HTTP timeout related constants."""
        assert isinstance(DEFAULT_HTTP_TIMEOUT, int)
        assert DEFAULT_HTTP_TIMEOUT == 30
        assert DEFAULT_HTTP_TIMEOUT > 0

    def test_port_constants(self):
        """Test port related constants."""
        assert isinstance(GATEWAY_PORT, int)
        assert isinstance(EXECUTION_PORT, int)
        assert isinstance(UX_AGENT_PORT, int)
        assert GATEWAY_PORT == 8080
        assert EXECUTION_PORT == 8081
        assert UX_AGENT_PORT == 8082
        assert 1024 <= GATEWAY_PORT <= 65535
        assert 1024 <= EXECUTION_PORT <= 65535
        assert 1024 <= UX_AGENT_PORT <= 65535

    def test_timeout_constants(self):
        """Test timeout related constants."""
        assert isinstance(TASK_EXECUTION_TIMEOUT, int)
        assert TASK_EXECUTION_TIMEOUT == 300
        assert TASK_EXECUTION_TIMEOUT > 0

    def test_interval_constants(self):
        """Test interval related constants."""
        assert isinstance(POLLING_INTERVAL, int)
        assert isinstance(MONITOR_INTERVAL, int)
        assert POLLING_INTERVAL == 2
        assert MONITOR_INTERVAL == 10
        assert POLLING_INTERVAL > 0
        assert MONITOR_INTERVAL > 0

    def test_delay_constants(self):
        """Test delay related constants."""
        assert isinstance(SERVER_START_DELAY, int)
        assert isinstance(CLI_INIT_DELAY, int)
        assert isinstance(RESTART_DELAY, int)
        assert isinstance(ERROR_RETRY_DELAY, int)
        assert SERVER_START_DELAY == 1
        assert CLI_INIT_DELAY == 2
        assert RESTART_DELAY == 2
        assert ERROR_RETRY_DELAY == 5
        assert all(
            delay > 0
            for delay in [
                SERVER_START_DELAY,
                CLI_INIT_DELAY,
                RESTART_DELAY,
                ERROR_RETRY_DELAY,
            ]
        )

    def test_display_constants(self):
        """Test display related constants."""
        assert isinstance(TASK_TEXT_TRUNCATE, int)
        assert TASK_TEXT_TRUNCATE == 60
        assert TASK_TEXT_TRUNCATE > 0

    def test_retry_constants(self):
        """Test retry related constants."""
        assert isinstance(MAX_TASK_RETRIES, int)
        assert MAX_TASK_RETRIES == 3
        assert MAX_TASK_RETRIES > 0

    def test_constants_naming_convention(self):
        """Test that all constants follow SCREAMING_SNAKE_CASE."""
        constant_names = [
            "DEFAULT_HTTP_TIMEOUT",
            "GATEWAY_PORT",
            "EXECUTION_PORT",
            "UX_AGENT_PORT",
            "TASK_EXECUTION_TIMEOUT",
            "POLLING_INTERVAL",
            "SERVER_START_DELAY",
            "CLI_INIT_DELAY",
            "RESTART_DELAY",
            "TASK_TEXT_TRUNCATE",
            "MONITOR_INTERVAL",
            "ERROR_RETRY_DELAY",
            "MAX_TASK_RETRIES",
        ]

        for name in constant_names:
            # Check that name is all uppercase with underscores
            assert name.isupper()
            assert all(c.isalpha() or c == "_" or c.isdigit() for c in name)
            # Check that constant exists and is accessible
            assert hasattr(pytest.importorskip("src.constants"), name)

    def test_all_constants_are_integers(self):
        """Test that all constants are integers."""
        constants = [
            DEFAULT_HTTP_TIMEOUT,
            GATEWAY_PORT,
            EXECUTION_PORT,
            UX_AGENT_PORT,
            TASK_EXECUTION_TIMEOUT,
            POLLING_INTERVAL,
            SERVER_START_DELAY,
            CLI_INIT_DELAY,
            RESTART_DELAY,
            TASK_TEXT_TRUNCATE,
            MONITOR_INTERVAL,
            ERROR_RETRY_DELAY,
            MAX_TASK_RETRIES,
        ]

        for constant in constants:
            assert isinstance(constant, int)
            assert constant > 0  # All constants should be positive integers

    def test_constants_count(self):
        """Test that we have exactly 14 constants as specified."""
        import src.constants as constants_module

        # Get all attributes that are constants (uppercase names)
        constant_names = [
            name
            for name in dir(constants_module)
            if not name.startswith("_") and name.isupper()
        ]

        assert (
            len(constant_names) == 13
        ), f"Expected 13 constants, found {len(constant_names)}: {constant_names}"
