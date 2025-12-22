# Phos 物理改進路線圖

> 基於 Physicist Review、測試結果與技術文檔，整理出可完善的物理項目
> 
> **當前物理正確性**: 7.0/10 (中等物理, ~50-60%)  
> **目標**: 8.5-9.0/10 (高級物理, ~75-85%)

---

## 優先級分類

### 🔴 P0 - 關鍵物理錯誤（必須修正）

這些問題會導致明顯的物理不一致或計算錯誤：

#### 1. **Mie 散射相對折射率錯誤** ⚠️ 高優先級

**當前問題**:
```python
# scripts/generate_mie_lookup.py Line 60-64
# ❌ 錯誤：使用絕對折射率（相對空氣）
n_agbr = 1.5 + 0.5 / wavelength_um**2  # 相對空氣
m = mie.Mie(x=x, m=complex(n_agbr, 0))
```

**物理原理**:
- Mie 理論要求的是「粒子折射率 / 介質折射率」
- 銀鹵化物在**明膠/水相介質**中（非空氣中！）
- n_AgBr(λ) ≈ 2.2-2.4（可見光）
- n_gelatin ≈ 1.50-1.52
- **相對折射率**: m(λ) = n_AgBr(λ) / n_gelatin ≈ 1.45-1.60

**修正方案**:
```python
# 修正後
n_agbr_air = 2.20 + 0.08 * (550/wavelength_nm)  # AgBr in air (文獻值)
n_gelatin = 1.50  # 明膠介質折射率
m_relative = n_agbr_air / n_gelatin  # ≈ 1.47 @ 550nm

# 使用相對折射率計算
m = mie.Mie(x=x, m=complex(m_relative, 0))
```

**影響**:
- 當前查表的 η(λ) 數值可能偏差 20-50%
- Mie 振盪位置錯誤（x=2πa/λ 正確，但 m 錯誤會改變共振峰）
- 藍光/紅光散射比例不準確

**驗證**:
```bash
# 重新生成查表並對比
python3 scripts/generate_mie_lookup.py --use-relative-index
python3 scripts/compare_mie_versions.py  # v2 vs v3
```

**參考文獻**:
- Palik, *Handbook of Optical Constants of Solids* (AgBr 折射率)
- Bohren & Huffman (1983), 相對折射率定義 (Chapter 4)

---

#### 2. **光譜敏感度曲線過度簡化** ✅ 已實現（需驗證）

**狀態**: Phase 1 完成 (光譜形狀測試 23/23 ✅)  
**發現**: 當前實作已使用多高斯混合，問題不存在！  
**下一步**: Phase 2 - ColorChecker ΔE 驗證

**當前問題**:
```python
# film_models.py - 使用單峰對稱高斯
# ❌ 真實膠片敏感度曲線不是對稱的！
EmulsionLayer(
    r_response_weight=0.82,  # 僅一個係數
    # 缺少波長依賴曲線
)
```

**物理現實**:
- 膠片敏感度曲線通常有：
  - **多峰結構**（主峰 + 次峰）
  - **非對稱形狀**（紅層常有長尾）
  - **層間重疊**（造成色彩交互敏感度）
  
**真實案例** (Kodak Portra 400):
```
紅層:   ████████░░░░░░░░░░░   (600-700nm, 長尾至 750nm)
綠層:   ░░░░██████████░░░░░   (500-600nm, 主峰 550nm)
藍層:   ░░░░░░░░░░████████   (400-500nm, 次峰 480nm)
```

**修正方案 (Phase 4 增強)**:
```python
# 選項 A: 使用廠商 CSV 數據（最準確）
spectral_sensitivity = load_film_csv("kodak_portra_400.csv")

# 選項 B: 多峰高斯混合（無 CSV 時）
def multi_peak_sensitivity(wavelengths):
    """2-3 個偏斜高斯疊加"""
    peak1 = skewed_gaussian(wavelengths, mu=620, sigma=40, alpha=1.5)
    peak2 = skewed_gaussian(wavelengths, mu=680, sigma=50, alpha=0.8)
    return 0.7 * peak1 + 0.3 * peak2
```

**影響**:
- 色彩還原準確度（ΔE 誤差可能 +3-5）
- 膠片特有色相偏移丟失（如 Velvia 的飽和綠）
- 層間串擾不準確

**驗證**:
```python
# 使用 ColorChecker 24 色卡測試
def test_color_accuracy():
    colorchecker_rgb = load_colorchecker()
    for rgb in colorchecker_rgb:
        spectrum = rgb_to_spectrum(rgb)
        film_response = apply_spectral_sensitivity(spectrum)
        output_rgb = spectrum_to_rgb(film_response)
        delta_e = ciede2000(rgb, output_rgb)
        assert delta_e < 5.0  # ΔE00 < 5 可接受
```

---

### 🟡 P1 - 重要物理改進（建議實作）

這些改進會顯著提升物理正確性，但當前簡化尚可接受：

#### 3. **PSF 波長依賴次方關係未嚴格推導** 🟡

**當前實作** (Phase 1):
```python
# Phos_0.3.0.py Line 893-918
# 使用經驗公式
wavelength_power = 3.5  # η(λ) ∝ λ^-3.5
radius_power = 0.8      # σ(λ) ∝ λ^-0.8
```

**物理問題**:
- λ^-3.5 介於 Rayleigh (λ^-4) 與 Mie (λ^-1 to λ^-2) 之間
- 但 **粒徑 0.5-3μm 時，多數在 Mie 範圍**（x=2πa/λ ≈ 3-20）
- PSF 半徑 ∝ λ^-0.8 缺乏理論支持（應從角度分布推導）

**改進方案**:
```python
# 方案 A: 基於 Mie 查表（已實作 Phase 5）
eta_r, sigma_r = lookup_mie_params(wavelength=650, iso=400)
eta_g, sigma_g = lookup_mie_params(wavelength=550, iso=400)
eta_b, sigma_b = lookup_mie_params(wavelength=450, iso=400)

# 方案 B: 分段模型（快速模式）
if particle_size < 0.3:  # Rayleigh
    eta = k * wavelength**(-4)
    sigma_angular = constant
elif particle_size < 2.0:  # Mie transition
    eta, sigma = mie_lookup(particle_size, wavelength)
else:  # Large particle (geometric)
    eta = k * wavelength**(-1)
    sigma = forward_scattering_approx(particle_size, wavelength)
```

**驗證指標**:
- η(450nm) / η(650nm) 應在 1.5-4.0 範圍（視 ISO 而定）
- σ(450nm) / σ(650nm) 應在 1.2-2.0 範圍

---

#### 4. **Beer-Lambert 穿透率命名與參數化混亂** 🟡

**當前問題** (Phase 2):
```python
# film_models.py Line 165-173
# ❌ 命名混亂
HalationParams(
    wavelength_attenuation_r=0.7,  # 這是透過率？還是衰減係數？
    transmittance_r=0.7,  # 與上面重複？
    ah_absorption=0.95,  # 吸收率 = 1 - 透過率？
)
```

**物理原理**:
- Beer-Lambert: **T(λ) = exp(-α(λ)·L)**
- α(λ): 吸收係數 (cm⁻¹)
- L: 路徑長度 (cm)
- Halation 是**雙程**：往返穿透乳劑 + 片基

**修正方案**:
```python
# 標準化參數定義
@dataclass
class HalationParams:
    """Halation 參數（基於 Beer-Lambert 定律）"""
    
    # 乳劑穿透率（單程）
    emulsion_transmittance_r: float = 0.85
    emulsion_transmittance_g: float = 0.75
    emulsion_transmittance_b: float = 0.60
    
    # AH 層吸收係數 (cm⁻¹) 或直接給透過率
    ah_layer_transmittance_r: float = 0.30  # 有 AH 層：紅光穿透 30%
    ah_layer_transmittance_g: float = 0.10  # 綠光穿透 10%
    ah_layer_transmittance_b: float = 0.05  # 藍光穿透 5%
    
    # 背板反射率
    backplate_reflectance: float = 0.30
    
    # 有效 Halation 能量分數（自動計算）
    @property
    def effective_halation_r(self) -> float:
        """雙程透過 × 背板反射"""
        return (self.emulsion_transmittance_r ** 2 * 
                self.ah_layer_transmittance_r ** 2 * 
                self.backplate_reflectance)
```

**計算範例**:
```python
# CineStill 800T（無 AH 層）
halation_r = (0.85)**2 * (1.0)**2 * 0.30 = 0.217  # 21.7% 紅光 halation
halation_b = (0.60)**2 * (1.0)**2 * 0.30 = 0.108  # 10.8% 藍光 halation

# Portra 400（有 AH 層）
halation_r = (0.85)**2 * (0.30)**2 * 0.30 = 0.020  # 2.0% 紅光 halation
halation_b = (0.60)**2 * (0.05)**2 * 0.30 = 0.0003  # 0.03% 藍光 halation
```

---

#### 5. **粒徑分布未與 ISO 明確關聯** 🟡

**當前問題**:
```python
# film_models.py - ISO 定義分散
Velvia50: iso_value=50    # ISO 分散在多處
GrainParams: intensity=0.06  # 但與 ISO 無直接公式
```

**物理規律**:
- **ISO ↑ → 粒徑 ↑ → 散射 ↑ → 顆粒感 ↑**
- 經驗公式：`d_mean ≈ 0.2 + 0.0015·ISO (μm)`
  - ISO 50: d ≈ 0.28 μm
  - ISO 400: d ≈ 0.80 μm
  - ISO 3200: d ≈ 5.0 μm

**改進方案**:
```python
def derive_physical_params_from_iso(iso: int):
    """從 ISO 推導物理參數"""
    # 粒徑（對數常態分布平均）
    d_mean_um = 0.2 + 0.0015 * iso
    d_sigma = 0.3 * d_mean_um  # 標準差 ~30%
    
    # 散射比例（隨粒徑增加）
    scattering_ratio = 0.03 + 0.00008 * iso  # 3% @ ISO50 → 9% @ ISO800
    
    # 顆粒強度
    grain_intensity = 0.02 + 0.0002 * iso  # 視覺顆粒感
    
    # Mie 查表參數
    mie_params = lookup_mie_params(
        particle_diameter=d_mean_um,
        wavelength=[450, 550, 650],
        medium_n=1.50
    )
    
    return {
        "particle_size": d_mean_um,
        "scattering_ratio": scattering_ratio,
        "grain_intensity": grain_intensity,
        "mie_eta": mie_params["eta"],
        "mie_sigma": mie_params["sigma"]
    }
```

**驗證**:
- RMS granularity 應與 ISO 呈單調遞增
- 視覺顆粒度測試：ISO 3200 > ISO 800 > ISO 400

---

### 🟢 P2 - 進階物理特性（可選）

這些特性會進一步提升真實感，但對當前目標非必需：

#### 6. **互易律失效（Reciprocity Failure）** 🟢

**物理現象**:
- 長曝光（>1s）或極短曝光（<1/1000s）時，膠片響應偏離線性
- 原因：化學反應動力學非即時
- 表現：長曝光需增加補償（如 10s → 實際需 15s）

**實作方案**:
```python
def apply_reciprocity_failure(exposure_time: float, intensity: np.ndarray):
    """Schwarzschild 定律: E_eff = I·t^p，p < 1 表示失效"""
    if exposure_time < 0.001:  # 極短曝光
        p = 0.95
    elif exposure_time > 1.0:  # 長曝光
        p = 0.85 - 0.05 * np.log10(exposure_time)  # 越長越失效
    else:
        p = 1.0  # 正常範圍
    
    effective_exposure = intensity * (exposure_time ** p)
    return effective_exposure
```

**參考案例**:
- Kodak T-Max 400: 10s曝光需補償 +1/3 EV
- Velvia 50: 60s曝光需補償 +1 EV

---

#### 7. **色溫/照明光源適應** 🟢

**物理現象**:
- 日光膠片（D65, 5500K）在鎢絲燈（3200K）下偏黃
- 燈光膠片（Tungsten）在日光下偏藍
- 需色溫校正矩陣

**實作方案**:
```python
def apply_color_temperature_adaptation(
    image: np.ndarray,
    film_balanced_for: int = 5500,  # K
    scene_light_temp: int = 3200     # K
):
    """色溫適應（von Kries 變換）"""
    # 計算色溫偏移
    xyz_film = planck_locus(film_balanced_for)
    xyz_scene = planck_locus(scene_light_temp)
    
    # Bradford 色彩適應矩陣
    M_adapt = bradford_transform(xyz_scene, xyz_film)
    
    # 應用到影像
    image_adapted = apply_matrix(image, M_adapt)
    return image_adapted
```

---

#### 8. **多次散射（Multiple Scattering）** 🟢

**當前限制**:
- 僅模擬單次散射（光子散射一次即被捕獲）
- 真實情況：光子可能散射 2-5 次才被吸收

**物理影響**:
- 長距離 Halation 尾部更長
- 整體對比度略降

**實作方案**:
```python
def apply_multiple_scattering(image, psf_single, num_iterations=3):
    """迭代模擬多次散射"""
    scattered = np.zeros_like(image)
    current = image
    
    for i in range(num_iterations):
        # 每次散射能量遞減
        energy_fraction = 0.1 * (0.5 ** i)  # 10%, 5%, 2.5%, ...
        scattered_once = convolve(current, psf_single) * energy_fraction
        scattered += scattered_once
        current = scattered_once  # 用於下一次散射
    
    return image * 0.9 + scattered  # 90% 直接光 + 10% 多次散射
```

---

#### 9. **角度依賴散射（Directional Effects）** 🟢

**當前假設**: Lambertian（各向同性）
**真實情況**: 前向散射主導（Mie）+ 少量背向散射

**實作方案**:
```python
def directional_psf(angle_deg: float, wavelength: float):
    """角度依賴 PSF（簡化模型）"""
    # 前向散射（小角度）
    forward_weight = np.exp(-angle_deg**2 / (2 * 5**2))
    
    # 大角散射（尾部）
    wide_angle_weight = (1 + angle_deg**2 / 100)**(-1.5)
    
    psf = 0.8 * forward_weight + 0.2 * wide_angle_weight
    return psf / np.sum(psf)
```

---

## 實作優先級建議

### 階段 1: 修正關鍵錯誤（2-3 天）
1. ✅ **修正 Mie 相對折射率**（P0）
   - 重新生成 lookup table v3
   - 驗證 η(λ) 比例合理性
   
2. ✅ **標準化 Beer-Lambert 參數**（P0-P1）
   - 重構 `HalationParams`
   - 更新所有膠片配置

### 階段 2: 重要改進（1-2 週）
3. ✅ **多峰光譜敏感度**（P1）
   - 收集廠商 CSV（Kodak, Fuji）
   - 實作多峰高斯混合
   
4. ✅ **ISO-粒徑統一模型**（P1）
   - 實作 `derive_physical_params_from_iso()`
   - 重新校準所有膠片參數

5. ⚪ **PSF 波長依賴理論修正**（P1）
   - 基於 Mie 查表而非經驗公式
   - 分段模型（Rayleigh/Mie/Geometric）

### 階段 3: 進階特性（可選，1-2 月）
6. ⚪ **互易律失效**（P2）
7. ⚪ **色溫適應**（P2）
8. ⚪ **多次散射**（P2）

---

## 測試驗證計畫

每個改進需通過以下測試：

### 物理一致性測試
```python
# tests/test_physics_consistency.py
def test_mie_relative_index():
    """驗證 Mie 相對折射率正確"""
    m = calculate_relative_index(wavelength=550)
    assert 1.4 < m < 1.7  # AgBr/gelatin 合理範圍

def test_beer_lambert_energy():
    """驗證 Halation 能量守恆"""
    T_forward = 0.7
    T_ah = 0.1
    R_back = 0.3
    halation_energy = (T_forward**2) * (T_ah**2) * R_back
    assert 0 < halation_energy < 0.1  # 合理範圍

def test_iso_grain_monotonic():
    """驗證 ISO ↑ → 顆粒感 ↑"""
    grain_50 = derive_grain_from_iso(50)
    grain_400 = derive_grain_from_iso(400)
    grain_3200 = derive_grain_from_iso(3200)
    assert grain_50 < grain_400 < grain_3200
```

### 視覺驗證測試
```python
# tests/test_visual_accuracy.py
def test_colorchecker_accuracy():
    """ColorChecker ΔE < 5"""
    for rgb in load_colorchecker():
        output = process_image(rgb, film="Portra400")
        delta_e = ciede2000(rgb, output)
        assert delta_e < 5.0

def test_cinestill_red_halation():
    """CineStill 紅色 Halation 視覺特徵"""
    point_source = create_test_image("white_point_on_black")
    output = process_image(point_source, film="Cinestill800T")
    
    # 檢查紅色通道 Halation 能量 > 藍色通道
    r_halo = measure_halo_energy(output[:,:,0])
    b_halo = measure_halo_energy(output[:,:,2])
    assert r_halo > 2 * b_halo  # 紅光 Halation 至少 2 倍於藍光
```

---

## 總結

**當前狀態**: 7.0/10 物理正確性  
**P0 修正後**: 7.8/10  
**P1 改進後**: 8.5/10  
**P2 完成後**: 9.0/10

**核心原則**:
- ✅ 能量守恆永遠優先
- ✅ 參數必須有物理單位與明確定義
- ✅ 簡化必須註明並量化誤差範圍
- ✅ 視覺品質與物理準確度並重

**下一步行動**:
1. 與用戶確認優先級
2. 開始 P0 修正（Mie 折射率 + Beer-Lambert）
3. 視覺驗證新版 Mie lookup table
4. 更新文檔與測試

---

**文檔版本**: v1.0  
**創建日期**: 2025-12-20  
**負責**: Main Agent + Physicist  
**狀態**: 待用戶確認優先級
