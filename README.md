# Phos - 基于计算光学的胶片模拟

**Current Version: 0.1.3 (Optimization Release)** ⚡

## 综述 General

你说的对，但是 Phos. 是基于「计算光学」概念的胶片模拟。通过计算光在底片上的行为，复现自然、柔美、立体的胶片质感。

**"No LUTs, we calculate LUX."**

Hello! Phos is a film simulation app based on the idea of "Computational Optical Imaging". By calculating the optical effects on the film, we reproduce the natural, soft, and elegant tone of these classical films.

这是一个原理验证demo，图像处理部分基于 OpenCV，交互基于 Streamlit 平台制作，部分代码使用了 AI 辅助生成。

This is a demo for idea testing. The image processing part is based on OpenCV, and the interaction is built on the Streamlit platform. Some of the code was generated with the assistance of AI.

如果您发现了项目中的问题，或是有更好的想法想要分享，还请通过邮箱 lyco_p@163.com 与我联系，我将不胜感激。

If you find any issues in the project or have better ideas you would like to share, please contact me via email at lyco_p@163.com. I would be very grateful.

---

## ✨ v0.1.3 新特性 What's New

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
```bash
streamlit run Phos_0.1.3.py
```

### 运行测试 Run Tests
```bash
python3 test_v0.1.3.py
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
├── Phos_0.1.3.py              # 主应用程序 (v0.1.3 优化版)
├── phos_core.py               # 优化核心模块 (并行处理 + 缓存)
├── film_models.py             # 胶片参数定义 (7款胶片)
├── test_v0.1.3.py            # 快速测试脚本
├── tests/                     # Pytest 测试套件
│   ├── conftest.py           # 测试配置
│   ├── test_film_models.py   # 胶片模型测试
│   └── test_performance.py   # 性能基准测试
├── legacy/                    # 旧版本归档
│   └── Phos_0.1.0.py
├── V0.1.3_RELEASE.md         # v0.1.3 发布说明
├── OPTIMIZATION_REPORT.md     # 优化技术报告
└── requirements.txt           # 依赖清单
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

## 作者 Author

由 **@LYCO6273** 开发

Developed by **@LYCO6273**

🔗 **GitHub**: https://github.com/LYCO6273/Phos  
📧 **Email**: lyco_p@163.com

---

## 🗺️ 开发路线图 Roadmap

### v0.1.3 ✅ (当前版本 Current)
- ✅ 性能优化 (缓存 + 并行 + 内存优化)
- ✅ 新增 4 款胶片
- ✅ 完整测试框架

### v0.2.0 (计划中 Planned)
- 🔲 批量处理模式 (Batch processing mode)
- 🔲 进度条显示 (Progress bars)
- 🔲 批量结果 ZIP 下载 (ZIP download for batch results)
- 🔲 高级参数调整界面 (Advanced parameter adjustment UI)
- 🔲 自定义胶片参数系统 (Custom film parameter system - YAML/JSON)

### v0.3.0 (未来 Future)
- 🔲 胶片对比模式 (Film comparison mode)
- 🔲 实时预览优化 (Real-time preview optimization)
- 🔲 更多胶片型号 (More film profiles)
- 🔲 CLI 命令行工具 (CLI tool)

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
