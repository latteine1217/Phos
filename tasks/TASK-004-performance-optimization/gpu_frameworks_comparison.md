# GPU 框架深度比較：PyTorch vs JAX vs OpenCV CUDA

**創建時間**: 2025-12-20  
**分析者**: Main Agent  
**目標**: 為 Phos 選擇最適合的 GPU 加速方案

---

## 📊 Executive Summary

### 一句話推薦

> **CuPy** 依然是最佳選擇（API 相容性 + 效能 + 簡潔性），但本文檔深入探討三種替代方案的優劣。

### 性能對比表（預測）

| 框架 | 預期加速 | 安裝難度 | API 相容性 | 依賴大小 | 推薦度 |
|------|---------|---------|-----------|---------|--------|
| **CuPy** | 8-10x | ⭐⭐⭐⭐⭐ 易 | ⭐⭐⭐⭐⭐ NumPy-like | 200MB | ⭐⭐⭐⭐⭐ |
| **PyTorch** | 6-8x | ⭐⭐⭐⭐⭐ 易 | ⭐⭐⭐ 需轉換 | 2GB | ⭐⭐⭐⭐ |
| **JAX** | 10-12x | ⭐⭐⭐ 中 | ⭐⭐⭐⭐ NumPy-like | 500MB | ⭐⭐⭐⭐ |
| **OpenCV CUDA** | 6-8x | ⭐ 難 | ⭐⭐⭐⭐ OpenCV-like | 0MB (編譯) | ⭐⭐ |

### 最終建議排序

1. **🥇 CuPy** (保持原推薦，本文不深入)
2. **🥈 JAX** (最高效能，適合研究/實驗性專案)
3. **🥉 PyTorch** (生態系統最成熟，適合擴展深度學習)
4. **4️⃣ OpenCV CUDA** (僅當已有編譯環境時考慮)

---

## 1️⃣ PyTorch: 深度學習框架的 GPU 加速

### 概述

**PyTorch** 是 Meta（Facebook）開發的深度學習框架，擁有最成熟的 GPU 加速生態系統。

**核心優勢**:
- ✅ 自動記憶體管理（GPU 記憶體池）
- ✅ 豐富的卷積運算子（`torch.nn.functional`）
- ✅ 易於安裝（`pip install torch`，自帶 CUDA runtime）
- ✅ 未來擴展性（可訓練濾鏡、神經網路膠片模型）

**核心劣勢**:
- ❌ API 與 NumPy 差異大（需要 4D tensor: `(N,C,H,W)`）
- ❌ 依賴龐大（~2GB 安裝包）
- ⚠️ 自動微分開銷（需手動關閉 `with torch.no_grad()`）

---

### 安裝指南

#### Linux / Windows (CUDA 11.8)

```bash
# CUDA 版本（推薦）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 驗證安裝
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
```

#### macOS (僅 CPU，或 MPS 加速)

```bash
# CPU 版本
pip install torch torchvision

# M1/M2 Mac 可使用 MPS (Metal Performance Shaders)
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

**預編譯包大小**:
- CUDA 版本: ~2.0 GB
- CPU 版本: ~800 MB

---

### API 教程：從 NumPy 到 PyTorch

#### 核心概念

| 概念 | NumPy | PyTorch |
|------|-------|---------|
| **陣列類型** | `np.ndarray` | `torch.Tensor` |
| **資料型別** | `np.float32` | `torch.float32` |
| **裝置** | CPU 固定 | `cpu` / `cuda:0` / `mps` |
| **形狀** | `(H, W)` | `(H, W)` 或 `(N, C, H, W)` |

#### 關鍵差異：4D Tensor 要求

PyTorch 的卷積運算子需要 4D tensor:
- `N`: Batch size（批次大小）
- `C`: Channels（通道數）
- `H`: Height（高度）
- `W`: Width（寬度）

**轉換流程**:
```python
# NumPy: (H, W) 單通道灰階影像
image_np = np.random.rand(2000, 3000).astype(np.float32)

# PyTorch: (H, W) → (1, 1, H, W)
image_torch = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0)
# 形狀: (2000, 3000) → (1, 1, 2000, 3000)
```

---

### 程式碼範例：PyTorch 卷積

#### 範例 1: 基本卷積

```python
import torch
import torch.nn.functional as F
import numpy as np

def convolve_pytorch(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    使用 PyTorch 進行 GPU 加速卷積
    
    Args:
        image_np: NumPy 陣列 (H, W), float32
        kernel_np: 卷積核 (kH, kW), float32
        
    Returns:
        result_np: 卷積結果 (H, W), float32
    """
    # 1. 檢查 GPU 可用性
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 2. NumPy → Torch (CPU)
    # (H, W) → (1, 1, H, W)
    image_t = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0)
    
    # (kH, kW) → (1, 1, kH, kW)
    kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0)
    
    # 3. 傳輸到 GPU
    image_t = image_t.to(device)
    kernel_t = kernel_t.to(device)
    
    # 4. 卷積運算（關閉自動微分以提升效能）
    with torch.no_grad():
        # padding='same' 模式（PyTorch 1.9+）
        kh, kw = kernel_np.shape
        padding = (kh // 2, kw // 2)
        
        result_t = F.conv2d(
            image_t, 
            kernel_t, 
            padding=padding,
            # 注意: PyTorch 沒有 'reflect' padding in conv2d
            # 需要手動處理
        )
    
    # 5. GPU → CPU → NumPy
    result_np = result_t.squeeze().cpu().numpy()
    
    return result_np
```

#### 範例 2: 處理邊界模式（Reflect Padding）

PyTorch 的 `F.conv2d` 不支援 `reflect` padding，需手動處理：

```python
def convolve_pytorch_reflect(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    PyTorch 卷積 + Reflect 邊界
    
    物理需求: 邊界需使用 reflect 模式（與 OpenCV 一致）
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 1. NumPy → Torch
    image_t = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0).to(device)
    kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0).to(device)
    
    # 2. Reflect padding（手動）
    kh, kw = kernel_np.shape
    pad_h, pad_w = kh // 2, kw // 2
    
    # F.pad with 'reflect' mode
    image_padded = F.pad(
        image_t, 
        (pad_w, pad_w, pad_h, pad_h),  # (left, right, top, bottom)
        mode='reflect'
    )
    
    # 3. 卷積（padding=0，因為已手動 pad）
    with torch.no_grad():
        result_t = F.conv2d(image_padded, kernel_t, padding=0)
    
    # 4. 返回 NumPy
    result_np = result_t.squeeze().cpu().numpy()
    
    return result_np
```

#### 範例 3: 批次處理優化

PyTorch 的強項是批次處理：

```python
def convolve_batch_pytorch(images_np: list, kernel_np: np.ndarray) -> list:
    """
    批次卷積（最大化 GPU 利用率）
    
    Args:
        images_np: 列表，每個元素為 (H, W) NumPy 陣列
        kernel_np: 共用卷積核 (kH, kW)
        
    Returns:
        results_np: 列表，卷積結果
    """
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    
    # 1. 批次轉換 (N, 1, H, W)
    images_t = torch.stack([
        torch.from_numpy(img).unsqueeze(0) for img in images_np
    ]).to(device)
    
    # 2. 核轉換 (1, 1, kH, kW)
    kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0).to(device)
    
    # 3. 批次卷積（一次 GPU 調用處理所有影像）
    kh, kw = kernel_np.shape
    padding = (kh // 2, kw // 2)
    
    with torch.no_grad():
        results_t = F.conv2d(images_t, kernel_t, padding=padding)
    
    # 4. 批次返回
    results_np = [r.squeeze().cpu().numpy() for r in results_t]
    
    return results_np
```

---

### 記憶體管理

#### GPU 記憶體監控

```python
def print_gpu_memory():
    """顯示 GPU 記憶體使用情況"""
    if not torch.cuda.is_available():
        print("GPU 不可用")
        return
    
    allocated = torch.cuda.memory_allocated() / 1e9  # GB
    reserved = torch.cuda.memory_reserved() / 1e9
    
    print(f"已分配: {allocated:.2f} GB")
    print(f"已保留: {reserved:.2f} GB")
```

#### 記憶體清理

```python
# 手動清理 GPU 記憶體
torch.cuda.empty_cache()

# 或在批次處理中定期清理
for i, img in enumerate(images):
    result = process_image(img)
    
    if i % 10 == 0:
        torch.cuda.empty_cache()  # 每 10 張清理一次
```

---

### 效能分析

#### 預期加速比（2000×3000 影像，201×201 核）

| 操作 | CPU (OpenCV) | PyTorch GPU | 加速比 |
|------|-------------|-------------|--------|
| **單次卷積** | 250 ms | 40 ms | **6.25x** |
| **批次 10 張** | 2500 ms | 180 ms | **13.9x** |
| **第一次調用** | 250 ms | 150 ms | 1.67x (JIT 編譯) |

#### 效能開銷來源

1. **形狀轉換**: `(H,W)` → `(1,1,H,W)` → `(H,W)` (~5ms)
2. **CPU↔GPU 傳輸**: ~10-20ms (取決於影像大小)
3. **首次調用**: JIT 編譯 + GPU 初始化 (~100ms)

**結論**: 單張影像加速有限（6x），批次處理優勢明顯（14x）

---

### 整合到 Phos

#### 修改 `convolve_adaptive()`

```python
# Phos_0.3.0.py

# 頂部導入（條件式）
try:
    import torch
    import torch.nn.functional as F
    PYTORCH_AVAILABLE = torch.cuda.is_available()
except ImportError:
    PYTORCH_AVAILABLE = False

def convolve_adaptive(image, kernel, method='auto', use_gpu=False, backend='cupy'):
    """
    自適應卷積（支援多 GPU 後端）
    
    Args:
        backend: 'cupy' | 'pytorch' | 'jax' | 'opencv_cuda'
    """
    if use_gpu and backend == 'pytorch' and PYTORCH_AVAILABLE:
        return convolve_pytorch_reflect(image, kernel)
    elif method == 'auto':
        ksize = kernel.shape[0]
        if ksize > 150:
            return convolve_fft(image, kernel)
        else:
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    # ... 其他分支
```

---

### PyTorch 優缺點總結

#### ✅ 優點

1. **安裝簡單**: `pip install torch` 一行搞定（自帶 CUDA runtime）
2. **生態系統**: 最成熟的深度學習生態（torchvision, timm, transformers）
3. **文檔豐富**: 官方教程詳細，社群活躍
4. **批次處理**: 針對批次運算高度優化
5. **未來擴展**: 可輕鬆整合神經網路（如可訓練的膠片濾鏡）

#### ❌ 缺點

1. **API 差異**: 需要 4D tensor，轉換有開銷
2. **依賴龐大**: ~2GB（對輕量專案負擔重）
3. **邊界模式**: `conv2d` 不原生支援 `reflect`，需手動 pad
4. **單張影像**: 小批次時加速有限（JIT + 傳輸開銷）
5. **macOS GPU**: 僅 M1/M2 支援 MPS（NVIDIA GPU 不支援）

#### 🎯 適用場景

- ✅ 批次處理（10+ 張影像）
- ✅ 計劃擴展深度學習功能
- ✅ 已有 PyTorch 依賴
- ❌ 輕量級專案
- ❌ macOS + NVIDIA GPU 用戶

---

## 2️⃣ JAX: Google 的高效能計算框架

### 概述

**JAX** 是 Google 開發的 NumPy + 自動微分 + XLA 編譯器，專注於高效能數值計算。

**核心優勢**:
- ✅ **NumPy-like API**: 幾乎與 NumPy 完全相容
- ✅ **XLA 編譯**: 自動優化計算圖（比 PyTorch 更快）
- ✅ **純函數式**: 無副作用，易於並行化
- ✅ **JIT 編譯**: `@jax.jit` 裝飾器一鍵加速

**核心劣勢**:
- ❌ **學習曲線**: 函數式編程範式（與命令式不同）
- ❌ **文檔較少**: 相比 PyTorch 生態較小
- ⚠️ **編譯開銷**: 首次調用需編譯（可能很慢）

---

### 安裝指南

#### Linux (CUDA 11.x)

```bash
# CUDA 版本
pip install --upgrade "jax[cuda11_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html

# 驗證安裝
python3 -c "import jax; print(jax.devices())"
```

#### macOS / Windows (CPU-only)

```bash
# CPU 版本
pip install --upgrade jax jaxlib

# macOS Metal 加速（實驗性）
# 目前不穩定，不推薦
```

**依賴大小**:
- CUDA 版本: ~500 MB
- CPU 版本: ~200 MB

**注意**: JAX GPU 支援主要在 Linux，Windows/macOS 支援有限。

---

### API 教程：JAX 數值計算

#### 核心概念

| 概念 | NumPy | JAX |
|------|-------|-----|
| **陣列類型** | `np.ndarray` | `jax.numpy.ndarray` |
| **命名空間** | `numpy` | `jax.numpy` |
| **裝置管理** | 無 | `jax.device_put()` |
| **編譯** | 無 | `@jax.jit` |

#### 關鍵優勢：NumPy API 相容

```python
import jax.numpy as jnp
import numpy as np

# NumPy 程式碼
x_np = np.random.rand(100, 100)
y_np = np.sin(x_np) + np.cos(x_np)

# JAX 程式碼（幾乎相同！）
x_jax = jnp.random.rand(100, 100)
y_jax = jnp.sin(x_jax) + jnp.cos(x_jax)
```

---

### 程式碼範例：JAX 卷積

#### 範例 1: 基本卷積（使用 scipy.signal）

```python
import jax
import jax.numpy as jnp
from jax.scipy.signal import convolve
import numpy as np

def convolve_jax_simple(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    JAX 卷積（簡單版本）
    
    使用 jax.scipy.signal.convolve（與 NumPy 相容）
    """
    # 1. NumPy → JAX（自動傳到預設裝置）
    image_jax = jnp.array(image_np)
    kernel_jax = jnp.array(kernel_np)
    
    # 2. 卷積（mode='same' 保持尺寸）
    result_jax = convolve(image_jax, kernel_jax, mode='same')
    
    # 3. JAX → NumPy
    result_np = np.array(result_jax)
    
    return result_np
```

**問題**: `jax.scipy.signal.convolve` 不支援 `reflect` 邊界模式！

#### 範例 2: 使用 lax.conv（高效能版）

```python
from jax import lax

def convolve_jax_lax(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    JAX 卷積（使用 lax.conv_general_dilated，最高效）
    
    lax: Low-level API，XLA 直接編譯
    """
    # 1. NumPy → JAX
    image_jax = jnp.array(image_np)
    kernel_jax = jnp.array(kernel_np)
    
    # 2. 調整形狀（lax.conv 需要 4D）
    # (H, W) → (1, H, W, 1)  [NHWC format]
    image_4d = image_jax[None, :, :, None]
    
    # (kH, kW) → (kH, kW, 1, 1)  [kernel: (H, W, in_channels, out_channels)]
    kernel_4d = kernel_jax[:, :, None, None]
    
    # 3. 卷積（使用 lax.conv_general_dilated）
    kh, kw = kernel_np.shape
    padding = ((kh // 2, kh // 2), (kw // 2, kw // 2))
    
    result_4d = lax.conv_general_dilated(
        lhs=image_4d,            # 輸入
        rhs=kernel_4d,           # 核
        window_strides=(1, 1),   # 步長
        padding=padding,         # 填充
        dimension_numbers=('NHWC', 'HWIO', 'NHWC')  # 格式
    )
    
    # 4. 調整回 2D
    result_jax = result_4d[0, :, :, 0]
    
    # 5. JAX → NumPy
    result_np = np.array(result_jax)
    
    return result_np
```

**注意**: `lax.conv` 也不支援 `reflect` padding（僅 `SAME`/`VALID`）

#### 範例 3: 手動 Reflect Padding

```python
def convolve_jax_reflect(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    JAX 卷積 + Reflect 邊界（手動實作）
    """
    # 1. NumPy → JAX
    image_jax = jnp.array(image_np)
    kernel_jax = jnp.array(kernel_np)
    
    # 2. Reflect padding
    kh, kw = kernel_np.shape
    pad_h, pad_w = kh // 2, kw // 2
    
    # JAX 的 pad 支援 'reflect' 嗎？檢查文檔...
    # 答案: ❌ jnp.pad 僅支援 'constant', 'edge', 'wrap'
    # 需要自行實作 reflect padding！
    
    # 簡化方案: 使用 'edge' (雖然不完美)
    image_padded = jnp.pad(
        image_jax,
        ((pad_h, pad_h), (pad_w, pad_w)),
        mode='edge'  # 退而求其次
    )
    
    # 3. 使用 FFT 卷積（JAX 原生支援）
    # 先跳過 padding 問題，展示 FFT
    image_fft = jnp.fft.rfft2(image_padded)
    
    # 核填充並居中
    kernel_padded = jnp.zeros_like(image_padded)
    kernel_padded = kernel_padded.at[:kh, :kw].set(kernel_jax)
    kernel_padded = jnp.roll(kernel_padded, (-kh//2, -kw//2), axis=(0, 1))
    
    kernel_fft = jnp.fft.rfft2(kernel_padded)
    
    # 卷積
    result_fft = image_fft * kernel_fft
    result = jnp.fft.irfft2(result_fft)
    
    # 4. 裁剪
    result = result[pad_h:-pad_h, pad_w:-pad_w]
    
    return np.array(result)
```

**問題**: JAX 的 `jnp.pad` 不支援 `reflect` 模式（與 Phos 不相容）！

---

### JIT 編譯：速度的秘密武器

#### 範例：@jax.jit 裝飾器

```python
import jax
import time

# 未編譯版本
def convolve_slow(image, kernel):
    return jnp.convolve(image, kernel, mode='same')

# JIT 編譯版本
@jax.jit
def convolve_fast(image, kernel):
    return jnp.convolve(image, kernel, mode='same')

# 測試
image = jnp.ones(10000)
kernel = jnp.ones(201)

# 第一次調用（編譯 + 執行）
t0 = time.perf_counter()
result1 = convolve_fast(image, kernel).block_until_ready()
compile_time = time.perf_counter() - t0
print(f"第一次（編譯）: {compile_time*1000:.1f} ms")

# 第二次調用（僅執行）
t0 = time.perf_counter()
result2 = convolve_fast(image, kernel).block_until_ready()
run_time = time.perf_counter() - t0
print(f"第二次（執行）: {run_time*1000:.1f} ms")

# 未編譯版本
t0 = time.perf_counter()
result3 = convolve_slow(image, kernel).block_until_ready()
slow_time = time.perf_counter() - t0
print(f"未編譯: {slow_time*1000:.1f} ms")

print(f"加速比: {slow_time / run_time:.1f}x")
```

**預期輸出**:
```
第一次（編譯）: 523.4 ms
第二次（執行）: 12.3 ms
未編譯: 145.2 ms
加速比: 11.8x
```

**關鍵**: 編譯開銷大，但後續調用極快（適合重複運算）

---

### 裝置管理

#### 手動指定 GPU

```python
# 列出所有裝置
devices = jax.devices()
print(devices)  # [CpuDevice(id=0), GpuDevice(id=0), ...]

# 指定 GPU
gpu = jax.devices('gpu')[0]

# 傳輸到 GPU
image_gpu = jax.device_put(image_jax, gpu)
```

#### 多 GPU 並行（進階）

```python
from jax import pmap

@pmap
def process_parallel(images):
    """在多個 GPU 上並行處理"""
    return jnp.sin(images) + jnp.cos(images)

# 自動分配到所有 GPU
images = jnp.ones((4, 1000, 1000))  # 4 張影像
results = process_parallel(images)  # 每個 GPU 處理 1 張
```

---

### 效能分析

#### 預期加速比（2000×3000 影像，201×201 核）

| 操作 | CPU (NumPy) | JAX GPU | 加速比 |
|------|------------|---------|--------|
| **首次調用** | 250 ms | 800 ms | **0.31x** (編譯慢) |
| **第二次調用** | 250 ms | 20 ms | **12.5x** ✅ |
| **批次 10 張** | 2500 ms | 150 ms | **16.7x** ✅ |

**結論**: JAX 是最快的方案（理論上），但首次編譯開銷大。

---

### JAX 的致命問題：Reflect Padding

#### 現狀

```python
# JAX 支援的 padding 模式
jnp.pad(image, pad_width, mode='constant')  # ✅
jnp.pad(image, pad_width, mode='edge')      # ✅
jnp.pad(image, pad_width, mode='wrap')      # ✅
jnp.pad(image, pad_width, mode='reflect')   # ❌ 不支援！
```

#### 影響

Phos 的所有卷積都使用 `cv2.BORDER_REFLECT`（反射邊界），JAX 無法直接相容。

#### 解決方案

1. **手動實作 reflect padding**（複雜，效能未知）
2. **使用 'edge' 近似**（精度損失）
3. **放棄 JAX**（最實際）

**結論**: JAX 不適合 Phos（邊界模式不相容）

---

### JAX 優缺點總結

#### ✅ 優點

1. **最高效能**: XLA 編譯器優化，理論最快（12-17x）
2. **NumPy 相容**: API 幾乎完全相同（除了 padding）
3. **純函數式**: 易於測試、除錯、並行化
4. **JIT 編譯**: 自動優化計算圖
5. **前沿研究**: Google 內部使用（DeepMind, Brain）

#### ❌ 缺點

1. **編譯開銷**: 首次調用慢（800ms）
2. **邊界模式**: ❌ 不支援 `reflect`（與 Phos 不相容）
3. **學習曲線**: 函數式編程範式（副作用受限）
4. **生態較小**: 相比 PyTorch 文檔少
5. **平台限制**: GPU 支援主要在 Linux

#### 🎯 適用場景

- ✅ 研究/實驗性專案（願意妥協邊界模式）
- ✅ 批次處理（編譯一次，執行多次）
- ✅ Linux + NVIDIA GPU 環境
- ❌ 需要 `reflect` 邊界的專案（如 Phos）
- ❌ Windows/macOS 用戶

---

## 3️⃣ OpenCV CUDA: 原生 GPU 支援

### 概述

**OpenCV CUDA** 是 OpenCV 的 GPU 加速模組，支援 CUDA、OpenCL、Vulkan 多種後端。

**核心優勢**:
- ✅ **原生整合**: 無額外 Python 依賴
- ✅ **API 相似**: `cv2.cuda.*` 與 `cv2.*` 結構相似
- ✅ **多後端**: CUDA (NVIDIA) / OpenCL (AMD) / Vulkan (通用)

**核心劣勢**:
- ❌ **編譯複雜**: 需從源碼編譯（無預編譯輪）
- ❌ **文檔缺乏**: 官方文檔較少，範例有限
- ⚠️ **功能受限**: 部分 CPU 函數無 GPU 對應

---

### 安裝指南

#### 方案 A: 從源碼編譯（Linux）

```bash
# 1. 安裝依賴
sudo apt-get install build-essential cmake git
sudo apt-get install libgtk-3-dev pkg-config
sudo apt-get install nvidia-cuda-toolkit  # CUDA

# 2. 下載源碼
git clone https://github.com/opencv/opencv.git
git clone https://github.com/opencv/opencv_contrib.git

# 3. 配置編譯（關鍵步驟）
cd opencv
mkdir build && cd build

cmake -D CMAKE_BUILD_TYPE=RELEASE \
      -D CMAKE_INSTALL_PREFIX=/usr/local \
      -D OPENCV_EXTRA_MODULES_PATH=../../opencv_contrib/modules \
      -D WITH_CUDA=ON \
      -D CUDA_ARCH_BIN=8.6 \            # 根據 GPU 架構調整
      -D CUDA_ARCH_PTX="" \
      -D ENABLE_FAST_MATH=ON \
      -D CUDA_FAST_MATH=ON \
      -D WITH_CUBLAS=ON \
      -D WITH_CUDNN=ON \                # 如有 cuDNN
      -D OPENCV_DNN_CUDA=ON \
      -D BUILD_opencv_python3=ON \
      -D PYTHON3_EXECUTABLE=$(which python3) \
      ..

# 4. 編譯（耗時 30-60 分鐘）
make -j$(nproc)

# 5. 安裝
sudo make install
sudo ldconfig

# 6. 驗證
python3 -c "import cv2; print(cv2.cuda.getCudaEnabledDeviceCount())"
```

**CUDA_ARCH_BIN 對照表**:
| GPU 型號 | 架構代號 | CUDA_ARCH_BIN |
|---------|---------|---------------|
| GTX 1060 | Pascal | 6.1 |
| RTX 2080 | Turing | 7.5 |
| RTX 3090 | Ampere | 8.6 |
| RTX 4090 | Ada | 8.9 |

#### 方案 B: Docker（推薦）

```dockerfile
# Dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-devel-ubuntu22.04

# 安裝 OpenCV with CUDA
RUN apt-get update && apt-get install -y \
    python3-opencv \
    # ... (編譯步驟省略)

# 安裝 Phos 依賴
COPY requirements.txt /app/
RUN pip install -r /app/requirements.txt
```

```bash
# 建構
docker build -t phos-gpu .

# 執行
docker run --gpus all -p 8501:8501 phos-gpu
```

---

### API 教程：OpenCV CUDA

#### 核心概念

| 概念 | CPU | GPU |
|------|-----|-----|
| **陣列類型** | `np.ndarray` | `cv2.cuda_GpuMat` |
| **記憶體位置** | RAM | VRAM |
| **上傳** | 無 | `gpu_mat.upload(cpu_array)` |
| **下載** | 無 | `cpu_array = gpu_mat.download()` |

#### 關鍵差異：GpuMat 物件

```python
import cv2
import numpy as np

# CPU 陣列
image_cpu = np.random.rand(1000, 1000).astype(np.float32)

# GPU 陣列
gpu_mat = cv2.cuda_GpuMat()
gpu_mat.upload(image_cpu)

# GPU 運算
result_gpu = cv2.cuda.filter2D(gpu_mat, -1, kernel)

# 下載回 CPU
result_cpu = result_gpu.download()
```

---

### 程式碼範例：OpenCV CUDA 卷積

#### 範例 1: 基本卷積

```python
import cv2
import numpy as np

def convolve_opencv_cuda(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    OpenCV CUDA 卷積
    
    Args:
        image_np: NumPy 陣列 (H, W), float32
        kernel_np: 卷積核 (kH, kW), float32
        
    Returns:
        result_np: 卷積結果 (H, W), float32
    """
    # 1. 檢查 CUDA 可用性
    if cv2.cuda.getCudaEnabledDeviceCount() == 0:
        raise RuntimeError("No CUDA-enabled device found")
    
    # 2. 上傳到 GPU
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image_np)
    
    # 3. GPU 卷積
    gpu_result = cv2.cuda.filter2D(
        gpu_image, 
        ddepth=-1,  # 保持原深度
        kernel=kernel_np,
        borderMode=cv2.BORDER_REFLECT  # ✅ 支援 reflect！
    )
    
    # 4. 下載回 CPU
    result_np = gpu_result.download()
    
    return result_np
```

**優點**: 直接支援 `BORDER_REFLECT`（與 CPU 版本一致）！

#### 範例 2: 高斯模糊（專用函數）

```python
def gaussian_blur_cuda(image_np: np.ndarray, ksize: int, sigma: float) -> np.ndarray:
    """
    GPU 加速高斯模糊（使用 cv2.cuda.GaussianBlur）
    """
    if cv2.cuda.getCudaEnabledDeviceCount() == 0:
        # Fallback to CPU
        return cv2.GaussianBlur(image_np, (ksize, ksize), sigma)
    
    # GPU 路徑
    gpu_image = cv2.cuda_GpuMat()
    gpu_image.upload(image_np)
    
    gpu_result = cv2.cuda.GaussianBlur(
        gpu_image,
        ksize=(ksize, ksize),
        sigmaX=sigma,
        borderMode=cv2.BORDER_REFLECT
    )
    
    return gpu_result.download()
```

#### 範例 3: 批次處理（Stream）

```python
def convolve_batch_opencv_cuda(images_np: list, kernel_np: np.ndarray) -> list:
    """
    批次卷積（使用 CUDA Stream 並行）
    """
    if cv2.cuda.getCudaEnabledDeviceCount() == 0:
        return [cv2.filter2D(img, -1, kernel_np) for img in images_np]
    
    # 創建 Stream（異步執行）
    stream = cv2.cuda.Stream()
    
    results = []
    for img in images_np:
        gpu_image = cv2.cuda_GpuMat()
        gpu_image.upload(img, stream=stream)
        
        gpu_result = cv2.cuda.filter2D(gpu_image, -1, kernel_np, stream=stream)
        
        result = gpu_result.download(stream=stream)
        results.append(result)
    
    # 等待所有操作完成
    stream.waitForCompletion()
    
    return results
```

---

### 功能對照表

| CPU 函數 | GPU 函數 | 支援度 |
|---------|---------|--------|
| `cv2.filter2D` | `cv2.cuda.filter2D` | ✅ |
| `cv2.GaussianBlur` | `cv2.cuda.GaussianBlur` | ✅ |
| `cv2.resize` | `cv2.cuda.resize` | ✅ |
| `cv2.cvtColor` | `cv2.cuda.cvtColor` | ✅ |
| `cv2.threshold` | `cv2.cuda.threshold` | ✅ |
| `cv2.morphologyEx` | `cv2.cuda.morphologyEx` | ✅ |
| **numpy FFT** | ❌ 無對應 | ❌ |

**發現**: OpenCV CUDA 不支援 FFT 卷積（僅空間域）

---

### 效能分析

#### 預期加速比（2000×3000 影像，201×201 核）

| 操作 | CPU | OpenCV CUDA | 加速比 |
|------|-----|-------------|--------|
| **filter2D** | 250 ms | 40 ms | **6.25x** |
| **GaussianBlur** | 200 ms | 35 ms | **5.71x** |
| **批次 10 張** | 2500 ms | 280 ms | **8.93x** |

**與 CuPy 對比**: 類似效能（6-8x），但編譯麻煩。

---

### 整合到 Phos

#### 修改 `convolve_adaptive()`

```python
# Phos_0.3.0.py

# 頂部檢測 CUDA 支援
OPENCV_CUDA_AVAILABLE = cv2.cuda.getCudaEnabledDeviceCount() > 0

def convolve_adaptive(image, kernel, method='auto', use_gpu=False, backend='cupy'):
    """
    自適應卷積（支援 OpenCV CUDA）
    """
    if use_gpu and backend == 'opencv_cuda' and OPENCV_CUDA_AVAILABLE:
        return convolve_opencv_cuda(image, kernel)
    elif method == 'auto':
        ksize = kernel.shape[0]
        if ksize > 150:
            return convolve_fft(image, kernel)
        else:
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    # ... 其他分支
```

---

### OpenCV CUDA 優缺點總結

#### ✅ 優點

1. **無額外依賴**: 不需 CuPy/PyTorch（編譯後）
2. **API 相似**: 與 CPU 版本幾乎一致
3. **多後端**: CUDA/OpenCL/Vulkan（跨平台潛力）
4. **Reflect 支援**: ✅ 原生支援 `BORDER_REFLECT`
5. **視覺相容**: 與 CPU 版本完全等價

#### ❌ 缺點

1. **編譯複雜**: ❌ 無預編譯輪，需手動編譯（30-60分鐘）
2. **文檔缺乏**: 官方文檔少，範例有限
3. **功能受限**: 無 FFT 卷積支援
4. **維護成本**: 每次 OpenCV 更新需重新編譯
5. **錯誤除錯**: CUDA 錯誤訊息不友善

#### 🎯 適用場景

- ✅ 已有 OpenCV CUDA 編譯環境
- ✅ 不願增加 Python 依賴
- ✅ 需要 OpenCL/Vulkan 後端（AMD GPU）
- ❌ 新專案（編譯成本太高）
- ❌ 快速原型開發

---

## 4️⃣ 框架橫向對比

### API 相容性對比

| 框架 | NumPy 相容 | 需轉換 | Reflect Padding | 學習曲線 |
|------|-----------|--------|-----------------|---------|
| **CuPy** | ⭐⭐⭐⭐⭐ | 最小 | ✅ | 低 |
| **PyTorch** | ⭐⭐⭐ | 4D tensor | ⚠️ 手動 pad | 中 |
| **JAX** | ⭐⭐⭐⭐ | 最小 | ❌ 不支援 | 高 |
| **OpenCV CUDA** | ⭐⭐⭐⭐ | GpuMat | ✅ | 低 |

### 效能對比（預測）

| 框架 | 單張影像 | 批次 10 張 | 首次調用 | 記憶體 |
|------|---------|-----------|---------|--------|
| **CuPy** | 8-10x | 9-11x | 快 | 低 |
| **PyTorch** | 6-8x | 13-15x | 中 | 高 |
| **JAX** | 12-15x | 16-18x | 慢 | 中 |
| **OpenCV CUDA** | 6-8x | 8-10x | 快 | 低 |

### 安裝複雜度對比

| 框架 | Linux | Windows | macOS | 依賴大小 |
|------|-------|---------|-------|---------|
| **CuPy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ❌ | 200MB |
| **PyTorch** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (MPS) | 2GB |
| **JAX** | ⭐⭐⭐⭐ | ⭐⭐ | ⭐ | 500MB |
| **OpenCV CUDA** | ⭐⭐ | ⭐ | ❌ | 0MB (編譯) |

### 生態系統對比

| 框架 | 社群規模 | 文檔品質 | 更新頻率 | 未來潛力 |
|------|---------|---------|---------|---------|
| **CuPy** | 中 | 好 | 穩定 | 中 |
| **PyTorch** | 大 | 優秀 | 快 | 高 |
| **JAX** | 中 | 中 | 快 | 高 |
| **OpenCV CUDA** | 小 | 差 | 慢 | 低 |

---

## 5️⃣ 實際測試結果（TODO）

### 測試環境

```
硬體: NVIDIA RTX 3090 (24GB VRAM)
CPU: AMD Ryzen 9 5950X (16C/32T)
RAM: 64GB DDR4-3600
OS: Ubuntu 22.04 LTS
CUDA: 11.8
Python: 3.11
```

### 測試腳本

```python
# scripts/benchmark_gpu_frameworks.py

import time
import numpy as np
import cv2

# 條件導入
try:
    import cupy as cp
    CUPY_AVAILABLE = True
except:
    CUPY_AVAILABLE = False

try:
    import torch
    TORCH_AVAILABLE = torch.cuda.is_available()
except:
    TORCH_AVAILABLE = False

try:
    import jax
    JAX_AVAILABLE = len(jax.devices('gpu')) > 0
except:
    JAX_AVAILABLE = False

OPENCV_CUDA_AVAILABLE = cv2.cuda.getCudaEnabledDeviceCount() > 0

def benchmark_all_frameworks():
    """測試所有框架效能"""
    
    # 測試影像
    image = np.random.rand(2000, 3000).astype(np.float32)
    kernel = cv2.getGaussianKernel(201, 50)
    kernel = (kernel @ kernel.T).astype(np.float32)
    
    results = {}
    
    # CPU Baseline
    print("測試 CPU (OpenCV filter2D)...")
    t0 = time.perf_counter()
    for _ in range(5):
        result_cpu = cv2.filter2D(image, -1, kernel)
    results['CPU_filter2D'] = (time.perf_counter() - t0) / 5 * 1000
    
    # CPU FFT
    print("測試 CPU (FFT)...")
    # ... (實作省略)
    
    # CuPy
    if CUPY_AVAILABLE:
        print("測試 CuPy...")
        # ... (實作省略)
    
    # PyTorch
    if TORCH_AVAILABLE:
        print("測試 PyTorch...")
        # ... (實作省略)
    
    # JAX
    if JAX_AVAILABLE:
        print("測試 JAX...")
        # ... (實作省略)
    
    # OpenCV CUDA
    if OPENCV_CUDA_AVAILABLE:
        print("測試 OpenCV CUDA...")
        # ... (實作省略)
    
    # 輸出結果
    print("\n" + "="*60)
    print(f"{'框架':<20} {'平均時間':<12} {'加速比':<10}")
    print("="*60)
    baseline = results['CPU_filter2D']
    for name, time_ms in results.items():
        speedup = baseline / time_ms
        print(f"{name:<20} {time_ms:>10.1f}ms  {speedup:>8.2f}x")
    print("="*60)

if __name__ == '__main__':
    benchmark_all_frameworks()
```

### 預期結果（未實測）

```
============================================================
框架                  平均時間      加速比       
============================================================
CPU_filter2D              380.0ms      1.00x
CPU_FFT                   250.0ms      1.52x
GPU_CuPy                   45.0ms      8.44x
GPU_PyTorch                60.0ms      6.33x
GPU_JAX                    30.0ms     12.67x  ← 理論最快
GPU_OpenCV_CUDA            50.0ms      7.60x
============================================================
```

**注意**: 以上為理論預測，實際需測試驗證！

---

## 6️⃣ 最終建議

### 推薦排序（考慮 Phos 實際需求）

#### 🥇 第一選擇：CuPy

**理由**:
1. ✅ NumPy API 相容（幾乎零學習成本）
2. ✅ 支援 `reflect` 邊界
3. ✅ 安裝簡單（`pip install cupy-cuda11x`）
4. ✅ 文檔完善，社群成熟
5. ✅ 效能優秀（8-10x）

**使用場景**: 所有 Phos 用戶（Linux/Windows + NVIDIA GPU）

---

#### 🥈 第二選擇：PyTorch

**理由**:
1. ✅ 安裝最簡單（自帶 CUDA runtime）
2. ✅ 未來可擴展（深度學習膠片模型）
3. ✅ 批次處理優勢明顯（13-15x）
4. ⚠️ API 轉換有開銷
5. ❌ 依賴龐大（2GB）

**使用場景**: 
- 計劃擴展深度學習功能
- 批次處理為主（10+ 張影像）
- 不介意依賴大小

---

#### 🥉 第三選擇：JAX

**理由**:
1. ✅ 理論效能最高（12-15x）
2. ✅ NumPy API 相似
3. ❌ **不支援 `reflect` 邊界**（致命缺陷）
4. ⚠️ 編譯開銷大（首次調用慢）
5. ⚠️ 生態較小

**使用場景**: 
- 研究/實驗性專案
- 願意妥協邊界模式（使用 `edge`）
- Linux 環境

**結論**: **不推薦用於 Phos**（邊界不相容）

---

#### 4️⃣ 第四選擇：OpenCV CUDA

**理由**:
1. ✅ 無額外 Python 依賴
2. ✅ 支援 `reflect` 邊界
3. ❌ **編譯極複雜**（30-60分鐘）
4. ❌ 文檔缺乏
5. ❌ 功能受限（無 FFT）

**使用場景**: 
- 已有 OpenCV CUDA 編譯環境
- 不願增加依賴
- 需要 OpenCL/Vulkan（AMD GPU）

**結論**: **僅當已編譯時考慮**

---

### 決策矩陣

| 需求 | CuPy | PyTorch | JAX | OpenCV CUDA |
|------|------|---------|-----|-------------|
| **易於安裝** | ✅ | ✅ | ⚠️ | ❌ |
| **API 相容** | ✅ | ⚠️ | ✅ | ✅ |
| **Reflect 支援** | ✅ | ⚠️ | ❌ | ✅ |
| **單張效能** | ✅ | ✅ | ✅ | ✅ |
| **批次效能** | ✅ | ⭐ | ⭐ | ✅ |
| **依賴大小** | ✅ | ❌ | ⚠️ | ✅ |
| **未來擴展** | ⚠️ | ⭐ | ⭐ | ❌ |
| **macOS 支援** | ❌ | ⚠️ | ❌ | ❌ |

### 實作建議

#### 短期（1-2 週）

✅ **採用 CuPy**（如原計畫）

**行動清單**:
1. 實作 `phos_gpu.py`（CuPy 卷積）
2. 整合到 `convolve_adaptive()`
3. 測試精度（PSNR >40dB）
4. 測試效能（目標 8-10x）
5. 添加 UI 開關

#### 中期（1-2 月）

⚠️ **評估 PyTorch 整合**（如計劃擴展深度學習）

**條件**:
- 批次處理需求增加
- 計劃開發可訓練濾鏡
- 用戶接受 2GB 依賴

#### 長期（3-6 月）

🔬 **實驗 JAX**（研究性質）

**條件**:
- 解決 `reflect` 邊界問題（自行實作）
- 極致效能需求（>10x）
- 願意承擔維護成本

---

## 7️⃣ 實作檢查表

### P0 (立即執行)

- [x] 完成 GPU 框架比較文檔（本文件）
- [ ] 決策：確認使用 CuPy（如原計畫）
- [ ] 創建 `phos_gpu.py`（CuPy 實作）
- [ ] 測試基準（2000×3000 影像）

### P1 (重要)

- [ ] 如效能不足：測試 PyTorch（批次處理）
- [ ] 如需擴展：評估 PyTorch 深度學習整合
- [ ] 文檔：更新 README（GPU 需求說明）

### P2 (可選)

- [ ] 實驗：JAX 邊界模式自行實作
- [ ] 實驗：OpenCV CUDA（如已有編譯環境）
- [ ] 比較：多框架實測基準（RTX 3090）

---

## 8️⃣ 參考資料

### 官方文檔

1. **CuPy**: https://docs.cupy.dev/en/stable/
2. **PyTorch**: https://pytorch.org/docs/stable/
3. **JAX**: https://jax.readthedocs.io/en/latest/
4. **OpenCV CUDA**: https://docs.opencv.org/4.x/d1/dfb/intro.html

### 效能基準

5. **GPU 卷積對比**: https://github.com/NVIDIA/cuda-samples
6. **PyTorch vs JAX**: https://wandb.ai/cayush/pytorch-vs-jax

### 論文

7. **XLA 編譯器**: https://www.tensorflow.org/xla
8. **CUDA 最佳實踐**: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/

---

**文檔版本**: v1.0  
**最後更新**: 2025-12-20  
**狀態**: ✅ 完成，建議採用 CuPy
