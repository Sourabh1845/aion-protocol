from aion.langchain_tool import aion_issue, aion_enforce, aion_revoke

def test_langchain_issue_valid():
    result = aion_issue.invoke({"scope": "ops.read"})
    assert "jti" in result
    assert result["scope"] == "ops.read"
    assert result["consumed"] == False
    print("LangChain issue test PASSED")

def test_langchain_enforce_valid():
    auth = aion_issue.invoke({"scope": "ops.read"})
    result = aion_enforce.invoke({"jti": auth["jti"], "scope": "ops.read"})
    assert result["status"] == "ENFORCED"
    print("LangChain enforce test PASSED")

def test_langchain_replay_blocked():
    auth = aion_issue.invoke({"scope": "ops.read"})
    aion_enforce.invoke({"jti": auth["jti"], "scope": "ops.read"})
    result = aion_enforce.invoke({"jti": auth["jti"], "scope": "ops.read"})
    assert result["error"] == "ENFORCEMENT_DENIED"
    print("LangChain replay test PASSED")

def test_langchain_invalid_scope():
    result = aion_issue.invoke({"scope": ""})
    assert "error" in result
    print("LangChain invalid scope test PASSED")

def test_langchain_revoke():
    auth = aion_issue.invoke({"scope": "ops.read"})
    result = aion_revoke.invoke({"jti": auth["jti"]})
    assert result["status"] == "REVOKED"
    print("LangChain revoke test PASSED")