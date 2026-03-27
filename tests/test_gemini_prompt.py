from loi.gemini_loi import gemini_loi
from cau_hinh.cai_dat import cai_dat_he_thong


def test_prompt_giu_cac_rule_quan_trong():
    cd = cai_dat_he_thong()
    bo = gemini_loi(cd)
    prompt = bo._create_prompt('hello', 'a.yml', 'en', 'vi', 'config')
    assert 'Return ONLY translated content' in prompt
    assert 'PRESERVE config keys - translate values only' in prompt
    assert 'DO NOT add any comment/footer/watermark to output' in prompt
