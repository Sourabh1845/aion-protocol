from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from aion.authority import issue
from aion.enforce import enforce
from aion.delegation import delegate

print("=" * 60)
print("AION MULTI-AGENT REAL TEST (Llama3.2)")
print("=" * 60)

llm = ChatOllama(model="llama3.2")

# ============================================
# MANAGER AGENT
# ============================================
class ManagerAgent:
    def __init__(self):
        self.name = "Manager-Agent"
        self.auth = None
        self.llm = llm

    def think(self, task):
        response = self.llm.invoke([
            SystemMessage(content="You are a manager AI agent. You manage tasks and delegate to workers."),
            HumanMessage(content=task)
        ])
        return response.content

    def get_authority(self):
        print(f"\n[{self.name}] Requesting authority from AION...")
        self.auth = issue("ops.read", issuer="root.system")
        print(f"[{self.name}] Authority received: {self.auth['jti']}")
        
        thought = self.think("I just received authority to read operations data. What should I do next?")
        print(f"[{self.name}] Thinking: {thought[:100]}...")
        return self.auth

    def delegate_to_worker(self, worker):
        print(f"\n[{self.name}] Delegating authority to {worker.name}...")
        delegated = delegate(
            parent_jti=self.auth["jti"],
            new_scope="ops.read",
            delegated_by=self.name
        )
        
        if "error" in delegated:
            print(f"[{self.name}] DELEGATION FAILED: {delegated['error']}")
            return None
            
        worker.auth = delegated
        print(f"[{self.name}] Delegation successful: {delegated['jti']}")
        return delegated

# ============================================
# WORKER AGENT
# ============================================
class WorkerAgent:
    def __init__(self):
        self.name = "Worker-Agent"
        self.auth = None
        self.llm = llm

    def think(self, task):
        response = self.llm.invoke([
            SystemMessage(content="You are a worker AI agent. You execute specific tasks assigned by manager."),
            HumanMessage(content=task)
        ])
        return response.content

    def execute(self, task):
        print(f"\n[{self.name}] Received task: {task}")
        
        if not self.auth:
            print(f"[{self.name}] BLOCKED — No authority!")
            return

        print(f"[{self.name}] Enforcing authority with AION...")
        result = enforce(self.auth["jti"], "ops.read")

        if result.get("status") == "ENFORCED":
            thought = self.think(f"I have been authorized to execute: {task}. How should I proceed?")
            print(f"[{self.name}] ALLOWED — Thinking: {thought[:100]}...")
            print(f"[{self.name}] Task completed: {task}")
        else:
            print(f"[{self.name}] BLOCKED by AION: {result}")

# ============================================
# RUN MULTI-AGENT TEST
# ============================================
print("\n--- Step 1: Manager gets root authority ---")
manager = ManagerAgent()
manager.get_authority()

print("\n--- Step 2: Manager delegates to Worker ---")
worker = WorkerAgent()
manager.delegate_to_worker(worker)

print("\n--- Step 3: Worker executes with delegated authority ---")
worker.execute("Process customer records from ops database")

print("\n--- Step 4: Replay attack test ---")
print(f"\n[{worker.name}] Trying same token again...")
result = enforce(worker.auth["jti"], "ops.read")
if "error" in result:
    print(f"[{worker.name}] BLOCKED by AION — Replay prevented: {result['reason']}")

print("\n" + "=" * 60)
print("MULTI-AGENT TEST COMPLETE")
print("=" * 60)