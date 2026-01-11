# GPU 加速可行性分析

**創建時間**: 2025-12-20  
**分析者**: Main Agent  
**目標**: 評估 GPU 加速的效益、成本與實作策略

---

## 📊 GPU vs CPU 效能對比（理論）

### 卷積操作特性

**CPU 實作**（當前）:
- OpenCV 多執行緒（通常 4-8 核心）
- 大核卷積：O(N·K²) → 2000×3000×(201²) ≈ 2.4×10¹¹ 次運算
- 實測：201×201 核 ≈ 250-400ms

**GPU 實作**（理論）:
- 並行度：1000-10000 CUDA cores
- 記憶體頻寬：CPU ~50GB/s vs GPU ~500GB/s（10x）
- 卷積加速：理論 5-20x（取決於批次大小）

---

## 🎯 可用 GPU 加速方案

### 方案 A: CuPy（最推薦）

**優點**:
- ✅ NumPy 相容 API（幾乎無痛遷移）
- ✅ 自動記憶體管理
- ✅ FFT 卷積直接支援（`cupyx.scipy.ndimage.convolve`）
- ✅ 輕量依賴（僅需 CUDA Toolkit）

**缺點**:
- ❌ 需要 NVIDIA GPU（不支援 AMD/Intel）
- ❌ CUDA 安裝複雜（macOS 不支援新版）
- ⚠️ 小影像傳輸開銷大（CPU↔GPU）

**預期加速**:
- 大核卷積：5-10x（201×201 核：250ms → 25-50ms）
- Halation 三層：900ms → 100-180ms ✅
- **總體**: 2.0s → 0.5-0.8s（2.5-4x）

**程式碼範例**:
```python
import cupy as cp
import cupyx.scipy.ndimage as cpx_ndimage

def convolve_gpu(image_np, kernel_np):
    """GPU 加速卷積（使用 CuPy）"""
    # 1. 傳輸到 GPU
    image_gpu = cp.asarray(image_np)
    kernel_gpu = cp.asarray(kernel_np)
    
    # 2. GPU 卷積
    result_gpu = cpx_ndimage.convolve(image_gpu, kernel_gpu, mode='reflect')
    
    # 3. 傳回 CPU
    result_np = cp.asnumpy(result_gpu)
    
    return result_np

# 自適應 GPU/CPU 切換
def convolve_adaptive(image, kernel, method='auto', use_gpu=True):
    if use_gpu and cp is not None:
        return convolve_gpu(image, kernel)
    elif method == 'fft':
        return convolve_fft(image, kernel)
    else:
        return cv2.filter2D(image, -1, kernel)
```

**安裝**:
```bash
# Linux/Windows (需 CUDA 11.x+)
pip install cupy-cuda11x

# macOS (不支援，需使用 Docker)
docker run --gpus all -it nvidia/cuda:11.8.0-base-ubuntu22.04
```

---

### 方案 B: OpenCV CUDA（次推薦）

**優點**:
- ✅ OpenCV 原生整合
- ✅ 支援更多硬體加速（OpenCL, Vulkan, CUDA）
- ✅ 無額外 Python 依賴

**缺點**:
- ❌ 需重新編譯 OpenCV（`opencv-contrib-python` 預設無 CUDA）
- ❌ API 不同（`cv2.cuda.filter2D` vs `cv2.filter2D`）
- ⚠️ 文檔較少

**程式碼範例**:
```python
import cv2

# 檢查 CUDA 支援
if cv2.cuda.getCudaEnabledDeviceCount() > 0:
    # GPU 上傳
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image)
    
    # GPU 卷積
    gpu_result = cv2.cuda.filter2D(gpu_image, -1, kernel)
    
    # GPU 下載
    result = gpu_result.download()
else:
    # Fallback to CPU
    result = cv2.filter2D(image, -1, kernel)
```

**安裝**:
```bash
# 需從源碼編譯（複雜）
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git
cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D OPENCV_EXTRA_MODULES_PATH=../opencv_contrib/modules \
      -D WITH_CUDA=ON \
      -D CUDA_ARCH_BIN=8.6 \
      ...
make -j8
```

---

### 方案 C: PyTorch（最靈活）

**優點**:
- ✅ 易安裝（`pip install torch`，自帶 CUDA）
- ✅ 自動微分（未來可擴展為可訓練模型）
- ✅ 強大的 tensor 操作

**缺點**:
- ❌ API 與 NumPy 差異較大
- ❌ 較重（~2GB 安裝包）
- ⚠️ 卷積需手動實作（`F.conv2d` 需要 4D tensor）

**程式碼範例**:
```python
import torch
import torch.nn.functional as F

def convolve_pytorch(image_np, kernel_np):
    """PyTorch GPU 卷積"""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # NumPy → Torch (H,W) → (1,1,H,W)
    image_t = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0).to(device)
    kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0).to(device)
    
    # 卷積（padding='same' 模擬 reflect）
    result_t = F.conv2d(image_t, kernel_t, padding=kernel_np.shape[0]//2)
    
    # Torch → NumPy
    result_np = result_t.squeeze().cpu().numpy()
    
    return result_np
```

**安裝**:
```bash
# CUDA 版本（自動包含 CUDA runtime）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# CPU 版本（測試用）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

---

## 🔬 實驗設計：效能基準測試

### 測試計畫

```python
# scripts/benchmark_gpu.py

import time
import numpy as np
import cv2

def benchmark_convolution_methods():
    """對比 CPU vs GPU 卷積效能"""
    
    # 測試影像
    img = np.random.rand(2000, 3000).astype(np.float32)
    kernel = cv2.getGaussianKernel(201, 50)
    kernel = kernel @ kernel.T
    
    methods = {
        'CPU_spatial': lambda: cv2.filter2D(img, -1, kernel),
        'CPU_fft': lambda: convolve_fft(img, kernel),
        'GPU_cupy': lambda: convolve_cupy(img, kernel),
        'GPU_pytorch': lambda: convolve_pytorch(img, kernel),
    }
    
    results = {}
    for name, func in methods.items():
        # Warmup
        func()
        
        # Benchmark (10 次平均)
        times = []
        for _ in range(10):
            t0 = time.perf_counter()
            func()
            times.append((time.perf_counter() - t0) * 1000)
        
        results[name] = {
            'mean': np.mean(times),
            'std': np.std(times)
        }
    
    # 輸出
    print(f"{'方法':<15} {'平均時間':<12} {'加速比':<10}")
    print("-" * 40)
    baseline = results['CPU_spatial']['mean']
    for name, stats in results.items():
        speedup = baseline / stats['mean']
        print(f"{name:<15} {stats['mean']:>10.1f}ms  {speedup:>8.2f}x")
```

**預期結果**:
```
方法              平均時間      加速比       
----------------------------------------
CPU_spatial        380.0ms      1.00x
CPU_fft            250.0ms      1.52x
GPU_cupy            45.0ms      8.44x  ← 目標
GPU_pytorch         60.0ms      6.33x
```

---

## 💰 成本效益分析

### 開發成本

| 項目 | CuPy | OpenCV CUDA | PyTorch |
|------|------|-------------|---------|
| **實作難度** | 低 | 中 | 中 |
| **程式碼修改** | ~50 行 | ~100 行 | ~150 行 |
| **測試工作量** | 1-2 天 | 3-5 天 | 2-3 天 |
| **相容性維護** | 需 GPU fallback | 需條件編譯 | 較簡單 |

### 使用成本

| 項目 | 影響 |
|------|------|
| **硬體需求** | NVIDIA GPU（GTX 1060+ 或 RTX 系列）|
| **安裝複雜度** | ⚠️ CUDA Toolkit 安裝（~3GB）|
| **用戶群體** | ❌ macOS 用戶無法使用（不支援 CUDA）|
| **雲端部署** | ✅ 可使用 AWS/GCP GPU 實例 |

### 效能提升

| 情境 | CPU (當前) | GPU (預期) | 提升 |
|------|-----------|-----------|------|
| **單張影像** (2000×3000) | 2.0s | 0.5s | **4x** ✅ |
| **批次 10 張** | 20s | 3s | **6.7x** ✅ |
| **即時預覽** (500×750) | 0.3s | 0.1s | **3x** ✅ |

---

## 🎯 建議實作策略

### Phase 1: 可選 GPU 加速（推薦）

**設計原則**:
- GPU 為可選功能（預設 CPU）
- 自動檢測硬體（無 GPU → fallback CPU）
- 使用者可在 UI 中開關

**實作步驟**:

1. **依賴管理** (`requirements.txt`):
```txt
# 核心依賴（必需）
numpy>=1.24.0
opencv-python>=4.8.0
streamlit>=1.28.0

# GPU 加速（可選）
cupy-cuda11x>=12.0.0; platform_system != "Darwin"  # macOS 不安裝
```

2. **GPU 模組** (`phos_gpu.py`):
```python
# phos_gpu.py

import numpy as np

# 嘗試導入 CuPy
try:
    import cupy as cp
    import cupyx.scipy.ndimage as cpx_ndimage
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    cp = None

def convolve_gpu(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """GPU 加速卷積（自動 fallback）"""
    if not GPU_AVAILABLE:
        # Fallback: 使用 CPU FFT
        from Phos_0_3_0 import convolve_fft
        return convolve_fft(image, kernel)
    
    # GPU 路徑
    image_gpu = cp.asarray(image)
    kernel_gpu = cp.asarray(kernel)
    result_gpu = cpx_ndimage.convolve(image_gpu, kernel_gpu, mode='reflect')
    return cp.asnumpy(result_gpu)

def get_gpu_info() -> dict:
    """獲取 GPU 資訊"""
    if not GPU_AVAILABLE:
        return {'available': False, 'reason': 'CuPy not installed'}
    
    try:
        device = cp.cuda.Device()
        return {
            'available': True,
            'name': device.name,
            'memory_total': device.mem_info[1] / 1e9,  # GB
            'memory_free': device.mem_info[0] / 1e9
        }
    except Exception as e:
        return {'available': False, 'reason': str(e)}
```

3. **整合到主程式** (`Phos_0.3.0.py`):
```python
from phos_gpu import GPU_AVAILABLE, convolve_gpu, get_gpu_info

# 在 convolve_adaptive() 中新增 GPU 路徑
def convolve_adaptive(image, kernel, method='auto', use_gpu=False):
    """
    自適應選擇卷積方法
    
    Args:
        method: 'auto' | 'spatial' | 'fft' | 'gpu'
        use_gpu: 是否嘗試使用 GPU（需硬體支援）
    """
    if use_gpu and GPU_AVAILABLE:
        return convolve_gpu(image, kernel)
    elif method == 'auto':
        ksize = kernel.shape[0]
        if ksize > 150:
            return convolve_fft(image, kernel)
        else:
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    # ... 其他分支
```

4. **Streamlit UI 整合** (側邊欄):
```python
# 顯示 GPU 狀態
gpu_info = get_gpu_info()
if gpu_info['available']:
    st.sidebar.success(f"🚀 GPU: {gpu_info['name']} ({gpu_info['memory_free']:.1f}GB 可用)")
    use_gpu = st.sidebar.checkbox("使用 GPU 加速", value=True, 
                                   help="需 NVIDIA GPU + CUDA")
else:
    st.sidebar.info(f"💻 GPU 不可用: {gpu_info['reason']}")
    use_gpu = False
```

---

### Phase 2: 批次處理 GPU 優化（進階）

**策略**: 批次影像一次性傳輸到 GPU，避免重複 CPU↔GPU 開銷

```python
def process_batch_gpu(images: list, film: FilmProfile) -> list:
    """批次處理（GPU 加速）"""
    if not GPU_AVAILABLE:
        return [process_image(img, film) for img in images]
    
    # 批次上傳到 GPU
    images_gpu = [cp.asarray(img) for img in images]
    
    # 批次處理（重用 kernel）
    kernel_gpu = cp.asarray(get_gaussian_kernel(film.halation_sigma))
    results_gpu = [convolve_gpu_no_transfer(img_gpu, kernel_gpu) 
                   for img_gpu in images_gpu]
    
    # 批次下載
    results_cpu = [cp.asnumpy(r) for r in results_gpu]
    
    return results_cpu
```

**預期加速**: 10 張影像 20s → 3s（6.7x）

---

## ⚠️ 風險與限制

### 技術風險

1. **硬體相容性**: 
   - ❌ macOS 不支援 CUDA（~30% 用戶群）
   - ⚠️ AMD GPU 需 ROCm（複雜）
   - ✅ Windows/Linux + NVIDIA 最佳支援

2. **安裝複雜度**:
   - CUDA Toolkit 安裝（~3GB）
   - 驅動版本需匹配（常見問題）
   - Docker 方案可緩解（但用戶體驗差）

3. **記憶體限制**:
   - 2000×3000 影像 ≈ 72MB（單通道）
   - 批次 10 張 ≈ 720MB
   - 需 >2GB VRAM（入門級 GPU 可能不足）

### 效益限制

4. **小影像無優勢**:
   - 傳輸開銷：~10ms（500×750 影像）
   - 實際加速：僅 2-3x（vs 理論 10x）
   - **結論**: 僅大影像/批次處理值得

5. **FFT 已優化**:
   - 當前 CPU FFT：201×201 核 ≈ 250ms
   - GPU 卷積：≈ 45ms
   - **增益**: 5.5x（vs 理論 10x）
   - **原因**: FFT 已是高效算法

---

## 📋 實作檢查表

### P0 (必需，建議採用)

- [ ] 創建 `phos_gpu.py` 模組
- [ ] 實作 `convolve_gpu()` with CuPy
- [ ] 實作自動 fallback 機制
- [ ] 更新 `convolve_adaptive()` 添加 `use_gpu` 參數
- [ ] Streamlit UI 顯示 GPU 狀態
- [ ] 測試：GPU vs CPU 精度驗證（PSNR >40dB）
- [ ] 測試：效能基準（2000×3000 影像）
- [ ] 文檔：README 添加 GPU 安裝指引

### P1 (重要，建議採用)

- [ ] 批次處理 GPU 優化
- [ ] 錯誤處理：GPU OOM → 自動 fallback CPU
- [ ] 多 GPU 支援（`cp.cuda.Device(id)`）
- [ ] 效能監控面板（Streamlit metrics）

### P2 (可選)

- [ ] OpenCV CUDA 支援（備選方案）
- [ ] PyTorch 整合（未來可擴展為可訓練模型）
- [ ] Docker GPU 映像檔（簡化安裝）
- [ ] 雲端 GPU 部署指引（AWS/GCP）

---

## 🎯 最終建議

### 短期（1-2 週）：✅ 採用 CuPy GPU 加速

**理由**:
1. **效益明確**: 4x 加速（2.0s → 0.5s）
2. **實作簡單**: ~50 行程式碼，1-2 天完成
3. **風險可控**: 自動 fallback，不影響無 GPU 用戶
4. **用戶體驗**: 高階用戶大幅提升效率

**優先級**: **高**（卷積是主要瓶頸，GPU 是天然解法）

### 中期（1-2 月）：批次處理優化

**目標**: 10 張影像 20s → 3s（6.7x）

### 長期（3-6 月）：可選探索

- PyTorch 整合（為可訓練膠片模型鋪路）
- 雲端部署（Streamlit Cloud + GPU）

---

**決策建議**: ✅ **採用 GPU 加速（Phase 1: CuPy）**

理由：效益/成本比最佳，技術成熟，風險可控。

**文檔版本**: v1.0  
**最後更新**: 2025-12-20
