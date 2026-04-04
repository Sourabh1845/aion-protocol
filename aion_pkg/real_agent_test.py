from aion.authority import issue
from aion.enforce import enforce
from aion.delegation import delegate
import time

print("=" * 60)
print("AION REAL WORLD AGENT TEST")
print("=" * 60)

# ============================================
# SCENARIO 1: Single Agent — File Read Task
# ============================================
print("\n--- SCENARIO 1: Single Agent File Read ---")

class FileReaderAgent:
    def __init__(self, name):
        self.name = name

    def run(self, task):
        print(f"\n[{self.name}] Task received: {task}")
        
        # Step 1: Request authority
        print(f"[{self.name}] Requesting authority from AION...")
        auth = issue("file.read", issuer=self.name)
        print(f"[{self.name}] Authority received: {auth['jti']}")
        
        # Step 2: Enforce before acting
        print(f"[{self.name}] Enforcing authority before action...")
        result = enforce(auth["jti"], "file.read")
        
        if result.get("status") == "ENFORCED":
            print(f"[{self.name}] ALLOWED — Executing task: {task}")
            return f"Task completed: {task}"
        else:
            print(f"[{self.name}] DENIED — Cannot execute: {result}")
            return None

agent = FileReaderAgent("Agent-FileReader")
agent.run("Read customer_data.csv")

# ============================================
# SCENARIO 2: Agent tries unauthorized action
# ============================================
print("\n--- SCENARIO 2: Unauthorized Action Attempt ---")

class RogueAgent:
    def __init__(self, name):
        self.name = name

    def run(self, task):
        print(f"\n[{self.name}] Task received: {task}")
        
        # Gets read permission but tries write
        print(f"[{self.name}] Requesting READ authority...")
        auth = issue("file.read", issuer=self.name)
        
        print(f"[{self.name}] Trying to WRITE with READ token...")
        result = enforce(auth["jti"], "file.write")
        
        if result.get("status") == "ENFORCED":
            print(f"[{self.name}] ALLOWED — This should not happen!")
        else:
            print(f"[{self.name}] BLOCKED by AION — {result['reason']}")

rogue = RogueAgent("Agent-Rogue")
rogue.run("Write malicious_data.csv")

# ============================================
# SCENARIO 3: Multi-Agent — Manager delegates to Worker
# ============================================
print("\n--- SCENARIO 3: Multi-Agent Delegation ---")

class ManagerAgent:
    def __init__(self, name):
        self.name = name
        self.auth = None

    def get_authority(self):
        print(f"\n[{self.name}] Getting root authority...")
        self.auth = issue("ops.read", issuer="root.system")
        print(f"[{self.name}] Authority: {self.auth['jti']}")

    def delegate_to_worker(self, worker):
        print(f"[{self.name}] Delegating to {worker.name}...")
        delegated = delegate(
            parent_jti=self.auth["jti"],
            new_scope="ops.read",
            delegated_by=self.name
        )
        worker.auth = delegated
        print(f"[Worker] Delegated authority: {delegated['jti']}")

class WorkerAgent:
    def __init__(self, name):
        self.name = name
        self.auth = None

    def execute(self, task):
        print(f"[{self.name}] Enforcing delegated authority...")
        result = enforce(self.auth["jti"], "ops.read")
        
        if result.get("status") == "ENFORCED":
            print(f"[{self.name}] ALLOWED — Executing: {task}")
        else:
            print(f"[{self.name}] DENIED — {result}")

manager = ManagerAgent("Manager-Agent")
worker = WorkerAgent("Worker-Agent")

manager.get_authority()
manager.delegate_to_worker(worker)
worker.execute("Process customer records")

# ============================================
# SCENARIO 4: Replay Attack
# ============================================
print("\n--- SCENARIO 4: Replay Attack Prevention ---")

auth = issue("payment.execute", issuer="payment-agent")
jti = auth["jti"]

print(f"\nFirst use — should ALLOW:")
r1 = enforce(jti, "payment.execute")
print(f"Result: {r1}")

print(f"\nSecond use — should BLOCK:")
r2 = enforce(jti, "payment.execute")
print(f"Result: {r2}")

print("\n" + "=" * 60)
print("ALL SCENARIOS COMPLETE")
print("=" * 60)