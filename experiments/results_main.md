# Kết quả EventSQL-Bench (tag `main`)


## Model `ollama/qwen2.5:3b` - ngôn ngữ câu hỏi `vi`

| Cấu hình | EX (mean±std) | #seed | 95% CI (seed đầu) | L1 | L2 | L3 | L4 | Unseen | Valid-SQL | Lần thử TB | Prompt tok/câu | Giây/câu | Clarif P/R/F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.167 | 1 | [0.10, 0.24] | 0.73 | 0.00 | 0.00 | 0.21 | 0.58 | 0.32 | 1.00 | 183 | 2.6 | 0.00/0.00/0.00 |
| +linking | 0.083 | 1 | [0.04, 0.14] | 0.47 | 0.00 | 0.04 | 0.00 | 0.00 | 0.26 | 1.00 | 318 | 2.4 | 0.00/0.00/0.00 |
| +fewshot | 0.556 | 1 | [0.46, 0.65] | 0.67 | 0.90 | 0.58 | 0.36 | 0.17 | 0.66 | 1.00 | 558 | 2.1 | 0.00/0.00/0.00 |
| +semantic | 0.556 | 1 | [0.46, 0.65] | 0.67 | 1.00 | 0.58 | 0.33 | 0.17 | 0.60 | 1.00 | 702 | 2.1 | 0.00/0.00/0.00 |
| +correction | 0.657 | 1 | [0.56, 0.74] | 0.73 | 1.00 | 0.74 | 0.39 | 0.25 | 0.92 | 1.54 | 1137 | 3.1 | 0.00/0.00/0.00 |
| +clarify | 0.657 | 1 | [0.56, 0.74] | 0.73 | 1.00 | 0.74 | 0.39 | 0.25 | 0.92 | 1.54 | 1014 | 2.7 | 1.00/1.00/1.00 |

Kiểm định McNemar (cùng tập câu hỏi):

- +linking vs baseline: ΔEX = -0.083, McNemar p = 0.0225
- +fewshot vs baseline: ΔEX = +0.389, McNemar p = 0.0000
- +fewshot vs +linking: McNemar p = 0.0000
- +semantic vs baseline: ΔEX = +0.389, McNemar p = 0.0000
- +semantic vs +fewshot: McNemar p = 1.0000
- +correction vs baseline: ΔEX = +0.491, McNemar p = 0.0000
- +correction vs +semantic: McNemar p = 0.0010
- +clarify vs baseline: ΔEX = +0.491, McNemar p = 0.0000
- +clarify vs +correction: McNemar p = 1.0000

Nhóm unseen_family (không có ví dụ cùng họ trong kho few-shot; n nhỏ, đọc thận trọng):

- baseline: 7/12
- +linking: 0/12
- +fewshot: 2/12
- +semantic: 2/12
- +correction: 3/12
- +clarify: 3/12
- McNemar +semantic vs +fewshot (unseen): p = 1.0000
- McNemar +correction vs +semantic (unseen): p = 1.0000
- McNemar +correction vs +fewshot (unseen): p = 1.0000

Phân loại kết quả (seed đầu, câu trả lời được):

| Cấu hình | ok | wrong_result | schema_error | syntax_error | runtime_error | clarified |
|---|---|---|---|---|---|---|
| baseline | 18 | 19 | 52 | 2 | 17 | 0 |
| +linking | 9 | 22 | 70 | 0 | 7 | 0 |
| +fewshot | 60 | 11 | 23 | 0 | 14 | 0 |
| +semantic | 60 | 6 | 37 | 0 | 5 | 0 |
| +correction | 71 | 29 | 8 | 0 | 0 | 0 |
| +clarify | 71 | 29 | 8 | 0 | 0 | 0 |

## Model `ollama/qwen3:8b` - ngôn ngữ câu hỏi `en`

| Cấu hình | EX (mean±std) | #seed | 95% CI (seed đầu) | L1 | L2 | L3 | L4 | Unseen | Valid-SQL | Lần thử TB | Prompt tok/câu | Giây/câu | Clarif P/R/F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.333 | 1 | [0.25, 0.43] | 0.93 | 0.00 | 0.40 | 0.06 | 0.00 | 0.49 | 1.00 | 188 | 8.2 | 0.00/0.00/0.00 |
| +fewshot | 0.889 | 1 | [0.82, 0.94] | 1.00 | 1.00 | 1.00 | 0.64 | 0.00 | 0.98 | 1.00 | 547 | 3.6 | 0.00/0.00/0.00 |
| +semantic | 0.991 | 1 | [0.97, 1.00] | 1.00 | 1.00 | 1.00 | 0.97 | 0.92 | 1.00 | 1.00 | 691 | 3.3 | 0.00/0.00/0.00 |
| +clarify | 0.991 | 1 | [0.97, 1.00] | 1.00 | 1.00 | 1.00 | 0.97 | 0.92 | 1.00 | 1.00 | 602 | 2.8 | 1.00/1.00/1.00 |

Kiểm định McNemar (cùng tập câu hỏi):

- +fewshot vs baseline: ΔEX = +0.556, McNemar p = 0.0000
- +semantic vs baseline: ΔEX = +0.657, McNemar p = 0.0000
- +semantic vs +fewshot: McNemar p = 0.0010
- +clarify vs baseline: ΔEX = +0.657, McNemar p = 0.0000
- +clarify vs +semantic: McNemar p = 1.0000

Nhóm unseen_family (không có ví dụ cùng họ trong kho few-shot; n nhỏ, đọc thận trọng):

- baseline: 0/12
- +fewshot: 0/12
- +semantic: 11/12
- +clarify: 11/12
- McNemar +semantic vs +fewshot (unseen): p = 0.0010

Phân loại kết quả (seed đầu, câu trả lời được):

| Cấu hình | ok | wrong_result | schema_error | syntax_error | runtime_error | clarified |
|---|---|---|---|---|---|---|
| baseline | 36 | 17 | 49 | 1 | 5 | 0 |
| +fewshot | 96 | 10 | 2 | 0 | 0 | 0 |
| +semantic | 107 | 1 | 0 | 0 | 0 | 0 |
| +clarify | 107 | 1 | 0 | 0 | 0 | 0 |

## Model `ollama/qwen3:8b` - ngôn ngữ câu hỏi `vi`

| Cấu hình | EX (mean±std) | #seed | 95% CI (seed đầu) | L1 | L2 | L3 | L4 | Unseen | Valid-SQL | Lần thử TB | Prompt tok/câu | Giây/câu | Clarif P/R/F1 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 0.352±0.000 | 3 | [0.27, 0.44] | 0.93 | 0.00 | 0.42 | 0.09 | 0.25 | 0.51 | 1.00 | 191 | 2.6 | 0.00/0.00/0.00 |
| +linking | 0.296 | 1 | [0.21, 0.39] | 0.93 | 0.00 | 0.36 | 0.00 | 0.00 | 0.39 | 1.00 | 326 | 4.6 | 0.00/0.00/0.00 |
| +fewshot | 0.880±0.000 | 3 | [0.81, 0.94] | 1.00 | 1.00 | 0.98 | 0.64 | 0.25 | 0.95 | 1.00 | 566 | 3.8 | 0.00/0.00/0.00 |
| +semantic | 0.963±0.000 | 3 | [0.93, 0.99] | 1.00 | 1.00 | 0.98 | 0.91 | 0.83 | 0.97 | 1.00 | 710 | 3.7 | 0.00/0.00/0.00 |
| +correction | 0.981 | 1 | [0.95, 1.00] | 1.00 | 1.00 | 0.98 | 0.97 | 1.00 | 0.99 | 1.04 | 748 | 2.9 | 0.00/0.00/0.00 |
| +clarify | 0.981 | 1 | [0.95, 1.00] | 1.00 | 1.00 | 0.98 | 0.97 | 1.00 | 0.99 | 1.04 | 647 | 3.0 | 1.00/1.00/1.00 |
| semantic_only | 0.444 | 1 | [0.35, 0.54] | 0.53 | 0.70 | 0.38 | 0.42 | 0.50 | 0.62 | 1.00 | 336 | 4.4 | 0.00/0.00/0.00 |
| correction_only | 0.370 | 1 | [0.28, 0.46] | 0.93 | 0.00 | 0.46 | 0.09 | 0.25 | 0.59 | 1.93 | 507 | 10.0 | 0.00/0.00/0.00 |

Kiểm định McNemar (cùng tập câu hỏi):

- +linking vs baseline: ΔEX = -0.056, McNemar p = 0.0312
- +fewshot vs baseline: ΔEX = +0.528, McNemar p = 0.0000
- +fewshot vs +linking: McNemar p = 0.0000
- +semantic vs baseline: ΔEX = +0.611, McNemar p = 0.0000
- +semantic vs +fewshot: McNemar p = 0.0039
- +correction vs baseline: ΔEX = +0.630, McNemar p = 0.0000
- +correction vs +semantic: McNemar p = 0.5000
- +clarify vs baseline: ΔEX = +0.630, McNemar p = 0.0000
- +clarify vs +correction: McNemar p = 1.0000
- semantic_only vs baseline: ΔEX = +0.093, McNemar p = 0.1934
- correction_only vs baseline: ΔEX = +0.019, McNemar p = 0.5000

Nhóm unseen_family (không có ví dụ cùng họ trong kho few-shot; n nhỏ, đọc thận trọng):

- baseline: 3/12
- +linking: 0/12
- +fewshot: 3/12
- +semantic: 10/12
- +correction: 12/12
- +clarify: 12/12
- semantic_only: 6/12
- correction_only: 3/12
- McNemar +semantic vs +fewshot (unseen): p = 0.0156
- McNemar +correction vs +semantic (unseen): p = 0.5000
- McNemar +correction vs +fewshot (unseen): p = 0.0039

Phân loại kết quả (seed đầu, câu trả lời được):

| Cấu hình | ok | wrong_result | schema_error | syntax_error | runtime_error | clarified |
|---|---|---|---|---|---|---|
| baseline | 38 | 22 | 43 | 0 | 5 | 0 |
| +linking | 32 | 10 | 49 | 0 | 17 | 0 |
| +fewshot | 95 | 8 | 5 | 0 | 0 | 0 |
| +semantic | 104 | 2 | 2 | 0 | 0 | 0 |
| +correction | 106 | 2 | 0 | 0 | 0 | 0 |
| +clarify | 106 | 2 | 0 | 0 | 0 | 0 |
| semantic_only | 48 | 20 | 15 | 6 | 19 | 0 |
| correction_only | 40 | 29 | 38 | 0 | 1 | 0 |
