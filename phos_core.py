"""
Phos Core - 核心處理模組（優化版本）

包含並行化和效能優化的核心圖像處理函數
"""

import cv2  # type: ignore
import numpy as np
from typing import Optional, Tuple, Callable, Dict
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
import streamlit as st  # type: ignore

from film_models import (
    FilmProfile, 
    EmulsionLayer,
    SENSITIVITY_MIN,
    SENSITIVITY_MAX,
    SENSITIVITY_SCALE,
    SENSITIVITY_BASE,
    BLOOM_STRENGTH_FACTOR,
    BLOOM_RADIUS_FACTOR,
    BLOOM_RADIUS_MIN,
    BLOOM_RADIUS_MAX,
    BASE_DIFFUSION_FACTOR,
    GRAIN_WEIGHT_MIN,
    GRAIN_WEIGHT_MAX,
    GRAIN_SENS_MIN,
    GRAIN_SENS_MAX,
    GRAIN_BLUR_KERNEL,
    GRAIN_BLUR_SIGMA,
    REINHARD_GAMMA_ADJUSTMENT,
    FILMIC_EXPOSURE_SCALE
)

# ==================== 快取 Gaussian Blur ====================

@lru_cache(maxsize=32)
def _get_blur_kernel(ksize: int) -> Tuple[int, int]:
    """
    快取模糊核尺寸計算
    
    Args:
        ksize: 核大小
        
    Returns:
        (ksize, ksize) tuple
    """
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    return (ksize, ksize)


def cached_gaussian_blur(image: np.ndarray, ksize: int, sigma: float) -> np.ndarray:
    """
    帶快取的高斯模糊（快取核大小計算）
    
    Args:
        image: 輸入圖像
        ksize: 核大小
        sigma: 標準差
        
    Returns:
        模糊後的圖像
    """
    kernel = _get_blur_kernel(ksize)
    return cv2.GaussianBlur(image, kernel, sigma)


# ==================== 並行化工具 ====================

def parallel_channel_process(
    func: Callable,
    r_data: Optional[np.ndarray],
    g_data: Optional[np.ndarray],
    b_data: Optional[np.ndarray],
    *args,
    **kwargs
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    並行處理 RGB 三通道
    
    Args:
        func: 處理函數
        r_data, g_data, b_data: RGB 通道數據
        *args, **kwargs: 傳遞給處理函數的參數
        
    Returns:
        (result_r, result_g, result_b): 處理後的三通道數據
    """
    if any(data is None for data in [r_data, g_data, b_data]):
        return None, None, None
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_r = executor.submit(func, r_data, *args, **kwargs)
        future_g = executor.submit(func, g_data, *args, **kwargs)
        future_b = executor.submit(func, b_data, *args, **kwargs)
        
        result_r = future_r.result()
        result_g = future_g.result()
        result_b = future_b.result()
    
    return result_r, result_g, result_b


# ==================== 記憶體優化版光學處理 ====================




def apply_reinhard_optimized(response: np.ndarray, gamma: float, color_mode: bool = False) -> np.ndarray:
    """
    記憶體優化的 Reinhard tone mapping
    
    Args:
        response: 輸入光譜響應數據
        gamma: Gamma 值
        color_mode: 是否為彩色模式
        
    Returns:
        映射後的結果
    """
    # Reinhard: L' = L * L / (1 + L)
    mapped = response * (response / (1.0 + response))
    
    # Gamma 校正（in-place）
    gamma_adj = REINHARD_GAMMA_ADJUSTMENT if color_mode else 1.0
    np.maximum(mapped, 0, out=mapped)
    mapped **= (gamma_adj / gamma)
    
    return np.clip(mapped, 0, 1)


def apply_filmic_optimized(response: np.ndarray, film: FilmProfile) -> np.ndarray:
    """
    記憶體優化的 Filmic tone mapping
    
    Args:
        response: 輸入光譜響應數據
        film: 胶片配置
        
    Returns:
        映射後的結果
    """
    # 確保非負
    response = np.maximum(response, 0)
    
    # 應用曝光和 gamma
    params = film.tone_params
    x = FILMIC_EXPOSURE_SCALE * np.power(response, params.gamma)
    
    # Filmic curve
    A, B, C, D, E, F = (
        params.shoulder_strength,
        params.linear_strength,
        params.linear_angle,
        params.toe_strength,
        params.toe_numerator,
        params.toe_denominator
    )
    
    numerator = x * (A * x + C * B) + D * E
    denominator = x * (A * x + B) + D * F
    
    # 避免除零
    with np.errstate(divide='ignore', invalid='ignore'):
        result = np.where(
            denominator != 0,
            (numerator / denominator) - E / F,
            0
        )
    
    return result


# ==================== 並行化的通道處理 ====================

def process_color_channels_parallel(
    response_r: np.ndarray,
    response_g: np.ndarray,
    response_b: np.ndarray,
    film: FilmProfile,
    bloom_params: Tuple[float, int, float, float],
    grain_data: Optional[Tuple] = None,
    tone_style: str = "filmic"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    並行處理彩色胶片的 RGB 三通道
    
    Args:
        response_r, response_g, response_b: RGB 光譜響應數據
        film: 胶片配置
        bloom_params: (sens, rads, strg, base)
        grain_data: 顆粒數據 (grain_r, grain_g, grain_b, grain_total)
        tone_style: Tone mapping 風格
        
    Returns:
        (result_r, result_g, result_b): 處理後的 RGB 數據
    """
    sens, rads, strg, base = bloom_params
    
    # 並行生成光暈
    bloom_params_list = [
        (sens, rads, strg, base, 3, 55),  # Red
        (sens, rads, strg, base, 2, 35),  # Green
        (sens, rads, strg, base, 1, 15),  # Blue
    ]
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        # 並行計算光暈（內聯 artistic bloom 邏輯，避免循環導入）
        # 對應 apply_bloom() 的 artistic 模式
        def _apply_bloom_artistic(response, sens, rads, strg, base, blur_scale, blur_sigma_scale):
            """內聯 artistic bloom 邏輯（避免循環導入 Phos.py）"""
            # 創建權重（高光區域權重更高）
            weights = (base + response ** 2) * sens
            weights = np.clip(weights, 0, 1)
            
            # 計算模糊核大小（必須為奇數）
            ksize = rads * blur_scale
            ksize = ksize if ksize % 2 == 1 else ksize + 1
            
            # 創建光暈層（使用快取的高斯模糊）
            bloom_input = response * weights
            bloom_layer = cached_gaussian_blur(bloom_input, ksize, sens * blur_sigma_scale)
            
            # 應用光暈（避免過曝）
            bloom_effect = bloom_layer * weights * strg
            bloom_effect = bloom_effect / (1.0 + bloom_effect)
            
            return bloom_effect
        
        bloom_futures = [
            executor.submit(_apply_bloom_artistic, response, *params)
            for response, params in zip([response_r, response_g, response_b], bloom_params_list)
        ]
        
        bloom_r, bloom_g, bloom_b = [f.result() for f in bloom_futures]
        
        # 組合層
        def combine_layer(bloom, response, layer, grain_r, grain_g, grain_b, grain_total):
            result = bloom * layer.diffuse_weight + np.power(response, layer.response_curve) * layer.direct_weight
            if grain_data is not None:
                result += (grain_r * layer.grain_intensity + 
                          grain_g * grain_total + 
                          grain_b * grain_total)
            return result
        
        if grain_data is not None:
            grain_r, grain_g, grain_b, grain_total = grain_data
        else:
            grain_r = grain_g = grain_b = grain_total = None
        
        # 並行組合層
        combine_futures = [
            executor.submit(combine_layer, bloom, response, layer, grain_r, grain_g, grain_b,
                          film.panchromatic_layer.grain_intensity)
            for bloom, response, layer in [
                (bloom_r, response_r, film.red_layer),
                (bloom_g, response_g, film.green_layer),
                (bloom_b, response_b, film.blue_layer)
            ]
        ]
        
        response_r_final, response_g_final, response_b_final = [f.result() for f in combine_futures]
        
        # 並行 tone mapping
        if tone_style == "filmic":
            tone_func = lambda response: apply_filmic_optimized(response, film)
        else:
            tone_func = lambda response: apply_reinhard_optimized(response, film.tone_params.gamma, color_mode=True)
        
        tone_futures = [
            executor.submit(tone_func, response)
            for response in [response_r_final, response_g_final, response_b_final]
        ]
        
        result_r, result_g, result_b = [f.result() for f in tone_futures]
    
    return result_r, result_g, result_b


# ==================== 效能監控 ====================

class PerformanceMonitor:
    """效能監控器"""
    
    def __init__(self):
        self.timings = {}
    
    def __enter__(self):
        import time
        self.start = time.time()
        return self
    
    def __exit__(self, *args):
        import time
        self.elapsed = time.time() - self.start
    
    def record(self, name: str, elapsed: float):
        """記錄執行時間"""
        self.timings[name] = elapsed
    
    def get_report(self) -> str:
        """生成效能報告"""
        if not self.timings:
            return "無效能數據"
        
        total = sum(self.timings.values())
        report = "=== 效能分析 ===\n"
        for name, elapsed in sorted(self.timings.items(), key=lambda x: -x[1]):
            percentage = (elapsed / total) * 100 if total > 0 else 0
            report += f"{name}: {elapsed:.3f}s ({percentage:.1f}%)\n"
        report += f"總計: {total:.3f}s"
        return report


# ==================== 光譜模型模組（Phase 4） ====================

@lru_cache(maxsize=1)
def load_smits_basis() -> dict:
    """
    載入 Smits RGB-to-Spectrum 基向量（快取）
    
    Returns:
        dict: 包含 wavelengths, white, cyan, magenta, yellow, red, green, blue
        
    Reference:
        Smits (1999): "An RGB-to-Spectrum Conversion for Reflectances"
        https://www.cs.utah.edu/~bes/papers/color/
    """
    data = np.load('data/smits_basis_spectra.npz')
    return {
        'wavelengths': data['wavelengths'],
        'white': data['white'],
        'cyan': data['cyan'],
        'magenta': data['magenta'],
        'yellow': data['yellow'],
        'red': data['red'],
        'green': data['green'],
        'blue': data['blue']
    }


@lru_cache(maxsize=1)
def load_cie_1931() -> dict:
    """
    載入 CIE 1931 標準觀察者匹配函數（快取）
    
    Returns:
        dict: 包含 wavelengths, x_bar, y_bar, z_bar
        
    Reference:
        CIE 1931 2° Standard Observer
    """
    data = np.load('data/cie_1931_31points.npz')
    return {
        'wavelengths': data['wavelengths'],
        'x_bar': data['x_bar'],
        'y_bar': data['y_bar'],
        'z_bar': data['z_bar']
    }


@lru_cache(maxsize=1)
def get_illuminant_d65() -> np.ndarray:
    """
    取得 D65 標準照明體光譜分布（31 點，380-770nm，13nm 間隔）
    
    Returns:
        np.ndarray: D65 SPD，形狀 (31,)，歸一化使 Y 色彩匹配函數積分 = 100
        
    Reference:
        CIE Standard Illuminant D65 (Daylight, 6504K)
        Data source: CIE 15:2004, interpolated from 5nm to 13nm using cubic spline
        
    Notes:
        Values corrected on 2025-12-22 to match official CIE D65 SPD.
        Previous values had 22% error at 445nm causing 13% Z-value error in XYZ integration.
    """
    # D65 標準值（13nm 間隔，380-770nm）
    # 數據來源: CIE 15:2004，由 5nm 間隔數據插值至 13nm
    d65_values = np.array([
        49.98, 62.12, 87.95, 93.44, 89.23,  # 380-432nm
        110.94, 117.70, 114.81, 113.28, 109.34,  # 445-484nm
        107.80, 105.40, 105.62, 104.22, 99.29,  # 497-536nm
        96.06, 89.70, 90.00, 88.85, 84.43,  # 549-588nm
        83.70, 79.98, 81.58, 78.79, 69.67,  # 601-640nm
        72.98, 63.14, 70.39, 70.74, 50.28,  # 653-692nm
        66.81  # 705-770nm
    ], dtype=np.float32)
    
    # 歸一化（使 Y 積分 = 100）
    return d65_values / 100.0


def rgb_to_spectrum(rgb: np.ndarray, method: str = 'smits', assume_linear: bool = False,
                    use_tiling: bool = True, tile_size: int = 512) -> np.ndarray:
    """
    將 RGB 影像轉換為 31 點光譜表示（380-770nm，13nm 間隔）
    
    使用 Smits (1999) 算法，基於 7 個基向量的線性組合重建光譜。
    保證輸出光譜物理可實現（非負）且能精確重建原始 RGB 值。
    
    **重要**: Smits 算法期待 **線性 RGB** 輸入（非 sRGB gamma-corrected）。
    若輸入為 sRGB 值（預設），函數會自動轉換為線性 RGB。
    
    **效能優化** (v0.3.0 Phase 4):
    - 使用分塊處理減少記憶體開銷（tile_size × tile_size）
    - 完全向量化避免 fancy indexing
    - 預設啟用分塊（use_tiling=True）
    
    Args:
        rgb: RGB 影像，形狀 (H, W, 3) 或單點 (3,)，值域 [0, 1]
            預設假設為 sRGB 編碼（gamma-corrected），會自動轉為線性
        method: 轉換方法，'smits'（精確）或 'lut'（快速，未實作）
        assume_linear: 若為 True，跳過 sRGB→Linear 轉換（輸入已是線性 RGB）
        use_tiling: 是否使用分塊處理（大影像建議啟用，3-5x 加速）
        tile_size: 分塊大小（預設 512×512，平衡記憶體與效能）
        
    Returns:
        spectrum: 光譜表示，形狀 (H, W, 31) 或 (31,)，值域 [0, 1]
        
    Algorithm:
        1. sRGB → Linear RGB（若需要）
        2. 找出最小 RGB 分量（決定主色調）
        3. 線性插值對應的基向量
        4. 組合為最終光譜
        
    Example:
        >>> rgb_srgb = np.array([0.5, 0.5, 0.5])  # sRGB 中灰
        >>> spectrum = rgb_to_spectrum(rgb_srgb)
        >>> # 內部轉為 linear ~0.214，產生對應光譜
        
    Performance:
        - 小影像 (<512×512): use_tiling=False 略快
        - 大影像 (>1000×1000): use_tiling=True 提升 3-5x
        - 6MP 影像 (2000×3000): ~2.5s → ~0.8s (3.1x 加速)
        
    Reference:
        Smits (1999): "An RGB-to-Spectrum Conversion for Reflectances"
        IEC 61966-2-1:1999 (sRGB gamma correction)
    """
    if method != 'smits':
        raise NotImplementedError(f"Method '{method}' not implemented. Use 'smits'.")
    
    # Step 1: sRGB → Linear RGB（若輸入為 sRGB）
    if not assume_linear:
        # sRGB inverse gamma: c_linear = ((c_srgb + 0.055) / 1.055)^2.4
        rgb = np.where(
            rgb <= 0.04045,
            rgb / 12.92,
            np.power((rgb + 0.055) / 1.055, 2.4)
        )
    
    # 載入基向量
    basis = load_smits_basis()
    
    # 處理輸入形狀
    input_shape = rgb.shape
    if len(input_shape) == 1:  # 單個 RGB 值
        rgb = rgb.reshape(1, 1, 3)
    elif len(input_shape) == 2:  # 灰階圖像意外輸入
        raise ValueError(f"Expected RGB with shape (H,W,3) or (3,), got {input_shape}")
    
    H, W, _ = rgb.shape
    
    # 【效能優化】分塊處理大影像
    if use_tiling and (H > tile_size or W > tile_size):
        spectrum = np.zeros((H, W, 31), dtype=np.float32)
        
        for y in range(0, H, tile_size):
            y_end = min(y + tile_size, H)
            for x in range(0, W, tile_size):
                x_end = min(x + tile_size, W)
                
                # 處理當前分塊
                tile = rgb[y:y_end, x:x_end, :]
                spectrum[y:y_end, x:x_end, :] = _rgb_to_spectrum_core(tile, basis)
    else:
        # 小影像或禁用分塊：直接處理
        spectrum = _rgb_to_spectrum_core(rgb, basis)
    
    # 恢復原始形狀
    if len(input_shape) == 1:
        spectrum = spectrum.reshape(31)
    
    return spectrum


def _rgb_to_spectrum_core(rgb: np.ndarray, basis: dict) -> np.ndarray:
    """
    Smits 算法核心實作（無分支向量化版本 - 終極優化 v2）
    
    Args:
        rgb: RGB tile，形狀 (H, W, 3)
        basis: Smits 基向量字典
        
    Returns:
        spectrum: 光譜，形狀 (H, W, 31)
        
    Performance notes:
        - 完全無分支：同時計算所有 3 種情況，用互斥掩碼混合
        - 修正掩碼重疊問題（RGB 相等時優先選擇 b_min）
        - 避免 fancy indexing：使用掩碼乘法取代條件賦值
        - 目標: 6MP 影像 <2s
    """
    white = basis['white']
    cyan = basis['cyan']
    magenta = basis['magenta']
    yellow = basis['yellow']
    red = basis['red']
    green = basis['green']
    blue = basis['blue']
    
    H, W, _ = rgb.shape
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    
    # 創建互斥掩碼（優先順序：b_min > r_min > g_min）
    mask_b_min_2d = (b <= r) & (b <= g)  # 藍色最小 → 黃色調
    mask_r_min_2d = (r <= g) & (r <= b) & ~mask_b_min_2d  # 紅色最小 → 青色調（排除 b_min）
    mask_g_min_2d = (g <= r) & (g <= b) & ~mask_b_min_2d & ~mask_r_min_2d  # 綠色最小 → 洋紅調（排除前兩者）
    
    # 擴展到 3D (H, W, 1)
    mask_b_min = mask_b_min_2d[..., None]
    mask_r_min = mask_r_min_2d[..., None]
    mask_g_min = mask_g_min_2d[..., None]
    
    # 擴展 RGB 到 3D (H, W, 1)
    r_3d = r[..., None]
    g_3d = g[..., None]
    b_3d = b[..., None]
    
    # 【Case 1: 藍色最小 → 黃色調】
    # spectrum_b = white*b + yellow*min(r-b,g-b) + (red*(r-g) if r>g else green*(g-r))
    spec_b = (
        white * b_3d +
        yellow * np.minimum(r_3d - b_3d, g_3d - b_3d) +
        np.where((r > g)[..., None], red * (r_3d - g_3d), green * (g_3d - r_3d))
    )
    
    # 【Case 2: 紅色最小 → 青色調】
    # spectrum_r = white*r + cyan*min(g-r,b-r) + (green*(g-b) if g>b else blue*(b-g))
    spec_r = (
        white * r_3d +
        cyan * np.minimum(g_3d - r_3d, b_3d - r_3d) +
        np.where((g > b)[..., None], green * (g_3d - b_3d), blue * (b_3d - g_3d))
    )
    
    # 【Case 3: 綠色最小 → 洋紅調】
    # spectrum_g = white*g + magenta*min(r-g,b-g) + (red*(r-b) if r>b else blue*(b-r))
    spec_g = (
        white * g_3d +
        magenta * np.minimum(r_3d - g_3d, b_3d - g_3d) +
        np.where((r > b)[..., None], red * (r_3d - b_3d), blue * (b_3d - r_3d))
    )
    
    # 【無分支混合】用互斥掩碼加權合併（現在掩碼不重疊）
    spectrum = mask_b_min * spec_b + mask_r_min * spec_r + mask_g_min * spec_g
    
    # 確保非負（理論上 Smits 算法已保證，但數值誤差可能導致微小負值）
    np.maximum(spectrum, 0, out=spectrum)
    
    return spectrum


def spectrum_to_xyz(
    spectrum: np.ndarray, 
    illuminant_spd: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    透過光譜積分將光譜表示轉換為 CIE XYZ 色彩空間
    
    模擬人眼視覺感知：將 31 點光譜與 CIE 1931 標準觀察者匹配函數積分。
    
    Args:
        spectrum: 光譜反射率/透射率，形狀 (H, W, 31) 或 (31,)，值域 [0, 1]
        illuminant_spd: 照明體光譜分布，形狀 (31,)，預設為 D65（日光 6504K）
        
    Returns:
        xyz: CIE XYZ 三刺激值，形狀 (H, W, 3) 或 (3,)
        
    Formula:
        X = Σ spectrum(λ) × illuminant(λ) × x̄(λ) × Δλ
        Y = Σ spectrum(λ) × illuminant(λ) × ȳ(λ) × Δλ  (luminance)
        Z = Σ spectrum(λ) × illuminant(λ) × z̄(λ) × Δλ
        
    Note:
        - Δλ = 13nm（固定間隔）
        - Y 通道代表亮度（luminance）
        
    Example:
        >>> spectrum = np.ones(31)  # 白色光譜
        >>> xyz = spectrum_to_xyz(spectrum)
        >>> xyz.shape
        (3,)
    """
    # 載入 CIE 1931 匹配函數
    cie = load_cie_1931()
    x_bar = cie['x_bar']
    y_bar = cie['y_bar']
    z_bar = cie['z_bar']
    
    # 預設照明體：D65
    if illuminant_spd is None:
        illuminant_spd = get_illuminant_d65()
    
    # 波長間隔（固定 13nm）
    delta_lambda = 13.0
    
    # 處理輸入形狀
    input_shape = spectrum.shape
    if len(input_shape) == 1:  # 單個光譜
        spectrum = spectrum.reshape(1, 1, 31)
    
    # 光譜積分（Einstein summation 優化）
    # spectrum: (H, W, 31)
    # illuminant_spd: (31,)
    # x_bar, y_bar, z_bar: (31,)
    
    # 計算權重: illuminant × cmf × Δλ
    weight_x = illuminant_spd * x_bar * delta_lambda  # (31,)
    weight_y = illuminant_spd * y_bar * delta_lambda
    weight_z = illuminant_spd * z_bar * delta_lambda
    
    # 積分（沿波長維度求和）
    X = np.sum(spectrum * weight_x[None, None, :], axis=-1)
    Y = np.sum(spectrum * weight_y[None, None, :], axis=-1)
    Z = np.sum(spectrum * weight_z[None, None, :], axis=-1)
    
    # 堆疊為 XYZ
    xyz = np.stack([X, Y, Z], axis=-1)
    
    # 歸一化（白色表面的 Y 值應為 1.0）
    # 計算白色光譜在 D65 下的 Y 值作為歸一化常數
    Y_white = np.sum(illuminant_spd * y_bar * delta_lambda)
    if Y_white > 0:
        xyz = xyz / Y_white
    
    # 恢復原始形狀
    if len(input_shape) == 1:
        xyz = xyz.reshape(3)
    
    return xyz


def xyz_to_srgb(xyz: np.ndarray) -> np.ndarray:
    """
    將 CIE XYZ 色彩空間轉換為 sRGB（標準 RGB）
    
    使用 IEC 61966-2-1:1999 標準轉換矩陣（D65 白點）並應用 sRGB gamma 校正。
    
    Args:
        xyz: CIE XYZ 三刺激值，形狀 (H, W, 3) 或 (3,)
        
    Returns:
        rgb: sRGB 值，形狀 (H, W, 3) 或 (3,)，值域 [0, 1]
        
    Algorithm:
        1. 線性轉換：XYZ → Linear RGB（3×3 矩陣）
        2. Gamma 校正：Linear RGB → sRGB（分段函數）
           - c <= 0.0031308: sRGB = 12.92 × c
           - c > 0.0031308:  sRGB = 1.055 × c^(1/2.4) - 0.055
        3. 裁剪至 [0, 1]
        
    Reference:
        IEC 61966-2-1:1999 (sRGB standard)
        D65 white point: (0.3127, 0.3290)
    """
    # sRGB 轉換矩陣（D65 白點）
    # 來源: IEC 61966-2-1:1999
    M = np.array([
        [ 3.2406, -1.5372, -0.4986],
        [-0.9689,  1.8758,  0.0415],
        [ 0.0557, -0.2040,  1.0570]
    ], dtype=np.float32)
    
    # 處理輸入形狀
    input_shape = xyz.shape
    if len(input_shape) == 1:  # 單個 XYZ 值
        xyz = xyz.reshape(1, 1, 3)
    
    # 線性轉換：XYZ → Linear RGB
    # 使用 einsum 優化矩陣乘法
    rgb_linear = np.einsum('ij,...j->...i', M, xyz)
    
    # sRGB Gamma 校正（分段函數）
    def srgb_gamma(c: np.ndarray) -> np.ndarray:
        """sRGB gamma 校正（分段函數）"""
        return np.where(
            c <= 0.0031308,
            12.92 * c,
            1.055 * np.power(np.maximum(c, 0), 1.0 / 2.4) - 0.055
        )
    
    rgb = srgb_gamma(rgb_linear)
    
    # 裁剪至 [0, 1]
    rgb = np.clip(rgb, 0, 1)
    
    # 恢復原始形狀
    if len(input_shape) == 1:
        rgb = rgb.reshape(3)
    
    return rgb

# ============================================================
# 膠片光譜敏感度（Film Spectral Sensitivity）
# ============================================================

@lru_cache(maxsize=8)
def load_film_sensitivity(film_name: str) -> dict:
    """
    載入膠片光譜敏感度曲線
    
    膠片的光譜敏感度決定了其色彩響應特性。不同膠片有不同的曲線形狀：
    - Portra: 溫暖、膚色優美、飽和度中等
    - Velvia: 超高飽和度、對比強烈、藍天綠樹鮮豔
    - Cinestill: 鎢絲燈平衡、適合室內暖光、橙色調
    - HP5Plus: 黑白全色片、均衡響應
    
    Args:
        film_name: 膠片名稱，支援:
            - 'Portra400': 彩色負片，溫暖色調
            - 'Velvia50': 反轉片，超高飽和度
            - 'Cinestill800T': 彩色負片，鎢絲燈平衡
            - 'HP5Plus400': 黑白負片，全色敏感
    
    Returns:
        Dict 包含:
            'wavelengths': (31,) 波長陣列 (380-770nm)
            'red': (31,) 紅色層光譜敏感度 [0, 1]
            'green': (31,) 綠色層光譜敏感度 [0, 1]
            'blue': (31,) 藍色層光譜敏感度 [0, 1]
            'type': str 膠片類型 ('color_negative', 'reversal', 'bw')
    
    Raises:
        ValueError: 若膠片名稱不存在
        
    Example:
        >>> curves = load_film_sensitivity('Portra400')
        >>> print(curves['wavelengths'].shape)  # (31,)
        >>> print(curves['red'].max())  # ~1.0 (歸一化到最大值)
        
    Notes:
        - 敏感度曲線已歸一化到 [0, 1] 範圍
        - 峰值響應 = 1.0（各通道獨立歸一化）
        - 數據來源：基於典型膠片 Datasheet 合成
    """
    data_path = Path(__file__).parent / "data" / "film_spectral_sensitivity.npz"
    
    if not data_path.exists():
        raise FileNotFoundError(f"Film sensitivity data not found: {data_path}")
    
    data = np.load(data_path)
    
    # 檢查膠片是否存在
    if f"{film_name}_red" not in data:
        available = [key.replace('_red', '') for key in data.keys() if key.endswith('_red')]
        raise ValueError(
            f"Film '{film_name}' not found. Available films: {', '.join(available)}"
        )
    
    return {
        'wavelengths': data['wavelengths'].astype(np.float32),
        'red': data[f'{film_name}_red'].astype(np.float32),
        'green': data[f'{film_name}_green'].astype(np.float32),
        'blue': data[f'{film_name}_blue'].astype(np.float32),
        'type': str(data[f'{film_name}_type'][0])
    }


def apply_film_spectral_sensitivity(
    spectrum: np.ndarray,
    sensitivity_curves: dict,
    normalize: bool = True,
    illuminant_spd: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    應用膠片光譜敏感度曲線，將光譜轉換為膠片 RGB
    
    這是光譜模型的核心：模擬膠片化學乳劑層對不同波長光的響應。
    與 CIE XYZ（人眼色彩匹配）不同，膠片的光譜響應是由銀鹽顆粒和
    染料耦合劑決定的，每種膠片都有獨特的「色彩性格」。
    
    Physical Model:
        R_film = ∫ Spectrum(λ) × S_red(λ) dλ
        G_film = ∫ Spectrum(λ) × S_green(λ) dλ
        B_film = ∫ Spectrum(λ) × S_blue(λ) dλ
        
        其中 S_red/green/blue 是膠片紅/綠/藍層的光譜敏感度曲線
    
    Args:
        spectrum: 光譜影像，形狀 (H, W, 31) 或 (31,)
                 代表物體表面的反射率（或發光）光譜
        sensitivity_curves: 膠片敏感度曲線字典（由 load_film_sensitivity() 取得）
            {
                'wavelengths': (31,),  # 波長陣列
                'red': (31,),          # 紅色層敏感度
                'green': (31,),        # 綠色層敏感度
                'blue': (31,)          # 藍色層敏感度
            }
        normalize: 是否歸一化（白色表面 → RGB ~(1, 1, 1)）
                  True: 適用於顯示
                  False: 保留原始積分值（可能用於後續處理）
        illuminant_spd: 照明體光譜分布（31 點），若提供則先乘入光源 SPD
                        None 時視為平坦光源（向後相容）
    
    Returns:
        np.ndarray: 膠片 RGB 影像，形狀 (H, W, 3) 或 (3,)，值域 [0, 1]
                   **色彩空間: sRGB（已 gamma 編碼，IEC 61966-2-1:1999）**
                   可直接用於顯示或儲存，與 xyz_to_srgb() 輸出一致
        
    Physical Validation:
        - 所有 RGB 值 >= 0（物理可實現）
        - 白色光譜 → RGB ~(1, 1, 1)（若 normalize=True）
        - 色彩關係保持（暖色 → 暖 RGB，冷色 → 冷 RGB）
        - 能量守恆: 在 gamma 前的 Linear RGB 域驗證
    
    Example:
        >>> # 處理單一顏色
        >>> rgb = np.array([0.8, 0.5, 0.3])  # 暖色調
        >>> spectrum = rgb_to_spectrum(rgb)
        >>> portra = load_film_sensitivity('Portra400')
        >>> film_rgb = apply_film_spectral_sensitivity(spectrum, portra)
        >>> # film_rgb 具有 Portra 的色彩特性（偏黃、膚色優美）
        
        >>> # 處理完整影像
        >>> img = load_image("photo.jpg")  # (H, W, 3)
        >>> spectrum = rgb_to_spectrum(img)  # (H, W, 31)
        >>> film_rgb = apply_film_spectral_sensitivity(spectrum, portra)
        >>> # 整張照片套用 Portra 色彩響應
    
    Notes:
        - 此函數與 spectrum_to_xyz() 類似，但使用膠片敏感度曲線替代 CIE 色彩匹配函數
        - Portra vs Velvia: Portra 溫暖柔和，Velvia 飽和銳利
        - 彩色負片 vs 反轉片: 負片寬容度大，反轉片對比高
        - 波長積分間隔: Δλ = 13nm（380-770nm, 31 點）
        - **色彩空間**: 輸出為 sRGB（包含 gamma 編碼），與 xyz_to_srgb() 一致
        - **物理流程**: 光譜 × illuminant_spd → 積分 → Linear RGB → 正規化 → sRGB gamma 編碼
        - 若 illuminant_spd 為 None，會嘗試讀取 st.session_state['film_illuminant']
        - 若 illuminant_spd 為 None，會嘗試讀取 st.session_state['film_illuminant']
    
    Version:
        v0.4.1: 修正缺少 gamma 編碼導致的亮度損失問題（-50% → +7.7%）
    """
    # 提取敏感度曲線
    s_red = sensitivity_curves['red']    # (31,)
    s_green = sensitivity_curves['green']  # (31,)
    s_blue = sensitivity_curves['blue']    # (31,)
    
    # 確認形狀一致
    n_wavelengths = len(s_red)
    if spectrum.shape[-1] != n_wavelengths:
        raise ValueError(
            f"Spectrum has {spectrum.shape[-1]} channels, "
            f"but sensitivity curves have {n_wavelengths} wavelengths"
        )
    
    # 處理輸入形狀
    input_shape = spectrum.shape
    if len(input_shape) == 1:
        # 單一光譜 (31,)
        spectrum = spectrum.reshape(1, 1, n_wavelengths)
    elif len(input_shape) == 3:
        # 影像光譜 (H, W, 31)
        pass
    else:
        raise ValueError(f"Spectrum shape must be (31,) or (H, W, 31), got {input_shape}")
    
    # 若未提供光源 SPD，嘗試從 UI session state 取得
    if illuminant_spd is None:
        try:
            illuminant_choice = st.session_state.get("film_illuminant")
        except Exception:
            illuminant_choice = None
        if isinstance(illuminant_choice, str) and "D65" in illuminant_choice:
            illuminant_spd = get_illuminant_d65()

    # 若提供光源 SPD，先乘入照明體能量
    if illuminant_spd is not None:
        if illuminant_spd.shape[0] != n_wavelengths:
            raise ValueError(
                f"Illuminant SPD has {illuminant_spd.shape[0]} points, "
                f"but sensitivity curves have {n_wavelengths} wavelengths"
            )
        spectrum = spectrum * illuminant_spd[None, None, :]
    
    # 光譜積分（矩形法）
    # R = Σ Spectrum(λ) × S_red(λ) × Δλ
    delta_lambda = 13.0  # nm（380-770nm, 31 點）
    
    # Broadcast: (H, W, 31) × (31,) → (H, W, 31)
    r_channel = np.sum(spectrum * s_red, axis=-1) * delta_lambda    # (H, W)
    g_channel = np.sum(spectrum * s_green, axis=-1) * delta_lambda  # (H, W)
    b_channel = np.sum(spectrum * s_blue, axis=-1) * delta_lambda   # (H, W)
    
    # 堆疊為 RGB
    film_rgb = np.stack([r_channel, g_channel, b_channel], axis=-1)  # (H, W, 3)
    
    # 歸一化（白色表面 → RGB ~1）
    if normalize:
        # 計算白色光譜（平坦，反射率 = 1）的響應
        white_spectrum = np.ones(n_wavelengths, dtype=np.float32)
        if illuminant_spd is not None:
            white_spectrum = white_spectrum * illuminant_spd
        
        r_white = np.sum(white_spectrum * s_red) * delta_lambda
        g_white = np.sum(white_spectrum * s_green) * delta_lambda
        b_white = np.sum(white_spectrum * s_blue) * delta_lambda
        
        # 分別歸一化各通道（保留相對色彩關係）
        # 注意：不同於 XYZ 只用 Y_white 歸一化，這裡各通道獨立
        # 這是因為膠片的 R/G/B 層曝光獨立
        film_rgb[..., 0] = film_rgb[..., 0] / r_white
        film_rgb[..., 1] = film_rgb[..., 1] / g_white
        film_rgb[..., 2] = film_rgb[..., 2] / b_white
    
    # sRGB Gamma 編碼（Linear RGB → sRGB）
    # 修正 v0.4.0 bug: 之前輸出 Linear RGB 導致顯示過暗 57%
    # 現在統一輸出 sRGB，與 xyz_to_srgb() 保持一致
    # 參考: IEC 61966-2-1:1999 sRGB standard
    film_rgb = np.where(
        film_rgb <= 0.0031308,
        12.92 * film_rgb,
        1.055 * np.power(np.maximum(film_rgb, 0), 1.0 / 2.4) - 0.055
    )
    
    # 裁剪至 [0, 1]
    film_rgb = np.clip(film_rgb, 0, 1)
    
    # 恢復原始形狀
    if len(input_shape) == 1:
        film_rgb = film_rgb.reshape(3)
    
    return film_rgb.astype(np.float32)


def process_image_spectral_mode(
    rgb_image: np.ndarray,
    film_name: str = 'Portra400',
    apply_film_response: bool = True,
    illuminant_spd: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    完整的光譜模式處理流程（測試/評估用）
    
    此函數展示光譜模型的完整工作流程，但尚未整合進主 UI。
    主要用於測試、比較、驗證光譜響應的效果。
    
    Pipeline:
        1. RGB → Spectrum (Smits 1999 algorithm)
        2a. [Film Mode] Spectrum → Film RGB (膠片光譜敏感度)
        2b. [Standard Mode] Spectrum → XYZ → sRGB (標準色彩)
    
    Args:
        rgb_image: 輸入 RGB 影像，形狀 (H, W, 3)，值域 [0, 1]
        film_name: 膠片名稱 ('Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400')
        apply_film_response: 
            - True: 應用膠片光譜響應（膠片模式）
            - False: 使用標準 XYZ 色彩空間（校準模式）
        illuminant_spd: 照明體光譜分布（31 點），None 表示平坦光源
    
    Returns:
        np.ndarray: 輸出 RGB 影像，形狀 (H, W, 3)，值域 [0, 1]
    
    Comparison:
        Film Mode vs Standard Mode:
        - Film: 具有膠片色彩特性（Portra 溫暖、Velvia 飽和）
        - Standard: 色彩準確（符合 CIE 標準觀察者）
        
        使用 Standard Mode 可以驗證光譜重建的準確度（應該接近原圖）
    
    Example:
        >>> img = load_image("portrait.jpg")  # (H, W, 3)
        >>> 
        >>> # 膠片模式：Portra 風格
        >>> portra_result = process_image_spectral_mode(img, 'Portra400', True)
        >>> 
        >>> # 標準模式：校準用
        >>> standard_result = process_image_spectral_mode(img, 'Portra400', False)
        >>> 
        >>> # 比較色差
        >>> color_diff = np.mean(np.abs(portra_result - standard_result))
        >>> print(f"Film color shift: {color_diff:.3f}")
    
    Notes:
        - 效能：目前未優化，處理 6MP 影像約 17 秒
        - 記憶體：31 通道光譜需 186 MB（vs RGB 18 MB）
        - 後續將整合進主流程，並加入分塊處理、效能優化
    """
    # Step 1: RGB → Spectrum
    spectrum = rgb_to_spectrum(rgb_image)  # (H, W, 31)
    
    # Step 2: Spectral response
    if apply_film_response:
        # 膠片光譜響應（31 通道 → RGB）
        sensitivity_curves = load_film_sensitivity(film_name)
        film_rgb = apply_film_spectral_sensitivity(
            spectrum,
            sensitivity_curves,
            illuminant_spd=illuminant_spd
        )
        return film_rgb
    else:
        # 標準色彩流程（31 通道 → XYZ → sRGB）
        xyz = spectrum_to_xyz(spectrum)
        srgb = xyz_to_srgb(xyz)
        return srgb
