"""Clearance certificate and W3C PROV-O lineage schemas."""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ProvLineage(BaseModel):
    """Minimal W3C PROV-O JSON-LD representation of asset lineage."""

    model_config = ConfigDict(populate_by_name=True)

    context: str = Field(
        default="http://www.w3.org/ns/prov#",
        alias="@context",
        description="W3C PROV ontology context",
    )
    type: str = Field(
        default="prov:Entity",
        alias="@type",
        description="PROV-O entity type",
    )
    id: str = Field(
        alias="@id",
        description="URI identifier of the entity based on SHA-256 hash",
    )
    wasGeneratedBy: dict[str, Any] = Field(
        description="PROV Activity that produced or verified this asset",
    )
    wasDerivedFrom: Optional[str] = Field(
        default=None,
        description="Original source URI or file locator",
    )


class ClearanceCertificate(BaseModel):
    """Cryptographic clearance certificate issued to verified clean assets."""

    certificate_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique clearance certificate UUID",
    )
    asset_id: str = Field(description="Identifier of the cleared asset")
    asset_hash: str = Field(description="SHA-256 hash that was signed: 'sha256:<hex>'")
    issued_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of issuance in ISO 8601 format",
    )
    issuer: str = Field(
        default="TraceAI Clearance Gateway v0.1.0",
        description="Identity of the issuing authority",
    )
    signature_algorithm: str = Field(
        default="RSASSA-PSS-SHA256",
        description="Cryptographic signature algorithm",
    )
    signature_b64: str = Field(
        description="Base64 encoded RSA signature over the asset hash",
    )
    key_fingerprint: str = Field(
        description="SHA-256 fingerprint of the signing RSA public key",
    )
