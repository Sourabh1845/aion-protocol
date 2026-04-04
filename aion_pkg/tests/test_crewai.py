from aion.crewai_tool import AIONIssueTool, AIONEnforceTool, AIONRevokeTool

issue_tool = AIONIssueTool()
enforce_tool = AIONEnforceTool()
revoke_tool = AIONRevokeTool()

def test_crewai_issue_valid():
    result = issue_tool._run(scope="ops.read")
    assert "jti" in result
    assert result["scope"] == "ops.read"
    assert result["consumed"] == False
    print("CrewAI issue test PASSED")

def test_crewai_enforce_valid():
    auth = issue_tool._run(scope="ops.read")
    result = enforce_tool._run(jti=auth["jti"], scope="ops.read")
    assert result["status"] == "ENFORCED"
    print("CrewAI enforce test PASSED")

def test_crewai_replay_blocked():
    auth = issue_tool._run(scope="ops.read")
    enforce_tool._run(jti=auth["jti"], scope="ops.read")
    result = enforce_tool._run(jti=auth["jti"], scope="ops.read")
    assert result["error"] == "ENFORCEMENT_DENIED"
    print("CrewAI replay test PASSED")

def test_crewai_invalid_scope():
    result = issue_tool._run(scope="")
    assert "error" in result
    print("CrewAI invalid scope test PASSED")

def test_crewai_revoke():
    auth = issue_tool._run(scope="ops.read")
    result = revoke_tool._run(jti=auth["jti"])
    assert result["status"] == "REVOKED"
    print("CrewAI revoke test PASSED")