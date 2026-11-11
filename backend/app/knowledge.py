"""Clinic Knowledge Base provider and Grounding Guardrail integration.

Provides a decoupled KnowledgeProvider interface supporting in-context YAML (v1)
and forward-compatible with SQLite FTS5 (v2).
"""

from pathlib import Path
from typing import Any, Protocol
import yaml


class KnowledgeProvider(Protocol):
    """Protocol for fetching grounding context for the receptionist LLM."""

    def get_grounding_context(self, query: str | None = None) -> str:
        """Return the formatted grounding knowledge context string."""
        ...


class YAMLKnowledgeProvider:
    """In-context structured YAML knowledge provider (v1).

    Loads curated clinic knowledge and emits structured grounding text containing
    strict Grounding Guardrail directives.
    """

    def __init__(self, yaml_path: str | Path = "data/clinic_knowledge.yaml"):
        self.yaml_path = Path(yaml_path)
        self._entries: list[dict[str, Any]] = []
        self._clinic_info: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Load and validate the YAML file."""
        if not self.yaml_path.exists():
            self._entries = []
            self._clinic_info = {}
            return

        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        self._clinic_info = data.get("clinic", {})
        raw_entries = data.get("entries", [])

        validated = []
        for entry in raw_entries:
            if not isinstance(entry, dict):
                continue
            # Validate required fields for forward-compatibility with FTS5
            if not all(k in entry for k in ("id", "category", "keywords", "question", "answer")):
                continue
            validated.append(entry)

        self._entries = validated

    @property
    def entries(self) -> list[dict[str, Any]]:
        return list(self._entries)

    def get_grounding_context(self, query: str | None = None) -> str:
        """Format the entire knowledge base (or matched subset) with Grounding Guardrails."""
        if not self._entries:
            return ""

        lines = [
            "CLINIC KNOWLEDGE BASE (GROUNDING SOURCE OF TRUTH):",
        ]

        if self._clinic_info:
            lines.append("Clinic Overview:")
            for k, v in self._clinic_info.items():
                lines.append(f"- {k.replace('_', ' ').title()}: {v}")
            lines.append("")

        lines.append("Approved Answers:")
        for e in self._entries:
            cat = e.get("category", "General").title()
            q = e.get("question", "").strip()
            a = e.get("answer", "").strip()
            lines.append(f"[{cat}] Q: {q}")
            lines.append(f"         A: {a}")

        lines.extend(
            [
                "",
                "GROUNDING GUARDRAIL DIRECTIVES:",
                "1. STRICT FACTUAL BOUNDARY: Answer questions about clinic services, pricing, prep, "
                "and policies ONLY using the approved answers above.",
                "2. NO SPECULATION: Never extrapolate, guess, or invent fees, doctor schedules, or "
                "services not explicitly listed.",
                "3. GRACEFUL FALLBACK: If the user asks something not covered in the knowledge base, "
                "acknowledge that you do not have that specific information and offer to record a "
                "Caller Message with their name, phone number, and question for staff follow-up.",
            ]
        )

        return "\n".join(lines)


# Singleton knowledge provider
clinic_knowledge: KnowledgeProvider = YAMLKnowledgeProvider()
