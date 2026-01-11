# 專案清理計畫 - Phos v0.4.1

**日期**: 2025-12-23  
**目標**: 移除過時檔案，保持專案清晰易維護

---

## 🎯 清理原則

1. **保留**: 活躍使用的檔案、文檔、測試
2. **歸檔**: 已完成任務的文檔、舊版本備份
3. **刪除**: 重複檔案、臨時檔案、過時腳本

---

## 📋 清理清單

### 類別 1: 備份檔案 (移至 archive/backups/)

**已在 archive/backups/**:
- [x] `Phos_0.3.0.py.backup_phase45`
- [x] `Phos_0.3.0.py.backup_pre_p0_2`
- [x] `film_models.py.backup_pre_medium_physics`
- [x] `film_models.py.backup_pre_p0_2`

**需要移動**:
- [ ] `scripts/diagnose_color_brightness.py.bak` → `archive/backups/`

**決策**: 保留在 archive/backups/（歷史參考）

---

### 類別 2: 已完成任務文檔 (移至 archive/completed_tasks/)

**已在 archive/completed_tasks/**:
- [x] `TASK-001-v020-verification/`
- [x] `TASK-002-physical-improvements/`
- [x] `P0-2_halation_refactor_plan.md`
- [x] `P1-2_iso_unification_plan.md`

**需要移動**:
- [ ] `tasks/TASK-003-medium-physics/` → 保留（仍在參考）
- [ ] `tasks/TASK-008-spectral-brightness-fix/` → 保留（v0.4.1 剛完成）

**決策**: TASK-003 和 TASK-008 保留在 `tasks/`（活躍參考）

---

### 類別 3: 過時文檔 (刪除或歸檔)

**可能過時**:
- [ ] `docs/BUGFIX_SUMMARY_20251220.md` → 檢查是否已整合到 CHANGELOG
- [ ] `docs/COLOR_FIX_TEST_GUIDE.md` → 檢查是否已整合到測試文檔
- [ ] `docs/DIAGNOSTIC_RESULTS_20251223.md` → 檢查是否為一次性診斷
- [ ] `docs/OPTIMIZATION_REPORT.md` → 檢查是否為一次性報告
- [ ] `docs/UI_INTEGRATION_SUMMARY.md` → 檢查版本

**決策**: 需要逐一檢查內容，決定保留/歸檔/刪除

---

### 類別 4: 測試腳本 (scripts/)

**診斷腳本（一次性使用）**:
- [ ] `scripts/diagnose_color_brightness.py` → TASK-008 專用，考慮歸檔
- [ ] `scripts/test_all_films_physical.py` → 檢查是否仍需要
- [ ] `scripts/test_mie_visual.py` → Mie 實驗專用
- [ ] `scripts/test_v041_brightness.py` → v0.4.1 測試專用

**生成腳本（可保留）**:
- [x] `scripts/generate_cie_data.py` ✅ 保留
- [x] `scripts/generate_film_spectra.py` ✅ 保留
- [x] `scripts/generate_mie_lookup.py` ✅ 保留
- [x] `scripts/generate_smits_basis.py` ✅ 保留

**分析腳本（可保留）**:
- [x] `scripts/compare_mie_versions.py` ✅ 保留
- [x] `scripts/profile_performance.py` ✅ 保留
- [x] `scripts/profile_real_workflow.py` ✅ 保留
- [x] `scripts/visualize_film_sensitivity.py` ✅ 保留
- [x] `scripts/visualize_iso_scaling.py` ✅ 保留

**決策**: 一次性測試腳本移至 `archive/scripts/`

---

### 類別 5: 測試輸出 (test_outputs/)

**內容**: 18 個 PNG 檔案 + 診斷報告

**決策選項**:
1. **保留**: 用於回歸測試（推薦）
2. **歸檔**: 移至 `archive/test_outputs/`
3. **刪除**: 可重新生成

**推薦**: 保留（檔案小，用於測試）

---

### 類別 6: 舊版主程式

**已刪除（Git 記錄中）**:
- [x] `Phos_0.3.0.py` → Git 已刪除

**當前主程式**:
- [x] `Phos.py` (v0.4.0, 需更新至 v0.4.1)

**決策**: 無需處理

---

### 類別 7: 數據檔案 (data/)

**Mie lookup tables**:
- [ ] `data/mie_lookup_table_v1.npz` → 舊版（v2 已取代）
- [x] `data/mie_lookup_table_v2.npz` ✅ 保留

**其他數據**:
- [x] `data/cie_1931_31points.npz` ✅ 保留
- [x] `data/film_spectral_sensitivity.npz` ✅ 保留
- [x] `data/smits_basis_spectra.npz` ✅ 保留

**決策**: v1 移至 `archive/data/`（歷史參考）

---

### 類別 8: 根目錄檔案

**Python 模組**:
- [x] `Phos.py` ✅ 保留（主程式）
- [x] `phos_core.py` ✅ 保留
- [x] `phos_batch.py` ✅ 保留
- [x] `film_models.py` ✅ 保留
- [x] `color_utils.py` ✅ 保留
- [ ] `phos_gpu.py` → 實驗性，考慮移至 `experiments/`

**配置與文檔**:
- [x] `README.md` ✅ 保留
- [x] `CHANGELOG.md` ✅ 保留
- [x] `LICENSE` ✅ 保留
- [x] `requirements.txt` ✅ 保留
- [x] `.gitignore` ✅ 保留
- [ ] `TEST_v0.4.1_DEPLOYMENT.md` → 移至 `tasks/TASK-008/`

---

## 🗂️ 建議新增的目錄結構

```
archive/
├── backups/          # 程式碼備份
├── completed_tasks/  # 已完成任務文檔
├── data/             # 舊版數據檔案 (NEW)
└── scripts/          # 一次性腳本 (NEW)

experiments/          # 實驗性功能 (NEW)
└── phos_gpu.py

tasks/                # 活躍任務
├── TASK-003-medium-physics/
├── TASK-008-spectral-brightness-fix/
└── PHYSICS_IMPROVEMENTS_ROADMAP.md

docs/                 # 活躍文檔
├── COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md
├── PHYSICAL_MODE_GUIDE.md
├── FILM_PROFILES_GUIDE.md
└── (移除過時報告)
```

---

## 📝 執行步驟

### Step 1: 創建新目錄
```bash
mkdir -p archive/data
mkdir -p archive/scripts
mkdir -p experiments
```

### Step 2: 移動備份檔案
```bash
mv scripts/diagnose_color_brightness.py.bak archive/backups/
```

### Step 3: 歸檔舊數據
```bash
mv data/mie_lookup_table_v1.npz archive/data/
```

### Step 4: 移動一次性腳本
```bash
mv scripts/diagnose_color_brightness.py archive/scripts/
mv scripts/test_all_films_physical.py archive/scripts/
mv scripts/test_mie_visual.py archive/scripts/
mv scripts/test_v041_brightness.py archive/scripts/
```

### Step 5: 移動實驗性代碼
```bash
mv phos_gpu.py experiments/
```

### Step 6: 整理文檔
```bash
# 移動 TEST_v0.4.1_DEPLOYMENT.md
mv TEST_v0.4.1_DEPLOYMENT.md tasks/TASK-008-spectral-brightness-fix/

# 檢查並決定過時文檔
# (需要人工檢查內容)
```

### Step 7: 更新 .gitignore
```bash
# 添加新的忽略規則（如果需要）
echo "archive/" >> .gitignore
echo "experiments/" >> .gitignore
```

---

## ✅ 預期成果

### 清理前
- 根目錄: 6 個 .py 檔案 + 多個文檔
- scripts/: 14 個腳本（混雜生成、測試、診斷）
- docs/: 12 個文檔（部分過時）
- data/: 5 個檔案（包含舊版本）

### 清理後
- 根目錄: 5 個核心 .py 檔案
- scripts/: 9 個活躍腳本（生成 + 分析）
- docs/: 3-4 個核心文檔
- data/: 4 個活躍數據檔案
- archive/: 完整歷史記錄
- experiments/: 實驗性功能隔離

---

## ⚠️ 風險評估

### 低風險操作
- ✅ 移動 .bak 檔案
- ✅ 歸檔 v1 數據
- ✅ 移動實驗性代碼

### 中風險操作
- ⚠️ 刪除過時文檔（需先檢查引用）
- ⚠️ 移動測試腳本（需確認無依賴）

### 高風險操作
- ❌ 刪除任何 .py 模組（禁止）
- ❌ 刪除測試檔案（禁止）

---

## 🎯 驗收標準

清理完成後應滿足：
- [ ] 根目錄檔案 < 10 個（排除隱藏檔案）
- [ ] scripts/ 僅包含活躍使用的腳本
- [ ] docs/ 僅包含核心文檔
- [ ] archive/ 包含完整歷史記錄
- [ ] 所有測試仍然通過
- [ ] Git status 乾淨（無誤刪）

---

**準備執行**: 等待用戶確認
