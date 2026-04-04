from crewai.tools import BaseTool
from aion.authority import issue, revoke
from aion.enforce import enforce
from aion.storage import get_authority
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

class AIONIssueTool(BaseTool):
    name: str = "AION Issue Authority"
    description: str = "Issue an AION authority token before agent acts."

    def _run(self, scope: str) -> dict:
        try:
            if not scope or not isinstance(scope, str):
                return {"error": "INVALID_SCOPE", "detail": "Scope must be non-empty string"}
            result = issue(scope)
            logger.info(f"Authority issued: {result['jti']} for scope: {scope}")
            return result
        except Exception as e:
            logger.error(f"Failed to issue authority: {str(e)}")
            return {"error": "ISSUE_FAILED", "detail": str(e)}

class AIONEnforceTool(BaseTool):
    name: str = "AION Enforce Authority"
    description: str = "Enforce AION token — agent must present valid token to act."

    def _run(self, jti: str, scope: str) -> dict:
        try:
            if not jti or not scope:
                return {"error": "INVALID_INPUT", "detail": "JTI and scope are required"}
            auth = get_authority(jti)
            if not auth:
                return {"error": "NOT_FOUND", "detail": f"No authority found for JTI: {jti}"}
            if datetime.fromisoformat(auth["expires_at"]) < datetime.now(timezone.utc):
                return {"error": "EXPIRED", "detail": "Authority token has expired"}
            result = enforce(jti, scope)
            logger.info(f"Authority enforced: {jti} for scope: {scope}")
            return result
        except Exception as e:
            logger.error(f"Failed to enforce authority: {str(e)}")
            return {"error": "ENFORCE_FAILED", "detail": str(e)}

class AIONRevokeTool(BaseTool):
    name: str = "AION Revoke Authority"
    description: str = "Revoke an AION authority token immediately."

    def _run(self, jti: str) -> dict:
        try:
            if not jti:
                return {"error": "INVALID_INPUT", "detail": "JTI is required"}
            auth = get_authority(jti)
            if not auth:
                return {"error": "NOT_FOUND", "detail": f"No authority found for JTI: {jti}"}
            result = revoke(jti)
            logger.info(f"Authority revoked: {jti}")
            return result
        except Exception as e:
            logger.error(f"Failed to revoke authority: {str(e)}")
            return {"error": "REVOKE_FAILED", "detail": str(e)}