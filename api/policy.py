from datetime import datetime, timezone

def _now():
    return datetime.now(timezone.utc)

def _check_allowed_hours(rule, now):
    hour = now.hour
    start, end = rule["value"]
    return start <= hour <= end

def _check_max_uses(rule, auth):
    return auth.get("uses", 0) < rule["value"]

RULE_CHECKS = {
    "allowed_hours": _check_allowed_hours,
    "max_uses": _check_max_uses,
}

def evaluate_policy(policy, auth):
    if not policy:
        return True, None

    now = _now()
    results = []

    for rule in policy.get("rules", []):
        checker = RULE_CHECKS.get(rule["type"])
        if not checker:
            continue

        ok = checker(rule, auth) if rule["type"] == "max_uses" else checker(rule, now)
        results.append(ok)

    mode = policy.get("mode", "ALL")

    if mode == "ALL" and not all(results):
        return False, "POLICY_VIOLATION"
    if mode == "ANY" and not any(results):
        return False, "NO_RULE_PASSED"

    return True, None


def merge_policies(parent, child):
    if not parent:
        return child
    if not child:
        return parent

    merged = {"mode": "ALL", "rules": []}

    rules = {}

    for p in parent.get("rules", []):
        rules[p["type"]] = p

    for c in child.get("rules", []):
        t = c["type"]
        if t not in rules:
            rules[t] = c
        else:
            if t == "max_uses":
                rules[t] = {
                    "type": "max_uses",
                    "value": min(rules[t]["value"], c["value"]),
                }
            elif t == "allowed_hours":
                a = rules[t]["value"]
                b = c["value"]
                rules[t] = {
                    "type": "allowed_hours",
                    "value": [max(a[0], b[0]), min(a[1], b[1])],
                }

    merged["rules"] = list(rules.values())
    return merged
