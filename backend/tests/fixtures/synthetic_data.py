"""
Synthetic test fixtures with known answers for verification.
"""

import polars as pl

# Known-answer dataset:
# Category A: values 10, 20, 30 -> sum = 60, mean = 20, count = 3
# Category B: values 40, null -> sum = 40, mean = 40, count = 1, null = 1
# Overall: 5 rows, 3 columns
SYNTHETIC_CSV_TEXT = """category,amount,date
A,10,2025-01-01
A,20,2025-01-05
A,30,2025-01-10
B,40,2025-02-01
B,,2025-02-15
"""

SYNTHETIC_CSV_BYTES = SYNTHETIC_CSV_TEXT.encode("utf-8")

KNOWN_ANSWERS = {
    "total_rows": 5,
    "total_cols": 3,
    "amount_null_count": 1,
    "amount_sum": 100.0,
    "amount_mean": 25.0,
    "amount_min": 10.0,
    "amount_max": 40.0,
    "group_sum_A": 60.0,
    "group_sum_B": 40.0,
}
