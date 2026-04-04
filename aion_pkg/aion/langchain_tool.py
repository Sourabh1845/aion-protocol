from langchain_core.tools import tool
from aion.authority import issue
from aion.enforce import enforce

@tool
def aion_issue(scope: str) -> dict:
    """Issue an AION authority token for a given scope before agent acts."""
    return issue(scope)

@tool
def aion_enforce(jti: str, scope: str) -> dict:
    """Enforce an AION authority token — agent must present valid token to act."""
    return enforce(jti, scope)