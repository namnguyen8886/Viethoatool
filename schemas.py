from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class MetaResponse(BaseModel):
    request_id: str | None = None
    timestamp: int | None = None


class ErrorDetail(BaseModel):
    code: str
    detail: str | None = None


class ApiResponse(BaseModel):
    ok: bool = True
    message: str = "OK"
    data: Any = None
    error: ErrorDetail | None = None
    meta: MetaResponse = Field(default_factory=MetaResponse)


class GeminiPromptUpdateRequest(BaseModel):
    prompt: str = Field(min_length=1)


class PluginModifyRequest(BaseModel):
    ten: str = Field(min_length=1)


class RunBody(BaseModel):
    lang_from: str = 'auto'
    lang_to: str = 'vi'


class SettingsData(BaseModel):
    source_lang: str = 'auto'
    target_lang: str = 'vi'
    gemini_model: str = 'gemini-2.5-flash'
    gemini_workers: int = 4
    gg_workers: int = 40
    gemini_chunk_chars: int = 5000
    gg_chunk_chars: int = 700
    fallback_enabled: bool = True
    gofile_upload: bool = True
    api_key_enabled: bool = False
    api_key_preview: str | None = None


class SettingsUpdateRequest(BaseModel):
    source_lang: str | None = None
    target_lang: str | None = None
    gemini_model: str | None = None
    gemini_workers: int | None = None
    gg_workers: int | None = None
    gemini_chunk_chars: int | None = None
    gg_chunk_chars: int | None = None
    fallback_enabled: bool | None = None
    gofile_upload: bool | None = None
    api_key_enabled: bool | None = None
    api_key: str | None = None


EngineMode = Literal[
    'auto', 'gemini_only', 'gg_only', 'gemini_preferred', 'gg_preferred'
]
ScanMode = Literal['all_supported', 'plugin_only', 'selected_plugins']
FileType = Literal['auto', 'text', 'yaml', 'json', 'lang', 'properties', 'zip']


class ShieldCheckRequest(BaseModel):
    text: str = Field(min_length=1)
    file_type: FileType = 'yaml'
    parent: str = ''
    path: str = ''


class TranslateFileRequest(BaseModel):
    path: str = Field(min_length=1)
    source_lang: str = 'auto'
    target_lang: str = 'vi'
    engine_mode: EngineMode = 'auto'
    style_prompt: str = ''
    scan_mode: ScanMode = 'all_supported'
    selected_plugins: list[str] = Field(default_factory=list)


class TranslateTextRequest(BaseModel):
    text: str = Field(min_length=1)
    source_lang: str = 'auto'
    target_lang: str = 'vi'
    engine_mode: EngineMode = 'auto'
    file_type: FileType = 'text'
    style_prompt: str = ''
    return_debug: bool = False
