from aion.authority import issue
from aion.delegation import delegate
from aion.enforce import enforce

print("=== AION Multi-Agent Delegation Demo ===\n")

# Root issues authority to Agent A
print("Step 1: Root issues authority to Agent A...")
agent_a_auth = issue("ops.read", issuer="root.system")
print(f"Agent A JTI: {agent_a_auth['jti']}")
print(f"Agent A Scope: {agent_a_auth['scope']}\n")

# Agent A delegates to Agent B
print("Step 2: Agent A delegates authority to Agent B...")
agent_b_auth = delegate(
    parent_jti=agent_a_auth["jti"],
    new_scope="ops.read",
    delegated_by="agent.A"
)
print(f"Agent B JTI: {agent_b_auth['jti']}")
print(f"Agent B Scope: {agent_b_auth['scope']}")
print(f"Agent B Parent: {agent_b_auth['parent']}\n")

# Agent B enforces its authority
print("Step 3: Agent B enforces its delegated authority...")
result = enforce(agent_b_auth["jti"], "ops.read")
print(f"Result: {result}\n")

# Agent B tries scope escalation
print("Step 4: Agent B tries scope escalation (ops.write)...")
escalation = delegate(
    parent_jti=agent_a_auth["jti"],
    new_scope="ops.write",
    delegated_by="agent.A"
)
print(f"Result: {escalation}\n")

print("=== Multi-agent delegation working! ===")