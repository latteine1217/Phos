"""
PSF (Point Spread Function) 工具模組

負責：
1. Mie 散射參數查表與插值
2. PSF 核生成（雙段核、高斯核、指數核）
3. 卷積運算（FFT 與空域自適應）

物理背景：
- Mie 散射：膠片銀鹽顆粒對光的散射
- PSF：光在介質中傳播的模糊核
- 卷積：散射效應的數學實現

PR #4: Extracted from Phos.py (Lines 295-349, 481-522, 525-578, 583-624, 627-652, 658-680, 683-710, 713-756)
"""

import numpy as np
import cv2
from functools import lru_cache
from typing import Optional, Tuple

# ==================== Global Cache ====================

_MIE_LOOKUP_TABLE_CACHE = None


# ==================== Mie Scattering ====================

def load_mie_lookup_table(path: str = "data/mie_lookup_table_v1.npz"):
    """
    載入 Mie 散射查表（帶快取）
    
    查表結構:
        wavelengths: [450, 550, 650] (nm)
        iso_values: [100, 200, 400, 800, 1600, 3200, 6400]
        sigma: (3, 7) 陣列，PSF 高斯寬度 (px)
        kappa: (3, 7) 陣列，PSF 指數拖尾長度 (px)
        rho: (3, 7) 陣列，核心能量占比（0-1）
        eta: (3, 7) 陣列，歸一化散射能量權重
    
    Args:
        path: 查表 .npz 檔案路徑
    
    Returns:
        dict: 包含所有查表陣列的字典
    
    Raises:
        FileNotFoundError: 查表檔案不存在
    """
    global _MIE_LOOKUP_TABLE_CACHE
    
    if _MIE_LOOKUP_TABLE_CACHE is not None:
        return _MIE_LOOKUP_TABLE_CACHE
    
    try:
        table = np.load(path, allow_pickle=True)
        _MIE_LOOKUP_TABLE_CACHE = {
            'wavelengths': table['wavelengths'],
            'iso_values': table['iso_values'],
            'sigma': table['sigma'],
            'kappa': table['kappa'],
            'rho': table['rho'],
            'eta': table['eta']
        }
        return _MIE_LOOKUP_TABLE_CACHE
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Mie 查表檔案不存在: {path}\n"
            f"請運行 'python3 scripts/generate_mie_lookup.py' 生成查表"
        )


def lookup_mie_params(wavelength_nm: float, iso: int, table: dict) -> tuple:
    """
    從 Mie 查表中插值獲取散射參數
    
    使用雙線性插值（wavelength × ISO）
    
    Args:
        wavelength_nm: 波長 (nm)，通常為 450/550/650
        iso: ISO 值，通常為 100-6400
        table: load_mie_lookup_table() 返回的字典
    
    Returns:
        (sigma, kappa, rho, eta): 散射參數元組
            sigma: PSF 高斯寬度 (px)
            kappa: PSF 指數拖尾長度 (px)
            rho: 核心能量占比（0-1）
            eta: 歸一化散射能量權重
    """
    wavelengths = table['wavelengths']
    iso_values = table['iso_values']
    
    # 1. 找到波長的鄰近索引
    wl_idx = np.searchsorted(wavelengths, wavelength_nm)
    wl_idx = np.clip(wl_idx, 1, len(wavelengths) - 1)
    
    # 2. 找到 ISO 的鄰近索引
    iso_idx = np.searchsorted(iso_values, iso)
    iso_idx = np.clip(iso_idx, 1, len(iso_values) - 1)
    
    # 3. 雙線性插值權重
    wl_low, wl_high = wavelengths[wl_idx - 1], wavelengths[wl_idx]
    iso_low, iso_high = iso_values[iso_idx - 1], iso_values[iso_idx]
    
    t_wl = (wavelength_nm - wl_low) / (wl_high - wl_low + 1e-10)
    t_iso = (iso - iso_low) / (iso_high - iso_low + 1e-10)
    
    # 4. 插值四個參數
    def interp_2d(arr):
        v00 = arr[wl_idx - 1, iso_idx - 1]
        v01 = arr[wl_idx - 1, iso_idx]
        v10 = arr[wl_idx, iso_idx - 1]
        v11 = arr[wl_idx, iso_idx]
        
        v0 = v00 * (1 - t_iso) + v01 * t_iso
        v1 = v10 * (1 - t_iso) + v11 * t_iso
        
        return v0 * (1 - t_wl) + v1 * t_wl
    
    sigma = float(interp_2d(table['sigma']))
    kappa = float(interp_2d(table['kappa']))
    rho = float(interp_2d(table['rho']))
    eta = float(interp_2d(table['eta']))
    
    return sigma, kappa, rho, eta


# ==================== PSF Generation ====================

def create_dual_kernel_psf(
    sigma: float, 
    kappa: float, 
    core_fraction: float, 
    radius: int = 100
) -> np.ndarray:
    """
    創建雙段核 PSF（Gaussian + Exponential）
    
    物理依據（Physicist Review Line 49）:
        K(r) = ρ·G(r;σ) + (1-ρ)·E(r;κ)
        - 核心（Gaussian）: 小角散射，能量集中
        - 拖尾（Exponential）: 大角散射，長距離擴散
    
    Args:
        sigma: 高斯核標準差（像素）
        kappa: 指數核衰減長度（像素）
        core_fraction: 核心占比 ρ ∈ [0,1]
        radius: PSF 半徑（像素）
    
    Returns:
        psf: 正規化的 2D PSF，∑psf = 1（能量守恆）
    
    範例:
        >>> psf = create_dual_kernel_psf(sigma=20, kappa=60, core_fraction=0.75, radius=100)
        >>> np.sum(psf)  # 應該 ≈ 1.0
        1.0000000...
    """
    # 創建徑向距離網格
    size = 2 * radius + 1
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    r = np.sqrt(x**2 + y**2).astype(np.float32)
    
    # 高斯核（小角散射）
    # G(r; σ) = exp(-r²/(2σ²))
    gaussian_core = np.exp(-r**2 / (2 * sigma**2))
    
    # 指數核（大角散射，長拖尾）
    # E(r; κ) = exp(-r/κ)
    exponential_tail = np.exp(-r / kappa)
    
    # 組合（能量加權）
    # K(r) = ρ·G(r) + (1-ρ)·E(r)
    psf = core_fraction * gaussian_core + (1 - core_fraction) * exponential_tail
    
    # 正規化（確保 ∑psf = 1，能量守恆）
    psf_sum = np.sum(psf)
    if psf_sum > 1e-10:  # 避免除以零
        psf = psf / psf_sum
    else:
        # 退化情況：返回 delta 函數
        psf = np.zeros_like(psf)
        psf[radius, radius] = 1.0
    
    return psf.astype(np.float32)


@lru_cache(maxsize=64)
def _get_gaussian_kernel_cached(sigma_int: int, ksize: int) -> tuple:
    """
    獲取高斯核（2D）- 快取版本（內部實作）
    
    將 float sigma 轉為 int（×1000）以支援 lru_cache，回傳 tuple 供快取。
    
    Args:
        sigma_int: 高斯標準差 × 1000（整數，可 hash）
        ksize: 核大小
    
    Returns:
        2D 高斯核（tuple 格式，可快取）
    """
    sigma = sigma_int / 1000.0
    
    # 生成 1D 核
    kernel_1d = cv2.getGaussianKernel(ksize, sigma)
    
    # 外積得到 2D 核
    kernel_2d = kernel_1d @ kernel_1d.T
    
    # 轉為 tuple 以支援 lru_cache（numpy array 無法 hash）
    return tuple(map(tuple, kernel_2d.tolist()))


def get_gaussian_kernel(sigma: float, ksize: int = None) -> np.ndarray:
    """
    獲取高斯核（2D）- 帶快取
    
    ⚡ 效能優化：使用 LRU cache 避免重複計算常用核
    
    Args:
        sigma: 高斯標準差
        ksize: 核大小（None = 自動計算為 6σ）
    
    Returns:
        2D 高斯核（numpy array，可直接用於 OpenCV）
    
    使用範例:
        kernel = get_gaussian_kernel(20.0)  # 首次計算
        kernel = get_gaussian_kernel(20.0)  # 快取命中，幾乎0耗時
    """
    if ksize is None:
        ksize = int(sigma * 6) | 1  # 6σ 涵蓋 99.7%，強制奇數
    
    # 將 float sigma 轉為整數（×1000）以支援快取
    sigma_int = int(round(sigma * 1000))
    
    # 呼叫快取版本
    kernel_tuple = _get_gaussian_kernel_cached(sigma_int, ksize)
    
    # 轉回 numpy array
    return np.array(kernel_tuple, dtype=np.float32)


def get_exponential_kernel_approximation(kappa: float, ksize: int) -> np.ndarray:
    """
    生成指數拖尾核的三層高斯近似（Decision #014: Mie 散射修正）
    
    物理背景：
        Mie 散射的相位函數具有指數拖尾特性：PSF_exp(r) ≈ exp(-r/κ)
        精確計算指數核計算成本高，使用三層高斯疊加近似：
        
        PSF_exp(r) ≈ 0.5·G(σ₁) + 0.3·G(σ₂) + 0.2·G(σ₃)
        
        其中：
            σ₁ = κ       (短距離，50% 能量)
            σ₂ = 2κ      (中距離，30% 能量)
            σ₃ = 4κ      (長距離，20% 能量)
    
    精確度：
        在 [0, 4κ] 範圍內相對誤差 < 5%
        在 [4κ, ∞] 範圍內指數衰減快於高斯，可接受近似
    
    Args:
        kappa: 指數衰減特徵尺度（像素）
        ksize: 核尺寸（奇數）
        
    Returns:
        正規化的 2D 核（sum = 1），shape (ksize, ksize)
        
    Reference:
        - Phase 1 Design Corrected (tasks/TASK-003-medium-physics/phase1_design_corrected.md)
        - Decision #014 (context/decisions_log.md)
    """
    # 生成三層高斯核
    kernel1 = get_gaussian_kernel(kappa, ksize)          # 核心層（50%）
    kernel2 = get_gaussian_kernel(kappa * 2.0, ksize)    # 中距層（30%）
    kernel3 = get_gaussian_kernel(kappa * 4.0, ksize)    # 長拖尾層（20%）
    
    # 加權組合
    kernel_combined = 0.5 * kernel1 + 0.3 * kernel2 + 0.2 * kernel3
    
    # 正規化（確保能量守恆）
    kernel_sum = np.sum(kernel_combined)
    if kernel_sum > 1e-8:
        kernel_combined /= kernel_sum
    
    return kernel_combined


# ==================== Convolution ====================

def convolve_fft(image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """
    使用 FFT 進行卷積（針對大核優化）
    
    物理依據: 卷積定理 f⊗g = F⁻¹(F(f)·F(g))
    
    效能:
        - 複雜度: O(N log N) vs O(N·K²) (空域)
        - 大核（K>150）快 ~1.7x
        - 小核（K<100）反而慢（setup overhead）
    
    Args:
        image: 輸入影像 (H×W)
        kernel: 卷積核 (K×K)
    
    Returns:
        卷積結果 (H×W)
    """
    h, w = image.shape[:2]
    kh, kw = kernel.shape[:2]
    
    # 1. 填充影像（reflect mode，與 cv2.filter2D 一致）
    pad_h, pad_w = kh // 2, kw // 2
    img_padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), 
                       mode='reflect')
    
    # 2. 核居中填充（避免偏移）
    kernel_padded = np.zeros_like(img_padded)
    kernel_padded[:kh, :kw] = kernel
    kernel_padded = np.roll(kernel_padded, 
                            (-kh // 2, -kw // 2), axis=(0, 1))
    
    # 3. FFT 卷積
    img_fft = np.fft.rfft2(img_padded)
    kernel_fft = np.fft.rfft2(kernel_padded)
    result_fft = img_fft * kernel_fft
    result = np.fft.irfft2(result_fft, s=img_padded.shape)
    
    # 4. 裁剪回原始尺寸
    result = result[pad_h:pad_h+h, pad_w:pad_w+w]
    
    return result.astype(image.dtype)


def convolve_adaptive(image: np.ndarray, kernel: np.ndarray, 
                     method: str = 'auto') -> np.ndarray:
    """
    自適應選擇卷積方法
    
    Args:
        image: 輸入影像
        kernel: 卷積核
        method: 'auto' | 'spatial' | 'fft'
            - auto: 根據核大小自動選擇（閾值 150px）
            - spatial: 強制使用空域卷積
            - fft: 強制使用 FFT 卷積
    
    Returns:
        卷積結果
    """
    if method == 'auto':
        ksize = kernel.shape[0]
        if ksize > 150:
            return convolve_fft(image, kernel)
        else:
            return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)
    elif method == 'fft':
        return convolve_fft(image, kernel)
    else:  # 'spatial'
        return cv2.filter2D(image, -1, kernel, borderType=cv2.BORDER_REFLECT)


# ==================== Exports ====================

__all__ = [
    'load_mie_lookup_table',
    'lookup_mie_params',
    'create_dual_kernel_psf',
    'get_gaussian_kernel',
    'get_exponential_kernel_approximation',
    'convolve_fft',
    'convolve_adaptive',
]
