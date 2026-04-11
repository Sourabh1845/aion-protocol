import requests
from groq import Groq
from dotenv import load_dotenv
import os
load_dotenv()

AION_BASE_URL = "https://aion-protocol.onrender.com"
AION_API_KEY = "aion-prod-key-2026"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def aion_issue(scope):
    r = requests.post(
        f"{AION_BASE_URL}/issue",
        json={"scope": scope, "issuer": "groq-agent"},
        headers={"X-AION-API-Key": AION_API_KEY}
    )
    return r.json()

def aion_enforce(jti, scope):
    r = requests.post(
        f"{AION_BASE_URL}/enforce",
        json={"jti": jti, "scope": scope},
        headers={"X-AION-API-Key": AION_API_KEY}
    )
    return r.json()

def run_demo():
    print("\n" + "="*55)
    print("AION PROTOCOL — GROQ AGENT INTEGRATION DEMO")
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
        print("\n[STEP 3] Authority granted — Agent executing action...")
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{
                "role": "user",
                "content": "What is the weather like in monsoon season in Odisha, India? Answer in 2-3 lines."
            }]
        )
        print(f"\n  Agent Response:\n  {response.choices[0].message.content}")
    else:
        print("\n[BLOCKED] Authority denied — Agent cannot proceed.")

    print("\n[STEP 4] Replay attack test — reusing same token...")
    replay = aion_enforce(token["jti"], scope)
    print(f"  Replay Result : {replay.get('error', 'UNKNOWN')} — {replay.get('reason', '')}")

    print("\n" + "="*55)
    print("DEMO COMPLETE — AION successfully governed agent actions")
    print("="*55 + "\n")

run_demo()