"""
Tone Mapping 模組

包含 HDR 到 LDR 的色調映射演算法。

Algorithms:
    - Reinhard: 全局 tone mapping
        L' = L · (1 + L/L_white²) / (1 + L)
        其中 L_white 為白點（最亮值映射位置）
    
    - Filmic: 分段曲線模擬膠片特性
        使用 Shoulder（肩部）、Linear（線性段）、Toe（趾部）三段式曲線
        公式: f(x) = [(x(Ax+CB)+DE] / [x(Ax+B)+DF] - E/F

Physics Foundation:
    - Reinhard: 基於視覺適應模型（photoreceptor adaptation）
    - Filmic: 基於膠片 H&D 曲線（Hurter-Driffield characteristic curve）

References:
    - Reinhard, E., et al. (2002). "Photographic tone reproduction for digital images."
      ACM Transactions on Graphics, 21(3), 267-276.
    - Hable, J. (2010). "Uncharted 2: HDR Lighting."
      Game Developers Conference presentation.
    - Duiker, H. (2003). "High Dynamic Range Image Encodings."
      AMPAS/ASC ACES white paper.

Version: 0.7.0-dev
Date: 2026-01-12
Status: PR #1 - Empty template (implementation in PR #3)

Note:
    此為 PR #1 空模板，實際函數將在 PR #3 從 Phos.py 搬移。
"""

import numpy as np
from typing import Tuple, Optional

# 從 film_models 導入必要的類型和常數
from film_models import FilmProfile, REINHARD_GAMMA_ADJUSTMENT, FILMIC_EXPOSURE_SCALE


# ==================== Reinhard Tone Mapping ====================

def apply_reinhard_to_channel(lux: np.ndarray, gamma: float, color_mode: bool = False) -> np.ndarray:
    """
    對單個通道應用 Reinhard tone mapping
    
    Reinhard tone mapping 是一種全局 tone mapping 算法，
    使用簡單的公式將 HDR 映射到 LDR。
    
    Args:
        lux: 輸入光度數據
        gamma: Gamma 值
        color_mode: 是否為彩色模式（影響 gamma 調整）
        
    Returns:
        映射後的結果 (0-1 範圍)
    """
    # Reinhard tone mapping: L' = L * L / (1 + L)
    mapped = lux * (lux / (1.0 + lux))
    
    # 顯示亮度微調（膜片特性差異化）
    # 在 linear_to_srgb() 編碼前，以 gamma_adj/gamma 的冪次調整亮度：
    #   - REINHARD_GAMMA_ADJUSTMENT = 1.05（輕微提升對比度，更接近膠片特性）
    #   - gamma 為各膠片的顯示 gamma（1.5–3.0），值越大越暗
    #   - 與下游 linear_to_srgb() 組合後，淨效果約為 power(output, gamma_adj)
    gamma_adj = REINHARD_GAMMA_ADJUSTMENT if color_mode else 1.0
    mapped = np.power(np.maximum(mapped, 0), gamma_adj / gamma)
    
    return np.clip(mapped, 0, 1)


def apply_reinhard(response_r: Optional[np.ndarray], response_g: Optional[np.ndarray], 
                   response_b: Optional[np.ndarray], response_total: np.ndarray, 
                   film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Reinhard tone mapping 算法
    
    Args:
        response_r, response_g, response_b: RGB 通道的光度數據
        response_total: 全色通道的光度數據
        film: 胶片配置對象
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    gamma = film.tone_params.gamma
    
    if film.color_type == "color" and all([response_r is not None, response_g is not None,  response_b is not None]):
        result_r = apply_reinhard_to_channel(response_r, gamma, color_mode=True)
        result_g = apply_reinhard_to_channel(response_g, gamma, color_mode=True)
        result_b = apply_reinhard_to_channel(response_b, gamma, color_mode=True)
        result_total = None
    else:
        result_total = apply_reinhard_to_channel(response_total, gamma, color_mode=False)
        result_r = None
        result_g = None
        result_b = None

    return result_r, result_g, result_b, result_total


# ==================== Filmic Tone Mapping ====================

def apply_filmic_to_channel(lux: np.ndarray, film: FilmProfile) -> np.ndarray:
    """
    對單個通道應用 Filmic tone mapping
    
    Filmic tone mapping 使用分段曲線模擬真實胶片的特性曲線。
    相比 Reinhard，它對高光和陰影有更好的控制。
    
    Args:
        lux: 輸入光度數據
        film: 胶片配置對象
        
    Returns:
        映射後的結果
        
    Note:
        特性曲線三個關鍵部分：
        - Shoulder (肩部): 控制高光過渡，避免高光溢出
        - Linear (線性段): 控制中間調響應
        - Toe (趾部): 控制陰影過渡，保留陰影細節
    """
    # 確保非負值
    lux = np.maximum(lux, 0)

    # 曝光縮放（Linear RGB 直接縮放，無需 gamma 預處理）
    # Hable Filmic 曲線設計用於線性光強度輸入：
    #   FILMIC_EXPOSURE_SCALE 將 [0,1] 的線性值映射到曲線的有效作用範圍
    # 舊版 sRGB 輸入需要 power(lux, gamma) 作為線性化預處理；
    # 在 Linear RGB 管線中，linear_to_srgb() 統一於管線末端處理 gamma 編碼。
    params = film.tone_params
    x = FILMIC_EXPOSURE_SCALE * lux
    
    # Filmic curve: 分段曲線公式
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


def apply_filmic(response_r: Optional[np.ndarray], response_g: Optional[np.ndarray], 
                 response_b: Optional[np.ndarray], response_total: np.ndarray, 
                 film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Filmic tone mapping 算法
    
    Args:
        response_r, response_g, response_b: RGB 通道的光度數據
        response_total: 全色通道的光度數據
        film: 胶片配置對象
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    if film.color_type == "color" and all([response_r is not None, response_g is not None,  response_b is not None]):
        result_r = apply_filmic_to_channel(response_r, film)
        result_g = apply_filmic_to_channel(response_g, film)
        result_b = apply_filmic_to_channel(response_b, film)
        result_total = None
    else:
        result_total = apply_filmic_to_channel(response_total, film)
        result_r = None
        result_g = None
        result_b = None
    
    return result_r, result_g, result_b, result_total


# ==================== 版本信息 ====================

__all__ = [
    'apply_reinhard_to_channel',
    'apply_reinhard',
    'apply_filmic_to_channel',
    'apply_filmic'
]
