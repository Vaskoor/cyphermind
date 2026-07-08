"""Wordlist management API — upload, status, seclists paths."""
from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.tools.wordlists import DNS_DIR, PARAMS_DIR, WEB_DIR, wordlist_status

router = APIRouter(prefix="/wordlists", tags=["wordlists"])

KIND_DIRS = {"dns": DNS_DIR, "web": WEB_DIR, "params": PARAMS_DIR}


class WordlistConfig(BaseModel):
    dns_wordlist: str | None = None
    web_wordlist: str | None = None
    params_wordlist: str | None = None


@router.get("/status")
async def get_wordlist_status():
    status = wordlist_status()
    status["recommended_seclists"] = {
        "dns": [
            "/usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt",
            "/usr/share/seclists/Discovery/DNS/dns-Jhaddix.txt",
        ],
        "web": [
            "/usr/share/seclists/Discovery/Web-Content/common.txt",
            "/usr/share/seclists/Discovery/Web-Content/raft-large-directories.txt",
        ],
        "params": [
            "/usr/share/seclists/Discovery/Web-Content/burp-parameter-names.txt",
        ],
    }
    status["env_vars"] = {
        "DNS_WORDLIST": "Path to DNS/subdomain bruteforce wordlist",
        "WEB_WORDLIST": "Path to directory fuzzing wordlist",
        "PARAMS_WORDLIST": "Path to parameter discovery wordlist",
    }
    return status


@router.get("/methodology")
async def get_methodology():
    from app.services.methodology_runner import get_pipeline_options
    return get_pipeline_options()


@router.post("/upload/{kind}")
async def upload_wordlist(kind: str, file: UploadFile = File(...)):
    if kind not in KIND_DIRS:
        raise HTTPException(400, f"kind must be one of: {', '.join(KIND_DIRS)}")

    if not file.filename:
        raise HTTPException(400, "Filename required")

    dest_dir = KIND_DIRS[kind]
    safe_name = Path(file.filename).name
    dest = dest_dir / safe_name

    try:
        with dest.open("wb") as f:
            shutil.copyfileobj(file.file, f)
    except OSError as exc:
        raise HTTPException(500, f"Failed to save wordlist: {exc}") from exc

    lines = sum(1 for _ in dest.open(encoding="utf-8", errors="replace"))
    return {
        "kind": kind,
        "path": str(dest),
        "filename": safe_name,
        "lines": lines,
        "hint": f"Add to .env: {kind.upper()}_WORDLIST={dest}",
    }
