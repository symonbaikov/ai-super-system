"""Generate the Gemini account corpus from documentation sources.

This utility normalises the curated X account metadata that ships with the
repository so Docker images can rely on a precomputed dataset instead of
parsing the `.docx.txt` exports on startup. The script is intentionally
idempotent and can be invoked multiple times during development or inside the
Docker build.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.api.services.gemini import GeminiAccount, GeminiService


def _account_to_dict(account: GeminiAccount) -> dict[str, Any]:
    return {
        "handle": account.handle,
        "description": account.description,
        "keywords": list(account.keywords),
        "clusters": list(account.clusters),
        "mints": list(account.mints),
        "weight": account.weight,
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    output_path = repo_root / "backend" / "configs" / "derived" / "gemini_accounts_cache.json"

    service = GeminiService(repo_root)
    accounts = [_account_to_dict(account) for account in service.accounts]

    output_path.write_text(
        json.dumps(accounts, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
