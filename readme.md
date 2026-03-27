# 🌐 Hệ Thống Dịch File v3.1.0

Dịch file Minecraft plugin, config, subtitle... dùng Gemini AI.

## Cài đặt

```bash
pip install -r requirements.txt
cp .env.example .env
# Sửa .env, điền GEMINI_API_KEY=AIza...
```

## 🖥️ CMD Panel (chọn số)

```bash
python panel_cmd.py
```

Menu số gồm: Dịch File, Quét Plugin, Quản lý Plugin, Quản lý Key, Thống kê, Web Panel...

## 🌐 Web Panel

```bash
uvicorn giao_tiep.api_rest:app --port 8000
# hoặc qua CMD Panel → chọn 7
```

Mở: http://localhost:8000

## 📚 Tính năng

| Tính năng | CMD | Web |
|-----------|-----|-----|
| Dịch file/zip/thư mục | ✅ | ✅ |
| Lọc plugin khi dịch | ✅ | ✅ |
| Quét folder plugin | ✅ | ✅ |
| Quản lý API Keys | ✅ | ✅ |
| Xem thống kê & log | ✅ | ✅ |
| Download kết quả | ✅ | ✅ |
| Chọn ngôn ngữ | ✅ | ✅ |

## Bug đã sửa

- Model `gemini-3-flash-preview` → `gemini-2.0-flash`
- Footer `# Translated by...` bị chèn vào file → đã xóa
- Encoding lỗi (latin-1, cp1252...) → tự động fallback
- Web panel trống → dashboard đầy đủ 6 tab
