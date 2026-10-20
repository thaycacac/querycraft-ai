# 00. Tổng quan dự án QueryCraft AI

## 1. Bối cảnh và vấn đề (Problem statement)
Dữ liệu hành vi người dùng (user behavior tracking) từ ứng dụng di động, game và sàn thương mại điện tử thường có:
- **Schema lồng nhau (nested)**: một dòng sự kiện chứa struct và array như `event_params`, `items`.
- **Schema không đồng nhất (heterogeneous)**: mỗi loại event mang bộ tham số khác nhau.
- **Khái niệm kinh doanh không có sẵn trong schema**: DAU, retention, conversion rate, ARPPU... phải được định nghĩa bằng công thức trên nhiều cột.

Người dùng không biết SQL khó truy vấn dữ liệu này. Text-to-SQL truyền thống gặp ba khó khăn:
1. **Câu hỏi mơ hồ**: "người dùng active tuần này" có thể hiểu theo nhiều cách.
2. **Ánh xạ khái niệm kinh doanh sang schema** (schema linking + metric resolution).
3. **Sinh SQL đúng ngữ nghĩa**, không chỉ đúng cú pháp, nhất là với UNNEST và dialect.

## 2. Mục tiêu (Goals)
- G1: Xây hệ thống chuyển câu hỏi tiếng Việt/Anh thành SQL chạy được trên dữ liệu event lồng nhau.
- G2: Tích hợp **semantic/metric layer** để giải quyết khái niệm kinh doanh.
- G3: Dùng **agentic workflow** (linking, sinh, thực thi, tự sửa lỗi, hỏi lại).
- G4: Đánh giá bằng benchmark đầy đủ (BIRD, Spider, Spider 2.0 tập con, Dr.Spider, EventSQL-Bench tự xây).
- G5: Người thực hiện hiểu sâu NLP/Text-to-SQL qua tài liệu tiếng Việt kèm bài thực hành.

## 3. Giả thuyết cần chứng minh
- H1: Agentic workflow tốt hơn một lần gọi prompt đơn.
- H2: Semantic layer tăng độ chính xác trên câu hỏi chứa metric và schema lồng nhau.
- H3: Model open-source nhỏ kèm semantic layer có thể tiệm cận model API lớn không có semantic layer.

## 4. Phạm vi (Scope)
Trong phạm vi: SQL chỉ đọc (SELECT), một database mỗi truy vấn, DuckDB làm engine chính, đánh giá một lượt (single-turn) và hỏi lại làm rõ.
Ngoài phạm vi: ghi/sửa dữ liệu, hội thoại nhiều lượt dài, huấn luyện LLM từ đầu, tối ưu hiệu năng truy vấn.

## 5. Giả định (Assumptions)
- Có sẵn mô tả schema, và có thể viết tay file semantic layer cho từng miền.
- Câu trả lời đúng được xác định bằng kết quả thực thi (Execution Accuracy).
- Truy cập được ít nhất một LLM API và một model local.

## 6. Liên hệ với yêu cầu môn học
| Yêu cầu NLP501 | Tài liệu |
|---|---|
| Problem statement, goals, scope, assumptions | 00 (file này) |
| Literature review | 03 |
| Datasets | 04 |
| Evaluation methods | 05 |
| Results của công trình trước | 06 |
| Proposed methods | 07 |

