from aion.langchain_tool import aion_issue, aion_enforce

print("=== AION + LangChain Demo ===\n")

# Agent authority issue karta hai
print("Step 1: Agent requests authority...")
auth = aion_issue.invoke({"scope": "ops.read"})
print(f"Authority issued: {auth['jti']}")
print(f"Scope: {auth['scope']}\n")

# Agent enforce karta hai before acting
print("Step 2: Agent enforces authority before acting...")
result = aion_enforce.invoke({"jti": auth["jti"], "scope": "ops.read"})
print(f"Result: {result}\n")

# Replay attack try karta hai
print("Step 3: Agent tries to act again (replay attack)...")
result2 = aion_enforce.invoke({"jti": auth["jti"], "scope": "ops.read"})
print(f"Result: {result2}\n")

print("=== AION governance working with LangChain tools ===")