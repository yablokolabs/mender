"""Nano-tier triage: reduce raw cluster evidence to signals, suspects, search queries."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mender.evidence import ClusterEvidence
from mender.modelio import complete_json
from mender.router.client import Message, ModelClient

SEVERITIES = ("critical", "high", "medium", "low", "unknown")

_TRIAGE_SYSTEM = (
    "You are the triage stage of a Kubernetes incident agent. You receive raw cluster "
    "evidence (pod lines, events, describe output, logs, manifests). Identify what is "
    "broken and where to look next. Respond with ONLY a JSON object of this shape:\n"
    '{"summary": str, "severity": "critical"|"high"|"medium"|"low"|"unknown",\n'
    ' "suspects": [str], "signals": [str], "search_queries": [str]}\n'
    "- summary: one or two sentences describing the failure as observed\n"
    "- suspects: components or subsystems most likely responsible (e.g. liveness probe, "
    "resource limits, image pull, secret volume)\n"
    "- signals: the concrete evidence lines you relied on\n"
    "- search_queries: 1-3 web search queries that could match this error to documented "
    "causes (include the exact error text)"
)


class Triage(BaseModel):
    summary: str
    severity: str = "unknown"
    suspects: list[str] = Field(default_factory=list)
    signals: list[str] = Field(default_factory=list)
    search_queries: list[str] = Field(default_factory=list)
    model: str = ""

    @classmethod
    def from_model_json(cls, data: object, *, model: str) -> Triage:
        if not isinstance(data, dict):
            return cls(summary=str(data), model=model)
        severity = str(data.get("severity", "unknown")).lower()
        return cls(
            summary=str(data.get("summary", "")),
            severity=severity if severity in SEVERITIES else "unknown",
            suspects=[str(s) for s in data.get("suspects", []) if str(s).strip()][:10],
            signals=[str(s) for s in data.get("signals", []) if str(s).strip()][:10],
            search_queries=[str(s) for s in data.get("search_queries", []) if str(s).strip()][:3],
            model=model,
        )


def triage(client: ModelClient, evidence: ClusterEvidence) -> Triage:
    """Run nano-tier triage over the collected evidence."""
    reply = complete_json(
        client,
        "nano",
        [
            Message(role="system", content=_TRIAGE_SYSTEM),
            Message(role="user", content=evidence.render()),
        ],
        purpose="triage",
    )
    tier_config = client.tier("nano")
    return Triage.from_model_json(reply, model=tier_config.model)
