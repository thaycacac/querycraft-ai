# 05. Phương pháp đánh giá

## 1. Các metric
| Metric | Định nghĩa | Ưu | Nhược |
|---|---|---|---|
| **Exact Match (EM)** | So khớp cấu trúc SQL dự đoán với SQL vàng | Không cần chạy DB | Phạt oan SQL đúng nhưng viết khác; không dùng cho LLM sinh tự do |
| **Execution Accuracy (EX)** | Chạy cả hai SQL, so kết quả | Phản ánh đúng mục đích | Có thể "đúng do ngẫu nhiên" (kết quả trùng tình cờ) |
| **Test-suite accuracy** | EX trên nhiều bản DB biến đổi để loại trùng tình cờ | Chặt hơn EX | Cần tạo/tải DB distilled |
| **VES** (BIRD) | EX có thưởng theo hiệu quả thực thi | Đo cả tốc độ | Nhiễu theo phần cứng |
| **Valid-SQL rate** | Tỷ lệ SQL chạy không lỗi | Chẩn đoán | Không đo đúng nghĩa |
| **Clarification P/R/F1** | Với câu mơ hồ: có hỏi lại không | Đo hành vi hỏi lại | Cần nhãn mơ hồ |
| **Chi phí/độ trễ** | Token vào/ra, giây mỗi câu | Quyết định triển khai | Phụ thuộc phần cứng |

## 2. Cách tính EX trong dự án (`src/querycraft/evaluation.py`)
1. Thực thi SQL vàng và SQL dự đoán trên cùng DB (chỉ đọc).
2. Chuẩn hóa giá trị: làm tròn số thực 4 chữ số, `None` giữ nguyên, ngày → chuỗi, list/struct → tuple.
3. **Cho phép hoán vị cột** (như test-suite Spider): tìm hoán vị cột sao cho các dòng khớp.
4. **Thứ tự dòng** chỉ bắt buộc khi SQL vàng có `ORDER BY` ở cấp ngoài cùng.
5. Phân loại: `ok`, `wrong_result`, `pred_error:*`, `gold_error:*`.
6. Kiểm tra bằng test: SQL vàng so với chính nó phải ra 100% (`tests/test_evaluation.py`).

Giới hạn: đây là EX trên **một** DB, chưa phải test-suite; kết quả trùng tình cờ có thể làm EX cao hơn thực tế một chút (đặc biệt ở câu trả về một số nhỏ hoặc 0).

## 3. Câu hỏi mơ hồ
- Câu mơ hồ không có SQL vàng, không tính vào EX.
- Với mỗi cấu hình ghi `clarified` (có hỏi lại không). Precision = trong số lần hỏi lại, bao nhiêu thực sự mơ hồ; Recall = trong số câu mơ hồ, bao nhiêu được hỏi lại.
- **Hỏi lại nhầm** câu rõ ràng bị tính là sai ở EX (không có SQL) → phạt việc hỏi lại thừa.

## 4. Thiết kế thí nghiệm
- **Ablation tích lũy**: baseline → +linking → +fewshot → +semantic → +correction → +clarify. Mỗi bước thêm đúng một thành phần.
- **Ablation riêng lẻ**: `semantic_only`, `correction_only` (so với baseline) để thấy đóng góp độc lập.
- **Ma trận model**: Qwen3-8B và Qwen2.5-3B (local); model API qua adapter Anthropic/OpenAI (cần API key, đã cài sẵn).
- **Ngôn ngữ**: câu hỏi tiếng Việt và tiếng Anh.
- **Seed**: temperature = 0 nhưng vẫn truyền seed; chạy nhiều seed cho các cấu hình chính để ước lượng độ biến thiên.
- **Mẫu con** cho Spider/BIRD (cố định bằng seed 123) vì chi phí.

## 5. Thống kê
- **Khoảng tin cậy bootstrap 95%** cho EX (`bootstrap_ci`).
- **Kiểm định McNemar chính xác** (`mcnemar_exact`) cho hai hệ thống trên cùng tập câu hỏi: chỉ đếm câu mà hai hệ thống bất đồng; p nhỏ nghĩa là chênh lệch khó là ngẫu nhiên.
- Khi so nhiều cấu hình, nhớ rằng nhiều phép thử làm tăng khả năng "ăn may"; báo cáo kích thước hiệu ứng (ΔEX) chứ không chỉ p-value.

## 6. Phân tích lỗi (error taxonomy)
`schema_error` (sai tên cột/bảng), `syntax_error`, `runtime_error`, `wrong_result` (lỗi im lặng), `clarified`. Khi xem `wrong_result`, mở file `.jsonl` trong `experiments/runs/` và đọc từng SQL để gán nguyên nhân: sai metric, sai join, sai UNNEST, sai lọc thời gian...

## 7. Mối đe dọa tính hợp lệ (threats to validity)
- **Nội tại**: gold SQL và semantic layer cùng tác giả; synonym có thể "dạy sẵn đáp án".
- **Ngoại suy**: dữ liệu mô phỏng, một DB, quy mô nhỏ, model nhỏ chạy cục bộ.
- **Rò rỉ dữ liệu**: Spider/BIRD có thể nằm trong dữ liệu huấn luyện của LLM; EventSQL-Bench do tự sinh nên không bị.
- **Few-shot cùng family**: ví dụ gần như cùng mẫu làm tăng điểm `+fewshot`; vì thế có tập `unseen_family`.

## 8. Tự kiểm tra
1. Vì sao hoán vị cột được chấp nhận nhưng hoán vị dòng chỉ được chấp nhận khi không có ORDER BY?
2. McNemar khác kiểm định t ở điểm nào?
3. Nêu một cách để giảm thiên lệch do cùng tác giả viết gold SQL.
