# 07. Phương pháp đề xuất: QueryCraft AI

## 1. Ý tưởng
Kết hợp **agentic workflow** (nhiều bước có kiểm tra bằng thực thi) với **semantic/metric layer** (định nghĩa nghiệp vụ tường minh), cùng bước **hỏi lại** khi câu hỏi mơ hồ. Tinh thần giống Metabase Metabot: LLM không đoán định nghĩa nghiệp vụ mà được neo vào metadata và metric đã định nghĩa; khác ở chỗ dự án tập trung vào dữ liệu event lồng nhau và đo từng thành phần bằng ablation.

## 2. Kiến trúc
```
Câu hỏi
  │
  ▼
[1. Metric Resolver + Ambiguity]  ← semantic/events.yaml
  │  mơ hồ? ──► Hỏi lại người dùng (dừng)
  ▼
[2. Schema Linker + Event Profiler]  ← BM25 + profiling event_params
  ▼
[3. Prompt Builder]  schema + event catalog + định nghĩa metric + few-shot (BM25)
  ▼
[4. SQL Generator (LLM)]
  ▼
[5. Validator/Executor]  sqlglot parse, chỉ SELECT, DuckDB read-only
  │  lỗi / rỗng? ──► [6. Self-Correction] (tối đa N vòng, đưa lỗi lại cho LLM)
  ▼
Kết quả + SQL + metric đã dùng
```
Mã: `src/querycraft/agent.py` (điều phối), `semantic.py`, `linker.py`, `db.py`, `llm.py`, `evaluation.py`.

## 3. Các thành phần
### 3.1 Semantic layer (`semantic/events.yaml`)
- **Metric**: tên, mô tả nghiệp vụ, synonym song ngữ, công thức SQL chuẩn (ví dụ DAU, ARPPU, retention D1, cart abandonment).
- **param_access**: hướng dẫn đọc `event_params` và `items`.
- **ambiguity_rules**: thuật ngữ gây mơ hồ (`doanh thu`, `tỷ lệ chuyển đổi`) cùng danh sách từ làm rõ.
- **Resolver**: khớp synonym dài nhất trước (tránh "ad revenue" bị nhận nhầm thành "revenue"), mở rộng phụ thuộc (AOV → revenue + orders).
- Ý tưởng mượn từ dbt MetricFlow/Cube (định nghĩa một lần, dùng mọi nơi) và từ kết quả 16% → 54% của knowledge graph trên SQL doanh nghiệp.

### 3.2 Schema linking và profiling
- `SchemaLinker`: BM25 trên tên bảng/cột, giữ khóa; schema nhỏ thì giữ nguyên.
- `profile_events`: quét dữ liệu liệt kê event và các key trong `event_params` cùng trường giá trị khác NULL. Đây là phần LLM không thể suy ra từ DDL.
- Với SQLite (Spider/BIRD): thêm 2 dòng mẫu mỗi bảng để LLM thấy dạng giá trị.

### 3.3 Few-shot retrieval
`ExampleRetriever` chọn 3 cặp (câu hỏi, SQL) gần nhất bằng BM25 từ kho train (theo ý tưởng DAIL-SQL).

### 3.4 Tự sửa lỗi
Khi SQL lỗi hoặc cho kết quả rỗng/toàn NULL, prompt gồm câu hỏi, SQL cũ, thông báo lỗi và yêu cầu sửa, tối đa 2 vòng.

### 3.5 Hỏi lại (clarification)
Nếu resolver phát hiện thuật ngữ mơ hồ, hệ thống trả câu hỏi làm rõ liệt kê các định nghĩa ứng viên và **không gọi LLM** (tiết kiệm chi phí, tránh đoán).

### 3.6 An toàn
Chỉ chấp nhận `SELECT/WITH`; DuckDB mở ở chế độ read-only; SQLite `mode=ro` kèm timeout.

## 4. Cách các cấu hình ablation ánh xạ vào mã
| Cấu hình | `AgentConfig` |
|---|---|
| baseline | tất cả tắt: chỉ DDL + câu hỏi |
| +linking | `linking=True` (pruning + event catalog / sample rows) |
| +fewshot | `+ fewshot=3` |
| +semantic | `+ semantic=True` (định nghĩa metric / evidence) |
| +correction | `+ correction=2` |
| +clarify | `+ clarify=True` |
| semantic_only, correction_only | chỉ bật đúng thành phần đó |

## 5. Giả thuyết và tiêu chí chấp nhận
- H1 (agentic > prompt đơn): `+correction` hoặc toàn pipeline có EX cao hơn baseline với McNemar p < 0,05.
- H2 (semantic layer): `semantic_only` và `+semantic` cao hơn mức tương ứng không có semantic, đặc biệt ở level 3-4 và nhóm `unseen_family`.
- H3 (model nhỏ + semantic ≈ model lớn không semantic): so Qwen2.5-3B/Qwen3-8B có semantic với baseline của model lớn hơn (API, cần key).
- Kết quả thực tế ghi ở `09-ket-qua-thi-nghiem.md`; nếu giả thuyết không được ủng hộ, ghi nhận trung thực và phân tích.

## 6. Hướng mở rộng
1. **Resolver bằng embedding**: đã có LLM fallback (`resolve_llm`, recall paraphrase 0/20 lên 17/20, xem doc 09); còn lại là embedding để giảm chi phí gọi LLM.
2. **Majority voting** nhiều ứng viên (CHASE-SQL, Arctic-Text2SQL-R1).
3. **Fine-tune/RL** model nhỏ với reward thực thi trên dữ liệu tổng hợp từ semantic layer.
4. **Spider 2.0 (GA4/BigQuery)** để kiểm chứng trên dữ liệu thật.
5. **Hội thoại nhiều lượt**, nhớ ngữ cảnh.
6. **Học semantic layer tự động** từ log truy vấn.

## 7. Tự kiểm tra
1. Vì sao hỏi lại không gọi LLM là một lựa chọn thiết kế tốt?
2. Nếu thêm metric mới, bạn sửa những file nào?
3. Nêu một tình huống mà tự sửa lỗi không cứu được nhưng semantic layer cứu được.
