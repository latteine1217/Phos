"""
波長依賴光學效果模組

負責：
1. 波長依賴的 Bloom 散射（Mie 散射修正）
2. Halation（背層反射）效果
3. 分離應用 Bloom + Halation 的完整光學鏈

物理背景：
- Bloom: 乳劑內銀鹽顆粒的 Mie 散射，波長依賴（藍光散射強）
- Halation: 光穿透片基、背板反射、產生長距離光暈
- 波長色散: λ↓ → 散射↑（藍光暈 > 紅光暈）

PR #5: Extracted from Phos.py (Lines 307-344, 347-428, 570-717, 720-781)
"""

import numpy as np
import cv2
from typing import Optional, Tuple

# Import dependencies from other modules
from modules.psf_utils import (
    create_dual_kernel_psf,
    load_mie_lookup_table,
    lookup_mie_params,
    get_gaussian_kernel,
    convolve_adaptive
)

# Import from main Phos module (bloom_strategies)
# Note: This creates a dependency on Phos.py for apply_bloom
# Alternative: Could move apply_bloom import inside function to avoid circular import


# ==================== Bloom with PSF ====================

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


# ==================== Wavelength-Dependent Bloom ====================

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


# ==================== Halation ====================

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
    halation_threshold = 0.5  # 高光閾值（0-1 歸一化亮度）
    # 來源: 經驗參數（Beer-Lambert halation 專用）
    # 理由: Halation 閾值應低於 Bloom 閾值（典型 0.7-0.8）
    #   - Halation: 背板反射，擴散範圍廣（50-150px）
    #   - Bloom: 乳劑散射，擴散範圍小（15-40px）
    # 物理意義: 
    #   - 閾值 0.5 對應曝光值 EV ~+2（中灰 18% → 50% 亮度）
    #   - 只有「明顯過曝」區域才產生背板反射
    # 實驗: 測試 0.3-0.7 範圍，0.5 為視覺平衡點
    #   - <0.4: Halation 過度（全圖都有光暈）
    #   - >0.6: Halation 不足（只有極端高光有效果）
    # 備註: Bloom 閾值通常為 0.7-0.8（見 BloomParams.threshold）
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


# ==================== Combined Optical Effects ====================

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
        blur_scale_r/g/b: 各通道模糊倍數（波長依賴，預設 3:2:1）
            來源: Rayleigh-Mie 散射理論簡化（粗略近似）
            理由: 散射強度 ∝ λ^-p（p ~3-4），藍光散射 > 紅光
            物理依據:
                - 紅光（λ=650nm）: scale=3（最長波長，最少散射）
                - 綠光（λ=550nm）: scale=2（中等）
                - 藍光（λ=450nm）: scale=1（最短波長，最多散射）
            簡化假設: 線性比例（實際應為指數關係，由 Mie 模式處理）
            精確模式: 使用 apply_wavelength_bloom() 替代（查表 Mie 參數）
            備註: 此參數僅用於「中等物理模式」(medium_physics)，
                  完整物理模式使用 Mie 查表獲得精確散射係數
        
    Returns:
        (bloom_r, bloom_g, bloom_b): 應用光學效果後的通道
    """
    # Import here to avoid circular dependency
    from bloom_strategies import apply_bloom
    
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


# ==================== Exports ====================

__all__ = [
    'apply_bloom_with_psf',
    'apply_wavelength_bloom',
    'apply_halation',
    'apply_optical_effects_separated',
]
