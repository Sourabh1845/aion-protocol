from aion.authority import issue, verify
from aion.storage import get_conn
from datetime import datetime, timezone

def test_expiry():
    auth = issue("ops.read")
    jti = auth["jti"]
    
    # Manually expire karo
    conn = get_conn()
    conn.execute(
        "UPDATE authorities SET expires_at=? WHERE jti=?",
        ("2020-01-01T00:00:00+00:00", jti)
    )
    conn.commit()
    conn.close()
    
    # Ab verify karo — expired hona chahiye
    result = verify(jti, "ops.read")
    assert result["error"] == "EXPIRED"
    
    print("Expiry test PASSED")