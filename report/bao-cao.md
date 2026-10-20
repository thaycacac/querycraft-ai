# Xây dựng hệ thống AI chuyển đổi ngôn ngữ tự nhiên thành SQL cho dữ liệu hành vi người dùng

**Môn học:** NLP501 – Natural Language Processing · **Báo cáo cuối khóa**
**Mã nguồn:** thư mục `querycraft-ai` · **Tài liệu chi tiết:** `docs/vi/` · **Số liệu gốc:** `experiments/results_main.md`, `experiments/results_paraphrase.md`

> Quy ước: mọi con số thí nghiệm trong báo cáo lấy từ các lần chạy ngày 2026-10-20 (model chạy local qua Ollama). Số liệu của các công trình khác lấy từ phần tóm tắt (abstract) trên arXiv, truy cập 2026-10-20; khác split, model và metric nên không so sánh trực tiếp với số của dự án.

---

## Tóm tắt

Dữ liệu theo dõi hành vi người dùng (app, game, e-commerce) có các event với tham số lồng nhau (`event_params`, `items`) và schema không đồng nhất. Hệ thống Text-to-SQL thông thường thường thất bại ở ba điểm: câu hỏi mơ hồ, ánh xạ khái niệm kinh doanh (DAU, ARPPU, retention) sang schema, và SQL chạy được nhưng sai ngữ nghĩa. Dự án xây **QueryCraft AI**, một agent LLM có các bước: phát hiện mơ hồ và hỏi lại, resolve metric qua một **semantic/metric layer** viết bằng YAML, liên kết schema, sinh SQL với few-shot, kiểm tra read-only, và tự sửa lỗi bằng phản hồi thực thi. Để đo hiệu quả, dự án tự xây **EventSQL-Bench** (DuckDB, 162 câu hỏi tiếng Việt và tiếng Anh, 4 mức độ khó, 17 câu mơ hồ) và đối chiếu với Spider và BIRD.

Với `qwen3:8b` chạy local, trên 108 câu trả lời được: Execution Accuracy (EX) tăng từ **0,352** (prompt đơn) lên **0,880** (few-shot), **0,963** (thêm semantic layer) và **0,981** (thêm tự sửa lỗi). Semantic layer cải thiện có ý nghĩa thống kê so với few-shot (McNemar p = 0,0039), nhất là ở nhóm 3 họ câu hỏi không có ví dụ tương tự (3/12 lên 10/12). Tự sửa lỗi đứng riêng không cải thiện có ý nghĩa. Schema linking dựa trên BM25 làm kết quả **tệ hơn** cả trên EventSQL-Bench lẫn BIRD. Giả thuyết so sánh model local nhỏ với model API lớn chưa kiểm chứng được vì chưa có API key.

---

## 1. Phát biểu bài toán, mục tiêu, phạm vi và giả định

### 1.1 Bối cảnh và vấn đề
Nhóm phân tích sản phẩm thường cần trả lời nhanh các câu hỏi như "DAU hôm qua?", "tỷ lệ bỏ giỏ hàng tuần này?", "ARPPU tháng 2?". Dữ liệu nằm trong bảng event với đặc điểm:
- **Lồng nhau, không đồng nhất:** mỗi loại event có bộ tham số riêng, lưu trong một mảng `event_params` gồm các cặp (key, value) và `items` là mảng struct. Cùng một cột chứa nhiều ý nghĩa tùy `event_name`.
- **Khái niệm kinh doanh không có trong schema:** "doanh thu", "người dùng hoạt động", "tỷ lệ chuyển đổi" là định nghĩa nghiệp vụ, mỗi tổ chức một khác.
- **Câu hỏi mơ hồ:** "Doanh thu tháng 1" có thể là doanh thu bán hàng, doanh thu theo món hàng hay doanh thu quảng cáo.

Text-to-SQL truyền thống được thiết kế và đánh giá trên bảng quan hệ phẳng, nên ba điểm này là nơi nó dễ sai nhất: sinh SQL sai tên cột hoặc không biết cú pháp truy cập mảng lồng, chọn sai định nghĩa metric (lỗi im lặng, SQL vẫn chạy ra số), hoặc đoán thay vì hỏi lại.

### 1.2 Mục tiêu
1. Thiết kế một hệ thống Text-to-SQL dạng agent kết hợp semantic/metric layer để tự động ánh xạ schema, resolve metric nghiệp vụ và sinh SQL thực thi được (ý tưởng tương tự Metabot của Metabase).
2. Xây benchmark riêng cho miền event tracking lồng nhau và đo **đóng góp riêng của từng thành phần** bằng ablation có kiểm định thống kê.
3. So sánh model mã nguồn mở chạy local với model API (kế hoạch; xem hạn chế).

### 1.3 Giả thuyết
- **H1:** quy trình agent (liên kết schema, sinh SQL, thực thi, tự sửa) chính xác hơn một lần gọi prompt đơn.
- **H2:** semantic/metric layer tăng độ chính xác với câu hỏi có khái niệm nghiệp vụ và schema lồng nhau.
- **H3:** model mã nguồn mở nhỏ kèm semantic layer tiệm cận model API lớn không có semantic layer.

### 1.4 Phạm vi
Trong phạm vi: một cơ sở dữ liệu DuckDB tổng hợp (EventSQL-Bench), truy vấn chỉ đọc, câu hỏi tiếng Việt và tiếng Anh, 15 metric trong semantic layer, một lượt hỏi (chưa hội thoại nhiều lượt). Ngoài phạm vi: Spider 2.0 và Dr.Spider, nhiều dialect, tự sinh semantic layer, fine-tune model.

### 1.5 Giả định
Dữ liệu event có dạng giống GA4 (mảng `event_params` với `key` và `value` có nhiều kiểu); semantic layer do con người viết; SQL vàng được kiểm tra bằng cách thực thi. Dự án do một người thực hiện trong khoảng 8 tuần (giả định chưa được xác nhận).

---

## 2. Tổng quan tài liệu (Literature review)

Chi tiết và trích dẫn đầy đủ ở `docs/vi/03-literature-review.md`.

### 2.1 Diễn tiến theo giai đoạn
| Giai đoạn | Đại diện | Điểm mạnh | Điểm yếu |
|---|---|---|---|
| Neural chuyên biệt | **RAT-SQL** (2019) | Mã hóa quan hệ giữa phần tử schema và câu hỏi bằng relation-aware self-attention; EM 57,2% trên Spider (65,6% với BERT) | Cần huấn luyện riêng, kém khái quát sang miền mới |
| Fine-tune PLM | **PICARD** (2021), **RESDSQL** (2023), **CodeS** | Giải mã ràng buộc cú pháp (PICARD); tách schema linking và sinh skeleton (RESDSQL); model mở nhỏ (CodeS) | Cần dữ liệu có nhãn theo miền; đúng cú pháp chưa chắc đúng nghĩa |
| Prompting LLM | **DIN-SQL** (85,3 Spider test, 55,9 BIRD test), **DAIL-SQL** (86,6 Spider), **C3** | Không cần huấn luyện; DAIL-SQL cho thấy chọn ví dụ few-shot theo độ tương đồng rất quan trọng | Nhiều lần gọi LLM, prompt thủ công, phụ thuộc model |
| Pipeline nhiều agent | **MAC-SQL** (59,59 BIRD test), **CHESS** (71,10), **CHASE-SQL** (73,0), **XiYan-SQL** (75,63 BIRD, 89,65 Spider test) | Độ chính xác cao nhất trên benchmark học thuật; sửa lỗi bằng phản hồi thực thi, sinh nhiều ứng viên rồi chọn | Chi phí và độ trễ cao, tối ưu cho benchmark hơn cho miền doanh nghiệp |
| Fine-tune lớn và RL | **OmniSQL** (SynSQL-2.5M), **Arctic-Text2SQL-R1** | Model nhỏ chạy local mà vẫn mạnh; phần thưởng dựa trên kết quả thực thi | Cần hạ tầng huấn luyện; vẫn không biết định nghĩa nghiệp vụ riêng |
| Doanh nghiệp | **Spider 2.0** (o1-preview chỉ 21,3% so với 91,2% trên Spider 1.0), **ReFoRCE** (35,83 Snow, 36,56 Lite) | Phản ánh thực tế: schema lớn, nhiều dialect | Thiết lập nặng; điểm vẫn thấp |
| Semantic layer | **Knowledge graph cho SQL doanh nghiệp** (GPT-4 zero-shot 16%, 54% khi hỏi qua knowledge graph), **Metabot**, **dbt MetricFlow**, **Cube**, **WrenAI** | Định nghĩa nghiệp vụ nhất quán, kiểm soát được | Phải xây và bảo trì |

### 2.2 Nhận xét
1. Hầu hết hệ thống được đo trên bảng phẳng; dữ liệu event lồng nhau cùng metric nghiệp vụ ít được đo riêng.
2. Ít công trình tách riêng đóng góp của semantic layer bằng ablation có kiểm định thống kê.
3. Hỏi lại khi mơ hồ hiếm khi được đánh giá như một nhiệm vụ riêng.
4. Khoảng cách giữa Spider 1.0 (91,2%) và Spider 2.0 (21,3%) cho thấy điểm benchmark học thuật không đại diện cho môi trường thực.

Về Metabot: theo mô tả trên trang của Metabase, SQL sinh ra được neo vào metadata và semantic layer của Metabase và chạy với quyền của người dùng đăng nhập. Chi tiết kiến trúc nội bộ không công bố ở nguồn đã kiểm tra, nên dự án chỉ lấy tinh thần "neo vào định nghĩa metric" chứ không tái hiện Metabot.

**Đóng góp của dự án so với tổng quan trên:** EventSQL-Bench cho dữ liệu event lồng nhau, kiến trúc agent với semantic layer, và ablation trên model mở chạy local có kiểm định thống kê.

---

## 3. Các bộ dữ liệu hiện có

Bảng so sánh đầy đủ ở `docs/vi/04-datasets.md`.

| Dataset | Quy mô | Đặc trưng | Hạn chế đối với đề tài |
|---|---|---|---|
| WikiSQL (2017) | ≈80 nghìn câu, một bảng | SQL đơn giản | Quá dễ, bão hòa |
| **Spider** (2018) | 10.181 câu, 5.693 SQL, 200 DB, 138 miền | Cross-domain, join và nested | Schema sạch và nhỏ, gần bão hòa, không có dữ liệu lồng, không có tri thức nghiệp vụ |
| Dr.Spider (2023) | 17 phép nhiễu | Đo độ bền (giảm 14,0% tổng thể, 50,7% ở phép khó nhất) | Nhiễu nhân tạo |
| **BIRD** (2023) | 12.751 câu, 95 DB, 33,4 GB, 37 miền | DB lớn, giá trị bẩn, có *external knowledge evidence*; ChatGPT 40,08% so với người 92,96% | Evidence do con người viết sẵn |
| Spider 2.0 (2024) | Tác vụ doanh nghiệp | Schema rất lớn, BigQuery/Snowflake, có GA4 | Đắt, cần tài khoản cloud |
| **EventSQL-Bench** (dự án) | 162 câu, 2 bảng, 1.500 user, 59 ngày | Event lồng nhau, metric nghiệp vụ, câu mơ hồ, 4 mức độ khó | Mô phỏng, một DB, quy mô nhỏ |

**Lý do chọn:** BIRD là cầu nối vì `evidence` hoạt động như một lớp định nghĩa nghiệp vụ; Spider là kiểm tra sức khỏe; Spider 2.0 sát thực tế nhất nhưng đắt nên để hướng mở rộng; và vì không có benchmark công khai cho event tracking lồng nhau, dự án tự xây EventSQL-Bench làm bằng chứng chính.

### 3.1 Cách xây EventSQL-Bench
- **Dữ liệu:** `benchmarks/eventsql/build.py` sinh bằng tiến trình ngẫu nhiên có seed 7: 1.500 user, 59 ngày kể từ 2026-01-01; mỗi user có nền tảng, quốc gia, kênh; hoạt động giảm dần theo thời gian; luồng view, add_to_cart, checkout, purchase; thêm tutorial, level_up, ad_impression. Bảng `events` có `event_params` (mảng key/value) và `items` (mảng struct).
- **Câu hỏi:** sinh theo họ (family) từ mẫu có tham số, song ngữ Việt/Anh. SQL vàng chạy lúc build và không được rỗng hay NULL. Bốn mức độ: L1 (bảng phẳng, không metric), L2 (truy cập dữ liệu lồng nhau), L3 (metric kinh doanh), L4 (khó: join, cohort, nhiều bước).
- **Chia tập:** mỗi họ có một ví dụ làm kho few-shot (37 câu train); 125 câu test, trong đó 108 trả lời được và 17 mơ hồ (không có SQL vàng, đúng khi hệ thống hỏi lại). Ba họ (`f_retention_d1`, `f_cart_abandon`, `f_top_categories`; 12 câu test) bị giữ ra hoàn toàn khỏi kho few-shot để đo khả năng khái quát.
- **Paraphrase:** 20 câu hỏi diễn đạt ngoài từ điển synonym, 19 câu liên kết với SQL vàng, để đo độ bền của bước resolve metric.

---

## 4. Phương pháp đánh giá

Chi tiết ở `docs/vi/05-danh-gia.md`.

### 4.1 Metric
| Metric | Cách dùng |
|---|---|
| **Execution Accuracy (EX)** | Chạy SQL vàng và SQL dự đoán trên cùng DB chỉ đọc, so kết quả. Metric chính. |
| Exact Match | Không dùng cho LLM vì phạt oan SQL đúng nhưng viết khác. Chỉ nêu khi trích dẫn paper cũ. |
| Valid-SQL rate | Tỷ lệ SQL chạy không lỗi (chẩn đoán). |
| Clarification P/R/F1 | Với câu mơ hồ: có hỏi lại không. Hỏi lại thừa ở câu rõ ràng bị phạt. |
| Độ trễ, token | Giây và token mỗi câu. |

### 4.2 Cách tính EX trong dự án
Chuẩn hóa giá trị (làm tròn số thực 4 chữ số, ngày thành chuỗi, list/struct thành tuple), cho phép hoán vị cột, chỉ bắt buộc thứ tự dòng khi SQL vàng có `ORDER BY`. Kiểm tra bằng test: SQL vàng so với chính nó phải đạt 100%. Với Spider/BIRD, gold-vs-gold đạt 30/30 trên mẫu thử.

### 4.3 Thiết kế thí nghiệm
- **Ablation tích lũy:** baseline, +linking, +fewshot, +semantic, +correction, +clarify.
- **Ablation riêng lẻ:** `semantic_only`, `correction_only`.
- **Model:** `qwen3:8b` (chính), `qwen2.5:3b`; adapter Anthropic/OpenAI đã có nhưng chưa chạy do thiếu API key.
- **Ngôn ngữ:** tiếng Việt (chính) và tiếng Anh.
- **Public benchmark:** mẫu cố định 200 câu (seed 123) từ Spider dev và BIRD dev.

### 4.4 Thống kê
Bootstrap 95% CI cho EX; kiểm định McNemar exact cho hai cấu hình trên cùng tập câu hỏi; báo cáo kích thước hiệu ứng ΔEX cạnh p-value.

---

## 5. Kết quả của các công trình trước

Nguồn: abstract trên arXiv (truy cập 2026-10-20). Xem `docs/vi/06-ket-qua-cac-cong-trinh-truoc.md`.

| Phương pháp | Benchmark / split | Kết quả |
|---|---|---|
| RAT-SQL | Spider (EM) | 57,2% (65,6% với BERT) |
| DIN-SQL | Spider test / BIRD test (EX) | 85,3% / 55,9% |
| DAIL-SQL | Spider (EX) | 86,6% |
| MAC-SQL + GPT-4 | BIRD test | 59,59% |
| CHESS | BIRD test | 71,10% (ít hơn khoảng 83% lần gọi LLM so với đầu bảng) |
| CHASE-SQL | BIRD dev / test | 73,01% / 73,0% |
| XiYan-SQL | BIRD / Spider test | 75,63% / 89,65% |
| ChatGPT (BIRD) | BIRD | 40,08% so với người 92,96% |
| o1-preview | Spider 2.0 | 21,3% (so với 91,2% Spider 1.0, 73,0% BIRD) |
| ReFoRCE | Spider 2.0-Snow / Lite | 35,83 / 36,56 |
| GPT-4 zero-shot, SQL trực tiếp | SQL QA doanh nghiệp | 16%, lên 54% khi hỏi qua knowledge graph |

**Rút ra:** (1) suy luận có cấu trúc kèm sửa lỗi bằng thực thi giúp rõ rệt; (2) sinh nhiều ứng viên rồi chọn đẩy điểm cao nhất nhưng đắt; (3) model nhỏ với dữ liệu/RL tốt cạnh tranh được với model lớn hơn nhiều lần; (4) khoảng cách học thuật và thực tế rất lớn; (5) ngữ nghĩa nghiệp vụ tường minh tăng mạnh độ chính xác. Dự án không cạnh tranh leaderboard BIRD (model 8B local, không voting) mà đo đóng góp tương đối của từng thành phần.

---

## 6. Phương pháp đề xuất

Chi tiết ở `docs/vi/07-phuong-phap-de-xuat.md`.

### 6.1 Kiến trúc
```
Câu hỏi
  ▼
[1. Ambiguity + Metric Resolver] ← semantic/events.yaml
  │ mơ hồ? → hỏi lại người dùng (không gọi LLM)
  ▼
[2. Schema Linker + Event Profiler]  (BM25; liệt kê event và key trong event_params)
  ▼
[3. Prompt Builder] schema + event catalog + định nghĩa metric + 3 ví dụ few-shot
  ▼
[4. SQL Generator (LLM)]
  ▼
[5. Validator/Executor] chỉ SELECT/WITH, DuckDB read-only
  │ lỗi / rỗng / toàn NULL? → [6. Self-Correction] (tối đa 2 vòng)
  ▼
Kết quả + SQL + metric đã dùng
```

### 6.2 Semantic/metric layer
Tệp YAML (`semantic/events.yaml`) định nghĩa 15 metric (revenue, item_revenue, ad_revenue, orders, aov, items_sold, dau, mau, paying_users, arppu, conversion_rate, cart_conversion_rate, cart_abandonment_rate, tutorial_completion_rate, retention_d1). Mỗi metric có mô tả nghiệp vụ, synonym tiếng Việt và tiếng Anh, và công thức SQL chuẩn. Ngoài ra có hướng dẫn truy cập `event_params`/`items` và **luật mơ hồ** (ví dụ "doanh thu" gồm revenue, item_revenue, ad_revenue; "tỷ lệ chuyển đổi" gồm conversion_rate và cart_conversion_rate). Resolver khớp synonym dài nhất trước (để "ad revenue" không bị nhận nhầm thành "revenue") và mở rộng phụ thuộc (AOV kéo theo revenue và orders). Ý tưởng mượn từ dbt MetricFlow, Cube: định nghĩa một lần, dùng mọi nơi.

**LLM fallback:** resolver theo từ điển rất dễ gãy khi người dùng diễn đạt khác (xem §7.6). Dự án thêm `resolve_llm`: khi luật không bắt được metric, hỏi LLM chọn metric từ danh sách trong semantic layer. Cấu hình này được bật mặc định cho demo.

### 6.3 Các thành phần còn lại
- **Schema linking:** BM25 tự cài (không dùng thư viện) trên tên bảng/cột; schema nhỏ giữ nguyên. **Event profiler** quét dữ liệu để liệt kê event và key trong `event_params`, thông tin mà LLM không thể suy ra từ DDL.
- **Few-shot retrieval:** chọn 3 cặp (câu hỏi, SQL) gần nhất bằng BM25 từ kho train, theo bài học của DAIL-SQL.
- **Tự sửa lỗi:** khi SQL lỗi hoặc kết quả rỗng/toàn NULL, đưa câu hỏi, SQL cũ, thông báo lỗi lại cho LLM; tối đa 2 vòng.
- **Hỏi lại:** câu hỏi làm rõ liệt kê các định nghĩa ứng viên; không gọi LLM.
- **An toàn:** chỉ chấp nhận SELECT/WITH; DuckDB read-only; SQLite `mode=ro` kèm timeout.

### 6.4 Ánh xạ cấu hình ablation
| Cấu hình | Bật |
|---|---|
| baseline | chỉ DDL và câu hỏi |
| +linking | cắt schema và event catalog |
| +fewshot | thêm 3 ví dụ truy xuất |
| +semantic | thêm định nghĩa metric |
| +correction | thêm tự sửa tối đa 2 vòng |
| +clarify | thêm hỏi lại khi mơ hồ |
| semantic_only / correction_only | chỉ bật đúng thành phần đó |

---

## 7. Thí nghiệm và kết quả

Chi tiết ở `docs/vi/09-ket-qua-thi-nghiem.md`.

### 7.1 Ablation trên EventSQL-Bench (`qwen3:8b`, câu hỏi tiếng Việt, 108 câu)
| Cấu hình | EX | L1 | L2 | L3 | L4 | Họ chưa thấy (n=12) |
|---|---|---|---|---|---|---|
| baseline | 0,352 | 0,93 | 0,00 | 0,42 | 0,09 | 3/12 |
| +linking | 0,296 | 0,93 | 0,00 | 0,36 | 0,00 | 0/12 |
| +fewshot | 0,880 | 1,00 | 1,00 | 0,98 | 0,64 | 3/12 |
| +semantic | 0,963 | 1,00 | 1,00 | 0,98 | 0,91 | 10/12 |
| +correction | 0,981 | 1,00 | 1,00 | 0,98 | 0,97 | 12/12 |
| +clarify | 0,981 | 1,00 | 1,00 | 0,98 | 0,97 | 12/12 |
| semantic_only | 0,444 | 0,53 | 0,70 | 0,38 | 0,42 | 6/12 |
| correction_only | 0,370 | 0,93 | 0,00 | 0,46 | 0,09 | 3/12 |

Kiểm định McNemar (cùng tập câu hỏi):
- +linking so với baseline: p = 0,031, **tệ hơn có ý nghĩa**.
- +semantic so với +fewshot: p = 0,0039.
- +correction so với +semantic: p = 0,5 (không có ý nghĩa).
- semantic_only so với baseline: p = 0,19; correction_only so với baseline: p = 0,5 (cả hai không có ý nghĩa).
- Nhóm chưa thấy: +semantic so với +fewshot p = 0,0156; +correction so với +fewshot p = 0,0039.

Khoảng tin cậy bootstrap 95%: baseline [0,27; 0,44], +fewshot [0,81; 0,94], +semantic [0,93; 0,99], +correction [0,95; 1,00].

**Làm rõ câu mơ hồ (17 câu):** precision, recall, F1 đều bằng 1,00. Đây là cận trên vì hành vi hỏi lại dựa trên luật và các câu mơ hồ cùng phân phối với luật.

**Chi phí:** 2,6 đến 4,6 giây mỗi câu; prompt tăng từ 191 token (baseline) lên khoảng 710 (+semantic); `correction_only` tốn 10 giây mỗi câu (trung bình 1,93 lần thử) vì sửa nhiều lần mà không có ví dụ dẫn hướng.

### 7.2 Phân loại lỗi (baseline, 108 câu)
Đúng 38; `schema_error` 43; `wrong_result` 22; `runtime_error` 5. Hai nguyên nhân chính của baseline: (a) không biết cú pháp truy cập `event_params` (mức L2 đạt 0%, dù đã có event catalog, vì model không biết `list_filter` của DuckDB); (b) chọn sai định nghĩa metric (L4 chỉ 0,09). Few-shot sửa (a) gần hết, semantic layer sửa phần lớn (b).

### 7.3 Ngôn ngữ và kích thước model
| Model | Ngôn ngữ | baseline | +fewshot | +semantic | +correction |
|---|---|---|---|---|---|
| qwen3:8b | Việt | 0,352 | 0,880 | 0,963 | 0,981 |
| qwen3:8b | Anh | 0,333 | 0,889 | 0,991 | không chạy |
| qwen2.5:3b | Việt | 0,167 | 0,556 | 0,556 | 0,657 |

Xu hướng giống nhau giữa hai ngôn ngữ. Model 3B hưởng lợi từ pipeline (0,167 lên 0,657) nhưng thấp xa model 8B, và semantic layer không giúp thêm ở cỡ này.

### 7.4 Spider và BIRD (200 câu mẫu, `qwen3:8b`)
| Cấu hình | Spider dev | BIRD dev |
|---|---|---|
| baseline | 0,720 | 0,240 |
| +linking | 0,725 | 0,155 |
| knowledge_only (chỉ evidence) | không chạy | 0,345 |
| +knowledge (linking và evidence) | không chạy | 0,220 |
| +correction | không chạy | 0,250 |

Trên Spider schema nhỏ nên linking gần như không đổi. Trên BIRD, evidence tăng EX từ 0,240 lên 0,345, nhưng linking kéo xuống. Evidence của BIRD đóng vai trò gần với semantic layer, nên đây là bằng chứng gián tiếp ủng hộ H2. Với n = 200 sai số chuẩn khoảng ±3 điểm phần trăm; các con số này không so trực tiếp với leaderboard.

### 7.5 Hỏi lại và số seed
Ba seed (0, 1, 2) cho kết quả giống hệt nhau (độ lệch chuẩn 0) vì temperature = 0 và Ollama cho kết quả xác định với seed cố định. Do đó "mean ± std" trong bảng tổng hợp không đo biến thiên thật; độ tin cậy dựa vào bootstrap CI và McNemar. Đo biến thiên do lấy mẫu cần chạy với temperature lớn hơn 0 (chưa làm).

### 7.6 Độ bền với diễn đạt ngoài từ điển (20 paraphrase)
| Cấu hình | Metric resolver recall | EX end-to-end |
|---|---|---|
| no_semantic | 0/20 | 11/19 (0,58) |
| semantic_rule | 0/20 | 10/19 (0,53) |
| semantic_rule + LLM fallback | 17/20 | 17/19 (0,89) |

Resolver theo từ điển không bắt được paraphrase nào. Điều này cho thấy mức 100% trên 162 câu gốc chỉ là cận trên, vì synonym được viết cùng lúc với câu hỏi. Bản chỉ dùng luật còn kém hơn cả không dùng semantic layer (10/19 so với 11/19), nhưng mẫu quá nhỏ để kết luận về chênh lệch này. LLM fallback phục hồi recall lên 17/20 và EX lên 0,89.

### 7.7 Kết luận theo giả thuyết
- **H1 (agentic tốt hơn prompt đơn):** ủng hộ yếu. Tự sửa lỗi đứng riêng không có ý nghĩa thống kê (0,352 lên 0,370); đặt cuối pipeline chỉ thêm 0,018 (p = 0,5). Nó chủ yếu sửa lỗi hiện rõ (cú pháp, tên cột), không sửa được lỗi âm thầm như chọn sai metric. Phần cải thiện lớn đến từ few-shot và semantic layer.
- **H2 (semantic layer giúp):** ủng hộ. Thêm 0,083 EX so với few-shot (p = 0,0039); L4 từ 0,64 lên 0,91; họ chưa thấy từ 3/12 lên 10/12; BIRD evidence đi cùng chiều; LLM fallback giữ được lợi ích khi paraphrase.
- **H3 (model local nhỏ kèm semantic layer ≈ API lớn):** **không kiểm chứng được** vì thiếu API key. Chỉ có một điểm dữ liệu: model 3B đạt 0,657.

### 7.8 Điều bất ngờ: schema linking làm tệ hơn
BM25 schema linking giảm EX trên EventSQL (0,352 xuống 0,296; p = 0,031) và trên BIRD (0,240 xuống 0,155). Các lỗi quan sát thấy: cột mơ hồ trong JOIN, và dùng sai `event_params[?]` như tham số prepared statement. Nguyên nhân gốc chưa được kiểm chứng; giả thuyết là việc cắt schema làm mất ngữ cảnh model cần. Đây là kết quả âm cần ghi nhận, không phải lỗi che giấu.

---

## 8. Hạn chế và mối đe dọa đến tính hợp lệ

1. **Thiên lệch cùng tác giả:** SQL vàng và SQL trong YAML do cùng một người viết; SQL trong semantic layer gần như trùng SQL vàng, nên kết quả `+semantic` lạc quan. Cách giảm: nhờ người thứ hai viết SQL vàng độc lập.
2. **Rò rỉ khuôn mẫu few-shot:** phần lớn mức tăng của few-shot đến từ tái sử dụng khuôn mẫu cùng họ; họ chưa thấy chỉ đạt 3/12.
3. **Nhóm chưa thấy chỉ có n = 12**, nên các kết luận ở nhóm này mang tính gợi ý.
4. **EX trên một DB**, chưa phải test-suite accuracy; kết quả trùng tình cờ có thể làm EX cao hơn thực tế.
5. **Dữ liệu tổng hợp, một DB**; không đại diện cho dữ liệu sản xuất.
6. **Contamination:** Spider và BIRD có thể nằm trong dữ liệu huấn luyện của model.
7. **Mẫu 200 câu, một lần chạy** trên public benchmark; không có biến thiên giữa các seed (§7.5).
8. **Hỏi lại F1 = 1,00 là cận trên** (dựa trên luật, cùng phân phối).
9. **Chưa thực hiện:** model API (H3), Spider 2.0, Dr.Spider, test-suite accuracy; `+correction` tiếng Anh; một số cấu hình Spider.
10. Streamlit demo đã khởi chạy được nhưng chưa được kiểm thử tương tác trên trình duyệt; CLI đã kiểm thử.

---

## 9. Kết luận và hướng phát triển

Dự án cho thấy với dữ liệu event lồng nhau, **ngữ nghĩa nghiệp vụ tường minh là đòn bẩy lớn hơn bản thân vòng lặp agent**: semantic layer nâng EX từ 0,880 lên 0,963 (p = 0,0039) và giúp khái quát sang họ câu hỏi chưa thấy, trong khi tự sửa lỗi chỉ xử lý lỗi hiện rõ. Kết quả có ý nghĩa thực hành: đầu tư vào định nghĩa metric đáng giá hơn thêm vòng lặp. Đồng thời, dự án ghi nhận kết quả âm về schema linking BM25 và về độ gãy của resolver theo từ điển (cần LLM fallback).

**Hướng phát triển:**
1. Chạy model API để kiểm chứng H3 và đo chi phí.
2. Thay schema linker bằng embedding và giữ lại cột khóa; tìm nguyên nhân thật của việc linking làm tệ hơn.
3. Người thứ hai viết SQL vàng độc lập; test-suite accuracy.
4. Majority voting nhiều ứng viên (CHASE-SQL, Arctic-Text2SQL-R1).
5. Fine-tune hoặc RL model nhỏ với reward thực thi trên dữ liệu tổng hợp từ semantic layer.
6. Spider 2.0 (GA4) để kiểm chứng trên dữ liệu thật; hội thoại nhiều lượt; học semantic layer tự động từ log truy vấn.

---

## Phụ lục A. Tái lập kết quả
```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev,app]"
.venv/bin/python benchmarks/eventsql/build.py                     # sinh dữ liệu và câu hỏi
.venv/bin/python -m querycraft.cli "ARPPU của tháng 2/2026 là bao nhiêu?"
.venv/bin/python experiments/run_eventsql.py --llm ollama:qwen3:8b --lang vi --seeds 0 --tag main
.venv/bin/python experiments/run_public.py --dataset bird --n 200 --llm ollama:qwen3:8b
.venv/bin/python experiments/run_paraphrase.py
.venv/bin/python experiments/report.py --tag main --out experiments/results_main.md
.venv/bin/streamlit run app/app.py                                 # demo
```
Chi tiết, kể cả cách chạy với model API: `docs/vi/08-huong-dan-thuc-hanh.md`. Có 23 test pytest.

## Phụ lục B. Tài liệu tham khảo (arXiv)
Spider; BIRD (2305.03111); RAT-SQL (1911.04942); PICARD (2109.05093); RESDSQL (2302.05965); CodeS (2402.16347); DIN-SQL (2304.11015); DAIL-SQL (2308.15363); MAC-SQL (2312.11242); CHESS (2405.16755); CHASE-SQL (2410.01943); XiYan-SQL (2411.08599); OmniSQL (2503.02240); Arctic-Text2SQL-R1 (2505.20315); Spider 2.0 (2411.07763); ReFoRCE (2502.00675); Knowledge graph cho SQL doanh nghiệp (2311.07509); Dr.Spider. Danh sách đọc theo thứ tự ưu tiên: `docs/vi/reading-list.md`.
