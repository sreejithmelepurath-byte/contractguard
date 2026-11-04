"""LLM analysis: contract text in, strict JSON (summary + red_flags) out."""
import json

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.schemas import AnalysisResult

SYSTEM_PROMPT = """You review freelance and service contracts for the freelancer.
Return ONLY a JSON object with exactly these keys:
  "summary": string - 3 to 5 plain-English sentences covering deliverables,
             timeline, payment and who owns the work.
  "red_flags": array of objects, each with
      "category": one of payment_terms, scope_revisions, intellectual_property,
                  termination, liability, non_compete, other
      "severity": one of low, medium, high
      "clause": a short excerpt (max 30 words) of the clause
      "explanation": one or two sentences on why it matters to the freelancer
Flag in particular: payment terms of Net-60 or longer, unlimited or unbounded
revisions, IP transfer that reaches beyond the delivered work, one-sided
termination, uncapped liability, and broad non-competes.
If nothing is concerning, return an empty red_flags array.
Do not give legal advice and do not invent clauses that are not in the text."""


class AnalysisError(RuntimeError):
    pass


class ContractAnalyzer:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", max_chars: int = 60_000):
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._max_chars = max_chars

    async def analyze(self, contract_text: str) -> AnalysisResult:
        text = contract_text[: self._max_chars]
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Contract text:\n\n{text}"},
            ],
        )
        raw = response.choices[0].message.content or "{}"
        return parse_result(raw)


def parse_result(raw: str) -> AnalysisResult:
    try:
        return AnalysisResult.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise AnalysisError("Model returned output that did not match the schema.") from exc
