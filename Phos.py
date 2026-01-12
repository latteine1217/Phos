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
from functools import lru_cache, wraps

# ==================== Deprecation Decorator ====================
def deprecated(reason: str, replacement: Optional[str] = None, remove_in: Optional[str] = None):
    """
    標記函數為過時
    
    Args:
        reason: 過時原因
        replacement: 建議的替代方案
        remove_in: 預計移除版本
    
    Example:
        @deprecated(
            reason="Function refactored into bloom_strategies module",
            replacement="apply_bloom(lux, bloom_params)",
            remove_in="v0.7.0"
        )
        def old_function(): ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated. {reason}"
            if replacement:
                msg += f" Use {replacement} instead."
            if remove_in:
                msg += f" Will be removed in {remove_in}."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator

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

# 導入顆粒生成策略（P1-2: Strategy Pattern）
from grain_strategies import generate_grain

# ==================== PR #2-#6: 模組化導入（v0.7.0）====================
# 
# ⚠️ DEPRECATION NOTICE (v0.7.1):
# 從 Phos.py 直接導入模組化函數已標記為棄用，將在 v0.8.0 移除
# 
# 遷移指南：
#   舊方式（v0.7.1 棄用，v0.8.0 移除）:
#     from Phos import apply_hd_curve, standardize
#   
#   新方式（推薦）:
#     from modules.image_processing import apply_hd_curve
#     from modules.optical_core import standardize
#   
#   或使用統一導入:
#     from modules import apply_hd_curve, standardize
#
# 完整遷移清單請參閱: MIGRATION_GUIDE_v08.md

# PR #2: optical_core (3 functions)
# DEPRECATED: Use 'from modules.optical_core import ...'
from modules.optical_core import (
    standardize,
    spectral_response,
    average_response
)

# PR #3: tone_mapping (4 functions)
# DEPRECATED: Use 'from modules.tone_mapping import ...'
from modules.tone_mapping import (
    apply_reinhard_to_channel,
    apply_reinhard,
    apply_filmic_to_channel,
    apply_filmic
)

# PR #4: psf_utils (7 functions)
# DEPRECATED: Use 'from modules.psf_utils import ...'
from modules.psf_utils import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    convolve_fft,
    convolve_adaptive,
    get_gaussian_kernel,
    get_exponential_kernel_approximation
)

# PR #5: wavelength_effects (4 functions)
# DEPRECATED: Use 'from modules.wavelength_effects import ...'
from modules.wavelength_effects import (
    apply_bloom_with_psf,
    apply_wavelength_bloom,
    apply_halation,
    apply_optical_effects_separated
)

# PR #6: image_processing (2 functions)
# DEPRECATED: Use 'from modules.image_processing import ...'
from modules.image_processing import (
    apply_hd_curve,
    combine_layers_for_channel
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


# ==================== 圖像預處理 & 光度計算 ====================
# PR #2: 已移至 modules/optical_core.py
# - standardize()
# - spectral_response()
# - average_response()


# ==================== 胶片顆粒效果 ====================

# ==================== Grain Generation ====================
# 注意：generate_grain() 已移至 grain_strategies.py（P1-2: Strategy Pattern）
# 原函數 110 行 → 策略模式：2 個策略類各 <50 行
# apply_grain(): 主要的 grain 生成介面，支持 artistic/poisson 模式
# 內部調用 generate_grain() 處理單通道顆粒生成





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
# PR #3: 已移至 modules/tone_mapping.py
# - apply_reinhard_to_channel()
# - apply_reinhard()
# - apply_filmic_to_channel()
# - apply_filmic()


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


# ==================== Legacy Medium Physics Path ====================
# 注意：以下函數用於 legacy medium physics 模式（wavelength-dependent bloom）
# 新代碼建議使用 apply_bloom() 統一介面（from bloom_strategies）
# 保留原因：向後相容性，現有配置文件可能依賴此路徑




# ==================== Wavelength-Dependent Optical Effects ====================
# PR #5: Moved to modules/wavelength_effects.py
# - apply_bloom_with_psf()
# - apply_wavelength_bloom()
# - apply_halation()
# - apply_optical_effects_separated()


# ==================== Phase 5: Mie 散射查表 ====================
# PR #4: 以下函數已移至 modules/psf_utils.py
# - load_mie_lookup_table()
# - lookup_mie_params()
# - convolve_fft()
# - convolve_adaptive()
# - _get_gaussian_kernel_cached()
# - get_gaussian_kernel()
# - get_exponential_kernel_approximation()


@deprecated(
    reason="This function has been refactored into bloom_strategies.MieCorrectedBloomStrategy",
    replacement="apply_bloom(lux, bloom_params) with mode='mie_corrected'",
    remove_in="v0.7.0"
)
def apply_bloom_mie_corrected(
    lux: np.ndarray,
    bloom_params: BloomParams,
    wavelength: float = 550.0
) -> np.ndarray:
    """
    應用 Mie 散射修正的 Bloom 效果（Decision #014: Phase 1 修正）
    
    **DEPRECATED**: This function will be removed in v0.7.0.
    Use apply_bloom(lux, bloom_params) with mode='mie_corrected' instead.
    The functionality has been refactored into bloom_strategies.MieCorrectedBloomStrategy.
    
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


# Functions moved to modules/wavelength_effects.py (see above comment block)


# ==================== PR #6: 圖像處理函數 ====================
# 以下函數已移至 modules/image_processing.py（保持向後相容）
# - apply_hd_curve()           (lines 467-551 → modules/image_processing.py)
# - combine_layers_for_channel() (lines 554-607 → modules/image_processing.py)


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
        
        # ============ Bloom Processing: Multiple Execution Paths ============
        if use_wavelength_bloom:
            # ============ Path 1: Legacy Medium Physics ============
            # Uses wavelength-dependent bloom (TASK-003 Phase 1+2)
            # Functions: apply_wavelength_bloom() + apply_bloom_with_psf()
            # Note: Kept for backward compatibility with existing configs
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
            # ============ Path 2: Legacy Medium Physics (Separated) ============
            # Phase 2: 僅 Bloom + Halation 分離（無波長依賴）
            bloom_r, bloom_g, bloom_b = apply_optical_effects_separated(
                response_r, response_g, response_b,
                film.bloom_params, film.halation_params,
                blur_scale_r=3, blur_scale_g=2, blur_scale_b=1
            )
        elif use_physical_bloom:
            # ============ Path 3: New Physical Mode (Strategy Pattern) ============
            # Uses strategy pattern (bloom_strategies.py)
            # Recommended for new code
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
