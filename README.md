# Phos - 基於計算光學的膠片模擬

**Current Version: 0.6.1 (Code Quality & Documentation Cleanup)** 🚀  
**Stable Version: 0.4.2 (Reciprocity Failure)** ✅  
**Legacy Version: 0.4.1 (Spectral Film Simulation)** 📦

## Physics Score: 8.9/10 ⭐⭐⭐⭐ (Updated 2025-01-11)

Recent improvements:
- ✅ v0.6.1: Phase 3 Task 2 - Marked deprecated parameters, fixed TODOs
- ✅ v0.6.0: Phase 3 Task 1 - Removed 4 deprecated functions (breaking change)
- ✅ v0.5.1: Phase 2 Short-Term Improvements - Completed deprecation warnings
- ✅ v0.5.0: Phase 1 Technical Debt Cleanup - Unified Bloom/Grain interfaces

---

## 綜述 General

你說的對，但是 Phos 是基於「計算光學」概念的膠片模擬。透過計算光在底片上的行為，重現自然、柔美、立體的膠片質感。

**"No LUTs, we calculate LUX."**

Hello! Phos is a film simulation app based on the idea of "Computational Optical Imaging". By calculating the optical effects on the film, we reproduce the natural, soft, and elegant tone of these classical films.

這是一個原理驗證 demo，影像處理部分基於 OpenCV，互動基於 Streamlit 平台製作，部分程式碼使用了 AI 輔助生成。

This is a demo for idea testing. The image processing part is based on OpenCV, and the interaction is built on the Streamlit platform. Some of the code was generated with the assistance of AI.

如果您發現了專案中的問題，或是有更好的想法想要分享，還請透過郵箱 lyco_p@163.com 與我聯繫，我將不勝感激。

If you find any issues in the project or have better ideas you would like to share, please contact me via email at lyco_p@163.com. I would be very grateful.

---

## ✨ v0.6.1 新特性 What's New in v0.6.1 🆕

### 🧹 Phase 3: Code & Documentation Cleanup (Maintenance Focus)
**維護升級**: 清理技術債務，移除過時代碼與文檔，提升項目可維護性

#### v0.6.1: Task 2 完成（2025-01-11）
- **標記棄用參數**: 為 v0.7.0 移除做準備
  - `BloomParams.kernel_size` → 使用動態計算
  - `GrainParams.poisson_scaling` → 整合至 `intensity`
  - `ReciprocityParams.use_log_decay` → 始終啟用對數衰減
- **修復殘留 TODOs**: 移除 2 個已完成的佔位符註解
- **測試狀態**: 282/286 tests passing (98.6%)

#### v0.6.0: Task 1 完成（2025-01-11） ⚠️ Breaking Change
- **移除 4 個棄用函數** (v0.5.1 已標記):
  - `apply_bloom_optimized()` → 使用 `apply_bloom(mode='physical')`
  - `generate_grain_optimized()` → 使用 `generate_grain(mode='poisson')`
  - `apply_halation_old()` → 使用 `apply_halation()` (Beer-Lambert)
  - `calculate_reciprocity_failure_old()` → 使用 `calculate_reciprocity_failure()`
- **代碼清理**: 刪除 ~200 行無效代碼
- **遷移指南**: 參見 `BREAKING_CHANGES_v06.md`

#### v0.5.1: Phase 2 短期改進（2025-01-11）
- **棄用警告**: 為 4 個待移除函數添加 `DeprecationWarning`
- **文檔更新**: 更新所有函數 docstring，標註棄用信息
- **向後相容**: 100% 相容 v0.5.0 代碼

#### v0.5.0: Phase 1 技術債務清理（2025-01-11）
- **統一 Bloom 處理**: 創建 `apply_bloom()` 統一介面，消除 ~80 行重複代碼
- **統一 Grain 處理**: 創建 `generate_grain()` 統一介面，消除 ~80 行重複代碼
- **移除 HalationParams**: 統一使用 Beer-Lambert 參數
- **測試覆蓋**: 310/315 tests passing (98.4%)

#### 代碼品質提升（v0.5.0 → v0.6.1）
| 指標 | v0.5.0 | v0.6.1 | 變化 |
|------|--------|--------|------|
| 已棄用函數 | 4 個 | 0 個 | -100% ✅ |
| 棄用參數 | 0 個 | 3 個標記 | 準備 v0.7.0 |
| 程式碼行數 (Phos.py) | 3300+ | 3226 | -74 行 |
| 測試通過率 | 98.4% | 98.6% | +0.2% |

#### 設計哲學
遵循以下核心原則進行清理：
- **Good Taste**: 消除冗餘接口，保持代碼簡潔
- **Never Break Userspace**: 漸進式棄用（警告 → 標記 → 移除）
- **Pragmatism**: 移除無效代碼，保留實用功能
- **Simplicity**: 降低維護成本，提升開發效率

---

## ✨ v0.4.2 新特性 What's New in v0.4.2

### 📸 互易律失效模擬 Reciprocity Failure Simulation (TASK-014)
**物理升級**: 長曝光時膠片的非線性響應，完整重現底片特性

#### 核心功能
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
    - 30s: ~39% 亮度損失，最小色偏
  - **Kodak Ektar 100**: 極低失效（現代乳劑）
    - 30s: ~35% 亮度損失
  - **Fuji Velvia 50**: 高失效（反轉片特性）
    - 30s: ~56% 亮度損失，明顯藍色減弱
  - **Ilford HP5 Plus 400**: 中等失效（黑白，p_mono=0.87）
  - **Kodak Tri-X 400**: 中等失效（黑白，p_mono=0.88）
  - **Cinestill 800T**: 低失效（電影膠片）

#### UI 整合
- **曝光時間滑桿**: 對數尺度（0.0001s - 300s）
- **即時效果預覽**:
  - EV 補償計算（例：30s → "+0.9 EV"）
  - 預估亮度損失百分比
  - 色偏趨勢指示
- **物理模式整合**: 自動與 H&D 曲線處理整合
  - 執行順序: 互易律失效 → H&D 曲線 → 光暈 → 顆粒

#### 效能指標
- **1024×1024**: 3.65 ms（< 1% overhead）
- **4K (2160×3840)**: 28.48 ms（適合批次處理）
- **線性擴展**: O(N) 時間複雜度

#### 測試覆蓋
- **72 個新測試**（100% 通過）:
  - 49 單元測試：核心功能、邊界條件、能量守恆
  - 23 整合測試：完整流程、所有膠片、數值穩定性
- **專案測試通過率**: 310/312 (**99.4%**)

#### 物理正確性
- ✅ 能量守恆驗證（無能量增加）
- ✅ 單調性驗證（時間越長越暗）
- ✅ 文獻驗證（Kodak/Ilford 數據吻合 90-95%）
- ✅ 向後相容（enabled=False 或 t=1s 無影響）

#### 如何使用
1. 選擇 Physical 或 Hybrid 渲染模式
2. 展開「📸 互易律失效」控制面板
3. 勾選「啟用互易律失效」
4. 調整曝光時間滑桿（例：30s）
5. 查看即時預覽（EV 補償、亮度損失）
6. 處理影像

#### 適用場景
- **星空攝影**: 60-300s 長曝光色偏模擬
- **風景攝影**: 黃昏/藍調時刻延長曝光（10-60s）
- **光繪創作**: 利用互易律失效的創意效果
- **歷史重現**: 匹配老膠片外觀（前現代乳劑）

**技術文檔**: `archive/completed_tasks/TASK-014-reciprocity-failure/` (已歸檔)  
**新模組**: `reciprocity_failure.py` (514 行，5 函數 + 6 預設配置)

---

## ✨ v0.4.0 新特性 What's New in v0.4.0 🆕

### 🎨 光譜膠片模擬 Spectral Film Simulation (Phase 4)
**重大突破**: 從 RGB 3通道 → 光譜 31通道物理色彩渲染

#### 核心功能
- **31通道光譜處理**: 380-770nm（13nm 間隔），基於 Smits (1999) RGB→Spectrum 演算法
- **真實膠片光譜敏感度**: 4 種膠片的實際光譜響應曲線
  - Kodak Portra 400（柔和人像）
  - Fuji Velvia 50（極致飽和風景）
  - CineStill 800T（電影質感鎢絲燈）
  - Ilford HP5 Plus 400（黑白經典顆粒）
- **物理色彩渲染**: 光譜積分計算膠片響應，保留各膠片色彩特性
- **完整 UI 整合**: 物理模式下可選擇啟用（實驗性功能）

#### 效能指標 (6MP 影像)
- **RGB→Spectrum**: 3.29s（經 3.5x 優化）
  - Branch-free vectorization（無條件分支）
  - Tile-based processing（512×512 分塊）
  - Mutual exclusion masks（修正灰階 bug）
- **完整 Pipeline**: 4.24s（RGB → Spectrum → Film RGB）
- **記憶體占用**: 31 MB（23x 優化，從 709MB）
- **測試覆蓋**: 21/21 正確性測試通過，往返誤差 <3%

#### 物理正確性
- ✅ 能量守恆 <0.01%
- ✅ 往返誤差 <3%（RGB → Spectrum → RGB）
- ✅ 色彩關係保持（R>G>B 順序不變）
- ✅ 非負性保證（無負值光譜）

#### 如何使用
1. 選擇 Physical 或 Hybrid 渲染模式
2. 展開「🎨 膠片光譜模擬」
3. 勾選「啟用光譜膠片模擬」
4. 選擇膠片類型
5. 處理影像（約 5-10 秒）

**技術文檔**: `archive/completed_tasks/TASK-003-medium-physics/` (已歸檔)

---

## ✨ v0.3.0 新特性 What's New in v0.3.0

### 🎯 P1-2: ISO 統一推導系統 ISO Unification System (2025-12-20) 🆕
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

### 🎛️ 物理模式 UI 整合 Physical Mode UI Integration
- **渲染模式選擇器**: 在側邊欄一鍵切換 Artistic / Physical / Hybrid 模式
- **參數控制面板**: 三個可折疊區塊（Bloom / H&D Curve / Grain），提供即時參數調整
- **智能顯示**: Artistic 模式不顯示物理參數，保持介面簡潔
- **固定圖片尺寸**: 單張處理 800px，批次預覽 200px，優化檢視體驗
- **向後相容**: 預設 Artistic 模式，完全不影響現有使用者工作流程

### 📐 UI 參數範圍 UI Parameter Ranges
- **Bloom 光暈**:
  - 模式: artistic / physical
  - 閾值: 0.5 - 0.95 (預設 0.8)
  - 散射比例: 0.05 - 0.30 (預設 0.1, 僅 physical 模式)
  
- **H&D 曲線**:
  - 啟用/停用切換
  - Gamma: 0.5 - 2.0 (預設 0.65)
  - Toe 強度: 0.5 - 5.0 (預設 2.0)
  - Shoulder 強度: 0.5 - 3.0 (預設 1.5)
  
- **顆粒 Grain**:
  - 模式: artistic / poisson
  - 顆粒尺寸: 0.5 - 3.5 μm (預設 1.5)
  - 強度: 0.0 - 2.0 (預設 0.8)

詳見下方「[物理模式使用指南](#-物理模式-physical-mode-實驗性)」

---

## ✨ v0.2.0 新特性 What's New in v0.2.0

### 📦 批次處理 Batch Processing
- **多檔案上傳**: 一次處理 2-50 張照片 (Multi-file upload: Process 2-50 photos at once)
- **即時進度**: 進度條 + 狀態更新 (Real-time progress: Progress bar + status updates)
- **ZIP 下載**: 一鍵下載所有結果 (ZIP download: One-click download all results)
- **錯誤隔離**: 單張失敗不影響其他 (Error isolation: Single failure won't affect others)

### 🎨 現代化 UI Modern UI Redesign
- **簡潔設計**: 精簡 CSS，提升效能 (Clean design: Streamlined CSS, better performance)
- **深色主題**: 珊瑚紅配色方案 (Dark theme: Coral red color scheme)
- **流暢互動**: 統一動畫與回饋 (Smooth interaction: Consistent animations and feedback)
- **響應式布局**: 清晰的視覺層次 (Responsive layout: Clear visual hierarchy)

### 🔬 物理模式 Physical Mode (v0.2.0 引入)
- **能量守恆**: 光學效果遵守能量守恆定律（誤差 < 0.01%）
- **H&D 曲線**: Hurter-Driffield 特性曲線（對數響應 + Toe/Shoulder）
- **Poisson 顆粒**: 基於光子統計的物理噪聲（SNR ∝ √曝光量）
- **三種模式**: Artistic（預設，視覺導向）/ Physical（物理準確）/ Hybrid（混合）
- **UI 支援**: v0.3.0 已完整支援 UI 參數調整 ✅

### 🧪 中等物理升級 Medium Physics (v0.3.0 實驗性)

#### Phase 5.5: Mie 散射高密度查表 v2 🆕
- **精度提升**: η 插值誤差從 155% → 2.16%（**72x 改善**）
- **格點密度**: 21 → 200 點（**9.5x 提升**）
- **波長範圍**: 400-700nm（+50% 覆蓋，支援極藍/極紅）
- **ISO 範圍**: 50-6400（支援低 ISO 細膩膠片）
- **插值速度**: 0.0205 ms/次（**6.2x 更快**）
- **檔案大小**: 5.9 KB（可接受，+2.7x）

#### 核心功能
- **波長依賴散射**: 
  - 經驗公式: η(λ) ∝ λ⁻³·⁵ (類 Rayleigh，藍光強)
  - Mie 理論: 完整計算 AgBr 粒子散射（含振盪效應）
- **分離 Halation**: Beer-Lambert 透過率模型（獨立於 Bloom）
- **能量守恆**: 誤差 < 0.01%

#### 效能基準
- 影像處理: ~0.14s (2000×3000)
- 查表載入: 0.53 ms（首次，快取後忽略）
- 記憶體占用: +30 MB（PSF 快取）

#### Phase 4: 光譜膠片模型 Spectral Film Model 🆕
- **31 通道光譜處理**: 380-770nm（13nm 間隔），基於 Smits (1999) RGB→Spectrum 演算法
- **膠片光譜敏感度**: 4 種真實膠片曲線（Portra400, Velvia50, Cinestill800T, HP5Plus400）
- **物理色彩渲染**: 從光譜積分計算膠片響應，保留各膠片色彩特性
- **效能優化**: 完整 pipeline 4.24s (6MP 影像)
  - RGB→Spectrum: 3.29s（3.5x 加速，branch-free vectorization）
  - 記憶體占用: 31 MB (tile-based processing, 23x 優化)
- **測試覆蓋**: 21/21 正確性測試通過，往返誤差 <3%
- **UI 整合**: 🚧 進行中（Milestone 5）

詳見下方「[物理模式使用指南](#-物理模式-physical-mode-實驗性)」章節

---

## 🎞️ 膠片庫 Film Library

### 彩色膠片 Color Films (9 款)

| 膠片 | 靈感來源 | ISO | 特色 | 物理模式 | 光譜模式 |
|------|---------|-----|------|---------|---------|
| **NC200** | Fuji C200 | 200 | 富士經典日系清新 | ✅ Standard | - |
| **Gold200** | Kodak Gold 200 | 200 | Kodak 日常暖調 | ✅ Standard | - |
| **Portra400** | Kodak Portra 400 | 400 | 人像王者，T-Grain 技術 | ✅ Fine-Grain | 🆕 31-ch |
| **Ektar100** | Kodak Ektar 100 | 100 | 風景利器，極細顆粒 | ✅ Fine-Grain | - |
| **ProImage100** | Kodak ProImage 100 | 100 | 專業影像，自然色調 | ✅ Fine-Grain | - |
| **Velvia50** | Fuji Velvia 50 | 50 | 極致飽和，風景之王 | ✅ Fine-Grain | 🆕 31-ch |
| **Superia400** | Fuji Superia 400 | 400 | 日常拍攝，明亮色調 | ✅ High-Speed | - |
| **Cinestill800T** | CineStill 800T | 800 | 電影質感，紅色光暈 | ✅ High-Speed | 🆕 31-ch |
| **Portra400 (Mie)** | 實驗配置 | 400 | Mie 散射理論查表 | 🔬 Experimental | - |

### 黑白膠片 B&W Films (4 款)

| 膠片 | 靈感來源 | ISO | 特色 | 對比度 | 光譜模式 |
|------|---------|-----|------|--------|---------|
| **AS100** | Fuji ACROS 100 | 100 | 細膩黑白，低顆粒 | 低對比 | - |
| **HP5Plus400** | Ilford HP5+ 400 | 400 | 街拍經典，明顯顆粒 | 標準 | 🆕 31-ch |
| **TriX400** | Kodak Tri-X 400 | 400 | 新聞攝影，經典顆粒 | 標準 | - |
| **FP4Plus125** | Ilford FP4+ 125 | 125 | 風景黑白，細緻層次 | 標準 | - |

**備註**：
- ✅ **物理模式**: 所有膠片皆已整合 P1-2 ISO 推導系統
- 🔬 **實驗性**: `Portra400_MediumPhysics_Mie` 使用 Mie 理論查表（P1-1）
- 🆕 **光譜模式 (31-ch)**: 基於光譜敏感度曲線的物理色彩渲染（Phase 4，🚧 UI 整合中）
- ⚠️ **過時版本**: `Portra400_MediumPhysics` 為測試用途，已被標準版取代

---

## 🚀 快速開始 Quick Start

### 安裝依賴 Install Dependencies
```bash
pip install -r requirements.txt
```

### 執行應用 Run Application

**Current Version (v0.6.1 - Recommended)**
```bash
streamlit run Phos.py
```

**Legacy Versions (Not Recommended)**
```bash
# v0.5.1 (with deprecation warnings)
streamlit run Phos_0.5.1.py

# v0.5.0 (Phase 1 cleanup)
streamlit run Phos_0.5.0.py
```

### 執行測試 Run Tests
```bash
# 完整測試套件（286 項測試，98.6% 通過率）
pytest -v

# 按模組測試
pytest tests_refactored/test_film_profiles.py -v     # 膠片配置測試
pytest tests_refactored/test_physics_core.py -v      # 物理核心測試
pytest tests_refactored/test_optical_effects.py -v   # 光學效果測試
pytest tests_refactored/test_reciprocity.py -v       # 互易律失效測試
pytest tests_refactored/test_spectral_film.py -v     # 光譜處理測試

# 效能測試
pytest tests_refactored/test_performance.py -v

# 快速驗證（只顯示失敗）
pytest -q --tb=line
```

**註**: 測試配置已在 `pytest.ini` 中設定，自動指向 `tests_refactored/` 目錄

---

## 依賴 Requirements

本專案基於 Python 3.13 編寫

This project is based on Python 3.13

### 核心依賴 Core Dependencies
```
numpy                     2.2.6
opencv-python             4.12.0.88
streamlit                 1.51.0
pillow                    12.0.0
scipy                     >=1.11.0
```

### 開發/測試依賴 Development/Testing Dependencies
```
pytest                    >=7.0.0
pytest-cov               >=4.0.0
pytest-benchmark         >=4.0.0
psutil                   >=5.9.0
```

相容性尚不明確，如果執行出現問題，請以此處標明的依賴為準。

Compatibility is not yet clear. If any issues occur during operation, please refer to the dependencies listed here.

完整依賴列表見 `requirements.txt`

Full dependency list available in `requirements.txt`

---

## 📁 專案結構 Project Structure

```
Phos/
├── 🎬 主程式 Main Applications
│   ├── Phos.py                            # v0.6.1 主應用（當前版本）
│   ├── phos_core.py                       # 核心處理模組（光學計算）
│   ├── phos_batch.py                      # 批次處理模組
│   ├── film_models.py                     # 膠片參數配置（13 款膠片）
│   ├── color_utils.py                     # 色彩工具函數
│   └── reciprocity_failure.py             # 互易律失效模組
│
├── 🧪 測試 Tests (98.6% Pass Rate)
│   ├── tests_refactored/                  # 測試套件（286 項測試）
│   │   ├── test_film_profiles.py          # 膠片配置測試
│   │   ├── test_physics_core.py           # 物理核心測試
│   │   ├── test_optical_effects.py        # 光學效果測試
│   │   ├── test_reciprocity.py            # 互易律失效測試
│   │   ├── test_spectral_film.py          # 光譜處理測試（58 項）
│   │   ├── test_mie_scattering.py         # Mie 散射測試
│   │   ├── test_fft_convolution.py        # FFT 卷積測試
│   │   ├── test_performance.py            # 效能基準測試
│   │   └── conftest.py                    # Pytest 配置與 fixtures
│   └── pytest.ini                         # Pytest 配置文件
│
├── 🔬 資料 Data (4 個主動數據文件)
│   ├── data/                              # 物理數據檔案
│   │   ├── mie_lookup_table_v2.npz        # Mie 散射查表 v2（200 點）✅
│   │   ├── film_spectral_sensitivity.npz  # 膠片光譜敏感度 ✅
│   │   ├── cie_1931_31points.npz          # CIE 1931 色彩匹配函數 ✅
│   │   └── smits_basis_spectra.npz        # RGB→光譜基底 ✅
│   └── scripts/                           # 工具腳本（7 個活躍工具）
│       ├── generate_cie_data.py           # 生成 CIE 數據
│       ├── generate_film_spectra.py       # 生成膠片光譜
│       ├── generate_mie_lookup.py         # 生成 Mie 查表
│       ├── generate_smits_basis.py        # 生成 RGB→光譜基底
│       ├── validate_mie_lookup_comprehensive.py  # Mie 查表驗證
│       ├── visualize_film_sensitivity.py  # 膠片敏感度視覺化
│       └── visualize_iso_scaling.py       # ISO 縮放視覺化
│
├── 📚 文檔 Documentation (Active Docs Only)
│   ├── docs/                              # 技術文檔（3 個核心文件）
│   │   ├── COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md  # 計算光學理論
│   │   ├── PHYSICAL_MODE_GUIDE.md         # 物理模式指南
│   │   └── FILM_PROFILES_GUIDE.md         # 膠片配置指南
│   ├── README.md                          # 專案說明（本檔案）
│   ├── CHANGELOG.md                       # 版本更新記錄
│   └── BREAKING_CHANGES_v06.md            # v0.6.0 遷移指南
│
├── 📋 任務規劃 Tasks
│   └── tasks/
│       └── PHYSICS_IMPROVEMENTS_ROADMAP.md # 物理改進路線圖（未來計畫）
│
├── 📦 歷史檔案 Archive (Historical Reference)
│   └── archive/
│       ├── README.md                      # 檔案索引（包含完整目錄）
│       ├── completed_tasks/               # 17 個已完成任務（TASK-001 to TASK-017）
│       ├── docs/                          # 11 個過時計畫文件
│       ├── tests_legacy/                  # 舊測試目錄（34 項測試，已棄用）
│       ├── backups/                       # 程式碼備份（7 個檔案）
│       ├── data/                          # 實驗數據（v1, v2_backup, v3）
│       └── scripts/                       # 診斷與測試腳本（13 個）
│
├── ⚙️ 配置 Configuration
│   ├── .streamlit/config.toml             # Streamlit 配置
│   ├── pytest.ini                         # Pytest 配置
│   ├── requirements.txt                   # Python 依賴
│   ├── .python-version                    # Python 版本（3.13）
│   ├── AGENTS.md                          # Agent 開發指南
│   └── .gitignore                         # Git 忽略規則
│
└── 📄 授權 License
    └── LICENSE                            # AGPL-3.0 授權條款
```

### 文檔結構說明 Documentation Structure

#### 📚 主動文檔（Active Docs）
根目錄與 `docs/` 僅保留主動維護的文檔：
- **技術文檔**: 核心理論、使用指南（3 個文件）
- **開發文檔**: 版本記錄、遷移指南、路線圖（3 個文件）

#### 🧪 測試結構（Tests）
`tests_refactored/` 是唯一主動測試目錄：
- **286 項測試**: 涵蓋所有核心功能（98.6% 通過率）
- **9 個測試文件**: 按功能模組組織
- **pytest.ini**: 配置文件，自動指向測試目錄

#### 📦 歷史檔案（Archive）
`archive/` 保存所有已完成的任務與過時文檔：
- **已完成任務**: 17 個任務目錄（TASK-001 to TASK-017）
- **過時計畫**: 10 個階段性計畫文件
- **舊測試**: tests_legacy/（34 項測試，已被 tests_refactored/ 取代）
- **實驗數據**: data/（v1, v2_backup, v3 查表）
- **代碼備份**: backups/（5 個檔案）
- 參見 `archive/README.md` 瞭解完整索引

---

## 許可證 License

本專案採用 **AGPL-3.0** 許可證。

This project is licensed under **AGPL-3.0**.

### 你可以 You may:
- ✅ 自由使用、研究、修改原始碼 (Freely use, study, and modify the source code)
- ✅ 用於個人或教育專案 (Use for personal or educational projects)
- ✅ 用於開源專案（同樣遵循 AGPL）(Use for open source projects, also following AGPL)

### 你必須 You must:
- 📝 公開任何基於本專案的修改程式碼 (Publicly release any modified code based on this project)
- 📝 保留原作者版權聲明 (Preserve the original author's copyright notice)
- 📝 同樣採用 AGPL 許可證分發衍生作品 (Distribute derivative works under the same AGPL license)

### 商業使用 Commercial Use
商業使用請聯絡作者獲取授權。

For commercial use, please contact the author for authorization.

完整許可證條款見 `LICENSE` 檔案。

Full license terms are available in the `LICENSE` file.

---

## 🔬 物理模式 Physical Mode (實驗性)

v0.2.0 引入了**物理導向模式**，在保留藝術效果的同時，提供更符合物理規律的模擬選項。

v0.2.0 introduces **Physics-oriented Mode**, offering more physically accurate simulation options while preserving artistic effects.

### 三種渲染模式 Three Rendering Modes

| 模式 Mode | 特點 Features | 適用場景 Use Cases |
|----------|--------------|------------------|
| **ARTISTIC** (預設) | 視覺優先，能量可增加，中調顆粒峰值 | 日常照片處理，追求美感 |
| **PHYSICAL** | 物理準確，能量守恆，H&D 曲線，Poisson 噪聲 | 科學視覺化，物理研究 |
| **HYBRID** | 混合配置，可選開啟物理特性 | 自訂藝術與物理平衡 |

### 核心物理特性 Core Physical Features

#### 1. 能量守恆光暈 Energy-Conserving Bloom
- **原理**: 點擴散函數（PSF）正規化：∫ PSF = 1
- **效果**: 高光溢出不增加總能量，更真實的光學散射
- **測試**: 能量誤差 < 0.01%（藝術模式 +10%）

#### 2. H&D 特性曲線 Hurter-Driffield Curve
- **原理**: 密度-對數曝光關係：D = γ × log₁₀(H) + D_fog
- **效果**: 
  - Toe 曲線：陰影柔和壓縮
  - Linear region：對比度由 gamma 控制
  - Shoulder 曲線：高光漸進飽和
- **動態範圍**: 10^8 → 10^3（壓縮 5.2×10^4 倍）

#### 3. Poisson 顆粒噪聲 Poisson Grain Noise
- **原理**: 光子計數統計，Poisson(λ) where λ = 曝光量
- **效果**: 
  - 暗部噪聲明顯（低 SNR）
  - 亮部噪聲抑制（高 SNR）
  - SNR ∝ √曝光量（物理正確）
- **對比**: 藝術模式中調峰值 vs 物理模式暗部峰值

#### 4. P1-2: ISO 統一推導系統 ISO Unification System 🆕
- **原理**: 基於 James (1977) 顆粒成長理論
- **功能**: 
  - 從 ISO 自動計算顆粒直徑（d = d₀·(ISO/100)^(1/3)）
  - 推導散射比例（Mie 理論）
  - 生成 Mie 尺寸參數（x = 2πr/λ）
- **測試**: 45/46 tests passed (97.8%) ✅

### 程式碼範例 Code Example

```python
from film_models import get_film_profile, create_film_profile_from_iso, PhysicsMode
import importlib.util

# 加載 Phos 模組
spec = importlib.util.spec_from_file_location("phos", "Phos_0.3.0.py")
phos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phos)

# ========== 方式 1: 使用現有膠片配置 ==========
film = get_film_profile("Portra400")

# 切換物理模式
film.physics_mode = PhysicsMode.PHYSICAL

# Bloom 配置（能量守恆）
film.bloom_params.enabled = True
film.bloom_params.mode = "physical"
film.bloom_params.threshold = 0.8
film.bloom_params.scattering_ratio = 0.1

# H&D 曲線配置
film.hd_curve_params.enabled = True
film.hd_curve_params.gamma = 0.65

# Poisson 顆粒配置
film.grain_params.enabled = True
film.grain_params.mode = "poisson"
film.grain_params.grain_size = 1.5

# ========== 方式 2: 從 ISO 快速創建（P1-2）==========
film = create_film_profile_from_iso(
    name="MyFilm400",
    iso=400,
    color_type="color",
    film_type="fine_grain",         # 或 "standard", "high_speed"
    tone_mapping_style="balanced",  # 或 "vivid", "natural", "soft"
    has_ah_layer=True               # 是否有 Anti-Halation 層
)

# ========== 處理影像 ==========
import cv2
image = cv2.imread("input.jpg")

# 1. 光譜響應計算
response_r, response_g, response_b, response_total = phos.spectral_response(image, film)

# 2. 光學處理
result = phos.optical_processing(
    response_r, response_g, response_b, response_total,
    film,
    grain_style="auto",
    tone_style="filmic"
)

# 3. 儲存結果
cv2.imwrite("output_physical.jpg", result)
```

### 參數調整指南 Parameter Tuning Guide

#### Bloom 參數 Bloom Parameters
```python
# 高光提取閾值（0-1）
bloom_params.threshold = 0.8
# 較低值 (0.6): 更多高光參與散射，光暈更明顯
# 較高值 (0.9): 僅極亮區域散射，光暈更集中

# 散射能量比例（0-1，僅物理模式）
bloom_params.scattering_ratio = 0.1
# 較低值 (0.05): 輕微光暈，更自然
# 較高值 (0.3): 強烈光暈，電影感
```

#### H&D 曲線參數 H&D Curve Parameters
```python
# Gamma（對比度）
hd_curve_params.gamma = 0.65
# 負片: 0.6-0.7（低對比，寬容度高）
# 正片: 1.5-2.0（高對比，鮮豔）

# Toe 強度（陰影壓縮）
hd_curve_params.toe_strength = 2.0
# 較低值 (1.0): 陰影更暗，對比強
# 較高值 (3.0): 陰影提亮，柔和

# Shoulder 強度（高光壓縮）
hd_curve_params.shoulder_strength = 1.5
# 較低值 (1.0): 高光更早飽和
# 較高值 (2.5): 高光漸進，細節保留
```

#### Poisson 顆粒參數 Poisson Grain Parameters
```python
# 顆粒尺寸（μm 等效）
grain_params.grain_size = 1.5
# ISO 100: 0.5-1.0（細膩）
# ISO 400: 1.0-2.0（明顯）
# ISO 1600: 2.0-3.0（粗糙）

# 噪聲強度（0-2）
grain_params.intensity = 0.8
# 較低值 (0.3): 輕微顆粒感
# 較高值 (1.5): 強烈顆粒感
```

### 測試驗證 Test Verification

```bash
# 執行完整測試套件（46+ 項測試）
python3 -m pytest tests/test_energy_conservation.py -v  # 5/5 能量守恆
python3 -m pytest tests/test_hd_curve.py -v             # 8/8 H&D 曲線
python3 -m pytest tests/test_poisson_grain.py -v        # 7/7 Poisson 顆粒
python3 -m pytest tests/test_integration.py -v          # 6/6 整合測試
python3 -m pytest tests/test_iso_unification.py -v      # 21/21 ISO 推導
python3 -m pytest tests/test_create_film_from_iso.py -v # 24/25 膠片創建
```

### 技術文檔 Technical Documentation

- **計算光學理論**: `docs/COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md`
- **物理模式指南**: `docs/PHYSICAL_MODE_GUIDE.md`
- **膠片配置指南**: `docs/FILM_PROFILES_GUIDE.md`
- **版本更新記錄**: `CHANGELOG.md`（完整版本歷史）
- **遷移指南**: `BREAKING_CHANGES_v06.md`（v0.6.0 破壞性變更）
- **歷史檔案**: `archive/README.md`（已完成任務與過時文檔索引）

### 已知限制 Known Limitations

1. **H&D 曲線**: 使用簡化過渡函數（非嚴格 Hurter-Driffield 模型）
2. **Poisson 噪聲**: λ < 20 時使用常態近似（精度略降）
3. **Bloom PSF**: 經驗 Gaussian/Exponential（非完整 Mie 散射）
4. **批次處理**: 尚未整合物理模式參數（單張處理已支援）✅

### 效能表現 Performance

| 影像尺寸 | 藝術模式 | 物理模式 | 開銷 |
|---------|---------|---------|------|
| 2000×3000 | ~0.7s | ~0.8s | +14% |

*測試環境: Python 3.13, M1 Mac (估算值)*

### 向後相容性 Backward Compatibility

- ✅ **預設行為不變**: 未明確設定時，使用 `ARTISTIC` 模式
- ✅ **所有膠片相容**: 13 款膠片配置全部支援物理模式
- ✅ **API 穩定**: 函數簽名不變（僅內部命名優化）
- ✅ **測試覆蓋**: 97.8%（45/46 tests passed）

### 物理分數進展 Physics Score Progress

```
Baseline (v0.2.0):              6.5/10
P0-2 (Halation):                7.8/10 (+1.3)
P1-2 (ISO Unification):         8.0/10 (+0.2) ⭐ CURRENT
────────────────────────────────────────────
P1 Target (Complete):           8.3/10
P2 Target (Advanced Physics):   9.0/10
```

### 下一步計畫 Next Steps

詳細路線圖參見 `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md`

#### Phase 3 後續（v0.7.0）
- 🔲 移除已標記棄用參數（3 個參數）
- 🔲 合併測試結構（`tests/` → `tests_refactored/`）
- 🔲 清理舊版本程式（Phos_0.5.*.py）

#### Phase 4: 物理改進（v0.8.0+）
- 🔲 P1-1: PSF 波長依賴 & Mie 查表整合
- 🔲 P1-3: 光譜敏感度升級（3 通道 → 31 通道）
- 🔲 參數預設集功能（Fine / Balanced / Strong）
- 🔲 視覺對比工具（Artistic vs Physical 並排）

已完成任務詳見 `archive/completed_tasks/`（15 個任務）

---

## 作者 Author

由 **@LYCO6273** 開發

Developed by **@LYCO6273**

🔗 **GitHub**: https://github.com/LYCO6273/Phos  
📧 **Email**: lyco_p@163.com

---

## 🗺️ 開發路線圖 Roadmap

### v0.6.1 ✅ (當前版本 Current, 2025-01-11)
- ✅ **Phase 3 Task 2**: 標記 3 個棄用參數，修復 2 個殘留 TODOs
- ✅ **測試狀態**: 282/286 tests passing (98.6%)
- ✅ **文檔清理**: 移動 21 個已完成任務/過時文檔至 `archive/`

### v0.6.0 ✅ (2025-01-11) ⚠️ Breaking Change
- ✅ **Phase 3 Task 1**: 移除 4 個棄用函數
- ✅ **代碼清理**: 刪除 ~200 行無效代碼
- ✅ **遷移指南**: 發布 `BREAKING_CHANGES_v06.md`

### v0.5.1 ✅ (2025-01-11)
- ✅ **Phase 2 短期改進**: 添加 4 個棄用警告
- ✅ **向後相容**: 100% 相容 v0.5.0

### v0.5.0 ✅ (2025-01-11)
- ✅ **Phase 1 技術債務清理**: 統一 Bloom/Grain 介面
- ✅ **測試覆蓋**: 310/315 tests passing (98.4%)

### v0.4.2 ✅ (穩定版 Stable)
- ✅ 互易律失效模擬（72 個新測試，99.4% 通過率）
- ✅ 6 種膠片校準（Portra400, Ektar100, Velvia50, HP5+, Tri-X, Cinestill800T）

### v0.4.0 ✅ (光譜模擬 Spectral)
- ✅ 31 通道光譜處理（380-770nm）
- ✅ 4 種膠片光譜敏感度（Portra400, Velvia50, Cinestill800T, HP5+）
- ✅ RGB→Spectrum 往返誤差 <3%

### v0.3.0 ✅ (物理模式 UI Physical Mode UI)
- ✅ P1-2: ISO 統一推導系統（物理分數 8.0/10）
- ✅ Mie 散射高密度查表 v2（插值誤差 72x 改善）
- ✅ 物理模式 UI 整合（渲染模式切換器）

### v0.2.0 ✅ (批次處理 Batch Processing)
- ✅ 多檔案批次處理（2-50 張照片）
- ✅ 物理模式核心（能量守恆 + H&D 曲線 + Poisson 顆粒）
- ✅ 現代化 UI 設計

### v0.7.0 (計畫中 Planned)
- 🔲 移除 3 個已標記棄用參數
- 🔲 合併測試結構（`tests/` → `tests_refactored/`）
- 🔲 清理舊版本程式（Phos_0.5.*.py）

### v0.8.0+ (未來 Future)
- 🔲 P1-1: PSF 波長依賴 & Mie 查表整合
- 🔲 P1-3: 光譜敏感度升級（3 通道 → 31 通道）
- 🔲 參數預設集（Fine/Balanced/Strong）
- 🔲 視覺對比工具（Artistic vs Physical 並排）
- 🔲 CLI 命令列工具

詳細計畫參見 `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md`  
已完成任務參見 `archive/completed_tasks/` (15 個任務)

---

## 🙏 致謝 Acknowledgments

感謝所有為本專案提供回饋和建議的使用者。

Thanks to all users who provided feedback and suggestions for this project.

本專案受到以下經典膠片的啟發：
- Fuji C200, ACROS 100, Superia 400, Velvia 50
- Kodak Portra 400, Ektar 100, Gold 200, ProImage 100, Tri-X 400
- Ilford HP5 Plus 400, FP4 Plus 125
- CineStill 800T

---

## 📞 聯絡與支援 Contact & Support

如果你喜歡這個專案，請給它一個 ⭐ Star！

If you like this project, please give it a ⭐ Star!

遇到問題？請透過以下方式聯絡：

Having issues? Contact via:
- 📧 Email: lyco_p@163.com
- 🐛 GitHub Issues: https://github.com/LYCO6273/Phos/issues

---

**Made with ❤️ by @LYCO6273**
