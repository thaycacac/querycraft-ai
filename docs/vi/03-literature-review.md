# 03. Literature review: Text-to-SQL từ seq2seq đến agentic + semantic layer

> Số liệu lấy từ phần tóm tắt (abstract) trên arXiv, truy cập 2026-10-20. Leaderboard thay đổi liên tục; khi trích dẫn trong báo cáo hãy mở lại paper/leaderboard để xác nhận. Mục nào không có số tức là tóm tắt không nêu.

## 1. Dòng thời gian
```
2017-2019  Seq2SQL, SQLNet (WikiSQL) → Spider (2018) → RAT-SQL (2019)
2021       PICARD (constrained decoding), T5 fine-tune
2022-2023  RESDSQL, LLM prompting: C3, DIN-SQL, DAIL-SQL, BIRD (2023), CodeS
2023-2024  Multi-agent/pipeline: MAC-SQL, CHESS, CHASE-SQL, XiYan-SQL
2024-2025  Fine-tune + RL: OmniSQL, Arctic-Text2SQL-R1; enterprise: Spider 2.0, ReFoRCE
2023-nay   Semantic layer / knowledge graph cho SQL doanh nghiệp; sản phẩm: Metabot, Vanna, WrenAI...
```

## 2. Giai đoạn 1: mô hình thần kinh chuyên biệt
**RAT-SQL** (Wang et al., 2019, arXiv:1911.04942): mã hóa schema và câu hỏi cùng nhau bằng *relation-aware self-attention*, gộp schema encoding, schema linking và biểu diễn đặc trưng vào một encoder. Paper báo cáo exact match 57.2% trên Spider (tăng 8.7 điểm tuyệt đối so với đối thủ gần nhất lúc đó) và 65.6% khi dùng BERT.
- Mạnh: ý tưởng *quan hệ giữa các phần tử schema* vẫn là nền tảng cho schema linking sau này.
- Yếu: cần huấn luyện riêng, chỉ khớp với phân phối Spider, không xử lý tri thức miền.

## 3. Giai đoạn 2: fine-tune mô hình ngôn ngữ tiền huấn luyện
- **PICARD** (Scholak et al., 2021, arXiv:2109.05093): *ràng buộc giải mã* bằng phân tích cú pháp tăng dần, loại bỏ token tạo ra SQL không hợp lệ ở từng bước, nâng các T5 fine-tune lên mức SOTA lúc đó. Mạnh: đảm bảo cú pháp. Yếu: chậm, và đúng cú pháp chưa chắc đúng nghĩa.
- **RESDSQL** (Li et al., 2023, arXiv:2302.05965): *tách* schema linking khỏi phân tích cú pháp: encoder nhận các phần tử schema đã xếp hạng, decoder sinh *skeleton* SQL trước rồi mới sinh SQL đầy đủ. Mạnh: giảm gánh nặng cho decoder. Yếu: vẫn cần huấn luyện, khó khái quát sang miền mới.
- **CodeS** (arXiv:2402.16347): họ mô hình mã nguồn mở 1B-15B cho Text-to-SQL, đánh giá trên Spider, BIRD, Spider-DK/Syn/Realistic, Dr.Spider. Mạnh: nhỏ, chạy cục bộ. Yếu: kém model lớn khi suy luận phức tạp.

## 4. Giai đoạn 3: prompting LLM
- **DIN-SQL** (Pourreza & Rafiei, 2023, arXiv:2304.11015): chia bài toán thành module (schema linking, phân loại độ khó, sinh SQL, tự sửa) và dùng prompt cho từng module. Báo cáo 85.3 EX trên Spider test và 55.9 trên BIRD test (khi đó là SOTA). Mạnh: không cần huấn luyện. Yếu: nhiều lần gọi LLM, tốn token, prompt thủ công.
- **DAIL-SQL** (Gao et al., 2023, arXiv:2308.15363): khảo sát có hệ thống biểu diễn prompt, cách chọn và tổ chức ví dụ few-shot; đạt 86.6% EX trên Spider và nhấn mạnh hiệu quả token. Bài học: *chọn ví dụ theo độ tương đồng* quan trọng. Dự án dùng ý tưởng này ở `ExampleRetriever`.
- **C3** (zero-shot với ChatGPT): thiết kế prompt rõ ràng, gợi ý hiệu chỉnh và nhất quán. Mạnh: zero-shot. Yếu: phụ thuộc model đóng.

## 5. Giai đoạn 4: pipeline nhiều agent
- **MAC-SQL** (arXiv:2312.11242): ba agent: Selector (cắt schema), Decomposer (chia nhỏ câu hỏi và sinh SQL từng bước), Refiner (sửa dựa trên lỗi thực thi). Báo cáo 59.59 EX trên BIRD test với GPT-4; bản SQL-Llama đạt 43.94 so với 46.35 của GPT-4 thuần. Dự án dùng tinh thần Selector + Refiner.
- **CHESS** (arXiv:2405.16755): pipeline gồm truy xuất thông tin (entity/context), chọn schema, sinh và kiểm tra ứng viên. Báo cáo 71.10% trên BIRD test, trong vòng 2 điểm so với phương pháp độc quyền tốt nhất nhưng dùng ít hơn khoảng 83% số lần gọi LLM; dẫn đầu nhóm mô hình mở.
- **CHASE-SQL** (arXiv:2410.01943): sinh nhiều ứng viên bằng chiến lược đa dạng rồi chọn bằng bộ xếp hạng cặp. Báo cáo 73.01% (dev) và 73.0% (test) trên BIRD.
- **XiYan-SQL** (arXiv:2411.08599): kết hợp nhiều ứng viên và mô hình chọn; báo cáo 75.63% trên BIRD, 89.65% trên Spider test.
- Mạnh chung: độ chính xác cao nhất ở các benchmark học thuật. Yếu chung: tốn chi phí gọi LLM, độ trễ cao, tối ưu cho benchmark hơn là cho miền doanh nghiệp.

## 6. Giai đoạn 5: fine-tune quy mô lớn và học tăng cường
- **OmniSQL** (arXiv:2503.02240): xây **SynSQL-2.5M** (2,5 triệu mẫu trên hơn 16.000 database tổng hợp, kèm lời giải CoT) và huấn luyện model 7B/14B/32B; báo cáo đạt hoặc vượt các LLM hàng đầu trên chín bộ dữ liệu dù nhỏ hơn.
- **Arctic-Text2SQL-R1** (arXiv:2505.20315): RL với tín hiệu thưởng đơn giản *chỉ dựa trên độ đúng khi thực thi*; bản 7B vượt các hệ 70B ở nhóm cùng thời, đứng đầu BIRD khi công bố; dùng value retrieval và majority voting.
- Mạnh: model nhỏ chạy cục bộ, rẻ. Yếu: cần hạ tầng huấn luyện; vẫn không biết định nghĩa nghiệp vụ riêng của bạn.

## 7. Bài toán doanh nghiệp: Spider 2.0 và semantic layer
- **Spider 2.0** (arXiv:2411.07763): benchmark workflow doanh nghiệp (schema lớn, nhiều dialect, tác vụ phân tích). Trong khung agent của tác giả, o1-preview chỉ giải được **21,3%** so với 91,2% trên Spider 1.0 và 73,0% trên BIRD. Thông điệp: các con số học thuật không đại diện cho môi trường thực.
- **ReFoRCE** (arXiv:2502.00675): agent nén thông tin database, sửa lỗi cú pháp/ngữ nghĩa đa dialect, voting và khám phá cột theo phản hồi thực thi; báo cáo 35,83 (Spider 2.0-Snow) và 36,56 (Spider 2.0-Lite) khi đứng đầu bảng.
- **Knowledge graph / semantic layer cho SQL doanh nghiệp** (arXiv:2311.07509): GPT-4 zero-shot trực tiếp trên SQL đạt **16%**, khi hỏi qua biểu diễn knowledge graph của database đạt **54%**. Đây là bằng chứng gần nhất cho giả thuyết H2 của dự án (ngữ nghĩa nghiệp vụ tường minh tăng độ chính xác).

## 8. Sản phẩm và hệ thống công nghiệp
- **Metabase Metabot**: sinh và gỡ lỗi SQL từ prompt; theo mô tả của Metabase, SQL được *neo vào metadata và semantic layer* (metrics, định nghĩa) của chính Metabase thay vì LLM tách rời, chạy với quyền của người dùng đăng nhập. Nhà cung cấp LLM có thể thay đổi. Chi tiết kiến trúc nội bộ không được công bố ở nguồn tôi kiểm tra; hãy đọc docs và mã nguồn Metabase để đối chiếu.
- **Vanna** (RAG trên DDL, tài liệu, câu hỏi-SQL mẫu), **WrenAI** (semantic layer dạng MDL), **Dataherald**, **DB-GPT**; hệ thống nội bộ như QueryGPT (Uber), Pinterest, LinkedIn SQL Bot. Cần đọc blog kỹ thuật của từng công ty để trích dẫn chính xác.
- **dbt MetricFlow, Cube**: tầng metric dùng chung cho BI; dự án mượn ý tưởng *định nghĩa metric một lần, dùng mọi nơi*.

## 9. Bảng so sánh tổng hợp
| Nhóm | Đại diện | Cần huấn luyện | Chi phí suy luận | Điểm mạnh | Điểm yếu |
|---|---|---|---|---|---|
| Neural chuyên biệt | RAT-SQL | Có | Thấp | Schema encoding | Kém khái quát |
| Fine-tune PLM | PICARD, RESDSQL, CodeS | Có | Thấp-TB | Cú pháp, chạy cục bộ | Cần dữ liệu |
| Prompting LLM | DIN-SQL, DAIL-SQL, C3 | Không | Trung bình | Nhanh triển khai | Phụ thuộc model, prompt thủ công |
| Pipeline/agent | MAC-SQL, CHESS, CHASE-SQL, XiYan | Không/ít | Cao | Chính xác nhất trên BIRD | Đắt, chậm |
| Fine-tune + RL | OmniSQL, Arctic-R1 | Có | Thấp-TB | Model nhỏ mạnh | Hạ tầng huấn luyện |
| Enterprise agent | ReFoRCE | Không | Cao | Schema lớn, đa dialect | Vẫn thấp trên Spider 2.0 |
| Semantic layer | Metabot, MetricFlow, WrenAI | Không | Thấp | Định nghĩa nghiệp vụ nhất quán, kiểm soát được | Phải xây và bảo trì |

## 10. Khoảng trống nghiên cứu → đóng góp của dự án
1. Benchmark học thuật chủ yếu là bảng quan hệ phẳng; **dữ liệu event lồng nhau + metric nghiệp vụ** ít được đo.
2. Ít công trình **đo riêng đóng góp của semantic layer** bằng ablation có kiểm định thống kê.
3. **Hỏi lại khi mơ hồ** hiếm khi được đánh giá như một nhiệm vụ riêng.
4. Dự án đóng góp: EventSQL-Bench, kiến trúc agent + semantic layer, ablation trên model mở chạy cục bộ so với API.

## 11. Cách đọc paper hiệu quả (để học)
Mỗi paper ghi 5 dòng: vấn đề, ý tưởng chính, dữ liệu/metric, kết quả, hạn chế. Sau đó tự hỏi "nếu áp dụng vào dữ liệu event lồng nhau thì phần nào hỏng?".

## 12. Tự kiểm tra
1. Vì sao PICARD đảm bảo cú pháp nhưng không đảm bảo kết quả đúng?
2. DAIL-SQL rút ra điều gì về chọn ví dụ few-shot?
3. Vì sao Spider 2.0 thấp hơn nhiều so với Spider 1.0?
4. Kết quả 16% → 54% của knowledge graph ủng hộ giả thuyết nào của dự án?
