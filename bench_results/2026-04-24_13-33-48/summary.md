# OCR Benchmark Summary — 2026-04-24_13-33-48

## TABLE II: OCR provider comparison

```
Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.73 |    7.03 |       No |    27 |      0
vision                           |       0.26 |    0.39 |       No |    27 |     27
tesseract                        |       2.26 |   19.35 |      Yes |    27 |      0
cascade                          |       2.73 |    4.26 |  Partial |    27 |      0
```

## Per-PDF breakdown


### handwritten_assignment.pdf

Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.21 |    6.67 |       No |     8 |      0
vision                           |       0.22 |    0.23 |       No |     8 |      8
tesseract                        |       0.86 |    0.91 |      Yes |     8 |      0
cascade                          |       1.77 |    1.86 |  Partial |     8 |      0

### minaz.pdf

Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.75 |    2.83 |       No |     6 |      0
vision                           |       0.38 |    0.40 |       No |     6 |      6
tesseract                        |      12.54 |   17.81 |      Yes |     6 |      0
cascade                          |       2.83 |    2.93 |  Partial |     6 |      0

### satya.pdf

Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.79 |    2.79 |       No |     3 |      0
vision                           |       0.28 |    0.28 |       No |     3 |      3
tesseract                        |       3.10 |    3.10 |      Yes |     3 |      0
cascade                          |       3.45 |    3.45 |  Partial |     3 |      0

### saksham.pdf

Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.36 |    3.03 |       No |     5 |      0
vision                           |       0.25 |    0.26 |       No |     5 |      5
tesseract                        |       2.04 |    2.13 |      Yes |     5 |      0
cascade                          |       3.64 |    3.95 |  Partial |     5 |      0

### zeeya.pdf

Provider                         | Latency(s) |  p95(s) |  Offline |     N | Errors
-----------------------------------------------------------------------------------
mistral                          |       2.77 |    4.22 |       No |     5 |      0
vision                           |       0.35 |    0.38 |       No |     5 |      5
tesseract                        |      12.15 |   19.35 |      Yes |     5 |      0
cascade                          |       3.18 |    3.20 |  Partial |     5 |      0

*Generated: 2026-04-24_13-33-48*