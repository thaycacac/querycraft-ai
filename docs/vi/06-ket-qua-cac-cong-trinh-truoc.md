# 06. Kết quả của các công trình trước

> Nguồn: abstract trên arXiv, truy cập 2026-10-20. Các số **không so sánh trực tiếp** với nhau được: khác split (dev/test), model nền, metric (EM/EX) và thời điểm. Cột "Nguồn" ghi ID arXiv.

## 1. Kết quả theo benchmark
| Phương pháp | Năm | Benchmark / split | Kết quả | Ghi chú | Nguồn |
|---|---|---|---|---|---|
| RAT-SQL | 2019 | Spider (EM) | 57,2%; 65,6% khi dùng BERT | Ở thời điểm công bố | 1911.04942 |
| DIN-SQL | 2023 | Spider test (EX) | 85,3% | Prior best 79,9 | 2304.11015 |
| DIN-SQL | 2023 | BIRD test (EX) | 55,9% | | 2304.11015 |
| DAIL-SQL | 2023 | Spider (EX) | 86,6% | Nhấn mạnh hiệu quả token | 2308.15363 |
| MAC-SQL + GPT-4 | 2023 | BIRD test (EX) | 59,59% | SQL-Llama 43,94 vs GPT-4 thuần 46,35 | 2312.11242 |
| CHESS | 2024 | BIRD test (EX) | 71,10% | Ít hơn ≈83% lần gọi LLM so với đầu bảng | 2405.16755 |
| CHASE-SQL | 2024 | BIRD dev / test (EX) | 73,01% / 73,0% | Đầu bảng lúc nộp | 2410.01943 |
| XiYan-SQL | 2024 | BIRD / Spider test (EX) | 75,63% / 89,65% | | 2411.08599 |
| ChatGPT (baseline BIRD) | 2023 | BIRD (EX) | 40,08% vs người 92,96% | Từ paper BIRD | 2305.03111 |
| o1-preview (agent) | 2024 | Spider 2.0 | 21,3% | vs 91,2% Spider 1.0 và 73,0% BIRD | 2411.07763 |
| ReFoRCE | 2025 | Spider 2.0-Snow / Lite | 35,83 / 36,56 | Đầu bảng lúc công bố | 2502.00675 |
| GPT-4 zero-shot (SQL trực tiếp) | 2023 | Enterprise SQL QA | 16% | 54% khi hỏi qua knowledge graph | 2311.07509 |

Các công trình không có số trong abstract (PICARD, RESDSQL, CodeS, OmniSQL, Arctic-Text2SQL-R1) cần được lấy từ bảng kết quả trong paper khi viết báo cáo; không điền số từ trí nhớ.

## 2. Các phát hiện rút ra
1. **Suy luận có cấu trúc + sửa lỗi thực thi** (DIN-SQL, MAC-SQL, CHESS) cải thiện rõ so với prompt thuần.
2. **Sinh nhiều ứng viên và chọn** (CHASE-SQL, XiYan-SQL, ReFoRCE) đẩy độ chính xác lên cao nhưng đắt.
3. **Model nhỏ + dữ liệu/RL tốt** (OmniSQL, Arctic-Text2SQL-R1) có thể cạnh tranh với model lớn gấp nhiều lần.
4. **Khoảng cách benchmark học thuật và thực tế** (Spider 2.0: 21,3% so với 91,2%) cho thấy schema lớn và tri thức miền mới là vấn đề thật.
5. **Ngữ nghĩa nghiệp vụ tường minh** (knowledge graph: 16% → 54%) tăng mạnh độ chính xác trên dữ liệu doanh nghiệp.
6. **Độ bền kém**: Dr.Spider cho thấy ngay cả model bền nhất giảm 14,0% tổng thể.

## 3. Điều dự án mong đợi so với các kết quả trên
- Không cạnh tranh với leaderboard BIRD (dự án dùng model 8B cục bộ, không voting nhiều ứng viên); mục tiêu là **đo đóng góp tương đối** của từng thành phần.
- Kỳ vọng định tính: semantic layer tăng mạnh ở câu metric, self-correction tăng ở lỗi nhìn thấy được, clarification không đổi EX nhưng đổi hành vi với câu mơ hồ.

## 4. Tự kiểm tra
1. Vì sao không được so 85,3 (DIN-SQL, Spider test) với EX dev của bạn?
2. Từ bảng trên, thành phần nào giúp tăng nhiều nhất trên BIRD, và đánh đổi chi phí là gì?
