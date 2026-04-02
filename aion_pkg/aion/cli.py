import sys
import json
from aion.authority import issue, verify, revoke
from aion.enforce import enforce

def main():
    if len(sys.argv) < 2:
        print("Usage: aion <command> [args]")
        print("Commands: issue <scope> | verify <jti> <scope> | enforce <jti> <scope> | revoke <jti>")
        return

    cmd = sys.argv[1]

    if cmd == "issue":
        scope = sys.argv[2] if len(sys.argv) > 2 else "default"
        result = issue(scope)
        print(json.dumps(result, indent=2))

    elif cmd == "verify":
        jti = sys.argv[2]
        scope = sys.argv[3]
        print(json.dumps(verify(jti, scope), indent=2))

    elif cmd == "enforce":
        jti = sys.argv[2]
        scope = sys.argv[3]
        print(json.dumps(enforce(jti, scope), indent=2))

    elif cmd == "revoke":
        jti = sys.argv[2]
        print(json.dumps(revoke(jti), indent=2))

    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()