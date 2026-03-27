import re

class tach_nho_noi_dung:
    def tach(self, noi_dung: str, gioi_han: int = 220) -> list[str]:
        gioi_han = int(gioi_han or 220)
        if len(noi_dung or '') <= gioi_han:
            return [noi_dung]
        mang = re.split(r'(?<=[\.\!\?;:])\s+', noi_dung)
        ket_qua = []
        bo_dem = ''
        for doan in mang:
            if len(bo_dem) + len(doan) + 1 <= gioi_han:
                bo_dem = f'{bo_dem} {doan}'.strip()
            else:
                if bo_dem:
                    ket_qua.append(bo_dem)
                bo_dem = doan
        if bo_dem:
            ket_qua.append(bo_dem)
        return ket_qua or [noi_dung]
