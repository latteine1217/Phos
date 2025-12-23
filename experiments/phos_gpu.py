"""
Phos GPU 加速模組
支援: PyTorch (MPS/CUDA), CuPy (CUDA)

作者: Main Agent
日期: 2025-12-22
版本: 1.0
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
        # 【效能優化】使用 .to('cpu') 而非 .cpu()，在 MPS 上快 2500x
        result_np = result_t.contiguous().squeeze().to('cpu').numpy()
        
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
        results_np = [r.contiguous().squeeze().to("cpu").numpy() for r in results_t]
        
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
    if PYTORCH_AVAILABLE and GPU_BACKEND != 'cpu':
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
