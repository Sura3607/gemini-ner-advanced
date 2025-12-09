import os
import logging
import json
import google.generativeai as genai
from google.api_core import exceptions
from label_studio_ml.model import LabelStudioMLBase

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 1. PROMPT NER (GIỮ NGUYÊN THEO BÀI TOÁN GIAO THÔNG CỦA BẠN)
# -----------------------------------------------------------------------------
NER_PROMPT = """
Bạn là chuyên gia gán nhãn dữ liệu tai nạn giao thông (NER).
Nhiệm vụ: Trích xuất chính xác thực thể từ văn bản theo các nhãn sau:

1. PER_DRIVER: Chỉ gán cho từ chỉ người lái (ví dụ: "tài xế", "người lái", "lái xe", "tài xế Nguyễn Văn A").
2. PER_VICTIM: Nạn nhân (người chết/bị thương).
3. LOC: Địa điểm CỤ THỂ (Tên đường, Quốc lộ, Tỉnh, Thành phố, Cầu, Km số...).
4. ORG: Tổ chức (Công an, Bệnh viện, Công ty...).
5. VEH: Phương tiện (Xe máy, Ô tô, Xe tải, Xe đầu kéo, Container...).
6. TIME: Thời gian (Giờ, ngày).
7. EVENT: Sự kiện (vụ va chạm, lật xe...).
8. CAUSE: Nguyên nhân (mất lái, nổ lốp, say rượu...).
9. CONSEQUENCE: Hậu quả (tử vong, hư hỏng...).

QUY TẮC CHẶT CHẼ (BẮT BUỘC TUÂN THỦ):
1. KHÔNG GÁN CHỒNG (NO OVERLAP): Các thực thể không được chứa nhau.
   - Sai: {"label": "PER_DRIVER", "text": "tài xế xe container"} (Gộp chung người và xe)
   - Đúng: Tách riêng ra -> [{"label": "PER_DRIVER", "text": "tài xế"}, {"label": "VEH", "text": "xe container"}]

2. KHÔNG GÁN LOC MƠ HỒ:
   - Tuyệt đối KHÔNG gán nhãn LOC cho các từ chung chung như: "hiện trường", "nơi này", "ở đây", "đoạn đường trên", "khu vực".
   - Chỉ gán LOC cho địa danh có tên riêng hoặc định danh cụ thể như: "Quốc lộ 1A", "Cầu Thăng Long", "Hà Nội", "Km số 15",  "cao tốc Pháp Vân - Cầu Giẽ", "tỉnh Lạng Sơn".

3. NGUYÊN NHÂN CŨNG BAO GỒM VẬN TỐC:
    - Ví dụ: "chạy quá tốc độ", "vượt ẩu", "phóng nhanh", "đi không đúng phần đường", vượt quá 70/80/90 km/h...

4. TRÍCH XUẤT CHÍNH XÁC:
   - "text" phải đúng y hệt trong văn bản gốc.

YÊU CẦU OUTPUT (JSON):
Trả về danh sách JSON gồm "label" và "text".
Ví dụ: 
[
  {"label": "PER_DRIVER", "text": "tài xế"}, 
  {"label": "VEH", "text": "xe đầu kéo"},
  {"label": "LOC", "text": "Hà Nội"}
]
Nếu không có thực thể, trả về [].
"""

class GeminiNERSmart(LabelStudioMLBase):
    def __init__(self, project_id=None, label_config=None, **kwargs):
        super(GeminiNERSmart, self).__init__(project_id=project_id, label_config=label_config, **kwargs)
        
        # Lấy API Key
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Chưa cấu hình GEMINI_API_KEY trong file .env")
        genai.configure(api_key=self.api_key)

        # Lấy danh sách model từ file .env
        priority_str = os.getenv("MODEL_PRIORITY", "gemini-1.5-flash")
        self.model_list = [m.strip() for m in priority_str.split(',')]
        
        logger.info(f"--> Cấu hình thứ tự Model: {self.model_list}")

    def _call_gemini_fallback(self, prompt):
        """Hàm chạy vòng lặp thử từng model"""
        last_exception = None
        
        for model_name in self.model_list:
            try:
                # Khởi tạo model tương ứng
                model = genai.GenerativeModel(
                    model_name,
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Gọi API
                response = model.generate_content(prompt)
                
                # Nếu thành công, log nhẹ và trả về
                # logger.info(f"Success with model: {model_name}")
                return response
            
            except Exception as e:
                # Nếu lỗi, in ra và thử model tiếp theo
                logger.warning(f"Model {model_name} thất bại. Lỗi: {e}. Đang thử model tiếp theo...")
                last_exception = e
                continue
        
        # Nếu thử hết danh sách mà vẫn lỗi
        logger.error("Tất cả model đều thất bại!")
        raise last_exception

    def predict(self, tasks, **kwargs):
        predictions = []

        for task in tasks:
            input_text = task['data'].get('text') or task['data'].get('Text')
            
            if not input_text:
                predictions.append({"result": [], "score": 0})
                continue

            full_prompt = f"{NER_PROMPT}\n\n---\nVăn bản:\n\"{input_text}\""

            try:
                # GỌI QUA HÀM FALLBACK
                response = self._call_gemini_fallback(full_prompt)
                
                entities = json.loads(response.text)
                results = []
                
                # Mapping Start/End Index
                for ent in entities:
                    label = ent.get("label")
                    text_val = ent.get("text")
                    if not label or not text_val: continue
                    
                    start_idx = input_text.find(text_val)
                    if start_idx != -1:
                        results.append({
                            "from_name": "label",
                            "to_name": "text",
                            "type": "labels",
                            "value": {
                                "start": start_idx,
                                "end": start_idx + len(text_val),
                                "text": text_val,
                                "labels": [label]
                            }
                        })

                predictions.append({"result": results, "score": 1.0})

            except Exception as e:
                logger.error(f"Task Failed: {e}")
                predictions.append({"result": [], "score": 0})
        
        return predictions