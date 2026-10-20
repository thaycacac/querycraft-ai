# 02. Text-to-SQL cơ bản và dữ liệu event lồng nhau

## 1. Định nghĩa
Cho câu hỏi tự nhiên `q` và schema `S` của database `D`, sinh ra SQL `y` sao cho thực thi `y` trên `D` trả về đúng đáp án người hỏi muốn.

Các thành phần của một hệ thống hiện đại:
1. **Hiểu câu hỏi** (ý định, thực thể, thời gian).
2. **Schema linking**: chọn bảng/cột liên quan.
3. **Giải quyết thuật ngữ nghiệp vụ** (metric).
4. **Sinh SQL**.
5. **Kiểm tra và sửa** bằng cách thực thi.

## 2. Ôn SQL cần cho dự án (DuckDB)
```sql
-- Join và nhóm
SELECT u.acquisition_channel, COUNT(*) FROM users u GROUP BY 1;

-- FILTER: đếm có điều kiện trong cùng một lần quét
SELECT COUNT(DISTINCT user_pseudo_id) FILTER (WHERE event_name='purchase') FROM events;

-- CTE
WITH d AS (SELECT event_date, COUNT(DISTINCT user_pseudo_id) n FROM events GROUP BY 1)
SELECT AVG(n) FROM d;

-- Dữ liệu lồng nhau: đọc một param trong LIST(STRUCT)
SELECT list_filter(event_params, p -> p.key='value')[1].value.double_value FROM events;

-- UNNEST: mở rộng mảng items thành nhiều dòng
SELECT i.category, SUM(i.price*i.quantity)
FROM events e, UNNEST(e.items) AS t(i) GROUP BY 1;
```
Lưu ý: `GROUP BY 1` nhóm theo cột đầu của SELECT; `bool_or` gộp điều kiện theo user; `date + INTERVAL 1 DAY` để cộng ngày.

## 3. Vì sao dữ liệu tracking khó
Dữ liệu kiểu GA4/Firebase lưu mỗi event một dòng với tham số trong mảng `event_params` (key, value gồm `string_value`, `int_value`, `double_value`). Hệ quả cho LLM:
- Không có cột `revenue`; phải biết `revenue` nằm trong `event_params` có `key='value'`, ở trường `double_value`, và chỉ của event `purchase`.
- **Không đoán được từ DDL**: tên key và trường giá trị nằm trong *dữ liệu*, không nằm trong schema. Vì thế dự án có bước **profiling tự động** (`profile_events` trong `src/querycraft/db.py`) liệt kê event và key đang có.
- Cùng một từ ("doanh thu") có nhiều nghĩa: doanh thu bán hàng (gồm ship), doanh thu sản phẩm, doanh thu quảng cáo → cần semantic layer và khả năng hỏi lại.

## 4. Các thách thức cốt lõi và cách dự án xử lý
| Thách thức | Biểu hiện | Cách xử lý trong dự án |
|---|---|---|
| Schema linking | Chọn sai bảng/cột | BM25 trên tên bảng/cột + profiling event |
| Tri thức miền | DAU, ARPPU, retention | Semantic layer YAML (`semantic/events.yaml`) |
| Mơ hồ | "Doanh thu" không rõ loại | Quy tắc `ambiguity_rules` → hỏi lại |
| Dữ liệu lồng nhau | Quên UNNEST/list_filter | Hướng dẫn truy cập trong semantic layer + few-shot |
| Lỗi thực thi | Sai tên cột, sai cú pháp | Vòng tự sửa lỗi với thông báo lỗi |
| Kết quả "đúng cú pháp nhưng sai nghĩa" | Trả về rỗng/NULL | Phát hiện kết quả rỗng → yêu cầu sửa |
| An toàn | `DROP TABLE` | Chỉ cho phép SELECT/WITH, mở DB read-only |

## 5. Hai loại sai lầm cần phân biệt
- **Lỗi nhìn thấy được**: SQL không chạy (parser/binder error). Vòng tự sửa lỗi xử lý tốt.
- **Lỗi im lặng**: SQL chạy ra số sai (ví dụ dùng sai định nghĩa metric). Chỉ semantic layer, few-shot đúng và đánh giá bằng Execution Accuracy mới phát hiện được. Đây là lý do semantic layer quan trọng hơn self-correction cho dữ liệu nghiệp vụ.

## 6. Bài thực hành
1. Mở `data/eventsql.duckdb` bằng DuckDB CLI, chạy `DESCRIBE events;` và `SELECT * FROM events WHERE event_name='purchase' LIMIT 3;`.
2. Tự viết SQL tính DAU ngày 2026-01-15, rồi so với `gold_sql` trong `benchmarks/eventsql/questions.jsonl`.
3. Viết SQL cho "doanh thu theo kênh acquisition" (cần JOIN `users`), đối chiếu họ câu hỏi `f_revenue_channel`.

## 7. Tự kiểm tra
1. Vì sao DDL không đủ để viết đúng SQL cho `event_params`?
2. Sự khác nhau giữa `revenue` và `item_revenue` trong dự án là gì?
3. Cho một ví dụ lỗi im lặng và nêu cách phát hiện.
