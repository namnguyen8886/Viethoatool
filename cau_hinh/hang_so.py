from pathlib import Path

thu_muc_goc = Path(__file__).resolve().parents[1]
thu_muc_du_lieu = thu_muc_goc / 'du_lieu'
thu_muc_log = thu_muc_du_lieu / 'log'
thu_muc_tam = thu_muc_du_lieu / 'tam'
thu_muc_cache = thu_muc_du_lieu / 'cache'
thu_muc_tri_nho = thu_muc_du_lieu / 'tri_nho'
thu_muc_bao_cao = thu_muc_du_lieu / 'bao_cao'
thu_muc_ket_qua = thu_muc_du_lieu / 'ket_qua'
thu_muc_du_lieu_gg = thu_muc_goc / 'du_lieu_gg'

for thu_muc in [
    thu_muc_du_lieu,
    thu_muc_log,
    thu_muc_tam,
    thu_muc_cache,
    thu_muc_tri_nho,
    thu_muc_bao_cao,
    thu_muc_ket_qua,
    thu_muc_du_lieu_gg,
]:
    thu_muc.mkdir(parents=True, exist_ok=True)
