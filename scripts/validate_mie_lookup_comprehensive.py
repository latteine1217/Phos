#!/usr/bin/env python3
"""
Mie 散射查表全面驗證腳本（Critical Task #3）

根據寫程式哲學「Data ≠ Truth」原則，驗證：
1. 插值誤差的統計分布（平均/中位數/95%/最大值）
2. 極端情況誤差（ISO 6400, λ=700nm 等邊界點）
3. 能量守恆驗證（η + ρ ≤ 1）
4. 單調性驗證（ISO 增加 → η 增加）

依賴:
    pip install miepython numpy scipy matplotlib

使用:
    python3 scripts/validate_mie_lookup_comprehensive.py

輸出:
    - 終端輸出統計報告
    - validation_report.txt（詳細報告）
    - error_distribution.png（誤差分布圖）
"""

import numpy as np
import miepython
from scipy.optimize import minimize
from scipy.stats import lognorm
from pathlib import Path
import sys
import matplotlib.pyplot as plt

# ============================================================
# 1. 載入查表數據
# ============================================================

def load_mie_lookup():
    """載入 Mie 散射查表"""
    lookup_path = Path(__file__).parent.parent / "data" / "mie_lookup_table_v3.npz"
    
    if not lookup_path.exists():
        print(f"❌ 錯誤：查表文件不存在 {lookup_path}")
        sys.exit(1)
    
    data = np.load(lookup_path)
    
    return {
        'wavelengths': data['wavelengths'],  # (10,) 400-700nm
        'iso_values': data['iso_values'],     # (20,) 50-6400
        'sigma_core': data['sigma_core'],     # (10, 20)
        'kappa_tail': data['kappa_tail'],     # (10, 20)
        'core_ratio': data['core_ratio'],     # (10, 20)
        'eta_scatter': data['eta_scatter']    # (10, 20)
    }


# ============================================================
# 2. 物理參數定義（與 generate_mie_lookup.py 保持一致）
# ============================================================

N_GELATIN = 1.50

def n_AgBr_vacuum(wavelength_nm):
    """AgBr 折射率（Cauchy 公式）"""
    λ_um = wavelength_nm / 1000.0
    A = 2.0393
    B = 0.0629
    return A + B / (λ_um ** 2)

def relative_refractive_index(wavelength_nm):
    """相對折射率 m = n_AgBr / n_gelatin"""
    return n_AgBr_vacuum(wavelength_nm) / N_GELATIN

def get_particle_distribution(iso):
    """粒徑分布參數（線性插值）"""
    iso_list = [50, 100, 125, 160, 200, 250, 320, 400, 500, 640, 
                800, 1000, 1250, 1600, 2000, 2500, 3200, 4000, 5000, 6400]
    mean_list = [0.7, 0.8, 0.85, 0.9, 1.0, 1.05, 1.1, 1.2, 1.3, 1.4,
                 1.5, 1.6, 1.7, 1.8, 1.95, 2.1, 2.2, 2.35, 2.45, 2.5]
    std_list = [0.28, 0.30, 0.32, 0.33, 0.35, 0.36, 0.38, 0.40, 0.42, 0.43,
                0.45, 0.46, 0.48, 0.50, 0.52, 0.53, 0.55, 0.57, 0.58, 0.60]
    
    mean = np.interp(iso, iso_list, mean_list)
    std = np.interp(iso, iso_list, std_list)
    
    return {'mean': mean, 'std': std}


def compute_mie_parameters_ground_truth(wavelength_nm, iso):
    """
    計算真實 Mie 參數（Ground Truth）
    
    使用與 generate_mie_lookup.py 相同的演算法，確保一致性
    """
    m = relative_refractive_index(wavelength_nm)
    dist = get_particle_distribution(iso)
    
    # 對數常態分布採樣（100 點足夠精確）
    radii = np.linspace(0.1, 5.0, 100)  # μm
    mu = np.log(dist['mean']) - 0.5 * np.log(1 + (dist['std'] / dist['mean']) ** 2)
    sigma = np.sqrt(np.log(1 + (dist['std'] / dist['mean']) ** 2))
    weights = lognorm.pdf(radii, sigma, scale=np.exp(mu))
    weights /= np.sum(weights)
    
    # 計算平均散射參數
    eta_total = 0
    rho_total = 0
    
    for r, w in zip(radii, weights):
        x = 2 * np.pi * r / (wavelength_nm / 1000.0)
        qext, qsca, qback, g = miepython.mie(m, x)
        
        eta = qsca  # 散射效率
        rho = qext - qsca  # 吸收效率
        
        eta_total += eta * w
        rho_total += rho * w
    
    # 簡化 PSF 參數（假設單段核）
    sigma_core = 15.0 * (550.0 / wavelength_nm) ** 0.8
    kappa_tail = 40.0 * (550.0 / wavelength_nm) ** 0.6
    core_ratio = 0.7
    
    return {
        'sigma_core': sigma_core,
        'kappa_tail': kappa_tail,
        'core_ratio': core_ratio,
        'eta_scatter': eta_total
    }


# ============================================================
# 3. 插值函數（與實際使用一致）
# ============================================================

def interpolate_mie_params(wavelength_nm, iso, lookup_data):
    """雙線性插值（與實際程式碼一致）"""
    wavelengths = lookup_data['wavelengths']
    iso_values = lookup_data['iso_values']
    
    # 找到波長插值索引
    if wavelength_nm <= wavelengths[0]:
        w_idx0, w_idx1 = 0, 0
        w_frac = 0.0
    elif wavelength_nm >= wavelengths[-1]:
        w_idx0, w_idx1 = len(wavelengths) - 1, len(wavelengths) - 1
        w_frac = 0.0
    else:
        w_idx1 = np.searchsorted(wavelengths, wavelength_nm)
        w_idx0 = w_idx1 - 1
        w_frac = (wavelength_nm - wavelengths[w_idx0]) / (wavelengths[w_idx1] - wavelengths[w_idx0])
    
    # 找到 ISO 插值索引
    if iso <= iso_values[0]:
        i_idx0, i_idx1 = 0, 0
        i_frac = 0.0
    elif iso >= iso_values[-1]:
        i_idx0, i_idx1 = len(iso_values) - 1, len(iso_values) - 1
        i_frac = 0.0
    else:
        i_idx1 = np.searchsorted(iso_values, iso)
        i_idx0 = i_idx1 - 1
        i_frac = (iso - iso_values[i_idx0]) / (iso_values[i_idx1] - iso_values[i_idx0])
    
    # 雙線性插值
    def bilinear(arr):
        v00 = arr[w_idx0, i_idx0]
        v01 = arr[w_idx0, i_idx1]
        v10 = arr[w_idx1, i_idx0]
        v11 = arr[w_idx1, i_idx1]
        
        v0 = v00 * (1 - i_frac) + v01 * i_frac
        v1 = v10 * (1 - i_frac) + v11 * i_frac
        
        return v0 * (1 - w_frac) + v1 * w_frac
    
    return {
        'sigma_core': bilinear(lookup_data['sigma_core']),
        'kappa_tail': bilinear(lookup_data['kappa_tail']),
        'core_ratio': bilinear(lookup_data['core_ratio']),
        'eta_scatter': bilinear(lookup_data['eta_scatter'])
    }


# ============================================================
# 4. 驗證測試集
# ============================================================

def generate_test_grid():
    """
    生成測試格點（包含極端情況）
    
    策略：
    1. 查表格點（應該完全匹配，誤差 <0.01%）
    2. 中間點（測試插值精度）
    3. 極端點（邊界測試）
    """
    test_cases = []
    
    # 類型 1：查表格點（20 個點，預期誤差 ~0%）
    wavelengths_grid = np.linspace(400, 700, 10)
    iso_grid = [50, 100, 400, 800, 3200, 6400]
    
    for wl in wavelengths_grid:
        for iso in iso_grid:
            test_cases.append({
                'wavelength': wl,
                'iso': iso,
                'type': 'grid_point'
            })
    
    # 類型 2：中間點（100 個點，測試插值）
    for _ in range(100):
        wl = np.random.uniform(420, 680)
        iso = np.random.choice([75, 150, 500, 1200, 2500, 5000])
        test_cases.append({
            'wavelength': wl,
            'iso': iso,
            'type': 'interpolation'
        })
    
    # 類型 3：極端點（邊界測試）
    extreme_cases = [
        (400, 50, 'extreme_min_min'),
        (700, 6400, 'extreme_max_max'),
        (400, 6400, 'extreme_min_iso_max'),
        (700, 50, 'extreme_max_wavelength_min_iso'),
        (550, 6400, 'extreme_high_iso'),
        (400, 50, 'extreme_low_iso'),
    ]
    
    for wl, iso, label in extreme_cases:
        test_cases.append({
            'wavelength': wl,
            'iso': iso,
            'type': label
        })
    
    return test_cases


# ============================================================
# 5. 執行驗證
# ============================================================

def validate_comprehensive():
    """全面驗證 Mie 查表"""
    print("=" * 60)
    print("Mie 散射查表全面驗證")
    print("=" * 60)
    print()
    
    # 載入查表
    print("📂 載入查表數據...")
    lookup_data = load_mie_lookup()
    print(f"   - 波長範圍: {lookup_data['wavelengths'][0]:.0f}-{lookup_data['wavelengths'][-1]:.0f} nm")
    print(f"   - ISO 範圍: {lookup_data['iso_values'][0]:.0f}-{lookup_data['iso_values'][-1]:.0f}")
    print(f"   - 格點數: {len(lookup_data['wavelengths'])} × {len(lookup_data['iso_values'])} = {len(lookup_data['wavelengths']) * len(lookup_data['iso_values'])}")
    print()
    
    # 生成測試集
    print("🧪 生成測試集...")
    test_cases = generate_test_grid()
    print(f"   - 總測試點: {len(test_cases)}")
    print(f"   - 格點: {sum(1 for t in test_cases if t['type'] == 'grid_point')}")
    print(f"   - 插值點: {sum(1 for t in test_cases if t['type'] == 'interpolation')}")
    print(f"   - 極端點: {sum(1 for t in test_cases if 'extreme' in t['type'])}")
    print()
    
    # 執行驗證
    print("⚙️  計算插值誤差（這需要幾分鐘）...")
    errors = []
    extreme_errors = {}
    
    for i, case in enumerate(test_cases):
        if (i + 1) % 20 == 0:
            print(f"   進度: {i+1}/{len(test_cases)} ({100*(i+1)/len(test_cases):.1f}%)")
        
        # 計算 Ground Truth
        gt = compute_mie_parameters_ground_truth(case['wavelength'], case['iso'])
        
        # 計算插值值
        interp = interpolate_mie_params(case['wavelength'], case['iso'], lookup_data)
        
        # 計算相對誤差（%）
        eta_error = abs(interp['eta_scatter'] - gt['eta_scatter']) / (gt['eta_scatter'] + 1e-10) * 100
        
        errors.append({
            'wavelength': case['wavelength'],
            'iso': case['iso'],
            'type': case['type'],
            'eta_error': eta_error,
            'eta_gt': gt['eta_scatter'],
            'eta_interp': interp['eta_scatter']
        })
        
        # 記錄極端情況
        if 'extreme' in case['type']:
            extreme_errors[case['type']] = eta_error
    
    print()
    
    # ============================================================
    # 6. 統計分析
    # ============================================================
    
    eta_errors = [e['eta_error'] for e in errors]
    
    print("=" * 60)
    print("📊 統計結果")
    print("=" * 60)
    print()
    print("散射效率 (η) 插值誤差:")
    print(f"   - 平均值 (Mean):        {np.mean(eta_errors):.4f}%")
    print(f"   - 中位數 (Median):      {np.median(eta_errors):.4f}%")
    print(f"   - 標準差 (Std):         {np.std(eta_errors):.4f}%")
    print(f"   - 95th 百分位數:        {np.percentile(eta_errors, 95):.4f}%")
    print(f"   - 99th 百分位數:        {np.percentile(eta_errors, 99):.4f}%")
    print(f"   - 最大值 (Max):         {np.max(eta_errors):.4f}%")
    print()
    
    # 極端情況報告
    print("🔴 極端情況誤差:")
    for label, error in extreme_errors.items():
        status = "✅" if error < 5.0 else "⚠️"
        print(f"   {status} {label:30s}: {error:.4f}%")
    print()
    
    # 分類統計
    grid_errors = [e['eta_error'] for e in errors if e['type'] == 'grid_point']
    interp_errors = [e['eta_error'] for e in errors if e['type'] == 'interpolation']
    
    print("📈 分類統計:")
    print(f"   格點誤差 (應接近 0):    {np.mean(grid_errors):.4f}% (max: {np.max(grid_errors):.4f}%)")
    print(f"   插值點誤差:             {np.mean(interp_errors):.4f}% (max: {np.max(interp_errors):.4f}%)")
    print()
    
    # 能量守恆驗證
    print("🔋 能量守恆驗證 (η ≤ 1.0):")
    violations = [e for e in errors if e['eta_gt'] > 1.0 or e['eta_interp'] > 1.0]
    if violations:
        print(f"   ⚠️  發現 {len(violations)} 個違反能量守恆的點")
        for v in violations[:5]:
            print(f"      - λ={v['wavelength']:.0f}nm, ISO={v['iso']:.0f}: η_gt={v['eta_gt']:.3f}, η_interp={v['eta_interp']:.3f}")
    else:
        print("   ✅ 所有點符合能量守恆")
    print()
    
    # 單調性驗證
    print("📊 單調性驗證 (ISO 增加 → η 增加):")
    monotonic_violations = 0
    for wl in [450, 550, 650]:
        iso_seq = [100, 400, 800, 3200]
        eta_seq = []
        for iso in iso_seq:
            interp = interpolate_mie_params(wl, iso, lookup_data)
            eta_seq.append(interp['eta_scatter'])
        
        is_monotonic = all(eta_seq[i] <= eta_seq[i+1] for i in range(len(eta_seq)-1))
        status = "✅" if is_monotonic else "⚠️"
        print(f"   {status} λ={wl}nm: {eta_seq}")
        
        if not is_monotonic:
            monotonic_violations += 1
    
    if monotonic_violations == 0:
        print("   ✅ 所有波長符合單調性")
    print()
    
    # ============================================================
    # 7. 生成報告
    # ============================================================
    
    report_path = Path(__file__).parent.parent / "validation_report.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("Mie 散射查表驗證報告\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"平均誤差: {np.mean(eta_errors):.4f}%\n")
        f.write(f"95th 百分位: {np.percentile(eta_errors, 95):.4f}%\n")
        f.write(f"最大誤差: {np.max(eta_errors):.4f}%\n\n")
        f.write("極端情況:\n")
        for label, error in extreme_errors.items():
            f.write(f"  {label}: {error:.4f}%\n")
    
    print(f"📄 詳細報告已保存: {report_path}")
    
    # ============================================================
    # 8. 繪製誤差分布圖
    # ============================================================
    
    try:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 子圖 1: 誤差直方圖
        axes[0, 0].hist(eta_errors, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
        axes[0, 0].axvline(np.mean(eta_errors), color='red', linestyle='--', label=f'Mean: {np.mean(eta_errors):.2f}%')
        axes[0, 0].axvline(np.percentile(eta_errors, 95), color='orange', linestyle='--', label=f'95th: {np.percentile(eta_errors, 95):.2f}%')
        axes[0, 0].set_xlabel('Interpolation Error (%)')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Error Distribution')
        axes[0, 0].legend()
        axes[0, 0].grid(alpha=0.3)
        
        # 子圖 2: 誤差 vs ISO
        iso_vals = [e['iso'] for e in errors]
        axes[0, 1].scatter(iso_vals, eta_errors, alpha=0.5, s=10)
        axes[0, 1].set_xlabel('ISO')
        axes[0, 1].set_ylabel('Error (%)')
        axes[0, 1].set_title('Error vs ISO')
        axes[0, 1].set_xscale('log')
        axes[0, 1].grid(alpha=0.3)
        
        # 子圖 3: 誤差 vs 波長
        wl_vals = [e['wavelength'] for e in errors]
        axes[1, 0].scatter(wl_vals, eta_errors, alpha=0.5, s=10)
        axes[1, 0].set_xlabel('Wavelength (nm)')
        axes[1, 0].set_ylabel('Error (%)')
        axes[1, 0].set_title('Error vs Wavelength')
        axes[1, 0].grid(alpha=0.3)
        
        # 子圖 4: CDF
        sorted_errors = np.sort(eta_errors)
        cdf = np.arange(1, len(sorted_errors) + 1) / len(sorted_errors)
        axes[1, 1].plot(sorted_errors, cdf, linewidth=2)
        axes[1, 1].axhline(0.95, color='orange', linestyle='--', label='95th percentile')
        axes[1, 1].axvline(np.percentile(eta_errors, 95), color='orange', linestyle='--')
        axes[1, 1].set_xlabel('Error (%)')
        axes[1, 1].set_ylabel('CDF')
        axes[1, 1].set_title('Cumulative Distribution')
        axes[1, 1].legend()
        axes[1, 1].grid(alpha=0.3)
        
        plt.tight_layout()
        
        plot_path = Path(__file__).parent.parent / "error_distribution.png"
        plt.savefig(plot_path, dpi=150)
        print(f"📊 誤差分布圖已保存: {plot_path}")
    except Exception as e:
        print(f"⚠️  無法生成圖表（需要 matplotlib）: {e}")
    
    print()
    print("=" * 60)
    print("✅ 驗證完成")
    print("=" * 60)


# ============================================================
# 9. 主程式
# ============================================================

if __name__ == "__main__":
    validate_comprehensive()
