"""Cryptographic Evidence Signing & Verification Layer (Task Card T2.1)."""

import base64
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Union
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from src.traceai.core.models import ClearanceCertificate, Verdict


def hash_asset_bytes(raw_bytes: bytes) -> str:
    """Compute standard content-addressable SHA-256 digest."""
    digest = hashlib.sha256(raw_bytes).hexdigest()
    return f"sha256:{digest}"


def canonicalize_json(data: dict) -> bytes:
    """Produce deterministic canonical JSON UTF-8 byte stream (RFC 8785 style)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class CryptoSigner:
    """RSA-2048 PSS signer and verifier for Clearance Certificates."""

    def __init__(
        self,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        public_key: Optional[rsa.RSAPublicKey] = None,
    ):
        self._private_key = private_key
        if public_key is not None:
            self._public_key = public_key
        elif private_key is not None:
            self._public_key = private_key.public_key()
        else:
            self._public_key = None

    @classmethod
    def generate(cls, key_size: int = 2048) -> "CryptoSigner":
        """Generate a fresh RSA keypair."""
        priv = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
        return cls(private_key=priv)

    @classmethod
    def load_from_pem(
        cls,
        private_pem: Optional[str] = None,
        public_pem: Optional[str] = None,
    ) -> "CryptoSigner":
        """Load signer from PEM strings."""
        priv = None
        pub = None
        if private_pem:
            priv = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
        if public_pem:
            pub = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        return cls(private_key=priv, public_key=pub)

    def export_public_key_pem(self) -> str:
        """Export public key as PEM string."""
        if not self._public_key:
            raise ValueError("No public key available")
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

    def sign_canonical(self, canonical_bytes: bytes) -> str:
        """Sign canonical bytes with RSA-PSS SHA-256 and MAX_LENGTH salt."""
        if not self._private_key:
            raise ValueError("Cannot sign without private key")

        signature = self._private_key.sign(
            canonical_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def verify_canonical(self, canonical_bytes: bytes, signature_b64: str) -> bool:
        """Verify RSA-PSS signature against canonical bytes."""
        if not self._public_key:
            raise ValueError("Cannot verify without public key")

        try:
            sig_bytes = base64.b64decode(signature_b64)
            self._public_key.verify(
                sig_bytes,
                canonical_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except (InvalidSignature, Exception):
            return False

    def issue_clearance_certificate(
        self,
        asset_id: str,
        asset_hash: str,
        certificate_id: Optional[UUID] = None,
        issued_at: Optional[datetime] = None,
    ) -> ClearanceCertificate:
        """Issue an RSA-PSS signed clearance certificate over canonical JSON."""
        cert_id = certificate_id or uuid4()
        now = issued_at or datetime.now(timezone.utc)

        # Unsigned payload dictionary for signing
        payload = {
            "certificate_id": str(cert_id),
            "asset_id": asset_id,
            "asset_hash": asset_hash,
            "verdict": Verdict.PASSED.value,
            "issued_at": now.isoformat(),
        }
        canonical_bytes = canonicalize_json(payload)
        sig = self.sign_canonical(canonical_bytes)

        return ClearanceCertificate(
            certificate_id=cert_id,
            asset_id=asset_id,
            asset_hash=asset_hash,
            verdict=Verdict.PASSED,
            issued_at=now,
            rsa_signature=sig,
        )

    def verify_certificate(self, cert: ClearanceCertificate) -> bool:
        """Verify an issued clearance certificate against its signature."""
        payload = {
            "certificate_id": str(cert.certificate_id),
            "asset_id": cert.asset_id,
            "asset_hash": cert.asset_hash,
            "verdict": cert.verdict.value if hasattr(cert.verdict, "value") else cert.verdict,
            "issued_at": cert.issued_at.isoformat(),
        }
        canonical_bytes = canonicalize_json(payload)
        return self.verify_canonical(canonical_bytes, cert.rsa_signature)
