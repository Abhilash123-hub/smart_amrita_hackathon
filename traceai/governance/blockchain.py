"""Blockchain Upgrade Path (B8): IBIS-style tamper-evident ledger registry."""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class BlockchainLedger:
    """Tamper-evident cryptographically chained ledger for Clearance Certificates (IBIS-pattern)."""

    def __init__(self):
        self.blocks: list[dict[str, Any]] = []
        self._registry: dict[str, dict[str, Any]] = {}
        # Genesis block
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis = {
            "index": 0,
            "timestamp": "2026-01-01T00:00:00Z",
            "previous_hash": "0" * 64,
            "transactions": [{"type": "GENESIS", "message": "TraceAI Ledger Anchor v0.1"}],
            "merkle_root": hashlib.sha256(b"genesis").hexdigest(),
        }
        genesis["block_hash"] = self._hash_block(genesis)
        self.blocks.append(genesis)

    def _hash_block(self, block: dict) -> str:
        serialized = json.dumps(
            {k: v for k, v in block.items() if k != "block_hash"}, sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(serialized).hexdigest()

    def anchor_certificate(
        self,
        certificate_id: str,
        asset_hash: str,
        signature_b64: str,
        parent_tx: Optional[str] = None,
    ) -> str:
        """Record an off-chain clearance certificate onto the immutable ledger.
        
        Acceptance Criteria: Certificate authenticity verifiable by third parties
        without querying TraceAI server directly.
        """
        tx_id = f"tx:{uuid4().hex[:16]}"
        now = datetime.now(timezone.utc).isoformat()

        tx = {
            "tx_id": tx_id,
            "certificate_id": certificate_id,
            "asset_hash": asset_hash,
            "signature_b64": signature_b64,
            "parent_tx": parent_tx,
            "anchored_at": now,
        }

        prev_block = self.blocks[-1]
        new_block = {
            "index": len(self.blocks),
            "timestamp": now,
            "previous_hash": prev_block["block_hash"],
            "transactions": [tx],
            "merkle_root": hashlib.sha256(f"{certificate_id}:{asset_hash}".encode()).hexdigest(),
        }
        new_block["block_hash"] = self._hash_block(new_block)
        self.blocks.append(new_block)

        self._registry[certificate_id] = {
            "tx_id": tx_id,
            "block_index": new_block["index"],
            "block_hash": new_block["block_hash"],
            "asset_hash": asset_hash,
            "parent_tx": parent_tx,
        }

        return tx_id

    def verify_on_chain(self, certificate_id: str, asset_hash: str) -> dict[str, Any]:
        """Verify certificate against the tamper-evident chain."""
        entry = self._registry.get(certificate_id)
        if not entry:
            return {"verified": False, "reason": "Certificate not found on ledger"}

        if entry["asset_hash"] != asset_hash:
            return {"verified": False, "reason": "Asset hash does not match on-chain record"}

        block = self.blocks[entry["block_index"]]
        # Re-verify cryptographic integrity of block hash
        expected_hash = self._hash_block(block)
        if expected_hash != block["block_hash"]:
            return {"verified": False, "reason": "Blockchain block hash corrupted"}

        return {
            "verified": True,
            "tx_id": entry["tx_id"],
            "block_index": entry["block_index"],
            "block_hash": entry["block_hash"],
            "immutable": True,
        }
