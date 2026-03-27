class gioi_han_do_dai:
    def hop_le(self, goc: str, dich: str) -> bool:
        if not goc:
            return True
        return len(dich) <= max(int(len(goc) * 1.8), len(goc) + 5)

    def can_tach(self, noi_dung: str, gioi_han: int = 220) -> bool:
        return len(noi_dung or '') > int(gioi_han or 220)
