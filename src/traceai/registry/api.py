"""Public Fingerprint Registry API for Rightsholder Submissions & Attestation (Task Card T4.7)."""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class RightsholderSubmission(BaseModel):
    submission_id: str
    rightsholder_name: str
    contact_email: str
    work_title: str
    fingerprint_hash: str  # sha256 or pHash
    track: str  # TEXT, IMAGE, AUDIO, VIDEO, CODE
    attestation_statement: str
    revoked: bool = False
    submitted_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class FingerprintRegistry:
    """Registry allowing rightsholders to submit and revoke copyright fingerprints."""

    def __init__(self):
        self._submissions: dict[str, RightsholderSubmission] = {}

    def submit_work(self, submission: RightsholderSubmission) -> str:
        self._submissions[submission.submission_id] = submission
        return submission.submission_id

    def revoke_work(self, submission_id: str) -> bool:
        if submission_id in self._submissions:
            self._submissions[submission_id].revoked = True
            return True
        return False

    def is_fingerprint_registered(self, fingerprint_hash: str) -> bool:
        """Check if fingerprint is actively registered (not revoked)."""
        for s in self._submissions.values():
            if s.fingerprint_hash == fingerprint_hash and not s.revoked:
                return True
        return False
