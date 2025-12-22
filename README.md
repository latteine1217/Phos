# Phos - 基於計算光學的膠片模擬

**Current Version: 0.3.0 (Physical Mode UI Integration)** 🚀  
**Stable Version: 0.2.0 (Batch Processing + Modern UI)** ✅

## 綜述 General

你說的對，但是 Phos 是基於「計算光學」概念的膠片模擬。透過計算光在底片上的行為，重現自然、柔美、立體的膠片質感。

**"No LUTs, we calculate LUX."**

Hello! Phos is a film simulation app based on the idea of "Computational Optical Imaging". By calculating the optical effects on the film, we reproduce the natural, soft, and elegant tone of these classical films.

這是一個原理驗證 demo，影像處理部分基於 OpenCV，互動基於 Streamlit 平台製作，部分程式碼使用了 AI 輔助生成。

This is a demo for idea testing. The image processing part is based on OpenCV, and the interaction is built on the Streamlit platform. Some of the code was generated with the assistance of AI.

如果您發現了專案中的問題，或是有更好的想法想要分享，還請透過郵箱 lyco_p@163.com 與我聯繫，我將不勝感激。

If you find any issues in the project or have better ideas you would like to share, please contact me via email at lyco_p@163.com. I would be very grateful.

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

詳見下方「[物理模式使用指南](#-物理模式-physical-mode-實驗性)」和 `docs/UI_INTEGRATION_SUMMARY.md`

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

詳見下方「[物理模式使用指南](#-物理模式-physical-mode-實驗性)」章節

---

## 🎞️ 膠片庫 Film Library

### 彩色膠片 Color Films (9 款)

| 膠片 | 靈感來源 | ISO | 特色 | 物理模式 |
|------|---------|-----|------|---------|
| **NC200** | Fuji C200 | 200 | 富士經典日系清新 | ✅ Standard |
| **Gold200** | Kodak Gold 200 | 200 | Kodak 日常暖調 | ✅ Standard |
| **Portra400** | Kodak Portra 400 | 400 | 人像王者，T-Grain 技術 | ✅ Fine-Grain |
| **Ektar100** | Kodak Ektar 100 | 100 | 風景利器，極細顆粒 | ✅ Fine-Grain |
| **ProImage100** | Kodak ProImage 100 | 100 | 專業影像，自然色調 | ✅ Fine-Grain |
| **Velvia50** | Fuji Velvia 50 | 50 | 極致飽和，風景之王 | ✅ Fine-Grain |
| **Superia400** | Fuji Superia 400 | 400 | 日常拍攝，明亮色調 | ✅ High-Speed |
| **Cinestill800T** | CineStill 800T | 800 | 電影質感，紅色光暈 | ✅ High-Speed |
| **Portra400 (Mie)** | 實驗配置 | 400 | Mie 散射理論查表 | 🔬 Experimental |

### 黑白膠片 B&W Films (4 款)

| 膠片 | 靈感來源 | ISO | 特色 | 對比度 |
|------|---------|-----|------|--------|
| **AS100** | Fuji ACROS 100 | 100 | 細膩黑白，低顆粒 | 低對比 |
| **HP5Plus400** | Ilford HP5+ 400 | 400 | 街拍經典，明顯顆粒 | 標準 |
| **TriX400** | Kodak Tri-X 400 | 400 | 新聞攝影，經典顆粒 | 標準 |
| **FP4Plus125** | Ilford FP4+ 125 | 125 | 風景黑白，細緻層次 | 標準 |

**備註**：
- ✅ **物理模式**: 所有膠片皆已整合 P1-2 ISO 推導系統
- 🔬 **實驗性**: `Portra400_MediumPhysics_Mie` 使用 Mie 理論查表（P1-1）
- ⚠️ **過時版本**: `Portra400_MediumPhysics` 為測試用途，已被標準版取代

---

## 🚀 快速開始 Quick Start

### 安裝依賴 Install Dependencies
```bash
pip install -r requirements.txt
```

### 執行應用 Run Application

**v0.3.0 (最新 Latest - Physical Mode UI)**
```bash
streamlit run Phos_0.3.0.py
```

**v0.2.0 (穩定版 Stable - Batch Processing)**
```bash
streamlit run Phos_0.2.0.py
```

### 執行測試 Run Tests
```bash
# 完整測試套件（46+ 項測試）
pytest tests/ -v

# P1-2 ISO 推導系統測試
python3 -m pytest tests/test_iso_unification.py -v          # 21 tests
python3 -m pytest tests/test_create_film_from_iso.py -v     # 25 tests

# 物理模式測試
python3 -m pytest tests/test_energy_conservation.py -v      # 5 tests
python3 -m pytest tests/test_hd_curve.py -v                 # 8 tests
python3 -m pytest tests/test_poisson_grain.py -v            # 7 tests
python3 -m pytest tests/test_integration.py -v              # 6 tests
```

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
│   ├── Phos_0.3.0.py                      # v0.3.0 主應用（物理模式 UI）
│   ├── phos_core.py                       # 核心處理模組
│   ├── phos_batch.py                      # 批次處理模組
│   ├── film_models.py                     # 膠片參數配置（13 款膠片）
│   └── color_utils.py                     # 色彩工具函數
│
├── 🧪 測試 Tests
│   ├── tests/                             # Pytest 測試套件
│   │   ├── test_iso_unification.py        # P1-2: ISO 推導測試（21 項）
│   │   ├── test_create_film_from_iso.py   # P1-2: 膠片創建測試（25 項）
│   │   ├── test_energy_conservation.py    # 能量守恆測試（5 項）
│   │   ├── test_hd_curve.py               # H&D 曲線測試（8 項）
│   │   ├── test_poisson_grain.py          # Poisson 顆粒測試（7 項）
│   │   ├── test_integration.py            # 整合測試（6 項）
│   │   ├── test_film_models.py            # 膠片模型測試
│   │   ├── test_performance.py            # 效能基準測試
│   │   └── debug/                         # 偵錯測試腳本
│   └── conftest.py                        # Pytest 配置
│
├── 🔬 資料 Data
│   ├── data/                              # 物理數據檔案
│   │   ├── mie_lookup_table_v2.npz        # Mie 散射查表 v2（200 點）
│   │   ├── film_spectral_sensitivity.npz  # 膠片光譜敏感度
│   │   ├── cie_1931_31points.npz          # CIE 1931 色彩匹配函數
│   │   └── smits_basis_spectra.npz        # RGB→光譜基底
│   └── scripts/                           # 資料生成腳本
│       ├── generate_mie_lookup.py         # 生成 Mie 查表
│       ├── visualize_iso_scaling.py       # P1-2 視覺化驗證
│       └── test_all_films_physical.py     # 全膠片測試
│
├── 📚 文檔 Documentation
│   ├── docs/                              # 技術文檔
│   │   ├── COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md  # 計算光學理論
│   │   ├── PHYSICAL_MODE_GUIDE.md         # 物理模式指南
│   │   ├── UI_INTEGRATION_SUMMARY.md      # UI 整合文檔
│   │   ├── OPTIMIZATION_REPORT.md         # 效能優化報告
│   │   ├── BUGFIX_SUMMARY_20251220.md     # 錯誤修復記錄
│   │   └── FILM_DESCRIPTIONS_FEATURE.md   # 膠片說明功能
│   ├── context/                           # 專案上下文
│   │   ├── context_session_*.md           # 開發會話記錄
│   │   └── decisions_log.md               # 技術決策日誌（16 項決策）
│   └── README.md                          # 本檔案
│
├── 📋 任務 Tasks
│   ├── tasks/                             # 活動任務
│   │   ├── TASK-003-medium-physics/       # P0-2: 中等物理（完成）
│   │   ├── TASK-004-performance-optimization/  # 效能優化研究
│   │   ├── TASK-005-spectral-sensitivity/ # P1-3: 光譜敏感度
│   │   ├── TASK-006-psf-wavelength-mie/   # P1-1: PSF 波長依賴
│   │   ├── TASK-007-physics-enhancement/  # P1 物理增強（進行中）
│   │   └── PHYSICS_IMPROVEMENTS_ROADMAP.md # 物理改進路線圖
│   └── archive/                           # 已完成任務
│       ├── completed_tasks/
│       │   ├── TASK-001-v020-verification/  # v0.2.0 驗證
│       │   ├── TASK-002-physical-improvements/  # P0-2 實施
│       │   ├── P0-2_halation_refactor_plan.md   # Halation 重構
│       │   └── P1-2_iso_unification_plan.md     # ISO 統一計畫
│       └── backups/                       # 程式碼備份
│
├── ⚙️ 配置 Configuration
│   ├── .streamlit/config.toml             # Streamlit 配置
│   ├── requirements.txt                   # Python 依賴
│   ├── .python-version                    # Python 版本（3.13）
│   └── .gitignore                         # Git 忽略規則
│
└── 📄 授權 License
    └── LICENSE                            # AGPL-3.0 授權條款
```

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
- **決策日誌**: `context/decisions_log.md`（16 項技術決策記錄）
- **測試報告**: `tests/` 目錄（46+ 項單元/整合測試）

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

- ✅ P1-2: ISO 統一推導系統（v0.3.0 完成）
- ✅ Mie 散射高密度查表 v2（v0.3.0 Phase 5.5 完成）
- 🔲 P1-1: PSF 波長依賴 & Mie 查表整合
- 🔲 P1-3: 光譜敏感度升級（3 通道 → 31 通道）
- 🔲 視覺驗證 Mie v2 vs 經驗公式差異（UI 測試）
- 🔲 批次處理物理模式整合（v0.3.1）
- 🔲 參數預設集功能（Fine / Balanced / Strong）
- 🔲 視覺對比工具（Artistic vs Physical 並排）
- 🔲 自訂 H&D 曲線匯入（YAML/JSON）

---

## 作者 Author

由 **@LYCO6273** 開發

Developed by **@LYCO6273**

🔗 **GitHub**: https://github.com/LYCO6273/Phos  
📧 **Email**: lyco_p@163.com

---

## 🗺️ 開發路線圖 Roadmap

### v0.3.3 ✅ (當前版本 Current, 2025-12-22)
- ✅ **Phase 1: Mie 散射修正**（Decision #014）
  - 散射機制修正：Rayleigh（λ^-4）→ Mie（λ^-3.5）
  - PSF 寬度修正：λ^-2 → λ^-0.8（小角散射近似）
  - 雙段 PSF 結構：核心（高斯）+ 尾部（指數）
  - 能量/寬度解耦：避免不可辨識性問題
  - 驗證：能量比 B/R = 3.62x ✓，寬度比 = 1.34x ✓
- ✅ **Phase 2: Mie + Halation 整合**
  - 空間尺度分離：Bloom (~40px) vs Halation (80-150px)
  - 波長依賴相反：Bloom (B>R) vs Halation (R>B)
  - 雙光暈結構：內層藍色銳利 + 外層紅色柔和
  - 7/7 整合測試通過
- ✅ **測試修復**（Decision #022）
  - 修復 3 個棄用參數測試失敗
  - 遷移至 Beer-Lambert 新結構
  - 測試通過率：95.6% → 98.8% (+3.2%)
- 📊 **整體進度**：180/183 tests passing, Phase 1 & 2 完成度 64.7%

### v0.3.2 ✅ (2025-12-19)
- ✅ **Halation 獨立建模**（Decision #012）
  - Beer-Lambert 分層穿透率：乳劑 + 基底 + AH 層
  - 波長依賴配置：T_e(R/G/B), T_AH(R/G/B)
  - AH 層效果：CineStill (無 AH) vs Portra (有 AH, 97% 抑制)
  - 物理驗證：f_h(紅) > f_h(綠) > f_h(藍) ✓
  - 6 項 Halation 專項測試通過

### v0.3.0 ✅ (2025-12-20)
- ✅ **P1-2: ISO 統一推導系統**
  - 從 ISO 自動推導顆粒參數
  - 膠片類型分類（fine_grain / standard / high_speed）
  - 物理分數：7.8 → **8.0/10** ⭐
  - 測試覆蓋：45/46 (97.8%)
- ✅ **Phase 5.5: Mie 散射高密度查表 v2**
  - 精度提升：η 插值誤差 155% → 2.16%（72x）
  - 格點密度：21 → 200 點（9.5x）
  - 波長範圍：400-700nm（+50%）
  - 插值速度：0.127 ms → 0.0205 ms（6.2x 更快）
- ✅ 波長依賴散射（經驗公式 & Mie 理論雙選項）
- ✅ Halation 獨立建模（Beer-Lambert 透過率）
- ✅ 物理模式 UI 整合 (Physical Mode UI Integration)
- ✅ 渲染模式切換器 (Rendering Mode Selector: Artistic/Physical/Hybrid)
- ✅ 參數調整面板 (Parameter Adjustment Panels: Bloom/H&D/Grain)
- ✅ 智能顯示邏輯 (Conditional Display Logic)
- ✅ 固定圖片尺寸 (Fixed Image Preview Sizes: 800px/200px)

### v0.2.0 ✅ (穩定版 Stable)
- ✅ 批次處理模式 (Batch processing mode)
- ✅ 物理模式核心 (Physical Mode Core: Energy/H&D/Poisson)
- ✅ 完整測試框架 (26 項測試，100% 通過)
- ✅ 現代化 UI 設計 (Modern UI redesign)

### v0.1.3 ✅ (優化版 Optimization)
- ✅ 效能優化 (快取 + 並行 + 記憶體優化)
- ✅ 新增 4 款膠片 (Portra400, Ektar100, HP5+, Cinestill800T)
- ✅ 完整測試框架 (Pytest suite)

### v0.3.1 (計畫中 Planned)
- 🔲 P1-1: PSF 波長依賴 & Mie 查表整合
- 🔲 P1-3: 光譜敏感度升級（3 通道 → 31 通道）
- 🔲 批次處理物理模式整合 (Batch Processing Physics Integration)
- 🔲 參數預設集 (Parameter Presets: Fine/Balanced/Strong)
- 🔲 視覺對比工具 (Visual Comparison: Side-by-side Artistic/Physical)

### v0.4.0 (未來 Future)
- 🔲 自訂膠片參數系統 (Custom Film Parameters: YAML/JSON)
- 🔲 更多 PSF 模型 (Advanced PSF Models: Full Mie Scattering)
- 🔲 即時預覽優化 (Real-time Preview Optimization)
- 🔲 CLI 命令列工具 (CLI Tool)

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
