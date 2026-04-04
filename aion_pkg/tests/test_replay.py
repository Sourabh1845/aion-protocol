from aion.authority import issue, verify

def test_replay_attack():
    auth = issue("ops.read")
    jti = auth["jti"]
    
    # Pehli baar — pass hona chahiye
    result1 = verify(jti, "ops.read")
    assert result1["status"] == "OK"
    
    # Doosri baar — block hona chahiye
    result2 = verify(jti, "ops.read")
    assert result2["error"] == "CONSUMED"
    
    print("Replay attack test PASSED")