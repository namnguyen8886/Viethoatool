from du_phong.khoa_cung_token import khoa_cung_token


def test_khoa_va_mo_token():
    bo = khoa_cung_token()
    goc = '&ahello %player% /spawn permission.use'
    kq = bo.khoa(goc)
    assert '__khoa_' in kq.noi_dung
    mo = bo.mo(kq.noi_dung, kq.bang_anh_xa)
    assert mo == goc
