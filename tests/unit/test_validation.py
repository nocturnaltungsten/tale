"""Tests for input validation framework."""

import uuid

import pytest

from src.exceptions import ValidationException
from src.validation import (
    validate_json_request,
    validate_port_number,
    validate_task_id,
    validate_task_text,
    validate_timeout_seconds,
)


@pytest.mark.unit
class TestValidateTaskText:
    """Test cases for validate_task_text function."""

    def test_valid_task_text(self):
        """Test validation of valid task text."""
        text = "Write a Python function"
        result = validate_task_text(text)
        assert result == text

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from task text."""
        text = "  Write a Python function  "
        result = validate_task_text(text)
        assert result == "Write a Python function"

    def test_empty_text_raises_exception(self):
        """Test that empty text raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_text("")
        assert "cannot be empty" in str(exc_info.value)

    def test_whitespace_only_raises_exception(self):
        """Test that whitespace-only text raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_text("   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_text_too_long_raises_exception(self):
        """Test that text over 10,000 characters raises ValidationException."""
        long_text = "x" * 10001
        with pytest.raises(ValidationException) as exc_info:
            validate_task_text(long_text)
        assert "cannot exceed 10,000 characters" in str(exc_info.value)

    def test_text_exactly_10000_chars_passes(self):
        """Test that text exactly 10,000 characters passes validation."""
        text = "x" * 10000
        result = validate_task_text(text)
        assert result == text

    def test_non_string_raises_exception(self):
        """Test that non-string input raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_text(123)
        assert "must be a string" in str(exc_info.value)


@pytest.mark.unit
class TestValidateTaskId:
    """Test cases for validate_task_id function."""

    def test_valid_uuid4(self):
        """Test validation of valid UUID4."""
        task_id = str(uuid.uuid4())
        result = validate_task_id(task_id)
        assert result == task_id

    def test_invalid_uuid_format_raises_exception(self):
        """Test that invalid UUID format raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_id("not-a-uuid")
        assert "valid UUID4 format" in str(exc_info.value)

    def test_uuid_version_1_raises_exception(self):
        """Test that UUID version 1 raises ValidationException."""
        uuid1 = str(uuid.uuid1())
        with pytest.raises(ValidationException) as exc_info:
            validate_task_id(uuid1)
        assert "UUID version 4" in str(exc_info.value)

    def test_non_string_raises_exception(self):
        """Test that non-string input raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_id(123)
        assert "must be a string" in str(exc_info.value)


@pytest.mark.unit
class TestValidatePortNumber:
    """Test cases for validate_port_number function."""

    def test_valid_port_number(self):
        """Test validation of valid port numbers."""
        assert validate_port_number(8080) == 8080
        assert validate_port_number(1024) == 1024
        assert validate_port_number(65535) == 65535

    def test_port_below_1024_raises_exception(self):
        """Test that ports below 1024 raise ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_port_number(80)
        assert "must be >= 1024" in str(exc_info.value)

    def test_port_above_65535_raises_exception(self):
        """Test that ports above 65535 raise ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_port_number(70000)
        assert "must be <= 65535" in str(exc_info.value)

    def test_non_integer_raises_exception(self):
        """Test that non-integer input raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_port_number("8080")
        assert "must be an integer" in str(exc_info.value)


@pytest.mark.unit
class TestValidateTimeoutSeconds:
    """Test cases for validate_timeout_seconds function."""

    def test_valid_timeout_values(self):
        """Test validation of valid timeout values."""
        assert validate_timeout_seconds(1) == 1
        assert validate_timeout_seconds(30) == 30
        assert validate_timeout_seconds(3600) == 3600

    def test_timeout_below_1_raises_exception(self):
        """Test that timeout below 1 second raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_timeout_seconds(0)
        assert "must be at least 1 second" in str(exc_info.value)

    def test_timeout_above_3600_raises_exception(self):
        """Test that timeout above 3600 seconds raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_timeout_seconds(3601)
        assert "cannot exceed 3600 seconds" in str(exc_info.value)

    def test_non_integer_raises_exception(self):
        """Test that non-integer input raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_timeout_seconds("30")
        assert "must be an integer" in str(exc_info.value)


@pytest.mark.unit
class TestValidateJsonRequest:
    """Test cases for validate_json_request function."""

    def test_valid_json_request(self):
        """Test validation of valid JSON request."""
        data = {"name": "test", "value": 42}
        required_keys = ["name", "value"]
        result = validate_json_request(data, required_keys)
        assert result == data

    def test_missing_required_keys_raises_exception(self):
        """Test that missing required keys raise ValidationException."""
        data = {"name": "test"}
        required_keys = ["name", "value"]
        with pytest.raises(ValidationException) as exc_info:
            validate_json_request(data, required_keys)
        assert "Missing required keys: value" in str(exc_info.value)

    def test_multiple_missing_keys_raises_exception(self):
        """Test that multiple missing keys are reported."""
        data = {"name": "test"}
        required_keys = ["name", "value", "type"]
        with pytest.raises(ValidationException) as exc_info:
            validate_json_request(data, required_keys)
        assert "Missing required keys: value, type" in str(exc_info.value)

    def test_extra_keys_allowed(self):
        """Test that extra keys are allowed."""
        data = {"name": "test", "value": 42, "extra": "allowed"}
        required_keys = ["name", "value"]
        result = validate_json_request(data, required_keys)
        assert result == data

    def test_empty_required_keys_passes(self):
        """Test that empty required keys list passes validation."""
        data = {"name": "test"}
        required_keys = []
        result = validate_json_request(data, required_keys)
        assert result == data

    def test_non_dict_data_raises_exception(self):
        """Test that non-dict data raises ValidationException."""
        with pytest.raises(ValidationException) as exc_info:
            validate_json_request("not a dict", ["key"])
        assert "must be a dictionary" in str(exc_info.value)

    def test_non_list_required_keys_raises_exception(self):
        """Test that non-list required_keys raises ValidationException."""
        data = {"name": "test"}
        with pytest.raises(ValidationException) as exc_info:
            validate_json_request(data, "not a list")
        assert "must be a list" in str(exc_info.value)


@pytest.mark.unit
class TestValidationExceptionContext:
    """Test that ValidationException includes proper context data."""

    def test_task_text_context(self):
        """Test that task text validation includes context."""
        with pytest.raises(ValidationException) as exc_info:
            validate_task_text("x" * 10001)

        exception = exc_info.value
        assert exception.context["length"] == 10001
        assert exception.context["max_length"] == 10000

    def test_port_number_context(self):
        """Test that port validation includes context."""
        with pytest.raises(ValidationException) as exc_info:
            validate_port_number(80)

        exception = exc_info.value
        assert exception.context["port"] == 80
        assert exception.context["min_port"] == 1024

    def test_json_request_context(self):
        """Test that JSON request validation includes context."""
        data = {"name": "test"}
        required_keys = ["name", "value"]

        with pytest.raises(ValidationException) as exc_info:
            validate_json_request(data, required_keys)

        exception = exc_info.value
        assert exception.context["missing_keys"] == ["value"]
        assert exception.context["required_keys"] == required_keys
        assert exception.context["provided_keys"] == ["name"]
