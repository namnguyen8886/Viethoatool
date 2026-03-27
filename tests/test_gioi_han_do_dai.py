from du_phong.gioi_han_do_dai import gioi_han_do_dai


def test_gioi_han_do_dai():
    bo = gioi_han_do_dai()
    assert bo.hop_le('hello', 'xin chao') is True
    assert bo.hop_le('a', 'day la mot cau rat dai va lang mang') is False
