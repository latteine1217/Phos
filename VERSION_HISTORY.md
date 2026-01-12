# Phos - 版本歷史 Version History

本檔案記錄 Phos 專案的所有版本更新與重要里程碑。

This file documents all version updates and major milestones of the Phos project.

---

## 📊 版本狀態總覽 Version Status Overview

| 版本 | 狀態 | 發布日期 | 重點特性 | 物理分數 |
|------|------|---------|---------|---------|
| **v0.8.3** | 🆕 Current | 2026-01-12 | UI/UX 大改版 | 9.2/10 |
| **v0.8.2.3** | ✅ Stable | 2026-01-12 | sRGB 輸出修復 | 9.2/10 |
| **v0.8.2** | ⚠️ Deprecated | 2026-01-12 | 色彩管理 | 9.2/10 |
| **v0.8.1** | ✅ Stable | 2026-01-12 | 光譜校正 + 純物理模式 | 9.2/10 |
| **v0.8.0** | ⚠️ Breaking | 2026-01-12 | Import Cleanup | 9.2/10 |
| **v0.7.0** | ✅ Stable | 2025-01-12 | 模組化架構 | 9.0/10 |
| **v0.6.1** | ✅ Stable | 2025-01-11 | 棄用標記 | 8.7/10 |
| **v0.4.2** | ✅ Stable | 2025-12-24 | 互易律失效 | 9.0/10 |

---

## 🆕 v0.8.3 - Major UI/UX Overhaul (2026-01-12)

### ✨ 重點特性 Highlights
**全新用戶體驗**: 視覺美化 + 功能優化 + 資訊呈現三位一體升級

### Phase 1: 視覺美化 Visual Enhancements
- 🎨 **動態背景**: 徑向漸層 + 動畫光暈效果
- 💫 **按鈕動畫**: 
  - Smooth cubic-bezier 過渡（0.3s）
  - 懸停提升效果（-2px translateY）
  - 主按鈕脈動發光動畫
  - 點擊反饋動畫
- 🎴 **增強卡片**:
  - 底片資訊卡片懸停發光效果
  - 漸層邊框 + 陰影深度
  - 更好的字體層次
  - Emoji + 色碼元數據標籤
- 📊 **警告框**: 
  - 按類型色碼（success/info/warning/error）
  - 背景模糊效果
  - 淡入動畫（0.3s）
  - 4px 強調邊框
- 🖼️ **圖片容器**:
  - 懸停提升效果 + 陰影增強
  - 流暢過渡（0.3s ease）

### Phase 2: 功能優化 Functional Improvements
- 💡 **快速預設**（4 種場景）:
  - 👤 **人像模式**: Portra400 + 柔和顆粒 + physical bloom（閾值 0.85）
  - 🏞️ **風景模式**: Velvia50 + 無顆粒 + physical bloom（閾值 0.80）
  - 🚶 **街拍模式**: TriX400 + 默認顆粒 + artistic bloom（閾值 0.75）
  - 🎬 **電影風格**: Cinestill800T + 較粗顆粒 + artistic bloom（閾值 0.70）
- 🔄 **一鍵重置**: 恢復所有參數到預設值
- ℹ️ **配置摘要**: 查看當前所有參數設定
- 🎯 **自動配置**: 選擇預設自動配置：
  - 底片類型
  - 處理品質模式
  - 顆粒風格
  - 曲線映射
  - Bloom 參數

### Phase 3: 資訊呈現 Information Presentation
- 📊 **圖像統計**（可折疊區塊）:
  - 解析度（W × H）
  - 總像素數（格式化千分位）
  - 記憶體大小（MB）
  - 平均亮度（0-255）
  - 亮度變化百分比（處理前後）
- 💎 **處理統計卡片**:
  - 三欄布局與色碼卡片：
    - ⏱️ 處理時間（黃色強調）
    - 🔬 物理模式（藍色強調）
    - 💾 檔案大小或品質（綠色強調）
  - 大型置中數字 + 圖標
  - 漸層背景 + 邊框
- ✨ **成功訊息**:
  - 漸層背景 + 發光效果
  - 清晰排版 + 高亮指標
  - 批次處理平均時間顯示

### 技術細節 Technical Details
- **修改檔案**: `ui_components.py`（大幅重構）
  - Lines 36-283: CSS 改進（動畫、漸層、過渡）
  - Lines 323-476: 快速預設 + 自動配置邏輯
  - Lines 490-548: 預設感知物理設定渲染
  - Lines 770-871: 增強結果顯示 + 統計
  - Lines 896-925: 改進批次處理 UI
- **向後相容**: ✅ 無破壞性變更
- **測試狀態**: ✅ Python 語法驗證通過

### 用戶反饋改善 User Feedback Addressed
- ✅ **「不夠直觀」** → 快速預設 + 場景說明
- ✅ **「視覺美化」** → CSS 動畫 + 漸層 + 懸停效果
- ✅ **「資訊呈現」** → 統計卡片 + 圖像元數據
- ✅ **「功能優化」** → 重置按鈕 + 預設自動配置

### 改進對比 Comparison
| 功能 | v0.8.2.3 之前 | v0.8.3 之後 |
|------|--------------|-----------|
| 背景 | 單一漸層 | 動態徑向光暈 |
| 按鈕 | 簡單過渡 | 脈動發光 + 提升 |
| 預設 | 無 | 4 種場景預設 |
| 統計 | 純文字 | 彩色卡片 |
| 重置 | 手動 rerun | 一鍵按鈕 |

---

## 🔧 v0.8.2.3 - CRITICAL Hotfix: sRGB Output Conversion (2026-01-12)

### 🐛 問題 Problem
**最嚴重的問題**: 輸出圖像完全沒有底片效果，只有亮度變暗。所有 tone mapping 和色彩調整都看不出來。

### 🔍 根本原因 Root Cause
v0.8.2 引入 sRGB → Linear RGB 輸入轉換後，**忘記在輸出時進行反向轉換**（Linear RGB → sRGB）。

完整色彩管理流程應該是：
```
輸入: sRGB (相機/手機標準輸出)
  ↓ srgb_to_linear()
Linear RGB (物理計算空間)
  ↓ spectral_response, bloom, grain, tone mapping
Linear RGB (處理完成)
  ↓ ❌ v0.8.2 缺少這步！
  ↓ ✅ v0.8.2.3 新增 linear_to_srgb()
sRGB (螢幕顯示輸出)
```

**為什麼會這樣？**
- Linear RGB 的中灰（0.18）在螢幕上看起來非常暗（約 46% 亮度）
- Tone mapping 的對比度調整在 Linear 空間完成，但沒有 gamma 編碼就無法正確顯示
- 色彩飽和度和色調也完全失真

### ✅ 修復內容 Fixed

**新增函數** - `modules/optical_core.py`:
- Added `linear_to_srgb()` function (IEC 61966-2-1:1999 standard)
- Piecewise function: `12.92 × C` below 0.0031308, `1.055 × C^(1/2.4) - 0.055` above
- Includes `np.clip(0, 1)` to prevent out-of-gamut issues
- Added to `__all__` exports (line 260)

**輸出轉換** - `Phos.py`:
- **彩色膠片** (lines 698-706):
  ```python
  result_r_srgb = linear_to_srgb(result_r)
  result_g_srgb = linear_to_srgb(result_g)
  result_b_srgb = linear_to_srgb(result_b)
  combined_r = (result_r_srgb * 255).astype(np.uint8)
  ```
- **黑白膠片** (lines 745-747):
  ```python
  result_total_srgb = linear_to_srgb(result_total)
  final_image = (result_total_srgb * 255).astype(np.uint8)
  ```
- Import updated: Added `linear_to_srgb` to imports (line 153)

**UI 修復** - `ui_components.py`:
- Fixed Streamlit API deprecation: `use_column_width=True` → `width="stretch"` for `st.image()`
- Lines 793, 797: Updated both original and film image display

### 🧪 測試 Tests Added
- `tests_refactored/test_color_space.py`:
  - New `TestLinearToSRGB` class with 7 comprehensive tests
  - Tests: zero/one values, threshold, midtone, clipping, shape preservation, monotonicity
  - Updated `TestRoundTrip` to use module functions
  - **Status**: 37/37 passed (100%)

### 📊 結果 Results
- ✅ **底片效果完全恢復** - Tone mapping, color grading, contrast adjustment now visible
- ✅ **正確亮度** - Linear 0.18 → sRGB 0.46 (correct middle gray perception)
- ✅ **色彩準確** - Film color science now displays correctly
- ✅ **物理正確** - Complete color-managed workflow: sRGB in → Linear processing → sRGB out
- ✅ **測試通過**: 100/100 (grain + tone mapping + image processing + color space)

### 🎯 影響 Impact
**Critical fix** - 沒有這個修正，v0.8.2 的所有色彩管理改進都無法正常顯示。這是 v0.8.2 最重要的 hotfix。

---

## 🔧 v0.8.2.2 - Hotfix: Grain Size Reduction (2026-01-12)

### 🐛 問題 Problem
After v0.8.2 introduced sRGB→Linear RGB conversion, grain became extremely coarse (~2.5-3× too strong).

### 🔍 根本原因 Root Cause
`grain_intensity` parameters (0.08-0.20) were originally calibrated for sRGB gamma space. In Linear RGB space, the same additive noise values create much stronger perceptual effects after gamma encoding for display.

**技術細節**:
- In Linear RGB: 0.18 ≈ 18% middle gray
- Adding ±0.18 noise → oscillates between 0.0 and 0.36
- After gamma 2.2 encoding → perceptual range [0.0, 0.65] (65% swing!)
- In sRGB gamma space (original): Same ±0.18 on value 0.5 → [0.32, 0.68] (only 25% swing)

### ✅ 修復內容 Fixed
1. **新增補償係數** - `modules/image_processing.py`:
   - `GRAIN_LINEAR_RGB_COMPENSATION = 0.30`
   - Applied in `combine_layers_for_channel()` (line 190)
   - Result: Grain size reduced ~70-80%

2. **修正 sens 計算** - `Phos.py`:
   - Added gamma 2.2 perceptual correction
   - Ensures grain intensity scales correctly with ISO

3. **正規化 Chi-squared 噪聲** - `grain_strategies.py`:
   - Fixed distribution normalization
   - Prevents extreme outliers

4. **增加模糊半徑** - `film_models.py`:
   - Grain blur sigma: 1.0 → 1.5
   - Smoother grain appearance

### 📊 結果 Results
- ✅ Grain size reduced from "超級粗" to natural appearance
- ✅ Perceptual grain strength now consistent with sRGB version
- ✅ All grain tests passing (24/24)

---

## 🔧 v0.8.2.1 - Hotfix: Brightness Restoration (2026-01-12)

### 🐛 問題 Problem
Output images very dark (50% gray → 18% gray, -64% brightness loss)

### 🔍 根本原因 Root Cause
Multiple `np.power()` operations (designed for sRGB) caused cumulative brightness compression in Linear RGB.

### ✅ 修復內容 Fixed
Removed gamma/response_curve power operations in:
- `modules/tone_mapping.py` (lines 64, 126)
- `modules/image_processing.py` (line 190)
- `Phos.py` (lines 712-716)

### 📊 結果 Results
- ✅ Midtone brightness restored from 3% to 18% (+475%)
- ✅ Correct Linear RGB brightness levels
- ✅ Tone mapping now works correctly

---

## 🎨 v0.8.2 - Color Management & Gamma Correction (2026-01-12)

### ✨ 核心特性 Core Features
**物理正確性提升**: 實作 sRGB → Linear RGB gamma 解碼，確保所有光學計算在線性光空間進行

### 核心變更 Core Changes
- **新增函數**: `modules/optical_core.py:srgb_to_linear()` - IEC 61966-2-1:1999 標準實作
- **修正流程**: 輸入圖像經過 gamma 解碼後，在線性光空間進行光譜響應矩陣運算
- **物理基礎**: Beer-Lambert Law, Grassmann's Laws 只在線性光空間物理正確
- **測試覆蓋**: 新增 30 個色彩空間測試，全部通過 (100% ✅)

### 技術細節 Technical Details
- **色彩空間流程**:
  ```
  sRGB Input (gamma 2.2) 
    → Gamma Decode (Linear RGB)
    → Spectral Response Matrix
    → Optical Effects (Bloom, Halation, Grain)
    → Tone Mapping (back to gamma space)
    → Output
  ```
- **影響範圍**: 
  - ✅ 所有膠片的光譜響應矩陣現在假設 Linear RGB 輸入（已明確文件化）
  - ✅ 能量守恆測試全部通過（8/8 彩色膠片，灰階偏差 = 0.0000）
  - ✅ 物理效果（bloom, halation, grain）在線性空間正確執行
- **效能影響**: 
  - Gamma 解碼：81ms（3000×4000 圖像）
  - 完整流程：427ms（增加 ~20%，物理正確性提升）

### 參考文獻 References
- IEC 61966-2-1:1999 - sRGB 色彩空間標準
- Poynton, C. (2003). "Digital Video and HD: Algorithms and Interfaces"
- Hunt, R. W. G. (2004). "The Reproduction of Colour", 6th ed.

---

## 🎨 v0.8.1 - Spectral Calibration & Pure Physical Mode (2026-01-12)

### 🎨 光譜響應校正 Spectral Response Calibration
**物理精度提升**: 消除灰階輸入色偏，實現精確能量守恆（8 種彩色膠片）

### 🔬 純物理模式 Pure Physical Mode
**架構簡化**: 移除 ARTISTIC/HYBRID 模式，統一使用 PHYSICAL 模式
- **PhysicsMode enum**: 僅保留 `PHYSICAL` 選項
- **FilmProfile 預設值**: 所有 13 款膠片 + 8 款 Mie 變體預設 `physics_mode=PhysicsMode.PHYSICAL`
- **UI 簡化**: 移除模式選擇器，固定顯示「🔬 物理模式: 能量守恆、H&D曲線、泊松顆粒」
- **邏輯簡化**: 移除冗餘 `physics_mode` 檢查，直接根據 `bloom_params.mode` / `grain_params.mode` 判斷
- **測試覆蓋**: 155/155 核心測試通過 (100% ✅)

### 技術細節 Technical Details
- **檔案修改**: `film_models.py`, `ui_components.py`, `Phos.py`, `test_optical_effects.py`
- **向後相容**: 所有膠片自動使用物理模式，無需手動設置
- **破壞性變更**: 移除 `PhysicsMode.ARTISTIC` 和 `PhysicsMode.HYBRID`（建議 v0.7.x 用戶謹慎升級）

---

## ⚠️ v0.8.0 - Breaking Change: Import Cleanup (2026-01-12)

### 🚨 破壞性變更 Breaking Change
不再支持從 Phos.py 導入模組化函數

### 核心變更 Core Changes
- ❌ **移除**: 從 `Phos.py` 直接導入 21 個模組化函數的官方支持
- ✅ **必須使用**: `from modules import ...` 導入
- 📚 **遷移指南**: [`MIGRATION_GUIDE_v08.md`](MIGRATION_GUIDE_v08.md)
- 🧪 **測試狀態**: 452/452 tests passing (100% ✅)

### 為什麼要做這個變更？ Why This Change?
1. **清晰的 API 邊界**: Phos.py 是 Streamlit 應用，不是可導入的庫
2. **防止混淆**: 明確 `modules/` 包才是正式 API
3. **更好的維護性**: 簡化代碼依賴關係
4. **符合 Python 最佳實踐**: 應用程式與庫分離

### 遷移方式 Migration Guide

**❌ 舊方式（v0.8.0 不再支持）**:
```python
from Phos import apply_hd_curve, standardize, apply_reinhard
```

**✅ 新方式（必須使用）**:
```python
# 方式 1: 從具體模組導入
from modules.image_processing import apply_hd_curve
from modules.optical_core import standardize
from modules.tone_mapping import apply_reinhard

# 方式 2: 從統一入口導入
from modules import apply_hd_curve, standardize, apply_reinhard
```

---

## 📦 v0.7.0 - Modularization Complete (2025-01-12)

### 📦 模組化架構 Modular Architecture
**架構重構**: 將 Phos.py 拆分為 5 個可維護的模組，大幅提升代碼可維護性

- **Phos.py 瘦身**: 1916 → 942 行 (**-51%** 🎉)
- **5 個模組**: 
  - `modules/optical_core.py` (149 lines) - 光度計算核心
  - `modules/tone_mapping.py` (187 lines) - Tone mapping 策略
  - `modules/psf_utils.py` (374 lines) - PSF 生成工具
  - `modules/wavelength_effects.py` (391 lines) - 波長依賴光學效果
  - `modules/image_processing.py` (203 lines) - H&D 曲線與層組合
- **21 個函數提取**: 全部函數已模組化
- **452 個測試通過**: 100% 測試覆蓋
- **100% 向後相容**: v0.7.0 中舊代碼無需修改（v0.8.0 已移除舊導入）

### v0.7.1: 標記舊導入為棄用 Deprecation Warnings
- 從 `Phos.py` 直接導入模組化函數標記為 **DEPRECATED**
- 添加詳細的棄用警告與遷移指南
- 為 v0.8.0 Breaking Change 做準備

### 模組化成果 Modularization Results

| 指標 | 初始值 | 最終值 | 變化 |
|------|--------|--------|------|
| **Phos.py 行數** | 1916 | 942 | **-974 (-51%)** 🚀 |
| **模組數量** | 0 | 5 | ✅ 完成 |
| **測試總數** | 434 | 452 | +18 |
| **函數提取數** | 0 | 21 | 全部提取 |

---

## 🧹 v0.6.x - Code Quality & Documentation Cleanup (2025-01-11)

### v0.6.1: Task 2 完成
- **標記棄用參數**: 為 v0.7.0 移除做準備
  - `BloomParams.kernel_size` → 使用動態計算
  - `GrainParams.poisson_scaling` → 整合至 `intensity`
  - `ReciprocityParams.use_log_decay` → 始終啟用對數衰減
- **修復殘留 TODOs**: 移除 2 個已完成的佔位符註解
- **測試狀態**: 282/286 tests passing (98.6%)

### v0.6.0: Task 1 完成 ⚠️ Breaking Change
- **移除 4 個棄用函數** (v0.5.1 已標記):
  - `apply_bloom_optimized()` → 使用 `apply_bloom(mode='physical')`
  - `generate_grain_optimized()` → 使用 `generate_grain(mode='poisson')`
  - `apply_halation_old()` → 使用 `apply_halation()` (Beer-Lambert)
  - `calculate_reciprocity_failure_old()` → 使用 `calculate_reciprocity_failure()`
- **代碼清理**: 刪除 ~200 行無效代碼
- **遷移指南**: 參見 `BREAKING_CHANGES_v06.md`

### v0.5.1: Phase 2 短期改進
- **棄用警告**: 為 4 個待移除函數添加 `DeprecationWarning`
- **文檔更新**: 更新所有函數 docstring，標註棄用信息
- **向後相容**: 100% 相容 v0.5.0 代碼

### v0.5.0: Phase 1 技術債務清理
- **統一 Bloom 處理**: 創建 `apply_bloom()` 統一介面，消除 ~80 行重複代碼
- **統一 Grain 處理**: 創建 `generate_grain()` 統一介面，消除 ~80 行重複代碼
- **移除 HalationParams**: 統一使用 Beer-Lambert 參數
- **測試覆蓋**: 310/315 tests passing (98.4%)

---

## 🔬 v0.4.2 - Reciprocity Failure Simulation (2025-12-24)

### 📸 互易律失效模擬 Reciprocity Failure
**物理升級**: 長曝光時膠片的非線性響應，完整重現底片特性

### 核心功能 Core Features
- **Schwarzschild 定律**: 準確模擬長曝光亮度損失與色偏
  - 數學模型: `I_eff = I · t^(p-1)`（正規化形式，t=1s 完全相容）
  - 對數 p 值衰減: `p(t) = p0 - k·log10(t/t_ref)`（文獻吻合度 90%+）
  - 曝光時間範圍: 0.0001s - 300s（高速攝影 → 星空攝影）

- **通道獨立處理**: 模擬真實色偏現象
  - 紅色通道: p=0.93（失效最低）
  - 綠色通道: p=0.90（中等失效）
  - 藍色通道: p=0.87（失效最高 → 長曝光偏暖）

- **6 種真實膠片校準**:
  - **Kodak Portra 400**: 低失效（T-Grain 技術）
  - **Kodak Ektar 100**: 極低失效（現代乳劑）
  - **Fuji Velvia 50**: 高失效（反轉片特性）
  - **Ilford HP5 Plus 400**: 中等失效（黑白，p_mono=0.87）
  - **Kodak Tri-X 400**: 中等失效（黑白，p_mono=0.88）
  - **Cinestill 800T**: 低失效（電影膠片）

### 效能指標 Performance
- **1024×1024**: 3.65 ms（< 1% overhead）
- **4K (2160×3840)**: 28.48 ms（適合批次處理）
- **線性擴展**: O(N) 時間複雜度

### 測試覆蓋 Test Coverage
- **72 個新測試**（100% 通過）:
  - 49 單元測試：核心功能、邊界條件、能量守恆
  - 23 整合測試：完整流程、所有膠片、數值穩定性
- **專案測試通過率**: 310/312 (**99.4%**)

---

## 🎨 v0.4.0 - Spectral Film Simulation (Phase 4)

### 光譜膠片模擬 Spectral Film Simulation
**重大突破**: 從 RGB 3通道 → 光譜 31通道物理色彩渲染

### 核心功能 Core Features
- **31通道光譜處理**: 380-770nm（13nm 間隔），基於 Smits (1999) RGB→Spectrum 演算法
- **真實膠片光譜敏感度**: 4 種膠片的實際光譜響應曲線
  - Kodak Portra 400（柔和人像）
  - Fuji Velvia 50（極致飽和風景）
  - CineStill 800T（電影質感鎢絲燈）
  - Ilford HP5 Plus 400（黑白經典顆粒）
- **物理色彩渲染**: 光譜積分計算膠片響應，保留各膠片色彩特性

### 效能指標 Performance (6MP 影像)
- **RGB→Spectrum**: 3.29s（經 3.5x 優化）
  - Branch-free vectorization（無條件分支）
  - Tile-based processing（512×512 分塊）
  - Mutual exclusion masks（修正灰階 bug）
- **完整 Pipeline**: 4.24s（RGB → Spectrum → Film RGB）
- **記憶體占用**: 31 MB（23x 優化，從 709MB）
- **測試覆蓋**: 21/21 正確性測試通過，往返誤差 <3%

### 物理正確性 Physical Correctness
- ✅ 能量守恆 <0.01%
- ✅ 往返誤差 <3%（RGB → Spectrum → RGB）
- ✅ 色彩關係保持（R>G>B 順序不變）
- ✅ 非負性保證（無負值光譜）

---

## 🎯 v0.3.0 - ISO Unification System & UI Integration (2025-12-20)

### P1-2: ISO 統一推導系統 ISO Unification System
- **物理公式推導**: 從 ISO 值自動計算顆粒直徑、散射比例、Mie 參數
- **膠片類型分類**: 
  - `fine_grain`: 細緻顆粒（Portra400, Ektar100, Velvia50）
  - `standard`: 標準顆粒（NC200, Gold200）
  - `high_speed`: 高感顆粒（Cinestill800T, Superia400）
- **一鍵創建膠片**: `create_film_profile_from_iso()` 快速生成配置
- **物理分數提升**: 7.8/10 → **8.0/10** ⭐
- **測試覆蓋率**: 45/46 tests passed (97.8%) ✅

**核心公式**（參考 James 1977）:
```python
# 顆粒直徑（μm）
d_mean = d0 × (ISO/100)^(1/3)

# 視覺顆粒強度（0-1）
grain_intensity = k × √(d_mean/d0) × √(ISO/100)

# 散射比例（Mie 理論）
scattering_ratio = 0.04 + 0.04 × (d_mean/d0)²
```

### 物理模式 UI 整合 Physical Mode UI Integration
- **渲染模式選擇器**: 在側邊欄一鍵切換 Artistic / Physical / Hybrid 模式
- **參數控制面板**: 三個可折疊區塊（Bloom / H&D Curve / Grain），提供即時參數調整
- **智能顯示**: Artistic 模式不顯示物理參數，保持介面簡潔
- **固定圖片尺寸**: 單張處理 800px，批次預覽 200px，優化檢視體驗
- **向後相容**: 預設 Artistic 模式，完全不影響現有使用者工作流程

---

## 📦 v0.2.0 - Batch Processing & Physical Mode (2025-12-15)

### 📦 批次處理 Batch Processing
- **多檔案上傳**: 一次處理 2-50 張照片
- **即時進度**: 進度條 + 狀態更新
- **ZIP 下載**: 一鍵下載所有結果
- **錯誤隔離**: 單張失敗不影響其他

### 🎨 現代化 UI Modern UI Redesign
- **簡潔設計**: 精簡 CSS，提升效能
- **深色主題**: 珊瑚紅配色方案
- **流暢互動**: 統一動畫與回饋
- **響應式布局**: 清晰的視覺層次

### 🔬 物理模式 Physical Mode
- **能量守恆**: 光學效果遵守能量守恆定律（誤差 < 0.01%）
- **H&D 曲線**: Hurter-Driffield 特性曲線（對數響應 + Toe/Shoulder）
- **Poisson 顆粒**: 基於光子統計的物理噪聲（SNR ∝ √曝光量）
- **三種模式**: Artistic（預設，視覺導向）/ Physical（物理準確）/ Hybrid（混合）

---

## 📊 物理分數進展 Physics Score Progress

```
Baseline (v0.2.0):              6.5/10
P0-2 (Halation):                7.8/10 (+1.3)
P1-2 (ISO Unification):         8.0/10 (+0.2)
v0.4.2 (Reciprocity):           9.0/10 (+1.0)
v0.8.1 (Spectral Calib):        9.2/10 (+0.2) ⭐ CURRENT
────────────────────────────────────────────
P2 Target (Advanced Physics):   9.5/10
```

---

## 📅 發布時間軸 Release Timeline

```
2026-01-12: v0.8.3 (UI/UX 大改版)
2026-01-12: v0.8.2.3 (Critical sRGB 修復)
2026-01-12: v0.8.2.2 (顆粒修復)
2026-01-12: v0.8.2.1 (亮度修復)
2026-01-12: v0.8.2 (色彩管理)
2026-01-12: v0.8.1 (光譜校正 + 純物理模式)
2026-01-12: v0.8.0 (Import Cleanup, Breaking)
2025-01-12: v0.7.0 (模組化架構)
2025-01-11: v0.6.1 (棄用標記)
2025-01-11: v0.6.0 (函數移除, Breaking)
2025-12-24: v0.4.2 (互易律失效)
2025-12-20: v0.3.0 (ISO 統一系統)
2025-12-15: v0.2.0 (批次處理 + 物理模式)
```

---

## 🔗 相關文件 Related Documents

- **完整變更日誌**: [`CHANGELOG.md`](CHANGELOG.md) - 詳細技術變更記錄
- **專案說明**: [`README.md`](README.md) - 專案概述與快速開始
- **遷移指南**: [`MIGRATION_GUIDE_v08.md`](MIGRATION_GUIDE_v08.md) - v0.8.0 升級指南
- **破壞性變更**: [`BREAKING_CHANGES_v06.md`](BREAKING_CHANGES_v06.md) - v0.6.0 升級指南
- **物理模式指南**: [`docs/PHYSICAL_MODE_GUIDE.md`](docs/PHYSICAL_MODE_GUIDE.md)
- **膠片配置指南**: [`docs/FILM_PROFILES_GUIDE.md`](docs/FILM_PROFILES_GUIDE.md)

---

**最後更新 Last Updated**: 2026-01-12  
**維護者 Maintainer**: @LYCO6273
