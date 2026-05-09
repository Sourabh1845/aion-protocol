import json
from pathlib import Path

DEFAULT_IGNORES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    ".aion",
    "site-packages",
    "aion_protocol.egg-info",
    "docs",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
}

RISK_RULES = [
    {
        "id": "shell-subprocess",
        "severity": "HIGH",
        "scope": "shell.run",
        "patterns": ["subprocess.", "os.system(", "Popen("],
        "message": "Shell command execution found",
        "recommendation": 'Wrap this action with @guard(scope="shell.run").',
    },
    {
        "id": "file-delete",
        "severity": "HIGH",
        "scope": "file.delete",
        "patterns": ["os.remove(", "os.unlink(", "shutil.rmtree(", "Path.unlink("],
        "message": "File deletion capability found",
        "recommendation": 'Wrap this action with @guard(scope="file.delete").',
    },
    {
        "id": "secret-env-access",
        "severity": "HIGH",
        "scope": "secrets.read",
        "patterns": [
            "os.environ",
            "getenv(",
            ".env",
            "api_key=",
            "apikey=",
            "secret=",
            "password=",
            "token=",
        ],
        "message": "Secret or environment access pattern found",
        "recommendation": "Use AION policy to block or audit secrets.* access.",
    },
    {
        "id": "network-call",
        "severity": "MEDIUM",
        "scope": "network.call",
        "patterns": ["requests.", "httpx.", "fetch(", "axios.", "urllib.request"],
        "message": "Network/API call capability found",
        "recommendation": 'Consider @guard(scope="network.call") for external API actions.',
    },
    {
        "id": "email-send",
        "severity": "HIGH",
        "scope": "email.send",
        "patterns": ["sendmail(", "SMTP(", "send_email", "email.send"],
        "message": "Email sending capability found",
        "recommendation": 'Wrap this action with @guard(scope="email.send").',
    },
    {
        "id": "database-write",
        "severity": "HIGH",
        "scope": "database.write",
        "patterns": ["DROP TABLE", "DELETE FROM", "TRUNCATE TABLE", "UPDATE ", "INSERT INTO"],
        "message": "Database write/destructive pattern found",
        "recommendation": "Require approval for database.write or database.admin actions.",
    },
    {
        "id": "mcp-config",
        "severity": "MEDIUM",
        "scope": "mcp.tool",
        "patterns": ["mcpServers", "modelcontextprotocol", "MCP_SERVER", "mcp-server"],
        "message": "MCP configuration or server reference found",
        "recommendation": "Review MCP tool permissions and add AION Guard/MCP firewall later.",
    },
]


def _should_ignore(path):
    parts = set(path.parts)
    name = path.name.lower()
    text_path = str(path).lower()

    if any(part in DEFAULT_IGNORES for part in parts):
        return True

    if name == "scan.py":
        return True

    if "test" in name or "demo" in name:
        return True

    if "\\tests\\" in text_path or "/tests/" in text_path:
        return True

    return False


def _is_text_file(path):
    return path.suffix.lower() in TEXT_EXTENSIONS


def _scan_line(file_path, line_number, line):
    findings = []
    lowered = line.lower()

    for rule in RISK_RULES:
        for pattern in rule["patterns"]:
            if pattern.lower() in lowered:
                findings.append(
                    {
                        "id": rule["id"],
                        "severity": rule["severity"],
                        "scope": rule["scope"],
                        "file": str(file_path),
                        "line": line_number,
                        "pattern": pattern,
                        "message": rule["message"],
                        "recommendation": rule["recommendation"],
                    }
                )
                break

    return findings


def scan_path(target="."):
    root = Path(target).resolve()
    findings = []
    files_scanned = 0

    if root.is_file():
        files = [root]
    else:
        files = [
            path
            for path in root.rglob("*")
            if path.is_file() and not _should_ignore(path) and _is_text_file(path)
        ]

    for file_path in files:
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for index, line in enumerate(f, start=1):
                    findings.extend(_scan_line(file_path, index, line))
            files_scanned += 1
        except OSError:
            continue

    return {
        "target": str(root),
        "files_scanned": files_scanned,
        "findings_count": len(findings),
        "findings": findings,
    }


def summarize_findings(report):
    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for finding in report["findings"]:
        severity = finding["severity"]
        counts[severity] = counts.get(severity, 0) + 1

    return counts


def print_report(report, limit=50):
    counts = summarize_findings(report)

    print("AION Scan Report")
    print(f"Target: {report['target']}")
    print(f"Files scanned: {report['files_scanned']}")
    print(f"Findings: {report['findings_count']}")
    print(
        f"HIGH: {counts.get('HIGH', 0)} | "
        f"MEDIUM: {counts.get('MEDIUM', 0)} | "
        f"LOW: {counts.get('LOW', 0)}"
    )
    print("")

    if not report["findings"]:
        print("No risky agent/tool patterns found.")
        return

    for finding in report["findings"][:limit]:
        print(
            f"[{finding['severity']}] {finding['message']} "
            f"({finding['file']}:{finding['line']})"
        )
        print(f"  pattern: {finding['pattern']}")
        print(f"  scope: {finding['scope']}")
        print(f"  recommendation: {finding['recommendation']}")
        print("")

    remaining = report["findings_count"] - limit
    if remaining > 0:
        print(f"...and {remaining} more finding(s).")


def report_to_json(report):
    return json.dumps(report, indent=2, sort_keys=True)
