from aion.authority import issue, verify

def test_scope_escalation():
    auth = issue("ops.read")
    jti = auth["jti"]
    
    # ops.write maangna — block hona chahiye
    result = verify(jti, "ops.write")
    assert result["error"] == "SCOPE_MISMATCH"
    
    print("Scope escalation test PASSED")