import pytest

from aion.guard import AIONApprovalRequired, AIONBlockedError, guard


def test_guard_allows_low_risk_action():
    @guard(
        scope="file.read",
        agent="test-agent",
        metadata_factory=lambda path: {"path": path},
    )
    def read_file(path):
        return f"read {path}"

    result = read_file("README.md")

    assert result["result"] == "read README.md"
    assert result["aion"]["decision"] == "allow"
    assert result["aion"]["risk"] == "low"
    assert result["aion"]["elapsed_ms"] < 100


def test_guard_blocks_forbidden_pattern():
    @guard(
        scope="shell.run",
        agent="test-agent",
        metadata_factory=lambda command: {"command": command},
    )
    def run_shell(command):
        return f"executed {command}"

    with pytest.raises(AIONBlockedError):
        run_shell("rm -rf important")


def test_guard_requires_approval_when_approval_mode_disabled():
    @guard(
        scope="file.delete",
        agent="test-agent",
        metadata_factory=lambda path: {"path": path},
    )
    def delete_file(path):
        return f"deleted {path}"

    with pytest.raises(AIONApprovalRequired):
        delete_file("old.log")
