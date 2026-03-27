from __future__ import annotations

def dem_fail(report):
    hk = (report or {}).get('hau_kiem') or {}
    if hk.get('hop_le'):
        return 0
    return max(1, len(hk.get('loi', []) or []))


def can_hardcore(report):
    hk = (report or {}).get('hau_kiem') or {}
    if hk.get('hop_le'):
        return False
    loi = set(hk.get('loi', []) or [])
    return any(any(k in x for k in ('placeholder', 'token', 'url_domain', 'yaml', 'action_tag', 'prefix')) for x in loi) or bool(loi)

AUTO_MODES = ('auto1', 'auto2', 'auto3')
