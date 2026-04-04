from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from aion.authority import issue
from aion.enforce import enforce

print("=" * 60)
print("AION + REAL AI AGENT TEST (Llama3.2)")
print("=" * 60)

llm = ChatOllama(model="llama3.2")

@tool
def request_and_enforce_authority(scope: str) -> str:
    """Request and enforce AION authority before performing any action."""
    auth = issue(scope)
    result = enforce(auth["jti"], scope)
    if result.get("status") == "ENFORCED":
        return f"AUTHORITY GRANTED for scope: {scope}, JTI: {auth['jti']}"
    else:
        return f"AUTHORITY DENIED: {result}"

@tool
def read_file(filename: str) -> str:
    """Read a file. Requires file.read authority from AION first."""
    return f"File content of {filename}: [sample data row 1, row 2, row 3]"

@tool
def write_file(filename: str, content: str) -> str:
    """Write to a file. Requires file.write authority from AION first."""
    return f"Written to {filename}: {content}"

tools = [request_and_enforce_authority, read_file, write_file]

agent = create_react_agent(llm, tools)

print("\n--- Test: Agent reads a file with AION governance ---\n")

result = agent.invoke({
    "messages": [
        ("user", "You must call request_and_enforce_authority with scope 'file.read' FIRST, then read the file called sales_data.csv")
    ]
})

print("\nAgent Response:")
for msg in result["messages"]:
    if hasattr(msg, "content") and msg.content:
        print(f"{msg.__class__.__name__}: {msg.content}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)