# 01. Nền tảng NLP cần biết cho Text-to-SQL

Mục tiêu: sau chương này bạn giải thích được vì sao LLM làm được Text-to-SQL, và những giới hạn của nó nằm ở đâu.

## 1. Bài toán NLP ở mức tổng quát
NLP biến văn bản thành biểu diễn máy xử lý được, rồi từ biểu diễn đó sinh ra kết quả (nhãn, văn bản, cấu trúc). Text-to-SQL thuộc nhóm **semantic parsing**: chuyển câu tự nhiên thành một **biểu diễn hình thức có thể thực thi** (SQL). Khác với dịch máy, đầu ra phải **đúng cú pháp** và **đúng ngữ nghĩa trên một database cụ thể**.

## 2. Biểu diễn văn bản
- **Tokenization**: chia văn bản thành token (từ con). BPE/WordPiece/SentencePiece tách `session_start` thành nhiều mảnh. Hệ quả: tên cột dài và có `_` tốn nhiều token; tiếng Việt thường tốn nhiều token hơn tiếng Anh.
- **Embedding**: mỗi token là một vector. Từ gần nghĩa có vector gần nhau (word2vec, GloVe là bản tĩnh; Transformer cho vector phụ thuộc ngữ cảnh).
- **Sparse vs dense retrieval**: BM25 (đếm từ, có IDF) khớp từ khóa chính xác; embedding khớp nghĩa. Dự án này tự cài BM25 trong `src/querycraft/linker.py` để thấy rõ cơ chế.

## 3. Từ RNN đến Transformer
| Giai đoạn | Ý tưởng | Hạn chế |
|---|---|---|
| RNN/LSTM seq2seq | Đọc tuần tự, nén cả câu vào một vector | Quên thông tin xa, khó song song hóa |
| Attention (Bahdanau) | Khi sinh mỗi từ, "nhìn lại" các vị trí của nguồn | Vẫn tuần tự |
| Transformer | Self-attention: mọi token nhìn mọi token cùng lúc | Chi phí O(n²) theo độ dài |
| Pretrained LM (BERT, T5) | Học trước trên văn bản khổng lồ rồi fine-tune | Cần dữ liệu có nhãn cho từng tác vụ |
| LLM (GPT, Claude, Qwen...) | Mô hình rất lớn, làm tác vụ qua prompt | Có thể "bịa" (hallucination), tốn chi phí |

**Self-attention** tính cho mỗi token một tổ hợp có trọng số của các token khác: `Attention(Q,K,V) = softmax(QKᵀ/√d)·V`. Trong Text-to-SQL, nó cho phép liên kết từ "doanh thu" trong câu hỏi với cột `value` trong schema khi cả hai nằm trong cùng một ngữ cảnh.

## 4. LLM và prompting
- **Zero-shot**: chỉ đưa schema và câu hỏi. Đây là baseline của dự án.
- **Few-shot / in-context learning**: đưa thêm vài cặp (câu hỏi, SQL). DAIL-SQL chứng minh cách *chọn* ví dụ (theo độ tương đồng câu hỏi và cấu trúc SQL) quan trọng.
- **Chain-of-thought (CoT)**: bắt model suy luận từng bước trước khi viết SQL; DIN-SQL chia bài toán thành các bước nhỏ.
- **Self-consistency / majority voting**: sinh nhiều SQL, thực thi, chọn kết quả xuất hiện nhiều nhất (CHASE-SQL, Arctic-Text2SQL-R1, ReFoRCE dùng ý tưởng này).
- **Tool use / agent**: LLM gọi công cụ (thực thi SQL, xem schema) và lặp. Dự án cài vòng lặp tự sửa lỗi dựa trên thông báo lỗi của database.
- **Temperature**: 0 cho kết quả ổn định (dùng trong benchmark); cao hơn để đa dạng khi cần voting.

## 5. Fine-tuning và RL (hiểu để đọc literature)
- **SFT**: học từ cặp (câu hỏi+schema → SQL). CodeS, OmniSQL huấn luyện kiểu này.
- **RL với phần thưởng thực thi**: thưởng khi SQL chạy ra đúng kết quả (Arctic-Text2SQL-R1 dùng tín hiệu thưởng đơn giản dựa trên độ đúng khi thực thi).
- **Distillation**: dùng model lớn sinh dữ liệu để dạy model nhỏ (OmniSQL sinh SynSQL-2.5M).
- Dự án này **không fine-tune**; đây là hướng mở rộng (xem mục 6 của doc 07).

## 6. Vì sao Text-to-SQL khó với LLM
1. **Schema linking**: schema lớn không vừa ngữ cảnh, tên cột khó hiểu.
2. **Mơ hồ**: một câu có nhiều cách hiểu.
3. **Tri thức miền**: "DAU", "retention" không có trong schema.
4. **Dữ liệu lồng nhau**: cần `UNNEST`, truy cập struct/list.
5. **Dialect**: BigQuery, Snowflake, DuckDB, SQLite khác nhau.
6. **Đánh giá**: SQL khác nhau có thể cho cùng kết quả (nên dùng Execution Accuracy, xem doc 05).

## 7. Bài thực hành
1. Đọc `src/querycraft/linker.py`, giải thích bằng lời công thức BM25 và vai trò của `k1`, `b`.
2. Dùng Ollama chạy cùng một câu hỏi với `temperature=0` và `1.0`, so sánh SQL.
3. Đếm token của một prompt tiếng Việt và bản tiếng Anh tương đương (xem `prompt_tokens` trong file `.jsonl` ở `experiments/runs/`).

## 8. Tự kiểm tra
1. Vì sao self-attention giúp ích cho schema linking hơn RNN?
2. Few-shot khác fine-tune ở điểm nào về chi phí và rủi ro?
3. Vì sao đặt temperature = 0 trong benchmark, và khi nào bạn cần temperature > 0?
