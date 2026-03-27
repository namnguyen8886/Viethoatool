import time
import uuid
from dataclasses import dataclass, field

@dataclass
class job:
    ma_job: str
    trang_thai: str = 'pending'
    log: list[str] = field(default_factory=list)
    ket_qua: dict = field(default_factory=dict)
    tao_luc: float = field(default_factory=time.time)

class quan_ly_job:
    def __init__(self):
        self.ds: dict[str, job] = {}

    def tao_job(self) -> job:
        ma = uuid.uuid4().hex[:12]
        obj = job(ma_job=ma)
        self.ds[ma] = obj
        return obj

    def lay_job(self, ma_job: str) -> job | None:
        return self.ds.get(ma_job)
