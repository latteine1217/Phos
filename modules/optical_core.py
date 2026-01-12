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


# ==================== 色彩空間轉換 ====================

def srgb_to_linear(rgb: np.ndarray) -> np.ndarray:
    """
    sRGB gamma 解碼（轉換至線性光空間）
    
    將 sRGB 色彩空間的值轉換為線性 RGB（物理光強度）。
    這是物理正確色彩處理的基礎，所有光學計算必須在線性空間進行。
    
    Physics Foundation:
        - sRGB 使用 gamma ≈ 2.2 的非線性編碼，用於顯示器顯示
        - 線性 RGB 代表真實物理光強度，用於光學計算
        - Beer-Lambert Law, Bloom, Halation 等效果必須在線性空間正確
    
    Formula (IEC 61966-2-1:1999):
        if C_srgb <= 0.04045:
            C_linear = C_srgb / 12.92           # 線性區域（暗部）
        else:
            C_linear = ((C_srgb + 0.055) / 1.055)^2.4  # Gamma 區域（中高光）
    
    Args:
        rgb: sRGB 值，範圍 [0, 1]（float32 或 float64）
        
    Returns:
        Linear RGB 值，範圍 [0, 1]
        
    Example:
        >>> srgb_val = np.array([0.5])  # sRGB 中間調
        >>> linear_val = srgb_to_linear(srgb_val)
        >>> linear_val
        array([0.21404])  # 線性空間約為 21% 強度
    
    Reference:
        - IEC 61966-2-1:1999 - Multimedia systems and equipment - 
          Colour measurement and management - Part 2-1: Default RGB colour space - sRGB
        - Poynton, C. (2003). "Digital Video and HD: Algorithms and Interfaces"
    
    Note:
        此函數是 v0.8.2 的核心修正，解決了之前在 gamma 空間進行線性矩陣運算的錯誤。
    """
    return np.where(
        rgb <= 0.04045,
        rgb / 12.92,  # 線性區域
        np.power((rgb + 0.055) / 1.055, 2.4)  # Gamma 解碼
    )


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
    
    Color Space Processing (v0.8.2 重要修正):
        1. 輸入圖像假設為 sRGB 色彩空間（相機/手機標準輸出）
        2. 先進行 gamma 解碼：sRGB → Linear RGB
        3. 在線性光空間進行光譜響應矩陣運算（物理正確）
        4. film.spectral_response_matrix 假設 Linear RGB 輸入
    
    Physics Foundation:
        - Beer-Lambert Law: 光吸收必須在線性空間計算
        - 光譜敏感度的線性組合只在線性光空間物理正確
        - Gamma 空間的矩陣運算會導致色彩偏移和對比度錯誤
    
    Args:
        image: 輸入圖像 (BGR 格式，0-255，假設 sRGB 色彩空間)
        film: 胶片配置對象
        
    Returns:
        (response_r, response_g, response_b, response_total): 各通道的光譜響應 (0-1 範圍)
            - 彩色胶片: response_r/g/b 為各層響應，response_total 為全色層
            - 黑白胶片: 僅 response_total 有值，其餘為 None
    
    Note:
        v0.8.2 核心修正：新增 sRGB → Linear RGB gamma 解碼
        這確保所有光學計算在物理正確的線性光空間進行。
    """
    # 分離 RGB 通道
    b, g, r = cv2.split(image)
    
    # 轉換為浮點數 (0-1 範圍)
    r_float = r.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    b_float = b.astype(np.float32) / 255.0
    
    # v0.8.2 新增：sRGB gamma 解碼 → Linear RGB
    # 這是物理正確色彩處理的關鍵步驟
    # Reference: IEC 61966-2-1:1999
    r_linear = srgb_to_linear(r_float)
    g_linear = srgb_to_linear(g_float)
    b_linear = srgb_to_linear(b_float)
    
    # 獲取光譜響應係數（假設 Linear RGB 輸入）
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    # 模擬不同乳劑層的光譜響應（光譜敏感度的線性組合）
    # 在線性光空間進行矩陣運算（物理正確）
    if film.color_type == "color":
        response_r = r_r * r_linear + r_g * g_linear + r_b * b_linear
        response_g = g_r * r_linear + g_g * g_linear + g_b * b_linear
        response_b = b_r * r_linear + b_g * g_linear + b_b * b_linear
        response_total = t_r * r_linear + t_g * g_linear + t_b * b_linear
    else:
        response_total = t_r * r_linear + t_g * g_linear + t_b * b_linear
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
    'srgb_to_linear',     # v0.8.2: 新增 sRGB gamma 解碼
    'standardize',
    'spectral_response',
    'average_response'
]
