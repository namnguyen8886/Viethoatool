class tu_dien_du_phong:
    def __init__(self):
        self.du_lieu = {
            'Close': 'Đóng',
            'Back': 'Quay lại',
            'Open': 'Mở',
            'Save': 'Lưu',
            'Cancel': 'Hủy',
            'Confirm': 'Xác nhận',
            'Enabled': 'Bật',
            'Disabled': 'Tắt',
            'Loading...': 'Đang tải...',
            'Cooldown': 'Hồi chiêu',
            'Charge': 'Tụ lực',
            'Tier': 'Bậc',
        }

    def lay(self, van_ban: str):
        return self.du_lieu.get(van_ban)
