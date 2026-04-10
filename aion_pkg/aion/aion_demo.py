import requests
from google import genai

AION_BASE_URL = "https://aion-protocol.onrender.com"
AION_API_KEY = "aion-prod-key-2026"
GEMINI_API_KEY = "AIzaSyBEcs5MRSfqY0iFDXF4gEgjPpORr27vJNE"

client = genai.Client(api_key=GEMINI_API_KEY)

def aion_issue(scope):
    r = requests.post(
        f"{AION_BASE_URL}/issue",
        json={"scope": scope, "issuer": "gemini-agent"},
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
    print("\n" + "="*50)
    print("AION PROTOCOL - GEMINI AGENT DEMO")
    print("="*50)

    print("\n[STEP 1] Gemini Agent permission maang raha hai AION se...")
    scope = "read.weather.data"
    token = aion_issue(scope)
    print(f"Token issued: {token['jti']}")
    print(f"Signed: {'signature' in token}")

    print("\n[STEP 2] AION enforce kar raha hai...")
    result = aion_enforce(token["jti"], scope)
    print(f"Result: {result}")

    if result.get("status") == "ENFORCED":
        print("\n[STEP 3] Permission mili - Gemini action kar raha hai...")
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Monsoon in Odisha India in 2 lines."
        )
        print(f"\nGemini Response:\n{response.text}")
    else:
        print("\n[BLOCKED] Permission nahi mili.")

    print("\n[STEP 4] Replay attack test...")
    replay = aion_enforce(token["jti"], scope)
    print(f"Replay: {replay}")
    print("\nDEMO COMPLETE")

run_demo()