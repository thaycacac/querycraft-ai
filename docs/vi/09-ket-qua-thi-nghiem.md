# 09. Kết quả thí nghiệm

Tất cả số liệu lấy từ `experiments/results_main.md`, `experiments/results_paraphrase.md` và `experiments/run_remaining.log`, chạy ngày 2026-10-20 trên Mac M1 Max, model chạy local qua Ollama.

## 1. Thiết lập
- **EventSQL-Bench** (tự xây): DuckDB, 1500 user, 59 ngày, cột `event_params` và `items` lồng nhau. 162 câu hỏi: 125 test, trong đó 108 trả lời được và 17 mơ hồ. Chia 4 mức độ khó. 3 họ câu hỏi (`f_retention_d1`, `f_cart_abandon`, `f_top_categories`, 12 câu) không có ví dụ cùng họ trong kho few-shot.
- **Metric chính**: Execution Accuracy (EX). Kiểm định McNemar exact trên cùng tập câu hỏi, bootstrap 95% CI.
- **Model**: `qwen3:8b` (chính), `qwen2.5:3b` (so sánh model nhỏ). Không có API key nên **chưa chạy model API** (adapter Anthropic/OpenAI đã có, lệnh ở doc 08 §5).
- **Spider dev** và **BIRD dev**: mẫu cố định 200 câu (seed 123), mỗi dataset.

## 2. Ablation trên EventSQL-Bench (qwen3:8b, câu hỏi tiếng Việt, 108 câu)

| Cấu hình | EX | L1 | L2 | L3 | L4 | Unseen (n=12) |
|---|---|---|---|---|---|---|
| baseline | 0,352 | 0,93 | 0,00 | 0,42 | 0,09 | 3/12 |
| +linking | 0,296 | 0,93 | 0,00 | 0,36 | 0,00 | 0/12 |
| +fewshot | 0,880 | 1,00 | 1,00 | 0,98 | 0,64 | 3/12 |
| +semantic | 0,963 | 1,00 | 1,00 | 0,98 | 0,91 | 10/12 |
| +correction | 0,981 | 1,00 | 1,00 | 0,98 | 0,97 | 12/12 |
| +clarify | 0,981 | 1,00 | 1,00 | 0,98 | 0,97 | 12/12 |
| semantic_only | 0,444 | 0,53 | 0,70 | 0,38 | 0,42 | 6/12 |
| correction_only | 0,370 | 0,93 | 0,00 | 0,46 | 0,09 | 3/12 |

Kiểm định McNemar:
- +linking so với baseline: p = 0,031 (**tệ hơn**, có ý nghĩa).
- +semantic so với +fewshot: p = 0,0039.
- +correction so với +semantic: p = 0,5 (không có ý nghĩa).
- semantic_only so với baseline: p = 0,19; correction_only so với baseline: p = 0,5 (không có ý nghĩa).
- Nhóm unseen: +semantic so với +fewshot p = 0,0156; +correction so với +fewshot p = 0,0039.

Phân loại lỗi của baseline: schema_error 43, wrong_result 22, runtime_error 5, đúng 38.
Làm rõ câu mơ hồ (17 câu): precision/recall/F1 = 1,00/1,00/1,00. Kết quả này dựa trên luật, cùng phân phối với dữ liệu, nên chỉ là cận trên.
Độ trễ: 2,6–4,6 giây/câu; riêng correction_only 10 giây/câu (trung bình 1,93 lần thử).

## 3. Ngôn ngữ và kích thước model

| Model | Ngôn ngữ | baseline | +fewshot | +semantic | +correction |
|---|---|---|---|---|---|
| qwen3:8b | vi | 0,352 | 0,880 | 0,963 | 0,981 |
| qwen3:8b | en | 0,333 | 0,889 | 0,991 | (không chạy) |
| qwen2.5:3b | vi | 0,167 | 0,556 | 0,556 | 0,657 |

Xu hướng giống nhau giữa tiếng Việt và tiếng Anh. Model 3B hưởng lợi từ pipeline (0,167 → 0,657) nhưng vẫn thấp hơn nhiều so với 8B, và semantic layer không giúp được thêm ở cỡ này.

## 4. Spider và BIRD (200 câu mẫu, qwen3:8b)

| Cấu hình | Spider dev | BIRD dev |
|---|---|---|
| baseline | 0,720 | 0,240 |
| +linking | 0,725 | 0,155 |
| knowledge_only (chỉ evidence) | (không chạy) | 0,345 |
| +knowledge (linking + evidence) | (không chạy) | 0,220 |
| +correction | (không chạy) | 0,250 |

- Spider: linking gần như không đổi vì schema nhỏ.
- BIRD: evidence tăng EX từ 0,240 lên 0,345, nhưng linking kéo xuống. Evidence của BIRD đóng vai trò gần với semantic layer (định nghĩa khái niệm nghiệp vụ), nên đây là bằng chứng gián tiếp ủng hộ H2.
- Với n = 200, sai số chuẩn khoảng ±3 điểm phần trăm. Con số tuyệt đối không so sánh trực tiếp được với leaderboard (khác tập mẫu, model, prompt).

## 5. Độ bền với cách diễn đạt ngoài từ điển (20 paraphrase)

| Cấu hình | Metric resolver recall | EX end-to-end |
|---|---|---|
| no_semantic | 0/20 | 11/19 (0,58) |
| semantic_rule | 0/20 | 10/19 (0,53) |
| semantic_rule + llm_resolver | 17/20 | 17/19 (0,89) |

Resolver theo từ điển synonym không bắt được paraphrase nào (recall 0/20). Con số 100% trên 162 câu gốc là cận trên, vì synonym được viết cùng lúc với câu hỏi. Thêm bước LLM fallback phục hồi recall lên 17/20 và EX lên 0,89.

## 6. Số seed

Mỗi cấu hình chạy seed 0, 1, 2, kết quả **giống hệt nhau** (std = 0). Lý do: temperature = 0 và Ollama với seed cố định cho kết quả xác định, và các seed khác nhau không làm thay đổi gì. Vì vậy mean ± std **không đo được biến thiên thực** của model. Cách đo độ tin cậy thực tế ở đây là bootstrap CI và McNemar trên tập câu hỏi. Muốn đo biến thiên do sampling thì phải chạy temperature > 0.

## 7. Kết luận theo giả thuyết
- **H1 (agentic tốt hơn prompt đơn)**: ủng hộ yếu. Self-correction riêng lẻ không có ý nghĩa thống kê (0,352 → 0,370); khi đặt cuối pipeline thì +0,018 (p = 0,5). Nó chủ yếu sửa lỗi hiện rõ (lỗi cú pháp, schema), không sửa được lỗi âm thầm như sai metric. Cải thiện lớn đến từ few-shot và semantic layer.
- **H2 (semantic layer giúp)**: ủng hộ. +0,083 so với few-shot (p = 0,0039), L4 từ 0,64 lên 0,91, họ câu hỏi chưa thấy từ 3/12 lên 10/12, và LLM fallback giữ được lợi ích khi paraphrase. BIRD evidence đi cùng chiều.
- **H3 (model local nhỏ + semantic layer tiệm cận API lớn)**: **không kiểm chứng được** vì không có API key. Chỉ có một điểm dữ liệu: model 3B đạt 0,657, thấp hơn nhiều so với 8B.

## 8. Phân tích lỗi và điều bất ngờ
- **Schema linking làm tệ hơn** trên cả EventSQL (−0,056, p = 0,031) và BIRD (0,240 → 0,155). Các lỗi quan sát thấy: cột mơ hồ trong JOIN và dùng sai `event_params[?]` như prepared statement. Nguyên nhân gốc chưa được kiểm chứng; giả thuyết là việc cắt schema làm mất ngữ cảnh mà model cần.
- Mức 2 (nested) đạt 0% khi không có few-shot, vì model không biết cú pháp `list_filter` của DuckDB dù đã có catalog event.
- Phần lớn mức tăng của few-shot đến từ tái sử dụng khuôn mẫu cùng họ; họ chưa thấy vẫn chỉ đạt 3/12.

## 9. Mối đe dọa đến tính hợp lệ
1. SQL vàng và YAML semantic layer do cùng một người viết, SQL trong YAML gần như trùng SQL vàng, nên kết quả +semantic lạc quan.
2. Rò rỉ few-shot trong cùng họ câu hỏi.
3. Nhóm unseen chỉ có n = 12.
4. EX trên một DB, không phải test-suite; dữ liệu tổng hợp, một DB duy nhất.
5. Spider/BIRD có thể đã nằm trong dữ liệu huấn luyện của model (contamination).
6. Mẫu 200 câu, một lần chạy, không có số seed độc lập (xem §6).

## 10. Chưa làm
- Model API (H3), Spider 2.0 tập con, Dr.Spider, test-suite accuracy.
- Spider cho knowledge_only/+correction, và +correction tiếng Anh.
- Kiểm tra giao diện Streamlit trên trình duyệt (CLI đã chạy đúng).
