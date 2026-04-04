from crewai.tools import BaseTool
from aion.authority import issue
from aion.enforce import enforce

class AIONIssueTool(BaseTool):
    name: str = "AION Issue Authority"
    description: str = "Issue an AION authority token before agent acts."

    def _run(self, scope: str) -> dict:
        return issue(scope)

class AIONEnforceTool(BaseTool):
    name: str = "AION Enforce Authority"
    description: str = "Enforce AION token — agent must present valid token to act."

    def _run(self, jti: str, scope: str) -> dict:
        return enforce(jti, scope)