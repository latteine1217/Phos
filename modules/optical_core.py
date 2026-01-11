"""
光度計算核心模組

包含膠片感光層的光譜響應計算與光度計量。

Functions:
    - spectral_response: 計算膠片感光層的光譜響應
    - average_response: 計算平均光譜響應
    - standardize: 標準化圖像尺寸

Physics Foundation:
    - Beer-Lambert Law: 光吸收定律
        T(λ) = exp(-α(λ)·L)
        其中 T 為透過率，α 為吸收係數，L 為介質厚度
    
    - Spectral Sensitivity: 膠片光譜敏感度曲線
        R(λ) = ∫ S(λ)·I(λ) dλ
        其中 S(λ) 為感光劑敏感度，I(λ) 為入射光譜
    
    - Linear Light Space: 線性光空間計算
        所有光度計算在線性空間進行（0-1 浮點數）
        最終輸出轉換至 sRGB gamma 空間（0-255 uint8）

References:
    - Hunt, R. W. G. (2004). The Reproduction of Colour, 6th ed.
    - James, T. H. (1977). Theory of the Photographic Process, 4th ed.
    - Todd & Zakia (1974). Photographic Sensitometry.

Version: 0.7.0-dev
Date: 2026-01-12
Status: PR #1 - Empty template (implementation in PR #2)

Note:
    此為 PR #1 空模板，實際函數將在 PR #2 從 Phos.py 搬移。
    搬移時保持原有邏輯 100% 不變，確保向後相容。
"""

import numpy as np
import cv2
from typing import Tuple, Optional

# 從 film_models 導入必要的類型和常數
from film_models import FilmProfile, STANDARD_IMAGE_SIZE


# ==================== 圖像預處理 ====================

def standardize(image: np.ndarray) -> np.ndarray:
    """
    標準化圖像尺寸
    
    將圖像的短邊調整為標準尺寸（3000px），保持寬高比
    
    Args:
        image: 輸入圖像 (BGR 格式)
        
    Returns:
        調整後的圖像
    """
    height, width = image.shape[:2]
    
    # 確定縮放比例
    if height < width:
        # 竖圖 - 高度為短邊
        scale_factor = STANDARD_IMAGE_SIZE / height
        new_height = STANDARD_IMAGE_SIZE
        new_width = int(width * scale_factor)
    else:
        # 橫圖 - 寬度為短邊
        scale_factor = STANDARD_IMAGE_SIZE / width
        new_width = STANDARD_IMAGE_SIZE
        new_height = int(height * scale_factor)
    
    # 確保新尺寸為偶數（避免某些處理問題）
    new_width = new_width + 1 if new_width % 2 != 0 else new_width
    new_height = new_height + 1 if new_height % 2 != 0 else new_height
    
    # 選擇適當的插值方法
    interpolation = cv2.INTER_AREA if scale_factor < 1 else cv2.INTER_LANCZOS4
    resized_image = cv2.resize(image, (new_width, new_height), interpolation=interpolation)
    
    return resized_image


# ==================== 光度計算 ====================

def spectral_response(image: np.ndarray, film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], np.ndarray]:
    """
    計算胶片感光層的光譜響應
    
    這個函數模擬了光在胶片不同感光層中的光譜吸收與響應過程。
    每個感光層對不同波長的光有不同的敏感度。
    
    Args:
        image: 輸入圖像 (BGR 格式，0-255)
        film: 胶片配置對象
        
    Returns:
        (response_r, response_g, response_b, response_total): 各通道的光譜響應 (0-1 範圍)
            - 彩色胶片: response_r/g/b 為各層響應，response_total 為全色層
            - 黑白胶片: 僅 response_total 有值，其餘為 None
    """
    # 分離 RGB 通道
    b, g, r = cv2.split(image)
    
    # 轉換為浮點數 (0-1 範圍)
    r_float = r.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    b_float = b.astype(np.float32) / 255.0
    
    # 獲取光譜響應係數
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    # 模擬不同乳劑層的光譜響應（光譜敏感度的線性組合）
    if film.color_type == "color":
        response_r = r_r * r_float + r_g * g_float + r_b * b_float
        response_g = g_r * r_float + g_g * g_float + g_b * b_float
        response_b = b_r * r_float + b_g * g_float + b_b * b_float
        response_total = t_r * r_float + t_g * g_float + t_b * b_float
    else:
        response_total = t_r * r_float + t_g * g_float + t_b * b_float
        response_r = None
        response_g = None
        response_b = None

    return response_r, response_g, response_b, response_total


def average_response(response_total: np.ndarray) -> float:
    """
    計算平均光譜響應
    
    Args:
        response_total: 全色通道的光譜響應數據
        
    Returns:
        平均響應值
    """
    avg_response = np.mean(response_total)
    return np.clip(avg_response, 0, 1)


# ==================== 版本信息 ====================

__all__ = [
    'standardize',
    'spectral_response',
    'average_response'
]
