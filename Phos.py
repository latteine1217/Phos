"""
Phos 0.4.1 - Film Simulation Based on Computational Optics

"No LUTs, we calculate LUX."

你说的对，但是 Phos. 是基于「计算光学」概念的胶片模拟。
通过计算光在底片上的行为，复现自然、柔美、立体的胶片质感。

Version: 0.4.1 (Spectral Brightness Fix)
Major Features: 
- 🎨 31通道光譜膠片模擬（Smits RGB→Spectrum）
- 🔬 真實膠片光譜敏感度曲線（4種膠片）
- ⚡ 3.5x 效能優化（branch-free vectorization + tiling）
- 🎯 物理正確色彩渲染（往返誤差 <3%）
- 📊 完整物理模式 UI 控制
- 🧪 ISO 統一推導系統 + Mie 散射理論

Legacy Features (v0.2.0-v0.3.0):
- 批量處理模式 + ZIP 下載
- 物理模式（H&D 曲線、Poisson 顆粒、能量守恆）
- Beer-Lambert Halation + 波長依賴 Bloom

Release Notes: See tasks/TASK-003-medium-physics/phase4_milestone4_completion.md
"""

import streamlit as st

# 设置页面配置 
st.set_page_config(
    page_title="Phos. 胶片模拟 v0.4.1",
    page_icon="🎞️",
    layout="wide",
    initial_sidebar_state="expanded"
)

import cv2
import numpy as np
import time
import warnings
from PIL import Image
import io
from typing import Optional, Tuple, List
from functools import lru_cache

# ==================== 導入 UI 組件 ====================
from ui_components import (
    apply_custom_styles, 
    render_sidebar, 
    render_single_image_result, 
    render_batch_processing_ui, 
    render_welcome_page
)

# 應用自定義樣式
apply_custom_styles()

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
    BloomParams,  # 新增：用於 Mie 散射類型提示
    GrainParams,  # Phase 1 Task 3: 用於統一的 generate_grain()
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

# ==================== Grain 統一處理函數（Phase 1 Task 3）====================

def generate_grain(
    lux_channel: np.ndarray,
    grain_params: GrainParams,
    sens: Optional[float] = None
) -> np.ndarray:
    """
    統一的顆粒生成函數（支援 artistic/poisson 模式）
    
    整合了原本分散的 generate_grain_for_channel() 和 generate_poisson_grain() 邏輯。
    根據 grain_params.mode 自動選擇對應的實作。
    
    物理機制：
        - Artistic 模式：視覺導向，中間調顆粒最明顯（保留現有美感）
        - Poisson 模式：物理導向，基於光子計數統計（暗部噪聲更明顯）
    
    Args:
        lux_channel: 光度通道數據 (0-1 範圍，float32)
        grain_params: GrainParams 對象（包含模式與所有參數）
        sens: 敏感度參數（僅 artistic 模式使用，poisson 模式忽略）
    
    Returns:
        np.ndarray: 顆粒噪聲（標準化到 [-1, 1] 範圍）
    
    Example:
        >>> # Artistic 模式（向後相容）
        >>> grain_params = GrainParams(mode="artistic", intensity=0.18)
        >>> noise = generate_grain(lux, grain_params, sens=0.5)
        
        >>> # Poisson 模式（物理準確）
        >>> grain_params = GrainParams(
        ...     mode="poisson",
        ...     intensity=0.15,
        ...     exposure_level=1000.0,
        ...     grain_size=1.0
        ... )
        >>> noise = generate_grain(lux, grain_params)
    
    Version: 0.5.0 (Phase 1 Task 3: Grain 統一化)
    """
    mode = grain_params.mode
    
    # ==================== Artistic 模式 ====================
    if mode == "artistic":
        # 原 generate_grain_for_channel() 邏輯
        if sens is None:
            raise ValueError("Artistic mode requires 'sens' parameter")
        
        # 創建正負噪聲（使用平方正態分佈產生更自然的顆粒）
        noise = np.random.normal(0, 1, lux_channel.shape).astype(np.float32)
        noise = noise ** 2
        noise = noise * np.random.choice([-1, 1], lux_channel.shape)
        
        # 創建權重圖（中等亮度區域權重最高，模擬胶片顆粒在中間調最明顯的特性）
        # 【Task 3-4: 移除無效 in-place 優化】
        weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
        weights = np.clip(weights, GRAIN_WEIGHT_MIN, GRAIN_WEIGHT_MAX)
        
        # 應用權重和敏感度
        sens_grain = np.clip(sens, GRAIN_SENS_MIN, GRAIN_SENS_MAX)
        weighted_noise = noise * weights * sens_grain
        
        # 添加輕微模糊使顆粒更柔和
        weighted_noise = cv2.GaussianBlur(weighted_noise, GRAIN_BLUR_KERNEL, GRAIN_BLUR_SIGMA)
        
        return np.clip(weighted_noise, -1, 1)
    
    # ==================== Poisson 模式（物理導向）====================
    elif mode == "poisson":
        # 原 generate_poisson_grain() 邏輯
        # 1. 將相對曝光量轉換為平均光子計數
        photon_count_mean = lux_channel * grain_params.exposure_level
        
        # 避免零或負值（添加小偏移）
        photon_count_mean = np.clip(photon_count_mean, 1.0, None)
        
        # 2. 根據 Poisson 分布生成實際光子計數
        # 使用正態近似（當 λ > 20 時，Poisson(λ) ≈ Normal(λ, √λ)）
        photon_count_actual = np.random.normal(
            loc=photon_count_mean, 
            scale=np.sqrt(photon_count_mean)
        ).astype(np.float32)
        
        # 確保非負
        photon_count_actual = np.maximum(photon_count_actual, 0)
        
        # 3. 計算相對噪聲：(實際計數 - 期望計數) / 期望計數
        relative_noise = (photon_count_actual - photon_count_mean) / (photon_count_mean + 1e-6)
        
        # 4. 銀鹽顆粒效應：空間相關性（顆粒有物理尺寸）
        grain_blur_sigma = grain_params.grain_size  # 微米 → 像素（簡化對應）
        if grain_blur_sigma > 0.5:
            kernel_size = int(grain_blur_sigma * 4) | 1  # 確保奇數
            kernel_size = max(3, min(kernel_size, 15))  # 限制範圍
            relative_noise = cv2.GaussianBlur(
                relative_noise, 
                (kernel_size, kernel_size), 
                grain_blur_sigma
            )
        
        # 5. 標準化 relative_noise 到基準範圍（3-sigma 原則）
        noise_std = np.std(relative_noise)
        if noise_std > 1e-6:
            relative_noise_normalized = relative_noise / (3 * noise_std)
        else:
            relative_noise_normalized = relative_noise
        
        # 6. 應用顆粒密度與強度調整
        grain_noise = relative_noise_normalized * grain_params.grain_density * grain_params.intensity
        
        return np.clip(grain_noise, -1, 1)
    
    else:
        raise ValueError(f"Unknown grain mode: {mode}. Expected 'artistic' or 'poisson'.")


# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 generate_grain() 統一介面





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
            weighted_noise_r = generate_grain(response_r, film.grain_params)
            weighted_noise_g = generate_grain(response_g, film.grain_params)
            weighted_noise_b = generate_grain(response_b, film.grain_params)
        else:
            # 藝術模式（使用 sens 參數，intensity 從 film.grain_params 獲取）
            weighted_noise_r = generate_grain(response_r, film.grain_params, sens=sens)
            weighted_noise_g = generate_grain(response_g, film.grain_params, sens=sens)
            weighted_noise_b = generate_grain(response_b, film.grain_params, sens=sens)
        weighted_noise_total = None
    else:
        # 黑白胶片：僅生成全色通道的顆粒
        if use_poisson:
            weighted_noise_total = generate_grain(response_total, film.grain_params)
        else:
            weighted_noise_total = generate_grain(response_total, film.grain_params, sens=sens)
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


# ==================== Bloom 統一處理函數（Phase 1 Task 2 - 策略模式重構 v0.6.0）====================

# 導入策略模式重構的 Bloom 模組
from bloom_strategies import apply_bloom

# 注意：apply_bloom() 現已移至 bloom_strategies.py
# 重構改進：
#   - 從 250+ 行 → 10 行（96% 代碼減少）
#   - 消除 if-elif-else 條件判斷（Good Taste）
#   - 每個策略 < 50 行（Simplicity）
#   - 物理假設獨立可辯護（Pragmatism）
#
# 若需查看具體實作，請參閱：
#   - bloom_strategies.py: ArtisticBloomStrategy, PhysicalBloomStrategy, MieCorrectedBloomStrategy
#
# API 保持完全向後相容，無需修改調用代碼


# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 apply_bloom() 統一介面





# ==================== Phase 1: 波長依賴散射 ====================

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


def apply_bloom_with_psf(
    response: np.ndarray,
    eta: float,
    psf: np.ndarray,
    threshold: float
) -> np.ndarray:
    """
    使用自定義 PSF 應用 Bloom 散射（能量守恆）
    
    能量守恆邏輯（與 Phase 2 一致）:
        output = response - scattered_energy + PSF(scattered_energy)
        
    Args:
        response: 單通道響應（0-1，float32）
        eta: 散射能量比例（0-1）
        psf: 正規化 PSF（∑psf = 1）
        threshold: 高光閾值（0-1）
    
    Returns:
        bloom: 散射後的通道（0-1，能量守恆）
    """
    # 1. 提取高光（超過閾值的部分才散射）
    highlights = np.where(response > threshold, response - threshold, 0.0).astype(np.float32)
    
    # 2. 計算散射能量
    scattered_energy = highlights * eta
    
    # 3. PSF 卷積（已正規化，∑psf=1）
    scattered_light = cv2.filter2D(scattered_energy, -1, psf, borderType=cv2.BORDER_REFLECT)
    
    # 4. 能量守恆重組
    # output = 原始響應 - 被散射掉的能量 + 散射後的光
    output = response - scattered_energy + scattered_light
    
    # 5. 安全裁切（數值穩定性）
    output = np.clip(output, 0.0, 1.0)
    
    return output


def apply_wavelength_bloom(
    response_r: np.ndarray,
    response_g: np.ndarray,
    response_b: np.ndarray,
    wavelength_params,
    bloom_params
) -> tuple:
    """
    應用波長依賴 Bloom 散射（Phase 1 核心函數）
    
    物理模型（Physicist Review Line 46-51）:
        能量權重: η(λ) = η_base × (λ_ref/λ)^p （p≈3-4，Mie+Rayleigh 混合）
        PSF 寬度:  σ(λ) = σ_base × (λ_ref/λ)^q （q≈0.5-1.0，小角散射）
        雙段核:    K(λ) = ρ(λ)·G(σ(λ)) + (1-ρ(λ))·E(κ(λ))
    
    預期效果:
        - 白色高光 → 藍色光暈（藍光散射更強）
        - 路燈核心黃色，外圈藍色（色散效應）
        - η_b/η_r ≈ 2.5x, σ_b/σ_r ≈ 1.35x
    
    Args:
        response_r/g/b: RGB 通道的乳劑響應（0-1，float32）
        wavelength_params: WavelengthBloomParams 實例
        bloom_params: BloomParams 實例
    
    Returns:
        (bloom_r, bloom_g, bloom_b): 散射後的 RGB 通道（0-1）
    """
    # ===== 使用 Mie 散射查表（唯一方法）=====
    # 所有 FilmProfile 已使用 Mie 查表（v0.4.1+）
    # 經驗公式已移除（TASK-013 Phase 7, 2025-12-24）
    #
    # 若查表載入失敗，應顯式報錯（不回退到低精度經驗公式）
    # 解決方式：確認 data/mie_lookup_table_v3.npz 存在，或執行 scripts/generate_mie_lookup.py
    
    try:
        table = load_mie_lookup_table(wavelength_params.mie_lookup_path)
        iso = wavelength_params.iso_value
        
        # 查表獲取各波長參數
        sigma_r, kappa_r, rho_r, eta_r_raw = lookup_mie_params(
            wavelength_params.lambda_r, iso, table
        )
        sigma_g, kappa_g, rho_g, eta_g_raw = lookup_mie_params(
            wavelength_params.lambda_g, iso, table
        )
        sigma_b, kappa_b, rho_b, eta_b_raw = lookup_mie_params(
            wavelength_params.lambda_b, iso, table
        )
        
        # 歸一化能量權重（綠光為基準）
        eta_r = eta_r_raw / eta_g_raw * bloom_params.scattering_ratio
        eta_g = bloom_params.scattering_ratio
        eta_b = eta_b_raw / eta_g_raw * bloom_params.scattering_ratio
        
    except FileNotFoundError as e:
        # Mie 查表載入失敗 → 顯式報錯（不回退到經驗公式）
        raise FileNotFoundError(
            f"Mie 散射查表載入失敗: {wavelength_params.mie_lookup_path}\n"
            f"原因: {e}\n"
            f"解決方式:\n"
            f"  1. 確認檔案存在: data/mie_lookup_table_v3.npz\n"
            f"  2. 或執行: python scripts/generate_mie_lookup.py\n"
            f"註: 經驗公式已移除（v0.4.2+），Mie 查表為唯一方法"
        ) from e
    
    # 5. 創建各通道的雙段核 PSF
    # PSF 半徑基於最大 sigma（通常是藍光）
    psf_radius = int(max(sigma_r, sigma_g, sigma_b) * 4)  # 4σ 覆蓋 99.99% 能量
    
    psf_r = create_dual_kernel_psf(sigma_r, kappa_r, rho_r, radius=psf_radius)
    psf_g = create_dual_kernel_psf(sigma_g, kappa_g, rho_g, radius=psf_radius)
    psf_b = create_dual_kernel_psf(sigma_b, kappa_b, rho_b, radius=psf_radius)
    
    # 6. 能量守恆散射（每通道獨立）
    threshold = bloom_params.threshold
    
    bloom_r = apply_bloom_with_psf(response_r, eta_r, psf_r, threshold)
    bloom_g = apply_bloom_with_psf(response_g, eta_g, psf_g, threshold)
    bloom_b = apply_bloom_with_psf(response_b, eta_b, psf_b, threshold)
    
    return bloom_r, bloom_g, bloom_b


# ==================== Phase 5: Mie 散射查表 ====================

# 全域快取（避免重複載入）
_MIE_LOOKUP_TABLE_CACHE = None

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


# ==================== 效能優化：FFT 卷積 ====================

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


from functools import lru_cache

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


def apply_bloom_mie_corrected(
    lux: np.ndarray,
    bloom_params: BloomParams,
    wavelength: float = 550.0
) -> np.ndarray:
    """
    應用 Mie 散射修正的 Bloom 效果（Decision #014: Phase 1 修正）
    
    物理機制：
        1. 乳劑內銀鹽晶體的 Mie 散射（d ≈ λ，非 Rayleigh）
        2. 能量權重 η(λ) ∝ λ^-3.5（非 Rayleigh 的 λ^-4）
        3. PSF 寬度 σ(λ) ∝ (λ_ref/λ)^0.8（小角前向散射）
        4. 雙段 PSF：核心（高斯）+ 尾部（指數）
        5. 能量守恆：∑E_out = ∑E_in（誤差 < 0.01%）
    
    與 apply_bloom_conserved 的差異：
        - 舊版：單一能量比例，單一 PSF 寬度
        - 新版：波長依賴能量（η(λ)）與 PSF 寬度（σ(λ)）解耦
        - 新版：雙段 PSF（核心 + 尾部）更符合 Mie 散射角度分布
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        bloom_params: BloomParams 對象（需包含 Mie 參數）
        wavelength: 當前通道的波長（nm），用於計算波長依賴參數
        
    Returns:
        應用 Bloom 後的光度數據（能量守恆）
        
    Reference:
        - Decision #014: context/decisions_log.md
        - Phase 1 Design Corrected: tasks/TASK-003-medium-physics/phase1_design_corrected.md
        - Physicist Review: tasks/TASK-003-medium-physics/physicist_review.md (Line 41-59)
    """
    if bloom_params.mode != "mie_corrected":
        # 回退到統一介面
        return apply_bloom(lux, bloom_params)
    
    # === 1. 計算波長依賴的能量分數 η(λ) ===
    λ_ref = bloom_params.reference_wavelength
    λ = wavelength
    p = bloom_params.energy_wavelength_exponent
    
    # η(λ) = η_base × (λ_ref / λ)^p
    η_λ = bloom_params.base_scattering_ratio * (λ_ref / λ) ** p
    
    # === 2. 計算波長依賴的 PSF 參數 ===
    q_core = bloom_params.psf_width_exponent
    q_tail = bloom_params.psf_tail_exponent
    
    # σ(λ) = σ_base × (λ_ref / λ)^q_core
    # κ(λ) = κ_base × (λ_ref / λ)^q_tail
    σ_core = bloom_params.base_sigma_core * (λ_ref / λ) ** q_core
    κ_tail = bloom_params.base_kappa_tail * (λ_ref / λ) ** q_tail
    
    # === 3. 確定核心/尾部能量分配 ρ(λ) ===
    if wavelength <= 450:
        ρ = bloom_params.psf_core_ratio_b
    elif wavelength >= 650:
        ρ = bloom_params.psf_core_ratio_r
    else:
        # 線性插值
        if wavelength < 550:
            # 450-550: 藍→綠
            t = (wavelength - 450) / (550 - 450)
            ρ = (1 - t) * bloom_params.psf_core_ratio_b + t * bloom_params.psf_core_ratio_g
        else:
            # 550-650: 綠→紅
            t = (wavelength - 550) / (650 - 550)
            ρ = (1 - t) * bloom_params.psf_core_ratio_g + t * bloom_params.psf_core_ratio_r
    
    # === 4. 提取高光區域 ===
    highlights = np.maximum(lux - bloom_params.threshold, 0)
    scattered_energy = highlights * η_λ
    
    # === 5. 應用雙段 PSF ===
    if bloom_params.psf_dual_segment:
        # 核心（高斯，小角散射）
        ksize_core = int(σ_core * 6) | 1  # 6σ 覆蓋 99.7%
        kernel_core = get_gaussian_kernel(σ_core, ksize_core)
        core_component = convolve_adaptive(scattered_energy, kernel_core, method='spatial')
        
        # 尾部（指數近似：三層高斯）
        ksize_tail = int(κ_tail * 5) | 1  # 5κ 覆蓋指數拖尾主要區域
        kernel_tail = get_exponential_kernel_approximation(κ_tail, ksize_tail)
        tail_component = convolve_adaptive(scattered_energy, kernel_tail, method='fft')
        
        # 加權組合
        bloom_layer = ρ * core_component + (1 - ρ) * tail_component
    else:
        # 單段高斯（向後相容）
        ksize = int(σ_core * 6) | 1
        kernel = get_gaussian_kernel(σ_core, ksize)
        bloom_layer = convolve_adaptive(scattered_energy, kernel, method='auto')
    
    # === 6. 能量守恆正規化 ===
    if bloom_params.energy_conservation:
        total_in = np.sum(scattered_energy)
        total_out = np.sum(bloom_layer)
        if total_out > 1e-6:
            bloom_layer = bloom_layer * (total_in / total_out)
    
    # === 7. 能量重分配 ===
    result = lux - scattered_energy + bloom_layer
    
    # === 8. 驗證能量守恆（調試用） ===
    if bloom_params.energy_conservation:
        energy_in = np.sum(lux)
        energy_out = np.sum(result)
        relative_error = abs(energy_in - energy_out) / (energy_in + 1e-6)
        if relative_error > 0.01:  # 誤差 > 1%
            import warnings
            warnings.warn(
                f"Mie Bloom 能量守恆誤差: {relative_error * 100:.3f}% "
                f"(λ={wavelength:.0f}nm, η={η_λ:.4f}, σ={σ_core:.1f}px)"
            )
    
    return np.clip(result, 0, 1)


def apply_halation(lux: np.ndarray, halation_params, wavelength: float = 550.0) -> np.ndarray:
    """
    應用 Halation（背層反射）效果 - Beer-Lambert 一致版（P0-2 重構, P1-4 標準化）
    
    物理機制：
    1. 光穿透乳劑層與片基
    2. 通過/被 Anti-Halation 層吸收
    3. 到達背板反射
    4. 往返路徑產生大範圍光暈
    
    遵循 Beer-Lambert 定律（雙程往返）：
    - 單程透過率：T(λ) = exp(-α(λ)·L)
    - 雙程有效分數：f_h(λ) = [T_e(λ) · T_b(λ) · T_AH(λ)]² · R_bp
    
    計算流程：
    1. 根據 wavelength 插值計算 f_h(λ)（使用 effective_halation_r/g/b）
    2. 提取高光（threshold=0.5）
    3. 計算散射能量：E_scatter = highlights × f_h × energy_fraction
    4. 應用長尾 PSF（指數/Lorentzian/高斯）
    5. 能量守恆正規化
    6. 返回：lux - E_scatter + PSF(E_scatter)
    
    與 Bloom 的區別：
    - Bloom: 短距離（20-30 px），高斯核，乳劑內散射
    - Halation: 長距離（100-200 px），指數拖尾，背層反射
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        halation_params: HalationParams 對象（含單程透過率參數）
        wavelength: 當前通道的波長（nm），用於波長依賴插值
            - 450nm: 藍光（使用 effective_halation_b）
            - 550nm: 綠光（使用 effective_halation_g）
            - 650nm: 紅光（使用 effective_halation_r）
            - 其他：線性插值
        
    Returns:
        應用 Halation 後的光度數據（能量守恆，誤差 < 0.05%）
    
    能量守恆驗證：
        見 tests/test_p0_2_halation_beer_lambert.py:
        - test_halation_energy_conservation_global
        - test_halation_energy_conservation_local_window
    
    真實案例驗證：
        - CineStill 800T: f_h,red ≈ 0.24 → 強烈紅暈
        - Portra 400: f_h,red ≈ 0.022 → 幾乎無暈
        見 test_cinestill_vs_portra_red_halo_ratio
    
    Note:
        energy_fraction 為藝術縮放參數，與物理 f_h(λ) 分離，
        用於控制視覺效果強度（典型值 0.02-0.10）。
    """
    if not halation_params.enabled:
        return lux
    
    # 1. 根據波長計算雙程有效 Halation 分數
    # 使用線性插值於 450nm（藍）、550nm（綠）、650nm（紅）三點
    if wavelength <= 450:
        f_h = halation_params.effective_halation_b
    elif wavelength >= 650:
        f_h = halation_params.effective_halation_r
    else:
        # 450-650nm 線性插值
        if wavelength < 550:
            # 450-550: 藍→綠
            t = (wavelength - 450) / (550 - 450)
            f_h = (1 - t) * halation_params.effective_halation_b + \
                  t * halation_params.effective_halation_g
        else:
            # 550-650: 綠→紅
            t = (wavelength - 550) / (650 - 550)
            f_h = (1 - t) * halation_params.effective_halation_g + \
                  t * halation_params.effective_halation_r
    
    # 2. 提取會產生 Halation 的高光（閾值：0.5，較 Bloom 低）
    halation_threshold = 0.5
    highlights = np.maximum(lux - halation_threshold, 0)
    
    # 3. 應用雙程 Beer-Lambert 分數 + 藝術縮放
    halation_energy = highlights * f_h * halation_params.energy_fraction
    
    # 【效能優化】強制轉換為 float32（film_models 的參數是 np.float64，會導致 GaussianBlur 慢 3 倍）
    halation_energy = halation_energy.astype(np.float32, copy=False)
    
    # 4. 應用長尾 PSF
    ksize = halation_params.psf_radius
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    
    if halation_params.psf_type == "exponential":
        # 指數拖尾：使用多尺度高斯近似
        # PSF(r) ≈ exp(-k·r)，用三層高斯疊加近似
        sigma_base = halation_params.psf_radius * 0.2
        
        # ===== 效能優化：最佳核大小策略 =====
        # 實測結果（2000×3000 影像）：
        #   - 33px: GaussianBlur 132ms（最佳）
        #   - 101px: GaussianBlur 429ms（可接受）
        #   - 151px: GaussianBlur 596ms（臨界）
        #   - 241px: GaussianBlur 2000ms+（過慢）
        # 結論：控制在 33-151px 範圍內
        
        sigma_small = sigma_base          # 20
        sigma_medium = sigma_base * 2.0   # 40
        sigma_large = sigma_base * 4.0    # 80
        
        # 限制核大小在效能甜蜜點
        ksize_small = 61    # 對 σ=20，3σ覆蓋 99.7%
        ksize_medium = 121  # 對 σ=40，3σ覆蓋 99.7%
        ksize_large = 151   # 對 σ=80，不足 3σ 但平衡效能（原本需 481px）
        
        halation_layer = (
            cv2.GaussianBlur(halation_energy, (ksize_small, ksize_small), sigma_small) * 0.5 +
            cv2.GaussianBlur(halation_energy, (ksize_medium, ksize_medium), sigma_medium) * 0.3 +
            cv2.GaussianBlur(halation_energy, (ksize_large, ksize_large), sigma_large) * 0.2
        )
    elif halation_params.psf_type == "lorentzian":
        # Lorentzian（Cauchy）拖尾：更長的尾部
        # 近似：使用極大 sigma 的高斯
        sigma_long = halation_params.psf_radius * 0.3
        kernel = get_gaussian_kernel(sigma_long, ksize)
        halation_layer = convolve_adaptive(halation_energy, kernel, method='fft')
    else:
        # 預設：高斯（較短拖尾）
        sigma = halation_params.psf_radius * 0.15
        kernel = get_gaussian_kernel(sigma, ksize)
        halation_layer = convolve_adaptive(halation_energy, kernel, method='auto')
    
    # 5. 能量守恆正規化
    total_energy_in = np.sum(halation_energy)
    total_energy_out = np.sum(halation_layer)
    if total_energy_out > 1e-6:
        halation_layer = halation_layer * (total_energy_in / total_energy_out)
    
    # 6. 從原圖減去被反射的能量，加上散射後的光暈
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
            result = apply_bloom(response, bloom_params)
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
    # 標準化：以中性曝光量（exposure=1.0, log=0）為參考點
    # 基線密度：使用 D_min + 動態範圍的 1/3（避免過度偏移）
    D_baseline = hd_params.D_min + (hd_params.D_max - hd_params.D_min) * 0.33
    density = hd_params.gamma * log_exposure + D_baseline
    
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
    組合散射光、直射光和顆粒效果（能量守恆版本）
    
    物理原理：
    - 散射光（bloom）與直射光（lux）應該滿足能量守恆
    - 總權重歸一化：w_diffuse + w_direct = 1.0
    - 顆粒作為噪聲疊加（不參與能量守恆）
    
    Args:
        bloom: 光暈效果（散射光）
        lux: 原始光度數據（直射光）
        layer: 感光層參數
        grain_r, grain_g, grain_b: RGB 顆粒噪聲
        grain_total: 全色顆粒強度
        use_grain: 是否使用顆粒
        
    Returns:
        組合後的光度數據
    """
    # 歸一化權重（確保能量守恆）
    total_weight = layer.diffuse_weight + layer.direct_weight
    if total_weight > 1e-6:
        w_diffuse = layer.diffuse_weight / total_weight
        w_direct = layer.direct_weight / total_weight
    else:
        # 邊界情況：兩個權重都為 0
        w_diffuse = 0.5
        w_direct = 0.5
    
    # 散射光 + 直射光（非線性響應）
    # 注意：歸一化後確保 w_diffuse + w_direct = 1.0
    result = bloom * w_diffuse + np.power(lux, layer.response_curve) * w_direct
    
    # 添加顆粒（作為加性噪聲，不參與能量守恆）
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
                      film: FilmProfile, grain_style: str, tone_style: str,
                      use_film_spectra: bool = False, film_spectra_name: str = 'Portra400',
                      exposure_time: float = 1.0) -> np.ndarray:
    """
    光學處理主函數
    
    這是整個胶片模擬的核心，包含：
    0. (可選) 應用互易律失效 (Reciprocity Failure)
    1. 計算自適應參數
    2. 應用光暈效果（Halation/Bloom）
    3. 應用顆粒效果
    4. 組合散射光和直射光
    5. Tone mapping
    6. 合成最終圖像
    7. (可選) 應用膠片光譜敏感度 (Phase 4.5)
    
    Args:
        response_r, response_g, response_b: RGB 通道的光度數據
        response_total: 全色通道的光度數據
        film: 胶片配置對象
        grain_style: 顆粒風格
        tone_style: Tone mapping 風格
        use_film_spectra: 是否使用膠片光譜敏感度（預設 False，保持向後相容）
        film_spectra_name: 膠片光譜名稱 ('Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400')
        exposure_time: 曝光時間（秒），用於互易律失效計算（預設 1.0s，即無效應）
        
    Returns:
        處理後的圖像 (0-255 uint8)
    """
    # 0. 應用互易律失效（Reciprocity Failure, TASK-014）
    # 在所有其他處理之前應用，模擬長曝光時的膠片非線性響應
    if (hasattr(film, 'reciprocity_params') and 
        film.reciprocity_params is not None and 
        film.reciprocity_params.enabled and 
        exposure_time != 1.0):
        try:
            from reciprocity_failure import apply_reciprocity_failure
            
            # 對彩色膠片應用通道獨立的互易律失效
            if film.color_type == "color" and all([response_r is not None, response_g is not None, response_b is not None]):
                # 組合 RGB 通道為 3D 陣列
                rgb_stack = np.stack([response_r, response_g, response_b], axis=2)
                rgb_stack = apply_reciprocity_failure(rgb_stack, exposure_time, film.reciprocity_params)
                response_r = rgb_stack[:, :, 0]
                response_g = rgb_stack[:, :, 1]
                response_b = rgb_stack[:, :, 2]
            else:
                # 對黑白膠片應用單一通道互易律失效
                response_total = apply_reciprocity_failure(
                    response_total[:, :, np.newaxis],  # 轉為 3D
                    exposure_time,
                    film.reciprocity_params
                )[:, :, 0]  # 轉回 2D
        except ImportError:
            import warnings
            warnings.warn("reciprocity_failure 模組未找到，跳過互易律失效處理")
        except Exception as e:
            import warnings
            warnings.warn(f"互易律失效處理失敗，跳過: {str(e)}")
    
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
        
        # 檢查是否啟用波長依賴 Bloom（Phase 1）
        use_wavelength_bloom = (use_medium_physics and 
                               hasattr(film, 'wavelength_bloom_params') and 
                               film.wavelength_bloom_params is not None and
                               film.wavelength_bloom_params.enabled)
        
        if use_wavelength_bloom:
            # Phase 1: 波長依賴 Bloom + Halation（TASK-003 Phase 1+2）
            # 步驟 1: 波長依賴 Bloom 散射（η(λ) 與 σ(λ) 解耦）
            bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(
                response_r, response_g, response_b,
                film.wavelength_bloom_params,
                film.bloom_params
            )
            
            # 步驟 2: Halation 背層反射（波長依賴）
            bloom_r = apply_halation(bloom_r, film.halation_params, wavelength=650.0)
            bloom_g = apply_halation(bloom_g, film.halation_params, wavelength=550.0)
            bloom_b = apply_halation(bloom_b, film.halation_params, wavelength=450.0)
            
        elif use_medium_physics:
            # Phase 2: 僅 Bloom + Halation 分離（無波長依賴）
            bloom_r, bloom_g, bloom_b = apply_optical_effects_separated(
                response_r, response_g, response_b,
                film.bloom_params, film.halation_params,
                blur_scale_r=3, blur_scale_g=2, blur_scale_b=1
            )
        elif use_physical_bloom:
            # 物理模式：僅 Bloom（能量守恆）
            bloom_r = apply_bloom(response_r, film.bloom_params)
            bloom_g = apply_bloom(response_g, film.bloom_params)
            bloom_b = apply_bloom(response_b, film.bloom_params)
        else:
            # 藝術模式：現有行為
            artistic_params = BloomParams(
                mode="artistic",
                sensitivity=sens,
                radius=rads,
                artistic_strength=strg,
                artistic_base=base
            )
            bloom_r = apply_bloom(response_r, artistic_params)
            bloom_g = apply_bloom(response_g, artistic_params)
            bloom_b = apply_bloom(response_b, artistic_params)
        
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
        
        # 4.5. 應用膠片光譜敏感度（Phase 4，優化版）
        if use_film_spectra:
            try:
                from phos_core import (
                    rgb_to_spectrum, 
                    apply_film_spectral_sensitivity,
                    load_film_sensitivity
                )
                
                # 合併 RGB 為影像陣列（0-1 範圍）
                lux_combined = np.stack([result_r, result_g, result_b], axis=2)
                
                # RGB → Spectrum → Film RGB (optimized pipeline)
                spectrum = rgb_to_spectrum(lux_combined, use_tiling=True, tile_size=512)
                film_curves = load_film_sensitivity(film_spectra_name)
                rgb_with_film = apply_film_spectral_sensitivity(
                    spectrum, 
                    film_curves,
                    normalize=True
                )
                
                # 拆分回通道
                result_r = rgb_with_film[:, :, 0]
                result_g = rgb_with_film[:, :, 1]
                result_b = rgb_with_film[:, :, 2]
                
            except Exception as e:
                # 膠片光譜處理失敗時回退到原始結果
                import warnings
                warnings.warn(f"膠片光譜處理失敗，使用原始結果: {str(e)}")
        
        # 5. 合成最終圖像
        combined_r = (result_r * 255).astype(np.uint8)
        combined_g = (result_g * 255).astype(np.uint8)
        combined_b = (result_b * 255).astype(np.uint8)
        final_image = cv2.merge([combined_b, combined_g, combined_r])
        
    else:
        # 黑白胶片：僅處理全色通道
        artistic_params = BloomParams(
            mode="artistic",
            sensitivity=sens,
            radius=rads,
            artistic_strength=strg,
            artistic_base=base
        )
        bloom = apply_bloom(response_total, artistic_params)
        
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
                 physics_params: Optional[dict] = None,
                 use_film_spectra: bool = False, film_spectra_name: str = 'Portra400') -> Tuple[np.ndarray, float, str]:
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
            
            # 互易律失效參數 (TASK-014)
            if 'reciprocity_enabled' in physics_params:
                film.reciprocity_params.enabled = physics_params.get('reciprocity_enabled', False)
        
        # 4. 調整顆粒強度（傳統 grain_style）
        film = adjust_grain_intensity(film, grain_style)
        
        # 5. 標準化圖像尺寸
        image = standardize(image)
        
        # 6. 計算光度響應
        response_r, response_g, response_b, response_total = spectral_response(image, film)
        
        # 7. 應用光學處理
        final_image = optical_processing(
            response_r, response_g, response_b, response_total, 
            film, grain_style, tone_style,
            use_film_spectra=use_film_spectra,
            film_spectra_name=film_spectra_name,
            exposure_time=physics_params.get('exposure_time', 1.0) if physics_params else 1.0
        )
        
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

# ==================== Streamlit 主界面 ====================

# 初始化 session state
if 'processing_mode' not in st.session_state:
    st.session_state.processing_mode = "單張處理"
if 'batch_results' not in st.session_state:
    st.session_state.batch_results = []

# 渲染側邊欄，獲取用戶參數
sidebar_params = render_sidebar()

# 提取參數
processing_mode = sidebar_params['processing_mode']
film_type = sidebar_params['film_type']
grain_style = sidebar_params['grain_style']
tone_style = sidebar_params['tone_style']
physics_mode = sidebar_params['physics_mode']
physics_params = sidebar_params['physics_params']
uploaded_image = sidebar_params['uploaded_image']
uploaded_images = sidebar_params['uploaded_images']

# 更新 session state
st.session_state.processing_mode = processing_mode

# ==================== 主區域 ====================

# 單張處理模式
if processing_mode == "單張處理" and uploaded_image is not None:
    try:
        # 處理圖像
        film_image, process_time, output_path = process_image(
            uploaded_image, film_type, grain_style, tone_style, physics_params,
            use_film_spectra=physics_params.get('use_film_spectra', False),
            film_spectra_name=physics_params.get('film_spectra_name', 'Portra400')
        )
        
        # 顯示結果
        render_single_image_result(film_image, process_time, physics_mode, output_path)
        
    except ValueError as e:
        st.error(f"❌ 錯誤: {str(e)}")
    except Exception as e:
        st.error(f"❌ 未預期的錯誤: {str(e)}")
        st.error("請嘗試重新上傳圖像或選擇其他胶片類型")

# 批量處理模式
elif processing_mode == "批量處理" and uploaded_images is not None and len(uploaded_images) > 0:
    # 準備設定
    settings = {
        'grain_style': grain_style,
        'tone_style': tone_style,
        'use_film_spectra': physics_params.get('use_film_spectra', False),
        'film_spectra_name': physics_params.get('film_spectra_name', 'Portra400'),
        'exposure_time': physics_params.get('exposure_time', 1.0)
    }
    
    # 渲染批量處理 UI
    render_batch_processing_ui(
        uploaded_images, film_type, settings,
        standardize, spectral_response, optical_processing, get_cached_film_profile
    )

# 未上傳文件時的歡迎界面
else:
    render_welcome_page()
