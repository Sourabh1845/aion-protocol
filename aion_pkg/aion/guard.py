import functools
import os
import time

from aion.policy import evaluate_policy
from aion.receipts import record_receipt


class AIONBlockedError(PermissionError):
    pass


class AIONApprovalRequired(PermissionError):
    pass


def _approval_enabled():
    value = os.getenv("AION_REQUIRE_APPROVAL", "false").lower().strip()
    return value in {"1", "true", "yes", "y"}


def _approval_prompt(scope, risk, reason, metadata):
    print("\nAION approval required")
    print(f"Scope: {scope}")
    print(f"Risk: {risk}")
    print(f"Reason: {reason}")
    if metadata:
        print(f"Metadata: {metadata}")

    answer = input("Approve this action? Type YES to approve: ")
    return answer.strip() == "YES"


def guard(scope, agent="unknown-agent", metadata_factory=None, policy=None):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.perf_counter()

            metadata = {}
            if metadata_factory:
                metadata = metadata_factory(*args, **kwargs) or {}

            decision = evaluate_policy(scope, metadata=metadata, policy=policy)
            action = decision["decision"]

            if action == "block":
                receipt = record_receipt(
                    scope=scope,
                    decision=action,
                    risk=decision["risk"],
                    reason=decision["reason"],
                    status="blocked",
                    agent=agent,
                    metadata=metadata,
                    async_write=True,
                )
                raise AIONBlockedError(
                    f"AION blocked {scope}: {decision['reason']} "
                    f"(receipt={receipt['receipt_id']})"
                )

            if action == "approval":
                if not _approval_enabled():
                    receipt = record_receipt(
                        scope=scope,
                        decision=action,
                        risk=decision["risk"],
                        reason="Approval required but approval mode is disabled",
                        status="approval_required",
                        agent=agent,
                        metadata=metadata,
                        async_write=True,
                    )
                    raise AIONApprovalRequired(
                        f"AION requires approval for {scope}. "
                        f"Set AION_REQUIRE_APPROVAL=true to enable CLI approval "
                        f"(receipt={receipt['receipt_id']})"
                    )

                approved = _approval_prompt(
                    scope=scope,
                    risk=decision["risk"],
                    reason=decision["reason"],
                    metadata=metadata,
                )
                if not approved:
                    receipt = record_receipt(
                        scope=scope,
                        decision=action,
                        risk=decision["risk"],
                        reason="Human approval denied",
                        status="denied",
                        agent=agent,
                        metadata=metadata,
                        async_write=True,
                    )
                    raise AIONApprovalRequired(
                        f"AION approval denied for {scope} "
                        f"(receipt={receipt['receipt_id']})"
                    )

            result = func(*args, **kwargs)
            elapsed_ms = round((time.perf_counter() - started) * 1000, 3)

            receipt = record_receipt(
                scope=scope,
                decision=action,
                risk=decision["risk"],
                reason=decision["reason"],
                status="allowed",
                agent=agent,
                metadata={**metadata, "elapsed_ms": elapsed_ms},
                async_write=True,
            )

            return {
                "aion": {
                    "decision": action,
                    "risk": decision["risk"],
                    "receipt_id": receipt["receipt_id"],
                    "elapsed_ms": elapsed_ms,
                },
                "result": result,
            }

        return wrapper

    return decorator
