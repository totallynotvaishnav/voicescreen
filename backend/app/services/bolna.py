import logging
import httpx
from app.config import get_settings

logger = logging.getLogger(__name__)


class BolnaAPIError(Exception):
    """Raised when the Bolna API returns an error."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Bolna API error ({status_code}): {detail}")


class BolnaService:
    """Client for the Bolna Voice AI API."""

    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.BOLNA_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.settings.BOLNA_API_KEY}",
            "Content-Type": "application/json",
        }

    async def make_call(
        self, phone_number: str, candidate_name: str, job_title: str = ""
    ) -> dict:
        """Initiate an outbound call via Bolna.

        Args:
            phone_number: Recipient phone number (E.164 format, e.g. +91...)
            candidate_name: Candidate's name (for logging)
            job_title: Job title (for logging)

        Returns:
            dict with execution_id, run_id, status from Bolna API

        Raises:
            BolnaAPIError: If the API returns a non-200 status
        """
        payload = {
            "agent_id": self.settings.BOLNA_AGENT_ID,
            "recipient_phone_number": phone_number,
            "user_data": {
                "name": candidate_name,
                "job_title": job_title
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/call",
                json=payload,
                headers=self.headers,
            )
            if response.status_code != 200:
                raise BolnaAPIError(response.status_code, response.text)

            data = response.json()
            logger.info(
                f"Call initiated for {candidate_name}: execution_id={data.get('execution_id')}")
            return data

    async def get_execution(self, execution_id: str) -> dict:
        """Get execution details for a call."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/executions/{execution_id}",
                headers=self.headers,
            )
            if response.status_code != 200:
                raise BolnaAPIError(response.status_code, response.text)
            return response.json()
