"""
Phos Core - 核心處理模組（優化版本）

包含並行化和效能優化的核心圖像處理函數
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import streamlit as st

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

def generate_grain_optimized(lux_channel: np.ndarray, sens: float) -> np.ndarray:
    """
    記憶體優化的顆粒生成（使用 in-place 操作）
    
    Args:
        lux_channel: 光度通道數據
        sens: 敏感度參數
        
    Returns:
        顆粒噪聲
    """
    # 創建噪聲（直接使用 float32 節省記憶體）
    noise = np.random.normal(0, 1, lux_channel.shape).astype(np.float32)
    
    # In-place 平方
    noise **= 2
    
    # In-place 乘以隨機正負號
    noise *= np.random.choice([-1, 1], lux_channel.shape)
    
    # 創建權重（中等亮度權重最高）
    weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
    np.clip(weights, GRAIN_WEIGHT_MIN, GRAIN_WEIGHT_MAX, out=weights)
    
    # 應用權重（in-place）
    sens_grain = np.clip(sens, GRAIN_SENS_MIN, GRAIN_SENS_MAX)
    noise *= weights
    noise *= sens_grain
    
    # 添加輕微模糊
    noise = cv2.GaussianBlur(noise, GRAIN_BLUR_KERNEL, GRAIN_BLUR_SIGMA)
    
    return np.clip(noise, -1, 1)


def apply_bloom_optimized(
    lux: np.ndarray,
    sens: float,
    rads: int,
    strg: float,
    base: float,
    blur_scale: int,
    blur_sigma_scale: float
) -> np.ndarray:
    """
    記憶體優化的光暈效果
    
    Args:
        lux: 光度數據
        sens, rads, strg, base: 光暈參數
        blur_scale: 模糊核倍數
        blur_sigma_scale: 模糊 sigma 倍數
        
    Returns:
        光暈效果
    """
    # 創建權重
    weights = base + lux ** 2
    weights *= sens
    np.clip(weights, 0, 1, out=weights)
    
    # 計算模糊核大小
    ksize = rads * blur_scale
    
    # 創建光暈層（使用快取的高斯模糊）
    bloom_input = lux * weights
    bloom_layer = cached_gaussian_blur(bloom_input, ksize, sens * blur_sigma_scale)
    
    # 應用光暈（避免過曝）
    bloom_effect = bloom_layer * weights * strg
    bloom_effect = bloom_effect / (1.0 + bloom_effect)
    
    return bloom_effect


def apply_reinhard_optimized(lux: np.ndarray, gamma: float, color_mode: bool = False) -> np.ndarray:
    """
    記憶體優化的 Reinhard tone mapping
    
    Args:
        lux: 輸入光度數據
        gamma: Gamma 值
        color_mode: 是否為彩色模式
        
    Returns:
        映射後的結果
    """
    # Reinhard: L' = L * L / (1 + L)
    mapped = lux * (lux / (1.0 + lux))
    
    # Gamma 校正（in-place）
    gamma_adj = REINHARD_GAMMA_ADJUSTMENT if color_mode else 1.0
    np.maximum(mapped, 0, out=mapped)
    mapped **= (gamma_adj / gamma)
    
    return np.clip(mapped, 0, 1)


def apply_filmic_optimized(lux: np.ndarray, film: FilmProfile) -> np.ndarray:
    """
    記憶體優化的 Filmic tone mapping
    
    Args:
        lux: 輸入光度數據
        film: 胶片配置
        
    Returns:
        映射後的結果
    """
    # 確保非負
    lux = np.maximum(lux, 0)
    
    # 應用曝光和 gamma
    params = film.tone_params
    x = FILMIC_EXPOSURE_SCALE * np.power(lux, params.gamma)
    
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
    lux_r: np.ndarray,
    lux_g: np.ndarray,
    lux_b: np.ndarray,
    film: FilmProfile,
    bloom_params: Tuple[float, int, float, float],
    grain_data: Optional[Tuple] = None,
    tone_style: str = "filmic"
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    並行處理彩色胶片的 RGB 三通道
    
    Args:
        lux_r, lux_g, lux_b: RGB 光度數據
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
        # 並行計算光暈
        bloom_futures = [
            executor.submit(apply_bloom_optimized, lux, *params)
            for lux, params in zip([lux_r, lux_g, lux_b], bloom_params_list)
        ]
        
        bloom_r, bloom_g, bloom_b = [f.result() for f in bloom_futures]
        
        # 組合層
        def combine_layer(bloom, lux, layer, grain_r, grain_g, grain_b, grain_total):
            result = bloom * layer.diffuse_light + np.power(lux, layer.response_curve) * layer.direct_light
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
            executor.submit(combine_layer, bloom, lux, layer, grain_r, grain_g, grain_b,
                          film.panchromatic_layer.grain_intensity)
            for bloom, lux, layer in [
                (bloom_r, lux_r, film.red_layer),
                (bloom_g, lux_g, film.green_layer),
                (bloom_b, lux_b, film.blue_layer)
            ]
        ]
        
        lux_r_final, lux_g_final, lux_b_final = [f.result() for f in combine_futures]
        
        # 並行 tone mapping
        if tone_style == "filmic":
            tone_func = lambda lux: apply_filmic_optimized(lux, film)
        else:
            tone_func = lambda lux: apply_reinhard_optimized(lux, film.tone_params.gamma, color_mode=True)
        
        tone_futures = [
            executor.submit(tone_func, lux)
            for lux in [lux_r_final, lux_g_final, lux_b_final]
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
