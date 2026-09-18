from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ClearanceCertificate(BaseModel):
    certificate_id: str
    asset_hash: str
    algorithm: str = "RSASSA-PSS-SHA256"
    signature_b64: str
    key_fingerprint: str
    issued_at: str

class ProvOGraph(BaseModel):
    context: str = Field(default="http://www.w3.org/ns/prov#", alias="@context")
    type: str = Field(default="Entity", alias="@type")
    wasGeneratedBy: str = Field(default="TraceAI:IngestionScanActivity", alias="prov:wasGeneratedBy")
    wasAssociatedWith: str = Field(default="TraceAI:GatewayAgent", alias="prov:wasAssociatedWith")
    endedAtTime: str = Field(alias="prov:endedAtTime")

class ThreatDiagnosis(BaseModel):
    matched_work: str
    similarity_score: float
    confidence_pct: str
    trigger_stage: str
    violations: List[str]

class AnalyzeResponse(BaseModel):
    scan_id: str
    filename: str
    detected_mime: str
    status: str  # "PASSED" or "BLOCKED"
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    similarity_score: float
    certificate: Optional[ClearanceCertificate] = None
    prov_o: Optional[Dict[str, Any]] = None
    threat_diagnosis: Optional[ThreatDiagnosis] = None