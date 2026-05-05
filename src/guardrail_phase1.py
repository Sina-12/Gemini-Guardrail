"""Phase 1 dynamic guardrail: audit loop over prepared summaries.

This module uses one local inference path through Ollama:
- OpenAI-compatible endpoint at http://localhost:11434/v1
- Model: phi4-mini-reasoning (judge only)

The guardrail flow decomposes candidate summaries into atomic claims,
evaluates each claim against source evidence, generates revision directives,
and returns trust/quality signals for each iteration.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import os
import re
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from openai import AsyncOpenAI
import torch
from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

# Project root is one level above this file's directory (…/src/guardrail_phase1.py → repo root).
PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv

    # Repo-root .env is authoritative (works when cwd is src/ or repo root).
    load_dotenv(dotenv_path=ENV_FILE, override=True)
except ImportError:
    pass


OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
OLLAMA_REWRITE_MODEL = "phi4-mini"
OLLAMA_JUDGE_MODEL = "phi4-mini-reasoning"
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")
OLLAMA_REQUEST_TIMEOUT_SEC = float(os.getenv("OLLAMA_REQUEST_TIMEOUT_SEC", "300"))
MAX_SOURCE_CHARS = 10000
MAX_CLAIMS_PER_AUDIT = 12
TOP_K_EVIDENCE = 3
SEMANTIC_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEBERTA_MODEL_NAME = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
SEMANTIC_LOW_SIM_THRESHOLD = 0.35


def _truncate_for_model(text: str, max_chars: int) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head - 80
    return (
        text[:head]
        + "\n\n[... middle truncated for model context ...]\n\n"
        + text[-tail:]
    )


def _split_sentences(text: str) -> List[str]:
    """
    Split text into sentence-like units without treating every '.' as a boundary.

    Common abbreviations (e.g. e.g., i.e., et al.) and numeric decimals are
    temporarily masked so they are not split at their internal periods.
    """
    raw = text.strip()
    if not raw:
        return []

    protected: List[str] = []
    ph_open = "\uE000"
    ph_close = "\uE001"

    def _protect(pattern: re.Pattern[str], s: str) -> str:
        def repl(m: re.Match[str]) -> str:
            protected.append(m.group(0))
            return f"{ph_open}{len(protected) - 1}{ph_close}"

        return pattern.sub(repl, s)

    s = raw.replace("\r\n", "\n")

    # URLs contain many '.' that are not sentence boundaries.
    s = _protect(re.compile(r"https?://[^\s]+", re.IGNORECASE), s)

    # Numeric decimals (and simple dotted versions / scientific notation).
    s = _protect(
        re.compile(r"\b\d+\.\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"),
        s,
    )

    # Abbreviations and honorifics that contain a period but are not sentence ends.
    abbrev = re.compile(
        r"\b(?:"
        r"e\.g\.|i\.e\.|et al\.|vs\.|etc\.|approx\.|ca\.|"
        r"figs?\.|dr\.|mr\.|mrs\.|ms\.|prof\.|ph\.d\.|sr\.|jr\.|"
        r"st\.|ave\.|blvd\.|no\.|vol\.|pp?\.|chs?\.|secs?\.|"
        r"eds?\.|inc\.|ltd\.|co\.|corp\.|"
        r"u\.s\.a?\.|u\.k\.|e\.u\.|a\.m\.|p\.m\.|"
        r"viz\.|cf\.|"
        r"b\.c\.|a\.d\.|c\.e\."
        r")\b",
        re.IGNORECASE,
    )
    s = _protect(abbrev, s)

    chunks = [p.strip() for p in re.split(r"(?<=[.!?])\s+", s) if p.strip()]

    def _unmask(chunk: str) -> str:
        def repl(m: re.Match[str]) -> str:
            return protected[int(m.group(1))]

        return re.sub(rf"{re.escape(ph_open)}(\d+){re.escape(ph_close)}", repl, chunk)

    return [_unmask(c) for c in chunks]


def normalize_text_for_compare(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", text.lower())).strip()


def _mean_pool(last_hidden: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
    summed = torch.sum(last_hidden * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


@dataclass
class ClaimAudit:
    claim: str
    verdict: str
    confidence: float
    evidence: str
    reason: str


class SummaryGenerator:
    """Prepared summary + directive-aware subtle rewriter using phi4-mini."""

    def __init__(self) -> None:
        self.model_name = OLLAMA_REWRITE_MODEL
        self._client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._timeout = OLLAMA_REQUEST_TIMEOUT_SEC
        self._max_source_chars = MAX_SOURCE_CHARS
        self._backend = "dataset_summary"
        self._last_model_error: Optional[str] = None

    def _pack_rewrite_inputs(
        self, source_text: str, base_summary: str, directives: List[str], max_sentences: int
    ) -> str:
        directives_block = (
            "\n".join(f"- {d}" for d in directives)
            if directives
            else "- No directives. Return the original summary."
        )
        source_block = _truncate_for_model(source_text, self._max_source_chars)
        return (
            f"Task: revise this summary in at most {max_sentences} sentences.\n"
            "Requirements:\n"
            "- Keep the original summary style, tone, structure, and wording as-is.\n"
            "- Apply ONLY the minimum edits required by directives.\n"
            "- Do not paraphrase unaffected sentences.\n"
            "- Do not add new details unless required to fix a flagged issue.\n"
            "- Keep claims faithful to source text and avoid unsupported facts.\n"
            "- Output only the revised summary text.\n\n"
            f"Current summary:\n{base_summary}\n\n"
            f"Revision directives:\n{directives_block}\n\n"
            f"Source text:\n{source_block}"
        )

    async def _rewrite_summary_async(
        self, source_text: str, base_summary: str, directives: List[str], max_sentences: int
    ) -> str:
        prompt = self._pack_rewrite_inputs(source_text, base_summary, directives, max_sentences)
        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise editor. Make subtle factual corrections only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=300,
                temperature=0.1,
                timeout=self._timeout,
            )
            text = response.choices[0].message.content
            if isinstance(text, str) and text.strip():
                self._backend = f"ollama_chat:{self.model_name}"
                return text.strip()
            self._last_model_error = "Ollama returned empty rewrite content."
            return ""
        except Exception as exc:
            self._last_model_error = f"Ollama rewrite call failed: {exc}"
            return ""

    async def _rewrite_sentence_async(
        self,
        source_text: str,
        sentence: str,
        guidance: str,
    ) -> str:
        source_block = _truncate_for_model(source_text, self._max_source_chars)
        prompt = (
            "Task: rewrite exactly one sentence.\n"
            "Requirements:\n"
            "- Keep the original wording/style as much as possible.\n"
            "- Modify only what is required by the guidance.\n"
            "- Output one sentence only, no bullets or extra text.\n\n"
            f"Original sentence:\n{sentence}\n\n"
            f"Guidance:\n{guidance}\n\n"
            f"Source text:\n{source_block}"
        )
        try:
            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a strict one-sentence editor."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=140,
                temperature=0.1,
                timeout=self._timeout,
            )
            text = response.choices[0].message.content
            if isinstance(text, str) and text.strip():
                self._backend = f"ollama_chat:{self.model_name}"
                return text.strip()
            self._last_model_error = "Ollama returned empty sentence rewrite content."
            return ""
        except Exception as exc:
            self._last_model_error = f"Ollama sentence rewrite call failed: {exc}"
            return ""

    def generate(
        self,
        source_text: str,
        prepared_summary: str,
        current_summary: str,
        directives: List[str],
        iteration: int,
        max_sentences: int = 5,
    ) -> str:
        if iteration <= 1:
            if not prepared_summary.strip():
                return ""
            self._backend = "dataset_summary"
            return prepared_summary.strip()

        if not current_summary.strip():
            return ""

        out = asyncio.run(
            self._rewrite_summary_async(
                source_text=source_text,
                base_summary=current_summary,
                directives=directives,
                max_sentences=max_sentences,
            )
        )
        return out.strip() if out.strip() else current_summary

    def rewrite_sentence(self, source_text: str, sentence: str, guidance: str) -> str:
        if not sentence.strip():
            return sentence
        out = asyncio.run(
            self._rewrite_sentence_async(
                source_text=source_text,
                sentence=sentence,
                guidance=guidance,
            )
        )
        candidate = out.strip()
        if candidate and candidate != sentence.strip():
            # Keep one sentence even if the model returns extras.
            pieces = _split_sentences(candidate)
            return pieces[0].strip() if pieces else candidate

        # Retry once with stronger guidance if output is empty/unchanged.
        retry_guidance = (
            guidance
            + "\nIMPORTANT: You must revise the sentence so it differs from the original while preserving meaning."
        )
        retry = asyncio.run(
            self._rewrite_sentence_async(
                source_text=source_text,
                sentence=sentence,
                guidance=retry_guidance,
            )
        ).strip()
        if retry:
            pieces = _split_sentences(retry)
            candidate_retry = pieces[0].strip() if pieces and pieces[0].strip() else retry
            if candidate_retry and candidate_retry != sentence.strip():
                return candidate_retry
        return sentence


class LocalAuditModels:
    """Startup-loaded local models for semantic search + DeBERTa NLI."""

    def __init__(self) -> None:
        self.semantic_tokenizer = AutoTokenizer.from_pretrained(SEMANTIC_MODEL_NAME)
        self.semantic_model = AutoModel.from_pretrained(SEMANTIC_MODEL_NAME)
        self.nli_tokenizer = AutoTokenizer.from_pretrained(DEBERTA_MODEL_NAME)
        self.nli_model = AutoModelForSequenceClassification.from_pretrained(DEBERTA_MODEL_NAME)
        self.nli_model.eval()
        self.semantic_model.eval()

    def _embed_texts(self, texts: List[str]) -> torch.Tensor:
        encoded = self.semantic_tokenizer(
            texts, padding=True, truncation=True, max_length=256, return_tensors="pt"
        )
        with torch.no_grad():
            out = self.semantic_model(**encoded)
            pooled = _mean_pool(out.last_hidden_state, encoded["attention_mask"])
            return torch.nn.functional.normalize(pooled, p=2, dim=1)

    def best_evidence_by_cosine(
        self, claim: str, source_sentences: List[str], top_k: int = TOP_K_EVIDENCE
    ) -> Tuple[List[str], float, List[int]]:
        if not source_sentences:
            return [], 0.0, []
        all_texts = [claim] + source_sentences
        embeds = self._embed_texts(all_texts)
        claim_vec = embeds[0]
        source_vecs = embeds[1:]
        sims = torch.matmul(source_vecs, claim_vec)
        k = max(1, min(int(top_k), len(source_sentences)))
        top_vals, top_idxs = torch.topk(sims, k=k)
        top_indices = [int(i.item()) for i in top_idxs]
        top_sentences = [source_sentences[j] for j in top_indices]
        return top_sentences, float(top_vals[0].item()), top_indices

    @staticmethod
    def _normalize_nli_label(raw_label: str) -> str:
        label = (raw_label or "").strip().lower()
        if "contrad" in label:
            return "contradiction"
        if "entail" in label:
            return "entailment"
        if "neutral" in label:
            return "neutral"
        return label or "unknown"

    def classify_deberta(self, premises: List[str], hypothesis: str) -> Tuple[str, float]:
        premise = "\n".join(f"[E{i+1}] {p}" for i, p in enumerate(premises) if p.strip())
        encoded = self.nli_tokenizer(
            premise, hypothesis, truncation=True, max_length=512, return_tensors="pt"
        )
        with torch.no_grad():
            logits = self.nli_model(**encoded).logits[0]
            probs = torch.softmax(logits, dim=-1)
        idx = int(torch.argmax(probs).item())
        confidence = float(probs[idx].item())
        raw_label = self.nli_model.config.id2label.get(idx, str(idx))
        label = self._normalize_nli_label(str(raw_label))
        return label, round(confidence, 4)


class ForensicAuditor:
    """Flow: semantic evidence retrieval -> DeBERTa contradiction -> phi4 judge."""

    def __init__(self, audit_models: LocalAuditModels) -> None:
        self.audit_models = audit_models
        self.model_name = OLLAMA_JUDGE_MODEL
        self._client = AsyncOpenAI(base_url=OLLAMA_BASE_URL, api_key=OLLAMA_API_KEY)
        self._timeout = OLLAMA_REQUEST_TIMEOUT_SEC
        self._max_claims = MAX_CLAIMS_PER_AUDIT
        self._max_source_chars = MAX_SOURCE_CHARS
        self._backend = "pending"

    def decompose_atomic_claims(self, summary: str) -> List[str]:
        return _split_sentences(summary)

    @staticmethod
    def _build_judge_context_window(
        source_sents: List[str], top_indices: List[int]
    ) -> Tuple[str, List[str]]:
        """
        For each top semantic hit index j, include sentences j-1, j, j+1 in document order.
        De-duplicate indices, sort by position, return formatted text for the judge and
        the ordered sentence list for the UI.
        """
        n = len(source_sents)
        idx_set: set[int] = set()
        for j in top_indices:
            if j < 0 or j >= n:
                continue
            for k in range(max(0, j - 1), min(n, j + 2)):
                idx_set.add(k)
        sorted_idx = sorted(idx_set)
        lines: List[str] = []
        ordered_sents: List[str] = []
        for k in sorted_idx:
            sent = source_sents[k].strip()
            if not sent:
                continue
            lines.append(f"[doc {k + 1}] {sent}")
            ordered_sents.append(source_sents[k])
        return "\n".join(lines), ordered_sents

    async def _judge_contradiction_async(
        self,
        judge_context: str,
        claim: str,
        deberta_confidence: float,
    ) -> Tuple[bool, str]:
        prompt = (
            "You are the final hallucination judge.\n"
            "DeBERTa flagged this claim after semantic retrieval and NLI screening.\n"
            "Decide if the claim is hallucinated using ONLY the source excerpts below.\n"
            "Each excerpt is either a top semantic match for the claim or the sentence "
            "immediately before or after such a match in the original document order.\n"
            "Understand that the excerpts are only part of the source text, so the point is to verify the summary sentence using the provided excerpts, but not assume the excerpts should conain everything.\n"
            "Besides hallucinations, you need to make sure if the summary line captures the points of the excerpts and provide an explanation of how good the summary line is at capturing the points of the excerpts.\n"
            'Return strict JSON only: {"hallucinated": true/false, "explanation": "short explanation"}\n\n'
            f"Source excerpts (document order):\n{judge_context}\n\n"
            f"Claim:\n{claim}\n\nDeBERTa confidence: {deberta_confidence}"
        )
        request_kwargs = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Output strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 220,
            "temperature": 0.0,
            "timeout": self._timeout,
        }
        # Prefer structured JSON when backend supports OpenAI response_format.
        try:
            response = await self._client.chat.completions.create(
                **request_kwargs,
                response_format={"type": "json_object"},
            )
        except Exception:
            response = await self._client.chat.completions.create(**request_kwargs)
        content = response.choices[0].message.content or ""
        parsed = self._parse_judge_response(content)
        if parsed is None:
            raise RuntimeError("phi4-mini-reasoning judge returned unparsable output.")
        self._backend = f"ollama_chat:{self.model_name}"
        return parsed

    @staticmethod
    def _parse_judge_response(content: str) -> Optional[Tuple[bool, str]]:
        raw = content.strip()
        if not raw:
            return None
        candidates = [raw]

        # Common model wrapper: ```json ... ```
        fence_match = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```", raw, flags=re.DOTALL | re.IGNORECASE
        )
        if fence_match:
            candidates.append(fence_match.group(1))

        # Try whole-object extraction.
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if match:
            candidates.append(match.group(0))

        # Salvage path: hallucinated yes/no style text.
        lowered = raw.lower()
        if "hallucinated" in lowered:
            hallucinated = bool(
                re.search(r"hallucinated\s*[:=]\s*(true|yes|1)", lowered)
                or re.search(r"\b(true|yes)\b", lowered)
            )
            explanation = raw
            explanation = re.sub(r"```(?:json)?|```", "", explanation, flags=re.IGNORECASE).strip()
            explanation = explanation or "Judge explanation unavailable."
            return hallucinated, explanation

        for candidate in candidates:
            try:
                obj = json.loads(candidate)
                val = obj.get("hallucinated")
                if isinstance(val, bool):
                    hallucinated = val
                elif isinstance(val, str):
                    hallucinated = val.strip().lower() in {"true", "yes", "1"}
                elif isinstance(val, (int, float)):
                    hallucinated = bool(val)
                else:
                    hallucinated = False
                explanation = str(obj.get("explanation", "")).strip() or "Judge explanation unavailable."
                return hallucinated, explanation
            except Exception:
                continue
        return None

    def audit(self, source_text: str, summary: str, emit: Optional[Callable[[Dict], None]] = None) -> Dict:
        body = _truncate_for_model(source_text, self._max_source_chars)
        source_sents = _split_sentences(body)
        claims = self.decompose_atomic_claims(summary)
        if emit:
            emit(
                {
                    "type": "audit_start",
                    "claim_count": len(claims),
                    "source_sentence_count": len(source_sents),
                }
            )
        truncated_claims = False
        if len(claims) > self._max_claims:
            claims = claims[: self._max_claims]
            truncated_claims = True

        audits: List[ClaimAudit] = []
        for idx, claim in enumerate(claims):
            evidence_candidates, cosine_sim, top_indices = self.audit_models.best_evidence_by_cosine(
                claim, source_sents, top_k=TOP_K_EVIDENCE
            )
            if not evidence_candidates:
                raise RuntimeError("Semantic retrieval failed: no source evidence sentence found.")
            evidence = " ".join(evidence_candidates)
            judge_context, evidence_context_sentences = self._build_judge_context_window(
                source_sents, top_indices
            )

            label, deberta_conf = self.audit_models.classify_deberta(evidence_candidates, claim)
            contradiction = label == "contradiction"
            neutral_low_conf = (label == "neutral") and (deberta_conf < 0.85)
            entail_low_conf = (label == "entailment") and (deberta_conf < 0.75)
            send_to_judge = contradiction or neutral_low_conf or entail_low_conf
            if emit:
                emit(
                    {
                        "type": "claim_scored",
                        "claim_index": idx,
                        "claim": claim,
                        "evidence": evidence,
                        "evidence_top3": evidence_candidates,
                        "evidence_context_sentences": evidence_context_sentences,
                        "deberta_label": label,
                        "deberta_confidence": deberta_conf,
                        "cosine_similarity": round(float(cosine_sim), 4),
                        "send_to_judge": send_to_judge,
                    }
                )

            if send_to_judge:
                if emit:
                    emit(
                        {
                            "type": "judge_start",
                            "claim_index": idx,
                            "claim": claim,
                            "judge_model": self.model_name,
                        }
                    )
                hallucinated, judge_explanation = asyncio.run(
                    self._judge_contradiction_async(
                        judge_context=judge_context,
                        claim=claim,
                        deberta_confidence=deberta_conf,
                    )
                )
                verdict = "hallucinated" if hallucinated else "supported"
                reason = (
                    f"DeBERTa label={label} (confidence={deberta_conf}) triggered {self.model_name} review; "
                    f"{self.model_name} judge verdict: {judge_explanation}"
                )
                backend = f"semantic_cosine+deberta+{self._backend}"
                if emit:
                    emit(
                        {
                            "type": "judge_result",
                            "claim_index": idx,
                            "hallucinated": hallucinated,
                            "explanation": judge_explanation,
                        }
                    )
            else:
                verdict = "supported"
                reason = (
                    f"DeBERTa label={label} (confidence={deberta_conf}). "
                    f"{self.model_name} judge not triggered because confidence passed the routing thresholds."
                )
                backend = "semantic_cosine+deberta"

            if cosine_sim < SEMANTIC_LOW_SIM_THRESHOLD:
                reason = (
                    f"Low semantic cosine ({cosine_sim:.4f}) triggered focused DeBERTa screening. "
                    + reason
                )

            audits.append(
                ClaimAudit(
                    claim=claim,
                    verdict=verdict,
                    confidence=deberta_conf,
                    evidence=evidence,
                    reason=f"{reason} Backend: {backend}.",
                )
            )
            if emit:
                emit(
                    {
                        "type": "claim_finalized",
                        "claim_index": idx,
                        "verdict": verdict,
                        "claim": claim,
                        "evidence": evidence,
                        "confidence": deberta_conf,
                        "reason": reason,
                    }
                )

        unsupported = [a for a in audits if a.verdict == "hallucinated"]
        supported_count = len(audits) - len(unsupported)
        total = max(1, len(audits))
        support_ratio = supported_count / total

        directives = []
        for claim in unsupported:
            directives.append(
                (
                    "Hallucination detected. Rewrite or remove claim: "
                    f"'{claim.claim}'. Use evidence: '{claim.evidence}'. "
                    f"Judge explanation: {claim.reason}"
                )
            )

        result = {
            "claims": [a.__dict__ for a in audits],
            "directives": directives,
            "hallucination_count": len(unsupported),
            "support_ratio": round(support_ratio, 4),
            "trust_delta": round((support_ratio * 2.0) - (len(unsupported) * 0.2), 4),
            "truncated_claims": truncated_claims,
            "max_claims": self._max_claims,
        }
        if emit:
            emit(
                {
                    "type": "audit_complete",
                    "hallucination_count": result["hallucination_count"],
                    "support_ratio": result["support_ratio"],
                }
            )
        return result


class GuardrailOrchestrator:
    """Stateful recursive refinement loop."""

    def __init__(self, audit_models: LocalAuditModels) -> None:
        self.generator = SummaryGenerator()
        self.auditor = ForensicAuditor(audit_models=audit_models)

    @staticmethod
    def _guidance_from_claim(claim_info: Dict) -> str:
        reason = str(claim_info.get("reason", "")).strip()
        m = re.search(r"judge verdict:\s*(.+?)(?:\s*Backend:|$)", reason, flags=re.IGNORECASE)
        if m and m.group(1).strip():
            return m.group(1).strip()
        claim_txt = str(claim_info.get("claim", "")).strip()
        return reason or claim_txt or "Rewrite to remove unsupported content."

    @staticmethod
    def _compose_sentence_rewrite_guidance(claim_info: Dict) -> str:
        claim_txt = str(claim_info.get("claim", "")).strip()
        evidence_txt = str(claim_info.get("evidence", "")).strip()
        judge_guidance = GuardrailOrchestrator._guidance_from_claim(claim_info)
        parts = [
            f"Claim flagged as hallucinated: {claim_txt}" if claim_txt else "",
            f"Grounding evidence to use: {evidence_txt}" if evidence_txt else "",
            f"Judge guidance: {judge_guidance}" if judge_guidance else "",
            "Rewrite the sentence so it is supported by the evidence and clearly differs from the original wording.",
        ]
        return "\n".join([p for p in parts if p])

    @staticmethod
    def _ensure_changed_sentence(original_sentence: str, candidate_sentence: str, claim_info: Dict) -> str:
        original_norm = normalize_text_for_compare(original_sentence)
        candidate_norm = normalize_text_for_compare(candidate_sentence)
        if candidate_norm and candidate_norm != original_norm:
            return candidate_sentence
        evidence_txt = str(claim_info.get("evidence", "")).strip()
        claim_txt = str(claim_info.get("claim", "")).strip()
        # Deterministic fallback so the new summary reflects an actual correction attempt.
        if evidence_txt:
            return evidence_txt
        if claim_txt and normalize_text_for_compare(claim_txt) != original_norm:
            return claim_txt
        return candidate_sentence

    def run(
        self,
        source_text: str,
        prepared_summary: str,
        max_iters: int = 3,
        min_support_ratio: float = 0.8,
    ) -> Dict:
        state = {
            "iteration": 0,
            "trust_score": 0.5,
            "history": [],
            "final_summary": "",
            "status": "running",
        }

        # 1) Full-summary audit pass (keep this immutable for UI notes).
        original_summary = prepared_summary.strip()
        audit = self.auditor.audit(source_text=source_text, summary=original_summary)
        state["iteration"] = 1
        state["trust_score"] = round(
            max(0.0, min(1.0, state["trust_score"] + float(audit["trust_delta"]) * 0.2)), 4
        )
        state["history"].append(
            {
                "iteration": 1,
                "candidate_summary": original_summary,
                "audit": audit,
                "trust_score": state["trust_score"],
                "generator_backend": "dataset_summary",
                "auditor_backend": self.auditor._backend,
            }
        )

        if audit["support_ratio"] >= min_support_ratio and audit["hallucination_count"] == 0:
            state["final_summary"] = original_summary
            state["status"] = "accepted"
        else:
            # 2) Targeted rewrite/re-audit only on hallucinated sentences.
            new_sentences = _split_sentences(original_summary)
            claims = audit.get("claims", [])
            for claim_idx, claim_info in enumerate(claims):
                if claim_info.get("verdict") != "hallucinated" or claim_idx >= len(new_sentences):
                    continue
                guidance = self._compose_sentence_rewrite_guidance(claim_info)
                sentence = new_sentences[claim_idx]
                for _ in range(max(1, max_iters)):
                    rewritten = self.generator.rewrite_sentence(
                        source_text=source_text, sentence=sentence, guidance=guidance
                    )
                    rewritten = self._ensure_changed_sentence(sentence, rewritten, claim_info)
                    sentence_audit = self.auditor.audit(source_text=source_text, summary=rewritten)
                    verdict = (
                        sentence_audit["claims"][0]["verdict"]
                        if sentence_audit.get("claims")
                        else "supported"
                    )
                    sentence = rewritten
                    if verdict != "hallucinated":
                        break
                new_sentences[claim_idx] = sentence
            state["final_summary"] = " ".join(s.strip() for s in new_sentences if s.strip())
            state["status"] = "revised"

        state["backends"] = {
            "generator": self.generator._backend,
            "auditor": self.auditor._backend,
        }
        return state

    def run_stream(
        self,
        source_text: str,
        prepared_summary: str,
        max_iters: int = 3,
        min_support_ratio: float = 0.8,
        emit: Optional[Callable[[Dict], None]] = None,
    ) -> Dict:
        state = {
            "iteration": 0,
            "trust_score": 0.5,
            "history": [],
            "final_summary": "",
            "status": "running",
        }
        if emit:
            emit(
                {
                    "type": "run_started",
                    "max_iters": max_iters,
                    "min_support_ratio": min_support_ratio,
                }
            )

        # Phase A: full summary audit once.
        original_summary = prepared_summary.strip()
        if emit:
            emit(
                {
                    "type": "iteration_started",
                    "iteration": 1,
                    "directives_count": 0,
                    "trust_score": state["trust_score"],
                }
            )
            emit(
                {
                    "type": "summarizer_start",
                    "iteration": 1,
                    "model": "prepared_summary",
                    "target": "original",
                }
            )
            emit(
                {
                    "type": "summarizer_complete",
                    "iteration": 1,
                    "candidate_summary": original_summary,
                    "target": "original",
                }
            )
            emit({"type": "auditor_start", "iteration": 1, "model": self.auditor.model_name})

        audit = self.auditor.audit(
            source_text=source_text,
            summary=original_summary,
            emit=(lambda event: emit({"iteration": 1, "target": "original", **event}) if emit else None),
        )

        state["iteration"] = 1
        state["trust_score"] = round(
            max(0.0, min(1.0, state["trust_score"] + float(audit["trust_delta"]) * 0.2)), 4
        )
        state["history"].append(
            {
                "iteration": 1,
                "candidate_summary": original_summary,
                "audit": audit,
                "trust_score": state["trust_score"],
                "generator_backend": "dataset_summary",
                "auditor_backend": self.auditor._backend,
            }
        )
        if emit:
            emit(
                {
                    "type": "trust_updated",
                    "iteration": 1,
                    "trust_score": state["trust_score"],
                    "support_ratio": audit["support_ratio"],
                    "target": "original",
                }
            )
            emit(
                {
                    "type": "iteration_complete",
                    "iteration": 1,
                    "audit": audit,
                    "target": "original",
                }
            )

        if audit["support_ratio"] >= min_support_ratio and audit["hallucination_count"] == 0:
            state["final_summary"] = original_summary
            state["status"] = "accepted"
            if emit:
                emit({"type": "run_accepted", "iteration": 1, "final_summary": original_summary})
        else:
            # Phase B: create a new summary and only rewrite/re-audit hallucinated lines.
            new_sentences = _split_sentences(original_summary)
            if emit:
                emit(
                    {
                        "type": "new_summary_started",
                        "iteration": 2,
                        "candidate_summary": original_summary,
                    }
                )
            claims = audit.get("claims", [])
            for claim_idx, claim_info in enumerate(claims):
                if claim_info.get("verdict") != "hallucinated" or claim_idx >= len(new_sentences):
                    continue
                guidance = self._compose_sentence_rewrite_guidance(claim_info)
                sentence = new_sentences[claim_idx]
                for attempt in range(1, max(1, max_iters) + 1):
                    rewritten = self.generator.rewrite_sentence(
                        source_text=source_text, sentence=sentence, guidance=guidance
                    )
                    rewritten = self._ensure_changed_sentence(sentence, rewritten, claim_info)
                    if emit:
                        emit(
                            {
                                "type": "new_sentence_rewritten",
                                "iteration": 1 + attempt,
                                "claim_index": claim_idx,
                                "old_sentence": sentence,
                                "sentence": rewritten,
                                "rewrite_model": self.generator.model_name,
                                "rewrite_backend": self.generator._backend,
                            }
                        )
                    sentence_audit = self.auditor.audit(source_text=source_text, summary=rewritten)
                    sentence_claim = sentence_audit["claims"][0] if sentence_audit.get("claims") else None
                    verdict = sentence_claim["verdict"] if sentence_claim else "supported"
                    if emit and sentence_claim:
                        emit(
                            {
                                "type": "judge_result",
                                "iteration": 1 + attempt,
                                "target": "new",
                                "claim_index": claim_idx,
                                "hallucinated": verdict == "hallucinated",
                                "explanation": sentence_claim.get("reason", ""),
                            }
                        )
                    sentence = rewritten
                    new_sentences[claim_idx] = sentence
                    if emit:
                        emit(
                            {
                                "type": "new_summary_update",
                                "iteration": 1 + attempt,
                                "candidate_summary": " ".join(
                                    s.strip() for s in new_sentences if s.strip()
                                ),
                            }
                        )
                    if verdict != "hallucinated":
                        break

            state["final_summary"] = " ".join(s.strip() for s in new_sentences if s.strip())
            state["status"] = "revised"

        state["backends"] = {
            "generator": self.generator._backend,
            "auditor": self.auditor._backend,
        }
        if emit:
            emit(
                {
                    "type": "run_complete",
                    "status": state["status"],
                    "iteration": state["iteration"],
                    "trust_score": state["trust_score"],
                }
            )
        return state


def create_guardrail_orchestrator() -> GuardrailOrchestrator:
    """Create orchestrator with startup-loaded local DeBERTa/semantic models."""
    return GuardrailOrchestrator(audit_models=LocalAuditModels())
