# TASK-013 Phase 7 設計：經驗公式移除計畫

**Date**: 2025-12-24 01:55  
**Phase**: Phase 7 - Issue #4 (經驗公式向後相容警告)  
**Priority**: P1 (High)  
**Estimated Time**: 1 hour  
**Status**: 🟡 In Progress

---

## 目標

移除 Phos.py 中已棄用的經驗公式分支（`wavelength_power=3.5`），簡化程式碼邏輯，消除 DeprecationWarning。

---

## 背景分析

### 當前狀況

**1. 所有 FilmProfile 已使用 Mie 查表**:
```
✅ Mie 查表: 22/22 (100%)
✅ 經驗公式: 0/22 (0%)
```

**2. 經驗公式分支狀況**:
- 位置: `Phos.py` Line 1020-1061 (42 lines)
- 觸發條件: `use_mie_lookup=False` 或 Mie 查表載入失敗
- 當前狀態: **死代碼** (無任何配置使用)
- DeprecationWarning: 觸發時會警告使用者

**3. 回退機制**:
```python
# Line 1015-1018
except FileNotFoundError as e:
    # 查表不存在，回退到經驗公式
    print(f"⚠️  Mie 查表載入失敗，回退到經驗公式: {e}")
    use_mie = False
```

---

## 決策：方案 A（完全移除）

### 理由

1. ✅ **無向後相容需求**
   - 0/22 配置使用經驗公式
   - 所有 _Mie 後綴版本已存在（保留向後相容）
   - WavelengthBloomParams 預設 `use_mie_lookup=True`

2. ✅ **簡化維護**
   - 移除 42 行死代碼
   - 消除雙分支邏輯
   - 減少測試負擔

3. ✅ **改善錯誤處理**
   - Mie 查表失敗 → 應直接報錯（不是無聲降級）
   - 經驗公式精度低（η(λ) 誤差 > 100%）
   - 避免無意識使用低精度結果

4. ✅ **Physics Score 無影響**
   - 所有配置已使用 Mie
   - 移除不影響任何實際行為

### vs 方案 B（保留 1 版本）

**方案 B 缺點**:
- 需維護死代碼至 v0.5.0（3-6 個月）
- 增加測試負擔（需測試經驗公式分支）
- 無實際使用者受益（0/22 配置使用）

**結論**: 方案 A 更優

---

## 實作計畫

### Step 1: 移除經驗公式分支 (0.3h)

**檔案**: `Phos.py`

**移除範圍**:
- Line 1020-1061: 經驗公式計算邏輯 (42 lines)
- Line 1015-1018: FileNotFoundError 回退機制 (4 lines)

**修改內容**:

**Before** (Line 991-1061):
```python
use_mie = wavelength_params.use_mie_lookup

if use_mie:
    # ===== Phase 5: 使用 Mie 散射查表 =====
    try:
        table = load_mie_lookup_table(wavelength_params.mie_lookup_path)
        # ... Mie 查表邏輯 ...
    except FileNotFoundError as e:
        # 查表不存在，回退到經驗公式
        print(f"⚠️  Mie 查表載入失敗，回退到經驗公式: {e}")
        use_mie = False

if not use_mie:
    # ===== Phase 1: 使用經驗公式（DEPRECATED, P1-1）=====
    # ⚠️ 警告：經驗公式 η(λ) ∝ λ^-3.5 缺乏理論依據
    # ...（42 行經驗公式計算）...
```

**After**:
```python
# ===== 使用 Mie 散射查表（唯一方法）=====
# 所有 FilmProfile 已使用 Mie 查表（v0.4.1+）
# 經驗公式已移除（TASK-013 Phase 7, 2025-12-24）

table = load_mie_lookup_table(wavelength_params.mie_lookup_path)
iso = wavelength_params.iso_value

# 查表獲取各波長參數
sigma_r, kappa_r, rho_r, eta_r_raw = lookup_mie_params(
    wavelength_params.lambda_r, iso, table
)
sigma_g, kappa_g, rho_g, eta_g_raw = lookup_mie_params(
    wavelength_params.lambda_g, iso, table
)
sigma_b, kappa_b, rho_b, eta_b_raw = lookup_mie_params(
    wavelength_params.lambda_b, iso, table
)

# 歸一化能量權重（綠光為基準）
eta_r = eta_r_raw / eta_g_raw * bloom_params.scattering_ratio
eta_g = bloom_params.scattering_ratio
eta_b = eta_b_raw / eta_g_raw * bloom_params.scattering_ratio
```

**變更統計**:
- 移除: 46 lines (經驗公式 42 + 回退 4)
- 新增: 21 lines (簡化 Mie 邏輯)
- 淨減少: 25 lines

---

### Step 2: 移除 WavelengthBloomParams 中的經驗公式參數 (0.2h)

**檔案**: `film_models.py`

**移除參數**:
```python
@dataclass
class WavelengthBloomParams:
    enabled: bool = True
    
    # ❌ 移除：經驗公式參數（已無使用）
    # wavelength_power: float = 3.5
    # radius_power: float = 0.8
    
    # ✅ 保留：Mie 查表參數
    use_mie_lookup: bool = True
    mie_lookup_path: str = "data/mie_lookup_table_v3.npz"
    iso_value: int = 400
    # ... 其他參數 ...
```

**影響**:
- `wavelength_power`: Line ~410 (註解已標註 deprecated)
- `radius_power`: Line ~411 (註解已標註 deprecated)

**處理方式**:
- 選項 A: 完全移除（破壞性變更，但無實際影響）
- 選項 B: 保留但設為 `None`，觸發錯誤
- **推薦**: 選項 A（已無配置使用）

---

### Step 3: 更新文檔與註解 (0.2h)

**1. 更新 `film_models.py` 註解**:
```python
# Line ~838 (create_default_wavelength_bloom_params)
# Before:
# P1-1: 預設啟用 Mie 查表（移除顯式 use_mie_lookup=False）

# After:
# Mie 查表為唯一實作（經驗公式已移除, TASK-013 Phase 7）
```

**2. 更新 `docs/VISUAL_IMPROVEMENTS_V041.md`**:
添加「技術變更」段落：
```markdown
### v0.4.2 技術變更（預計）

**移除經驗公式分支** (TASK-013 Phase 7):
- 所有 FilmProfile 已使用 Mie 散射查表
- 經驗公式（λ^-3.5）精度不足，已完全移除
- 簡化程式碼 25 行，消除 DeprecationWarning
```

**3. 更新 `CHANGELOG.md`**:
```markdown
## [v0.4.2] - TBD

### Removed
- **Wavelength Bloom**: 移除經驗公式分支（λ^-3.5）
  - 所有 FilmProfile 已使用 Mie 查表（更精確）
  - 簡化程式碼邏輯，移除死代碼
  - 無向後相容影響（0/22 配置使用經驗公式）
```

---

### Step 4: 測試驗證 (0.3h)

**1. 單元測試**:
```bash
# 確認所有測試通過（經驗公式移除不影響）
pytest tests/test_wavelength_bloom.py -v
pytest tests/test_mie_*.py -v
pytest tests/ --ignore=tests/debug/ -v
```

**預期結果**:
- ✅ 所有測試通過（無經驗公式相關測試）
- ✅ 無 DeprecationWarning

**2. 整合測試**:
```python
# 測試 Mie 查表失敗情況
# scripts/test_phase7_mie_fallback.py

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from film_models import create_film_profiles
import Phos

# 測試 1: 正常載入
films = create_film_profiles()
portra = films['Portra400_MediumPhysics_Mie']
print("✅ Portra400+Mie 載入成功")

# 測試 2: 錯誤查表路徑（應報錯，不回退）
portra_bad = films['Portra400']
portra_bad.wavelength_bloom_params.mie_lookup_path = "nonexistent.npz"

try:
    # 應該拋出 FileNotFoundError，不回退到經驗公式
    bloom_r, bloom_g, bloom_b = Phos.apply_wavelength_dependent_bloom(...)
    print("❌ 應該拋出錯誤，但沒有")
except FileNotFoundError as e:
    print(f"✅ 正確拋出錯誤: {e}")
```

**3. 效能回歸測試**:
```bash
# 確認效能無退化
python scripts/benchmark_performance.py

# 對比 Phase 6 基準
python -c "
import json
with open('test_outputs/performance_baseline_v041.json', 'r') as f:
    data = json.load(f)
# 檢查 Physics+Mie 配置效能
"
```

---

## 風險評估

### 風險 1: 破壞向後相容性

**可能性**: LOW  
**影響**: MEDIUM

**緩解措施**:
- ✅ 所有 22 個配置已使用 Mie
- ✅ WavelengthBloomParams 預設 `use_mie_lookup=True`
- ✅ 舊配置（無 _Mie 後綴）已存在，提供升級路徑

**驗證**:
```python
# 測試舊配置仍可載入
films = create_film_profiles()
old_portra = films['Portra400']  # 非 _Mie 版本
assert old_portra.wavelength_bloom_params.use_mie_lookup == True
```

### 風險 2: Mie 查表載入失敗時無回退

**可能性**: LOW  
**影響**: HIGH (程式崩潰)

**緩解措施**:
- ✅ **這是預期行為**（顯式失敗優於無聲降級）
- ✅ 錯誤訊息清晰，指示修復方式
- ✅ Mie 查表檔案應存在於專案中（`data/mie_lookup_table_v3.npz`）

**改善錯誤訊息**:
```python
# Before
except FileNotFoundError as e:
    print(f"⚠️  Mie 查表載入失敗，回退到經驗公式: {e}")

# After
except FileNotFoundError as e:
    raise FileNotFoundError(
        f"Mie 散射查表載入失敗: {wavelength_params.mie_lookup_path}\n"
        f"原因: {e}\n"
        f"解決方式:\n"
        f"  1. 確認檔案存在: data/mie_lookup_table_v3.npz\n"
        f"  2. 或執行: python scripts/generate_mie_lookup.py\n"
        f"註: 經驗公式已移除（v0.4.2+），Mie 查表為唯一方法"
    ) from e
```

### 風險 3: 測試覆蓋不足

**可能性**: LOW  
**影響**: LOW

**緩解措施**:
- ✅ 已有 `test_wavelength_bloom.py`（Mie 查表測試）
- ✅ 已有 `test_mie_*.py`（Mie 理論測試）
- ✅ Phase 7 新增 Mie 查表失敗測試

---

## 驗收標準

### 功能驗收

- ✅ 經驗公式分支完全移除（~46 lines）
- ✅ 所有 FilmProfile 正常載入（22/22）
- ✅ Mie 查表失敗時拋出清晰錯誤（不回退）
- ✅ 無 DeprecationWarning

### 測試驗收

- ✅ pytest: 240+ passed, 29 failed (與 Phase 6 相同)
- ✅ 核心功能測試: 100% passed
- ✅ Mie 查表測試: 100% passed

### 文檔驗收

- ✅ 更新 `film_models.py` 註解
- ✅ 更新 `docs/VISUAL_IMPROVEMENTS_V041.md`
- ✅ 更新 `CHANGELOG.md`

### 效能驗收

- ✅ 效能無退化（vs Phase 6 基準）
- ✅ 程式碼簡化 ~25 lines

---

## 實作順序

1. **Step 1** (0.3h): 移除 Phos.py 經驗公式分支
2. **Step 2** (0.2h): 移除 film_models.py 經驗公式參數（可選）
3. **Step 3** (0.2h): 更新文檔與註解
4. **Step 4** (0.3h): 測試驗證

**總計**: 1.0 hours

---

## 下一步

Phase 7 完成後 → **Phase 8**: ColorChecker 測試重構 (Issue #6, 2-3h)

---

**設計完成時間**: 2025-12-24 02:00  
**狀態**: 🟢 Ready for Implementation
