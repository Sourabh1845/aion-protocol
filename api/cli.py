# api/cli.py

import sys
import json
from api.authority import issue, verify
from api.enforce import enforce


def main():
    cmd = sys.argv[1]

    if cmd == "issue":
        scope = sys.argv[2]
        policy = json.loads(sys.argv[3]) if len(sys.argv) > 3 else None
        print(json.dumps(issue(scope, policy), indent=2))

    elif cmd == "verify":
        jti = sys.argv[2]
        scope = sys.argv[3]
        print(json.dumps(verify(jti, scope), indent=2))

    elif cmd == "enforce":
        jti = sys.argv[2]
        scope = sys.argv[3]
        try:
            print(json.dumps(enforce(jti, scope), indent=2))
        except Exception as e:
            print(json.dumps({"error": "ENFORCEMENT_DENIED", "reason": str(e)}, indent=2))


if __name__ == "__main__":
    main()
