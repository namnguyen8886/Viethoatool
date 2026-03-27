from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class manual_hardcore_rules:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path or Path(__file__).resolve().parents[1] / 'du_lieu' / 'tri_nho' / 'manual_hardcore_rules.json')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data = {'items': []}
        self._loaded = False

    def load(self):
        if self._loaded:
            return self.data
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding='utf-8'))
            except Exception:
                self.data = {'items': []}
        self._loaded = True
        return self.data

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding='utf-8')

    def _norm(self, text: str) -> str:
        return (text or '').strip()

    def _find(self, file_name: str, raw_text: str) -> dict[str, Any] | None:
        self.load()
        file_name = file_name or ''
        raw_text = self._norm(raw_text)
        for item in self.data.get('items', []):
            if item.get('file_name', '') == file_name and item.get('raw_text', '') == raw_text:
                return item
        return None

    def get(self, file_name: str, raw_text: str):
        return self._find(file_name, raw_text)

    def set_skip(self, file_name: str, raw_text: str):
        self.load()
        item = self._find(file_name, raw_text)
        if item is None:
            item = {'file_name': file_name or '', 'raw_text': self._norm(raw_text)}
            self.data.setdefault('items', []).append(item)
        item['action'] = 'skip'
        item['locks'] = []
        self.save()

    def set_locks(self, file_name: str, raw_text: str, locks: list[str]):
        self.load()
        item = self._find(file_name, raw_text)
        if item is None:
            item = {'file_name': file_name or '', 'raw_text': self._norm(raw_text)}
            self.data.setdefault('items', []).append(item)
        item['action'] = 'lock'
        item['locks'] = [x for x in (locks or []) if x]
        self.save()
