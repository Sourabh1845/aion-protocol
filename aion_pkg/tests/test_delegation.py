from aion.authority import issue
from aion.delegation import delegate
from aion.enforce import enforce

def test_3_level_chain():
    # Root → Agent A
    agent_a = issue("ops.read", issuer="root.system")
    assert "jti" in agent_a

    # Agent A → Agent B
    agent_b = delegate(agent_a["jti"], "ops.read", "agent.A")
    assert "jti" in agent_b
    assert agent_b["parent"] == agent_a["jti"]

    # Agent B → Agent C
    agent_c = delegate(agent_b["jti"], "ops.read", "agent.B")
    assert "jti" in agent_c
    assert agent_c["parent"] == agent_b["jti"]

    # Agent C enforces
    result = enforce(agent_c["jti"], "ops.read")
    assert result["status"] == "ENFORCED"
    print("3-level chain test PASSED")

def test_max_depth_blocked():
    agent_a = issue("ops.read", issuer="root.system")
    agent_b = delegate(agent_a["jti"], "ops.read", "agent.A")
    agent_c = delegate(agent_b["jti"], "ops.read", "agent.B")
    agent_d = delegate(agent_c["jti"], "ops.read", "agent.C")
    assert "error" in agent_d
    assert "MAX_DEPTH" in agent_d["error"]
    print("Max depth blocked test PASSED")

def test_scope_escalation_blocked():
    agent_a = issue("ops.read", issuer="root.system")
    result = delegate(agent_a["jti"], "ops.write", "agent.A")
    assert "error" in result
    assert "SCOPE_VIOLATION" in result["error"]
    print("Scope escalation blocked test PASSED")

def test_expiry_propagation():
    agent_a = issue("ops.read", issuer="root.system")
    agent_b = delegate(agent_a["jti"], "ops.read", "agent.A")
    # Child expiry cannot exceed parent expiry
    from datetime import datetime, timezone
    parent_expiry = datetime.fromisoformat(agent_a["expires_at"])
    child_expiry = datetime.fromisoformat(agent_b["expires_at"])
    assert child_expiry <= parent_expiry
    print("Expiry propagation test PASSED")