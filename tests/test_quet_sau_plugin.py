import zipfile
from pathlib import Path
from xu_ly_file.quet_sau import quet_sau


def test_quet_sau_chi_lay_plugin_da_chon(tmp_path: Path):
    z = tmp_path / 'b.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        zf.writestr('plugins/MythicHUD/messages.yml', 'a: hello')
        zf.writestr('plugins/ProtocolLib/config.yml', 'b: world')
    bo = quet_sau()
    kq = bo.quet(z, ds_plugin_can_dao=['MythicHUD'])
    assert any('MythicHUD/messages.yml' in x for x in kq['can_dich'])
    assert not any('ProtocolLib/config.yml' in x for x in kq['can_dich'])
