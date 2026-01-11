# TASK-011 Phase 1: 物理模型設計

## 執行時間
**開始**: 2025-12-24 06:50  
**完成**: 2025-12-24 07:10  
**耗時**: 20 min

---

## 核心發現 🎯

**重大發現**: 當前代碼（film_models.py Line 131-238）**已經實現了標準化結構**！

P0-2 (TASK-003) 已完成：
- ✅ 使用單程透過率：`emulsion_transmittance_*`, `base_transmittance`, `ah_layer_transmittance_*`
- ✅ 正確的雙程公式：`effective_halation_*` 計算 `[T_e·T_b·T_AH]²·R_bp`
- ✅ 向後相容機制：`__post_init__` 自動轉換舊參數

**結論**: 無需大規模重構，僅需文檔化與測試補強。

---

## Physicist 審查總結

**審查報告**: `physicist_review.md` (194 lines)

### 關鍵發現

1. **命名與結構**:
   - ✅ 新參數已標準化（單程透過率）
   - ⚠️ 舊參數仍有混亂（transmittance_r/g/b, ah_absorption）
   - ⚠️ 文檔化不足（缺少單位註解、物理意義、合理範圍）

2. **物理一致性**:
   - ✅ 雙程公式正確：f_h(λ) = [T_e·T_b·T_AH]²·R_bp
   - ✅ Beer-Lambert 應用正確：T(λ) = exp(-α·L)
   - ⚠️ 舊參數的線性近似不嚴謹（T_AH ≈ 1-α, 僅在 α<<1 成立）

3. **測試覆蓋**:
   - ✅ 基礎測試存在 (test_halation.py, 8/10 passed)
   - ⚠️ 缺少雙程路徑驗證測試
   - ⚠️ CineStill 測試被跳過（配置不存在）
   - ❌ test_p0_2_halation_beer_lambert.py 文件不存在

4. **參數校準**:
   - ⚠️ 缺少 CineStill 800T 配置（無 AH 層，強紅暈）
   - ⚠️ 現有配置未驗證物理特徵（需實測 f_h 值）

---

## 真實案例計算（Physicist 提供）

### 公用參數
- T_b = 0.98 (片基)
- R_bp = 0.30 (背板反射率)

### CineStill 800T（無 AH 層）

**參數建議**:
```python
emulsion_transmittance_r = 0.92
emulsion_transmittance_g = 0.87
emulsion_transmittance_b = 0.78
ah_layer_transmittance_r = 1.0  # 無 AH 層
ah_layer_transmittance_g = 1.0
ah_layer_transmittance_b = 1.0
backplate_reflectance = 0.30
```

**計算結果**:
```python
f_h,red   = (0.92 · 0.98 · 1.0)² · 0.30 ≈ 0.244 → 24.4% 強紅暈 ✅
f_h,green = (0.87 · 0.98 · 1.0)² · 0.30 ≈ 0.218 → 21.8%
f_h,blue  = (0.78 · 0.98 · 1.0)² · 0.30 ≈ 0.175 → 17.5%
```

**物理特徵**: 紅光 Halation 最強（霓虹燈紅暈效果）

---

### Kodak Portra 400（有 AH 層）

**參數建議**:
```python
emulsion_transmittance_r = 0.92
emulsion_transmittance_g = 0.87
emulsion_transmittance_b = 0.78
ah_layer_transmittance_r = 0.30  # 有 AH 層，強吸收
ah_layer_transmittance_g = 0.10
ah_layer_transmittance_b = 0.05
backplate_reflectance = 0.30
```

**計算結果**:
```python
f_h,red   = (0.92 · 0.98 · 0.30)² · 0.30 ≈ 0.022 → 2.2% 弱紅暈 ✅
f_h,green = (0.87 · 0.98 · 0.10)² · 0.30 ≈ 0.0022 → 0.22%
f_h,blue  = (0.78 · 0.98 · 0.05)² · 0.30 ≈ 4.3e-4 → 0.043%
```

**物理特徵**: Halation 幾乎不可見，符合 Portra 特性

---

### 對比驗證

**紅光 Halation 比例**:
```
f_h,red (CineStill) / f_h,red (Portra) = 0.244 / 0.022 ≈ 11× 差異 ✅
```

**結論**: AH 層使 Halation 減少 11 倍，符合物理預期。

---

## 標準化設計

### 參數命名（已實現）

| 參數名 | 物理意義 | 單位 | 合理範圍 |
|--------|---------|------|---------|
| `emulsion_transmittance_r/g/b` | 乳劑層單程透過率 T_e(λ) | 無量綱 | 0.60-0.98 |
| `base_transmittance` | 片基單程透過率 T_b | 無量綱 | 0.95-0.995 |
| `ah_layer_transmittance_r/g/b` | AH 層單程透過率 T_AH(λ) | 無量綱 | 0.02-0.35 (有 AH)<br>1.0 (無 AH) |
| `backplate_reflectance` | 背板反射率 R_bp | 無量綱 | 0.05-0.50 |
| `energy_fraction` | 畫面級能量縮放 | 無量綱 | 0.02-0.10 |

### 計算公式（已實現）

```python
# 單程聚合透過率
T_single(λ) = T_e(λ) · T_b · T_AH(λ)

# 雙程 Halation 能量分數
f_h(λ) = [T_single(λ)]² · R_bp

# 若使用吸收係數（進階）
T(λ) = exp(-α(λ) · L)
```

### 向後相容（已實現）

```python
# 舊參數自動轉換
transmittance_r → emulsion_transmittance_r = sqrt(transmittance_r / base_transmittance²)
ah_absorption → ah_layer_transmittance_* = 1 - ah_absorption  # 線性近似
```

---

## 修改任務範圍

### 原計畫
- Phase 2: 代碼重構（4 hours）
- Phase 3: 物理驗證測試（3 hours）
- Phase 4: 參數校準（4 hours）
- Phase 5: 文檔更新（2 hours）

### 新計畫（簡化）

#### Phase 2: 文檔強化（1 hour） ✅ COMPLETED
- ✅ 新增單位註解（無量綱、cm⁻¹）
- ✅ 新增物理意義說明
- ✅ 新增合理範圍註解
- ✅ 增強 docstrings（effective_halation_* 屬性）
- ✅ 新增 CineStill vs Portra 典型值範例

**修改文件**: `film_models.py` (Line 131-270)

#### Phase 3: 測試補強（2-3 hours）
- [ ] 修復 test_p0_2_halation_beer_lambert.py (或創建新測試)
- [ ] 新增雙程路徑驗證測試
- [ ] 新增 CineStill vs Portra 對比測試
- [ ] 啟用被跳過的 CineStill 測試
- [ ] 能量守恆驗證（單通道測試）

#### Phase 4: 參數配置（1 hour）
- [ ] 新增 CineStill 800T 膠片配置
- [ ] 驗證 Portra 400 配置（調整至符合物理特徵）
- [ ] 驗證 f_h 值符合預期範圍

#### Phase 5: 決策記錄（30 min）
- [ ] 更新 decisions_log.md (Decision #029)
- [ ] 更新 PHYSICS_IMPROVEMENTS_ROADMAP.md (P1-4 狀態)
- [ ] 創建 completion_report.md

---

## Physics Gate 決議

**狀態**: ✅ **PASSED**

**Physicist 批准**:
- ✅ 雙程公式物理正確
- ✅ 參數命名標準化
- ✅ Beer-Lambert 應用一致
- ✅ 能量守恆邏輯清晰

**建議**:
- 強化文檔（單位、範圍）→ ✅ Phase 2 已完成
- 補強測試（雙程路徑、膠片對比）→ Phase 3
- 校準參數（CineStill, Portra）→ Phase 4

**下一步**: 繼續 Phase 3 (測試補強)

---

## 預估調整

**原預估**: 1-2 天 (16 hours)  
**新預估**: 4-5 hours  
**節省時間**: 11 hours（因無需重構）

**時間分配**:
- ✅ Phase 1: 20 min
- ✅ Phase 2: 30 min
- ⏳ Phase 3: 2-3 hours
- ⏳ Phase 4: 1 hour
- ⏳ Phase 5: 30 min

---

## 決策依據

**為何不需重構？**

1. **P0-2 (TASK-003) 已完成結構改造**:
   - 2025-12 月實作，引入單程透過率結構
   - 雙程公式在 Line 219-238 正確實現
   - 向後相容機制完善

2. **當前問題是文檔與測試，非設計**:
   - 參數物理意義明確，僅需註解補充
   - 測試覆蓋不足，非公式錯誤

3. **Physicist 批准當前設計**:
   - 物理模型正確
   - 命名一致
   - 計算邏輯無誤

**結論**: 任務降級為「文檔化 + 測試補強」，Physics Score 預期增益從 +0.2 調整為 +0.1。

---

## 下一步行動

1. ✅ 完成 Phase 2 文檔強化
2. ⏳ Phase 3: 測試補強
   - 創建/修復 Beer-Lambert 驗證測試
   - 新增 CineStill vs Portra 對比測試
   - 啟用被跳過的測試案例
3. ⏳ Phase 4: 新增 CineStill 800T 配置
4. ⏳ Phase 5: 文檔更新與完成報告

---

**Phase 1 完成**: 2025-12-24 07:10  
**Status**: ✅ Physics Gate PASSED  
**Next**: Phase 3 測試補強
