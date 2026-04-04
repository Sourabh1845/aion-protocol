from aion.crewai_tool import AIONIssueTool, AIONEnforceTool

print("=== AION + CrewAI Demo ===\n")

issue_tool = AIONIssueTool()
enforce_tool = AIONEnforceTool()

# Agent authority issue karta hai
print("Step 1: Agent requests authority...")
auth = issue_tool._run(scope="ops.write")
print(f"Authority issued: {auth['jti']}")
print(f"Scope: {auth['scope']}\n")

# Agent enforce karta hai before acting
print("Step 2: Agent enforces authority before acting...")
result = enforce_tool._run(jti=auth["jti"], scope="ops.write")
print(f"Result: {result}\n")

# Replay attack
print("Step 3: Agent tries replay attack...")
result2 = enforce_tool._run(jti=auth["jti"], scope="ops.write")
print(f"Result: {result2}\n")

print("=== AION governance working with CrewAI tools ===")