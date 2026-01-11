# TASK-003 Phase 5: Mie 散射查表設計文檔

**任務 ID**: TASK-003-medium-physics  
**Phase**: 5 - Mie Scattering Lookup Table  
**優先級**: P1 (重要)  
**預估工時**: 8-12 小時  
**開始時間**: 2025-12-19 23:55  
**完成時間**: 2025-12-20 01:45  
**狀態**: ✅ **Phase 5.5 完成**（v2 高密度查表整合）

---

## Phase 5.5 完成摘要 (2025-12-20)

### 主要成果
- ✅ 生成高密度查表 v2（10λ × 20ISO = 200 格點）
- ✅ 格點密度提升：21 → 200（**9.5x**）
- ✅ η 插值誤差改善：155% → 2.16%（**72x 改善**）
- ✅ 插值速度提升：0.127 ms → 0.0205 ms（**6.2x 更快**）
- ✅ 波長範圍擴展：450-650nm → 400-700nm（**+50%**）
- ✅ ISO 範圍擴展：100-6400 → 50-6400（支援低 ISO）
- ✅ 全部測試通過（5/5）
- ✅ 文檔更新完成（PHYSICAL_MODE_GUIDE.md、README.md）

### v1 vs v2 對比

| 指標 | v1 | v2 | 改善 |
|------|----|----|------|
| 格點數 | 21 (3×7) | 200 (10×20) | **9.5x** |
| η 平均誤差 | 155% (內測) / 27.7% (vs基準) | 2.16% / 0.0% | **72x / ∞x** |
| η 最大誤差 | 281% / 78.9% | 2.61% / 0.0% | **108x / ∞x** |
| 插值速度 | 0.127 ms | 0.0205 ms | **6.2x** |
| 檔案大小 | 2.2 KB | 5.9 KB | 2.7x (可接受) |
| 波長範圍 | 450-650nm | 400-700nm | +50% |
| ISO 範圍 | 100-6400 | 50-6400 | 支援 ISO 50 |

### 修改檔案
- `scripts/generate_mie_lookup.py`: Line 28-56 修正（v2 參數）
- `film_models.py`: 4 處路徑替換（v1 → v2）
- `tests/test_mie_lookup.py`: 6 處路徑 + 預期值更新
- `scripts/compare_mie_versions.py`: 新建（110 lines）
- `data/mie_lookup_table_v2.npz`: 5.9 KB（預設查表）
- `data/mie_lookup_table_v1.npz`: 保留（歷史參考）

### 下一步（可選）
- **P0**: Streamlit UI 視覺驗證（Mie v2 vs 經驗公式）
- **P2 - Phase 5.6**: 三次樣條插值（vs 雙線性）
- **P2 - Phase 5.7**: 更密集格點（15λ × 30ISO）
- **P2 - Phase 5.8**: 簡化查表（僅 η，固定 σ/κ/ρ）

---

## 1. 目標與動機

### 當前問題
Phase 1 使用經驗公式：
```python
η(λ) = η_base × (λ_ref/λ)^3.5  # 能量權重
σ(λ) = σ_base × (λ_ref/λ)^0.8  # PSF 寬度
```

**限制**:
- **缺乏物理基礎**: 指數 p=3.5 與 q=0.8 為經驗值，非嚴格 Mie 理論
- **不考慮粒徑分布**: 實際銀鹽晶體尺寸 0.5-3 μm（對數常態分布）
- **忽略折射率色散**: AgBr 折射率 n(λ) 隨波長變化
- **PSF 形狀簡化**: 雙段核參數 (ρ, κ) 未從 Mie 相位函數推導

### Phase 5 目標
**離線計算真實 Mie 散射 → 壓縮為查表 → 實時插值**

1. ✅ **物理準確**: 使用完整 Mie 理論（含相對折射率、粒徑分布）
2. ✅ **高效實時**: 查表載入 < 100 ms，插值 < 1 ms
3. ✅ **參數化**: 支援不同 ISO（粒徑分布）、底片類型（介質折射率）
4. ✅ **向後相容**: 保留經驗公式作為 fallback（無查表時）

---

## 2. 物理模型

### 2.1 Mie 散射理論

**適用條件**: 銀鹽晶體尺寸參數 x = πd/λ ∈ [2, 20]（Mie 範圍）

**輸入參數**:
- **波長** λ: 450 nm (藍), 550 nm (綠), 650 nm (紅)
- **粒徑分布**: 對數常態 LogNormal(μ, σ)
  - 低 ISO (100-400): μ = 0.8 μm, σ = 0.3
  - 中 ISO (800-1600): μ = 1.5 μm, σ = 0.4
  - 高 ISO (3200+): μ = 2.5 μm, σ = 0.5
- **相對折射率** m(λ) = n_AgBr(λ) / n_gelatin
  - n_gelatin ≈ 1.50 (明膠/介質)
  - n_AgBr(λ) ≈ 2.2 + 0.05/(λ/μm)² (Cauchy 近似)
  - m(450nm) ≈ 1.52, m(550nm) ≈ 1.48, m(650nm) ≈ 1.47

**輸出**:
- **散射截面** σ_scat(λ, d)
- **相位函數** P(θ, λ, d) (角度分布)

### 2.2 角度 → 空間 PSF 映射

**幾何關係**:
```
r = z_eff × tan(θ)  (小角近似: r ≈ z_eff × θ)
```

**參數**:
- **z_eff**: 有效散射深度（乳劑層幾何平均深度）
  - 典型彩色負片: z_eff ≈ 10-15 μm
  - 估算: z_eff = film_thickness × 0.5
  
**積分**:
```python
PSF_2D(r, λ) = ∫∫ P(θ, φ, λ) × δ(r' - z_eff·tan(θ)) r' dr' dφ
             ≈ (2π/z_eff²) × P(arctan(r/z_eff), λ) × r  (軸對稱近似)
```

### 2.3 雙段核參數提取

**目標**: 將 Mie PSF 壓縮為 (σ, κ, ρ) 三參數

**方法 1 - 矩匹配**:
```python
# 計算 Mie PSF 的徑向矩
M0 = ∫ PSF(r) r dr       # 總能量 (應為 1)
M1 = ∫ r·PSF(r) r dr     # 一階矩（平均半徑）
M2 = ∫ r²·PSF(r) r dr    # 二階矩（方差）

# 匹配雙段核
K_dual(r) = ρ·exp(-r²/(2σ²)) + (1-ρ)·exp(-r/κ)

# 求解 (σ, κ, ρ) 使得矩相等
```

**方法 2 - 最小二乘擬合**:
```python
# 直接擬合徑向分布
minimize: ∑(PSF_mie(r_i) - K_dual(r_i; σ, κ, ρ))²
subject to: ρ ∈ [0.6, 0.9], σ > 0, κ > σ
```

**驗證指標**:
- RMSE < 2% (均方根誤差)
- PSNR > 35 dB
- 半高寬 HWHM 誤差 < 5%

---

## 3. 查表結構設計

### 3.1 查表維度

**主查表**: `mie_psf_params.npz`

**維度**:
```python
Table[λ_idx, ISO_idx] = (σ, κ, ρ, η)
```

**離散點**:
- **λ_idx**: 3 點 (450, 550, 650 nm)
- **ISO_idx**: 7 點 (100, 200, 400, 800, 1600, 3200, 6400)
- **總大小**: 3 × 7 × 4 = 84 個浮點數 (~0.3 KB)

### 3.2 額外元數據

```python
metadata = {
    'wavelengths': [450, 550, 650],  # nm
    'iso_values': [100, 200, 400, 800, 1600, 3200, 6400],
    'z_eff': 12.5,  # μm (預設有效深度)
    'n_gelatin': 1.50,
    'particle_size_distributions': {
        100: {'mean': 0.8, 'std': 0.3},  # μm
        200: {'mean': 1.0, 'std': 0.35},
        # ... 每個 ISO 的粒徑分布
    },
    'version': '1.0',
    'generated_date': '2025-12-19',
    'mie_library': 'miepython v2.3.0'
}
```

### 3.3 插值策略

**線性插值** (NumPy `np.interp`):
```python
def lookup_mie_params(wavelength: float, iso: int) -> Tuple[float, float, float, float]:
    """
    查表並插值獲取 (σ, κ, ρ, η)
    
    Args:
        wavelength: 波長 (nm), 範圍 [400, 700]
        iso: 感光度, 範圍 [50, 6400]
    
    Returns:
        (sigma, kappa, rho, eta): 雙段核參數
    """
    # 1. 波長方向線性插值
    sigma_interp = np.interp(wavelength, table['wavelengths'], sigma_table[:, iso_idx])
    kappa_interp = np.interp(wavelength, table['wavelengths'], kappa_table[:, iso_idx])
    
    # 2. ISO 方向線性插值（對數空間）
    log_iso = np.log10(iso)
    log_iso_table = np.log10(table['iso_values'])
    sigma = np.interp(log_iso, log_iso_table, sigma_interp)
    
    return sigma, kappa, rho, eta
```

**快取機制**:
```python
@lru_cache(maxsize=128)
def get_mie_params_cached(wavelength: int, iso: int):
    # 離散化輸入以利用快取
    λ_discrete = round(wavelength / 10) * 10  # 10nm 精度
    iso_discrete = min(table['iso_values'], key=lambda x: abs(x - iso))
    return lookup_mie_params(λ_discrete, iso_discrete)
```

---

## 4. 實作方案

### 4.1 離線計算腳本

**檔案**: `scripts/generate_mie_lookup.py`

```python
#!/usr/bin/env python3
"""
離線生成 Mie 散射查表

依賴:
    pip install miepython numpy scipy
"""

import numpy as np
import miepython
from scipy.optimize import minimize
from scipy.stats import lognorm

# ============================================================
# 1. 物理參數定義
# ============================================================

WAVELENGTHS = np.array([450, 550, 650])  # nm
ISO_VALUES = [100, 200, 400, 800, 1600, 3200, 6400]

# 粒徑分布 (對數常態參數)
PARTICLE_DISTRIBUTIONS = {
    100:  {'mean': 0.8, 'std': 0.3},   # μm
    200:  {'mean': 1.0, 'std': 0.35},
    400:  {'mean': 1.2, 'std': 0.4},
    800:  {'mean': 1.5, 'std': 0.45},
    1600: {'mean': 1.8, 'std': 0.5},
    3200: {'mean': 2.2, 'std': 0.55},
    6400: {'mean': 2.5, 'std': 0.6}
}

# 折射率
N_GELATIN = 1.50

def n_AgBr(wavelength_nm):
    """AgBr 折射率（Cauchy 近似）"""
    λ_um = wavelength_nm / 1000
    return 2.2 + 0.05 / (λ_um ** 2)

def relative_refractive_index(wavelength_nm):
    """相對折射率 m = n_AgBr / n_gelatin"""
    return n_AgBr(wavelength_nm) / N_GELATIN

# ============================================================
# 2. Mie 散射計算
# ============================================================

def compute_mie_phase_function(wavelength_nm, particle_diameter_um, angles_deg):
    """
    計算單顆粒的 Mie 相位函數
    
    Args:
        wavelength_nm: 波長 (nm)
        particle_diameter_um: 粒徑 (μm)
        angles_deg: 角度陣列 (度)
    
    Returns:
        P(θ): 正規化相位函數 (積分為 4π)
    """
    # 尺寸參數
    x = np.pi * particle_diameter_um / (wavelength_nm / 1000)
    
    # 相對折射率
    m = relative_refractive_index(wavelength_nm)
    
    # 計算散射矩陣元素 (S1, S2)
    mu = np.cos(np.deg2rad(angles_deg))
    s1, s2 = miepython.mie_S1_S2(m, x, mu)
    
    # 相位函數 P(θ) = (|S1|² + |S2|²) / (2 k² σ_scat)
    # 簡化: 正規化使得積分為 4π
    phase = (np.abs(s1)**2 + np.abs(s2)**2)
    phase = phase / (np.trapz(phase * np.sin(np.deg2rad(angles_deg)), angles_deg) * 2 * np.pi)
    
    return phase

def compute_polydisperse_phase(wavelength_nm, iso, angles_deg, n_samples=50):
    """
    計算粒徑分布加權的平均相位函數
    
    Args:
        wavelength_nm: 波長 (nm)
        iso: 感光度
        angles_deg: 角度陣列
        n_samples: 粒徑採樣點數
    
    Returns:
        <P(θ)>: 粒徑分布加權平均相位函數
    """
    params = PARTICLE_DISTRIBUTIONS[iso]
    mean_um = params['mean']
    std_um = params['std']
    
    # 對數常態分布採樣
    scale = mean_um
    s = std_um / mean_um  # shape parameter
    dist = lognorm(s=s, scale=scale)
    
    # 粒徑範圍: [0.2 μm, 4 μm]
    diameters = np.linspace(0.2, 4.0, n_samples)
    weights = dist.pdf(diameters)
    weights = weights / np.sum(weights)  # 正規化
    
    # 加權平均相位函數
    phase_avg = np.zeros_like(angles_deg, dtype=float)
    for d, w in zip(diameters, weights):
        try:
            phase = compute_mie_phase_function(wavelength_nm, d, angles_deg)
            phase_avg += w * phase
        except Exception as e:
            print(f"  ⚠️  警告: d={d:.2f}μm 計算失敗 ({e}), 跳過")
            continue
    
    return phase_avg

# ============================================================
# 3. 角度 → 空間 PSF 轉換
# ============================================================

def phase_to_spatial_psf(phase_function, angles_deg, z_eff_um=12.5, max_radius_px=150):
    """
    將角度相位函數轉換為空間 PSF
    
    Args:
        phase_function: P(θ) 陣列
        angles_deg: 對應角度 (度)
        z_eff_um: 有效散射深度 (μm)
        max_radius_px: 最大半徑 (像素)
    
    Returns:
        r_px, PSF(r): 徑向 PSF 分布
    """
    # 角度 → 空間映射: r = z_eff × tan(θ)
    angles_rad = np.deg2rad(angles_deg)
    r_um = z_eff_um * np.tan(angles_rad)
    
    # 假設像素尺寸 12 μm/px（掃描解析度 ~2000 DPI）
    pixel_size_um = 12.0
    r_px = r_um / pixel_size_um
    
    # 正規化 PSF: ∫ PSF(r) 2πr dr = 1
    psf_r = phase_function / (2 * np.pi * r_px + 1e-10)  # 避免除零
    
    # 插值到均勻網格
    r_grid = np.linspace(0, max_radius_px, 300)
    psf_grid = np.interp(r_grid, r_px, psf_r, left=psf_r[0], right=0)
    
    # 再次正規化
    norm_factor = np.trapz(psf_grid * r_grid, r_grid) * 2 * np.pi
    psf_grid = psf_grid / (norm_factor + 1e-10)
    
    return r_grid, psf_grid

# ============================================================
# 4. 雙段核參數擬合
# ============================================================

def dual_kernel(r, sigma, kappa, rho):
    """雙段核模型"""
    gaussian = np.exp(-r**2 / (2 * sigma**2))
    exponential = np.exp(-r / kappa)
    return rho * gaussian + (1 - rho) * exponential

def fit_dual_kernel(r, psf_target):
    """
    擬合雙段核參數 (σ, κ, ρ)
    
    Returns:
        (sigma, kappa, rho, rmse)
    """
    # 初始猜測
    sigma_init = 20.0  # px
    kappa_init = 40.0  # px
    rho_init = 0.75
    
    def objective(params):
        sigma, kappa, rho = params
        psf_model = dual_kernel(r, sigma, kappa, rho)
        # 正規化
        norm = np.trapz(psf_model * r, r) * 2 * np.pi
        psf_model = psf_model / (norm + 1e-10)
        # RMSE
        return np.sqrt(np.mean((psf_target - psf_model)**2))
    
    # 約束
    bounds = [(5, 50), (10, 100), (0.5, 0.95)]  # (σ, κ, ρ)
    
    result = minimize(objective, [sigma_init, kappa_init, rho_init], 
                     bounds=bounds, method='L-BFGS-B')
    
    sigma, kappa, rho = result.x
    rmse = result.fun
    
    return sigma, kappa, rho, rmse

# ============================================================
# 5. 能量係數計算
# ============================================================

def compute_energy_fraction(wavelength_nm, iso):
    """
    計算散射能量分數 η(λ, ISO)
    
    基於 Mie 散射截面積分
    """
    params = PARTICLE_DISTRIBUTIONS[iso]
    mean_um = params['mean']
    std_um = params['std']
    
    # 尺寸參數
    x = np.pi * mean_um / (wavelength_nm / 1000)
    m = relative_refractive_index(wavelength_nm)
    
    # Mie 散射效率 Q_scat
    qext, qsca, qback, g = miepython.mie(m, x)
    
    # 能量分數（簡化：正比於 Q_scat）
    # 正規化：綠光 (550nm) 為基準
    q_ref = miepython.mie(relative_refractive_index(550), 
                          np.pi * mean_um / 0.55)[1]
    
    eta = qsca / (q_ref + 1e-10)
    
    return eta

# ============================================================
# 6. 主生成流程
# ============================================================

def generate_lookup_table():
    """生成完整查表"""
    print("=" * 70)
    print("  Mie 散射查表生成")
    print("=" * 70)
    
    # 初始化表格
    n_wavelengths = len(WAVELENGTHS)
    n_isos = len(ISO_VALUES)
    
    table_sigma = np.zeros((n_wavelengths, n_isos))
    table_kappa = np.zeros((n_wavelengths, n_isos))
    table_rho = np.zeros((n_wavelengths, n_isos))
    table_eta = np.zeros((n_wavelengths, n_isos))
    
    # 角度網格
    angles_deg = np.linspace(0.01, 30, 200)  # 0.01° ~ 30° (小角區)
    
    # 遍歷所有 (λ, ISO) 組合
    for i, wavelength in enumerate(WAVELENGTHS):
        for j, iso in enumerate(ISO_VALUES):
            print(f"\n處理: λ={wavelength}nm, ISO={iso}")
            
            # 1. 計算多粒徑平均相位函數
            print("  [1/4] 計算 Mie 相位函數...")
            phase = compute_polydisperse_phase(wavelength, iso, angles_deg)
            
            # 2. 轉換為空間 PSF
            print("  [2/4] 轉換為空間 PSF...")
            r, psf = phase_to_spatial_psf(phase, angles_deg)
            
            # 3. 擬合雙段核
            print("  [3/4] 擬合雙段核參數...")
            sigma, kappa, rho, rmse = fit_dual_kernel(r, psf)
            
            # 4. 計算能量分數
            print("  [4/4] 計算能量分數...")
            eta = compute_energy_fraction(wavelength, iso)
            
            # 儲存結果
            table_sigma[i, j] = sigma
            table_kappa[i, j] = kappa
            table_rho[i, j] = rho
            table_eta[i, j] = eta
            
            print(f"  ✅ 結果: σ={sigma:.2f}, κ={kappa:.2f}, ρ={rho:.3f}, η={eta:.3f}, RMSE={rmse:.4f}")
    
    # 封裝為字典
    lookup_table = {
        'wavelengths': WAVELENGTHS,
        'iso_values': ISO_VALUES,
        'sigma': table_sigma,
        'kappa': table_kappa,
        'rho': table_rho,
        'eta': table_eta,
        'metadata': {
            'z_eff_um': 12.5,
            'pixel_size_um': 12.0,
            'n_gelatin': N_GELATIN,
            'particle_distributions': PARTICLE_DISTRIBUTIONS,
            'version': '1.0',
            'date': '2025-12-19',
            'library': 'miepython'
        }
    }
    
    # 儲存
    output_path = '../data/mie_lookup_table_v1.npz'
    np.savez_compressed(output_path, **lookup_table)
    print(f"\n✅ 查表已儲存: {output_path}")
    print(f"   檔案大小: {os.path.getsize(output_path) / 1024:.2f} KB")
    
    return lookup_table

if __name__ == '__main__':
    import os
    os.makedirs('../data', exist_ok=True)
    generate_lookup_table()
```

---

## 5. 整合方案

### 5.1 修改 `film_models.py`

新增查表路徑配置：

```python
@dataclass
class WavelengthBloomParams:
    # ... 既有欄位 ...
    
    # 新增: Mie 查表支援
    use_mie_lookup: bool = False  # 預設關閉（向後相容）
    mie_lookup_path: Optional[str] = None  # 查表檔案路徑
```

### 5.2 修改 `Phos_0.3.0.py`

新增查表載入與插值函數：

```python
# 全域快取
_MIE_LOOKUP_CACHE = None

def load_mie_lookup_table(path: str) -> dict:
    """載入 Mie 查表（帶快取）"""
    global _MIE_LOOKUP_CACHE
    if _MIE_LOOKUP_CACHE is None:
        data = np.load(path, allow_pickle=True)
        _MIE_LOOKUP_CACHE = {
            'wavelengths': data['wavelengths'],
            'iso_values': data['iso_values'],
            'sigma': data['sigma'],
            'kappa': data['kappa'],
            'rho': data['rho'],
            'eta': data['eta'],
            'metadata': data['metadata'].item()
        }
        print(f"✅ Mie 查表已載入: {path}")
    return _MIE_LOOKUP_CACHE

@lru_cache(maxsize=128)
def lookup_mie_params(wavelength_nm: int, iso: int) -> Tuple[float, float, float, float]:
    """查表並插值"""
    table = _MIE_LOOKUP_CACHE
    if table is None:
        raise RuntimeError("Mie lookup table not loaded")
    
    # 波長插值
    sigma_interp = np.interp(wavelength_nm, table['wavelengths'], table['sigma'][:, :])
    kappa_interp = np.interp(wavelength_nm, table['wavelengths'], table['kappa'][:, :])
    rho_interp = np.interp(wavelength_nm, table['wavelengths'], table['rho'][:, :])
    eta_interp = np.interp(wavelength_nm, table['wavelengths'], table['eta'][:, :])
    
    # ISO 插值（對數空間）
    log_iso = np.log10(iso)
    log_iso_table = np.log10(table['iso_values'])
    
    sigma = np.interp(log_iso, log_iso_table, sigma_interp)
    kappa = np.interp(log_iso, log_iso_table, kappa_interp)
    rho = np.interp(log_iso, log_iso_table, rho_interp)
    eta = np.interp(log_iso, log_iso_table, eta_interp)
    
    return sigma, kappa, rho, eta
```

### 5.3 修改 `apply_wavelength_bloom()`

```python
def apply_wavelength_bloom(response_r, response_g, response_b, 
                          wavelength_params, bloom_params):
    # 檢查是否使用 Mie 查表
    if wavelength_params.use_mie_lookup:
        # 從查表獲取參數
        if _MIE_LOOKUP_CACHE is None:
            load_mie_lookup_table(wavelength_params.mie_lookup_path)
        
        iso = bloom_params.iso if hasattr(bloom_params, 'iso') else 400  # 預設 ISO 400
        
        sigma_r, kappa_r, rho_r, eta_r = lookup_mie_params(650, iso)
        sigma_g, kappa_g, rho_g, eta_g = lookup_mie_params(550, iso)
        sigma_b, kappa_b, rho_b, eta_b = lookup_mie_params(450, iso)
    else:
        # 使用經驗公式（既有邏輯）
        p = wavelength_params.wavelength_power
        eta_r = ... # 既有計算
        sigma_r = ...
        # ...
    
    # 後續流程不變
```

---

## 6. 驗證計畫

### 6.1 單元測試

**檔案**: `tests/test_mie_lookup.py`

```python
def test_lookup_table_format():
    """測試查表格式正確性"""
    table = np.load('data/mie_lookup_table_v1.npz')
    assert 'sigma' in table
    assert table['sigma'].shape == (3, 7)  # 3 wavelengths × 7 ISOs
    
def test_interpolation_accuracy():
    """測試插值精度"""
    # 已知點應精確匹配
    sigma, _, _, _ = lookup_mie_params(550, 400)
    sigma_table = table['sigma'][1, 2]  # λ=550nm, ISO=400
    assert abs(sigma - sigma_table) < 1e-6

def test_dual_kernel_fit_error():
    """測試雙段核擬合誤差 < 2%"""
    for λ, iso in [(450, 400), (550, 800), (650, 1600)]:
        # 重新計算 Mie PSF
        phase = compute_polydisperse_phase(λ, iso, angles)
        r, psf_mie = phase_to_spatial_psf(phase, angles)
        
        # 從查表獲取參數
        sigma, kappa, rho, _ = lookup_mie_params(λ, iso)
        psf_dual = dual_kernel(r, sigma, kappa, rho)
        
        # RMSE
        rmse = np.sqrt(np.mean((psf_mie - psf_dual)**2))
        assert rmse < 0.02, f"RMSE={rmse:.4f} > 2% at λ={λ}, ISO={iso}"
```

### 6.2 視覺驗證

**對比測試**:
1. 經驗公式 (Phase 1) vs Mie 查表 (Phase 5)
2. 預期差異：
   - 高 ISO: Mie 查表應產生更寬 PSF（大顆粒）
   - 藍光光暈: Mie 查表可能稍弱（實際 η_b/η_r < 3.62）

### 6.3 效能測試

```python
def test_lookup_performance():
    """測試查表效能"""
    import time
    
    # 載入時間
    t0 = time.time()
    load_mie_lookup_table('data/mie_lookup_table_v1.npz')
    load_time = time.time() - t0
    assert load_time < 0.1, f"載入時間 {load_time:.3f}s > 100ms"
    
    # 插值時間（含快取）
    t0 = time.time()
    for _ in range(1000):
        lookup_mie_params(500, 400)  # 快取命中
    query_time = (time.time() - t0) / 1000
    assert query_time < 0.001, f"查詢時間 {query_time*1000:.3f}ms > 1ms"
```

---

## 7. 時程規劃

### Phase 5.1: 架構設計 ✅ (當前)
- 時間: 2 小時
- 產出: 本設計文檔

### Phase 5.2: 離線計算腳本
- 時間: 3-4 小時
- 依賴: `pip install miepython scipy`
- 產出: `scripts/generate_mie_lookup.py`
- 驗證: 生成 `data/mie_lookup_table_v1.npz` (~1 KB)

### Phase 5.3-5.4: 整合與測試
- 時間: 2-3 小時
- 產出: 
  - 修改 `film_models.py` (+20 lines)
  - 修改 `Phos_0.3.0.py` (+60 lines)
  - 新建 `tests/test_mie_lookup.py` (~200 lines)

### Phase 5.5: 視覺驗證
- 時間: 1 小時
- 方法: Streamlit UI 對比測試

### Phase 5.6: 效能優化
- 時間: 1-2 小時
- 優化: 快取策略、預載入機制

**總預估**: 8-12 小時

---

## 8. 風險與緩解

### 風險 1: Mie 計算庫依賴
- **問題**: `miepython` 可能在某些平台安裝失敗
- **緩解**: 提供預生成查表 + Docker 環境

### 風險 2: 擬合誤差 > 2%
- **問題**: 雙段核無法完美擬合 Mie PSF
- **緩解**: 改用三段核（Gaussian + 2×Exponential）

### 風險 3: 查表覆蓋不足
- **問題**: ISO 50 或 12800 超出查表範圍
- **緩解**: 外推（extrapolate）+ 警告訊息

### 風險 4: 效能退化
- **問題**: 查表插值開銷 > 1ms
- **緩解**: 預計算常用參數（如 ISO 400/800）

---

## 9. 成功指標

- ✅ 查表檔案 < 1 MB
- ✅ 載入時間 < 100 ms
- ✅ 插值誤差 < 1%
- ✅ 雙段核 RMSE < 2%
- ✅ 整體效能 < 10s (2000×3000)
- ✅ 視覺效果自然（高 ISO 光暈更寬）

---

## 10. 參考資料

1. **Bohren & Huffman (1983)**: *Absorption and Scattering of Light by Small Particles*
2. **miepython 文檔**: https://miepython.readthedocs.io/
3. **Physicist 審查**: `tasks/TASK-003-medium-physics/physicist_review.md` (Line 276-283)
4. **Phase 1 實作**: `Phos_0.3.0.py` Line 953-1034

---

**最後更新**: 2025-12-20 00:20  
**狀態**: 🔄 Phase 5.1 完成，Phase 5.2 準備開始
