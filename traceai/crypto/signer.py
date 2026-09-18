from __future__ import annotations

"""Cryptographic signing and certificate verification using RSA."""

import base64
import hashlib
from pathlib import Path
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from traceai.schemas.certificate import ClearanceCertificate


class CryptoSigner:
    """Manages RSA keys and generates cryptographic clearance certificates."""

    def __init__(
        self,
        private_key: Optional[rsa.RSAPrivateKey] = None,
        public_key: Optional[rsa.RSAPublicKey] = None,
    ):
        if private_key is None and public_key is None:
            # Auto-generate a new 2048-bit RSA keypair if none provided
            self._private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            self._public_key = self._private_key.public_key()
        else:
            self._private_key = private_key
            self._public_key = public_key or (private_key.public_key() if private_key else None)

    @classmethod
    def generate(cls, key_size: int = 2048) -> "CryptoSigner":
        """Generate a new RSA keypair."""
        priv_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        return cls(private_key=priv_key)

    @classmethod
    def load_from_files(
        cls,
        private_key_path: Optional[Path | str] = None,
        public_key_path: Optional[Path | str] = None,
        password: Optional[bytes] = None,
    ) -> "CryptoSigner":
        """Load private and/or public keys from PEM files."""
        priv_key = None
        pub_key = None

        if private_key_path:
            p_priv = Path(private_key_path)
            if p_priv.exists():
                pem_data = p_priv.read_bytes()
                priv_key = serialization.load_pem_private_key(pem_data, password=password)
                if isinstance(priv_key, rsa.RSAPrivateKey):
                    pub_key = priv_key.public_key()

        if public_key_path and pub_key is None:
            p_pub = Path(public_key_path)
            if p_pub.exists():
                pem_data = p_pub.read_bytes()
                loaded_pub = serialization.load_pem_public_key(pem_data)
                if isinstance(loaded_pub, rsa.RSAPublicKey):
                    pub_key = loaded_pub

        return cls(private_key=priv_key, public_key=pub_key)

    def save_keys(
        self,
        directory: Path | str,
        private_name: str = "traceai_private.pem",
        public_name: str = "traceai_public.pem",
    ) -> tuple[Path, Path]:
        """Save the private and public keys to PEM files in the specified directory."""
        dir_path = Path(directory).resolve()
        dir_path.mkdir(parents=True, exist_ok=True)

        priv_path = dir_path / private_name
        pub_path = dir_path / public_name

        if self._private_key:
            priv_pem = self._private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            priv_path.write_bytes(priv_pem)

        if self._public_key:
            pub_pem = self._public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
            pub_path.write_bytes(pub_pem)

        return priv_path, pub_path

    @property
    def public_key_pem(self) -> str:
        """Export public key as PEM encoded string."""
        if not self._public_key:
            raise ValueError("Public key is not available.")
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")

    @property
    def key_fingerprint(self) -> str:
        """SHA-256 fingerprint of the SubjectPublicKeyInfo DER encoding."""
        if not self._public_key:
            return "unknown"
        der = self._public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return f"sha256:{hashlib.sha256(der).hexdigest()}"

    def sign_hash(self, asset_hash: str) -> str:
        """Sign an asset hash string using RSA-PSS with SHA-256, returning base64 string."""
        if not self._private_key:
            raise RuntimeError("Private key is required to sign asset hashes.")

        signature = self._private_key.sign(
            data=asset_hash.encode("utf-8"),
            padding=padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            algorithm=hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("ascii")

    def verify_signature(self, asset_hash: str, signature_b64: str) -> bool:
        """Verify an RSA-PSS signature against the public key."""
        if not self._public_key:
            raise RuntimeError("Public key is required to verify signatures.")

        try:
            raw_sig = base64.b64decode(signature_b64.encode("ascii"))
            self._public_key.verify(
                signature=raw_sig,
                data=asset_hash.encode("utf-8"),
                padding=padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                algorithm=hashes.SHA256(),
            )
            return True
        except (InvalidSignature, ValueError):
            return False

    def issue_certificate(self, asset_id: str, asset_hash: str) -> ClearanceCertificate:
        """Create and cryptographically sign a ClearanceCertificate for a clean asset."""
        signature_b64 = self.sign_hash(asset_hash)
        return ClearanceCertificate(
            asset_id=asset_id,
            asset_hash=asset_hash,
            signature_algorithm="RSASSA-PSS-SHA256",
            signature_b64=signature_b64,
            key_fingerprint=self.key_fingerprint,
        )
