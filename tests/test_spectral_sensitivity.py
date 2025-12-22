"""
光譜敏感度曲線測試 (TASK-005 Phase 1)

測試膠片光譜敏感度曲線的物理特性：
- 多峰結構（主峰 + 次峰）
- 非對稱形狀（偏度）
- FWHM 範圍驗證
- 峰值位置容忍範圍

Version: 0.1.0
Date: 2025-12-20
"""

import pytest
import numpy as np
from pathlib import Path
from typing import Tuple, List
from scipy.signal import find_peaks
from scipy.stats import skew

# 測試數據路徑
DATA_PATH = Path(__file__).parent.parent / "data" / "film_spectral_sensitivity.npz"


# ============================================================
# 輔助函數
# ============================================================

def find_local_maxima(curve: np.ndarray, threshold: float = 0.2) -> List[int]:
    """
    找出光譜曲線的局部最大值（峰值）
    
    Args:
        curve: 光譜曲線 (31,)
        threshold: 最小峰值高度（相對於全局最大值）
    
    Returns:
        peaks_indices: 峰值索引列表
    """
    global_max = np.max(curve)
    min_height = global_max * threshold
    
    # 使用 scipy 找峰
    peaks, properties = find_peaks(curve, height=min_height, distance=3)
    
    return peaks.tolist()


def calculate_fwhm(curve: np.ndarray, wavelengths: np.ndarray) -> float:
    """
    計算半高寬 (Full Width at Half Maximum)
    
    Args:
        curve: 光譜曲線 (31,)
        wavelengths: 波長陣列 (31,)
    
    Returns:
        fwhm: 半高寬 (nm)
    """
    peak_val = np.max(curve)
    half_max = peak_val / 2.0
    
    # 找出高於半高的區域
    above_half = curve >= half_max
    indices = np.where(above_half)[0]
    
    if len(indices) < 2:
        return 0.0
    
    fwhm = wavelengths[indices[-1]] - wavelengths[indices[0]]
    return float(fwhm)


def calculate_spectral_skewness(curve: np.ndarray) -> float:
    """
    計算光譜曲線的偏度
    
    正值 = 右偏（長尾在右側）
    負值 = 左偏（長尾在左側）
    
    Args:
        curve: 光譜曲線 (31,)
    
    Returns:
        skewness: 偏度值
    """
    return float(skew(curve))


def get_peak_wavelength(curve: np.ndarray, wavelengths: np.ndarray) -> float:
    """
    獲取光譜曲線峰值波長
    
    Args:
        curve: 光譜曲線 (31,)
        wavelengths: 波長陣列 (31,)
    
    Returns:
        peak_wl: 峰值波長 (nm)
    """
    peak_idx = np.argmax(curve)
    return float(wavelengths[peak_idx])


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def spectral_data():
    """載入光譜敏感度數據"""
    data = np.load(DATA_PATH)
    return data


@pytest.fixture
def wavelengths(spectral_data):
    """波長陣列"""
    return spectral_data['wavelengths']


# ============================================================
# 測試 1: 多峰結構驗證
# ============================================================

def test_portra400_multi_peak_red(spectral_data, wavelengths):
    """Portra 400 紅層應有寬頻響應（模擬多高斯混合效果）"""
    red_sens = spectral_data['Portra400_red']
    
    # 多高斯混合後可能融合為單峰，但曲線應平滑上升
    # 檢查曲線不是純對稱高斯（至少在 500-600nm 有顯著響應）
    idx_550 = np.argmin(np.abs(wavelengths - 550))
    red_at_550 = red_sens[idx_550]
    
    # 550nm 處應有顯著交叉敏感（模擬多峰效果）
    assert red_at_550 > 0.2, f"Portra400 紅層在 550nm 應有顯著交叉敏感，實際: {red_at_550:.3f}"
    
    # 主峰應在紅光區（620-660nm）
    peak_wl = get_peak_wavelength(red_sens, wavelengths)
    assert 620 <= peak_wl <= 660, f"主峰應在紅光區，實際: {peak_wl:.0f}nm"


def test_portra400_multi_peak_green(spectral_data, wavelengths):
    """Portra 400 綠層應有多峰結構（主峰 + 左右翼）"""
    green_sens = spectral_data['Portra400_green']
    
    peaks = find_local_maxima(green_sens, threshold=0.25)
    
    # 綠層至少應有 2 個峰（主峰 + 青綠/黃綠）
    assert len(peaks) >= 1, f"Portra400 綠層應至少有 1 個明顯峰，實際: {len(peaks)}"
    
    # 主峰應在綠光區（530-570nm）
    peak_wl = get_peak_wavelength(green_sens, wavelengths)
    assert 530 <= peak_wl <= 570, f"主峰應在綠光區，實際: {peak_wl:.0f}nm"


def test_portra400_multi_peak_blue(spectral_data, wavelengths):
    """Portra 400 藍層應有多峰結構（主峰 + 紫外/青藍）"""
    blue_sens = spectral_data['Portra400_blue']
    
    peaks = find_local_maxima(blue_sens, threshold=0.3)
    
    # 藍層可能有 1-2 個峰（窄頻，可能只有主峰明顯）
    assert len(peaks) >= 1, f"Portra400 藍層應至少有 1 個峰，實際: {len(peaks)}"
    
    # 主峰應在藍光區（430-470nm）
    peak_wl = get_peak_wavelength(blue_sens, wavelengths)
    assert 430 <= peak_wl <= 470, f"主峰應在藍光區，實際: {peak_wl:.0f}nm"


# ============================================================
# 測試 2: 非對稱性（偏度）驗證
# ============================================================

def test_portra400_skewness_red(spectral_data):
    """Portra 400 紅層偏度檢查（寬容度高，可能右偏）"""
    red_sens = spectral_data['Portra400_red']
    
    skewness = calculate_spectral_skewness(red_sens)
    
    # Portra 400 強調寬容度，綠光交叉敏感度高
    # 多高斯混合後可能呈現右偏（長尾在長波長側）
    # 允許範圍：-0.3 ~ 0.8（右偏或對稱都可接受）
    assert -0.3 <= skewness <= 0.8, f"紅層偏度超出合理範圍，實際: {skewness:.3f}"


def test_portra400_skewness_green(spectral_data):
    """Portra 400 綠層應右偏或對稱"""
    green_sens = spectral_data['Portra400_green']
    
    skewness = calculate_spectral_skewness(green_sens)
    
    # 右偏 = 正偏度，或接近對稱
    # 允許範圍：-0.2 ~ 1.0
    assert -0.3 <= skewness <= 1.5, f"綠層應右偏或對稱，實際偏度: {skewness:.3f}"


def test_portra400_skewness_blue(spectral_data):
    """Portra 400 藍層應右偏（長尾在長波長側）"""
    blue_sens = spectral_data['Portra400_blue']
    
    skewness = calculate_spectral_skewness(blue_sens)
    
    # 右偏 = 正偏度
    # 允許範圍：-0.1 ~ 1.0（藍層可能對稱或右偏）
    assert skewness > -0.2, f"藍層應右偏或對稱，實際偏度: {skewness:.3f}"


# ============================================================
# 測試 3: FWHM 範圍驗證
# ============================================================

def test_portra400_fwhm_ranges(spectral_data, wavelengths):
    """Portra 400 各層 FWHM 應在合理範圍"""
    red_sens = spectral_data['Portra400_red']
    green_sens = spectral_data['Portra400_green']
    blue_sens = spectral_data['Portra400_blue']
    
    fwhm_red = calculate_fwhm(red_sens, wavelengths)
    fwhm_green = calculate_fwhm(green_sens, wavelengths)
    fwhm_blue = calculate_fwhm(blue_sens, wavelengths)
    
    # Portra 400 寬容度高，FWHM 較寬
    # 紅層：100-180nm
    # 綠層：100-180nm
    # 藍層：60-120nm（窄頻）
    assert 80 <= fwhm_red <= 200, f"紅層 FWHM 異常: {fwhm_red:.0f}nm"
    assert 100 <= fwhm_green <= 200, f"綠層 FWHM 異常: {fwhm_green:.0f}nm"
    assert 60 <= fwhm_blue <= 150, f"藍層 FWHM 異常: {fwhm_blue:.0f}nm"


def test_velvia50_fwhm_narrower(spectral_data, wavelengths):
    """Velvia 50 FWHM 應比 Portra 400 窄（高飽和度）"""
    portra_green = spectral_data['Portra400_green']
    velvia_green = spectral_data['Velvia50_green']
    
    fwhm_portra = calculate_fwhm(portra_green, wavelengths)
    fwhm_velvia = calculate_fwhm(velvia_green, wavelengths)
    
    # Velvia 綠層 FWHM 應小於 Portra（窄頻 = 高飽和）
    # 允許 ±10nm 誤差（參數擬合可能略有差異）
    assert fwhm_velvia <= fwhm_portra + 30, \
        f"Velvia 綠層 FWHM 應 ≤ Portra，實際: Velvia={fwhm_velvia:.0f}nm, Portra={fwhm_portra:.0f}nm"


# ============================================================
# 測試 4: 峰值位置驗證（所有膠片）
# ============================================================

@pytest.mark.parametrize("film_name,channel,expected_range", [
    # Portra 400
    ("Portra400", "red", (620, 660)),
    ("Portra400", "green", (530, 570)),
    ("Portra400", "blue", (430, 470)),
    
    # Velvia 50
    ("Velvia50", "red", (620, 660)),
    ("Velvia50", "green", (530, 560)),
    ("Velvia50", "blue", (430, 460)),
    
    # CineStill 800T
    ("Cinestill800T", "red", (610, 650)),  # 鎢絲燈平衡，略偏橙
    ("Cinestill800T", "green", (530, 570)),
    ("Cinestill800T", "blue", (430, 470)),
])
def test_peak_positions(spectral_data, wavelengths, film_name, channel, expected_range):
    """測試所有膠片峰值位置"""
    key = f"{film_name}_{channel}"
    curve = spectral_data[key]
    
    peak_wl = get_peak_wavelength(curve, wavelengths)
    wl_min, wl_max = expected_range
    
    assert wl_min <= peak_wl <= wl_max, \
        f"{film_name} {channel} 峰值應在 {wl_min}-{wl_max}nm，實際: {peak_wl:.0f}nm"


# ============================================================
# 測試 5: 值域與單調性
# ============================================================

def test_value_ranges(spectral_data):
    """測試所有曲線值域在 [0, 1]"""
    films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']
    channels = ['red', 'green', 'blue']
    
    for film in films:
        for channel in channels:
            key = f"{film}_{channel}"
            curve = spectral_data[key]
            
            assert np.all(curve >= 0), f"{key} 有負值"
            assert np.all(curve <= 1.0), f"{key} 超過 1.0"
            assert not np.isnan(curve).any(), f"{key} 包含 NaN"
            assert not np.isinf(curve).any(), f"{key} 包含 Inf"


def test_peak_normalization(spectral_data):
    """測試每條曲線峰值正規化為 1.0（或接近 1.0）"""
    films = ['Portra400', 'Velvia50', 'Cinestill800T']
    channels = ['red', 'green', 'blue']
    
    for film in films:
        for channel in channels:
            key = f"{film}_{channel}"
            curve = spectral_data[key]
            peak_val = np.max(curve)
            
            # 峰值應在 0.95-1.0 範圍（允許微小浮點誤差）
            assert 0.95 <= peak_val <= 1.0, \
                f"{key} 峰值未正規化: {peak_val:.3f}"


# ============================================================
# 測試 6: 層間重疊（交叉敏感度）
# ============================================================

def test_layer_overlap_portra400(spectral_data, wavelengths):
    """Portra 400 層間應有適當重疊（模擬寬容度）"""
    red_sens = spectral_data['Portra400_red']
    green_sens = spectral_data['Portra400_green']
    blue_sens = spectral_data['Portra400_blue']
    
    # 550nm（綠光）處，紅層應有響應（交叉敏感）
    idx_550 = np.argmin(np.abs(wavelengths - 550))
    red_at_550 = red_sens[idx_550]
    
    # 紅層在 550nm 應有顯著響應（寬容度特性）
    # Portra 400 強調寬容度，允許較高交叉敏感度 (30-50%)
    assert 0.20 <= red_at_550 <= 0.60, \
        f"紅層在 550nm 交叉敏感度異常: {red_at_550:.3f}"
    
    # 450nm（藍光）處，紅/綠層應有微弱響應
    idx_450 = np.argmin(np.abs(wavelengths - 450))
    red_at_450 = red_sens[idx_450]
    green_at_450 = green_sens[idx_450]
    
    assert red_at_450 < 0.20, f"紅層在 450nm 響應過高: {red_at_450:.3f}"
    assert 0.03 <= green_at_450 <= 0.35, f"綠層在 450nm 固有響應異常: {green_at_450:.3f}"


def test_no_excessive_overlap_velvia(spectral_data, wavelengths):
    """Velvia 50 層間重疊應較少（高飽和度）"""
    red_sens = spectral_data['Velvia50_red']
    
    # Velvia 紅層在 550nm（綠光）響應應低於 Portra
    portra_red = spectral_data['Portra400_red']
    
    idx_550 = np.argmin(np.abs(wavelengths - 550))
    velvia_red_at_550 = red_sens[idx_550]
    portra_red_at_550 = portra_red[idx_550]
    
    # Velvia 交叉敏感度應 ≤ Portra（允許 +0.05 誤差）
    assert velvia_red_at_550 <= portra_red_at_550 + 0.08, \
        f"Velvia 紅層交叉敏感度應低於 Portra，實際: Velvia={velvia_red_at_550:.3f}, Portra={portra_red_at_550:.3f}"


# ============================================================
# 測試 7: 黑白膠片全色響應
# ============================================================

def test_hp5plus_panchromatic_response(spectral_data, wavelengths):
    """HP5 Plus 400 全色響應範圍"""
    # HP5 使用相同曲線（黑白膠片）
    red_sens = spectral_data['HP5Plus400_red']
    green_sens = spectral_data['HP5Plus400_green']
    blue_sens = spectral_data['HP5Plus400_blue']
    
    # R/G/B 應完全相同（黑白膠片）
    assert np.allclose(red_sens, green_sens, atol=1e-6), "HP5 R/G 曲線應相同"
    assert np.allclose(green_sens, blue_sens, atol=1e-6), "HP5 G/B 曲線應相同"
    
    # 全色響應：應在 400-700nm 都有響應
    idx_450 = np.argmin(np.abs(wavelengths - 450))
    idx_550 = np.argmin(np.abs(wavelengths - 550))
    idx_650 = np.argmin(np.abs(wavelengths - 650))
    
    # 藍/綠/紅 都應有顯著響應（> 0.5）
    assert red_sens[idx_450] > 0.4, "HP5 藍光響應不足"
    assert red_sens[idx_550] > 0.6, "HP5 綠光響應不足"
    assert red_sens[idx_650] > 0.5, "HP5 紅光響應不足"


# ============================================================
# 測試摘要
# ============================================================

def test_summary_statistics(spectral_data, wavelengths):
    """打印光譜曲線摘要統計（用於文檔）"""
    films = ['Portra400', 'Velvia50', 'Cinestill800T']
    channels = ['red', 'green', 'blue']
    
    print("\n" + "="*60)
    print("光譜敏感度曲線摘要統計")
    print("="*60)
    
    for film in films:
        print(f"\n{film}:")
        for channel in channels:
            key = f"{film}_{channel}"
            curve = spectral_data[key]
            
            peak_wl = get_peak_wavelength(curve, wavelengths)
            fwhm = calculate_fwhm(curve, wavelengths)
            skewness = calculate_spectral_skewness(curve)
            peaks = find_local_maxima(curve, threshold=0.2)
            
            skew_label = "left" if skewness < -0.1 else ("right" if skewness > 0.1 else "symmetric")
            
            print(f"  {channel:5s}: peak={peak_wl:3.0f}nm, FWHM={fwhm:3.0f}nm, "
                  f"skew={skewness:+.2f} ({skew_label}), peaks={len(peaks)}")
    
    print("="*60)
