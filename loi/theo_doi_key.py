from dataclasses import dataclass

@dataclass
class trang_thai_key:
    key: str
    status: str = 'active'
    last_used_at: float = 0.0
    cooldown_until: float = 0.0
    ban_until: float = 0.0
    quota_fail_count: int = 0
    reason: str = ''
