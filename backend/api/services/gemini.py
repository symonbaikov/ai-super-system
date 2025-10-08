from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


@dataclass(frozen=True)
class GeminiAccount:
    handle: str
    description: Optional[str]

    @property
    def searchable_text(self) -> str:
        base = self.handle.lower()
        if self.description:
            return f"{base} {self.description.lower()}"
        return base


class GeminiService:
    """Offline Gemini helper that ranks tracked accounts for a prompt."""

    def __init__(
        self,
        repo_root: Path,
        *,
        accounts_json: Optional[Path] = None,
        accounts_doc_glob: str = "*Сводный_список_аккаунтов*",
        max_results: int = 8,
        input_cost_per_token: float = 0.0000025,
        output_cost_per_token: float = 0.000005,
    ) -> None:
        self._repo_root = repo_root
        self._accounts_json = (
            accounts_json
            if accounts_json is not None
            else repo_root
            / "backend"
            / "configs"
            / "derived"
            / "accounts_x.json"
        )
        self._accounts_doc_glob = accounts_doc_glob
        self._max_results = max_results
        self._input_cost = input_cost_per_token
        self._output_cost = output_cost_per_token
        self._accounts: list[GeminiAccount] = self._load_accounts()

    @property
    def accounts(self) -> Sequence[GeminiAccount]:
        return tuple(self._accounts)

    def infer(self, prompt: str, *, strategy_id: Optional[str] = None, model: Optional[str] = None) -> dict[str, object]:
        """Return Gemini-style insight over the tracked account universe."""

        keywords = self._extract_keywords(prompt)
        ranked = self._rank_accounts(keywords)

        if not ranked:
            ranked = [
                {
                    "handle": account.handle,
                    "description": account.description,
                    "score": 0,
                }
                for account in self._accounts[: self._max_results]
            ]

        summary = self._build_summary(prompt, ranked, keywords, strategy_id=strategy_id, model=model)
        input_tokens = max(1, self._count_tokens(prompt))
        output_tokens = max(1, self._count_tokens(summary))
        cost = round(input_tokens * self._input_cost + output_tokens * self._output_cost, 6)

        return {
            "text": summary,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost_usd": cost,
            "accounts": ranked,
        }

    def _rank_accounts(self, keywords: Sequence[str]) -> list[dict[str, object]]:
        if not keywords:
            return []

        scored: list[tuple[float, GeminiAccount, dict[str, int]]] = []
        for account in self._accounts:
            scores = {kw: account.searchable_text.count(kw) for kw in keywords if kw in account.searchable_text}
            if not scores:
                continue
            total = sum(scores.values()) + (0.2 if account.description else 0.0)
            scored.append((total, account, scores))

        scored.sort(key=lambda item: (-item[0], item[1].handle.lower()))

        results: list[dict[str, object]] = []
        for total, account, scores in scored[: self._max_results]:
            results.append(
                {
                    "handle": account.handle,
                    "description": account.description,
                    "score": round(total, 3),
                    "keywords": sorted(scores.keys()),
                }
            )
        return results

    def _build_summary(
        self,
        prompt: str,
        ranked: list[dict[str, object]],
        keywords: Sequence[str],
        *,
        strategy_id: Optional[str],
        model: Optional[str],
    ) -> str:
        parts: list[str] = []
        if keywords:
            joined_keywords = ", ".join(sorted(keywords))
            parts.append(f"Gemini scanned {len(self._accounts)} tracked accounts for keywords: {joined_keywords}.")
        else:
            parts.append(
                f"Gemini scanned {len(self._accounts)} tracked accounts."
            )

        if ranked:
            account_texts = []
            for entry in ranked:
                snippet = entry["handle"]
                desc = entry.get("description")
                if isinstance(desc, str) and desc:
                    snippet = f"{snippet} — {desc}"
                account_texts.append(snippet)
            parts.append("Top matches: " + "; ".join(account_texts) + ".")
        else:
            parts.append("No direct matches were found; returning the watchlist head.")

        if strategy_id:
            parts.append(f"Strategy context: {strategy_id}.")
        if model:
            parts.append(f"Model: {model}.")
        parts.append(f"Prompt preview: {prompt[:160].strip()}" + ("…" if len(prompt) > 160 else "."))
        return " ".join(parts)

    @staticmethod
    def _count_tokens(text: str) -> int:
        return len(re.findall(r"[\w$#@]+", text))

    @staticmethod
    def _extract_keywords(prompt: str) -> List[str]:
        raw_tokens = re.findall(r"[\w$#@]{3,}", prompt.lower())
        keywords = set()
        for token in raw_tokens:
            cleaned = token.strip("#$")
            if len(cleaned) >= 3:
                keywords.add(cleaned)
        return sorted(keywords)

    def _load_accounts(self) -> list[GeminiAccount]:
        handles = self._load_handles()
        annotations = self._load_account_annotations()
        accounts: list[GeminiAccount] = []
        seen = set()

        for handle in handles:
            key = handle.lower()
            desc = annotations.get(key)
            accounts.append(GeminiAccount(handle=handle, description=desc))
            seen.add(key)

        for key, desc in annotations.items():
            if key not in seen:
                accounts.append(GeminiAccount(handle=key, description=desc))

        if not accounts:
            raise RuntimeError("No Gemini accounts were loaded; check documentation sources.")

        return accounts

    def _load_handles(self) -> list[str]:
        if not self._accounts_json.exists():
            return []
        try:
            data = json.loads(self._accounts_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Failed to parse {self._accounts_json}") from exc

        handles = []
        for entry in data:
            if isinstance(entry, str) and entry.startswith("@"):
                handles.append(entry)
        return handles

    def _load_account_annotations(self) -> dict[str, str]:
        sources_dir = self._repo_root / "backend" / "docs" / "sources"
        if not sources_dir.exists():
            return {}
        files = sorted(sources_dir.glob(self._accounts_doc_glob))
        if not files:
            return {}
        annotations: dict[str, str] = {}
        for path in files:
            annotations.update(self._parse_accounts_doc(path))
        return annotations

    def _parse_accounts_doc(self, path: Path) -> dict[str, str]:
        annotations: dict[str, str] = {}
        current_handle: Optional[str] = None
        buffer: list[str] = []

        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith("№") or line.startswith("Аккаунт") or line.startswith("Описание"):
                continue
            if line.isdigit():
                if current_handle is not None and buffer:
                    annotations[current_handle.lower()] = " ".join(buffer).strip()
                current_handle = None
                buffer = []
                continue
            if line.startswith("@"):
                if current_handle is not None and buffer:
                    annotations[current_handle.lower()] = " ".join(buffer).strip()
                current_handle = line
                buffer = []
                continue
            if current_handle:
                buffer.append(line)

        if current_handle is not None and buffer:
            annotations[current_handle.lower()] = " ".join(buffer).strip()
        return annotations

