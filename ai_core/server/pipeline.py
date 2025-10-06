
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for type hints
    from backend.api.services.groq import GroqClient  # noqa: F401


@dataclass
class ModuleOutput:
    name: str
    route: str
    summary: str
    confidence: float
    findings: Dict[str, Any]


@dataclass
class PipelineResult:
    chain: List[str]
    scout: ModuleOutput
    analyst: ModuleOutput
    judge: ModuleOutput
    decision: Dict[str, Any]
    metadata: Dict[str, Any]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


class TripleAIPipeline:
    """Triple AI orchestration with optional Groq backend."""

    def __init__(self, config_dir: Path, groq_client: Optional["GroqClient"] = None) -> None:
        if not config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {config_dir}")

        self._config_dir = config_dir
        self._supercenter = _load_json(config_dir / "ai_supercenter.json")
        self._router = _load_json(config_dir / "llm_router.json")
        self._risk_policy = _load_json(config_dir / "risk_policy.json")
        self._profiles = _load_json(config_dir / "profiles_config.json")
        self._weights = _load_json(config_dir / "ai_weights_v2.json")
        self._global_rules = _load_json(config_dir / "ai_global_rules.json")
        self._groq_client = groq_client

        self._chain: list[str] = []
        for module_id, module in self._supercenter.get("modules", {}).items():
            route = module.get("uses_llm_route")
            if isinstance(route, str):
                self._chain.append(route)
            else:
                parts = module_id.split("_")
                if parts:
                    self._chain.append(parts[-1].lower())
        if not self._chain:
            self._chain = ["scout", "analyst", "judge"]

        self._weights_sum = (
            sum(item.get("weight", 0) for item in self._weights.get("features", {}).values())
            or 1.0
        )

        self._system_prompts = {
            "scout": (
                "You are the Scout module in a multi-agent trading system.\n"
                "Analyse social momentum, novelty, and spam likelihood in concise bullet points."
            ),
            "analyst": (
                "You are the Analyst module. Merge social momentum with on-chain metrics and return a structured risk summary with key metrics."
            ),
            "judge": (
                "You are the Judge module. Enforce global risk policy and return BUY/WATCH/NO with rationale and mandatory safety notes."
            ),
        }

    @classmethod
    def from_path(
        cls, config_dir: Path | str, *, groq_client: Optional["GroqClient"] = None
    ) -> "TripleAIPipeline":
        return cls(Path(config_dir), groq_client=groq_client)

    async def run(
        self, prompt: str, metadata: Optional[Mapping[str, Any]] = None
    ) -> PipelineResult:
        meta = dict(metadata or {})
        cleaned_prompt = self._clean_prompt(prompt)
        profile_id = self._resolve_profile(meta)

        scout_output = await self._run_scout(cleaned_prompt, meta, profile_id)
        analyst_output, analyst_score = await self._run_analyst(cleaned_prompt, meta)
        judge_output, decision = await self._run_judge(cleaned_prompt, meta, analyst_score)

        return PipelineResult(
            chain=list(self._chain),
            scout=scout_output,
            analyst=analyst_output,
            judge=judge_output,
            decision=decision,
            metadata={
                "profile": profile_id,
                "fallback_used": decision.get("fallback_used", False),
                "global_rules_version": self._global_rules.get("version"),
            },
        )

    async def _run_scout(
        self, prompt: str, metadata: dict[str, Any], profile_id: str
    ) -> ModuleOutput:
        route = self._profiles.get("profiles", {}).get(profile_id, {}).get("route", "scout")
        metrics = metadata.get("metrics", {})

        memeability = metrics.get("SOCIAL_BURST", 0)
        freq = metrics.get("FREQ_5M", 0)
        mentions = metrics.get("MENTIONS", 0)

        confidence = 0.3
        hints: list[str] = []
        if memeability:
            confidence += min(memeability / 10, 0.3)
            hints.append(f"Memeability boost {memeability}")
        if freq:
            confidence += min(freq / 20, 0.25)
            hints.append(f"Frequency spike {freq}/5m")
        if mentions:
            confidence += min(mentions / 200, 0.15)
            hints.append(f"Mentions {mentions}")

        confidence = round(min(confidence, 0.95), 3)

        findings = {
            "profile": profile_id,
            "hints": hints,
            "uses_llm_route": route,
            "router_model": self._router.get("routes", {}).get(route, {}).get("model"),
        }
        llm = await self._call_llm(route, prompt, metadata)
        summary = llm.get("text") if llm else prompt[:280] + ("…" if len(prompt) > 280 else "")
        if llm:
            findings["llm_usage"] = llm["raw"].get("usage", {})
        return ModuleOutput(name="scout", route=route, summary=summary, confidence=confidence, findings=findings)

    async def _run_analyst(
        self, prompt: str, metadata: dict[str, Any]
    ) -> tuple[ModuleOutput, float]:
        route = "analyst"
        metrics = metadata.get("metrics", {})
        scores = metadata.get("scores", {})

        score, passed_features, failed_features = self._score_features(metrics)

        base_summary = self._build_analysis_summary(prompt, metrics, scores)
        findings = {
            "passed": sorted(passed_features),
            "failed": sorted(failed_features),
            "inputs_used": sorted(metrics.keys()),
        }
        confidence = round(max(min(0.4 + score, 0.98), 0.05), 3)

        llm = await self._call_llm(route, prompt, metadata)
        summary = llm.get("text") if llm else base_summary
        if llm:
            findings["llm_usage"] = llm["raw"].get("usage", {})

        return (
            ModuleOutput(
                name="analyst",
                route=route,
                summary=summary,
                confidence=confidence,
                findings=findings,
            ),
            score,
        )

    async def _run_judge(
        self, prompt: str, metadata: dict[str, Any], analyst_score: float
    ) -> tuple[ModuleOutput, dict[str, Any]]:
        route = "judge"
        risk_eval = self._evaluate_risk(metadata)

        decision = self._decide(analyst_score, risk_eval)

        reasons = list(self._global_rules.get("principles", []))[:3]
        if risk_eval["critical_hits"]:
            reasons.insert(0, "Fail-closed: critical policy violation detected")
        elif decision["verdict"] == "WATCH":
            reasons.insert(0, "Monitor closely; analyst confidence below BUY threshold")

        summary = (
            f"Final decision {decision['verdict']} (risk={decision['risk_level']},"
            f" score={decision['score']:.2f})."
        )

        findings = {
            "critical_hits": risk_eval["critical_hits"],
            "warnings": risk_eval["warnings"],
            "policy": risk_eval["policy_snapshot"],
            "reasons": reasons,
        }

        llm = await self._call_llm(route, prompt, metadata, decision=decision)
        if llm and llm.get("text"):
            summary = llm["text"]
            findings["llm_usage"] = llm["raw"].get("usage", {})

        module_output = ModuleOutput(
            name="judge",
            route=route,
            summary=summary,
            confidence=decision["confidence"],
            findings=findings,
        )
        return module_output, decision

    async def _call_llm(
        self,
        route: str,
        prompt: str,
        metadata: Mapping[str, Any],
        *,
        decision: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        if not self._groq_client:
            return None
        route_cfg = self._router.get("routes", {}).get(route, {})
        messages = [
            {
                "role": "user",
                "content": self._build_stage_prompt(route, prompt, metadata, decision=decision),
            }
        ]
        metadata_payload = {"route": route}
        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                metadata_payload[key] = value
        try:
            response = await self._groq_client.chat_completion(
                messages=messages,
                system=self._system_prompts.get(route),
                model=route_cfg.get("model"),
                temperature=route_cfg.get("temperature"),
                metadata=metadata_payload,
            )
        except Exception:  # pragma: no cover - network failure fallback
            return None
        text = ""
        for choice in response.get("choices", []):
            message = choice.get("message") or {}
            if message.get("content"):
                text = message["content"]
                break
        return {"raw": response, "text": text}

    def _clean_prompt(self, prompt: str) -> str:
        return " ".join(prompt.split())

    def _resolve_profile(self, metadata: Mapping[str, Any]) -> str:
        profile = metadata.get("profile")
        if profile and profile in self._profiles.get("profiles", {}):
            return str(profile)
        return "twitter"

    def _score_features(self, metrics: Mapping[str, Any]) -> tuple[float, List[str], List[str]]:
        passed: list[str] = []
        failed: list[str] = []
        score = 0.0

        features: Mapping[str, Mapping[str, Any]] = self._weights.get("features", {})
        for name, cfg in features.items():
            value = metrics.get(name)
            weight = cfg.get("weight", 0)
            if value is None:
                continue

            meets_min = cfg.get("min") is None or value >= cfg["min"]
            meets_max = cfg.get("max") is None or value <= cfg["max"]
            if meets_min and meets_max:
                score += weight
                passed.append(name)
            else:
                score -= weight * 0.5
                failed.append(name)

        normalised = max(min(score / self._weights_sum, 1.0), -1.0)
        return normalised, passed, failed

    def _build_analysis_summary(
        self,
        prompt: str,
        metrics: Mapping[str, Any],
        scores: Mapping[str, Any],
    ) -> str:
        top_metrics = ", ".join(
            f"{key}={metrics[key]}" for key in list(metrics.keys())[:4]
        )
        score_parts = ", ".join(
            f"{key}:{value}" for key, value in list(scores.items())[:3]
        )
        summary = f"Analyst review of '{prompt[:60]}': metrics({top_metrics or 'n/a'})"
        if score_parts:
            summary += f"; scores({score_parts})"
        return summary

    def _build_stage_prompt(
        self,
        route: str,
        prompt: str,
        metadata: Mapping[str, Any],
        *,
        decision: Optional[dict[str, Any]] = None,
    ) -> str:
        base = f"Prompt: {prompt}"
        segments = [base]
        metrics = metadata.get("metrics")
        if isinstance(metrics, Mapping):
            segments.append(f"Metrics: {json.dumps(metrics, ensure_ascii=False)}")
        scores = metadata.get("scores")
        if isinstance(scores, Mapping):
            segments.append(f"Scores: {json.dumps(scores, ensure_ascii=False)}")
        if decision:
            segments.append(f"Decision context: {json.dumps(decision, ensure_ascii=False)}")
        return '\n'.join(segments)

    def _evaluate_risk(self, metadata: Mapping[str, Any]) -> dict[str, Any]:
        flags = metadata.get("risk_flags", {})
        scores = metadata.get("scores", {})
        metrics = metadata.get("metrics", {})

        critical_hits = self._check_critical(flags, scores)
        warnings = self._check_warnings(metrics)

        policy_snapshot = {
            "fail_closed": self._risk_policy.get("fail_closed", True),
            "critical": list(self._risk_policy.get("critical", {}).keys()),
            "base_requirements": list(self._risk_policy.get("base_requirements", {}).keys()),
        }
        return {
            "critical_hits": critical_hits,
            "warnings": warnings,
            "policy_snapshot": policy_snapshot,
        }

    def _check_critical(self, flags: Mapping[str, Any], scores: Mapping[str, Any]) -> list[str]:
        hits: list[str] = []
        critical: Mapping[str, Any] = self._risk_policy.get("critical", {})
        for key, requirement in critical.items():
            if isinstance(requirement, bool):
                if flags.get(key) is True:
                    hits.append(key)
            else:
                value = self._extract_numeric(key, scores, flags)
                if value is not None and value < requirement:
                    hits.append(key)
        return hits

    def _check_warnings(self, metrics: Mapping[str, Any]) -> list[str]:
        warnings: list[str] = []
        base_req: Mapping[str, Any] = self._risk_policy.get("base_requirements", {})
        for key, requirement in base_req.items():
            value = self._extract_numeric(key, metrics, metrics)
            if value is None:
                continue
            if isinstance(requirement, bool):
                if requirement and not value:
                    warnings.append(key)
            else:
                if value < requirement:
                    warnings.append(key)
        return warnings

    def _extract_numeric(self, key: str, *sources: Mapping[str, Any]) -> Optional[float]:
        for source in sources:
            if key in source:
                try:
                    return float(source[key])
                except (TypeError, ValueError):
                    return None
        return None

    def _decide(self, analyst_score: float, risk_eval: Mapping[str, Any]) -> dict[str, Any]:
        critical_hits: Iterable[str] = risk_eval.get("critical_hits", [])
        warnings: Iterable[str] = risk_eval.get("warnings", [])
        fail_closed = self._risk_policy.get("fail_closed", True)

        score = max(min(analyst_score, 1.0), -1.0)
        verdict: str
        confidence: float
        risk_level: str

        if fail_closed and critical_hits:
            verdict = "NO"
            confidence = 0.15
            risk_level = "high"
        else:
            if score >= 0.6:
                verdict = "BUY"
                risk_level = "medium" if warnings else "low"
                confidence = 0.85 if not warnings else 0.65
            elif score >= 0.25:
                verdict = "WATCH"
                risk_level = "medium"
                confidence = 0.55
            else:
                verdict = "NO"
                risk_level = "high" if warnings else "medium"
                confidence = 0.35

        return {
            "verdict": verdict,
            "score": round(score, 3),
            "risk_level": risk_level,
            "confidence": round(confidence, 3),
            "critical_hits": list(critical_hits),
            "warnings": list(warnings),
            "fallback_used": False,
        }


__all__ = ["TripleAIPipeline", "PipelineResult", "ModuleOutput"]
