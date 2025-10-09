from __future__ import annotations

import json
import re
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import httpx


@dataclass(frozen=True)
class GeminiAccount:
    handle: str
    description: Optional[str]
    keywords: tuple[str, ...] = ()
    clusters: tuple[str, ...] = ()
    mints: tuple[str, ...] = ()
    weight: float = 1.0

    @property
    def searchable_text(self) -> str:
        parts = [self.handle.lower()]
        if self.description:
            parts.append(self.description.lower())
        if self.keywords:
            parts.extend(self.keywords)
        if self.clusters:
            parts.extend(cluster.lower() for cluster in self.clusters)
        if self.mints:
            parts.extend(mint.lower() for mint in self.mints)
        return " ".join(parts)


class GeminiRemoteError(RuntimeError):
    """Raised when Flowith/Gemini returns an unexpected response."""


class GeminiService:
    """Gemini helper that prefers the live Flowith API and falls back to the corpus."""

    def __init__(
        self,
        repo_root: Path,
        *,
        accounts_json: Optional[Path] = None,
        accounts_metadata: Optional[Path] = None,
        accounts_doc_glob: str = "*Сводный_список_аккаунтов*",
        accounts_cache: Optional[Path] = None,
        max_results: int = 8,
        input_cost_per_token: float = 0.0000025,
        output_cost_per_token: float = 0.000005,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 15.0,
        http_client: Optional[httpx.Client] = None,
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
        self._accounts_metadata = (
            accounts_metadata
            if accounts_metadata is not None
            else repo_root
            / "backend"
            / "configs"
            / "derived"
            / "gemini_accounts.json"
        )
        self._accounts_cache = (
            accounts_cache
            if accounts_cache is not None
            else repo_root
            / "backend"
            / "configs"
            / "derived"
            / "gemini_accounts_cache.json"
        )
        self._accounts_doc_glob = accounts_doc_glob
        self._max_results = max_results
        self._input_cost = input_cost_per_token
        self._output_cost = output_cost_per_token
        self._api_url = api_url.strip() if api_url else None
        self._api_key = api_key.strip() if api_key else None
        self._timeout = timeout
        self._http_client = http_client
        self._owns_client = False
        if self._api_url and self._api_key and self._http_client is None:
            self._http_client = httpx.Client(timeout=self._timeout)
            self._owns_client = True
        self._account_map: dict[str, GeminiAccount] = {}
        self._accounts: list[GeminiAccount] = self._load_accounts()

    def close(self) -> None:
        if self._owns_client and self._http_client is not None:
            self._http_client.close()
            self._http_client = None
            self._owns_client = False

    @property
    def accounts(self) -> Sequence[GeminiAccount]:
        return tuple(self._accounts)

    def infer(self, prompt: str, *, strategy_id: Optional[str] = None, model: Optional[str] = None) -> dict[str, object]:
        """Return Gemini-style insight over the tracked account universe."""

        keywords = self._extract_keywords(prompt)
        ranked = self._rank_accounts(keywords)
        fallback_accounts = self._ensure_accounts(ranked)

        remote_payload = None
        if self._api_url and self._api_key and self._http_client is not None:
            try:
                remote_payload = self._call_remote(prompt, model=model, strategy_id=strategy_id)
            except GeminiRemoteError as exc:
                logging.getLogger(__name__).warning("Gemini remote call failed: %s", exc)
            except httpx.HTTPError as exc:
                logging.getLogger(__name__).warning("Gemini HTTP error: %s", exc)

        if remote_payload is not None:
            return self._build_remote_response(
                remote_payload,
                prompt,
                fallback_accounts,
                keywords,
                strategy_id=strategy_id,
                model=model,
            )

        summary = self._build_summary(prompt, fallback_accounts, keywords, strategy_id=strategy_id, model=model)
        input_tokens = max(1, self._count_tokens(prompt))
        output_tokens = max(1, self._count_tokens(summary))
        cost = round(input_tokens * self._input_cost + output_tokens * self._output_cost, 6)

        response: dict[str, object] = {
            "text": summary,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost_usd": cost,
            "accounts": fallback_accounts,
            "provider": "flowith-local",
            "analysis": self._build_analysis(fallback_accounts, keywords),
            "usage": {
                "requests": 1,
                "matched_accounts": len(
                    [entry for entry in fallback_accounts if (entry.get("score") or 0) > 0]
                ),
                "fallback_mode": True,
            },
        }
        return response

    def _call_remote(
        self,
        prompt: str,
        *,
        model: Optional[str],
        strategy_id: Optional[str],
    ) -> Any:
        if not self._http_client or not self._api_url or not self._api_key:
            raise GeminiRemoteError("Remote Gemini client is not configured")

        payload: Dict[str, Any] = {
            "model": model or "gemini-2.5-flash",
            "input": prompt,
            "output_format": "json",
            "max_output_tokens": 400,
        }
        if strategy_id:
            payload["metadata"] = {"strategyId": strategy_id}

        response = self._http_client.post(
            self._api_url,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data = response.json()
        if data is None:
            raise GeminiRemoteError("Empty response from Gemini")
        return data

    def _build_remote_response(
        self,
        payload: Any,
        prompt: str,
        fallback_accounts: list[dict[str, object]],
        keywords: Sequence[str],
        *,
        strategy_id: Optional[str],
        model: Optional[str],
    ) -> dict[str, object]:
        text = self._extract_remote_text(payload)
        accounts = self._extract_remote_accounts(payload) or fallback_accounts
        tokens = self._extract_remote_tokens(payload)
        if tokens is None:
            tokens = {
                "input": max(1, self._count_tokens(prompt)),
                "output": max(1, self._count_tokens(text or "")),
            }
        else:
            tokens = {
                "input": max(1, int(tokens.get("input", tokens.get("prompt", 0)) or 0)),
                "output": max(1, int(tokens.get("output", tokens.get("completion", 0)) or 0)),
            }

        summary = text or self._build_summary(prompt, accounts, keywords, strategy_id=strategy_id, model=model)
        output_tokens = tokens["output"]
        input_tokens = tokens["input"]
        cost = self._extract_remote_cost(payload)
        if cost is None:
            cost = round(input_tokens * self._input_cost + output_tokens * self._output_cost, 6)

        response: dict[str, object] = {
            "text": summary,
            "tokens": {"input": input_tokens, "output": output_tokens},
            "cost_usd": float(cost),
            "accounts": accounts,
            "provider": "flowith",
        }

        analysis = self._extract_remote_analysis(payload)
        if analysis is not None:
            response["analysis"] = analysis
        else:
            response["analysis"] = self._build_analysis(accounts, keywords)

        usage = None
        if isinstance(payload, dict):
            usage = payload.get("usage")
        if isinstance(usage, dict):
            response["usage"] = usage
        else:
            response["usage"] = {
                "requests": 1,
                "matched_accounts": len([entry for entry in accounts if entry.get("handle")]),
                "fallback_mode": False,
            }

        return response

    def _ensure_accounts(self, ranked: list[dict[str, object]]) -> list[dict[str, object]]:
        if ranked:
            return ranked
        fallback = []
        for account in self._accounts[: self._max_results]:
            fallback.append(
                {
                    "handle": account.handle,
                    "description": account.description,
                    "score": 0,
                    "keywords": [],
                    "clusters": list(account.clusters),
                    "mints": list(account.mints),
                }
            )
        return fallback

    def _rank_accounts(self, keywords: Sequence[str]) -> list[dict[str, object]]:
        if not keywords:
            return []

        scored: list[tuple[float, GeminiAccount, dict[str, float]]] = []
        for account in self._accounts:
            matches: dict[str, float] = {}
            base = account.searchable_text
            if not base:
                continue
            for kw in keywords:
                weight = 0.0
                lowered = kw.lower()
                if lowered in base:
                    weight += base.count(lowered) * 0.6
                if account.keywords and lowered in account.keywords:
                    weight += 1.5
                if account.clusters and any(lowered in cluster.lower() for cluster in account.clusters):
                    weight += 1.1
                if account.mints and any(lowered in mint.lower() for mint in account.mints):
                    weight += 0.9
                if lowered in account.handle.lower():
                    weight += 1.2
                if weight:
                    matches[kw] = matches.get(kw, 0.0) + weight
            if not matches:
                continue
            total = sum(matches.values()) * account.weight
            if account.description:
                total += 0.2
            scored.append((total, account, matches))

        scored.sort(key=lambda item: (-item[0], item[1].handle.lower()))

        results: list[dict[str, object]] = []
        for total, account, scores in scored[: self._max_results]:
            sorted_keywords = sorted(scores, key=lambda kw: -scores[kw])
            results.append(
                {
                    "handle": account.handle,
                    "description": account.description,
                    "score": round(total, 3),
                    "keywords": sorted_keywords,
                    "clusters": list(account.clusters),
                    "mints": list(account.mints),
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
            cluster_counts: dict[str, int] = {}
            mint_counts: dict[str, int] = {}
            for entry in ranked:
                snippet = entry["handle"]
                desc = entry.get("description")
                if isinstance(desc, str) and desc:
                    snippet = f"{snippet} — {desc}"
                account_texts.append(snippet)
                account = self._account_map.get(entry["handle"].lower())
                if account:
                    for cluster in account.clusters:
                        cluster_counts[cluster] = cluster_counts.get(cluster, 0) + 1
                    for mint in account.mints:
                        mint_counts[mint] = mint_counts.get(mint, 0) + 1
            parts.append("Top matches: " + "; ".join(account_texts) + ".")
            if cluster_counts:
                clusters_preview = ", ".join(sorted(cluster_counts, key=lambda k: -cluster_counts[k])[:3])
                parts.append(f"Dominant clusters: {clusters_preview}.")
            if mint_counts:
                top_mints = ", ".join(sorted(mint_counts, key=lambda k: -mint_counts[k])[:4])
                parts.append(f"Mentioned tokens: {top_mints}.")
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
        if not text:
            return 0
        return len(re.findall(r"[\w$#@]+", text))

    def _build_analysis(self, ranked: list[dict[str, object]], keywords: Sequence[str]) -> dict[str, Any]:
        clusters: dict[str, int] = {}
        mints: dict[str, int] = {}
        for entry in ranked:
            account = self._account_map.get(str(entry.get("handle", "")).lower())
            if not account:
                continue
            for cluster in account.clusters:
                clusters[cluster] = clusters.get(cluster, 0) + 1
            for mint in account.mints:
                mints[mint] = mints.get(mint, 0) + 1

        sorted_clusters = sorted(clusters.items(), key=lambda item: (-item[1], item[0]))
        sorted_mints = sorted(mints.items(), key=lambda item: (-item[1], item[0]))

        return {
            "keywords": list(keywords),
            "clusters": [name for name, _ in sorted_clusters[:5]],
            "mints": [name for name, _ in sorted_mints[:8]],
            "matches": [
                {
                    "handle": entry.get("handle"),
                    "score": entry.get("score"),
                    "keywords": entry.get("keywords", []),
                }
                for entry in ranked
            ],
            "coverage": {
                "total_accounts": len(self._accounts),
                "matched_accounts": len(
                    [
                        entry
                        for entry in ranked
                        if entry.get("score") or entry.get("keywords") or entry.get("handle")
                    ]
                ),
            },
        }

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
        cached = self._load_cached_accounts()
        if cached:
            return cached

        handles = self._load_handles()
        annotations = self._load_account_annotations()
        metadata = self._load_account_metadata()
        accounts: list[GeminiAccount] = []
        seen = set()

        def build_account(handle: str, desc: Optional[str], meta: Optional[dict[str, Any]]) -> GeminiAccount:
            keywords: tuple[str, ...] = ()
            clusters: tuple[str, ...] = ()
            mints: tuple[str, ...] = ()
            weight = 1.0
            if meta:
                keywords = tuple(sorted({kw.lower() for kw in meta.get("keywords", []) if isinstance(kw, str)}))
                clusters = tuple(sorted({cl for cl in meta.get("clusters", []) if isinstance(cl, str)}))
                mints = tuple(sorted({mint for mint in meta.get("mints", []) if isinstance(mint, str)}))
                try:
                    weight = float(meta.get("weight", 1.0))
                except (TypeError, ValueError):
                    weight = 1.0
                if not desc and isinstance(meta.get("bio"), str):
                    desc = meta["bio"].strip()
            account = GeminiAccount(
                handle=handle,
                description=desc,
                keywords=keywords,
                clusters=clusters,
                mints=mints,
                weight=max(0.2, weight),
            )
            self._account_map[handle.lower()] = account
            return account

        for handle in handles:
            key = handle.lower()
            desc = annotations.get(key)
            accounts.append(build_account(handle, desc, metadata.get(key)))
            seen.add(key)

        for key, desc in annotations.items():
            if key not in seen:
                accounts.append(build_account(key, desc, metadata.get(key)))
                seen.add(key)

        for key, meta in metadata.items():
            if key not in seen:
                handle = meta.get("handle") if isinstance(meta, dict) else None
                handle = handle if isinstance(handle, str) and handle.startswith("@") else key
                desc = annotations.get(key)
                accounts.append(build_account(handle, desc, meta))
                seen.add(key)

        if not accounts:
            raise RuntimeError("No Gemini accounts were loaded; check documentation sources.")

        return accounts

    def _load_cached_accounts(self) -> list[GeminiAccount]:
        if not self._accounts_cache or not self._accounts_cache.exists():
            return []
        try:
            data = json.loads(self._accounts_cache.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []

        cached: list[GeminiAccount] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            handle = entry.get("handle")
            if not isinstance(handle, str) or not handle.startswith("@"):
                continue
            weight = entry.get("weight", 1.0)
            try:
                weight_value = float(weight)
            except (TypeError, ValueError):
                weight_value = 1.0

            cached.append(
                GeminiAccount(
                    handle=handle,
                    description=entry.get("description") if isinstance(entry.get("description"), str) else None,
                    keywords=tuple(
                        sorted({kw.lower() for kw in entry.get("keywords", []) if isinstance(kw, str)})
                    ),
                    clusters=tuple(
                        sorted({cluster for cluster in entry.get("clusters", []) if isinstance(cluster, str)})
                    ),
                    mints=tuple(
                        sorted({mint for mint in entry.get("mints", []) if isinstance(mint, str)})
                    ),
                    weight=max(0.2, weight_value),
                )
            )

        if cached:
            for account in cached:
                self._account_map[account.handle.lower()] = account
        return cached

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

    def _load_account_metadata(self) -> dict[str, dict[str, Any]]:
        if not self._accounts_metadata.exists():
            return {}
        try:
            data = json.loads(self._accounts_metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Failed to parse {self._accounts_metadata}") from exc

        metadata: dict[str, dict[str, Any]] = {}
        for entry in data:
            if not isinstance(entry, dict):
                continue
            handle = entry.get("handle")
            if isinstance(handle, str) and handle.startswith("@"):
                key = handle.lower()
            else:
                key = (handle or "").lower()
                if not key:
                    continue
            metadata[key] = entry
        return metadata

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

    @staticmethod
    def _extract_remote_text(payload: Any) -> Optional[str]:
        if isinstance(payload, dict):
            for key in ("text", "summary", "output"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return message.strip()
        if isinstance(payload, list) and payload:
            first = payload[0]
            if isinstance(first, dict):
                return GeminiService._extract_remote_text(first)
            if isinstance(first, str) and first.strip():
                return first.strip()
        if isinstance(payload, str) and payload.strip():
            return payload.strip()
        return None

    @staticmethod
    def _extract_remote_tokens(payload: Any) -> Optional[Dict[str, Any]]:
        if isinstance(payload, dict):
            for key in ("tokens", "usage"):
                value = payload.get(key)
                if isinstance(value, dict):
                    return value
            if "input_tokens" in payload or "output_tokens" in payload:
                return {
                    "input": payload.get("input_tokens"),
                    "output": payload.get("output_tokens"),
                }
        if isinstance(payload, list) and payload:
            return GeminiService._extract_remote_tokens(payload[0])
        return None

    @staticmethod
    def _extract_remote_cost(payload: Any) -> Optional[float]:
        if isinstance(payload, dict):
            if isinstance(payload.get("cost_usd"), (int, float)):
                return float(payload["cost_usd"])
            cost = payload.get("cost")
            if isinstance(cost, dict):
                usd = cost.get("usd")
                if isinstance(usd, (int, float)):
                    return float(usd)
        if isinstance(payload, list) and payload:
            return GeminiService._extract_remote_cost(payload[0])
        return None

    @staticmethod
    def _extract_remote_accounts(payload: Any) -> list[dict[str, object]]:
        accounts: list[dict[str, object]] = []
        candidates: Iterable[Any]
        if isinstance(payload, dict):
            if isinstance(payload.get("accounts"), list):
                candidates = payload["accounts"]
            elif isinstance(payload.get("results"), list):
                candidates = payload["results"]
            else:
                candidates = []
        elif isinstance(payload, list):
            candidates = payload
        else:
            candidates = []

        for entry in candidates:
            if not isinstance(entry, dict):
                continue
            handle = entry.get("handle") or entry.get("account") or entry.get("user")
            if not isinstance(handle, str) or not handle.strip():
                continue
            account: dict[str, object] = {"handle": handle.strip()}
            if isinstance(entry.get("description"), str):
                account["description"] = entry["description"].strip()
            if isinstance(entry.get("score"), (int, float)):
                account["score"] = round(float(entry["score"]), 3)
            keywords = entry.get("keywords")
            if isinstance(keywords, list):
                account["keywords"] = [str(item) for item in keywords if isinstance(item, str)]
            sentiment = entry.get("sentiment")
            if isinstance(sentiment, dict):
                account["sentiment"] = sentiment
            accounts.append(account)

        return accounts

    @staticmethod
    def _extract_remote_analysis(payload: Any) -> Optional[dict[str, Any]]:
        if isinstance(payload, dict):
            analysis = payload.get("analysis")
            if isinstance(analysis, dict):
                return analysis
        if isinstance(payload, list) and payload:
            return GeminiService._extract_remote_analysis(payload[0])
        return None

