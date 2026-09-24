"""Legacy Groq + hosted-API demo (reference only).

Nothing is hardcoded: the hosted API needs a key you provide.

    set AION_API_KEY=<your-key>       # PowerShell: $env:AION_API_KEY='<your-key>'
    set GROQ_API_KEY=<your-groq-key>
    python -m aion.aion_demo

For a fully offline walkthrough (no keys, no network) use `aion demo`.
"""

import os

import requests
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

AION_BASE_URL = os.getenv("AION_BASE_URL", "https://aion-protocol.onrender.com")


def _api_key():
    key = os.getenv("AION_API_KEY")
    if not key:
        raise SystemExit(
            "AION_API_KEY is not set. This demo calls a hosted AION server, which "
            "requires an API key.\nSet it first, e.g.  set AION_API_KEY=<your-key>\n"
            "For an offline walkthrough run:  aion demo"
        )
    return key


def aion_issue(scope):
    r = requests.post(
        f"{AION_BASE_URL}/issue",
        json={"scope": scope, "issuer": "groq-agent"},
        headers={"X-AION-API-Key": _api_key()}
    )
    return r.json()

def aion_enforce(jti, scope):
    r = requests.post(
        f"{AION_BASE_URL}/enforce",
        json={"jti": jti, "scope": scope},
        headers={"X-AION-API-Key": _api_key()}
    )
    return r.json()

def run_demo():
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise SystemExit("GROQ_API_KEY is not set. Set it first, e.g.  set GROQ_API_KEY=<your-key>")
    client = Groq(api_key=groq_key)

    print("\n" + "="*55)
    print("AION PROTOCOL - GROQ AGENT INTEGRATION DEMO")
    print("="*55)

    print("\n[STEP 1] Agent requesting authority from AION...")
    scope = "read.weather.data"
    token = aion_issue(scope)
    print(f"  Token ID  : {token['jti']}")
    print(f"  Scope     : {token['scope']}")
    print(f"  Signed    : {'signature' in token}")
    print(f"  Expires   : {token['expires_at']}")

    print("\n[STEP 2] Enforcing authority token...")
    result = aion_enforce(token["jti"], scope)
    print(f"  Result    : {result.get('status', result.get('error'))}")

    if result.get("status") == "ENFORCED":
        print("\n[STEP 3] Authority granted - Agent executing action...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": "What is the weather like in monsoon season in Odisha, India? Answer in 2-3 lines."
            }]
        )
        print(f"\n  Agent Response:\n  {response.choices[0].message.content}")
    else:
        print("\n[BLOCKED] Authority denied - Agent cannot proceed.")

    print("\n[STEP 4] Replay attack test - reusing same token...")
    replay = aion_enforce(token["jti"], scope)
    print(f"  Replay Result : {replay.get('error', 'UNKNOWN')} - {replay.get('reason', '')}")

    print("\n" + "="*55)
    print("DEMO COMPLETE - AION successfully governed agent actions")
    print("="*55 + "\n")

if __name__ == "__main__":
    run_demo()