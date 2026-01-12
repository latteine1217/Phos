"""
圖像處理模組

包含 H&D 曲線、層組合等圖像處理函數。

Functions:
    - apply_hd_curve: 應用 H&D 特性曲線
    - combine_layers_for_channel: 組合散射光與直射光

Physics Foundation:
    - H&D Curve (Hurter-Driffield Characteristic Curve): 膠片特性曲線
        描述曝光量 (H) 與光學密度 (D) 的關係
        D = gamma · log10(H) + D_fog
        
        三個關鍵區段：
        1. Toe（趾部）：低曝光量（陰影），響應壓縮
        2. Linear（線性區）：中間曝光量，對數線性響應
        3. Shoulder（肩部）：高曝光量（高光），響應飽和
        
        膠片類型差異：
        - 負片：gamma ≈ 0.6-0.7（低對比度，留後製空間）
        - 正片：gamma ≈ 1.5-2.0（高對比度，直接觀看）
    
    - Layer Combination: 層組合能量守恆
        散射光（bloom）+ 直射光（lux）= 總光度
        權重歸一化：w_diffuse + w_direct = 1.0
        顆粒作為加性噪聲疊加（不參與能量守恆）

References:
    - Hurter, F., & Driffield, V. C. (1890). "Photochemical Investigations".
      Journal of the Society of Chemical Industry, 9, 455-469.
    - Todd & Zakia (1974). Photographic Sensitometry. Morgan & Morgan.
    - Hunt, R. W. G. (2004). The Reproduction of Colour, 6th ed., Ch. 12.

Version: 0.7.0-dev
Date: 2026-01-12
Status: PR #1 - Empty template (implementation in PR #6)

Note:
    此為 PR #1 空模板，實際函數將在 PR #6 從 Phos.py 搬移。
"""

import numpy as np
from typing import Optional

# 導入 film_models 中的類型
import film_models
from film_models import EmulsionLayer


# ==================== PR #6: H&D Curve ====================

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
    - 基準密度由 use_visual_baseline 控制（視覺/物理模式）
    
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
    # 基線密度：提供視覺/物理兩種基準（向後相容）
    use_visual_baseline = getattr(hd_params, "use_visual_baseline", True)
    if use_visual_baseline:
        # 視覺基準：置中密度，適合藝術模式
        D_baseline = hd_params.D_min + (hd_params.D_max - hd_params.D_min) * 0.33
    else:
        # 物理基準：使用 D_min/D_fog
        D_baseline = hd_params.D_min
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


# ==================== PR #6: Layer Combination ====================

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
        # 邊界情況：兩個權重都為 0（防止除以零）
        w_diffuse = 0.5  # 均分權重（50% 散射光）
        w_direct = 0.5   # 均分權重（50% 直射光）
        # 來源: 技術安全參數（邊界條件處理）
        # 理由: 當 diffuse_weight = direct_weight = 0 時：
        #   - 實際情況: 不應發生（FilmProfile 驗證應捕捉此錯誤）
        #   - 安全處理: 均分權重避免除以零，保證 w_diffuse + w_direct = 1.0
        # 物理意義: 無明確物理意義（純防禦性編程）
        # 備註: 正常 FilmProfile 的 diffuse_weight 範圍 [0.3, 0.7]
    
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


# ==================== PR #6: 版本信息 ====================

__all__ = [
    'apply_hd_curve',
    'combine_layers_for_channel',
]
