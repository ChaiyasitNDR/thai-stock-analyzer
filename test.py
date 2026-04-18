import pandas as pd
import numpy as np

# ทดสอบ Profit Factor และ Expectancy โดยตรง

def test_profit_factor(returns: list) -> dict:
    s = pd.Series(returns)
    pos = s[s > 0]
    neg = s[s < 0]
    gross_profit = pos.sum()
    gross_loss   = abs(neg.sum())
    if gross_loss == 0 and gross_profit > 0:
        pf = 9999.0
    elif gross_profit == 0 and gross_loss > 0:
        pf = 0.0
    elif gross_profit == 0 and gross_loss == 0:
        pf = None
    else:
        pf = round(gross_profit / gross_loss, 2)

    hit_mask = s > 0
    p_win    = hit_mask.sum() / len(s)
    avg_hit  = s[hit_mask].mean() if hit_mask.sum() > 0 else 0
    avg_miss = s[~hit_mask].mean() if (~hit_mask).sum() > 0 else 0
    exp      = round(p_win * avg_hit + (1 - p_win) * avg_miss, 3)
    return {"pf": pf, "expectancy": exp}

# Test 1: ปกติ — กำไรมากกว่าขาดทุน
r1 = [2.0, 3.0, -1.0, -0.5, 1.5]
t1 = test_profit_factor(r1)
# gross_profit=6.5, gross_loss=1.5 → PF=4.33 (>1 ✅)
# expectancy = 0.6*(2.17) + 0.4*(-0.75) = 1.0 (บวก ✅)
print(f"Test 1: PF={t1['pf']} (expect ~4.33), Exp={t1['expectancy']} (expect ~1.0)")

# Test 2: ไม่มี loss เลย → PF = ∞
r2 = [1.0, 2.0, 3.0]
t2 = test_profit_factor(r2)
# gross_loss=0 → PF=9999 (∞ ✅)
print(f"Test 2: PF={t2['pf']} (expect 9999=∞)")

# Test 3: ไม่มี profit เลย → PF = 0
r3 = [-1.0, -2.0, -0.5]
t3 = test_profit_factor(r3)
# gross_profit=0 → PF=0 ✅, expectancy ลบ ✅
print(f"Test 3: PF={t3['pf']} (expect 0), Exp={t3['expectancy']} (expect negative)")