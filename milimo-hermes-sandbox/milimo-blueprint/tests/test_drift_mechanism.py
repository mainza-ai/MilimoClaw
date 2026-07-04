# SPDX-FileCopyrightText: Copyright (c) 2026 Mainza Kangombe. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the CI drift detection mechanism (check-drift.py).
"""

import importlib.util
from pathlib import Path
import tempfile
import shutil
import pytest
from unittest.mock import patch

# Dynamically import the check-drift.py script
scripts_dir = Path(__file__).parent.parent.parent / "scripts"
spec = importlib.util.spec_from_file_location("check_drift", str(scripts_dir / "check-drift.py"))
check_drift = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_drift)


@pytest.fixture
def temp_fixtures():
    """Create a temporary directory simulating the repository folders."""
    tmpdir = tempfile.mkdtemp(prefix="milimo-drift-test-")
    tmp_path = Path(tmpdir)

    # Create mock directory structures
    core_src = tmp_path / "milimo-core/src/milimo_core"
    sandbox_core_src = tmp_path / "milimo-hermes-sandbox/milimo-core/src/milimo_core"
    bp_src = tmp_path / "milimo-blueprint/orchestrator"
    sandbox_bp_src = tmp_path / "milimo-hermes-sandbox/milimo-blueprint/orchestrator"

    for d in [core_src, sandbox_core_src, bp_src, sandbox_bp_src]:
        d.mkdir(parents=True, exist_ok=True)

    yield {
        "root": tmp_path,
        "core_src": core_src,
        "sandbox_core_src": sandbox_core_src,
        "bp_src": bp_src,
        "sandbox_bp_src": sandbox_bp_src,
    }

    shutil.rmtree(tmpdir)


def test_diff_files_identical(temp_fixtures) -> None:
    """Verify diff_files returns True when file bytes match exactly."""
    f1 = temp_fixtures["core_src"] / "test.py"
    f2 = temp_fixtures["sandbox_core_src"] / "test.py"

    f1.write_bytes(b"print('hello')")
    f2.write_bytes(b"print('hello')")

    assert check_drift.diff_files(f1, f2) is True


def test_diff_files_differing(temp_fixtures) -> None:
    """Verify diff_files returns False when file bytes do not match."""
    f1 = temp_fixtures["core_src"] / "test.py"
    f2 = temp_fixtures["sandbox_core_src"] / "test.py"

    f1.write_bytes(b"print('hello')")
    f2.write_bytes(b"print('world')")

    assert check_drift.diff_files(f1, f2) is False


def test_main_no_drift(temp_fixtures) -> None:
    """Verify main() exits 0 when core and sandbox directories are in perfect sync."""
    # Write matching files in core and sandbox
    (temp_fixtures["core_src"] / "a.py").write_bytes(b"x = 1")
    (temp_fixtures["sandbox_core_src"] / "a.py").write_bytes(b"x = 1")

    (temp_fixtures["bp_src"] / "b.py").write_bytes(b"y = 2")
    (temp_fixtures["sandbox_bp_src"] / "b.py").write_bytes(b"y = 2")

    with patch("pathlib.Path.parent", temp_fixtures["root"]), \
         patch("sys.exit") as mock_exit:
        check_drift.main()
        mock_exit.assert_called_once_with(0)


def test_main_drift_file_missing_in_sandbox(temp_fixtures) -> None:
    """Verify main() exits 1 when a core file is missing from the sandbox mirror."""
    (temp_fixtures["core_src"] / "missing.py").write_bytes(b"x = 1")

    with patch("pathlib.Path.parent", temp_fixtures["root"]), \
         patch("sys.exit") as mock_exit:
        check_drift.main()
        mock_exit.assert_called_once_with(1)


def test_main_drift_file_content_mismatch(temp_fixtures) -> None:
    """Verify main() exits 1 when contents differ between core and sandbox files."""
    (temp_fixtures["core_src"] / "mismatch.py").write_bytes(b"x = 1")
    (temp_fixtures["sandbox_core_src"] / "mismatch.py").write_bytes(b"x = 2")

    with patch("pathlib.Path.parent", temp_fixtures["root"]), \
         patch("sys.exit") as mock_exit:
        check_drift.main()
        mock_exit.assert_called_once_with(1)
