from du_phong.gg_dich_du_phong import gg_dich_du_phong


def test_repair_message_prefix():
    gg = gg_dich_du_phong()
    goc = '[message] &cYou do not have enough money!'
    da_mo = '[tin nhắn]&cBạn không có đủ tiền!'
    fixed = gg._repair_prefix_and_spacing(goc, da_mo)
    assert fixed.startswith('[message] ')
    assert '[tin nhắn]' not in fixed


def test_repair_rawmsg_prefix_spacing():
    gg = gg_dich_du_phong()
    goc = '[console] rawmsg %player_name% true &a&lWEBSITE'
    da_mo = '[console] rawmsg%player_name%ĐÚNG VẬY&a&lTRANG WEB'
    fixed = gg._repair_prefix_and_spacing(goc, da_mo)
    assert fixed.startswith('[console] rawmsg %player_name% true ')
    assert 'rawmsg%player_name%' not in fixed


def test_url_not_cacheable():
    gg = gg_dich_du_phong()
    assert gg._co_the_cache_fragment('Visit www.yourserver.com now') is False
