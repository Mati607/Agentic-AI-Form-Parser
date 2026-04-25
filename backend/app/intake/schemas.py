from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FieldPatch(BaseModel):
    field_path: str = Field(..., min_length=1, max_length=500)
    value: Any
    reviewer_note: str | None = Field(default=None, max_length=2000)


class PatchFieldsRequest(BaseModel):
    patches: list[FieldPatch] = Field(default_factory=list, max_length=200)


class PromoteToSessionRequest(BaseModel):
    title: str | None = Field(default=None, max_length=500)
    default_form_url: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=5000)
