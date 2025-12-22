"""
Smits (1999) 基底光譜生成腳本 (Phase 4.2)

功能：
- 生成 7 個基底光譜（white, cyan, magenta, yellow, red, green, blue）
- 輸出為 NPZ 檔案（data/smits_basis_spectra.npz）
- 每個基底 31 個波長點（380-780nm, 每 13nm）

參考文獻：
- Smits, Brian. "An RGB-to-Spectrum Conversion for Reflectances." 
  Journal of Graphics Tools 4.4 (1999): 11-22.

說明：
- 由於原始論文數據難以獲取，本腳本使用物理啟發的近似
- 基於以下原則：
  1. White: 平坦光譜（全波段反射）
  2. Red/Green/Blue: 對應波段高反射
  3. Cyan/Magenta/Yellow: 互補色（對應吸收紅/綠/藍）
  4. 使用平滑過渡（高斯 + 步階函數組合）

Version: 0.4.0
Date: 2025-12-20
"""

import numpy as np
import sys
from pathlib import Path

# 添加父目錄到 sys.path（用於導入 color_utils）
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 1. 常數定義
# ============================================================

WAVELENGTHS = np.arange(380, 781, 13, dtype=np.float32)  # (31,)
N_WAVELENGTHS = len(WAVELENGTHS)

# 特徵波長（nm）
LAMBDA_RED = 650
LAMBDA_GREEN = 550
LAMBDA_BLUE = 450

# 高斯寬度（nm）
SIGMA_RED = 60
SIGMA_GREEN = 50
SIGMA_BLUE = 55


# ============================================================
# 2. 基底光譜生成函數
# ============================================================

def gaussian(wavelengths: np.ndarray, center: float, sigma: float) -> np.ndarray:
    """
    生成高斯函數
    
    Args:
        wavelengths: 波長陣列 (31,)
        center: 中心波長 (nm)
        sigma: 標準差 (nm)
    
    Returns:
        values: 高斯值 (31,)
    """
    return np.exp(-((wavelengths - center) ** 2) / (2 * sigma ** 2))


def smooth_step(wavelengths: np.ndarray, edge: float, width: float) -> np.ndarray:
    """
    生成平滑步階函數（smoothstep）
    
    Args:
        wavelengths: 波長陣列 (31,)
        edge: 步階中心位置 (nm)
        width: 過渡寬度 (nm)
    
    Returns:
        values: 步階值 [0, 1] (31,)
    """
    t = np.clip((wavelengths - edge) / width + 0.5, 0, 1)
    return t * t * (3 - 2 * t)  # Smoothstep 插值


def generate_white() -> np.ndarray:
    """
    White 基底：平坦光譜（全波段均勻反射）
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    return np.ones(N_WAVELENGTHS, dtype=np.float32)


def generate_red() -> np.ndarray:
    """
    Red 基底：長波段高反射，短波段低反射
    
    策略：
    - 600nm 以上：1.0（強反射）
    - 600nm 以下：急遽衰減至 0.0（使用 8 次方函數）
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    # 使用陡峭的步階（在 590nm 處過渡，窄寬度）
    step = smooth_step(WAVELENGTHS, edge=590, width=20)
    
    # 使用 8 次方強化陡峭性（更陡峭的過渡）
    spectrum = step ** 8
    
    return spectrum


def generate_green() -> np.ndarray:
    """
    Green 基底：中波段高反射，短波長波段低反射
    
    策略：
    - 高斯峰在 550nm
    - 使用較寬 sigma（覆蓋 500-600nm 範圍）
    - 4 次方強化陡峭性
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    # 主高斯峰（使用較寬的 sigma 以覆蓋綠色範圍）
    peak = gaussian(WAVELENGTHS, LAMBDA_GREEN, sigma=50)
    
    # 使用 4 次方強化陡峭性
    spectrum = peak ** 4
    
    return spectrum


def generate_blue() -> np.ndarray:
    """
    Blue 基底：短波段高反射，長波段低反射
    
    策略：
    - 500nm 以下：1.0（強反射）
    - 500nm 以上：急遽衰減至 0.0（使用 8 次方函數）
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    # 使用陡峭的反向步階（在 510nm 處過渡）
    step = 1.0 - smooth_step(WAVELENGTHS, edge=510, width=20)
    
    # 使用 8 次方強化陡峭性（更陡峭的過渡）
    spectrum = step ** 8
    
    return spectrum


def generate_cyan() -> np.ndarray:
    """
    Cyan 基底：吸收紅光（Red 的互補色）
    
    策略：
    - 短波高（藍+綠），長波低（吸收紅）
    - 簡化為 1.0 - Red
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    red_spectrum = generate_red()
    return 1.0 - red_spectrum


def generate_magenta() -> np.ndarray:
    """
    Magenta 基底：吸收綠光（Green 的互補色）
    
    策略：
    - 短波高（藍）+ 長波高（紅），中波低（吸收綠）
    - 簡化為 1.0 - Green
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    green_spectrum = generate_green()
    return 1.0 - green_spectrum


def generate_yellow() -> np.ndarray:
    """
    Yellow 基底：吸收藍光（Blue 的互補色）
    
    策略：
    - 中長波高（綠+紅），短波低（吸收藍）
    - 簡化為 1.0 - Blue
    
    Returns:
        spectrum: (31,), 值域 [0, 1]
    """
    blue_spectrum = generate_blue()
    return 1.0 - blue_spectrum


# ============================================================
# 3. 主生成函數
# ============================================================

def generate_all_basis_spectra() -> dict:
    """
    生成所有 7 個 Smits 基底光譜
    
    Returns:
        basis: {
            'white': (31,),
            'cyan': (31,),
            'magenta': (31,),
            'yellow': (31,),
            'red': (31,),
            'green': (31,),
            'blue': (31,)
        }
    """
    basis = {
        'white': generate_white(),
        'cyan': generate_cyan(),
        'magenta': generate_magenta(),
        'yellow': generate_yellow(),
        'red': generate_red(),
        'green': generate_green(),
        'blue': generate_blue()
    }
    
    # 歸一化檢查（應已在 [0, 1]）
    for key, spectrum in basis.items():
        assert np.all((spectrum >= 0) & (spectrum <= 1)), \
            f"{key} spectrum out of range [0, 1]"
    
    return basis


# ============================================================
# 4. 驗證函數
# ============================================================

def verify_basis_spectra(basis: dict):
    """
    驗證基底光譜的物理合理性
    
    檢查項目：
    1. 值域 [0, 1]
    2. 互補色關係（cyan ≈ 1 - red）
    3. 主要反射波段正確
    """
    print("\n" + "="*70)
    print("  基底光譜驗證")
    print("="*70)
    
    # 1. 值域檢查
    for key, spectrum in basis.items():
        min_val = spectrum.min()
        max_val = spectrum.max()
        print(f"{key:10s}: 範圍 [{min_val:.3f}, {max_val:.3f}]", end="")
        
        if 0 <= min_val and max_val <= 1:
            print("  ✅")
        else:
            print("  ❌")
    
    # 2. 互補色關係檢查
    print("\n互補色關係驗證：")
    
    # cyan ≈ 1 - red
    diff_cyan = np.mean(np.abs(basis['cyan'] - (1.0 - basis['red'])))
    print(f"  cyan vs (1-red):    誤差 {diff_cyan:.4f}", end="")
    print("  ✅" if diff_cyan < 0.1 else "  ⚠️")
    
    # magenta ≈ 1 - green
    diff_magenta = np.mean(np.abs(basis['magenta'] - (1.0 - basis['green'])))
    print(f"  magenta vs (1-green): 誤差 {diff_magenta:.4f}", end="")
    print("  ✅" if diff_magenta < 0.1 else "  ⚠️")
    
    # yellow ≈ 1 - blue
    diff_yellow = np.mean(np.abs(basis['yellow'] - (1.0 - basis['blue'])))
    print(f"  yellow vs (1-blue):  誤差 {diff_yellow:.4f}", end="")
    print("  ✅" if diff_yellow < 0.1 else "  ⚠️")
    
    # 3. 主要反射波段檢查
    print("\n主要反射波段驗證：")
    
    # Red: 在 650nm 附近應為高值
    idx_red = np.argmin(np.abs(WAVELENGTHS - 650))
    print(f"  red[650nm]:   {basis['red'][idx_red]:.3f}", end="")
    print("  ✅" if basis['red'][idx_red] > 0.8 else "  ⚠️")
    
    # Green: 在 550nm 附近應為高值
    idx_green = np.argmin(np.abs(WAVELENGTHS - 550))
    print(f"  green[550nm]: {basis['green'][idx_green]:.3f}", end="")
    print("  ✅" if basis['green'][idx_green] > 0.8 else "  ⚠️")
    
    # Blue: 在 450nm 附近應為高值
    idx_blue = np.argmin(np.abs(WAVELENGTHS - 450))
    print(f"  blue[450nm]:  {basis['blue'][idx_blue]:.3f}", end="")
    print("  ✅" if basis['blue'][idx_blue] > 0.8 else "  ⚠️")
    
    print("="*70)


# ============================================================
# 5. 主程式
# ============================================================

def main():
    """主程式"""
    print("="*70)
    print("  Smits (1999) 基底光譜生成器")
    print("="*70)
    print(f"波長範圍: {WAVELENGTHS[0]:.0f} - {WAVELENGTHS[-1]:.0f} nm")
    print(f"波長數量: {N_WAVELENGTHS}")
    print(f"波長間隔: {WAVELENGTHS[1] - WAVELENGTHS[0]:.0f} nm")
    
    # 生成基底光譜
    print("\n生成基底光譜...")
    basis = generate_all_basis_spectra()
    print("✅ 生成完成")
    
    # 驗證
    verify_basis_spectra(basis)
    
    # 保存到 NPZ
    output_path = Path(__file__).parent.parent / "data" / "smits_basis_spectra.npz"
    output_path.parent.mkdir(exist_ok=True)
    
    print(f"\n保存至: {output_path}")
    
    # 添加波長陣列到輸出
    np.savez_compressed(
        output_path,
        wavelengths=WAVELENGTHS,
        white=basis['white'],
        cyan=basis['cyan'],
        magenta=basis['magenta'],
        yellow=basis['yellow'],
        red=basis['red'],
        green=basis['green'],
        blue=basis['blue']
    )
    
    # 檢查檔案大小
    file_size = output_path.stat().st_size
    print(f"檔案大小: {file_size / 1024:.2f} KB")
    print("✅ 保存完成")
    
    # 測試載入
    print("\n測試載入...")
    loaded = np.load(output_path)
    print(f"  包含鍵: {list(loaded.keys())}")
    print(f"  wavelengths 維度: {loaded['wavelengths'].shape}")
    print(f"  white 維度: {loaded['white'].shape}")
    print("✅ 載入測試通過")
    
    print("\n" + "="*70)
    print("  ✅ 所有步驟完成")
    print("="*70)


if __name__ == '__main__':
    main()
