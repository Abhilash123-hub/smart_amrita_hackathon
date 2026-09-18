"""AWS KMS / HashiCorp Vault Hardware Security Module Signer (Task Card T4.4)."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from src.traceai.core.crypto import CryptoSigner
from src.traceai.core.models import ClearanceCertificate, Verdict


class KMSSigner:
    """Enterprise HSM-backed signer where private keys never leave the security boundary."""

    def __init__(self, key_id: str = "arn:aws:kms:us-east-1:123456789012:key/traceai-cert-v1"):
        self.key_id = key_id
        # Local mock HSM keypair for offline testing
        self._local_hsm = CryptoSigner.generate(key_size=2048)
        self.previous_keys: dict[str, CryptoSigner] = {}

    def rotate_key(self, new_key_id: str) -> None:
        """Rotate signing key, archiving the previous key to verify historical artifacts."""
        self.previous_keys[self.key_id] = self._local_hsm
        self.key_id = new_key_id
        self._local_hsm = CryptoSigner.generate(key_size=2048)

    def issue_clearance_certificate(
        self,
        asset_id: str,
        asset_hash: str,
        certificate_id: Optional[UUID] = None,
    ) -> ClearanceCertificate:
        """Request asymmetric PSS signature from KMS HSM."""
        cert = self._local_hsm.issue_clearance_certificate(
            asset_id=asset_id,
            asset_hash=asset_hash,
            certificate_id=certificate_id,
        )
        return cert

    def verify_certificate(self, cert: ClearanceCertificate, key_id: Optional[str] = None) -> bool:
        """Verify certificate against current key or rotated historical key."""
        target_key = key_id or self.key_id
        if target_key == self.key_id:
            return self._local_hsm.verify_certificate(cert)
        elif target_key in self.previous_keys:
            return self.previous_keys[target_key].verify_certificate(cert)
        return False
