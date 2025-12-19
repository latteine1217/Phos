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
import film_models
from film_models import (
    get_film_profile, 
    FilmProfile, 
    EmulsionLayer,
    PhysicsMode,
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


def generate_poisson_grain(lux_channel: np.ndarray, grain_params: film_models.GrainParams) -> np.ndarray:
    """
    生成物理導向的 Poisson 顆粒噪聲
    
    物理原理：
    1. 光子計數統計：曝光量 → 平均光子數（泊松過程）
    2. 銀鹽顆粒：每個光子有機率激發銀鹽晶體
    3. 量化噪聲：實際計數 ~ Poisson(λ)，標準差 = √λ
    4. 信噪比：SNR = λ / √λ = √λ（與曝光量平方根成正比）
    
    與藝術模式差異：
    - 藝術模式：權重最大在中間調（0.5 附近）
    - 物理模式：噪聲與 √曝光量 成反比（暗部噪聲更明顯）
    
    Args:
        lux_channel: 光度通道數據（0-1 範圍，代表相對曝光量）
        grain_params: Poisson 顆粒參數
        
    Returns:
        Poisson 顆粒噪聲（標準化到 [-1, 1] 範圍）
    """
    # 1. 將相對曝光量轉換為平均光子計數
    # exposure_level 作為基準（假設 lux=1.0 時的光子數）
    photon_count_mean = lux_channel * grain_params.exposure_level
    
    # 避免零或負值（添加小偏移）
    photon_count_mean = np.clip(photon_count_mean, 1.0, None)
    
    # 2. 根據 Poisson 分布生成實際光子計數
    # 使用正態近似（當 λ > 20 時，Poisson(λ) ≈ Normal(λ, √λ)）
    # 這樣計算效率更高，且對大 λ 值足夠準確
    photon_count_actual = np.random.normal(
        loc=photon_count_mean, 
        scale=np.sqrt(photon_count_mean)
    ).astype(np.float32)
    
    # 確保非負
    photon_count_actual = np.maximum(photon_count_actual, 0)
    
    # 3. 計算相對噪聲：(實際計數 - 期望計數) / 期望計數
    relative_noise = (photon_count_actual - photon_count_mean) / (photon_count_mean + 1e-6)
    
    # 4. 銀鹽顆粒效應：空間相關性（顆粒有物理尺寸）
    # 使用高斯模糊模擬銀鹽晶體的有限尺寸
    grain_blur_sigma = grain_params.grain_size  # 微米 → 像素（簡化對應）
    if grain_blur_sigma > 0.5:
        kernel_size = int(grain_blur_sigma * 4) | 1  # 確保奇數
        kernel_size = max(3, min(kernel_size, 15))  # 限制範圍
        relative_noise = cv2.GaussianBlur(
            relative_noise, 
            (kernel_size, kernel_size), 
            grain_blur_sigma
        )
    
    # 5. 標準化 relative_noise 到基準範圍
    # 使用 3-sigma 原則：99.7% 的值在 [-3σ, +3σ]
    noise_std = np.std(relative_noise)
    if noise_std > 1e-6:
        relative_noise_normalized = relative_noise / (3 * noise_std)
    else:
        relative_noise_normalized = relative_noise
    
    # 6. 應用顆粒密度與強度調整
    # grain_density: 影響噪聲強度（密度越高，噪聲越明顯）
    # intensity: 用戶調整的整體顆粒強度
    grain_noise = relative_noise_normalized * grain_params.grain_density * grain_params.intensity
    
    return np.clip(grain_noise, -1, 1)


def apply_grain(response_r: Optional[np.ndarray], response_g: Optional[np.ndarray], 
                response_b: Optional[np.ndarray], response_total: np.ndarray, 
                film: FilmProfile, sens: float) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    生成胶片顆粒效果
    
    根據 GrainParams.mode 選擇：
    - "artistic": 藝術模式（現有行為，中間調顆粒最明顯）
    - "poisson": 物理模式（Poisson 噪聲，暗部顆粒更明顯）
    
    Args:
        response_r, response_g, response_b: RGB 通道的光度數據（彩色胶片）
        response_total: 全色通道的光度數據
        film: 胶片配置對象
        sens: 敏感度參數
        
    Returns:
        (weighted_noise_r, weighted_noise_g, weighted_noise_b, weighted_noise_total): 各通道的顆粒噪聲
    """
    # 判斷是否使用 Poisson 模式
    use_poisson = (hasattr(film, 'grain_params') and 
                   film.grain_params is not None and
                   film.grain_params.mode == "poisson")
    
    if film.color_type == "color" and all([response_r is not None, response_g is not None,  response_b is not None]):
        # 彩色胶片：為每個通道生成獨立的顆粒
        if use_poisson:
            weighted_noise_r = generate_poisson_grain(response_r, film.grain_params)
            weighted_noise_g = generate_poisson_grain(response_g, film.grain_params)
            weighted_noise_b = generate_poisson_grain(response_b, film.grain_params)
        else:
            # 藝術模式（現有行為）
            weighted_noise_r = generate_grain_for_channel(response_r, sens)
            weighted_noise_g = generate_grain_for_channel(response_g, sens)
            weighted_noise_b = generate_grain_for_channel(response_b, sens)
        weighted_noise_total = None
    else:
        # 黑白胶片：僅生成全色通道的顆粒
        if use_poisson:
            weighted_noise_total = generate_poisson_grain(response_total, film.grain_params)
        else:
            weighted_noise_total = generate_grain_for_channel(response_total, sens)
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


# ==================== 光學擴散效果 ====================

def calculate_bloom_params(avg_response: float, sens_factor: float) -> Tuple[float, int, float, float]:
    """
    根據平均亮度計算光暈參數
    
    Args:
        avg_response: 平均亮度
        sens_factor: 胶片敏感係數
        
    Returns:
        (sens, rads, strg, base): 敏感度、擴散半徑、光暈強度、基礎擴散
    """
    # 根據平均亮度計算敏感度（暗圖更敏感）
    sens = float((1.0 - avg_response) * SENSITIVITY_SCALE + SENSITIVITY_BASE)
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


def apply_bloom_conserved(lux: np.ndarray, bloom_params, blur_scale: int, blur_sigma_scale: float) -> np.ndarray:
    """
    物理導向的光暈效果（能量守恆版本）
    
    與藝術模式的差異：
    1. 從高光區域提取能量（超過閾值部分）
    2. 應用 PSF（點擴散函數）重新分配能量
    3. 從原圖減去提取的能量
    4. 加上散射後的光暈
    5. 驗證總能量守恆：∑ E_in ≈ ∑ E_out
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        bloom_params: BloomParams 對象
        blur_scale: 模糊核大小倍數
        blur_sigma_scale: 模糊 sigma 倍數
        
    Returns:
        應用光暈後的光度數據（能量守恆）
    """
    # 1. 提取高光區域（超過閾值）
    threshold = bloom_params.threshold
    highlights = np.maximum(lux - threshold, 0)
    
    # 2. 計算散射能量（比例）
    scattering_ratio = bloom_params.scattering_ratio
    scattered_energy = highlights * scattering_ratio
    
    # 3. 應用點擴散函數（PSF）
    ksize = bloom_params.radius * blur_scale
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    
    if bloom_params.psf_type == "gaussian":
        # 高斯 PSF（各向同性）
        bloom_layer = cv2.GaussianBlur(scattered_energy, (ksize, ksize), 
                                        bloom_params.sensitivity * blur_sigma_scale)
    elif bloom_params.psf_type == "exponential":
        # 雙指數 PSF（長拖尾，模擬 Halation）
        # 簡化：使用兩次高斯模糊近似
        sigma1 = bloom_params.sensitivity * blur_sigma_scale
        sigma2 = sigma1 * 2.0
        bloom_layer = (cv2.GaussianBlur(scattered_energy, (ksize, ksize), sigma1) * 0.7 +
                       cv2.GaussianBlur(scattered_energy, (ksize, ksize), sigma2) * 0.3)
    else:
        bloom_layer = cv2.GaussianBlur(scattered_energy, (ksize, ksize), 
                                        bloom_params.sensitivity * blur_sigma_scale)
    
    # 4. 正規化 PSF（確保 ∫ PSF = 1，能量守恆）
    if bloom_params.energy_conservation:
        # 保持總能量不變
        total_scattered = np.sum(scattered_energy)
        total_bloom = np.sum(bloom_layer)
        if total_bloom > 1e-6:  # 避免除以零
            bloom_layer = bloom_layer * (total_scattered / total_bloom)
    
    # 5. 從原圖減去散射能量
    lux_corrected = lux - scattered_energy
    
    # 6. 加上散射後的光暈
    result = lux_corrected + bloom_layer
    
    # 7. 驗證能量守恆（調試用，可選）
    if bloom_params.energy_conservation:
        energy_in = np.sum(lux)
        energy_out = np.sum(result)
        if abs(energy_in - energy_out) / (energy_in + 1e-6) > 0.01:  # 誤差 > 1%
            import warnings
            warnings.warn(f"能量守恆誤差: {abs(energy_in - energy_out) / energy_in * 100:.2f}%")
    
    return np.clip(result, 0, 1)


def apply_halation(lux: np.ndarray, halation_params, wavelength: float = 550.0) -> np.ndarray:
    """
    應用 Halation（背層反射）效果
    
    物理機制：
    1. 光穿透乳劑層與片基
    2. 通過/被 Anti-Halation 層吸收
    3. 到達背板反射
    4. 往返路徑產生大範圍光暈
    
    遵循 Beer-Lambert 定律：
    - T(λ) = exp(-α(λ)L)
    - 雙程透過：f_h(λ) ≈ k · T(λ)² · R_bp
    
    與 Bloom 的區別：
    - Bloom: 短距離（20-30 px），高斯核，乳劑內散射
    - Halation: 長距離（100-200 px），指數拖尾，背層反射
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        halation_params: HalationParams 對象
        wavelength: 當前通道的波長（nm），用於 Beer-Lambert 衰減
        
    Returns:
        應用 Halation 後的光度數據（能量守恆）
    """
    if not halation_params.enabled:
        return lux
    
    # 1. 波長依賴透過率（Beer-Lambert）
    # 根據 wavelength 插值計算透過率
    # 簡化：使用預設的 RGB 透過率
    if wavelength < 500:  # 藍光
        transmittance = halation_params.transmittance_b
    elif wavelength < 600:  # 綠光
        transmittance = halation_params.transmittance_g
    else:  # 紅光
        transmittance = halation_params.transmittance_r
    
    # 2. Anti-Halation 層與背板反射
    # f_h = (1 - ah_absorption) * backplate_reflectance * transmittance²
    ah_factor = 1.0 - halation_params.ah_absorption
    total_factor = ah_factor * halation_params.backplate_reflectance * (transmittance ** 2)
    
    # 3. 提取會產生 Halation 的高光（閾值：0.5，較 Bloom 低）
    halation_threshold = 0.5
    highlights = np.maximum(lux - halation_threshold, 0)
    
    # 4. 應用能量係數
    halation_energy = highlights * total_factor * halation_params.energy_fraction
    
    # 5. 應用長尾 PSF
    ksize = halation_params.psf_radius
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    
    if halation_params.psf_type == "exponential":
        # 指數拖尾：使用多尺度高斯近似
        # PSF(r) ≈ exp(-k·r)，用三層高斯疊加近似
        sigma_base = halation_params.psf_radius * halation_params.psf_decay_rate
        
        # 短、中、長距離成分
        halation_layer = (
            cv2.GaussianBlur(halation_energy, (ksize//3, ksize//3), sigma_base) * 0.5 +
            cv2.GaussianBlur(halation_energy, (ksize, ksize), sigma_base * 2.0) * 0.3 +
            cv2.GaussianBlur(halation_energy, (ksize, ksize), sigma_base * 4.0) * 0.2
        )
    elif halation_params.psf_type == "lorentzian":
        # Lorentzian（Cauchy）拖尾：更長的尾部
        # 近似：使用極大 sigma 的高斯
        sigma_long = halation_params.psf_radius * 0.3
        halation_layer = cv2.GaussianBlur(halation_energy, (ksize, ksize), sigma_long)
    else:
        # 預設：高斯（較短拖尾）
        sigma = halation_params.psf_radius * 0.15
        halation_layer = cv2.GaussianBlur(halation_energy, (ksize, ksize), sigma)
    
    # 6. 能量守恆正規化
    total_energy_in = np.sum(halation_energy)
    total_energy_out = np.sum(halation_layer)
    if total_energy_out > 1e-6:
        halation_layer = halation_layer * (total_energy_in / total_energy_out)
    
    # 7. 從原圖減去被反射的能量，加上散射後的光暈
    result = lux - halation_energy + halation_layer
    
    return np.clip(result, 0, 1)


def apply_optical_effects_separated(
    response_r: Optional[np.ndarray],
    response_g: Optional[np.ndarray],
    response_b: Optional[np.ndarray],
    bloom_params,
    halation_params,
    blur_scale_r: int = 3,
    blur_scale_g: int = 2,
    blur_scale_b: int = 1
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], Optional[np.ndarray]]:
    """
    分離應用 Bloom 與 Halation（中等物理模式）
    
    流程：
    1. 對每個通道先應用 Bloom（短距離，乳劑內散射）
    2. 再應用 Halation（長距離，背層反射）
    3. 維持能量守恆
    
    Args:
        response_r/g/b: RGB 通道響應
        bloom_params: Bloom 參數
        halation_params: Halation 參數
        blur_scale_r/g/b: 各通道模糊倍數（波長依賴）
        
    Returns:
        (bloom_r, bloom_g, bloom_b): 應用光學效果後的通道
    """
    results = []
    
    for response, blur_scale, wavelength in [
        (response_r, blur_scale_r, 650.0),  # 紅光
        (response_g, blur_scale_g, 550.0),  # 綠光
        (response_b, blur_scale_b, 450.0)   # 藍光
    ]:
        if response is None:
            results.append(None)
            continue
        
        # Step 1: Bloom（短距離）
        if bloom_params.mode == "physical":
            result = apply_bloom_conserved(response, bloom_params, 
                                          blur_scale=blur_scale, 
                                          blur_sigma_scale=15 + blur_scale * 10)
        else:
            # Artistic 模式暫不處理
            result = response
        
        # Step 2: Halation（長距離）
        if halation_params.enabled:
            result = apply_halation(result, halation_params, wavelength=wavelength)
        
        results.append(result)
    
    return tuple(results)


def apply_hd_curve(exposure: np.ndarray, hd_params: film_models.HDCurveParams) -> np.ndarray:
    """
    應用 H&D 曲線（Hurter-Driffield Characteristic Curve）
    
    實作膠片的非線性響應特性：曝光量 (H) → 光學密度 (D) → 透射率 (T)
    
    H&D 曲線包含三個區段：
    1. Toe（趾部）：低曝光量（陰影區域），曲線壓縮
    2. Linear（線性區）：中間曝光量，對數線性響應
    3. Shoulder（肩部）：高曝光量（高光區域），曲線壓縮
    
    物理原理：
    - 光學密度：D = log10(1/T)，其中 T 為透射率
    - 線性區：D = gamma * log10(H) + D_fog
    - Toe/Shoulder：使用平滑過渡函數（soft compression）
    
    注意：
    - 此為膠片物理響應，與顯示 gamma (2.2) 無關
    - 負片：gamma ≈ 0.6-0.7（低對比度，留後製空間）
    - 正片：gamma ≈ 1.5-2.0（高對比度，直接觀看）
    
    Args:
        exposure: 曝光量數據（0-1 範圍，相對值）
        hd_params: H&D 曲線參數
        
    Returns:
        透射率數據（0-1 範圍）
    """
    if not hd_params.enabled:
        # 未啟用 H&D 曲線，直接返回（保持向後相容）
        return exposure
    
    # 0. 確保曝光量為正值（處理邊界條件）
    exposure_safe = np.clip(exposure, 1e-10, None)
    
    # 1. 轉換為對數曝光量（避免 log(0)）
    # 使用相對曝光量，假設 exposure=1.0 為正常曝光
    log_exposure = np.log10(exposure_safe)
    
    # 2. 線性區段：D = gamma * log10(H) + D_fog
    # 標準化：假設 log10(1.0) = 0 為參考點
    density = hd_params.gamma * log_exposure + (hd_params.D_min + hd_params.D_max) / 2
    
    # 3. Toe（趾部）：低曝光量的壓縮
    # 使用平滑函數：當 log_exposure < toe_end 時，密度增長變慢
    if hd_params.toe_enabled:
        toe_mask = log_exposure < hd_params.toe_end
        if np.any(toe_mask):
            # Toe 過渡函數：使用 soft clip（類似 tanh）
            # 計算相對於 toe_end 的距離
            toe_distance = (hd_params.toe_end - log_exposure[toe_mask]) / (hd_params.toe_end + 1e-6)
            # 應用壓縮（越遠離 toe_end，壓縮越強）
            toe_compression = 1.0 - hd_params.toe_strength * (1.0 - np.exp(-toe_distance))
            density[toe_mask] *= toe_compression
    
    # 4. Shoulder（肩部）：高曝光量的壓縮
    # 當 log_exposure > shoulder_start 時，密度增長變慢，逐漸飽和至 D_max
    if hd_params.shoulder_enabled:
        shoulder_mask = log_exposure > hd_params.shoulder_start
        if np.any(shoulder_mask):
            # Shoulder 過渡函數：漸近至 D_max
            # 計算相對於 shoulder_start 的距離
            shoulder_distance = (log_exposure[shoulder_mask] - hd_params.shoulder_start)
            # 應用壓縮（越遠離 shoulder_start，越接近 D_max）
            shoulder_compression = hd_params.shoulder_strength * shoulder_distance
            # 軟飽和：使用指數衰減逼近 D_max
            density[shoulder_mask] = (hd_params.D_max - 
                                      (hd_params.D_max - density[shoulder_mask]) * 
                                      np.exp(-shoulder_compression))
    
    # 5. 限制在有效動態範圍內
    density = np.clip(density, hd_params.D_min, hd_params.D_max)
    
    # 6. 轉換為透射率：T = 10^(-D)
    # 透射率：光線透過膠片的比例（0 = 完全阻擋，1 = 完全透過）
    transmittance = 10 ** (-density)
    
    # 7. 正規化到 [0, 1] 範圍（考慮 D_min 對應的基礎透射率）
    T_min = 10 ** (-hd_params.D_max)  # 最小透射率（對應最大密度）
    T_max = 10 ** (-hd_params.D_min)  # 最大透射率（對應最小密度）
    transmittance_normalized = (transmittance - T_min) / (T_max - T_min + 1e-6)
    
    return np.clip(transmittance_normalized, 0, 1)


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
    result = bloom * layer.diffuse_weight + np.power(lux, layer.response_curve) * layer.direct_weight
    
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


def optical_processing(response_r: Optional[np.ndarray], response_g: Optional[np.ndarray], 
                      response_b: Optional[np.ndarray], response_total: np.ndarray,
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
        response_r, response_g, response_b: RGB 通道的光度數據
        response_total: 全色通道的光度數據
        film: 胶片配置對象
        grain_style: 顆粒風格
        tone_style: Tone mapping 風格
        
    Returns:
        處理後的圖像 (0-255 uint8)
    """
    # 1. 計算自適應參數
    avg_response = average_response(response_total)
    sens, rads, strg, base = calculate_bloom_params(avg_response, film.sensitivity_factor)
    
    # 2. 應用顆粒（如果需要）
    use_grain = (grain_style != "不使用")
    if use_grain:
        grain_r, grain_g, grain_b, grain_total_noise = apply_grain(
            response_r, response_g, response_b, response_total, film, sens
        )
    else:
        grain_r = grain_g = grain_b = grain_total_noise = None
    
    # 3. 處理各通道（依據物理模式選擇 Bloom 實作）
    use_physical_bloom = (hasattr(film, 'physics_mode') and 
                          film.physics_mode == film_models.PhysicsMode.PHYSICAL and
                          hasattr(film, 'bloom_params') and
                          film.bloom_params.mode == "physical")
    
    if film.color_type == "color" and all([response_r is not None, response_g is not None,  response_b is not None]):
        # 彩色胶片：處理 RGB 三個通道
        # 不同顏色通道的光暈特性不同（紅色擴散最廣，藍色最窄）
        
        # 檢查是否啟用中等物理模式（Bloom + Halation 分離）
        use_medium_physics = (use_physical_bloom and 
                             hasattr(film, 'halation_params') and 
                             film.halation_params.enabled)
        
        if use_medium_physics:
            # 中等物理模式：Bloom + Halation 分離（TASK-003 Phase 2）
            bloom_r, bloom_g, bloom_b = apply_optical_effects_separated(
                response_r, response_g, response_b,
                film.bloom_params, film.halation_params,
                blur_scale_r=3, blur_scale_g=2, blur_scale_b=1
            )
        elif use_physical_bloom:
            # 物理模式：僅 Bloom（能量守恆）
            bloom_r = apply_bloom_conserved(response_r, film.bloom_params, blur_scale=3, blur_sigma_scale=55)
            bloom_g = apply_bloom_conserved(response_g, film.bloom_params, blur_scale=2, blur_sigma_scale=35)
            bloom_b = apply_bloom_conserved(response_b, film.bloom_params, blur_scale=1, blur_sigma_scale=15)
        else:
            # 藝術模式：現有行為
            bloom_r = apply_bloom_to_channel(response_r, sens, rads, strg, base, blur_scale=3, blur_sigma_scale=55)
            bloom_g = apply_bloom_to_channel(response_g, sens, rads, strg, base, blur_scale=2, blur_sigma_scale=35)
            bloom_b = apply_bloom_to_channel(response_b, sens, rads, strg, base, blur_scale=1, blur_sigma_scale=15)
        
        # 組合各層
        response_r_final = combine_layers_for_channel(
            bloom_r, response_r, film.red_layer, grain_r, grain_g, grain_b, 
            film.panchromatic_layer.grain_intensity, use_grain
        )
        response_g_final = combine_layers_for_channel(
            bloom_g, response_g, film.green_layer, grain_r, grain_g, grain_b,
            film.panchromatic_layer.grain_intensity, use_grain
        )
        response_b_final = combine_layers_for_channel(
            bloom_b, response_b, film.blue_layer, grain_r, grain_g, grain_b,
            film.panchromatic_layer.grain_intensity, use_grain
        )
        
        # 3.5. 應用 H&D 曲線（膠片特性曲線，物理模式專用）
        # 注意：H&D 曲線模擬膠片的非線性響應，與 tone mapping（顯示轉換）不同
        use_hd_curve = (hasattr(film, 'physics_mode') and 
                        film.physics_mode == film_models.PhysicsMode.PHYSICAL and
                        hasattr(film, 'hd_curve_params') and
                        film.hd_curve_params.enabled)
        
        if use_hd_curve:
            response_r_final = apply_hd_curve(response_r_final, film.hd_curve_params)
            response_g_final = apply_hd_curve(response_g_final, film.hd_curve_params)
            response_b_final = apply_hd_curve(response_b_final, film.hd_curve_params)
        
        # 4. Tone mapping
        if tone_style == "filmic":
            result_r, result_g, result_b, _ = apply_filmic(response_r_final, response_g_final, response_b_final, response_total, film)
        else:
            result_r, result_g, result_b, _ = apply_reinhard(response_r_final, response_g_final, response_b_final, response_total, film)
        
        # 5. 合成最終圖像
        combined_r = (result_r * 255).astype(np.uint8)
        combined_g = (result_g * 255).astype(np.uint8)
        combined_b = (result_b * 255).astype(np.uint8)
        final_image = cv2.merge([combined_b, combined_g, combined_r])
        
    else:
        # 黑白胶片：僅處理全色通道
        bloom = apply_bloom_to_channel(response_total, sens, rads, strg, base, blur_scale=3, blur_sigma_scale=55)
        
        # 組合層
        if use_grain and grain_total_noise is not None:
            lux_final = (bloom * film.panchromatic_layer.diffuse_weight + 
                        np.power(response_total, film.panchromatic_layer.response_curve) * film.panchromatic_layer.direct_weight +
                        grain_total_noise * film.panchromatic_layer.grain_intensity)
        else:
            lux_final = (bloom * film.panchromatic_layer.diffuse_weight + 
                        np.power(response_total, film.panchromatic_layer.response_curve) * film.panchromatic_layer.direct_weight)
        
        # 應用 H&D 曲線（黑白膠片）
        use_hd_curve = (hasattr(film, 'physics_mode') and 
                        film.physics_mode == film_models.PhysicsMode.PHYSICAL and
                        hasattr(film, 'hd_curve_params') and
                        film.hd_curve_params.enabled)
        
        if use_hd_curve:
            lux_final = apply_hd_curve(lux_final, film.hd_curve_params)
        
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


def process_image(uploaded_image, film_type: str, grain_style: str, tone_style: str, 
                 physics_params: Optional[dict] = None) -> Tuple[np.ndarray, float, str]:
    """
    處理上傳的圖像
    
    這是主要的處理流程，協調所有步驟：
    1. 讀取圖像
    2. 獲取胶片配置
    3. 應用物理參數（如有）
    4. 標準化尺寸
    5. 計算光度響應
    6. 應用光學效果
    
    Args:
        uploaded_image: 上傳的圖像文件
        film_type: 胶片類型
        grain_style: 顆粒風格
        tone_style: Tone mapping 風格
        physics_params: 物理模式參數字典（可選）
            - physics_mode: PhysicsMode (ARTISTIC/PHYSICAL/HYBRID)
            - bloom_mode: str
            - bloom_threshold: float
            - bloom_scattering_ratio: float
            - hd_enabled: bool
            - hd_gamma: float
            - hd_toe_strength: float
            - hd_shoulder_strength: float
            - grain_mode: str
            - grain_size: float
            - grain_intensity: float
        
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
        
        # 3. 應用物理參數（如有提供）
        if physics_params:
            from dataclasses import replace
            
            # 設定物理模式
            film.physics_mode = physics_params.get('physics_mode', film.physics_mode)
            
            # Bloom 參數
            film.bloom_params.mode = physics_params.get('bloom_mode', 'artistic')
            film.bloom_params.threshold = physics_params.get('bloom_threshold', 0.8)
            film.bloom_params.scattering_ratio = physics_params.get('bloom_scattering_ratio', 0.1)
            
            # H&D 曲線參數
            film.hd_curve_params.enabled = physics_params.get('hd_enabled', False)
            if film.hd_curve_params.enabled:
                film.hd_curve_params.gamma = physics_params.get('hd_gamma', 0.65)
                film.hd_curve_params.toe_strength = physics_params.get('hd_toe_strength', 2.0)
                film.hd_curve_params.shoulder_strength = physics_params.get('hd_shoulder_strength', 1.5)
            
            # 顆粒參數
            film.grain_params.mode = physics_params.get('grain_mode', 'artistic')
            film.grain_params.grain_size = physics_params.get('grain_size', 1.5)
            film.grain_params.intensity = physics_params.get('grain_intensity', 0.8)
        
        # 4. 調整顆粒強度（傳統 grain_style）
        film = adjust_grain_intensity(film, grain_style)
        
        # 5. 標準化圖像尺寸
        image = standardize(image)
        
        # 6. 計算光度響應
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 7. 應用光學處理
        final_image = optical_processing(response_r, response_g, response_b, response_total, film, grain_style, tone_style)
        
        # 8. 生成輸出文件名
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        mode_suffix = physics_params.get('physics_mode').name.lower() if physics_params else "artistic"
        output_path = f"phos_{film_type.lower()}_{mode_suffix}_{timestamp}.jpg"
        
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
        ["NC200", "Portra400", "Ektar100", "Velvia50", "Gold200", "ProImage100", "Superia400", 
         "Cinestill800T", "AS100", "HP5Plus400", "TriX400", "FP4Plus125", "FS200"],
        index=0,
        help="選擇要模擬的胶片類型，下方會顯示詳細資訊"
    )
    
    # 底片描述資料庫
    film_descriptions = {
        "NC200": {
            "name": "NC200",
            "brand": "Fujifilm C200 風格",
            "type": "🎨 彩色負片",
            "iso": "ISO 200",
            "desc": "經典富士色調，萬用平衡底片。色彩自然清新，適合日常拍攝。",
            "features": ["✓ 平衡色彩", "✓ 適中顆粒", "✓ 萬用場景"],
            "best_for": "日常記錄、旅行、人像"
        },
        "Portra400": {
            "name": "Portra 400",
            "brand": "Kodak",
            "type": "🎨 彩色負片",
            "iso": "ISO 400",
            "desc": "人像攝影之王。細膩膚色還原，極低顆粒，柔和色調。",
            "features": ["✓ 細膩膚色", "✓ 超低顆粒", "✓ 柔和色調"],
            "best_for": "人像、婚禮、時尚攝影"
        },
        "Ektar100": {
            "name": "Ektar 100",
            "brand": "Kodak",
            "type": "🎨 彩色負片",
            "iso": "ISO 100",
            "desc": "風景攝影利器。極高飽和度，超細顆粒，色彩鮮豔飽滿。",
            "features": ["✓ 極高飽和", "✓ 極細顆粒", "✓ 高銳度"],
            "best_for": "風景、建築、產品攝影"
        },
        "Velvia50": {
            "name": "Velvia 50",
            "brand": "Fujifilm",
            "type": "🎨 彩色反轉片",
            "iso": "ISO 50",
            "desc": "⭐ 風景之王。極致飽和度，深邃藍天，鮮豔花卉。富士經典正片。",
            "features": ["✓ 極致飽和", "✓ 冷調偏向", "✓ 超細顆粒"],
            "best_for": "風景、藍天、花卉攝影"
        },
        "Gold200": {
            "name": "Gold 200",
            "brand": "Kodak",
            "type": "🎨 彩色負片",
            "iso": "ISO 200",
            "desc": "⭐ 陽光金黃。溫暖色調，柔和高光，街拍最愛。性價比經典。",
            "features": ["✓ 溫暖色調", "✓ 柔和高光", "✓ 金黃偏向"],
            "best_for": "街拍、日常、陽光場景"
        },
        "ProImage100": {
            "name": "ProImage 100",
            "brand": "Kodak",
            "type": "🎨 彩色負片",
            "iso": "ISO 100",
            "desc": "⭐ 日常經典。色彩平衡，適中飽和，萬用底片。性價比之選。",
            "features": ["✓ 平衡色彩", "✓ 穩定曝光", "✓ 性價比高"],
            "best_for": "日常、旅行、萬用場景"
        },
        "Superia400": {
            "name": "Superia 400",
            "brand": "Fujifilm",
            "type": "🎨 彩色負片",
            "iso": "ISO 400",
            "desc": "⭐ 清新綠調。富士日常膠卷，高寬容度，自然風光表現優異。",
            "features": ["✓ 清新色調", "✓ 綠色偏向", "✓ 高寬容度"],
            "best_for": "日常、自然、風光攝影"
        },
        "Cinestill800T": {
            "name": "CineStill 800T",
            "brand": "CineStill",
            "type": "🎨 電影負片",
            "iso": "ISO 800",
            "desc": "電影感鎢絲燈片。強光暈效果，溫暖色調，夜景氛圍絕佳。",
            "features": ["✓ 強烈光暈", "✓ 電影色調", "✓ 夜景專用"],
            "best_for": "夜景、霓虹燈、電影感"
        },
        "AS100": {
            "name": "ACROS 100",
            "brand": "Fujifilm",
            "type": "⚫ 黑白負片",
            "iso": "ISO 100",
            "desc": "灰階細膩，顆粒柔和。富士經典黑白片，中間調豐富。",
            "features": ["✓ 細膩灰階", "✓ 柔和顆粒", "✓ 豐富層次"],
            "best_for": "風景、建築、靜物"
        },
        "HP5Plus400": {
            "name": "HP5 Plus 400",
            "brand": "Ilford",
            "type": "⚫ 黑白負片",
            "iso": "ISO 400",
            "desc": "經典黑白片。明顯顆粒，高對比，街拍常青樹。",
            "features": ["✓ 明顯顆粒", "✓ 高對比度", "✓ 經典風格"],
            "best_for": "街拍、紀實、人文攝影"
        },
        "TriX400": {
            "name": "Tri-X 400",
            "brand": "Kodak",
            "type": "⚫ 黑白負片",
            "iso": "ISO 400",
            "desc": "⭐ 街拍傳奇。標誌性顆粒，經典對比，紀實攝影首選。",
            "features": ["✓ 標誌顆粒", "✓ 高對比度", "✓ 經典S曲線"],
            "best_for": "街拍、紀實、報導攝影"
        },
        "FP4Plus125": {
            "name": "FP4 Plus 125",
            "brand": "Ilford",
            "type": "⚫ 黑白負片",
            "iso": "ISO 125",
            "desc": "⭐ 細膩灰階。低速精細，豐富中間調，適合慢速攝影。",
            "features": ["✓ 低速精細", "✓ 低顆粒", "✓ 豐富中調"],
            "best_for": "風景、靜物、慢速攝影"
        },
        "FS200": {
            "name": "FS200",
            "brand": "實驗性",
            "type": "⚫ 黑白正片",
            "iso": "ISO 200",
            "desc": "高對比度黑白正片。實驗性模型，強烈對比效果。",
            "features": ["✓ 超高對比", "✓ 實驗風格", "✓ 正片特性"],
            "best_for": "實驗性創作、高對比場景"
        }
    }
    
    # 顯示選中底片的詳細資訊
    film_info = film_descriptions.get(film_type, {})
    if film_info:
        st.markdown(f"""
        <div style='background: linear-gradient(135deg, rgba(26, 31, 46, 0.6), rgba(26, 31, 46, 0.4)); 
                    padding: 1rem; 
                    border-radius: 8px; 
                    border-left: 3px solid #FF6B6B;
                    margin-top: 0.5rem;
                    margin-bottom: 1rem;'>
            <p style='color: #FF6B6B; font-weight: 600; font-size: 1.05rem; margin: 0 0 0.25rem 0;'>
                {film_info['name']}
            </p>
            <p style='color: #B8B8B8; font-size: 0.85rem; margin: 0 0 0.75rem 0;'>
                {film_info['brand']} · {film_info['type']} · {film_info['iso']}
            </p>
            <p style='color: #E8E8E8; font-size: 0.9rem; line-height: 1.5; margin: 0 0 0.75rem 0;'>
                {film_info['desc']}
            </p>
            <div style='display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem;'>
                {''.join([f"<span style='background: rgba(255, 107, 107, 0.15); color: #FFB4B4; padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.8rem;'>{feature}</span>" for feature in film_info['features']])}
            </div>
            <p style='color: #888; font-size: 0.8rem; margin: 0;'>
                💡 適用場景：{film_info['best_for']}
            </p>
        </div>
        """, unsafe_allow_html=True)

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
    
    # ==================== 物理模式設定 (NEW) ====================
    st.markdown("### ✨ 渲染模式")
    
    physics_mode_choice = st.radio(
        "選擇渲染模式",
        ["Artistic（藝術）", "Physical（物理）", "Hybrid（混合）"],
        index=0,
        help="""選擇影像渲染方式:
        
        **Artistic**: 視覺優先，討喜色彩（預設）
        **Physical**: 物理準確，能量守恆，H&D曲線
        **Hybrid**: 自由混合藝術與物理特性
        
        詳見 PHYSICAL_MODE_GUIDE.md""",
        label_visibility="collapsed"
    )
    
    # 映射選擇到 PhysicsMode enum
    from film_models import PhysicsMode
    physics_mode_map = {
        "Artistic（藝術）": PhysicsMode.ARTISTIC,
        "Physical（物理）": PhysicsMode.PHYSICAL,
        "Hybrid（混合）": PhysicsMode.HYBRID
    }
    physics_mode = physics_mode_map[physics_mode_choice]
    
    # 顯示模式說明
    if physics_mode == PhysicsMode.ARTISTIC:
        st.info("🎨 **藝術模式**: 視覺導向，中調顆粒，鮮艷色彩")
    elif physics_mode == PhysicsMode.PHYSICAL:
        st.info("🔬 **物理模式**: 能量守恆、H&D曲線、泊松顆粒")
    else:  # HYBRID
        st.info("⚙️ **混合模式**: 可自訂各項參數（展開下方設定）")
    
    # 進階物理參數（僅 Physical 或 Hybrid 模式顯示）
    if physics_mode in [PhysicsMode.PHYSICAL, PhysicsMode.HYBRID]:
        st.markdown("---")
        st.markdown("### ⚙️ 物理參數")
        
        # Bloom 參數
        with st.expander("📊 Bloom（光暈）參數", expanded=False):
            bloom_mode = st.radio(
                "Bloom 模式",
                ["artistic", "physical"],
                index=1 if physics_mode == PhysicsMode.PHYSICAL else 0,
                help="artistic: 可增加能量（視覺導向）\nphysical: 能量守恆（物理準確）",
                key="bloom_mode"
            )
            
            bloom_threshold = st.slider(
                "高光閾值 (Threshold)",
                min_value=0.5,
                max_value=0.95,
                value=0.8,
                step=0.05,
                help="控制哪些像素參與散射。較低值 → 更多高光 → 光暈明顯",
                key="bloom_threshold"
            )
            
            if bloom_mode == "physical":
                bloom_scattering_ratio = st.slider(
                    "散射能量比例",
                    min_value=0.05,
                    max_value=0.30,
                    value=0.10,
                    step=0.05,
                    help="控制多少高光能量參與散射。真實膠片約 5-15%",
                    key="bloom_scattering"
                )
            else:
                bloom_scattering_ratio = 0.1  # 預設值
            
            st.caption(f"當前設定: {bloom_mode.upper()} 模式, 閾值 {bloom_threshold}, 散射 {bloom_scattering_ratio}")
        
        # H&D 曲線參數
        with st.expander("📈 H&D 曲線參數", expanded=False):
            hd_enabled = st.checkbox(
                "啟用 H&D 特性曲線",
                value=True if physics_mode == PhysicsMode.PHYSICAL else False,
                help="模擬真實膠片的對數響應與動態範圍壓縮",
                key="hd_enabled"
            )
            
            if hd_enabled:
                hd_gamma = st.slider(
                    "Gamma（對比度）",
                    min_value=0.50,
                    max_value=2.00,
                    value=0.65,
                    step=0.05,
                    help="負片: 0.6-0.7（低對比）\n正片: 1.5-2.0（高對比）",
                    key="hd_gamma"
                )
                
                hd_toe_strength = st.slider(
                    "Toe 強度（陰影壓縮）",
                    min_value=0.5,
                    max_value=5.0,
                    value=2.0,
                    step=0.5,
                    help="較高值 → 陰影更柔和、細節更豐富",
                    key="hd_toe"
                )
                
                hd_shoulder_strength = st.slider(
                    "Shoulder 強度（高光壓縮）",
                    min_value=0.5,
                    max_value=3.0,
                    value=1.5,
                    step=0.5,
                    help="較高值 → 高光渐進飽和、細節保留",
                    key="hd_shoulder"
                )
                
                st.caption(f"Gamma={hd_gamma}, Toe={hd_toe_strength}, Shoulder={hd_shoulder_strength}")
            else:
                hd_gamma = 0.65
                hd_toe_strength = 2.0
                hd_shoulder_strength = 1.5
        
        # 顆粒參數
        with st.expander("🎲 顆粒參數", expanded=False):
            grain_mode = st.radio(
                "顆粒模式",
                ["artistic", "poisson"],
                index=1 if physics_mode == PhysicsMode.PHYSICAL else 0,
                help="artistic: 中調峰值（視覺導向）\npoisson: 暗部峰值（光子統計）",
                key="grain_mode"
            )
            
            grain_size = st.slider(
                "顆粒尺寸 (μm)",
                min_value=0.5,
                max_value=3.5,
                value=1.5,
                step=0.5,
                help="ISO 100: 0.5-1.0\nISO 400: 1.0-2.0\nISO 1600+: 2.0-3.5",
                key="grain_size"
            )
            
            grain_intensity = st.slider(
                "顆粒強度",
                min_value=0.0,
                max_value=2.0,
                value=0.8,
                step=0.1,
                help="0.3: 輕微\n0.8: 適中\n1.5: 強烈",
                key="grain_intensity"
            )
            
            st.caption(f"{grain_mode.upper()} 模式, 尺寸 {grain_size}μm, 強度 {grain_intensity}")
    else:
        # Artistic 模式：使用預設值（不顯示參數）
        bloom_mode = "artistic"
        bloom_threshold = 0.8
        bloom_scattering_ratio = 0.1
        hd_enabled = False
        hd_gamma = 0.65
        hd_toe_strength = 2.0
        hd_shoulder_strength = 1.5
        grain_mode = "artistic"
        grain_size = 1.5
        grain_intensity = 0.8
    
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
        # 準備物理參數
        physics_params = {
            'physics_mode': physics_mode,
            'bloom_mode': bloom_mode,
            'bloom_threshold': bloom_threshold,
            'bloom_scattering_ratio': bloom_scattering_ratio,
            'hd_enabled': hd_enabled,
            'hd_gamma': hd_gamma,
            'hd_toe_strength': hd_toe_strength,
            'hd_shoulder_strength': hd_shoulder_strength,
            'grain_mode': grain_mode,
            'grain_size': grain_size,
            'grain_intensity': grain_intensity
        }
        
        # 處理圖像
        film_image, process_time, output_path = process_image(
            uploaded_image, film_type, grain_style, tone_style, physics_params
        )
        
        # 顯示結果（固定寬度）
        st.image(film_image, channels="BGR", width=800)
        st.success(f"✨ 底片顯影好了！用時 {process_time:.2f}秒 | 模式: {physics_mode.name}") 
        
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
                response_r, response_g, response_b, response_total = spectral_response(image_std, film_profile)
                
                # 光學處理
                result = optical_processing(
                    response_r, response_g, response_b, response_total,
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
                            st.image(result_rgb, caption=result.filename, width=200)
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
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>彩色胶片 Color Films (8款)</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>NC200</strong> - 富士經典日常</li>
                <li><strong>Portra400</strong> - Kodak 人像王者</li>
                <li><strong>Ektar100</strong> - Kodak 風景利器</li>
                <li><strong>Velvia50</strong> ⭐ - 富士極致飽和</li>
                <li><strong>Gold200</strong> ⭐ - Kodak 陽光金黃</li>
                <li><strong>ProImage100</strong> ⭐ - Kodak 日常經典</li>
                <li><strong>Superia400</strong> ⭐ - 富士清新綠調</li>
                <li><strong>Cinestill800T</strong> - 電影鎢絲燈</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div style='background: rgba(26, 31, 46, 0.3); padding: 1rem; border-radius: 8px;'>
            <p style='color: #E8E8E8; font-weight: 600; margin: 0 0 0.75rem 0;'>黑白胶片 B&W Films (5款)</p>
            <ul style='color: #B8B8B8; line-height: 1.8; margin: 0; padding-left: 1.25rem;'>
                <li><strong>AS100</strong> - 富士 ACROS 細膩</li>
                <li><strong>HP5Plus400</strong> - Ilford 經典</li>
                <li><strong>TriX400</strong> ⭐ - Kodak 街拍傳奇</li>
                <li><strong>FP4Plus125</strong> ⭐ - Ilford 低速精細</li>
                <li><strong>FS200</strong> - 實驗性高對比</li>
            </ul>
            <p style='color: #888; font-size: 0.85rem; margin-top: 0.5rem;'>⭐ = 新增底片</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 使用提示
    st.info("👈 請在左側邊欄選擇處理模式並上傳照片開始使用")
