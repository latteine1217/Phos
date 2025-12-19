"""
Phos 0.2.0 - Film Simulation Based on Computational Optics

"No LUTs, we calculate LUX."

你说的对，但是 Phos. 是基于「计算光学」概念的胶片模拟。
通过计算光在底片上的行为，复现自然、柔美、立体的胶片质感。

Version: 0.2.0 (Development - Batch Processing)
New Features: 
- 批量處理模式（支援多張照片同時處理）
- 進度條顯示
- ZIP 批量下載

Release Notes: See V0.2.0_ROADMAP.md for details
"""

import streamlit as st

# 设置页面配置 
st.set_page_config(
    page_title="Phos. 胶片模拟 v0.2.0",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="expanded"
)

import cv2
import numpy as np
import time
from PIL import Image
import io
from typing import Optional, Tuple, List
from functools import lru_cache

# ==================== 簡潔現代風格 CSS ====================
st.markdown("""
<style>
    /* 全局字體與基礎樣式 */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* 主背景 - 深色漸層 */
    .stApp {
        background: linear-gradient(135deg, #0F1419 0%, #1A1F2E 100%);
        background-attachment: fixed;
    }
    
    /* ===== 側邊欄樣式 ===== */
    [data-testid="stSidebar"] {
        background: rgba(26, 31, 46, 0.85) !important;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-right: 1px solid rgba(255, 107, 107, 0.15);
    }
    
    [data-testid="stSidebar"] h1 {
        color: #FF6B6B !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.25rem !important;
    }
    
    [data-testid="stSidebar"] h2 {
        color: #B8B8B8 !important;
        font-size: 0.9rem !important;
        font-weight: 400 !important;
        margin-bottom: 2rem !important;
    }
    
    [data-testid="stSidebar"] h3 {
        color: #E8E8E8 !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    
    [data-testid="stSidebar"] .stMarkdown {
        color: #B8B8B8 !important;
    }
    
    /* ===== 按鈕樣式 ===== */
    .stButton > button {
        width: 100%;
        background: rgba(255, 107, 107, 0.1) !important;
        color: #FF6B6B !important;
        border: 1px solid rgba(255, 107, 107, 0.3) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    
    .stButton > button:hover {
        background: rgba(255, 107, 107, 0.2) !important;
        border-color: rgba(255, 107, 107, 0.5) !important;
        transform: translateY(-1px);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #FF6B6B, #FF8E8E) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.25) !important;
    }
    
    .stButton > button[kind="primary"]:hover {
        box-shadow: 0 6px 16px rgba(255, 107, 107, 0.35) !important;
    }
    
    /* ===== 下載按鈕 ===== */
    .stDownloadButton > button {
        width: 100%;
        background: rgba(76, 175, 80, 0.1) !important;
        color: #66BB6A !important;
        border: 1px solid rgba(76, 175, 80, 0.3) !important;
        border-radius: 8px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
    }
    
    .stDownloadButton > button:hover {
        background: rgba(76, 175, 80, 0.2) !important;
        border-color: rgba(76, 175, 80, 0.5) !important;
    }
    
    /* ===== 選擇框樣式 ===== */
    .stSelectbox label, .stRadio label {
        color: #E8E8E8 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    
    .stSelectbox > div > div {
        background: rgba(26, 31, 46, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        color: #E8E8E8 !important;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: rgba(255, 107, 107, 0.5) !important;
        box-shadow: 0 0 0 1px rgba(255, 107, 107, 0.2) !important;
    }
    
    /* ===== 單選按鈕 ===== */
    .stRadio > div {
        background: transparent !important;
        gap: 0.5rem;
    }
    
    .stRadio > div > label > div {
        background: rgba(26, 31, 46, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 8px !important;
        padding: 0.75rem 1rem !important;
    }
    
    .stRadio > div > label > div:hover {
        border-color: rgba(255, 107, 107, 0.3) !important;
    }
    
    /* ===== 文件上傳器 ===== */
    [data-testid="stFileUploader"] {
        background: rgba(26, 31, 46, 0.4) !important;
        border: 2px dashed rgba(255, 107, 107, 0.3) !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }
    
    [data-testid="stFileUploader"]:hover {
        border-color: rgba(255, 107, 107, 0.5) !important;
        background: rgba(26, 31, 46, 0.6) !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: #E8E8E8 !important;
        font-weight: 500 !important;
    }
    
    /* ===== 進度條 ===== */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #FF6B6B, #FFB4B4) !important;
    }
    
    .stProgress > div > div {
        background: rgba(26, 31, 46, 0.6) !important;
        border-radius: 8px !important;
    }
    
    /* ===== 警告框 ===== */
    .stAlert {
        background: rgba(26, 31, 46, 0.8) !important;
        border-radius: 8px !important;
        border-left: 3px solid !important;
        padding: 0.75rem 1rem !important;
    }
    
    div[data-baseweb="notification"] {
        background: rgba(26, 31, 46, 0.8) !important;
        border-radius: 8px !important;
    }
    
    /* ===== 圖片容器 ===== */
    [data-testid="stImage"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3) !important;
    }
    
    /* ===== 分隔線 ===== */
    hr {
        border: none !important;
        height: 1px !important;
        background: rgba(255, 107, 107, 0.2) !important;
        margin: 1.5rem 0 !important;
    }
    
    /* ===== 標題樣式 ===== */
    h1 {
        color: #FF6B6B !important;
        font-weight: 700 !important;
    }
    
    h2, h3 {
        color: #E8E8E8 !important;
        font-weight: 600 !important;
    }
    
    p, li {
        color: #B8B8B8 !important;
        line-height: 1.6 !important;
    }
    
    /* ===== 滾動條 ===== */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(26, 31, 46, 0.3);
    }
    
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 107, 107, 0.3);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 107, 107, 0.5);
    }
    
    /* ===== 隱藏元素 ===== */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ===== 容器間距 ===== */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    [data-testid="column"] {
        padding: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# 導入批量處理模塊
from phos_batch import (
    BatchProcessor,
    BatchResult,
    create_zip_archive,
    generate_zip_filename,
    validate_batch_size,
    estimate_processing_time
)

# 導入胶片模型
from film_models import (
    get_film_profile, 
    FilmProfile, 
    EmulsionLayer,
    STANDARD_IMAGE_SIZE,
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


# ==================== 快取裝飾器 ====================

@st.cache_resource
def get_cached_film_profile(film_type: str) -> FilmProfile:
    """
    快取胶片配置，避免重複創建
    
    Args:
        film_type: 胶片類型
        
    Returns:
        FilmProfile: 快取的胶片配置
    """
    return get_film_profile(film_type)


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

def luminance(image: np.ndarray, film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], np.ndarray]:
    """
    計算亮度圖像，模擬胶片感光層的光譜響應
    
    這個函數模擬了光在胶片不同感光層中的吸收過程。
    每個感光層對不同波長的光有不同的敏感度。
    
    Args:
        image: 輸入圖像 (BGR 格式，0-255)
        film: 胶片配置對象
        
    Returns:
        (lux_r, lux_g, lux_b, lux_total): 各通道的光度響應 (0-1 範圍)
            - 彩色胶片: lux_r/g/b 為各層響應，lux_total 為全色層
            - 黑白胶片: 僅 lux_total 有值，其餘為 None
    """
    # 分離 RGB 通道
    b, g, r = cv2.split(image)
    
    # 轉換為浮點數 (0-1 範圍)
    r_float = r.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    b_float = b.astype(np.float32) / 255.0
    
    # 獲取光譜響應係數
    r_r, r_g, r_b, g_r, g_g, g_b, b_r, b_g, b_b, t_r, t_g, t_b = film.get_spectral_response()
    
    # 模擬不同乳劑層的吸收特性（光譜敏感度的線性組合）
    if film.color_type == "color":
        lux_r = r_r * r_float + r_g * g_float + r_b * b_float
        lux_g = g_r * r_float + g_g * g_float + g_b * b_float
        lux_b = b_r * r_float + b_g * g_float + b_b * b_float
        lux_total = t_r * r_float + t_g * g_float + t_b * b_float
    else:
        lux_total = t_r * r_float + t_g * g_float + t_b * b_float
        lux_r = None
        lux_g = None
        lux_b = None

    return lux_r, lux_g, lux_b, lux_total


def average_luminance(lux_total: np.ndarray) -> float:
    """
    計算圖像的平均亮度
    
    Args:
        lux_total: 全色通道的光度數據
        
    Returns:
        平均亮度值 (0-1 範圍)
    """
    avg_lux = np.mean(lux_total)
    return np.clip(avg_lux, 0, 1)


# ==================== 胶片顆粒效果 ====================

def generate_grain_for_channel(lux_channel: np.ndarray, sens: float) -> np.ndarray:
    """
    為單個通道生成胶片顆粒噪聲
    
    胶片顆粒是由於銀鹽晶體的隨機分布產生的。
    這個函數使用加權隨機噪聲來模擬這種效果。
    
    Args:
        lux_channel: 光度通道數據 (0-1 範圍)
        sens: 敏感度參數
        
    Returns:
        加權噪聲 (-1 到 1 範圍)
    """
    # 創建正負噪聲（使用平方正態分佈產生更自然的顆粒）
    noise = np.random.normal(0, 1, lux_channel.shape).astype(np.float32)
    noise = noise ** 2
    noise = noise * np.random.choice([-1, 1], lux_channel.shape)
    
    # 創建權重圖（中等亮度區域權重最高，模擬胶片顆粒在中間調最明顯的特性）
    weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
    weights = np.clip(weights, GRAIN_WEIGHT_MIN, GRAIN_WEIGHT_MAX)
    
    # 應用權重和敏感度
    sens_grain = np.clip(sens, GRAIN_SENS_MIN, GRAIN_SENS_MAX)
    weighted_noise = noise * weights * sens_grain
    
    # 添加輕微模糊使顆粒更柔和
    weighted_noise = cv2.GaussianBlur(weighted_noise, GRAIN_BLUR_KERNEL, GRAIN_BLUR_SIGMA)
    
    return np.clip(weighted_noise, -1, 1)


def apply_grain(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
                lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
                film: FilmProfile, sens: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    生成胶片顆粒效果
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據（彩色胶片）
        lux_total: 全色通道的光度數據
        film: 胶片配置對象
        sens: 敏感度參數
        
    Returns:
        (weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total): 各通道的顆粒噪聲
    """
    if film.color_type == "color" and all([lux_r is not None, lux_g is not None, lux_b is not None]):
        # 彩色胶片：為每個通道生成獨立的顆粒
        weighted_noise_r = generate_grain_for_channel(lux_r, sens)
        weighted_noise_g = generate_grain_for_channel(lux_g, sens)
        weighted_noise_b = generate_grain_for_channel(lux_b, sens)
        weighted_noise_total = None
    else:
        # 黑白胶片：僅生成全色通道的顆粒
        weighted_noise_total = generate_grain_for_channel(lux_total, sens)
        weighted_noise_r = None
        weighted_noise_g = None
        weighted_noise_b = None
    
    return weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total


# ==================== Tone Mapping ====================

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
    
    # 應用 gamma 校正
    gamma_adj = REINHARD_GAMMA_ADJUSTMENT if color_mode else 1.0
    mapped = np.power(np.maximum(mapped, 0), gamma_adj / gamma)
    
    return np.clip(mapped, 0, 1)


def apply_reinhard(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
                   lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
                   film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Reinhard tone mapping 算法
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據
        lux_total: 全色通道的光度數據
        film: 胶片配置對象
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    gamma = film.tone_params.gamma
    
    if film.color_type == "color" and all([lux_r is not None, lux_g is not None, lux_b is not None]):
        result_r = apply_reinhard_to_channel(lux_r, gamma, color_mode=True)
        result_g = apply_reinhard_to_channel(lux_g, gamma, color_mode=True)
        result_b = apply_reinhard_to_channel(lux_b, gamma, color_mode=True)
        result_total = None
    else:
        result_total = apply_reinhard_to_channel(lux_total, gamma, color_mode=False)
        result_r = None
        result_g = None
        result_b = None

    return result_r, result_g, result_b, result_total


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
    
    # 應用曝光和 gamma
    params = film.tone_params
    x = FILMIC_EXPOSURE_SCALE * np.power(lux, params.gamma)
    
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


def apply_filmic(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
                 lux_b: Optional[np.ndarray], lux_total: np.ndarray, 
                 film: FilmProfile) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Filmic tone mapping 算法
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據
        lux_total: 全色通道的光度數據
        film: 胶片配置對象
        
    Returns:
        (result_r, result_g, result_b, result_total): 映射後的各通道數據
    """
    if film.color_type == "color" and all([lux_r is not None, lux_g is not None, lux_b is not None]):
        result_r = apply_filmic_to_channel(lux_r, film)
        result_g = apply_filmic_to_channel(lux_g, film)
        result_b = apply_filmic_to_channel(lux_b, film)
        result_total = None
    else:
        result_total = apply_filmic_to_channel(lux_total, film)
        result_r = None
        result_g = None
        result_b = None
    
    return result_r, result_g, result_b, result_total


# ==================== 光學擴散效果 ====================

def calculate_bloom_params(avg_lux: float, sens_factor: float) -> Tuple[float, int, float, float]:
    """
    根據平均亮度計算光暈參數
    
    Args:
        avg_lux: 平均亮度
        sens_factor: 胶片敏感係數
        
    Returns:
        (sens, rads, strg, base): 敏感度、擴散半徑、光暈強度、基礎擴散
    """
    # 根據平均亮度計算敏感度（暗圖更敏感）
    sens = float((1.0 - avg_lux) * SENSITIVITY_SCALE + SENSITIVITY_BASE)
    sens = float(np.clip(sens, SENSITIVITY_MIN, SENSITIVITY_MAX))
    
    # 計算光暈強度和擴散半徑
    strg = float(BLOOM_STRENGTH_FACTOR * (sens ** 2) * sens_factor)
    rads = int(BLOOM_RADIUS_FACTOR * (sens ** 2) * sens_factor)
    rads = int(np.clip(rads, BLOOM_RADIUS_MIN, BLOOM_RADIUS_MAX))
    
    # 基礎擴散強度
    base = float(BASE_DIFFUSION_FACTOR * sens_factor)
    
    return sens, rads, strg, base


def apply_bloom_to_channel(lux: np.ndarray, sens: float, rads: int, strg: float, base: float, 
                           blur_scale: int, blur_sigma_scale: float) -> np.ndarray:
    """
    對單個通道應用光暈效果
    
    光暈（Halation）是由於光在胶片中的散射和反射產生的。
    高光區域會產生柔和的光暈，這是胶片的特徵之一。
    
    Args:
        lux: 光度通道數據
        sens: 敏感度
        rads: 擴散半徑
        strg: 光暈強度
        base: 基礎擴散強度
        blur_scale: 模糊核大小倍數
        blur_sigma_scale: 模糊 sigma 倍數
        
    Returns:
        光暈效果
    """
    # 創建權重（高光區域權重更高）
    weights = (base + lux ** 2) * sens
    weights = np.clip(weights, 0, 1)
    
    # 計算模糊核大小（必須為奇數）
    ksize = rads * blur_scale
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    
    # 創建光暈層（使用高斯模糊模擬光的擴散）
    bloom_layer = cv2.GaussianBlur(lux * weights, (ksize, ksize), sens * blur_sigma_scale)
    
    # 應用光暈
    bloom_effect = bloom_layer * weights * strg
    bloom_effect = bloom_effect / (1.0 + bloom_effect)  # 避免過曝
    
    return bloom_effect


def combine_layers_for_channel(bloom: np.ndarray, lux: np.ndarray, layer: EmulsionLayer,
                               grain_r: Optional[np.ndarray], grain_g: Optional[np.ndarray], 
                               grain_b: Optional[np.ndarray], grain_total: float,
                               use_grain: bool) -> np.ndarray:
    """
    組合散射光、直射光和顆粒效果
    
    Args:
        bloom: 光暈效果
        lux: 原始光度數據
        layer: 感光層參數
        grain_r, grain_g, grain_b: RGB 顆粒噪聲
        grain_total: 全色顆粒強度
        use_grain: 是否使用顆粒
        
    Returns:
        組合後的光度數據
    """
    # 散射光 + 直射光（非線性響應）
    result = bloom * layer.diffuse_light + np.power(lux, layer.response_curve) * layer.direct_light
    
    # 添加顆粒
    if use_grain:
        # 彩色胶片的顆粒有色彩相關性
        if grain_r is not None and grain_g is not None and grain_b is not None:
            result += (grain_r * layer.grain_intensity + 
                      grain_g * grain_total + 
                      grain_b * grain_total)
        elif grain_r is not None:
            result += grain_r * layer.grain_intensity
    
    return result


def optical_processing(lux_r: Optional[np.ndarray], lux_g: Optional[np.ndarray], 
                      lux_b: Optional[np.ndarray], lux_total: np.ndarray,
                      film: FilmProfile, grain_style: str, tone_style: str) -> np.ndarray:
    """
    光學處理主函數
    
    這是整個胶片模擬的核心，包含：
    1. 計算自適應參數
    2. 應用光暈效果（Halation/Bloom）
    3. 應用顆粒效果
    4. 組合散射光和直射光
    5. Tone mapping
    6. 合成最終圖像
    
    Args:
        lux_r, lux_g, lux_b: RGB 通道的光度數據
        lux_total: 全色通道的光度數據
        film: 胶片配置對象
        grain_style: 顆粒風格
        tone_style: Tone mapping 風格
        
    Returns:
        處理後的圖像 (0-255 uint8)
    """
    # 1. 計算自適應參數
    avg_lux = average_luminance(lux_total)
    sens, rads, strg, base = calculate_bloom_params(avg_lux, film.sensitivity_factor)
    
    # 2. 應用顆粒（如果需要）
    use_grain = (grain_style != "不使用")
    if use_grain:
        grain_r, grain_g, grain_b, grain_total_noise = apply_grain(
            lux_r, lux_g, lux_b, lux_total, film, sens
        )
    else:
        grain_r = grain_g = grain_b = grain_total_noise = None
    
    # 3. 處理各通道
    if film.color_type == "color" and all([lux_r is not None, lux_g is not None, lux_b is not None]):
        # 彩色胶片：處理 RGB 三個通道
        # 不同顏色通道的光暈特性不同（紅色擴散最廣，藍色最窄）
        bloom_r = apply_bloom_to_channel(lux_r, sens, rads, strg, base, blur_scale=3, blur_sigma_scale=55)
        bloom_g = apply_bloom_to_channel(lux_g, sens, rads, strg, base, blur_scale=2, blur_sigma_scale=35)
        bloom_b = apply_bloom_to_channel(lux_b, sens, rads, strg, base, blur_scale=1, blur_sigma_scale=15)
        
        # 組合各層
        lux_r_final = combine_layers_for_channel(
            bloom_r, lux_r, film.red_layer, grain_r, grain_g, grain_b, 
            film.panchromatic_layer.grain_intensity, use_grain
        )
        lux_g_final = combine_layers_for_channel(
            bloom_g, lux_g, film.green_layer, grain_r, grain_g, grain_b,
            film.panchromatic_layer.grain_intensity, use_grain
        )
        lux_b_final = combine_layers_for_channel(
            bloom_b, lux_b, film.blue_layer, grain_r, grain_g, grain_b,
            film.panchromatic_layer.grain_intensity, use_grain
        )
        
        # 4. Tone mapping
        if tone_style == "filmic":
            result_r, result_g, result_b, _ = apply_filmic(lux_r_final, lux_g_final, lux_b_final, lux_total, film)
        else:
            result_r, result_g, result_b, _ = apply_reinhard(lux_r_final, lux_g_final, lux_b_final, lux_total, film)
        
        # 5. 合成最終圖像
        combined_r = (result_r * 255).astype(np.uint8)
        combined_g = (result_g * 255).astype(np.uint8)
        combined_b = (result_b * 255).astype(np.uint8)
        final_image = cv2.merge([combined_b, combined_g, combined_r])
        
    else:
        # 黑白胶片：僅處理全色通道
        bloom = apply_bloom_to_channel(lux_total, sens, rads, strg, base, blur_scale=3, blur_sigma_scale=55)
        
        # 組合層
        if use_grain and grain_total_noise is not None:
            lux_final = (bloom * film.panchromatic_layer.diffuse_light + 
                        np.power(lux_total, film.panchromatic_layer.response_curve) * film.panchromatic_layer.direct_light +
                        grain_total_noise * film.panchromatic_layer.grain_intensity)
        else:
            lux_final = (bloom * film.panchromatic_layer.diffuse_light + 
                        np.power(lux_total, film.panchromatic_layer.response_curve) * film.panchromatic_layer.direct_light)
        
        # Tone mapping
        if tone_style == "filmic":
            _, _, _, result_total = apply_filmic(None, None, None, lux_final, film)
        else:
            _, _, _, result_total = apply_reinhard(None, None, None, lux_final, film)
        
        # 合成最終圖像
        final_image = (result_total * 255).astype(np.uint8)
    
    return final_image


# ==================== 主處理流程 ====================

def adjust_grain_intensity(film: FilmProfile, grain_style: str) -> FilmProfile:
    """
    根據用戶選擇調整顆粒強度
    
    Args:
        film: 原始胶片配置
        grain_style: 顆粒風格選擇
        
    Returns:
        調整後的胶片配置
    """
    # 顆粒強度倍數
    multipliers = {
        "默認": 1.0,
        "柔和": 0.5,
        "較粗": 1.5,
        "不使用": 0.0
    }
    
    multiplier = multipliers.get(grain_style, 1.0)
    
    # 創建新的感光層（不修改原始配置）
    if film.color_type == "color" and film.red_layer and film.green_layer and film.blue_layer:
        from dataclasses import replace
        return replace(
            film,
            red_layer=replace(film.red_layer, grain_intensity=film.red_layer.grain_intensity * multiplier),
            green_layer=replace(film.green_layer, grain_intensity=film.green_layer.grain_intensity * multiplier),
            blue_layer=replace(film.blue_layer, grain_intensity=film.blue_layer.grain_intensity * multiplier),
            panchromatic_layer=replace(film.panchromatic_layer, grain_intensity=film.panchromatic_layer.grain_intensity * multiplier)
        )
    else:
        from dataclasses import replace
        return replace(
            film,
            panchromatic_layer=replace(film.panchromatic_layer, grain_intensity=film.panchromatic_layer.grain_intensity * multiplier)
        )


def process_image(uploaded_image, film_type: str, grain_style: str, tone_style: str) -> Tuple[np.ndarray, float, str]:
    """
    處理上傳的圖像
    
    這是主要的處理流程，協調所有步驟：
    1. 讀取圖像
    2. 獲取胶片配置
    3. 標準化尺寸
    4. 計算光度響應
    5. 應用光學效果
    
    Args:
        uploaded_image: 上傳的圖像文件
        film_type: 胶片類型
        grain_style: 顆粒風格
        tone_style: Tone mapping 風格
        
    Returns:
        (處理後的圖像, 處理時間, 輸出文件名)
        
    Raises:
        ValueError: 圖像讀取失敗或胶片類型無效
    """
    start_time = time.time()
    
    try:
        # 1. 讀取上傳的文件
        file_bytes = np.asarray(bytearray(uploaded_image.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("無法讀取圖像文件，請確保上傳的是有效的圖像格式")
        
        # 2. 獲取胶片配置（使用快取）
        film = get_cached_film_profile(film_type)
        
        # 3. 調整顆粒強度
        film = adjust_grain_intensity(film, grain_style)
        
        # 4. 標準化圖像尺寸
        image = standardize(image)
        
        # 5. 計算光度響應
        lux_r, lux_g, lux_b, lux_total = luminance(image, film)
        
        # 6. 應用光學處理
        final_image = optical_processing(lux_r, lux_g, lux_b, lux_total, film, grain_style, tone_style)
        
        # 7. 生成輸出文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_path = f"phos_{film_type.lower()}_{timestamp}.jpg"
        
        process_time = time.time() - start_time
        
        return final_image, process_time, output_path
        
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError(f"處理圖像時發生錯誤: {str(e)}")


# ==================== Streamlit 界面 ====================

# 初始化 session state
if 'processing_mode' not in st.session_state:
    st.session_state.processing_mode = "單張處理"
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []

# 創建側邊欄
with st.sidebar:
    # 應用標題
    st.markdown("# Phos.")
    st.markdown("## 計算光學胶片模拟")
    st.markdown("---")
    st.markdown("#### 🚀 v0.2.0 · Batch Processing")
    st.markdown("")
    
    # 處理模式選擇
    st.markdown("### 📷 處理模式")
    processing_mode = st.radio(
        "選擇處理模式",
        ["單張處理", "批量處理"],
        index=0,
        help="單張處理: 處理一張照片\n批量處理: 同時處理多張照片",
        label_visibility="collapsed"
    )
    st.session_state.processing_mode = processing_mode
    
    st.markdown("---")
    st.markdown("### 🎞️ 胶片設定")
    
    # 胶片類型選擇
    film_type = st.selectbox(
        "請選擇胶片:",
        ["NC200", "Portra400", "Ektar100", "AS100", "HP5Plus400", "Cinestill800T", "FS200"],
        index=0,
        help='''選擇要模擬的胶片類型:

        === 彩色胶片 ===
        NC200: 靈感來自富士 C200，經典富士色調
        Portra400: 🆕 人像王者，細膩膚色，低顆粒（靈感來自 Kodak Portra 400）
        Ektar100: 🆕 風景利器，高飽和，極細顆粒（靈感來自 Kodak Ektar 100）
        Cinestill800T: 🆕 電影感，強光暈，溫暖色調（靈感來自 CineStill 800T）

        === 黑白胶片 ===
        AS100: 靈感來自富士 ACROS，灰階細膩，顆粒柔和
        HP5Plus400: 🆕 經典黑白，明顯顆粒，高對比（靈感來自 Ilford HP5 Plus 400）
        FS200: 高對比度黑白正片（原理驗證模型）
        '''
    )

    grain_style = st.selectbox(
        "胶片顆粒度：",
        ["默認", "柔和", "較粗", "不使用"],
        index=0,
        help="選擇胶片的顆粒度",
    )
    
    tone_style = st.selectbox(
        "曲線映射：",
        ["filmic", "reinhard"],
        index=0,
        help='''選擇Tone mapping方式:
        
        目前版本下Reinhard模型似乎表現出更好的動態範圍，
        filmic模型尚不夠完善,但對肩部趾部有更符合目標的刻畫'''
    )

    st.success(f"已選擇胶片: {film_type}")
    
    st.divider()
    
    # 根據處理模式顯示不同的文件上傳器
    if processing_mode == "單張處理":
        uploaded_image = st.file_uploader(
            "選擇一張照片來開始沖洗",
            type=["jpg", "jpeg", "png"],
            help="上傳一張照片沖洗試試看吧"
        )
        uploaded_images = None
    else:  # 批量處理
        uploaded_images = st.file_uploader(
            "選擇多張照片進行批量處理",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            help="一次最多可處理 50 張照片"
        )
        uploaded_image = None
        
        if uploaded_images:
            num_files = len(uploaded_images)
            is_valid, error_msg = validate_batch_size(num_files, max_size=50)
            
            if not is_valid:
                st.error(error_msg)
                uploaded_images = None
            else:
                st.info(f"✅ 已上傳 {num_files} 張照片")
                est_time = estimate_processing_time(num_files, avg_time_per_image=2.0)
                st.info(f"⏱️ 預計處理時間: {est_time}")

# ==================== 主區域 ====================

# 單張處理模式
if processing_mode == "單張處理" and uploaded_image is not None:
    try:
        # 處理圖像
        film_image, process_time, output_path = process_image(
            uploaded_image, film_type, grain_style, tone_style
        )
        
        # 顯示結果
        st.image(film_image, channels="BGR", use_container_width=True)
        st.success(f"底片顯影好了，用時 {process_time:.2f}秒") 
        
        # 添加下載按鈕
        # 將 BGR 轉換為 RGB 供 PIL 使用
        film_rgb = cv2.cvtColor(film_image, cv2.COLOR_BGR2RGB)
        film_pil = Image.fromarray(film_rgb)
        
        buf = io.BytesIO()
        film_pil.save(buf, format="JPEG", quality=95)
        byte_im = buf.getvalue()
        
        st.download_button(
            label="📥 下載高清圖像",
            data=byte_im,
            file_name=output_path,
            mime="image/jpeg"
        )
        
    except ValueError as e:
        st.error(f"❌ 錯誤: {str(e)}")
    except Exception as e:
        st.error(f"❌ 未預期的錯誤: {str(e)}")
        st.error("請嘗試重新上傳圖像或選擇其他胶片類型")

# 批量處理模式
elif processing_mode == "批量處理" and uploaded_images is not None and len(uploaded_images) > 0:
    st.header(f"📦 批量處理 - {len(uploaded_images)} 張照片")
    
    # 開始處理按鈕
    if st.button("🚀 開始批量處理", type="primary", use_container_width=True):
        try:
            # 初始化批量處理器
            batch_processor = BatchProcessor(max_workers=4)
            
            # 獲取胶片配置
            film = get_cached_film_profile(film_type)
            
            # 創建進度條和狀態文本
            progress_bar = st.progress(0)
            status_text = st.empty()
            time_text = st.empty()
            
            # 進度回調函數
            def update_progress(current, total, filename):
                progress = current / total
                progress_bar.progress(progress)
                status_text.text(f"處理中: {filename} ({current}/{total})")
            
            # 定義處理函數（將 process_image 邏輯封裝）
            def batch_process_func(image_array, film_profile, settings):
                """批量處理單張圖像的包裝函數"""
                # 標準化
                image_std = standardize(image_array)
                
                # 計算光度
                lux_r, lux_g, lux_b, lux_total = luminance(image_std, film_profile)
                
                # 光學處理
                result = optical_processing(
                    lux_r, lux_g, lux_b, lux_total,
                    film_profile,
                    settings['grain_style'],
                    settings['tone_style']
                )
                
                return result
            
            # 準備設定
            settings = {
                'grain_style': grain_style,
                'tone_style': tone_style
            }
            
            # 開始處理
            start_time = time.time()
            
            # 使用順序處理（ThreadPoolExecutor 在 Streamlit 中更穩定）
            results = batch_processor.process_batch_sequential(
                uploaded_images,
                film,
                batch_process_func,
                settings,
                progress_callback=update_progress
            )
            
            total_time = time.time() - start_time
            
            # 顯示結果統計
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count
            
            progress_bar.empty()
            status_text.empty()
            
            if success_count > 0:
                st.success(f"✅ 處理完成！成功: {success_count}/{len(results)} 張，總用時: {total_time:.2f} 秒")
                
                # 保存結果到 session state
                st.session_state.batch_results = results
                
                # 顯示處理結果預覽（前6張）
                st.subheader("📸 處理結果預覽")
                cols = st.columns(3)
                preview_count = min(6, success_count)
                preview_idx = 0
                
                for idx, result in enumerate(results):
                    if result.success and preview_idx < preview_count:
                        col = cols[preview_idx % 3]
                        with col:
                            # 轉換 BGR 到 RGB 顯示
                            result_rgb = cv2.cvtColor(result.image_data, cv2.COLOR_BGR2RGB)
                            st.image(result_rgb, caption=result.filename, use_container_width=True)
                            st.caption(f"⏱️ {result.processing_time:.2f}s")
                        preview_idx += 1
                
                if success_count > preview_count:
                    st.info(f"還有 {success_count - preview_count} 張照片未顯示，請下載 ZIP 查看全部")
                
                # 創建 ZIP 下載
                st.subheader("📦 下載處理結果")
                
                with st.spinner("正在生成 ZIP 檔案..."):
                    zip_data = create_zip_archive(
                        results,
                        film_name=film_type,
                        output_format="jpg",
                        quality=95
                    )
                    zip_filename = generate_zip_filename(film_type)
                
                st.download_button(
                    label=f"📥 下載全部照片 (ZIP)",
                    data=zip_data,
                    file_name=zip_filename,
                    mime="application/zip",
                    use_container_width=True
                )
                
                # 顯示失敗列表（如果有）
                if fail_count > 0:
                    with st.expander(f"⚠️ {fail_count} 張照片處理失敗", expanded=False):
                        for result in results:
                            if not result.success:
                                st.error(f"❌ {result.filename}: {result.error_message}")
            else:
                st.error("❌ 所有照片處理失敗，請檢查圖像格式或胶片設定")
                
        except Exception as e:
            st.error(f"❌ 批量處理時發生錯誤: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

# 未上傳文件時的歡迎界面
else:
    # 歡迎標題
    st.markdown("""
    <div style='text-align: center; padding: 2rem 0 3rem 0;'>
        <h1 style='font-size: 3.5rem; font-weight: 700; margin: 0 0 0.5rem 0;
                   color: #FF6B6B;'>
            Phos.
        </h1>
        <p style='font-size: 1.2rem; color: #B8B8B8; margin: 0 0 0.25rem 0;'>
            計算光學胶片模拟
        </p>
        <p style='font-size: 1rem; color: #888; font-style: italic; margin: 0;'>
            "No LUTs, we calculate LUX."
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 功能卡片
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div style='padding: 1.5rem; background: rgba(26, 31, 46, 0.5); 
                    border-radius: 12px; border: 1px solid rgba(255, 107, 107, 0.2);
                    min-height: 200px;'>
            <h3 style='color: #FF6B6B; margin: 0 0 1rem 0; font-size: 1.1rem;'>🎞️ 單張處理</h3>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li>精準模擬 7 款經典胶片</li>
                <li>計算光學原理，非 LUT</li>
                <li>細膩顆粒與光暈效果</li>
                <li>高質量輸出 (JPEG 95)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='padding: 1.5rem; background: rgba(26, 31, 46, 0.5); 
                    border-radius: 12px; border: 1px solid rgba(255, 107, 107, 0.2);
                    min-height: 200px;'>
            <h3 style='color: #FF6B6B; margin: 0 0 1rem 0; font-size: 1.1rem;'>📦 批量處理</h3>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li>一次處理最多 50 張照片</li>
                <li>實時進度顯示</li>
                <li>智能時間預估</li>
                <li>一鍵 ZIP 批量下載</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 胶片列表
    st.markdown("### 🎬 可用胶片")
    
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        st.markdown("""
        <div style='background: rgba(26, 31, 46, 0.3); padding: 1rem; border-radius: 8px;'>
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>彩色胶片 Color Films</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>NC200</strong> - 富士清新色調</li>
                <li><strong>Portra400</strong> - 人像低顆粒</li>
                <li><strong>Ektar100</strong> - 風景高飽和</li>
                <li><strong>Cinestill800T</strong> - 電影強光暈</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: rgba(26, 31, 46, 0.3); padding: 1rem; border-radius: 8px;'>
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>黑白胶片 B&W Films</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>AS100</strong> - 細膩灰階</li>
                <li><strong>HP5Plus400</strong> - 街拍經典</li>
                <li><strong>FS200</strong> - 高對比概念片</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 使用提示
    st.info("👈 請在左側邊欄選擇處理模式並上傳照片開始使用")
