## 1. Cấu hình API Key

1. Tạo một file tên là `.env` trong thư mục dự án (hoặc copy từ `.env.example`).
2. Mở file và điền API Key của bạn vào:
3. 
# Lấy key tại: [https://aistudio.google.com/](https://aistudio.google.com/)
 ```env
   GEMINI_API_KEY=AIzaSy_YOUR_API_KEY_HERE
   
   # Tùy chọn model (nếu cần)
   MODEL_PRIORITY=gemini-2.5-pro,gemini-2.5-flash,gemini-1.5-pro,gemini-1.5-flash
```

## 2. Build và Chạy Docker

Mở Terminal tại thư mục dự án và chạy lệnh sau để khởi động:

```bash
docker-compose up --build -d
```
-----

**Kiểm tra:**
Gõ lệnh `docker logs -f gemini_ner_smart`.
Nếu thấy dòng `Listening on http://0.0.0.0:9090` là thành công.
