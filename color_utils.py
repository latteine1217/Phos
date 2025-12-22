"""
色彩科學工具模組 (Phase 4: 光譜模型)

功能：
1. RGB ↔ Spectrum 轉換（Smits 1999 算法）
2. Spectrum ↔ XYZ 轉換（CIE 1931）
3. XYZ ↔ RGB 轉換（sRGB/AdobeRGB）
4. 光譜積分運算

Version: 0.4.0
Author: Phos Development Team
Date: 2025-12-20
"""

import numpy as np
from typing import Tuple, Optional, Dict
from functools import lru_cache


# ============================================================
# 1. 常數定義
# ============================================================

# 波長範圍（380-780nm，每 13nm，共 31 個波長點）
WAVELENGTHS = np.arange(380, 781, 13, dtype=np.float32)  # (31,)
N_WAVELENGTHS = len(WAVELENGTHS)  # 31
DELTA_LAMBDA = 13.0  # nm

# CIE 1931 色彩匹配函數（在 WAVELENGTHS 位置的值）
# 來源：CIE 15:2004, 插值到 31 個波長點
# 將從 data/cie_1931_31points.npz 載入精確值（Phase 4.3 完成）
# 暫時使用簡化版作為預設值（防止載入失敗）
CIE_X_BAR = np.array([
    0.0014, 0.0042, 0.0143, 0.0435, 0.1344, 0.2839, 0.3483, 0.3362, 0.2908, 0.1954, 0.0956,
    0.0320, 0.0049, 0.0093, 0.0633, 0.1655, 0.2904, 0.4334, 0.5945, 0.7621, 0.9163,
    1.0263, 1.0622, 1.0026, 0.8544, 0.6424, 0.4479, 0.2835, 0.1649, 0.0874, 0.0468
], dtype=np.float32)

CIE_Y_BAR = np.array([
    0.0000, 0.0001, 0.0004, 0.0012, 0.0040, 0.0116, 0.0230, 0.0380, 0.0600, 0.0910, 0.1390,
    0.2080, 0.3230, 0.5030, 0.7100, 0.8620, 0.9540, 0.9950, 0.9950, 0.9520, 0.8700,
    0.7570, 0.6310, 0.5030, 0.3810, 0.2650, 0.1750, 0.1070, 0.0610, 0.0320, 0.0170
], dtype=np.float32)

CIE_Z_BAR = np.array([
    0.0065, 0.0201, 0.0679, 0.2074, 0.6456, 1.3856, 1.7471, 1.7721, 1.6692, 1.2876, 0.8130,
    0.4652, 0.2720, 0.1582, 0.0782, 0.0422, 0.0203, 0.0087, 0.0039, 0.0021, 0.0017,
    0.0011, 0.0008, 0.0003, 0.0002, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000
], dtype=np.float32)

_CIE_DATA_LOADED = False

# Smits (1999) 基底光譜（7 個基底）
# 從 data/smits_basis_spectra.npz 載入
BASIS_SPECTRA: Dict[str, np.ndarray] = {}
_BASIS_SPECTRA_LOADED = False

# 膠片光譜敏感度曲線（4 款膠片）
# 從 data/film_spectral_sensitivity.npz 載入
FILM_SPECTRA: Dict[str, Dict[str, np.ndarray]] = {}
_FILM_SPECTRA_LOADED = False


# sRGB 轉換矩陣（XYZ → RGB）
# 來源：IEC 61966-2-1:1999
XYZ_TO_SRGB_MATRIX = np.array([
    [ 3.2406, -1.5372, -0.4986],
    [-0.9689,  1.8758,  0.0415],
    [ 0.0557, -0.2040,  1.0570]
], dtype=np.float32)

# sRGB 逆矩陣（RGB → XYZ）
SRGB_TO_XYZ_MATRIX = np.linalg.inv(XYZ_TO_SRGB_MATRIX)


# ============================================================
# 2. 初始化函數
# ============================================================

def _load_cie_data():
    """
    從 NPZ 檔案載入精確 CIE 1931 色彩匹配函數
    
    載入來源：data/cie_1931_31points.npz
    
    內容：
    - x_bar, y_bar, z_bar (各 31 個波長點)
    - wavelengths (31,)
    
    注意：
    - 使用快取機制（僅載入一次）
    - 失敗時回退到簡化版
    """
    global CIE_X_BAR, CIE_Y_BAR, CIE_Z_BAR, _CIE_DATA_LOADED
    
    if _CIE_DATA_LOADED:
        return  # 已載入，跳過
    
    from pathlib import Path
    
    # 嘗試載入 NPZ
    npz_path = Path(__file__).parent / "data" / "cie_1931_31points.npz"
    
    try:
        data = np.load(npz_path)
        
        # 載入 CIE 色彩匹配函數
        CIE_X_BAR = data['x_bar'].astype(np.float32)
        CIE_Y_BAR = data['y_bar'].astype(np.float32)
        CIE_Z_BAR = data['z_bar'].astype(np.float32)
        
        _CIE_DATA_LOADED = True
        
    except Exception as e:
        # 回退到簡化版（原始手動輸入的近似值）
        print(f"⚠️  Warning: 無法載入精確 CIE 數據 ({e})，使用簡化版")
        
        CIE_X_BAR = np.array([
            0.0014, 0.0042, 0.0143, 0.0435, 0.1344, 0.2839, 0.3483, 0.3362, 0.2908, 0.1954, 0.0956,
            0.0320, 0.0049, 0.0093, 0.0633, 0.1655, 0.2904, 0.4334, 0.5945, 0.7621, 0.9163,
            1.0263, 1.0622, 1.0026, 0.8544, 0.6424, 0.4479, 0.2835, 0.1649, 0.0874, 0.0468
        ], dtype=np.float32)
        
        CIE_Y_BAR = np.array([
            0.0000, 0.0001, 0.0004, 0.0012, 0.0040, 0.0116, 0.0230, 0.0380, 0.0600, 0.0910, 0.1390,
            0.2080, 0.3230, 0.5030, 0.7100, 0.8620, 0.9540, 0.9950, 0.9950, 0.9520, 0.8700,
            0.7570, 0.6310, 0.5030, 0.3810, 0.2650, 0.1750, 0.1070, 0.0610, 0.0320, 0.0170
        ], dtype=np.float32)
        
        CIE_Z_BAR = np.array([
            0.0065, 0.0201, 0.0679, 0.2074, 0.6456, 1.3856, 1.7471, 1.7721, 1.6692, 1.2876, 0.8130,
            0.4652, 0.2720, 0.1582, 0.0782, 0.0422, 0.0203, 0.0087, 0.0039, 0.0021, 0.0017,
            0.0011, 0.0008, 0.0003, 0.0002, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000
        ], dtype=np.float32)
        
        _CIE_DATA_LOADED = True


def _load_basis_spectra():
    """
    從 NPZ 檔案載入 Smits (1999) 基底光譜
    
    載入來源：data/smits_basis_spectra.npz
    
    內容：
    - white, cyan, magenta, yellow, red, green, blue (各 31 個波長點)
    - wavelengths (31,)
    
    注意：
    - 使用快取機制（僅載入一次）
    - 失敗時回退到簡化版
    """
    global BASIS_SPECTRA, _BASIS_SPECTRA_LOADED
    
    if _BASIS_SPECTRA_LOADED:
        return  # 已載入，跳過
    
    from pathlib import Path
    
    # 嘗試載入 NPZ
    npz_path = Path(__file__).parent / "data" / "smits_basis_spectra.npz"
    
    try:
        data = np.load(npz_path)
        
        # 載入 7 個基底
        BASIS_SPECTRA['white'] = data['white']
        BASIS_SPECTRA['cyan'] = data['cyan']
        BASIS_SPECTRA['magenta'] = data['magenta']
        BASIS_SPECTRA['yellow'] = data['yellow']
        BASIS_SPECTRA['red'] = data['red']
        BASIS_SPECTRA['green'] = data['green']
        BASIS_SPECTRA['blue'] = data['blue']
        
        _BASIS_SPECTRA_LOADED = True
        
    except Exception as e:
        # 回退到簡化版（高斯近似）
        print(f"⚠️  Warning: 無法載入 Smits 基底光譜 ({e})，使用簡化版")
        
        # White: 平坦光譜
        BASIS_SPECTRA['white'] = np.ones(N_WAVELENGTHS, dtype=np.float32)
        
        # Red: 長波段高
        BASIS_SPECTRA['red'] = np.where(
            WAVELENGTHS > 580,
            1.0,
            np.exp(-((WAVELENGTHS - 650) ** 2) / (2 * 80 ** 2))
        ).astype(np.float32)
        
        # Green: 中波段高
        BASIS_SPECTRA['green'] = np.exp(
            -((WAVELENGTHS - 550) ** 2) / (2 * 60 ** 2)
        ).astype(np.float32)
        
        # Blue: 短波段高
        BASIS_SPECTRA['blue'] = np.where(
            WAVELENGTHS < 520,
            1.0,
            np.exp(-((WAVELENGTHS - 450) ** 2) / (2 * 70 ** 2))
        ).astype(np.float32)
        
        # 互補色
        BASIS_SPECTRA['cyan'] = 1.0 - BASIS_SPECTRA['red']
        BASIS_SPECTRA['magenta'] = 1.0 - BASIS_SPECTRA['green']
        BASIS_SPECTRA['yellow'] = 1.0 - BASIS_SPECTRA['blue']
        
        # 歸一化到 [0, 1]
        for key in BASIS_SPECTRA:
            BASIS_SPECTRA[key] = np.clip(BASIS_SPECTRA[key], 0, 1)
        
        _BASIS_SPECTRA_LOADED = True


def _load_film_spectra():
    """
    從 NPZ 檔案載入膠片光譜敏感度曲線
    
    載入來源：data/film_spectral_sensitivity.npz
    
    內容：
    - 4 款膠片（Portra400, Velvia50, Cinestill800T, HP5Plus400）
    - 每款膠片 3 個通道（red, green, blue，各 31 個波長點）
    
    注意：
    - 使用快取機制（僅載入一次）
    - 失敗時回退到均勻敏感度（全 1.0）
    """
    global FILM_SPECTRA, _FILM_SPECTRA_LOADED
    
    if _FILM_SPECTRA_LOADED:
        return  # 已載入，跳過
    
    from pathlib import Path
    
    # 嘗試載入 NPZ
    npz_path = Path(__file__).parent / "data" / "film_spectral_sensitivity.npz"
    
    try:
        data = np.load(npz_path)
        
        # 載入 4 款膠片的光譜敏感度曲線
        films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
        for film in films:
            FILM_SPECTRA[film] = {
                'red': data[f'{film}_red'].astype(np.float32),
                'green': data[f'{film}_green'].astype(np.float32),
                'blue': data[f'{film}_blue'].astype(np.float32)
            }
        
        _FILM_SPECTRA_LOADED = True
        
    except Exception as e:
        # 回退到均勻敏感度（所有波長響應相同）
        print(f"⚠️  Warning: 無法載入膠片光譜數據 ({e})，使用均勻敏感度")
        
        films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
        for film in films:
            FILM_SPECTRA[film] = {
                'red': np.ones(N_WAVELENGTHS, dtype=np.float32),
                'green': np.ones(N_WAVELENGTHS, dtype=np.float32),
                'blue': np.ones(N_WAVELENGTHS, dtype=np.float32)
            }
        
        _FILM_SPECTRA_LOADED = True


# ============================================================
# 3. RGB → Spectrum 轉換（Smits 1999 簡化版）
# ============================================================

def rgb_to_spectrum(rgb: np.ndarray) -> np.ndarray:
    """
    將 RGB 影像轉換為光譜影像（Smits 1999 向量化版本）
    
    Args:
        rgb: RGB 影像 (H, W, 3) 或 (3,)，值域 [0, 1]
    
    Returns:
        spectrum: 光譜影像 (H, W, 31) 或 (31,)，值域 [0, 1]
    
    原理（Smits 1999）：
        根據 RGB 值混合基底光譜
        - White 成分: min(R, G, B)
        - 殘差分配: 使用互補色基底（cyan/magenta/yellow 或 red/green/blue）
        - 完全向量化（無 Python 迴圈）
    
    步驟：
        1. 計算 white 成分（三通道最小值）
        2. 計算殘差（rgb - white）
        3. 根據殘差判斷主導色並混合基底
    
    注意：
        - 往返誤差目標 < 5%
        - 基於 data/smits_basis_spectra.npz
    """
    # 確保基底光譜已載入
    if not _BASIS_SPECTRA_LOADED:
        _load_basis_spectra()
    
    # 處理單像素情況
    if rgb.ndim == 1:
        rgb = rgb[None, None, :]  # (3,) → (1, 1, 3)
        single_pixel = True
    else:
        single_pixel = False
    
    H, W = rgb.shape[:2]
    spectrum = np.zeros((H, W, N_WAVELENGTHS), dtype=np.float32)
    
    # 提取 RGB 通道
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    
    # 計算 white 成分（三通道最小值）
    min_rgb = np.minimum(np.minimum(r, g), b)
    
    # 計算殘差
    r_res = r - min_rgb
    g_res = g - min_rgb
    b_res = b - min_rgb
    
    # 向量化混合（利用 broadcasting）
    # White 成分
    spectrum += min_rgb[:, :, None] * BASIS_SPECTRA['white'][None, None, :]
    
    # Cyan/Magenta/Yellow 路徑（當兩個通道高於第三個時）
    # 使用 max(r_res, g_res, b_res) 判斷主導色
    max_res = np.maximum(np.maximum(r_res, g_res), b_res)
    
    # 避免除零
    eps = 1e-8
    
    # Cyan 成分（當 G 和 B 都高於 R 時）
    # cyan ≈ (min(g_res, b_res)) / max_res
    cyan_weight = np.where(
        (g_res > eps) & (b_res > eps) & (r_res < g_res) & (r_res < b_res),
        np.minimum(g_res, b_res),
        0
    )
    spectrum += cyan_weight[:, :, None] * BASIS_SPECTRA['cyan'][None, None, :]
    
    # Magenta 成分（當 R 和 B 都高於 G 時）
    magenta_weight = np.where(
        (r_res > eps) & (b_res > eps) & (g_res < r_res) & (g_res < b_res),
        np.minimum(r_res, b_res),
        0
    )
    spectrum += magenta_weight[:, :, None] * BASIS_SPECTRA['magenta'][None, None, :]
    
    # Yellow 成分（當 R 和 G 都高於 B 時）
    yellow_weight = np.where(
        (r_res > eps) & (g_res > eps) & (b_res < r_res) & (b_res < g_res),
        np.minimum(r_res, g_res),
        0
    )
    spectrum += yellow_weight[:, :, None] * BASIS_SPECTRA['yellow'][None, None, :]
    
    # 單色路徑（當僅一個通道主導時）
    # Red 成分
    red_weight = r_res - yellow_weight - magenta_weight
    red_weight = np.maximum(red_weight, 0)  # 避免負值
    spectrum += red_weight[:, :, None] * BASIS_SPECTRA['red'][None, None, :]
    
    # Green 成分
    green_weight = g_res - yellow_weight - cyan_weight
    green_weight = np.maximum(green_weight, 0)
    spectrum += green_weight[:, :, None] * BASIS_SPECTRA['green'][None, None, :]
    
    # Blue 成分
    blue_weight = b_res - cyan_weight - magenta_weight
    blue_weight = np.maximum(blue_weight, 0)
    spectrum += blue_weight[:, :, None] * BASIS_SPECTRA['blue'][None, None, :]
    
    # 裁剪到 [0, 1]
    spectrum = np.clip(spectrum, 0, 1)
    
    # 如果輸入為單像素，返回 (31,)
    if single_pixel:
        spectrum = spectrum[0, 0]
    
    return spectrum


# ============================================================
# 4. Spectrum → XYZ 轉換
# ============================================================

def spectrum_to_xyz(spectrum: np.ndarray) -> np.ndarray:
    """
    將光譜轉換為 XYZ 色彩空間（CIE 1931）
    
    Args:
        spectrum: 光譜 (H, W, 31) 或 (31,)
    
    Returns:
        xyz: XYZ 色彩 (H, W, 3) 或 (3,)
    
    原理：
        X = k · Σ spectrum(λ) · x̄(λ) · Δλ
        Y = k · Σ spectrum(λ) · ȳ(λ) · Δλ
        Z = k · Σ spectrum(λ) · z̄(λ) · Δλ
        
        k = 100 / Σ ȳ(λ) · Δλ (歸一化常數)
    """
    # 確保 CIE 數據已載入
    if not _CIE_DATA_LOADED:
        _load_cie_data()
    
    # 計算歸一化常數（Y = 100 對應白色）
    k = 100.0 / (np.sum(CIE_Y_BAR) * DELTA_LAMBDA)
    
    # 光譜積分（使用愛因斯坦求和約定）
    if spectrum.ndim == 3:  # (H, W, 31)
        X = k * DELTA_LAMBDA * np.sum(spectrum * CIE_X_BAR[None, None, :], axis=2)
        Y = k * DELTA_LAMBDA * np.sum(spectrum * CIE_Y_BAR[None, None, :], axis=2)
        Z = k * DELTA_LAMBDA * np.sum(spectrum * CIE_Z_BAR[None, None, :], axis=2)
        xyz = np.stack([X, Y, Z], axis=2)
    elif spectrum.ndim == 1:  # (31,)
        X = k * DELTA_LAMBDA * np.sum(spectrum * CIE_X_BAR)
        Y = k * DELTA_LAMBDA * np.sum(spectrum * CIE_Y_BAR)
        Z = k * DELTA_LAMBDA * np.sum(spectrum * CIE_Z_BAR)
        xyz = np.array([X, Y, Z])
    else:
        raise ValueError(f"Unsupported spectrum shape: {spectrum.shape}")
    
    return xyz


def spectrum_to_rgb_with_film(spectrum: np.ndarray, 
                                film_name: str = 'Portra400',
                                apply_gamma: bool = True) -> np.ndarray:
    """
    將光譜轉換為 RGB（考慮膠片敏感度）
    
    Args:
        spectrum: 光譜 (H, W, 31) 或 (31,)
        film_name: 膠片名稱 ('Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400')
        apply_gamma: 是否應用 Gamma 校正
    
    Returns:
        rgb: RGB 影像 (H, W, 3) 或 (3,)
    
    原理：
        傳統: XYZ = ∫ spectrum(λ) · CIE(λ) dλ
        膠片: XYZ = ∫ spectrum(λ) · film(λ) · CIE(λ) dλ
        
        其中 film(λ) 是膠片光譜敏感度曲線
    
    物理意義：
        - 膠片感光層對不同波長的響應度不同
        - 例如：Velvia 的藍層敏感度峰值更窄 → 飽和度更高
        - CineStill 的紅層峰值偏移至 627nm → 鎢絲燈優化
    """
    # 1. 確保膠片數據已載入
    if not _FILM_SPECTRA_LOADED:
        _load_film_spectra()
    
    # 2. 確保 CIE 數據已載入
    if not _CIE_DATA_LOADED:
        _load_cie_data()
    
    # 3. 獲取膠片敏感度曲線
    if film_name not in FILM_SPECTRA:
        raise ValueError(f"Unknown film: {film_name}. Available: {list(FILM_SPECTRA.keys())}")
    
    film_sens = FILM_SPECTRA[film_name]
    
    # 4. 計算歸一化常數（Y = 100 對應白光）
    # 注意：需使用綠色通道的敏感度計算（Y 對應視覺亮度）
    k = 100.0 / (np.sum(CIE_Y_BAR * film_sens['green']) * DELTA_LAMBDA)
    
    # 5. 光譜積分（加權：spectrum × film × CIE）
    if spectrum.ndim == 3:  # (H, W, 31)
        # X 通道: spectrum × film_R × X̄
        X = k * DELTA_LAMBDA * np.sum(
            spectrum * film_sens['red'][None, None, :] * CIE_X_BAR[None, None, :], 
            axis=2
        )
        
        # Y 通道: spectrum × film_G × Ȳ
        Y = k * DELTA_LAMBDA * np.sum(
            spectrum * film_sens['green'][None, None, :] * CIE_Y_BAR[None, None, :], 
            axis=2
        )
        
        # Z 通道: spectrum × film_B × Z̄
        Z = k * DELTA_LAMBDA * np.sum(
            spectrum * film_sens['blue'][None, None, :] * CIE_Z_BAR[None, None, :], 
            axis=2
        )
        
        xyz = np.stack([X, Y, Z], axis=2)
        
    elif spectrum.ndim == 1:  # (31,)
        X = k * DELTA_LAMBDA * np.sum(spectrum * film_sens['red'] * CIE_X_BAR)
        Y = k * DELTA_LAMBDA * np.sum(spectrum * film_sens['green'] * CIE_Y_BAR)
        Z = k * DELTA_LAMBDA * np.sum(spectrum * film_sens['blue'] * CIE_Z_BAR)
        xyz = np.array([X, Y, Z])
    else:
        raise ValueError(f"Unsupported spectrum shape: {spectrum.shape}")
    
    # 6. XYZ → RGB
    return xyz_to_rgb(xyz, apply_gamma=apply_gamma)


# ============================================================
# 5. XYZ → RGB 轉換
# ============================================================

def xyz_to_rgb(xyz: np.ndarray, 
               color_space: str = 'sRGB',
               apply_gamma: bool = True) -> np.ndarray:
    """
    將 XYZ 轉換為 RGB（使用標準色彩矩陣）
    
    Args:
        xyz: XYZ 色彩 (H, W, 3) 或 (3,)
        color_space: 'sRGB', 'AdobeRGB', 'ProPhotoRGB'（目前僅支援 sRGB）
        apply_gamma: 是否應用 Gamma 校正（sRGB 非線性）
    
    Returns:
        rgb: RGB 影像 (H, W, 3) 或 (3,)
    
    原理：
        [R]   [M]   [X]
        [G] = [M] × [Y]
        [B]   [M]   [Z]
        
        M: 色彩空間轉換矩陣
        
        sRGB Gamma 校正：
        C_linear → C_sRGB
        if C_linear <= 0.0031308:
            C_sRGB = 12.92 * C_linear
        else:
            C_sRGB = 1.055 * C_linear^(1/2.4) - 0.055
    """
    # TODO: Phase 4.3 - 支援其他色彩空間
    
    if color_space != 'sRGB':
        raise NotImplementedError(f"Color space '{color_space}' not yet supported")
    
    # XYZ → RGB（線性）
    # 注意：XYZ 範圍為 0-100，需先縮放至 0-1
    if xyz.ndim == 3:  # (H, W, 3)
        rgb_linear = np.einsum('ij,hwj->hwi', XYZ_TO_SRGB_MATRIX, xyz / 100.0)
    elif xyz.ndim == 1:  # (3,)
        rgb_linear = XYZ_TO_SRGB_MATRIX @ (xyz / 100.0)
    else:
        raise ValueError(f"Unsupported XYZ shape: {xyz.shape}")
    
    # 裁剪到有效範圍（避免負值）
    rgb_linear = np.clip(rgb_linear, 0, None)
    
    # sRGB Gamma 校正
    if apply_gamma:
        rgb = np.where(
            rgb_linear <= 0.0031308,
            12.92 * rgb_linear,
            1.055 * np.power(rgb_linear, 1 / 2.4) - 0.055
        )
    else:
        rgb = rgb_linear
    
    return np.clip(rgb, 0, 1)


def rgb_to_xyz(rgb: np.ndarray,
               color_space: str = 'sRGB',
               apply_gamma: bool = True) -> np.ndarray:
    """
    將 RGB 轉換為 XYZ（sRGB → XYZ）
    
    Args:
        rgb: RGB 影像 (H, W, 3) 或 (3,)
        color_space: 'sRGB'（目前僅支援）
        apply_gamma: 是否反向 Gamma 校正
    
    Returns:
        xyz: XYZ 色彩 (H, W, 3) 或 (3,)
    """
    if color_space != 'sRGB':
        raise NotImplementedError(f"Color space '{color_space}' not yet supported")
    
    # sRGB Gamma 逆校正（sRGB → Linear）
    if apply_gamma:
        rgb_linear = np.where(
            rgb <= 0.04045,
            rgb / 12.92,
            np.power((rgb + 0.055) / 1.055, 2.4)
        )
    else:
        rgb_linear = rgb
    
    # RGB → XYZ
    if rgb.ndim == 3:  # (H, W, 3)
        xyz = np.einsum('ij,hwj->hwi', SRGB_TO_XYZ_MATRIX, rgb_linear)
    elif rgb.ndim == 1:  # (3,)
        xyz = SRGB_TO_XYZ_MATRIX @ rgb_linear
    else:
        raise ValueError(f"Unsupported RGB shape: {rgb.shape}")
    
    return xyz


# ============================================================
# 6. 光譜積分工具
# ============================================================

def integrate_spectrum(spectrum: np.ndarray, 
                      weight: np.ndarray) -> np.ndarray:
    """
    計算光譜積分（梯形法則）
    
    Args:
        spectrum: 光譜 (H, W, 31)
        weight: 權重函數 (31,)，如膠片敏感度曲線
    
    Returns:
        integral: 積分結果 (H, W)
    
    原理：
        I = ∫ spectrum(λ) · weight(λ) dλ
          ≈ Σ spectrum(λ) · weight(λ) · Δλ
    
    用途：
        - 計算膠片各層光譜響應
        - response = ∫ S(λ) · Sensitivity(λ) dλ
    """
    if spectrum.shape[-1] != N_WAVELENGTHS:
        raise ValueError(f"Spectrum must have {N_WAVELENGTHS} wavelength channels, got {spectrum.shape[-1]}")
    
    if weight.shape[0] != N_WAVELENGTHS:
        raise ValueError(f"Weight must have {N_WAVELENGTHS} wavelength points, got {weight.shape[0]}")
    
    # 光譜積分（矩形法則，Δλ = 13nm）
    integral = DELTA_LAMBDA * np.sum(spectrum * weight[None, None, :], axis=2)
    
    return integral


# ============================================================
# 7. 往返測試工具
# ============================================================

def test_roundtrip_error(rgb_original: np.ndarray) -> float:
    """
    測試 RGB → Spectrum → XYZ → RGB 往返誤差
    
    Args:
        rgb_original: 原始 RGB (H, W, 3) 或 (3,)
    
    Returns:
        error: 平均絕對誤差（0-1）
    
    用途：
        - 驗證色彩轉換精度
        - 預期誤差 < 0.05 (5%)
    """
    # RGB → Spectrum
    spectrum = rgb_to_spectrum(rgb_original)
    
    # Spectrum → XYZ
    xyz = spectrum_to_xyz(spectrum)
    
    # XYZ → RGB
    rgb_reconstructed = xyz_to_rgb(xyz)
    
    # 計算誤差
    error = np.mean(np.abs(rgb_original - rgb_reconstructed))
    
    return float(error)


def test_film_color_shift(rgb_input: np.ndarray, 
                          films: Optional[list] = None) -> dict:
    """
    測試不同膠片對相同 RGB 輸入的色彩偏移
    
    Args:
        rgb_input: 輸入 RGB (3,) 或 (H, W, 3)
        films: 膠片列表，None 表示全部
    
    Returns:
        results: {
            'Portra400': {'rgb_output': ..., 'error': ...},
            'Velvia50': {...},
            ...
        }
    
    用途：
        - 驗證不同膠片的色彩差異
        - 例如：Velvia 應比 Portra 更飽和
    
    物理意義：
        - 相同光譜通過不同膠片，產生不同 RGB 響應
        - 差異來自膠片敏感度曲線的形狀（峰值、FWHM）
    """
    if films is None:
        films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
    
    results = {}
    
    # 步驟 1: RGB → Spectrum（與膠片無關）
    spectrum = rgb_to_spectrum(rgb_input)
    
    # 步驟 2: 每款膠片的 Spectrum → RGB
    for film in films:
        try:
            rgb_output = spectrum_to_rgb_with_film(spectrum, film_name=film)
            
            # 計算誤差（與原始 RGB 的偏差）
            error = np.max(np.abs(rgb_output - rgb_input))
            
            results[film] = {
                'rgb_output': rgb_output,
                'error': float(error)
            }
        except Exception as e:
            results[film] = {
                'rgb_output': None,
                'error': None,
                'exception': str(e)
            }
    
    return results


# ============================================================
# 8. 輔助工具
# ============================================================

@lru_cache(maxsize=32)
def load_film_spectral_curves(film_name: str) -> Dict[str, np.ndarray]:
    """
    載入膠片光譜敏感度曲線（快取）
    
    Args:
        film_name: 膠片名稱（如 'Portra400'）
    
    Returns:
        curves: {'red': (31,), 'green': (31,), 'blue': (31,)}
    
    注意：
        - Phase 4.4 實作：從 CSV 載入
        - 目前返回高斯近似
    """
    # TODO: Phase 4.4 - 從 data/film_spectral_curves/ 載入
    
    # 暫時使用高斯近似
    curves = {
        'red':   np.exp(-((WAVELENGTHS - 650) ** 2) / (2 * 60 ** 2)),
        'green': np.exp(-((WAVELENGTHS - 550) ** 2) / (2 * 50 ** 2)),
        'blue':  np.exp(-((WAVELENGTHS - 450) ** 2) / (2 * 55 ** 2))
    }
    
    # 歸一化
    for key in curves:
        curves[key] = curves[key] / curves[key].max()
    
    return curves


def get_wavelengths() -> np.ndarray:
    """返回波長陣列 (31,)"""
    return WAVELENGTHS.copy()


def get_cie_color_matching_functions() -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """返回 CIE 1931 色彩匹配函數"""
    return CIE_X_BAR.copy(), CIE_Y_BAR.copy(), CIE_Z_BAR.copy()


def get_basis_spectra() -> Dict[str, np.ndarray]:
    """返回 Smits (1999) 基底光譜"""
    return {k: v.copy() for k, v in BASIS_SPECTRA.items()}


# ============================================================
# 9. 模組資訊
# ============================================================

__version__ = '0.4.1'
__author__ = 'Phos Development Team'
__all__ = [
    # 常數
    'WAVELENGTHS', 'N_WAVELENGTHS', 'DELTA_LAMBDA',
    'CIE_X_BAR', 'CIE_Y_BAR', 'CIE_Z_BAR',
    'BASIS_SPECTRA', 'FILM_SPECTRA',
    
    # 轉換函數
    'rgb_to_spectrum', 'spectrum_to_xyz', 'xyz_to_rgb', 'rgb_to_xyz',
    'spectrum_to_rgb_with_film',
    
    # 積分工具
    'integrate_spectrum',
    
    # 測試工具
    'test_roundtrip_error', 'test_film_color_shift',
    
    # 輔助函數
    'load_film_spectral_curves',
    'get_wavelengths',
    'get_cie_color_matching_functions',
    'get_basis_spectra'
]


if __name__ == '__main__':
    # 快速測試
    print("=" * 70)
    print("  color_utils.py - 光譜模型模組 (Phase 4)")
    print("=" * 70)
    
    print(f"\n波長範圍: {WAVELENGTHS[0]:.0f} - {WAVELENGTHS[-1]:.0f} nm ({N_WAVELENGTHS} 點)")
    print(f"波長間隔: {DELTA_LAMBDA:.0f} nm")
    
    # 測試 RGB → Spectrum
    test_rgb = np.array([[[0.8, 0.3, 0.2]]], dtype=np.float32)
    test_spectrum = rgb_to_spectrum(test_rgb)
    print(f"\n測試 RGB → Spectrum:")
    print(f"  輸入 RGB: {test_rgb[0, 0]}")
    print(f"  輸出 Spectrum 維度: {test_spectrum.shape}")
    print(f"  Spectrum 範圍: {test_spectrum.min():.4f} ~ {test_spectrum.max():.4f}")
    
    # 測試往返
    error = test_roundtrip_error(test_rgb)
    print(f"\n往返測試 (RGB → Spectrum → XYZ → RGB):")
    print(f"  平均誤差: {error:.4f} ({error*100:.2f}%)")
    print(f"  {'✅ PASS' if error < 0.05 else '⚠️  WARNING'} (目標 < 5%)")
    
    print("\n" + "=" * 70)
    print("  模組初始化完成 ✅")
    print("=" * 70)
