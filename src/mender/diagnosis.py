"""Ultra-tier root-cause diagnosis with Tavily sources cited in the report."""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from mender.evidence import ClusterEvidence
from mender.modelio import complete_json
from mender.router.client import Message, ModelClient
from mender.tavily import Citation, SearchResult, TavilyClient
from mender.triage import Triage

_LABEL_CLEAN = re.compile(r"[^a-z0-9]+")


def normalize_label(label: str) -> str:
    return _LABEL_CLEAN.sub("_", label.lower()).strip("_")


_QUERY_SYSTEM = (
    "You are the search-planning stage of a Kubernetes incident agent. Given the triage "
    "summary and evidence, propose 1-3 web search queries that will match this exact "
    "failure to documented causes, known issues and release notes. Respond with ONLY "
    'JSON: {"queries": [str]}.'
)

_REPORT_SYSTEM = (
    "You are the root-cause stage of a Kubernetes incident agent. Using the evidence, the "
    "triage summary and the web search results provided, determine the root cause of the "
    "failure. Respond with ONLY a JSON object of this shape:\n"
    '{"title": str, "root_cause": str, "mechanism": str, "labels": [str],\n'
    ' "confidence": number, "evidence_refs": [str]}\n'
    "- title: one-line incident title\n"
    "- root_cause: the single most likely root cause, stated precisely\n"
    "- mechanism: how the cause produces the observed failure, step by step\n"
    "- labels: 1-5 short snake_case tags for scoring (e.g. oomkilled, memory_limit, "
    "probe_config, image_tag, missing_secret, migration_failure)\n"
    "- confidence: 0-1, honest — do not inflate\n"
    "- evidence_refs: short quotes from the evidence that support the conclusion\n"
    "When a search result explains part of the cause, mention it in root_cause/mechanism "
    "and include its number like [1] in your text."
)


class RootCauseReport(BaseModel):
    service: str
    namespace: str
    title: str
    root_cause: str
    mechanism: str = ""
    labels: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    triage_summary: str = ""
    search_queries: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    tavily_degraded: bool = False
    model: str = ""

    @property
    def normalized_labels(self) -> set[str]:
        return {normalize_label(label) for label in self.labels if label.strip()}

    @classmethod
    def from_model_json(
        cls,
        data: object,
        *,
        service: str,
        namespace: str,
        triage: Triage,
        queries: list[str],
        results: list[SearchResult],
        model: str,
    ) -> RootCauseReport:
        sources = [citation for result in results for citation in result.citations]
        degraded = any(result.degraded for result in results)
        if isinstance(data, dict):
            confidence = data.get("confidence", 0.0)
            try:
                confidence_f = float(confidence)
            except (TypeError, ValueError):
                confidence_f = 0.0
            _labels: list[str] = []
            if isinstance(data.get("labels"), list):
                _labels = [str(label) for label in data.get("labels", []) if str(label).strip()][:5]
            _evidence_refs: list[str] = []
            if isinstance(data.get("evidence_refs"), list):
                _evidence_refs = [
                    str(ref) for ref in data.get("evidence_refs", []) if str(ref).strip()
                ]
            _search_queries: list[str] = []
            if isinstance(queries, list):
                _search_queries = [str(q).strip() for q in queries if str(q).strip()]
            return cls(
                service=service,
                namespace=namespace,
                title=str(data.get("title", "Untitled incident")),
                root_cause=str(data.get("root_cause", "")),
                mechanism=str(data.get("mechanism", "")),
                labels=_labels,
                confidence=max(0.0, min(1.0, confidence_f)),
                evidence_refs=_evidence_refs,
                triage_summary=triage.summary,
                search_queries=_search_queries,
                sources=sources,
                tavily_degraded=degraded,
                model=model,
            )

        _search_queries_fb: list[str] = []
        if isinstance(queries, list):
            _search_queries_fb = [str(q).strip() for q in queries if str(q).strip()]
        return cls(
            service=service,
            namespace=namespace,
            title="Untitled incident",
            root_cause=str(data),
            triage_summary=triage.summary,
            search_queries=_search_queries_fb,
            sources=sources,
            tavily_degraded=degraded,
            model=model,
        )

    def markdown(self) -> str:
        refs = [f"- {ref}" for ref in self.evidence_refs] or ["- (none recorded)"]
        sources_md = [
            citation.markdown(number=i + 1) for i, citation in enumerate(self.sources)
        ] or ["- (no results)"]
        lines = [
            f"# Root cause: {self.title}",
            "",
            f"Service `{self.service}` in namespace `{self.namespace}`.",
            "",
            "## Root cause",
            self.root_cause,
            "",
            "## Mechanism",
            self.mechanism,
            "",
            f"Confidence: {self.confidence:.2f} · Labels: {', '.join(self.labels) or 'n/a'}",
            "",
            "## Evidence relied on",
            *refs,
            "",
            "## Tavily sources",
        ]
        if self.tavily_degraded:
            lines.append(
                "_Tavily search was degraded for some queries — sources may be incomplete._"
            )
        if self.search_queries:
            lines.append(f"Queries: {'; '.join(self.search_queries)}")
        lines += sources_md
        return "\n".join(lines)


def propose_queries(client: ModelClient, evidence: ClusterEvidence, triage: Triage) -> list[str]:
    """Ask the diagnosis tier which documented causes to search for."""
    user = (
        f"Triage summary: {triage.summary}\n"
        f"Severity: {triage.severity}\n"
        f"Suspects: {', '.join(triage.suspects)}\n\n{evidence.render()}"
    )
    reply = complete_json(
        client,
        "ultra",
        [Message(role="system", content=_QUERY_SYSTEM), Message(role="user", content=user)],
        purpose="search queries",
    )
    queries: list[str] = []
    if isinstance(reply, dict):
        queries = [str(q).strip() for q in reply.get("queries", []) if str(q).strip()]
    if not queries:
        queries = list(triage.search_queries)
    return queries[:3]


def gather_sources(tavily: TavilyClient, queries: list[str]) -> list[SearchResult]:
    """Run every proposed query; degradation is carried per result, never raised."""
    return [tavily.search(query, purpose="diagnosis") for query in queries]


def diagnose(
    client: ModelClient,
    evidence: ClusterEvidence,
    triage: Triage,
    results: list[SearchResult],
) -> RootCauseReport:
    """Produce the root-cause report from evidence, triage and search results."""
    sources_block = []
    counter = 0
    for result in results:
        for citation in result.citations:
            counter += 1
            snippet = citation.snippet[:600]
            sources_block.append(
                f"[{counter}] {citation.title}: {citation.url}\nsnippet: {snippet}"
            )
    search_section = "\n\n".join(sources_block) or "Tavily returned no results for these queries."

    suspects = ", ".join(triage.suspects)
    user = (
        f"EVIDENCE:\n{evidence.render()}\n\n"
        f"TRIAGE: {triage.summary} (severity {triage.severity}; suspects: {suspects})\n\n"
        f"SEARCH RESULTS (cite by number):\n{search_section}"
    )
    reply = complete_json(
        client,
        "ultra",
        [Message(role="system", content=_REPORT_SYSTEM), Message(role="user", content=user)],
        purpose="root cause report",
    )
    return RootCauseReport.from_model_json(
        reply,
        service=evidence.service,
        namespace=evidence.namespace,
        triage=triage,
        queries=[result.query for result in results],
        results=results,
        model=client.tier("ultra").model,
    )


def run_diagnosis(
    client: ModelClient,
    tavily: TavilyClient,
    evidence: ClusterEvidence,
    triage_result: Triage,
) -> RootCauseReport:
    """Full diagnosis: plan queries → Tavily search → root-cause report."""
    queries = propose_queries(client, evidence, triage_result)
    results = gather_sources(tavily, queries)
    return diagnose(client, evidence, triage_result, results)
