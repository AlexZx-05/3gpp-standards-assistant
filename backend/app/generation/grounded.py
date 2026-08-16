"""Strict evidence-only generation with source-bound citations."""

from urllib.parse import urlparse

from openai import OpenAI

from app.core.config import Settings, get_settings
from app.retrieval.types import Candidate


SYSTEM_PROMPT = (
    "You are a technical assistant specializing in 3GPP telecommunications standards. "
    "Answer ONLY from the supplied evidence. Do not use prior knowledge or invent facts, "
    "specifications, sections, pages, procedures, or requirements. Every factual claim needs "
    "a citation in the form [S1] that refers to supplied evidence. Cite every factual sentence individually. "
    "Never state or imply that a conclusion is inferred, likely, or merely suggested by the evidence. "
    "If evidence is insufficient, say so plainly."
)


class LLMConfigurationError(RuntimeError):
    """Raised when the selected provider and credential conflict."""


def evidence_block(candidates: list[Candidate]) -> str:
    blocks: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        metadata = candidate.metadata
        blocks.append(
            f"[S{index}] {metadata.get('specification', 'Unknown')} | section "
            f"{metadata.get('section') or 'not detected'} | page {metadata.get('page') or 'not detected'}\n"
            f"{candidate.text}"
        )
    return "\n\n".join(blocks)


class GroundedGenerator:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def configured(self) -> bool:
        return bool(self.settings.llm_api_key and self.settings.llm_model)

    def validate_configuration(self) -> None:
        """Catch common provider/credential mix-ups before making a request."""
        if not self.configured:
            return

        host = (urlparse(self.settings.llm_base_url).hostname or "").lower()
        api_key = self.settings.llm_api_key or ""
        if host == "api.x.ai" and api_key.startswith("gsk_"):
            raise LLMConfigurationError(
                "LLM_BASE_URL targets xAI, but LLM_API_KEY is a Groq-format key. "
                "Use an xAI key with the xAI endpoint, or configure Groq with "
                "LLM_BASE_URL=https://api.groq.com/openai/v1 and a Groq model."
            )
        if host == "api.groq.com" and api_key.startswith("xai-"):
            raise LLMConfigurationError(
                "LLM_BASE_URL targets Groq, but LLM_API_KEY is an xAI-format key. "
                "Use a Groq key with the Groq endpoint, or configure xAI consistently."
            )

    def answer(self, question: str, candidates: list[Candidate]) -> str:
        if not self.configured:
            return "Generation is not configured. Relevant indexed evidence is shown below; set LLM_API_KEY and LLM_MODEL to enable grounded answers."
        self.validate_configuration()
        client = OpenAI(api_key=self.settings.llm_api_key, base_url=self.settings.llm_base_url)
        response = client.chat.completions.create(
            model=self.settings.llm_model,
            temperature=0,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nEvidence:\n{evidence_block(candidates)}"},
            ],
        )
        return (response.choices[0].message.content or "Unable to produce a grounded answer.").strip()
