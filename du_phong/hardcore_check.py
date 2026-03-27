from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

STYLE_RE = re.compile(r'(?:[&§][0-9a-fk-orA-FK-OR])+')
HEX_RE = re.compile(r'(?:&#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{6}|<#[0-9A-Fa-f]{6}>|\{#[0-9A-Fa-f]{6}\})')
PLACEHOLDER_RE = re.compile(r'(?:%[^%\s]+%|\{[^{}\n]+\}|<[^<>\n]+>)')
NUMBER_RE = re.compile(r'\d+(?:[.,]\d+)*')
WORD_RE = re.compile(r'[A-Za-zÀ-ỹ]+(?:[+\-][A-Za-zÀ-ỹ0-9]+)?')
SPACE_RE = re.compile(r'\s+')
PUNCT_RE = re.compile(r'[^\w\s]')

TOKEN_PATTERNS = [STYLE_RE, HEX_RE, PLACEHOLDER_RE, NUMBER_RE, WORD_RE, SPACE_RE, PUNCT_RE]

@dataclass
class hc_string:
    sid: int
    path: str
    raw: str
    text: str
    tokens: list[str]


def fine_tokenize(text: str) -> list[str]:
    out: list[str] = []
    s = text or ''
    i = 0
    while i < len(s):
        for regex in TOKEN_PATTERNS:
            m = regex.match(s, i)
            if m:
                out.append(m.group(0))
                i = m.end()
                break
        else:
            out.append(s[i])
            i += 1
    merged: list[str] = []
    for tok in out:
        if not tok:
            continue
        if merged and SPACE_RE.fullmatch(tok) and SPACE_RE.fullmatch(merged[-1]):
            merged[-1] += tok
        else:
            merged.append(tok)
    return merged


def format_tokens_for_display(tokens: Iterable[str]) -> str:
    return ' '.join(f'{i}.{tok}' for i, tok in enumerate(tokens, 1))


def parse_hardcore_main(cmd: str) -> tuple[set[int], set[int], bool]:
    cmd = (cmd or '').strip()
    if not cmd:
        return set(), set(), True
    if cmd == '0':
        return set(), set(), False
    skip_ids: set[int] = set()
    fix_ids: set[int] = set()
    for part in cmd.split():
        if part.upper().endswith('F') and part[:-1].isdigit():
            fix_ids.add(int(part[:-1]))
        elif part.isdigit():
            skip_ids.add(int(part))
    return skip_ids, fix_ids, None


def parse_lock_line(cmd: str) -> tuple[int | None, list[str]]:
    cmd = (cmd or '').strip()
    if not cmd:
        return None, []
    parts = cmd.split()
    if not parts or not parts[0].isdigit():
        return None, []
    return int(parts[0]), parts[1:]
