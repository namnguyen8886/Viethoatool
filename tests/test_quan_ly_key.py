import pytest
from loi.quan_ly_key import quan_ly_key

@pytest.mark.asyncio
async def test_ban_key_sau_3_lan_429():
    ql = quan_ly_key(['k1'])
    await ql.danh_dau_429('k1')
    await ql.danh_dau_429('k1')
    await ql.danh_dau_429('k1')
    thong_ke = ql.thong_ke()[0]
    assert thong_ke['status'] == 'banned_1d'
