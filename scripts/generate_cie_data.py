"""
CIE 1931 色彩匹配函數生成腳本 (Phase 4.3)

功能：
- 生成精確的 CIE 1931 2° 標準觀察者色彩匹配函數
- 插值到 31 個波長點（380-780nm, 每 13nm）
- 輸出為 NPZ 檔案（data/cie_1931_31points.npz）

數據來源：
- CIE 1931 2° 標準觀察者（CIE 15:2004）
- 使用三次樣條插值（scipy.interpolate）

參考文獻：
- CIE. "Colorimetry." CIE 15:2004, 3rd edition. 2004.
- CVRL (Color & Vision Research Laboratory) Database

Version: 0.4.0
Date: 2025-12-20
"""

import numpy as np
from scipy import interpolate
from pathlib import Path
import sys

# 添加父目錄到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ============================================================
# 1. CIE 1931 2° 標準觀察者原始數據（380-780nm, 每 5nm）
# ============================================================

# 來源：CIE 15:2004, Table T.1
# 波長範圍：380-780nm, 每 5nm, 共 81 個點

CIE_WAVELENGTHS_ORIGINAL = np.arange(380, 781, 5)  # (81,)

# x̄(λ) - X 色彩匹配函數 (81 points: 380-780nm, every 5nm)
CIE_X_BAR_ORIGINAL = np.array([
    0.0014, 0.0022, 0.0042, 0.0076, 0.0143, 0.0232, 0.0435, 0.0776, 0.1344, 0.2148,
    0.2839, 0.3285, 0.3483, 0.3481, 0.3362, 0.3187, 0.2908, 0.2511, 0.1954, 0.1421,
    0.0956, 0.0580, 0.0320, 0.0147, 0.0049, 0.0024, 0.0093, 0.0291, 0.0633, 0.1096,
    0.1655, 0.2257, 0.2904, 0.3597, 0.4334, 0.5121, 0.5945, 0.6784, 0.7621, 0.8425,
    0.9163, 0.9786, 1.0263, 1.0567, 1.0622, 1.0456, 1.0026, 0.9384, 0.8544, 0.7514,
    0.6424, 0.5419, 0.4479, 0.3608, 0.2835, 0.2187, 0.1649, 0.1212, 0.0874, 0.0636,
    0.0468, 0.0329, 0.0227, 0.0158, 0.0114, 0.0081, 0.0058, 0.0041, 0.0029, 0.0020,
    0.0014, 0.0010, 0.0007, 0.0005, 0.0003, 0.0002, 0.0002, 0.0001, 0.0001, 0.0001,
    0.0000
], dtype=np.float64)

# ȳ(λ) - Y 色彩匹配函數（對應亮度）(81 points)
CIE_Y_BAR_ORIGINAL = np.array([
    0.0000, 0.0001, 0.0001, 0.0002, 0.0004, 0.0006, 0.0012, 0.0022, 0.0040, 0.0073,
    0.0116, 0.0168, 0.0230, 0.0298, 0.0380, 0.0480, 0.0600, 0.0739, 0.0910, 0.1126,
    0.1390, 0.1693, 0.2080, 0.2586, 0.3230, 0.4073, 0.5030, 0.6082, 0.7100, 0.7932,
    0.8620, 0.9149, 0.9540, 0.9803, 0.9950, 1.0002, 0.9950, 0.9786, 0.9520, 0.9154,
    0.8700, 0.8163, 0.7570, 0.6949, 0.6310, 0.5668, 0.5030, 0.4412, 0.3810, 0.3210,
    0.2650, 0.2170, 0.1750, 0.1382, 0.1070, 0.0816, 0.0610, 0.0446, 0.0320, 0.0232,
    0.0170, 0.0119, 0.0082, 0.0057, 0.0041, 0.0029, 0.0021, 0.0015, 0.0010, 0.0007,
    0.0005, 0.0004, 0.0002, 0.0002, 0.0001, 0.0001, 0.0001, 0.0000, 0.0000, 0.0000,
    0.0000
], dtype=np.float64)

# z̄(λ) - Z 色彩匹配函數 (81 points)
CIE_Z_BAR_ORIGINAL = np.array([
    0.0065, 0.0105, 0.0201, 0.0362, 0.0679, 0.1102, 0.2074, 0.3713, 0.6456, 1.0391,
    1.3856, 1.6230, 1.7471, 1.7826, 1.7721, 1.7441, 1.6692, 1.5281, 1.2876, 1.0419,
    0.8130, 0.6162, 0.4652, 0.3533, 0.2720, 0.2123, 0.1582, 0.1117, 0.0782, 0.0573,
    0.0422, 0.0298, 0.0203, 0.0134, 0.0087, 0.0057, 0.0039, 0.0027, 0.0021, 0.0018,
    0.0017, 0.0014, 0.0011, 0.0010, 0.0008, 0.0006, 0.0003, 0.0002, 0.0002, 0.0001,
    0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
    0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
    0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000,
    0.0000
], dtype=np.float64)


# ============================================================
# 2. 插值到 31 個波長點
# ============================================================

def interpolate_cie_to_31_points():
    """
    將 CIE 1931 數據插值到 31 個波長點（380-780nm, 每 13nm）
    
    使用三次樣條插值（cubic spline）
    
    Returns:
        wavelengths: (31,), 目標波長
        x_bar: (31,), 插值後的 x̄(λ)
        y_bar: (31,), 插值後的 ȳ(λ)
        z_bar: (31,), 插值後的z̄(λ)
    """
    # 目標波長（380-780nm, 每 13nm）
    target_wavelengths = np.arange(380, 781, 13, dtype=np.float32)
    
    # 三次樣條插值
    interp_x = interpolate.CubicSpline(CIE_WAVELENGTHS_ORIGINAL, CIE_X_BAR_ORIGINAL)
    interp_y = interpolate.CubicSpline(CIE_WAVELENGTHS_ORIGINAL, CIE_Y_BAR_ORIGINAL)
    interp_z = interpolate.CubicSpline(CIE_WAVELENGTHS_ORIGINAL, CIE_Z_BAR_ORIGINAL)
    
    # 插值到目標波長
    x_bar = interp_x(target_wavelengths).astype(np.float32)
    y_bar = interp_y(target_wavelengths).astype(np.float32)
    z_bar = interp_z(target_wavelengths).astype(np.float32)
    
    # 確保非負（插值可能產生微小負值）
    x_bar = np.maximum(x_bar, 0)
    y_bar = np.maximum(y_bar, 0)
    z_bar = np.maximum(z_bar, 0)
    
    return target_wavelengths, x_bar, y_bar, z_bar


# ============================================================
# 3. 驗證函數
# ============================================================

def verify_cie_data(wavelengths, x_bar, y_bar, z_bar):
    """
    驗證 CIE 數據的物理合理性
    
    檢查項目：
    1. 非負性
    2. 峰值位置（x̄: ~600nm, ȳ: ~555nm, z̄: ~445nm）
    3. 積分總量（應接近原始數據）
    """
    print("\n" + "="*70)
    print("  CIE 1931 數據驗證")
    print("="*70)
    
    # 1. 非負性檢查
    print("\n非負性檢查：")
    all_positive = True
    for name, data in [('x̄', x_bar), ('ȳ', y_bar), ('z̄', z_bar)]:
        min_val = data.min()
        print(f"  {name}: min = {min_val:.6f}", end="")
        if min_val >= 0:
            print("  ✅")
        else:
            print("  ❌")
            all_positive = False
    
    # 2. 峰值位置檢查
    print("\n峰值位置驗證：")
    
    idx_x_max = np.argmax(x_bar)
    lambda_x_max = wavelengths[idx_x_max]
    print(f"  x̄ 峰值: {lambda_x_max:.0f}nm (期望 ~600nm)", end="")
    print("  ✅" if 590 <= lambda_x_max <= 610 else "  ⚠️")
    
    idx_y_max = np.argmax(y_bar)
    lambda_y_max = wavelengths[idx_y_max]
    print(f"  ȳ 峰值: {lambda_y_max:.0f}nm (期望 ~555nm)", end="")
    print("  ✅" if 545 <= lambda_y_max <= 565 else "  ⚠️")
    
    idx_z_max = np.argmax(z_bar)
    lambda_z_max = wavelengths[idx_z_max]
    print(f"  z̄ 峰值: {lambda_z_max:.0f}nm (期望 ~445nm)", end="")
    print("  ✅" if 435 <= lambda_z_max <= 455 else "  ⚠️")
    
    # 3. 峰值大小檢查
    print("\n峰值大小驗證：")
    print(f"  x̄ 最大值: {x_bar.max():.4f} (期望 ~1.06)")
    print(f"  ȳ 最大值: {y_bar.max():.4f} (期望 ~1.00)")
    print(f"  z̄ 最大值: {z_bar.max():.4f} (期望 ~1.78)")
    
    # 4. 特定波長值檢查（與原始數據對比）
    print("\n特定波長值對比（原始 vs 插值）：")
    
    test_wavelengths = [445, 510, 555, 610, 650]
    for lambda_test in test_wavelengths:
        # 找到最接近的目標波長索引
        idx_target = np.argmin(np.abs(wavelengths - lambda_test))
        lambda_actual = wavelengths[idx_target]
        
        # 找到原始數據中的索引
        idx_orig = np.argmin(np.abs(CIE_WAVELENGTHS_ORIGINAL - lambda_test))
        
        # 對比
        x_orig = CIE_X_BAR_ORIGINAL[idx_orig]
        x_interp = x_bar[idx_target]
        
        y_orig = CIE_Y_BAR_ORIGINAL[idx_orig]
        y_interp = y_bar[idx_target]
        
        error_x = abs(x_interp - x_orig) / (x_orig + 1e-8) * 100
        error_y = abs(y_interp - y_orig) / (y_orig + 1e-8) * 100
        
        print(f"  λ={lambda_actual:.0f}nm:")
        print(f"    x̄: {x_orig:.4f} → {x_interp:.4f} (誤差 {error_x:.1f}%)")
        print(f"    ȳ: {y_orig:.4f} → {y_interp:.4f} (誤差 {error_y:.1f}%)")
    
    print("="*70)
    
    return all_positive


# ============================================================
# 4. 主程式
# ============================================================

def main():
    """主程式"""
    print("="*70)
    print("  CIE 1931 色彩匹配函數生成器")
    print("="*70)
    print(f"原始數據: {len(CIE_WAVELENGTHS_ORIGINAL)} 點 (380-780nm, 每 5nm)")
    print(f"目標數據: 31 點 (380-780nm, 每 13nm)")
    print(f"插值方法: 三次樣條插值")
    
    # 插值
    print("\n插值中...")
    wavelengths, x_bar, y_bar, z_bar = interpolate_cie_to_31_points()
    print("✅ 插值完成")
    
    # 驗證
    verify_cie_data(wavelengths, x_bar, y_bar, z_bar)
    
    # 保存到 NPZ
    output_path = Path(__file__).parent.parent / "data" / "cie_1931_31points.npz"
    output_path.parent.mkdir(exist_ok=True)
    
    print(f"\n保存至: {output_path}")
    
    np.savez_compressed(
        output_path,
        wavelengths=wavelengths,
        x_bar=x_bar,
        y_bar=y_bar,
        z_bar=z_bar
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
    print(f"  x_bar 維度: {loaded['x_bar'].shape}")
    print(f"  y_bar 維度: {loaded['y_bar'].shape}")
    print(f"  z_bar 維度: {loaded['z_bar'].shape}")
    print("✅ 載入測試通過")
    
    print("\n" + "="*70)
    print("  ✅ 所有步驟完成")
    print("="*70)


if __name__ == '__main__':
    main()
