# Phos - 基于计算光学的胶片模拟

**Current Version: 0.3.0 (Physical Mode UI Integration)** 🚀  
**Stable Version: 0.2.0 (Batch Processing + Modern UI)** ✅

## 综述 General

你说的对，但是 Phos. 是基于「计算光学」概念的胶片模拟。通过计算光在底片上的行为，复现自然、柔美、立体的胶片质感。

**"No LUTs, we calculate LUX."**

Hello! Phos is a film simulation app based on the idea of "Computational Optical Imaging". By calculating the optical effects on the film, we reproduce the natural, soft, and elegant tone of these classical films.

这是一个原理验证demo，图像处理部分基于 OpenCV，交互基于 Streamlit 平台制作，部分代码使用了 AI 辅助生成。

This is a demo for idea testing. The image processing part is based on OpenCV, and the interaction is built on the Streamlit platform. Some of the code was generated with the assistance of AI.

如果您发现了项目中的问题，或是有更好的想法想要分享，还请通过邮箱 lyco_p@163.com 与我联系，我将不胜感激。

If you find any issues in the project or have better ideas you would like to share, please contact me via email at lyco_p@163.com. I would be very grateful.

---

## ✨ v0.3.0 新特性 What's New in v0.3.0

### 🎛️ 物理模式 UI 整合 Physical Mode UI Integration
- **渲染模式選擇器**: 在側邊欄一鍵切換 Artistic / Physical / Hybrid 模式
- **參數控制面板**: 三個可折疊區塊（Bloom / H&D Curve / Grain），提供即時參數調整
- **智能顯示**: Artistic 模式不顯示物理參數，保持介面簡潔
- **固定圖片尺寸**: 單張處理 800px，批次預覽 200px，優化檢視體驗
- **向後相容**: 默認 Artistic 模式，完全不影響現有用戶工作流程

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

詳見下方「[物理模式使用指南](#-物理模式-physical-mode-實驗性)」和 `UI_INTEGRATION_SUMMARY.md`

---

## ✨ v0.2.0 新特性 What's New in v0.2.0

### 📦 批量处理 Batch Processing
- **多文件上传**: 一次处理 2-50 张照片 (Multi-file upload: Process 2-50 photos at once)
- **实时进度**: 进度条 + 状态更新 (Real-time progress: Progress bar + status updates)
- **ZIP 下载**: 一键下载所有结果 (ZIP download: One-click download all results)
- **错误隔离**: 单张失败不影响其他 (Error isolation: Single failure won't affect others)

### 🎨 现代化 UI Modern UI Redesign
- **简洁设计**: 精简 CSS，提升性能 (Clean design: Streamlined CSS, better performance)
- **深色主题**: 珊瑚红配色方案 (Dark theme: Coral red color scheme)
- **流畅交互**: 统一动画与反馈 (Smooth interaction: Consistent animations and feedback)
- **响应式布局**: 清晰的视觉层次 (Responsive layout: Clear visual hierarchy)

### 🔬 物理模式 Physical Mode (v0.2.0 引入)
- **能量守恒**: 光学效果遵守能量守恒定律（误差 < 0.01%）
- **H&D 曲线**: Hurter-Driffield 特性曲线（对数响应 + Toe/Shoulder）
- **泊松颗粒**: 基于光子统计的物理噪声（SNR ∝ √曝光量）
- **三种模式**: Artistic（默认，视觉导向）/ Physical（物理准确）/ Hybrid（混合）
- **UI 支持**: v0.3.0 已完整支援 UI 參數調整 ✅

详见下方「[物理模式使用指南](#-物理模式-physical-mode-实验性)」章节

---

## ✨ v0.1.3 新特性 What's New in v0.1.3

### 🎬 新增胶片 New Films (4)
- **Portra400** - 人像王者，细腻颗粒，柔和色调 (Portrait king, fine grain, soft tones)
- **Ektar100** - 风景利器，超细颗粒，高饱和度 (Landscape master, ultra-fine grain, high saturation)
- **HP5Plus400** - 经典黑白，明显颗粒，高对比 (Classic B&W, prominent grain, high contrast)
- **Cinestill800T** - 电影感，强烈光晕，高感光度 (Cinematic feel, strong halation, high sensitivity)

### ⚡ 性能优化 Performance Optimization
- **缓存机制**: 胶片配置加载速度提升 100% (Caching: 100% speedup for film profile loading)
- **并行处理**: 彩色胶片处理速度提升 30-40% (Parallel processing: 30-40% speedup for color films)
- **内存优化**: 内存占用减少 20-30% (Memory optimization: 20-30% reduction)

### 🧪 测试框架 Testing Framework
- 完整的 pytest 测试套件 (Full pytest test suite)
- 数值稳定性验证 (Numerical stability validation)
- 性能基准测试 (Performance benchmarks)

详见 `V0.1.3_RELEASE.md` 和 `OPTIMIZATION_REPORT.md`

See `V0.1.3_RELEASE.md` and `OPTIMIZATION_REPORT.md` for details

---

## 🎞️ 胶片库 Film Library (7 films)

**彩色胶片 Color Films:**
- NC200 (Fuji C200 inspired) - 日系清新
- Portra400 (Kodak Portra 400 inspired) - 人像专用 🆕
- Ektar100 (Kodak Ektar 100 inspired) - 风景首选 🆕
- Cinestill800T (CineStill 800T inspired) - 电影质感 🆕

**黑白胶片 B&W Films:**
- AS100 (Fuji ACROS inspired) - 细腻黑白
- HP5Plus400 (Ilford HP5+ 400 inspired) - 街拍经典 🆕
- FS200 - 高反差概念验证

---

## 🚀 快速开始 Quick Start

### 安装依赖 Install Dependencies
```bash
pip install -r requirements.txt
```

### 运行应用 Run Application

**v0.3.0 (最新 Latest - Physical Mode UI)**
```bash
streamlit run Phos_0.3.0.py
```

**v0.2.0 (稳定版 Stable - Batch Processing)**
```bash
streamlit run Phos_0.2.0.py
```

### 运行测试 Run Tests
```bash
# 完整測試套件（26 項測試）
pytest tests/

# 個別測試模組
python3 tests/test_energy_conservation.py  # 能量守恆（5 項）
python3 tests/test_hd_curve.py             # H&D 曲線（8 項）
python3 tests/test_poisson_grain.py        # 泊松顆粒（7 項）
python3 tests/test_integration.py          # 整合測試（6 項）
```

---

## 依赖 Requirements

本项目基于 Python 3.13 编写

This project is based on Python 3.13

### 核心依赖 Core Dependencies
```
numpy                     2.2.6
opencv-python             4.12.0.88
streamlit                 1.51.0
pillow                    12.0.0
```

### 开发/测试依赖 Development/Testing Dependencies
```
pytest                    >=7.0.0
pytest-cov               >=4.0.0
pytest-benchmark         >=4.0.0
psutil                   >=5.9.0
```

兼容性尚不明确，如果运行出现问题，请以此处标明的依赖为准。

Compatibility is not yet clear. If any issues occur during operation, please refer to the dependencies listed here.

完整依赖列表见 `requirements.txt`

Full dependency list available in `requirements.txt`

---

## 📁 项目结构 Project Structure

```
Phos/
├── 🚀 v0.3.0 (Latest - Physical Mode UI)
│   ├── Phos_0.3.0.py                      # 主应用 (物理模式 UI)
│   ├── UI_INTEGRATION_SUMMARY.md          # UI 整合文件
│   └── PHYSICAL_MODE_GUIDE.md             # 物理模式指南
│
├── ✅ v0.2.0 (Stable - Batch Processing)
│   ├── phos_batch.py                      # 批量处理模块
│   └── phos_core.py                       # 核心处理模块
│
├── 🧪 Tests & Core
│   ├── tests/                             # Pytest 测试套件 (26 项)
│   │   ├── conftest.py
│   │   ├── test_film_models.py
│   │   ├── test_performance.py
│   │   ├── test_energy_conservation.py    # 能量守恆測試 (5 項)
│   │   ├── test_hd_curve.py               # H&D 曲線測試 (8 項)
│   │   ├── test_poisson_grain.py          # 泊松顆粒測試 (7 項)
│   │   └── test_integration.py            # 整合測試 (6 項)
│   ├── film_models.py                     # 胶片参数 (7 款)
│   └── PHYSICS_REVIEW.md                  # 物理審查報告 (30 頁)
│
├── 📋 Project Context
│   ├── context/
│   │   ├── context_session_*.md           # 開發會話記錄
│   │   └── decisions_log.md               # 技術決策日誌
│   └── tasks/                             # 任務追蹤
│
├── ⚙️ Configuration
│   ├── .streamlit/config.toml             # Streamlit 配置
│   ├── requirements.txt                   # 依赖清单
│   └── .python-version                    # Python 版本
│
└── 📚 Documentation
    ├── README.md                          # 项目说明
    ├── LICENSE                            # AGPL-3.0 许可
    └── OPTIMIZATION_REPORT.md             # 優化報告
```

---

## 许可证 License

本项目采用 **AGPL-3.0** 许可证。

This project is licensed under **AGPL-3.0**.

### 你可以 You may:
- ✅ 自由使用、研究、修改源代码 (Freely use, study, and modify the source code)
- ✅ 用于个人或教育项目 (Use for personal or educational projects)
- ✅ 用于开源项目（同样遵循 AGPL）(Use for open source projects, also following AGPL)

### 你必须 You must:
- 📝 公开任何基于本项目的修改代码 (Publicly release any modified code based on this project)
- 📝 保留原作者版权声明 (Preserve the original author's copyright notice)
- 📝 同样采用 AGPL 许可证分发衍生作品 (Distribute derivative works under the same AGPL license)

### 商业使用 Commercial Use
商业使用请联系作者获取授权。

For commercial use, please contact the author for authorization.

完整许可证条款见 `LICENSE` 文件。

Full license terms are available in the `LICENSE` file.

---

## 🔬 物理模式 Physical Mode (实验性)

v0.2.0 引入了**物理导向模式**，在保留艺术效果的同时，提供更符合物理规律的模拟选项。

v0.2.0 introduces **Physics-oriented Mode**, offering more physically accurate simulation options while preserving artistic effects.

### 三种渲染模式 Three Rendering Modes

| 模式 Mode | 特点 Features | 适用场景 Use Cases |
|----------|--------------|------------------|
| **ARTISTIC** (默认) | 视觉优先，能量可增加，中调颗粒峰值 | 日常照片处理，追求美感 |
| **PHYSICAL** | 物理准确，能量守恒，H&D曲线，泊松噪声 | 科学可视化，物理研究 |
| **HYBRID** | 混合配置，可选开启物理特性 | 自定义艺术与物理平衡 |

### 核心物理特性 Core Physical Features

#### 1. 能量守恒光晕 Energy-Conserving Bloom
- **原理**: 点扩散函数（PSF）正规化：∫ PSF = 1
- **效果**: 高光溢出不增加总能量，更真实的光学散射
- **测试**: 能量误差 < 0.01%（艺术模式 +10%）

#### 2. H&D 特性曲线 Hurter-Driffield Curve
- **原理**: 密度-对数曝光关系：D = γ × log₁₀(H) + D_fog
- **效果**: 
  - Toe 曲线：阴影柔和压缩
  - Linear region：对比度由 gamma 控制
  - Shoulder 曲线：高光渐进饱和
- **动态范围**: 10^8 → 10^3（压缩 5.2×10^4 倍）

#### 3. 泊松颗粒噪声 Poisson Grain Noise
- **原理**: 光子计数统计，Poisson(λ) where λ = 曝光量
- **效果**: 
  - 暗部噪声明显（低 SNR）
  - 亮部噪声抑制（高 SNR）
  - SNR ∝ √曝光量（物理正确）
- **对比**: 艺术模式中调峰值 vs 物理模式暗部峰值

### 代码示例 Code Example

```python
from film_models import get_film_profile, PhysicsMode
import importlib.util

# 加载 Phos 模块
spec = importlib.util.spec_from_file_location("phos", "Phos_0.2.0.py")
phos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phos)

# 加载底片配置
film = get_film_profile("NC200")

# ========== 方式 1: 纯物理模式 ==========
film.physics_mode = PhysicsMode.PHYSICAL

# Bloom 配置（能量守恒）
film.bloom_params.enabled = True
film.bloom_params.mode = "physical"         # 物理模式
film.bloom_params.threshold = 0.8           # 高光阈值
film.bloom_params.scattering_ratio = 0.1    # 散射能量比例

# H&D 曲线配置
film.hd_curve_params.enabled = True
film.hd_curve_params.gamma = 0.65           # 负片 gamma（0.6-0.7）
film.hd_curve_params.D_min = 0.1            # 最小密度（雾度）
film.hd_curve_params.D_max = 3.0            # 最大密度（饱和）
film.hd_curve_params.toe_strength = 2.0     # Toe 曲线强度
film.hd_curve_params.shoulder_strength = 1.5 # Shoulder 曲线强度

# 泊松颗粒配置
film.grain_params.enabled = True
film.grain_params.mode = "poisson"          # 泊松模式
film.grain_params.grain_size = 1.5          # 颗粒尺寸（μm 等效）
film.grain_params.intensity = 0.8           # 噪声强度

# ========== 方式 2: 混合模式 ==========
film.physics_mode = PhysicsMode.HYBRID

# 可选择性启用物理特性
film.bloom_params.mode = "physical"         # Bloom 用物理
film.grain_params.mode = "artistic"         # 颗粒用艺术
film.hd_curve_params.enabled = True         # 启用 H&D 曲线

# ========== 处理影像 ==========
import cv2
image = cv2.imread("input.jpg")

# 1. 光谱响应计算（替代原 luminance 函数）
response_r, response_g, response_b, response_total = phos.spectral_response(image, film)

# 2. 光学处理（Bloom + Grain + H&D + Tone Mapping）
result = phos.optical_processing(
    response_r, response_g, response_b, response_total,
    film,
    grain_style="auto",    # 自动选择颗粒风格
    tone_style="filmic"    # 电影式色调映射
)

# 3. 保存结果
cv2.imwrite("output_physical.jpg", result)
```

### 参数调整指南 Parameter Tuning Guide

#### Bloom 参数 Bloom Parameters
```python
# 高光提取阈值（0-1）
bloom_params.threshold = 0.8
# 较低值 (0.6): 更多高光参与散射，光晕更明显
# 较高值 (0.9): 仅极亮区域散射，光晕更集中

# 散射能量比例（0-1，仅物理模式）
bloom_params.scattering_ratio = 0.1
# 较低值 (0.05): 轻微光晕，更自然
# 较高值 (0.3): 强烈光晕，电影感
```

#### H&D 曲线参数 H&D Curve Parameters
```python
# Gamma（对比度）
hd_curve_params.gamma = 0.65
# 负片: 0.6-0.7（低对比，宽容度高）
# 正片: 1.5-2.0（高对比，鲜艳）

# Toe 强度（阴影压缩）
hd_curve_params.toe_strength = 2.0
# 较低值 (1.0): 阴影更暗，对比强
# 较高值 (3.0): 阴影提亮，柔和

# Shoulder 强度（高光压缩）
hd_curve_params.shoulder_strength = 1.5
# 较低值 (1.0): 高光更早饱和
# 较高值 (2.5): 高光渐进，细节保留
```

#### 泊松颗粒参数 Poisson Grain Parameters
```python
# 颗粒尺寸（μm 等效）
grain_params.grain_size = 1.5
# ISO 100: 0.5-1.0（细腻）
# ISO 400: 1.0-2.0（明显）
# ISO 1600: 2.0-3.0（粗糙）

# 噪声强度（0-2）
grain_params.intensity = 0.8
# 较低值 (0.3): 轻微颗粒感
# 较高值 (1.5): 强烈颗粒感
```

### 测试验证 Test Verification

```bash
# 运行完整测试套件（26 项测试）
python3 tests/test_energy_conservation.py  # 5/5 能量守恒
python3 tests/test_hd_curve.py             # 8/8 H&D 曲线
python3 tests/test_poisson_grain.py        # 7/7 泊松颗粒
python3 tests/test_integration.py          # 6/6 整合测试
```

### 技术文档 Technical Documentation

- **物理审查报告**: `PHYSICS_REVIEW.md`（30 页完整分析）
- **决策日志**: `context/decisions_log.md`（所有技术决策记录）
- **测试报告**: `tests/` 目录（26 项单元/整合测试）

### 已知限制 Known Limitations

1. **H&D 曲线**: 使用简化过渡函数（非严格 Hurter-Driffield 模型）
2. **泊松噪声**: λ < 20 时使用正态近似（精度略降）
3. **Bloom PSF**: 经验 Gaussian/Exponential（非完整 Mie 散射）
4. **批次處理**: 尚未整合物理模式參數（單張處理已支援）✅

### 效能表现 Performance

| 影像尺寸 | 艺术模式 | 物理模式 | 开销 |
|---------|---------|---------|------|
| 2000×3000 | ~0.7s | ~0.8s | +8% |

*测试环境: Python 3.13, M1 Mac (估算值)*

### 向后兼容性 Backward Compatibility

- ✅ **默认行为不变**: 未明确设置时，使用 `ARTISTIC` 模式
- ✅ **所有底片兼容**: 7 款底片配置全部支持物理模式
- ✅ **API 稳定**: 函数签名不变（仅内部命名优化）
- ✅ **测试覆盖**: 100%（26/26 tests passed）

### 下一步计划 Next Steps

- ✅ Streamlit UI 物理模式开关（v0.3.0 已完成）
- 🔲 批次處理物理模式整合（v0.3.1）
- 🔲 參數預設集功能（Fine / Balanced / Strong）
- 🔲 视觉对比工具（Artistic vs Physical 並排）
- 🔲 更多 PSF 模型（Mie 散射、Halation 分离）
- 🔲 自定义 H&D 曲线导入（YAML/JSON）

---

## 作者 Author

由 **@LYCO6273** 开发

Developed by **@LYCO6273**

🔗 **GitHub**: https://github.com/LYCO6273/Phos  
📧 **Email**: lyco_p@163.com

---

## 🗺️ 开发路线图 Roadmap

### v0.3.0 ✅ (当前版本 Current)
- ✅ 物理模式 UI 整合 (Physical Mode UI Integration)
- ✅ 渲染模式切換器 (Rendering Mode Selector: Artistic/Physical/Hybrid)
- ✅ 參數調整面板 (Parameter Adjustment Panels: Bloom/H&D/Grain)
- ✅ 智能顯示邏輯 (Conditional Display Logic)
- ✅ 固定圖片尺寸 (Fixed Image Preview Sizes: 800px/200px)

### v0.2.0 ✅ (稳定版 Stable)
- ✅ 批量处理模式 (Batch processing mode)
- ✅ 物理模式核心 (Physical Mode Core: Energy/H&D/Poisson)
- ✅ 完整測試框架 (26 項測試，100% 通過)
- ✅ 现代化 UI 设计 (Modern UI redesign)

### v0.1.3 ✅ (優化版 Optimization)
- ✅ 性能优化 (缓存 + 并行 + 内存优化)
- ✅ 新增 4 款胶片 (Portra400, Ektar100, HP5+, Cinestill800T)
- ✅ 完整测试框架 (Pytest suite)

### v0.3.1 (计划中 Planned)
- 🔲 批次處理物理模式整合 (Batch Processing Physics Integration)
- 🔲 參數預設集 (Parameter Presets: Fine/Balanced/Strong)
- 🔲 視覺對比工具 (Visual Comparison: Side-by-side Artistic/Physical)

### v0.4.0 (未来 Future)
- 🔲 自定义胶片参数系统 (Custom Film Parameters: YAML/JSON)
- 🔲 更多 PSF 模型 (Advanced PSF Models: Mie Scattering)
- 🔲 实时预览优化 (Real-time Preview Optimization)
- 🔲 CLI 命令行工具 (CLI Tool)

---

## 🙏 致谢 Acknowledgments

感谢所有为本项目提供反馈和建议的用户。

Thanks to all users who provided feedback and suggestions for this project.

本项目受到以下经典胶片的启发：
- Fuji C200, ACROS 100
- Kodak Portra 400, Ektar 100
- Ilford HP5 Plus 400
- CineStill 800T

---

## 📞 联系与支持 Contact & Support

如果你喜欢这个项目，请给它一个 ⭐ Star！

If you like this project, please give it a ⭐ Star!

遇到问题？请通过以下方式联系：

Having issues? Contact via:
- 📧 Email: lyco_p@163.com
- 🐛 GitHub Issues: https://github.com/LYCO6273/Phos/issues

---

**Made with ❤️ by @LYCO6273**
