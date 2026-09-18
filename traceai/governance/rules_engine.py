"""Jurisdiction-Aware Rules Engine (B12): Configurable data-driven rules layer."""

import logging
from typing import Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class RuleDefinition(BaseModel):
    rule_id: str
    jurisdiction: str  # "EU", "US", "GLOBAL", or "*"
    min_confidence: float = 0.0
    max_confidence: float = 1.0
    require_tdm_opt_out: Optional[bool] = None
    target_trust_tiers: Optional[list[str]] = None
    outcome: str  # "BLOCKED", "HUMAN_REVIEW", "CLEAR"
    priority: int = 100


DEFAULT_RULES = [
    # EU Rule: Strict enforcement of TDM opt-out under EU DSM Art 4
    RuleDefinition(
        rule_id="EU_TDM_RESERVATION_BLOCK",
        jurisdiction="EU",
        min_confidence=0.75,
        max_confidence=0.90,
        require_tdm_opt_out=True,
        outcome="BLOCKED",
        priority=10,
    ),
    # US Rule: Fair-use mid-band routes to human review rather than instant block
    RuleDefinition(
        rule_id="US_FAIR_USE_MID_BAND",
        jurisdiction="US",
        min_confidence=0.75,
        max_confidence=0.88,
        require_tdm_opt_out=False,
        outcome="HUMAN_REVIEW",
        priority=20,
    ),
    # High-Risk Domain Rule across all jurisdictions
    RuleDefinition(
        rule_id="HIGH_RISK_DOMAIN_SENSITIVITY",
        jurisdiction="*",
        min_confidence=0.70,
        max_confidence=0.85,
        target_trust_tiers=["high-risk-domain"],
        outcome="HUMAN_REVIEW",
        priority=30,
    ),
]


class JurisdictionRulesEngine:
    """Evaluates contextual legal rules to resolve final status independently of raw model threshold."""

    def __init__(self, rules: Optional[list[RuleDefinition]] = None):
        self.rules = sorted(rules or DEFAULT_RULES, key=lambda r: r.priority)

    def add_rule(self, rule: RuleDefinition):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def evaluate_jurisdiction(
        self,
        jurisdiction: str,
        confidence_score: float,
        tdm_opted_out: bool = False,
        trust_tier: Optional[str] = None,
        default_outcome: str = "CLEAR",
    ) -> tuple[str, Optional[str]]:
        """Evaluate matching rules.
        
        Acceptance Criteria: The same asset with the same confidence score produces
        different outcomes under different configured jurisdiction rulesets.
        """
        for rule in self.rules:
            # Match jurisdiction
            if rule.jurisdiction != "*" and rule.jurisdiction.upper() != jurisdiction.upper():
                continue

            # Match confidence score range
            if not (rule.min_confidence <= confidence_score <= rule.max_confidence):
                continue

            # Match TDM opt-out requirement
            if rule.require_tdm_opt_out is not None and rule.require_tdm_opt_out != tdm_opted_out:
                continue

            # Match trust tier requirement
            if rule.target_trust_tiers and trust_tier not in rule.target_trust_tiers:
                continue

            logger.info("Rule matched: %s -> Outcome: %s", rule.rule_id, rule.outcome)
            return rule.outcome, rule.rule_id

        return default_outcome, None
