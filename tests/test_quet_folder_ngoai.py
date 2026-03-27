import zipfile
from pathlib import Path
from xu_ly_file.quet_folder_ngoai import quet_folder_ngoai


def test_quet_folder_ngoai_tim_duoc_plugin(tmp_path: Path):
    z = tmp_path / 'a.zip'
    with zipfile.ZipFile(z, 'w') as zf:
        zf.writestr('plugins/MythicHUD/messages.yml', 'a: hello')
        zf.writestr('plugins/MythicHUD/config.yml', 'b: world')
        zf.writestr('resource_pack/assets/test.png', 'x')
    bo = quet_folder_ngoai()
    kq = bo.quet(z)
    paths = [x['path'] for x in kq['muc']]
    assert any('MythicHUD' in p for p in paths)
