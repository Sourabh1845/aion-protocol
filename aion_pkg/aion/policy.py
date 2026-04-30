import fnmatch
import json
import os
from pathlib import Path

VALID_DECISIONS = {"allow", "log", "approval", "block"}

DEFAULT_POLICY = {
    "default_decision": "log",
    "tools": {
        "file.read": {"decision": "allow", "risk": "low"},
        "file.list": {"decision": "allow", "risk": "low"},
        "file.write": {"decision": "log", "risk": "medium"},
        "file.delete": {"decision": "approval", "risk": "high"},
        "email.send": {"decision": "approval", "risk": "high"},
        "shell.run": {
            "decision": "approval",
            "risk": "high",
            "block_patterns": ["rm -rf", "del /s", "format ", "drop database"],
        },
        "secrets.*": {"decision": "block", "risk": "forbidden"},
        "payments.*": {"decision": "approval", "risk": "high"},
        "deploy.production": {"decision": "approval", "risk": "high"},
    },
}


def load_policy(path=None):
    policy_path = path or os.getenv("AION_POLICY_FILE") or "aion-policy.json"
    file_path = Path(policy_path)

    if not file_path.exists():
        return DEFAULT_POLICY

    try:
        with file_path.open("r", encoding="utf-8") as f:
            loaded = json.load(f)
    except Exception as exc:
        return {
            **DEFAULT_POLICY,
            "_load_error": f"Could not load policy file {file_path}: {exc}",
        }

    merged = {
        "default_decision": loaded.get(
            "default_decision", DEFAULT_POLICY["default_decision"]
        ),
        "tools": {**DEFAULT_POLICY["tools"], **loaded.get("tools", {})},
    }
    return merged


def _normalize_decision(value):
    decision = str(value or "").lower().strip()
    return decision if decision in VALID_DECISIONS else "log"


def _string_blob(metadata):
    if metadata is None:
        return ""
    if isinstance(metadata, str):
        return metadata.lower()
    try:
        return json.dumps(metadata, sort_keys=True, default=str).lower()
    except Exception:
        return str(metadata).lower()


def _find_rule(scope, tools):
    if scope in tools:
        return tools[scope]

    for pattern, rule in tools.items():
        if fnmatch.fnmatch(scope, pattern):
            return rule

    return None


def _matches_block_pattern(rule, metadata):
    blob = _string_blob(metadata)
    for pattern in rule.get("block_patterns", []):
        if pattern.lower() in blob:
            return pattern
    return None


def evaluate_policy(scope, metadata=None, policy=None):
    if not scope or not isinstance(scope, str):
        return {
            "decision": "block",
            "risk": "invalid",
            "reason": "Scope must be a non-empty string",
            "scope": scope,
        }

    active_policy = policy or load_policy()
    tools = active_policy.get("tools", {})
    rule = _find_rule(scope, tools)

    if not rule:
        decision = _normalize_decision(active_policy.get("default_decision", "log"))
        return {
            "decision": decision,
            "risk": "unknown",
            "reason": f"No exact policy matched; using default decision: {decision}",
            "scope": scope,
        }

    matched_pattern = _matches_block_pattern(rule, metadata)
    if matched_pattern:
        return {
            "decision": "block",
            "risk": "forbidden",
            "reason": f"Blocked by pattern: {matched_pattern}",
            "scope": scope,
        }

    decision = _normalize_decision(rule.get("decision"))
    risk = rule.get("risk", "unknown")

    return {
        "decision": decision,
        "risk": risk,
        "reason": rule.get("reason", f"Matched policy for {scope}"),
        "scope": scope,
    }
