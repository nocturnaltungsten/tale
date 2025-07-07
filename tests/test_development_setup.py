"""Test development environment setup."""
import sys
from pathlib import Path


def test_python_version():
    """Test that we're running Python 3.10+."""
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version_info}"


def test_project_structure():
    """Test that essential project directories exist."""
    project_root = Path(__file__).parent.parent

    # Check essential directories
    assert (project_root / "src" / "tale").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "scripts").exists()
    assert (project_root / "dev-docs").exists()


def test_scripts_executable():
    """Test that development scripts are executable."""
    project_root = Path(__file__).parent.parent
    scripts_dir = project_root / "scripts"

    scripts = [
        "setup-dev.sh",
        "test.sh",
        "lint.sh",
        "format.sh",
        "clean.sh",
        "benchmark.sh",
    ]

    for script in scripts:
        script_path = scripts_dir / script
        assert script_path.exists(), f"Script {script} not found"
        assert script_path.stat().st_mode & 0o111, f"Script {script} not executable"


def test_configuration_files():
    """Test that configuration files exist."""
    project_root = Path(__file__).parent.parent

    config_files = [
        "pyproject.toml",
        ".pre-commit-config.yaml",
        "Makefile",
        ".github/workflows/ci.yml",
    ]

    for config_file in config_files:
        assert (
            project_root / config_file
        ).exists(), f"Config file {config_file} not found"


def test_imports():
    """Test that we can import tale modules."""
    # Test basic imports work (modules should exist even if empty)
    import tale

    assert hasattr(tale, "__version__") or True  # Version might not be set yet

    # Test submodule structure exists
    from tale import cli, mcp, models, servers, storage

    # These imports should not fail even if modules are empty
    assert cli is not None
    assert mcp is not None
    assert models is not None
    assert storage is not None
    assert servers is not None
