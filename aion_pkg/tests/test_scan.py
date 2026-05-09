from pathlib import Path

from aion.scan import scan_path, summarize_findings


def test_scan_detects_shell_execution(tmp_path):
    target = tmp_path / "agent.py"
    target.write_text(
        "import subprocess\nsubprocess.run(['echo', 'hello'])\n",
        encoding="utf-8",
    )

    report = scan_path(target)

    assert report["findings_count"] == 1
    assert report["findings"][0]["id"] == "shell-subprocess"
    assert report["findings"][0]["severity"] == "HIGH"


def test_scan_detects_file_delete(tmp_path):
    target = tmp_path / "tool.py"
    target.write_text(
        "import os\nos.remove('danger.txt')\n",
        encoding="utf-8",
    )

    report = scan_path(target)

    assert report["findings_count"] == 1
    assert report["findings"][0]["scope"] == "file.delete"


def test_scan_ignores_test_and_demo_files(tmp_path):
    test_file = tmp_path / "test_agent.py"
    demo_file = tmp_path / "delete_demo.py"

    test_file.write_text("import subprocess\nsubprocess.run(['x'])\n", encoding="utf-8")
    demo_file.write_text("import os\nos.remove('x')\n", encoding="utf-8")

    report = scan_path(tmp_path)

    assert report["findings_count"] == 0


def test_scan_summary_counts(tmp_path):
    target = tmp_path / "agent.py"
    target.write_text(
        "import subprocess\nsubprocess.run(['x'])\nrequests.post('https://example.com')\n",
        encoding="utf-8",
    )

    report = scan_path(target)
    summary = summarize_findings(report)

    assert summary["HIGH"] == 1
    assert summary["MEDIUM"] == 1
