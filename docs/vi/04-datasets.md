# 04. Các bộ dữ liệu Text-to-SQL: so sánh và đối chiếu

> Số liệu lấy từ abstract trên arXiv (truy cập 2026-10-20) hoặc ghi chú "≈" nếu là trí nhớ cần kiểm tra lại trước khi đưa vào báo cáo.

## 1. Bảng so sánh
| Dataset | Quy mô | Đặc trưng | Metric chính | Hạn chế |
|---|---|---|---|---|
| **WikiSQL** (2017) | ≈80 nghìn câu, ≈24 nghìn bảng | Một bảng, SQL đơn giản (không join, không lồng) | Execution/Logical-form accuracy | Quá dễ, đã bão hòa |
| **Spider** (2018) | 10.181 câu, 5.693 SQL phức tạp, 200 DB, 138 miền | Cross-domain: DB trong train và test khác nhau; join, nested, group | EM, EX, test-suite accuracy | Schema sạch, nhỏ; gần bão hòa (SOTA trên 85-90% EX) |
| **Spider-DK / Syn / Realistic** | Biến thể của Spider | Tri thức miền, đồng nghĩa, bỏ từ khóa lộ schema | EX | Vẫn là schema nhỏ |
| **Dr.Spider** (2023) | 17 phép nhiễu lên DB, câu hỏi, SQL | Đo độ bền: ngay cả model bền nhất giảm 14,0% tổng thể, 50,7% ở phép nhiễu khó nhất | EX trước/sau nhiễu | Nhiễu nhân tạo |
| **SParC / CoSQL** | Hội thoại nhiều lượt trên DB của Spider | Ngữ cảnh, hỏi lại, câu hỏi không trả lời được (CoSQL) | Question/Interaction match | Ít dùng với LLM mới |
| **KaggleDBQA** | ≈vài trăm câu, vài DB thật từ Kaggle | DB thực, ít dữ liệu train, có tài liệu mô tả | EX | Nhỏ |
| **BIRD** (2023) | 12.751 cặp, 95 DB, 33,4 GB, 37 miền | DB lớn, giá trị bẩn, có *external knowledge evidence*, đo hiệu quả (VES) | EX, VES | Evidence do người viết, khác thực tế khi không có sẵn |
| **EHRSQL** | ≈24 nghìn câu trên hồ sơ y tế (MIMIC-III, eICU) | Câu hỏi thời gian, câu không thể trả lời | EX + phát hiện unanswerable | Miền y tế |
| **Spider 2.0** (2024) | Hàng trăm tác vụ doanh nghiệp (phiên bản Lite/Snow/Dbt) | Schema rất lớn, BigQuery/Snowflake, tác vụ nhiều bước | Success rate | Đắt, cần tài khoản cloud; o1-preview chỉ 21,3% |
| **EventSQL-Bench** (dự án này) | 162 câu, 2 bảng, 1.500 user, ≈60 ngày | Event lồng nhau, metric nghiệp vụ, câu mơ hồ, 4 mức độ khó | EX, Clarification P/R/F1 | Dữ liệu mô phỏng, một DB, quy mô nhỏ |

## 2. So sánh theo trục quan trọng với đề tài
| Trục | Spider | BIRD | Spider 2.0 | EventSQL-Bench |
|---|---|---|---|---|
| Kích thước schema | Nhỏ | Trung bình-lớn | Rất lớn | Nhỏ (2 bảng) nhưng lồng sâu |
| Dữ liệu lồng nhau (struct/list) | Không | Hầu như không | Có (GA4, BigQuery) | **Trọng tâm** |
| Tri thức nghiệp vụ | Không | Có (evidence) | Có (tài liệu) | **Có (semantic layer)** |
| Câu hỏi mơ hồ | Không | Không | Ít | **Có, đo riêng** |
| Dialect | SQLite | SQLite | Nhiều | DuckDB |
| Chi phí chạy | Thấp | Trung bình | Cao | Thấp |
| Có leaderboard | Có | Có | Có | Không (tự xây) |

## 3. Vì sao chọn bộ benchmark của dự án
1. **BIRD** là cầu nối: `evidence` giống một lớp định nghĩa nghiệp vụ, nên đo được hiệu ứng "có/không có tri thức ngoài".
2. **Spider** làm kiểm tra sức khỏe và so sánh với literature.
3. **Dr.Spider / Spider-DK/Syn/Realistic** đo độ bền trước diễn đạt khác (tùy chọn nếu còn thời gian).
4. **Spider 2.0 (GA4)** là phép thử sát thực tế nhất nhưng đắt; dự án đưa vào như hướng mở rộng.
5. **EventSQL-Bench** là bằng chứng chính cho miền tracking.

## 4. Cách EventSQL-Bench được xây (và giới hạn)
- Dữ liệu sinh bằng tiến trình ngẫu nhiên có seed (`benchmarks/eventsql/build.py`): mỗi user có ngày đầu, nền tảng, quốc gia, kênh; hoạt động giảm dần theo thời gian; luồng view → add_to_cart → checkout → purchase; tutorial; level_up; ad_impression.
- Câu hỏi sinh theo **họ (family)** từ mẫu có tham số; SQL vàng được thực thi lúc build và phải khác rỗng/NULL.
- Chia train/test: mỗi family có 1 ví dụ làm kho few-shot (`split=train`), phần còn lại là test. Ba family (`retention_d1`, `cart_abandon`, `top_categories`) bị giữ ra hoàn toàn (`unseen_family`) để đo khả năng khái quát.
- 17 câu **mơ hồ** không có SQL vàng; đúng khi hệ thống hỏi lại.
- **Giới hạn cần nêu trong báo cáo**: dữ liệu mô phỏng; câu hỏi từ mẫu nên đa dạng ngôn ngữ thấp; synonym trong semantic layer do cùng tác giả viết (kết quả resolver là cận trên, cần thử với diễn đạt ngoài phân phối); gold SQL do cùng tác giả viết nên có nguy cơ thiên lệch định nghĩa.

## 5. Tải và dùng
`benchmarks/download.sh` tải BIRD dev và Spider vào `data/`. Loader ở `benchmarks/sqlbench.py`. Chạy: `python experiments/run_public.py --dataset bird --n 200`.

## 6. Tự kiểm tra
1. Vì sao Spider khó dùng để chứng minh lợi ích của semantic layer?
2. `evidence` của BIRD khác semantic layer thật ở điểm nào?
3. Nêu hai thiên lệch có thể có trong EventSQL-Bench và cách giảm.
