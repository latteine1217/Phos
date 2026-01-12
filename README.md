# Phos - 基於計算光學的膠片模擬

**Current Version: 0.8.3 (UI/UX Overhaul)** 🆕  
**Stable Version: 0.8.2 (Color Management - sRGB Output Conversion)** ✅  
**Previous Version: 0.8.1 (Spectral Calibration & Pure Physical Mode)** ⚠️

## Physics Score: 9.2/10 ⭐⭐⭐⭐⭐ (Updated 2026-01-12)

Recent improvements:
- 🆕 v0.8.3: **UI/UX Overhaul** - Visual enhancements + Quick presets + Enhanced statistics display
- ✅ v0.8.2: **Color Management** - Complete sRGB color pipeline (gamma decode + encode)
- ✅ v0.8.1: **Spectral Calibration** - Eliminated 7-13% green color cast across all films
- ✅ v0.8.1: **Pure Physical Mode** - Removed ARTISTIC/HYBRID modes, unified to PHYSICAL only
- ✅ v0.8.0: **Import Cleanup** - Removed deprecated imports from Phos.py
- ✅ v0.7.0: **Modularization** - 5 modules, 21 functions extracted, Phos.py reduced 51%

📚 **Complete Version History**: [`VERSION_HISTORY.md`](VERSION_HISTORY.md)

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

## ✨ v0.8.3 新特性 What's New in v0.8.3 🆕

### 🎨 UI/UX 全面改版 Comprehensive UI/UX Overhaul
**用戶體驗升級**: 視覺美化 + 快速預設 + 增強統計顯示

#### Phase 1: 視覺美化 Visual Enhancements
- **動態背景**: 徑向漸層光斑效果，提升視覺深度
- **按鈕動畫**:
  - 平滑 cubic-bezier 過渡效果（0.3s）
  - 懸停時向上移動效果（-2px translateY）
  - 主按鈕脈衝發光動畫（`@keyframes pulse-glow`）
  - 點擊時的按壓回饋
- **膠片資訊卡**:
  - 懸停時的顏色漸變效果
  - 更好的排版（字體大小、間距、字母間距）
  - 色彩編碼的元數據標籤
  - 懸停時的陰影深度變化
- **彩色提示框**: 成功/資訊/警告/錯誤的色彩編碼
- **圖片容器**: 懸停效果與陰影提升

#### Phase 2: 功能優化 Functional Improvements
- **🎯 快速預設** - 4 種場景化配置:
  - **👤 人像模式 (Portrait)**: Portra400 + 柔和顆粒 + 物理光暈 (0.85)
  - **🏞️ 風景模式 (Landscape)**: Velvia50 + 無顆粒 + 物理光暈 (0.80)
  - **🚶 街拍模式 (Street)**: TriX400 + 預設顆粒 + 藝術光暈 (0.75)
  - **🎬 電影風格 (Cinematic)**: Cinestill800T + 粗糙顆粒 + 藝術光暈 (0.70)

- **🔄 一鍵重置**: 重置所有參數至預設值
- **ℹ️ 配置摘要**: 查看當前所有設定
- **🎯 自動配置**: 預設自動配置：
  - 膠片類型
  - 處理品質模式
  - 顆粒風格
  - Tone mapping 曲線
  - 光暈參數

**實作細節**:
- 預設配置存儲在 `preset_configs` 字典
- 使用 `st.session_state` 實現預設持久化
- 自動應用預設值至所有 selectbox/slider 元件
- 使用可摺疊區塊 UI 並附詳細場景描述

#### Phase 3: 資訊呈現 Information Presentation
- **📊 圖片統計** (可摺疊區塊):
  - 解析度 (寬 × 高)
  - 總像素數（逗號格式化）
  - 記憶體大小 (MB)
  - 平均亮度 (0-255)
  - 亮度變化百分比（處理前後）

- **💎 處理統計卡片** (三欄布局):
  - ⏱️ 處理時間（黃色強調）
  - 🔬 物理模式（藍色強調）
  - 💾 檔案大小/品質（綠色強調）
  - 大型置中數字配圖示
  - 漸層背景與邊框

- **✨ 增強成功訊息**:
  - 漸層背景與發光效果
  - 乾淨排版與突出指標
  - 批次處理: 顯示成功/總數、總時間、平均每張時間

#### 技術細節
- **檔案修改**: `ui_components.py` (672 行，大幅重構)
- **CSS 樣式**: 36-283 行（視覺增強）
- **快速預設**: 323-548 行（功能整合）
- **統計顯示**: 770-925 行（資訊呈現）
- **測試狀態**: 所有現有測試通過 ✅

#### 向後相容性
- ✅ 所有現有功能保持不變
- ✅ 預設行為未改變
- ✅ API 簽名完全相容
- ✅ 無需修改現有代碼

#### 用戶反饋
修正了 v0.8.2.x 系列的關鍵問題：
- ✅ v0.8.2.3: sRGB 輸出轉換修復（膠片效果完全可見）
- ✅ v0.8.2.2: 顆粒尺寸減少 70-80%（線性 RGB 補償）
- ✅ v0.8.2.1: 中間色調亮度恢復（+475%）

完整技術細節參見 `CHANGELOG.md`

📚 **完整版本歷史**: [`VERSION_HISTORY.md`](VERSION_HISTORY.md)

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

## 🔬 物理模式 Physical Mode

v0.7.0 開始，Phos 全面採用**純物理模式**，基於物理原理實現真實膠片模擬。

Since v0.7.0, Phos uses **Pure Physical Mode**, implementing authentic film simulation based on physical principles.

### 純物理渲染 Pure Physical Rendering

| 特性 Feature | 實現方式 Implementation | 物理正確性 |
|-------------|----------------------|----------|
| **能量守恆** | 點擴散函數正規化 (∫ PSF = 1) | ✅ < 0.01% 誤差 |
| **H&D 曲線** | 對數響應 + Toe/Shoulder | ✅ 基於實驗數據 |
| **Poisson 顆粒** | 光子統計噪聲 (SNR ∝ √曝光量) | ✅ 暗部主導 |
| **光譜響應** | 行正規化係數矩陣 (v0.4.2) | ✅ 無灰階色偏 |

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
from film_models import get_film_profile, create_film_profile_from_iso
import cv2
from Phos import process_single_image

# ========== 方式 1: 使用預設膠片配置 ==========
film = get_film_profile("Portra400")
# v0.7.0+ 所有膠片預設使用物理模式

# 自訂物理參數（可選）
film.bloom_params.threshold = 0.8
film.bloom_params.scattering_ratio = 0.1
film.hd_curve_params.gamma = 0.65
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
image = cv2.imread("input.jpg")

result = process_single_image(
    image,
    film,
    grain_style="auto",      # poisson 顆粒（物理模式）
    tone_style="filmic"      # Filmic tone mapping
)

cv2.imwrite("output_physical.jpg", result)
```

### 參數調整指南 Parameter Tuning Guide

#### Bloom 參數 Bloom Parameters
```python
# 高光提取閾值（0-1）
bloom_params.threshold = 0.8
# 較低值 (0.6): 更多高光參與散射，光暈更明顯
# 較高值 (0.9): 僅極亮區域散射，光暈更集中

# 散射能量比例（0-1，物理模式）
bloom_params.scattering_ratio = 0.1
# 較低值 (0.05): 輕微光暈，更自然
# 較高值 (0.3): 強烈光暈，電影感

# 模式固定為 "physical"（v0.7.0+）
bloom_params.mode = "physical"  # 能量守恆
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

# 模式固定為 "poisson"（v0.7.0+）
grain_params.mode = "poisson"  # 基於光子統計
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
- **膠片配置指南**: `docs/FILM_PROFILES_GUIDE.md`
- **版本更新記錄**: `CHANGELOG.md`（完整版本歷史）
- **遷移指南**: `MIGRATION_GUIDE_v08.md`（v0.8.0 破壞性變更）
- **歷史檔案**: `archive/README.md`（已完成任務與過時文檔索引）

### 已知限制 Known Limitations

1. **H&D 曲線**: 使用簡化過渡函數（非嚴格 Hurter-Driffield 模型）
2. **Poisson 噪聲**: λ < 20 時使用常態近似（精度略降）
3. **Bloom PSF**: 經驗 Gaussian/Exponential（非完整 Mie 散射）

### 效能表現 Performance

| 影像尺寸 | 純物理模式 | 備註 |
|---------|-----------|------|
| 2000×3000 | ~0.8s | M1 Mac 估算值 |

*v0.7.0+ 所有處理皆使用物理模式*

### 向後相容性 Backward Compatibility

- ✅ **預設物理模式**: v0.7.0+ 所有膠片使用 `PhysicsMode.PHYSICAL`
- ✅ **所有膠片相容**: 13 款膠片配置全部支援物理模式
- ✅ **API 穩定**: 函數簽名不變
- ✅ **測試覆蓋**: 155/155 核心測試通過 (100%)

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

### 未來計畫 Future Plans
- 🔲 P1-1: PSF 波長依賴 & Mie 查表整合
- 🔲 P1-3: 光譜敏感度升級（3 通道 → 31 通道）
- 🔲 參數預設集系統（Fine/Balanced/Strong）
- 🔲 視覺對比工具（參數前後並排對比）
- 🔲 CLI 命令列工具
- 🔲 行動裝置 UI 優化

詳細計畫參見 `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md`  
已完成任務參見 `archive/completed_tasks/` (17 個任務)  
完整版本歷史參見 [`VERSION_HISTORY.md`](VERSION_HISTORY.md)

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
