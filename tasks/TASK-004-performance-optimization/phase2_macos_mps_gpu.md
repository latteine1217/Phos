# Phase 2: macOS MPS GPU 加速實施計畫

**創建時間**: 2025-12-22  
**目標平台**: macOS (Apple Silicon M1/M2/M3)  
**GPU 後端**: PyTorch MPS (Metal Performance Shaders)  
**預期加速**: 3-5x (M3 晶片)

---

## 📋 Executive Summary

### 平台限制與方案調整

原計畫採用 **CuPy**（NVIDIA CUDA），但在 macOS 上不可行：
- ❌ macOS 不支援 NVIDIA CUDA（自 10.14 起）
- ❌ CuPy 僅支援 NVIDIA GPU
- ✅ **替代方案**：PyTorch + MPS (Metal Performance Shaders)

### PyTorch MPS 優勢

**Apple Silicon 原生支援**:
- ✅ M1/M2/M3 晶片內建 GPU（8-40 核心）
- ✅ 統一記憶體架構（CPU 與 GPU 共享記憶體，傳輸開銷小）
- ✅ Metal 框架原生優化
- ✅ 安裝簡單（`pip install torch`）

**預期效能**:
| 操作 | CPU (M3) | MPS GPU (M3) | 加速比 |
|------|---------|--------------|--------|
| 單次卷積 (201×201) | 250ms | 60-80ms | **3-4x** |
| Halation (3通道) | 1.4s | 350-450ms | **3-4x** |
| **端到端處理** | **2.1s** | **0.6-0.8s** | **2.5-3.5x** |

**注意**: MPS 加速比低於 NVIDIA GPU (8-10x)，但對 M3 晶片用戶仍顯著提升。

---

## 🎯 實施計畫

### Phase 2.1: PyTorch MPS 基礎整合（估計 4-6 小時）

#### 目標
- 實作 `phos_gpu.py` 模組（PyTorch MPS 後端）
- 自動檢測 MPS 可用性
- 整合到 `convolve_adaptive()`
- 測試精度與效能

#### 任務清單

**Task 2.1.1: 安裝與驗證 PyTorch**
```bash
# 安裝 PyTorch（macOS 版本，包含 MPS 支援）
pip install torch torchvision

# 驗證 MPS 可用性
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
python3 -c "import torch; print(f'MPS built: {torch.backends.mps.is_built()}')"
```

**預期輸出**:
```
MPS available: True
MPS built: True
```

**Task 2.1.2: 創建 `phos_gpu.py` 模組**

核心功能：
1. 自動檢測 MPS/CUDA/CPU
2. 實作 `convolve_gpu()` (PyTorch 後端)
3. 處理 reflect padding（手動 pad）
4. 實作記憶體管理與錯誤處理

**檔案結構**:
```
phos_gpu.py
├── GPU_BACKEND: 'mps' | 'cuda' | 'cpu'
├── convolve_gpu(image, kernel) → np.ndarray
├── convolve_batch_gpu(images, kernel) → list[np.ndarray]
├── get_gpu_info() → dict
└── benchmark_gpu() → dict
```

**Task 2.1.3: 整合到主程式**

修改 `Phos_0.3.0.py`:
1. 導入 `phos_gpu` 模組（條件式）
2. 修改 `convolve_adaptive()` 添加 `use_gpu` 參數
3. 修改 `apply_halation()` 支援 GPU
4. 修改 `apply_bloom_mie_corrected()` 支援 GPU

**Task 2.1.4: Streamlit UI 整合**

添加 GPU 控制面板：
- 顯示 GPU 資訊（型號、可用性）
- 「使用 GPU 加速」核取方塊
- 效能監控（GPU 記憶體使用）

---

### Phase 2.2: 效能優化與測試（估計 2-3 小時）

#### 任務清單

**Task 2.2.1: 效能基準測試**

創建 `scripts/benchmark_mps_gpu.py`:
- 測試不同影像尺寸（1000×1500, 2000×3000）
- 測試不同核大小（61×61, 121×121, 151×151）
- 對比 CPU vs MPS
- 測試批次處理（1, 3, 10 張）

**驗收標準**:
- 單張影像加速 >3x
- 批次處理加速 >4x
- 總處理時間 <0.8s (2000×3000)

**Task 2.2.2: 精度驗證**

測試 GPU vs CPU 結果差異：
- PSNR >40dB（幾乎無差異）
- 最大像素誤差 <0.01
- 能量守恆誤差 <0.1%

**Task 2.2.3: 錯誤處理測試**

模擬錯誤情境：
- MPS OOM（記憶體不足） → 自動 fallback CPU
- MPS 不可用 → 自動使用 CPU
- 影像尺寸過大 → 警告並使用 CPU

---

### Phase 2.3: 文檔與用戶指引（估計 1-2 小時）

#### 任務清單

**Task 2.3.1: 更新 README.md**

添加章節：
- GPU 加速需求（macOS: M1/M2/M3）
- 安裝 PyTorch 指引
- 效能預期（macOS vs Linux/Windows）
- 常見問題（FAQ）

**Task 2.3.2: 創建 GPU 優化文檔**

`docs/GPU_ACCELERATION_GUIDE.md`:
- 支援的平台與 GPU
- 安裝指南（macOS/Linux/Windows）
- 效能對比表
- 問題排查

---

## 💻 程式碼實作

### 1. `phos_gpu.py` 完整實作

```python
"""
Phos GPU 加速模組
支援: PyTorch (MPS/CUDA), CuPy (CUDA)
"""

import numpy as np
import warnings
from typing import Optional, Union, List, Tuple

# ===== GPU 後端偵測 =====

# 嘗試導入 PyTorch
try:
    import torch
    import torch.nn.functional as F
    
    # 偵測可用裝置
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        GPU_BACKEND = 'mps'
        GPU_DEVICE = torch.device('mps')
    elif torch.cuda.is_available():
        GPU_BACKEND = 'cuda'
        GPU_DEVICE = torch.device('cuda')
    else:
        GPU_BACKEND = 'cpu'
        GPU_DEVICE = torch.device('cpu')
    
    PYTORCH_AVAILABLE = True
except ImportError:
    PYTORCH_AVAILABLE = False
    GPU_BACKEND = 'cpu'
    GPU_DEVICE = None

# 嘗試導入 CuPy（僅 NVIDIA GPU）
try:
    import cupy as cp
    import cupyx.scipy.ndimage as cpx_ndimage
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    cp = None


# ===== GPU 資訊查詢 =====

def get_gpu_info() -> dict:
    """
    獲取 GPU 資訊
    
    Returns:
        dict: {
            'available': bool,
            'backend': 'mps' | 'cuda' | 'cpu',
            'device_name': str,
            'memory_total_gb': float,  # CUDA only
            'memory_free_gb': float    # CUDA only
        }
    """
    if not PYTORCH_AVAILABLE:
        return {
            'available': False,
            'backend': 'cpu',
            'reason': 'PyTorch not installed'
        }
    
    if GPU_BACKEND == 'mps':
        # MPS 不提供記憶體查詢 API
        return {
            'available': True,
            'backend': 'mps',
            'device_name': 'Apple Metal GPU',
            'memory_total_gb': None,
            'memory_free_gb': None
        }
    elif GPU_BACKEND == 'cuda':
        try:
            device_id = torch.cuda.current_device()
            device_name = torch.cuda.get_device_name(device_id)
            memory_total = torch.cuda.get_device_properties(device_id).total_memory / 1e9
            memory_free = (torch.cuda.get_device_properties(device_id).total_memory - 
                          torch.cuda.memory_allocated(device_id)) / 1e9
            
            return {
                'available': True,
                'backend': 'cuda',
                'device_name': device_name,
                'memory_total_gb': memory_total,
                'memory_free_gb': memory_free
            }
        except Exception as e:
            return {
                'available': False,
                'backend': 'cuda',
                'reason': str(e)
            }
    else:
        return {
            'available': False,
            'backend': 'cpu',
            'reason': 'No GPU available'
        }


# ===== PyTorch GPU 卷積 =====

def convolve_pytorch(
    image_np: np.ndarray, 
    kernel_np: np.ndarray,
    device: Optional[torch.device] = None
) -> np.ndarray:
    """
    PyTorch GPU 加速卷積（支援 MPS/CUDA）
    
    使用 reflect padding 保持物理一致性
    
    Args:
        image_np: NumPy 陣列 (H, W), float32
        kernel_np: 卷積核 (kH, kW), float32
        device: torch.device ('mps'/'cuda'/'cpu')，None = 自動選擇
        
    Returns:
        result_np: 卷積結果 (H, W), float32
    """
    if device is None:
        device = GPU_DEVICE
    
    try:
        # 1. NumPy → Torch (CPU)
        # (H, W) → (1, 1, H, W)
        image_t = torch.from_numpy(image_np).unsqueeze(0).unsqueeze(0)
        kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0)
        
        # 2. 傳輸到 GPU
        image_t = image_t.to(device)
        kernel_t = kernel_t.to(device)
        
        # 3. Reflect padding（手動實作，保持與 OpenCV 一致）
        kh, kw = kernel_np.shape
        pad_h, pad_w = kh // 2, kw // 2
        
        image_padded = F.pad(
            image_t,
            (pad_w, pad_w, pad_h, pad_h),  # (left, right, top, bottom)
            mode='reflect'
        )
        
        # 4. 卷積（關閉自動微分以提升效能）
        with torch.no_grad():
            result_t = F.conv2d(image_padded, kernel_t, padding=0)
        
        # 5. GPU → CPU → NumPy
        result_np = result_t.squeeze().cpu().numpy()
        
        return result_np
    
    except RuntimeError as e:
        # MPS OOM 或其他錯誤 → fallback CPU
        warnings.warn(f"GPU 卷積失敗，fallback CPU: {e}")
        import cv2
        return cv2.filter2D(image_np, -1, kernel_np, borderType=cv2.BORDER_REFLECT)


def convolve_batch_pytorch(
    images_np: List[np.ndarray],
    kernel_np: np.ndarray,
    device: Optional[torch.device] = None
) -> List[np.ndarray]:
    """
    批次 GPU 卷積（最大化 GPU 利用率）
    
    Args:
        images_np: 列表，每個元素為 (H, W) NumPy 陣列
        kernel_np: 共用卷積核 (kH, kW)
        device: torch.device
        
    Returns:
        results_np: 列表，卷積結果
    """
    if device is None:
        device = GPU_DEVICE
    
    try:
        # 1. 批次轉換 (N, 1, H, W)
        images_t = torch.stack([
            torch.from_numpy(img).unsqueeze(0) for img in images_np
        ]).to(device)
        
        # 2. 核轉換 (1, 1, kH, kW)
        kernel_t = torch.from_numpy(kernel_np).unsqueeze(0).unsqueeze(0).to(device)
        
        # 3. Reflect padding
        kh, kw = kernel_np.shape
        pad_h, pad_w = kh // 2, kw // 2
        images_padded = F.pad(images_t, (pad_w, pad_w, pad_h, pad_h), mode='reflect')
        
        # 4. 批次卷積（一次 GPU 調用處理所有影像）
        with torch.no_grad():
            results_t = F.conv2d(images_padded, kernel_t, padding=0)
        
        # 5. 批次返回
        results_np = [r.squeeze().cpu().numpy() for r in results_t]
        
        return results_np
    
    except RuntimeError as e:
        warnings.warn(f"批次 GPU 卷積失敗，fallback 逐張處理: {e}")
        return [convolve_pytorch(img, kernel_np, device) for img in images_np]


# ===== CuPy GPU 卷積（NVIDIA CUDA Only）=====

def convolve_cupy(image_np: np.ndarray, kernel_np: np.ndarray) -> np.ndarray:
    """
    CuPy GPU 加速卷積（僅 NVIDIA GPU）
    
    Args:
        image_np: NumPy 陣列 (H, W), float32
        kernel_np: 卷積核 (kH, kW), float32
        
    Returns:
        result_np: 卷積結果 (H, W), float32
    """
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy not available (requires NVIDIA GPU + CUDA)")
    
    try:
        # 1. 傳輸到 GPU
        image_gpu = cp.asarray(image_np)
        kernel_gpu = cp.asarray(kernel_np)
        
        # 2. GPU 卷積（mode='reflect'）
        result_gpu = cpx_ndimage.convolve(image_gpu, kernel_gpu, mode='reflect')
        
        # 3. 傳回 CPU
        result_np = cp.asnumpy(result_gpu)
        
        return result_np
    
    except Exception as e:
        warnings.warn(f"CuPy 卷積失敗，fallback CPU: {e}")
        import cv2
        return cv2.filter2D(image_np, -1, kernel_np, borderType=cv2.BORDER_REFLECT)


# ===== 統一介面 =====

def convolve_gpu(
    image: np.ndarray,
    kernel: np.ndarray,
    backend: str = 'auto'
) -> np.ndarray:
    """
    GPU 加速卷積（統一介面）
    
    自動選擇最佳 GPU 後端：
    - macOS M1/M2/M3: PyTorch MPS
    - NVIDIA GPU: CuPy (優先) 或 PyTorch CUDA
    - 其他: CPU fallback
    
    Args:
        image: NumPy 陣列 (H, W), float32
        kernel: 卷積核 (kH, kW), float32
        backend: 'auto' | 'pytorch' | 'cupy' | 'cpu'
        
    Returns:
        result: 卷積結果 (H, W), float32
    """
    if backend == 'auto':
        if GPU_BACKEND == 'mps' and PYTORCH_AVAILABLE:
            return convolve_pytorch(image, kernel)
        elif GPU_BACKEND == 'cuda' and CUPY_AVAILABLE:
            return convolve_cupy(image, kernel)
        elif GPU_BACKEND == 'cuda' and PYTORCH_AVAILABLE:
            return convolve_pytorch(image, kernel)
        else:
            # Fallback CPU
            import cv2
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    
    elif backend == 'pytorch':
        return convolve_pytorch(image, kernel)
    
    elif backend == 'cupy':
        return convolve_cupy(image, kernel)
    
    elif backend == 'cpu':
        import cv2
        return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    
    else:
        raise ValueError(f"Unknown backend: {backend}")


# ===== 效能基準測試 =====

def benchmark_gpu(image_size: Tuple[int, int] = (2000, 3000), 
                  kernel_size: int = 201) -> dict:
    """
    GPU vs CPU 效能基準測試
    
    Args:
        image_size: 影像尺寸 (H, W)
        kernel_size: 核大小
        
    Returns:
        dict: {
            'cpu_time_ms': float,
            'gpu_time_ms': float,
            'speedup': float,
            'gpu_backend': str
        }
    """
    import time
    import cv2
    
    # 創建測試數據
    image = np.random.rand(*image_size).astype(np.float32)
    kernel = cv2.getGaussianKernel(kernel_size, kernel_size / 6.0)
    kernel = (kernel @ kernel.T).astype(np.float32)
    
    # Warmup
    if PYTORCH_AVAILABLE:
        _ = convolve_pytorch(image, kernel)
    
    # CPU 測試
    t0 = time.perf_counter()
    result_cpu = cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    cpu_time = (time.perf_counter() - t0) * 1000
    
    # GPU 測試
    if GPU_BACKEND != 'cpu':
        t0 = time.perf_counter()
        result_gpu = convolve_gpu(image, kernel)
        gpu_time = (time.perf_counter() - t0) * 1000
        
        # 精度驗證
        mse = np.mean((result_cpu - result_gpu) ** 2)
        psnr = 10 * np.log10(1.0 / mse) if mse > 0 else float('inf')
        
        return {
            'cpu_time_ms': cpu_time,
            'gpu_time_ms': gpu_time,
            'speedup': cpu_time / gpu_time,
            'gpu_backend': GPU_BACKEND,
            'psnr_db': psnr
        }
    else:
        return {
            'cpu_time_ms': cpu_time,
            'gpu_time_ms': None,
            'speedup': 1.0,
            'gpu_backend': 'cpu',
            'psnr_db': None
        }


# ===== 模組初始化資訊 =====

if __name__ == "__main__":
    print("=" * 60)
    print("Phos GPU 加速模組")
    print("=" * 60)
    
    gpu_info = get_gpu_info()
    print(f"\nGPU 狀態:")
    print(f"  可用: {gpu_info['available']}")
    print(f"  後端: {gpu_info.get('backend', 'N/A')}")
    print(f"  裝置: {gpu_info.get('device_name', 'N/A')}")
    
    if gpu_info['available']:
        print(f"\n執行基準測試 (2000×3000, 201×201 核)...")
        results = benchmark_gpu()
        print(f"\n結果:")
        print(f"  CPU 時間: {results['cpu_time_ms']:.1f} ms")
        if results['gpu_time_ms']:
            print(f"  GPU 時間: {results['gpu_time_ms']:.1f} ms")
            print(f"  加速比: {results['speedup']:.2f}x")
            print(f"  精度 (PSNR): {results['psnr_db']:.1f} dB")
    
    print("=" * 60)
```

---

### 2. 整合到 `Phos_0.3.0.py`

**修改點 1: 頂部導入**

```python
# Phos_0.3.0.py (Line ~30)

# GPU 加速模組（可選）
try:
    from phos_gpu import (
        GPU_BACKEND, 
        convolve_gpu, 
        get_gpu_info,
        PYTORCH_AVAILABLE
    )
    GPU_AVAILABLE = (GPU_BACKEND in ['mps', 'cuda'])
except ImportError:
    GPU_AVAILABLE = False
    GPU_BACKEND = 'cpu'
```

**修改點 2: 修改 `convolve_adaptive()`**

```python
# Phos_0.3.0.py (Line ~1330)

def convolve_adaptive(
    image: np.ndarray, 
    kernel: np.ndarray, 
    method: str = 'auto',
    use_gpu: bool = False  # 新增參數
) -> np.ndarray:
    """
    自適應選擇卷積方法（支援 GPU 加速）
    
    Args:
        image: 輸入影像 (H, W)
        kernel: 卷積核 (kH, kW)
        method: 'auto' | 'spatial' | 'fft' | 'gpu'
        use_gpu: 是否嘗試使用 GPU（需硬體支援）
        
    Returns:
        卷積結果 (H, W)
    """
    # GPU 路徑（優先）
    if use_gpu and GPU_AVAILABLE:
        return convolve_gpu(image, kernel)
    
    # CPU 路徑（原有邏輯）
    if method == 'auto':
        ksize = kernel.shape[0]
        if ksize > 150:
            return convolve_fft(image, kernel)
        else:
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    elif method == 'spatial':
        return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    elif method == 'fft':
        return convolve_fft(image, kernel)
    elif method == 'gpu':
        if not GPU_AVAILABLE:
            raise RuntimeError("GPU not available, use method='auto' for fallback")
        return convolve_gpu(image, kernel)
    else:
        raise ValueError(f"Unknown method: {method}")
```

**修改點 3: 修改 `apply_halation()` 支援 GPU**

```python
# Phos_0.3.0.py (Line ~1545)

def apply_halation(
    lux: np.ndarray, 
    halation_params, 
    wavelength: float = 550.0,
    use_gpu: bool = False  # 新增參數
) -> np.ndarray:
    """
    應用 Halation（背層反射）效果
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        halation_params: HalationParams 對象
        wavelength: 當前通道的波長（nm）
        use_gpu: 是否使用 GPU 加速
        
    Returns:
        應用 Halation 後的光度數據
    """
    # ... (前面邏輯不變)
    
    if halation_params.psf_type == "exponential":
        sigma_base = halation_params.psf_radius * 0.2
        sigma_small = sigma_base
        sigma_medium = sigma_base * 2.0
        sigma_large = sigma_base * 4.0
        
        ksize_small = 61
        ksize_medium = 121
        ksize_large = 151
        
        # ===== GPU 加速路徑 =====
        if use_gpu and GPU_AVAILABLE:
            from phos_gpu import convolve_pytorch
            
            # 使用 PyTorch，一次傳輸 3 個核
            kernel_small = get_gaussian_kernel(sigma_small, ksize_small)
            kernel_medium = get_gaussian_kernel(sigma_medium, ksize_medium)
            kernel_large = get_gaussian_kernel(sigma_large, ksize_large)
            
            halation_layer = (
                convolve_pytorch(halation_energy, kernel_small) * 0.5 +
                convolve_pytorch(halation_energy, kernel_medium) * 0.3 +
                convolve_pytorch(halation_energy, kernel_large) * 0.2
            )
        else:
            # CPU 路徑（原有邏輯）
            halation_layer = (
                cv2.GaussianBlur(halation_energy, (ksize_small, ksize_small), sigma_small) * 0.5 +
                cv2.GaussianBlur(halation_energy, (ksize_medium, ksize_medium), sigma_medium) * 0.3 +
                cv2.GaussianBlur(halation_energy, (ksize_large, ksize_large), sigma_large) * 0.2
            )
    
    # ... (後續邏輯不變)
```

---

### 3. Streamlit UI 整合

**修改 `Phos_0.3.0.py` 主程式**

```python
# Phos_0.3.0.py (Line ~1800, Streamlit 側邊欄)

def main():
    # ... (前面邏輯)
    
    # ===== GPU 加速控制面板 =====
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚡ GPU 加速")
    
    gpu_info = get_gpu_info()
    
    if gpu_info['available']:
        # 顯示 GPU 資訊
        backend_name = {
            'mps': 'Apple Metal (MPS)',
            'cuda': 'NVIDIA CUDA',
            'cpu': 'CPU Only'
        }.get(gpu_info['backend'], 'Unknown')
        
        st.sidebar.success(f"🚀 GPU 可用: {backend_name}")
        st.sidebar.caption(f"裝置: {gpu_info['device_name']}")
        
        # GPU 開關
        use_gpu = st.sidebar.checkbox(
            "啟用 GPU 加速", 
            value=True,
            help="使用 GPU 加速卷積運算（Halation, Bloom）\n預期加速: 3-5x (macOS M3)"
        )
        
        # 顯示效能提示
        if use_gpu:
            st.sidebar.info("💡 GPU 模式：預期處理時間 0.6-0.8 秒 (2000×3000)")
    else:
        st.sidebar.warning("💻 GPU 不可用")
        st.sidebar.caption(f"原因: {gpu_info.get('reason', 'Unknown')}")
        
        if GPU_BACKEND == 'cpu' and not PYTORCH_AVAILABLE:
            st.sidebar.info("📦 安裝 PyTorch 以啟用 GPU 加速:\n```\npip install torch torchvision\n```")
        
        use_gpu = False
    
    # ... (後續處理邏輯中傳遞 use_gpu 參數)
    
    # 範例：處理影像時傳遞 use_gpu
    if st.button("處理影像"):
        with st.spinner("處理中..."):
            # ... (其他處理邏輯)
            
            # 應用 Halation（使用 GPU）
            if film.halation_params.enabled:
                lux_r = apply_halation(lux_r, film.halation_params, wavelength=650.0, use_gpu=use_gpu)
                lux_g = apply_halation(lux_g, film.halation_params, wavelength=550.0, use_gpu=use_gpu)
                lux_b = apply_halation(lux_b, film.halation_params, wavelength=450.0, use_gpu=use_gpu)
```

---

## 📊 驗收標準

### 功能驗收

- [ ] MPS GPU 自動檢測成功
- [ ] `convolve_gpu()` 正常運作
- [ ] Streamlit UI 顯示 GPU 狀態
- [ ] GPU 開關可正常切換
- [ ] GPU 失敗時自動 fallback CPU

### 效能驗收 (M3 晶片)

- [ ] 單次卷積 (201×201, 2000×3000): <80ms (vs CPU 250ms, >3x)
- [ ] Halation (3通道): <450ms (vs CPU 1.4s, >3x)
- [ ] 端到端處理: <0.8s (vs CPU 2.1s, >2.5x)

### 精度驗收

- [ ] GPU vs CPU PSNR >40dB
- [ ] 最大像素誤差 <0.01
- [ ] 能量守恆誤差 <0.1%

### 穩定性驗收

- [ ] 連續處理 10 張影像無錯誤
- [ ] 記憶體無洩漏（長時間運行）
- [ ] 批次處理與單張處理結果一致

---

## ⚠️ 已知限制與風險

### 限制

1. **MPS 加速比低於 NVIDIA CUDA**
   - M3: 3-4x
   - NVIDIA RTX 3090: 8-10x
   - 原因：MPS 優化較少，Metal API 限制

2. **首次調用開銷**
   - PyTorch 需初始化 GPU（~100-200ms）
   - 後續調用無此開銷

3. **記憶體限制**
   - 統一記憶體架構：與系統共享 RAM
   - M3 (8GB 型號): 可能 OOM（大批次）

### 風險

1. **PyTorch 版本相容性**
   - MPS 支援在 PyTorch 1.12+ 才穩定
   - 需要 macOS 12.3+

2. **Metal API 限制**
   - 某些操作可能無 MPS 實作
   - Fallback CPU 時效能退化

---

## 📋 時程規劃

### Week 1 (Day 1-2)
- [x] 制定實施計畫（本文件）
- [ ] 安裝 PyTorch 並驗證 MPS
- [ ] 實作 `phos_gpu.py` 基礎版本
- [ ] 基準測試（單次卷積）

### Week 1 (Day 3-4)
- [ ] 整合到 `Phos_0.3.0.py`
- [ ] Streamlit UI 整合
- [ ] 端到端測試
- [ ] 精度驗證

### Week 1 (Day 5)
- [ ] 效能優化（批次處理）
- [ ] 錯誤處理完善
- [ ] 文檔更新

### Week 2 (Day 6-7)
- [ ] 用戶測試（實際影像）
- [ ] Bug 修復
- [ ] 最終文檔整理

---

## 🎯 下一步行動

### 立即執行 (今天)

1. **安裝 PyTorch**
```bash
pip install torch torchvision
python3 -c "import torch; print(torch.backends.mps.is_available())"
```

2. **創建 `phos_gpu.py`**
   - 複製上方完整程式碼
   - 測試 MPS 可用性

3. **基準測試**
```bash
python3 phos_gpu.py
```

### 後續執行 (本週)

4. **整合到主程式**
   - 修改 `convolve_adaptive()`
   - 修改 `apply_halation()`

5. **UI 整合**
   - Streamlit 側邊欄添加 GPU 控制

6. **端到端測試**
```bash
streamlit run Phos_0.3.0.py
```

---

**狀態**: 📝 計畫完成，等待執行  
**預期完成時間**: 1 週  
**負責人**: Main Agent  
**文檔版本**: v1.0
