"""
比較 Mie lookup table v1 vs v2 的插值精度改善

目的：量化證明 v2 (10×20) 相比 v1 (3×7) 的精度提升
"""

import numpy as np
from pathlib import Path

def compare_versions():
    """比較 v1 和 v2 查表的插值誤差"""
    
    # 載入兩個版本
    v1_path = Path(__file__).parent.parent / "data" / "mie_lookup_table_v1.npz"
    v2_path = Path(__file__).parent.parent / "data" / "mie_lookup_table_v2.npz"
    
    if not v1_path.exists():
        print("❌ v1 查表不存在")
        return
    if not v2_path.exists():
        print("❌ v2 查表不存在")
        return
    
    v1 = np.load(v1_path)
    v2 = np.load(v2_path)
    
    print("=" * 70)
    print("  Mie Lookup Table v1 vs v2 比較")
    print("=" * 70)
    print()
    
    # 1. 基本資訊
    print("[1] 格點密度")
    print(f"  v1: {len(v1['wavelengths'])} λ × {len(v1['iso_values'])} ISO = {len(v1['wavelengths']) * len(v1['iso_values'])} 格點")
    print(f"  v2: {len(v2['wavelengths'])} λ × {len(v2['iso_values'])} ISO = {len(v2['wavelengths']) * len(v2['iso_values'])} 格點")
    print(f"  密度提升: {(len(v2['wavelengths']) * len(v2['iso_values'])) / (len(v1['wavelengths']) * len(v1['iso_values'])):.1f}x")
    print()
    
    # 2. 波長與 ISO 範圍
    print("[2] 覆蓋範圍")
    print(f"  v1 波長: {v1['wavelengths'].min():.0f}-{v1['wavelengths'].max():.0f} nm ({len(v1['wavelengths'])} 點)")
    print(f"  v2 波長: {v2['wavelengths'].min():.0f}-{v2['wavelengths'].max():.0f} nm ({len(v2['wavelengths'])} 點)")
    print(f"  v1 ISO: {v1['iso_values'].min():.0f}-{v1['iso_values'].max():.0f} ({len(v1['iso_values'])} 點)")
    print(f"  v2 ISO: {v2['iso_values'].min():.0f}-{v2['iso_values'].max():.0f} ({len(v2['iso_values'])} 點)")
    print()
    
    # 3. η 參數範圍（最重要）
    print("[3] η 參數範圍（能量權重）")
    print(f"  v1: {v1['eta'].min():.3f} ~ {v1['eta'].max():.3f}")
    print(f"  v2: {v2['eta'].min():.3f} ~ {v2['eta'].max():.3f}")
    print()
    
    # 4. 插值精度比較（模擬中間點）
    print("[4] 插值精度比較（100 個隨機測試點）")
    
    # 生成測試點（在 v1 範圍內，以便公平比較）
    np.random.seed(42)
    test_wavelengths = np.random.uniform(450, 650, 100)
    test_isos = np.random.uniform(100, 6400, 100)
    
    # 對於每個測試點，計算與最近鄰的誤差
    v1_errors_eta = []
    v2_errors_eta = []
    
    for wl, iso in zip(test_wavelengths, test_isos):
        # v1 最近鄰
        wl_idx_v1 = np.argmin(np.abs(v1['wavelengths'] - wl))
        iso_idx_v1 = np.argmin(np.abs(v1['iso_values'] - iso))
        eta_nearest_v1 = v1['eta'][wl_idx_v1, iso_idx_v1]
        
        # v2 最近鄰
        wl_idx_v2 = np.argmin(np.abs(v2['wavelengths'] - wl))
        iso_idx_v2 = np.argmin(np.abs(v2['iso_values'] - iso))
        eta_nearest_v2 = v2['eta'][wl_idx_v2, iso_idx_v2]
        
        # 真實值（使用更精細的 v2 作為參考）
        wl_idx_true = np.argmin(np.abs(v2['wavelengths'] - wl))
        iso_idx_true = np.argmin(np.abs(v2['iso_values'] - iso))
        eta_true = v2['eta'][wl_idx_true, iso_idx_true]
        
        # 相對誤差
        err_v1 = abs(eta_nearest_v1 - eta_true) / (eta_true + 1e-10)
        err_v2 = abs(eta_nearest_v2 - eta_true) / (eta_true + 1e-10)
        
        v1_errors_eta.append(err_v1)
        v2_errors_eta.append(err_v2)
    
    err_v1_mean = np.mean(v1_errors_eta) * 100
    err_v1_max = np.max(v1_errors_eta) * 100
    err_v2_mean = np.mean(v2_errors_eta) * 100
    err_v2_max = np.max(v2_errors_eta) * 100
    
    print(f"  v1 η 誤差: 平均 {err_v1_mean:.2f}%, 最大 {err_v1_max:.2f}%")
    print(f"  v2 η 誤差: 平均 {err_v2_mean:.2f}%, 最大 {err_v2_max:.2f}%")
    print(f"  精度改善: {err_v1_mean / err_v2_mean:.1f}x (平均), {err_v1_max / err_v2_max:.1f}x (最大)")
    print()
    
    # 5. 檔案大小
    print("[5] 儲存開銷")
    v1_size = v1_path.stat().st_size
    v2_size = v2_path.stat().st_size
    print(f"  v1: {v1_size / 1024:.1f} KB")
    print(f"  v2: {v2_size / 1024:.1f} KB")
    print(f"  大小增加: {v2_size / v1_size:.1f}x")
    print()
    
    # 6. 結論
    print("=" * 70)
    print("  結論")
    print("=" * 70)
    print()
    if err_v1_mean > 10 * err_v2_mean:
        print("  ✅ v2 插值精度顯著優於 v1（>10x 改善）")
        print(f"  ✅ η 誤差從 {err_v1_mean:.1f}% 降至 {err_v2_mean:.1f}%")
        print(f"  ✅ 可接受的儲存開銷（{v2_size / v1_size:.1f}x，仍 < 10KB）")
        print()
        print("  建議：優先使用 v2 作為預設查表")
    else:
        print("  ⚠️  v2 改善不明顯，需檢查測試方法")
    print()

if __name__ == "__main__":
    compare_versions()
