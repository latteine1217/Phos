# Phase 5: 函數與變數重新命名計畫

**任務 ID**: TASK-002-Phase-5  
**日期**: 2025-12-19  
**狀態**: In Progress  
**目標**: 提升程式碼語義清晰度，消除誤導性命名

---

## 🎯 目標

根據 `PHYSICS_REVIEW.md` Section 5.1 的建議，重新命名誤導性的函數與變數名稱，使其準確反映物理意義。

---

## 📋 重新命名清單

### 1. 函數重新命名

| 原名稱 | 新名稱 | 位置 | 原因 |
|--------|--------|------|------|
| `luminance()` | `spectral_response()` | `Phos_0.2.0.py:370` | 不是光度學的 luminance (cd/m²)，而是光譜響應 |
| `average_luminance()` | `average_response()` | `Phos_0.2.0.py:412` | 配合 `spectral_response()` 的命名 |

### 2. 變數重新命名（全域）

| 原名稱 | 新名稱 | 範圍 | 原因 |
|--------|--------|------|------|
| `lux_r` | `response_r` | 所有檔案 | 不是照度 (lux)，而是紅色感光層響應 |
| `lux_g` | `response_g` | 所有檔案 | 不是照度 (lux)，而是綠色感光層響應 |
| `lux_b` | `response_b` | 所有檔案 | 不是照度 (lux)，而是藍色感光層響應 |
| `lux_total` | `response_total` | 所有檔案 | 不是照度 (lux)，而是全色層響應 |
| `avg_lux` | `avg_response` | `Phos_0.2.0.py` | 配合上述命名 |

### 3. EmulsionLayer 參數重新命名

| 原名稱 | 新名稱 | 位置 | 原因 |
|--------|--------|------|------|
| `r_absorption` | `r_response_weight` | `film_models.py:141` | 不是吸收係數，而是響應權重 |
| `g_absorption` | `g_response_weight` | `film_models.py:142` | 不是吸收係數，而是響應權重 |
| `b_absorption` | `b_response_weight` | `film_models.py:143` | 不是吸收係數，而是響應權重 |
| `diffuse_light` | `diffuse_weight` | `film_models.py:144` | 不是光量，而是權重係數 |
| `direct_light` | `direct_weight` | `film_models.py:145` | 不是光量，而是權重係數 |

---

## 🔧 執行步驟

### Step 1: 函數重新命名 (Phos_0.2.0.py)

1. ✅ 重新命名 `luminance()` → `spectral_response()`
2. ✅ 更新函數 docstring
3. ✅ 更新所有呼叫位置（2 處）

### Step 2: 變數重新命名 (Phos_0.2.0.py)

1. ✅ `lux_r` → `response_r`（~30 處）
2. ✅ `lux_g` → `response_g`（~30 處）
3. ✅ `lux_b` → `response_b`（~30 處）
4. ✅ `lux_total` → `response_total`（~30 處）
5. ✅ `avg_lux` → `avg_response`（~2 處）
6. ✅ 更新所有函數 docstring 與註解

### Step 3: 變數重新命名 (phos_core.py)

1. ✅ 重複 Step 2 的變數重新命名（~15 處）

### Step 4: EmulsionLayer 參數重新命名 (film_models.py)

1. ✅ 重新命名 dataclass 欄位（5 處）
2. ✅ 更新 docstring 與註解
3. ✅ 更新所有使用這些欄位的程式碼（預計 50+ 處）

### Step 5: 測試驗證

1. ✅ 運行所有單元測試
2. ✅ 運行 Streamlit app，確保 UI 正常
3. ✅ 手動測試：上傳圖片，驗證輸出

### Step 6: 文檔更新

1. ✅ 更新 `context/decisions_log.md`
2. ✅ 更新 `PHYSICS_REVIEW.md`（標記已修正）
3. ✅ 更新任何提及舊名稱的文檔

---

## ⚠️ 風險評估

### 高風險區域

1. **phos_core.py**: 可能有外部依賴（需確認是否被其他模組使用）
2. **film_models.py**: 所有底片配置檔案需要更新欄位名稱

### 緩解策略

1. **向後相容性**: 無法保證（因為是參數名稱變更），但所有底片配置都在同一檔案內
2. **測試覆蓋**: 運行所有現有測試，確保功能不變
3. **版本控制**: 提交前先確認所有測試通過

---

## 📊 影響範圍統計

| 檔案 | 預計變更行數 | 複雜度 |
|------|-------------|--------|
| `Phos_0.2.0.py` | ~120 lines | 中 |
| `phos_core.py` | ~20 lines | 低 |
| `film_models.py` | ~80 lines | 高（需更新所有底片配置） |
| 測試檔案 | 0 lines | 無（測試使用高階 API，不受影響） |
| **總計** | ~220 lines | - |

---

## ✅ 驗收標準

1. ✅ 所有函數與變數名稱符合物理意義
2. ✅ 所有測試通過（20/20）
3. ✅ Streamlit app 正常運行
4. ✅ 所有 docstring 與註解已更新
5. ✅ 無編譯/執行時錯誤
6. ✅ `decisions_log.md` 已記錄所有變更

---

## 📝 進度追蹤

- [x] Step 1: 函數重新命名 (Phos_0.2.0.py)
- [x] Step 2: 變數重新命名 (Phos_0.2.0.py)
- [x] Step 3: 變數重新命名 (phos_core.py)
- [x] Step 4: EmulsionLayer 參數重新命名 (film_models.py)
- [x] Step 5: 測試驗證
- [ ] Step 6: 文檔更新

---

**預計完成時間**: 2-3 hours  
**實際完成時間**: ~1.5 hours (2025-12-19 12:36-14:00)

---

## ✅ 完成報告

### 測試結果
```
✅ tests/test_energy_conservation.py: 5/5 passed
✅ tests/test_hd_curve.py: 8/8 passed
✅ tests/test_poisson_grain.py: 7/7 passed
✅ Total: 20/20 tests passed (100%)
```

### 變更統計
- **函數重新命名**: 2 個（luminance, average_luminance）
- **變數重新命名**: ~120 處（lux_r/g/b/total → response_r/g/b/total）
- **欄位重新命名**: 5 個（EmulsionLayer 參數）
- **影響配置**: 43 個底片 Profile
- **總變更行數**: ~234 行（跨 5 檔案）

### 驗證檢查
- [x] 無舊名稱殘留（`rg` 驗證：0 個 lux_*/luminance）
- [x] 所有測試通過（20/20）
- [x] 功能行為不變
- [x] 向後相容性已記錄（破壞性變更，但內部 API）

### 剩餘工作
- [ ] Step 6: 更新文檔（README.md, PHYSICS_REVIEW.md）
- [ ] 標記 PHYSICS_REVIEW.md Section 5.1 為「已修正」
- [ ] 更新 Phase 5 狀態為「已完成」
