"""Fine-tuning API — enable/disable, dataset export, config."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.finetuning import pipeline
from app.finetuning.state import DATASET_DIR

router = APIRouter(prefix="/finetuning", tags=["finetuning"])


class ToggleRequest(BaseModel):
    enabled: bool


class ConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    model_id: Optional[str] = None
    base_provider: Optional[str] = None
    api_base: Optional[str] = None
    roles: Optional[list[str]] = None
    pipeline_auto_export: Optional[bool] = None
    notes: Optional[str] = None


class BuildDatasetRequest(BaseModel):
    include_findings: bool = True
    include_memories: bool = True
    include_selfplay: bool = True
    max_samples: int = Field(2000, ge=1, le=10000)


@router.get("/status")
async def finetuning_status():
    return await pipeline.get_status()


@router.get("/health")
async def finetuning_health():
    return await pipeline.health_check()


@router.post("/toggle")
async def finetuning_toggle(body: ToggleRequest):
    """
    Enable or disable fine-tuned model routing at runtime.
    When disabled, all roles use normal providers (Kimi, Grok, etc.).
    """
    return await pipeline.toggle(body.enabled)


@router.post("/config")
async def finetuning_config(body: ConfigUpdate):
    """Update fine-tuning config (model ID, roles, base provider)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(400, "No updates provided")
    return await pipeline.update_config(updates)


@router.post("/build-dataset")
async def finetuning_build_dataset(body: BuildDatasetRequest):
    """
    Export training JSONL from findings, attack memory, and self-play.
    Upload the file to your provider's fine-tuning console (OpenAI, NVIDIA, etc.).
    """
    return await pipeline.build_dataset(**body.model_dump())


@router.get("/datasets")
async def list_datasets():
    from app.finetuning.dataset import list_datasets as _list
    return {"datasets": _list()}


@router.get("/datasets/{filename}/download")
async def download_dataset(filename: str):
    path = DATASET_DIR / filename
    if not path.exists() or ".." in filename:
        raise HTTPException(404, "Dataset not found")
    return FileResponse(path, filename=filename, media_type="application/jsonl")
