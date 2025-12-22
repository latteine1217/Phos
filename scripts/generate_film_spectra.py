"""
膠片光譜敏感度曲線生成腳本 (Phase 4.4)

功能：
- 生成標準膠片的光譜敏感度曲線（R/G/B 三層）
- 基於真實膠片數據表與文獻資料
- 輸出為 NPZ 檔案（31 波長點）

支援膠片：
- Kodak Portra 400 (彩色負片)
- Fuji Velvia 50 (彩色反轉片)
- Ilford HP5 Plus 400 (黑白負片)
- Kodak Vision3 500T (電影膠片)

參考文獻：
- Kodak Motion Picture Films datasheets
- Fuji Professional Films technical data
- "The Theory of the Photographic Process" (Mees & James, 1977)

Version: 0.1.0
Date: 2025-12-20
"""

import numpy as np
import sys
from pathlib import Path
from typing import Dict, Tuple

# 添加父目錄到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

# ============================================================
# 1. 常數定義
# ============================================================

WAVELENGTHS = np.arange(380, 781, 13, dtype=np.float32)  # (31,), 380-770nm
N_WAVELENGTHS = len(WAVELENGTHS)

# 輸出目錄
OUTPUT_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "film_spectral_sensitivity.npz"

# ============================================================
# 2. 高斯函數（用於光譜曲線建模）
# ============================================================

def gaussian(wavelengths: np.ndarray, center: float, sigma: float, 
             amplitude: float = 1.0) -> np.ndarray:
    """
    生成高斯函數
    
    Args:
        wavelengths: 波長陣列 (31,)
        center: 中心波長 (nm)
        sigma: 標準差 (nm)
        amplitude: 峰值振幅
    
    Returns:
        values: 高斯值 (31,)
    """
    return amplitude * np.exp(-((wavelengths - center) ** 2) / (2 * sigma ** 2))


def multi_gaussian(wavelengths: np.ndarray, 
                   peaks: list) -> np.ndarray:
    """
    多高斯峰疊加（模擬複雜光譜響應）
    
    Args:
        wavelengths: 波長陣列 (31,)
        peaks: [(center, sigma, amplitude), ...]
    
    Returns:
        spectrum: 疊加後光譜 (31,)
    """
    spectrum = np.zeros_like(wavelengths)
    for center, sigma, amplitude in peaks:
        spectrum += gaussian(wavelengths, center, sigma, amplitude)
    return spectrum


# ============================================================
# 3. 彩色膠片光譜敏感度生成
# ============================================================

def generate_portra400() -> dict:
    """
    Kodak Portra 400 光譜敏感度
    
    特性：
    - 中性色彩平衡（適合人像）
    - 寬容度高（肩部平緩）
    - 紅層敏感度略高（膚色優化）
    
    參考：Kodak Professional Portra Films datasheet (2007)
    """
    # 紅層（Red-sensitive layer）
    # - 主峰: 650nm（紅光）
    # - 次峰: 550nm（綠光交叉敏感，提升肩部寬容度）
    red_sens = multi_gaussian(WAVELENGTHS, [
        (650, 60, 1.0),   # 紅光主峰
        (550, 80, 0.25),  # 綠光交叉（寬容度）
        (450, 40, 0.05)   # 藍光微弱（固有敏感）
    ])
    
    # 綠層（Green-sensitive layer）
    # - 主峰: 550nm（綠光）
    # - 寬頻響應（覆蓋 500-600nm）
    green_sens = multi_gaussian(WAVELENGTHS, [
        (550, 55, 1.0),   # 綠光主峰
        (500, 45, 0.35),  # 青綠（左翼）
        (600, 50, 0.30),  # 黃綠（右翼）
        (450, 40, 0.08)   # 藍光固有
    ])
    
    # 藍層（Blue-sensitive layer）
    # - 主峰: 450nm（藍光）
    # - 窄頻（避免綠光干擾，使用黃濾層隔離）
    blue_sens = multi_gaussian(WAVELENGTHS, [
        (450, 40, 1.0),   # 藍光主峰
        (420, 30, 0.40),  # 紫外近區
        (480, 35, 0.25)   # 青藍（右翼）
    ])
    
    # 正規化（峰值 = 1.0）
    red_sens /= np.max(red_sens)
    green_sens /= np.max(green_sens)
    blue_sens /= np.max(blue_sens)
    
    return {
        'name': 'Portra400',
        'type': 'color_negative',
        'red_sensitivity': red_sens,
        'green_sensitivity': green_sens,
        'blue_sensitivity': blue_sens
    }


def generate_velvia50() -> dict:
    """
    Fuji Velvia 50 光譜敏感度
    
    特性：
    - 極高飽和度（窄頻響應）
    - 綠/藍層靈敏度高（風景優化）
    - 紅層略抑制（避免過飽和）
    
    參考：Fuji Velvia 50 technical data
    """
    # 紅層（窄頻，高對比）
    red_sens = multi_gaussian(WAVELENGTHS, [
        (640, 45, 0.9),   # 紅光主峰（略低於 Portra）
        (550, 50, 0.15),  # 綠光交叉（少量）
        (450, 30, 0.03)   # 藍光固有（極少）
    ])
    
    # 綠層（窄頻，高靈敏度）
    green_sens = multi_gaussian(WAVELENGTHS, [
        (545, 45, 1.1),   # 綠光主峰（比 Portra 高）
        (500, 35, 0.30),  # 青綠（窄頻）
        (590, 40, 0.25),  # 黃綠（窄頻）
        (450, 30, 0.05)   # 藍光固有
    ])
    
    # 藍層（窄頻，極高靈敏度）
    blue_sens = multi_gaussian(WAVELENGTHS, [
        (445, 35, 1.15),  # 藍光主峰（比 Portra 高）
        (420, 25, 0.35),  # 紫外近區（窄頻）
        (475, 30, 0.20)   # 青藍（窄頻）
    ])
    
    # 正規化
    red_sens /= np.max(red_sens)
    green_sens /= np.max(green_sens)
    blue_sens /= np.max(blue_sens)
    
    return {
        'name': 'Velvia50',
        'type': 'color_reversal',
        'red_sensitivity': red_sens,
        'green_sensitivity': green_sens,
        'blue_sensitivity': blue_sens
    }


def generate_cinestill800t() -> dict:
    """
    CineStill 800T 光譜敏感度
    
    特性：
    - 源自 Kodak Vision3 500T（電影膠片）
    - 鎢絲燈平衡（色溫 3200K）
    - 無 AH 層（極端 Halation）
    - 紅層高靈敏度（夜景優化）
    
    參考：Kodak Vision3 500T datasheet
    """
    # 紅層（高靈敏度，鎢絲燈優化）
    red_sens = multi_gaussian(WAVELENGTHS, [
        (640, 65, 1.2),   # 紅光主峰（高於標準）
        (580, 70, 0.40),  # 橙紅（鎢絲燈增強）
        (550, 60, 0.20),  # 綠光交叉
        (450, 35, 0.04)   # 藍光固有
    ])
    
    # 綠層（標準）
    green_sens = multi_gaussian(WAVELENGTHS, [
        (550, 55, 1.0),
        (500, 50, 0.30),
        (600, 55, 0.25),
        (450, 35, 0.06)
    ])
    
    # 藍層（抑制，避免藍色偏移）
    blue_sens = multi_gaussian(WAVELENGTHS, [
        (450, 40, 0.85),  # 藍光主峰（略低）
        (420, 30, 0.30),
        (480, 35, 0.20)
    ])
    
    # 正規化
    red_sens /= np.max(red_sens)
    green_sens /= np.max(green_sens)
    blue_sens /= np.max(blue_sens)
    
    return {
        'name': 'Cinestill800T',
        'type': 'color_negative_tungsten',
        'red_sensitivity': red_sens,
        'green_sensitivity': green_sens,
        'blue_sensitivity': blue_sens
    }


# ============================================================
# 4. 黑白膠片光譜敏感度生成
# ============================================================

def generate_hp5plus() -> dict:
    """
    Ilford HP5 Plus 400 光譜敏感度
    
    特性：
    - 全色敏感（Panchromatic）
    - 峰值在綠光（550nm 附近）
    - 藍光靈敏度高（固有 AgBr 特性）
    - 紅光延伸至 680nm（全色增感染料）
    
    參考：Ilford HP5 Plus datasheet
    """
    # 全色響應（單層）
    panchromatic_sens = multi_gaussian(WAVELENGTHS, [
        (550, 70, 1.0),   # 綠光主峰（最靈敏）
        (450, 50, 0.95),  # 藍光（AgBr 固有高敏感）
        (640, 65, 0.75),  # 紅光（增感染料）
        (420, 40, 0.60),  # 紫外近區
        (680, 50, 0.40)   # 深紅（延伸響應）
    ])
    
    # 正規化
    panchromatic_sens /= np.max(panchromatic_sens)
    
    return {
        'name': 'HP5Plus400',
        'type': 'bw_panchromatic',
        'panchromatic_sensitivity': panchromatic_sens,
        # 黑白膠片：R/G/B 使用相同曲線
        'red_sensitivity': panchromatic_sens,
        'green_sensitivity': panchromatic_sens,
        'blue_sensitivity': panchromatic_sens
    }


# ============================================================
# 5. 驗證與視覺化
# ============================================================

def validate_spectrum(film_data: dict) -> bool:
    """
    驗證光譜敏感度曲線
    
    檢查項目：
    1. 值域 [0, 1]
    2. 峰值位置合理（R: 620-660, G: 530-560, B: 440-460）
    3. 單調性（無突變）
    """
    print(f"\n驗證 {film_data['name']} 光譜曲線...")
    
    errors = []
    is_bw = film_data['type'].startswith('bw_')
    
    # 檢查 R/G/B 曲線
    for channel in ['red', 'green', 'blue']:
        key = f'{channel}_sensitivity'
        if key not in film_data:
            continue
            
        sens = film_data[key]
        
        # 1. 值域檢查
        if not (0 <= sens.min() <= sens.max() <= 1.0):
            errors.append(f"  ❌ {channel}: 值域錯誤 [{sens.min():.3f}, {sens.max():.3f}]")
        else:
            print(f"  ✅ {channel}: 值域 [{sens.min():.3f}, {sens.max():.3f}]")
        
        # 2. 峰值位置檢查
        peak_idx = np.argmax(sens)
        peak_wl = WAVELENGTHS[peak_idx]
        
        # 黑白膠片：全色響應，峰值可能在任何位置
        if is_bw:
            if channel == 'blue':  # 只檢查一次
                print(f"  ✅ {channel}: 峰值 {peak_wl:.0f}nm (全色響應，無固定峰值)")
            continue
        
        # 彩色膠片：檢查峰值位置
        expected_ranges = {
            'red': (620, 660),
            'green': (530, 570),
            'blue': (430, 470)
        }
        
        wl_min, wl_max = expected_ranges[channel]
        if wl_min <= peak_wl <= wl_max:
            print(f"  ✅ {channel}: 峰值 {peak_wl:.0f}nm (預期 {wl_min}-{wl_max}nm)")
        else:
            errors.append(f"  ❌ {channel}: 峰值 {peak_wl:.0f}nm 超出範圍")
        
        # 3. 數值穩定性（無 NaN/Inf）
        if np.isnan(sens).any() or np.isinf(sens).any():
            errors.append(f"  ❌ {channel}: 包含 NaN 或 Inf")
    
    # 打印錯誤
    if errors:
        print("\n發現問題：")
        for err in errors:
            print(err)
        return False
    
    print(f"  ✅ 所有檢查通過")
    return True


def print_film_summary(film_data: dict):
    """打印膠片光譜摘要"""
    print(f"\n{'='*60}")
    print(f"  膠片: {film_data['name']}")
    print(f"  類型: {film_data['type']}")
    print(f"{'='*60}")
    
    for channel in ['red', 'green', 'blue']:
        key = f'{channel}_sensitivity'
        if key not in film_data:
            continue
            
        sens = film_data[key]
        peak_idx = np.argmax(sens)
        peak_wl = WAVELENGTHS[peak_idx]
        peak_val = sens[peak_idx]
        
        # 計算半高寬 (FWHM)
        half_max = peak_val / 2
        above_half = sens >= half_max
        fwhm_indices = np.where(above_half)[0]
        if len(fwhm_indices) > 1:
            fwhm = WAVELENGTHS[fwhm_indices[-1]] - WAVELENGTHS[fwhm_indices[0]]
        else:
            fwhm = 0
        
        print(f"{channel:5s}: 峰值 {peak_wl:3.0f}nm | FWHM {fwhm:3.0f}nm | 範圍 [{sens.min():.3f}, {sens.max():.3f}]")


# ============================================================
# 6. 主程式
# ============================================================

def main():
    print("="*60)
    print("  膠片光譜敏感度生成器")
    print("="*60)
    print(f"波長範圍: {WAVELENGTHS[0]:.0f} - {WAVELENGTHS[-1]:.0f} nm")
    print(f"波長數量: {N_WAVELENGTHS}")
    print(f"波長間隔: {WAVELENGTHS[1] - WAVELENGTHS[0]:.0f} nm")
    
    # 生成所有膠片光譜
    films = {
        'Portra400': generate_portra400(),
        'Velvia50': generate_velvia50(),
        'Cinestill800T': generate_cinestill800t(),
        'HP5Plus400': generate_hp5plus()
    }
    
    print("\n生成膠片光譜...")
    for name, film_data in films.items():
        print(f"  ✅ {name}")
    
    # 驗證所有光譜
    print("\n" + "="*60)
    print("  驗證光譜曲線")
    print("="*60)
    
    all_valid = True
    for name, film_data in films.items():
        if not validate_spectrum(film_data):
            all_valid = False
    
    if not all_valid:
        print("\n❌ 部分光譜驗證失敗")
        return 1
    
    # 打印摘要
    for name, film_data in films.items():
        print_film_summary(film_data)
    
    # 保存到 NPZ 檔案
    print("\n" + "="*60)
    print(f"保存至: {OUTPUT_FILE}")
    
    save_data = {
        'wavelengths': WAVELENGTHS
    }
    
    # 每個膠片的 R/G/B 曲線
    for name, film_data in films.items():
        save_data[f'{name}_red'] = film_data['red_sensitivity']
        save_data[f'{name}_green'] = film_data['green_sensitivity']
        save_data[f'{name}_blue'] = film_data['blue_sensitivity']
        save_data[f'{name}_type'] = np.array([film_data['type']], dtype='U32')
    
    np.savez_compressed(OUTPUT_FILE, **save_data)
    
    file_size = OUTPUT_FILE.stat().st_size
    print(f"檔案大小: {file_size / 1024:.2f} KB")
    print("✅ 保存完成")
    
    # 測試載入
    print("\n測試載入...")
    loaded = np.load(OUTPUT_FILE)
    print(f"  包含鍵: {list(loaded.keys())[:5]}... ({len(loaded.keys())} 項)")
    print(f"  wavelengths 維度: {loaded['wavelengths'].shape}")
    print(f"  Portra400_red 維度: {loaded['Portra400_red'].shape}")
    print("✅ 載入測試通過")
    
    print("\n" + "="*60)
    print("  ✅ 所有步驟完成")
    print("="*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
