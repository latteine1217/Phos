# Phos 計算光學技術文檔

**版本**: v0.3.3  
**文檔類型**: Technical Reference  
**維護者**: @LYCO6273  
**最後更新**: 2025-12-22

**重要更新**:
- ✅ v0.3.3: Mie 散射修正（Decision #014）+ Halation 獨立建模（Decision #012）
- ✅ v0.3.2: Beer-Lambert 分層穿透率結構
- ✅ v0.3.0: Physical Mode 完整實作（能量守恆 + H&D 曲線 + Poisson 顆粒）

---

## 📋 目錄

1. [概述](#1-概述)
2. [核心理念](#2-核心理念)
3. [物理基礎](#3-物理基礎)
4. [計算模型](#4-計算模型)
5. [實作細節](#5-實作細節)
6. [膠片建模](#6-膠片建模)
7. [三種模式](#7-三種模式)
8. [測試與驗證](#8-測試與驗證)
9. [效能優化](#9-效能優化)
10. [限制與未來方向](#10-限制與未來方向)

---

## 1. 概述

### 1.1 專案定位

**Phos** 是一個基於**計算光學原理**的膠片模擬系統，核心理念為：

> **"No LUTs, we calculate LUX."**

與傳統 LUT (Look-Up Table) 方法不同，Phos 通過建立簡化的光學模型，**計算光線在膠片中的行為**，從而重現自然、柔美、立體的膠片質感。

### 1.2 設計理念

1. **物理啟發 (Physics-Inspired)**：基於真實光學現象（非完整物理模擬）
2. **藝術平衡 (Artistic Balance)**：在物理正確性與視覺美感間取得平衡
3. **可驗證性 (Verifiable)**：核心假設與計算過程可測試、可驗證
4. **效能導向 (Performance-Oriented)**：實時或近實時處理（< 5秒/張）

### 1.3 適用場景

- ✅ 數位照片膠片風格化
- ✅ 計算攝影研究
- ✅ 藝術創作與後製
- ❌ 嚴格的光學模擬（非 Ray Tracing）
- ❌ 科學級輻射傳輸計算

---

## 2. 核心理念

### 2.1 計算光學 vs 查表法

| 特性 | 查表法 (LUT) | 計算光學 (Phos) |
|-----|-------------|-----------------|
| **原理** | 預先定義的顏色映射 | 模擬光學過程 |
| **靈活性** | 固定（需重新生成 LUT）| 高（參數可調） |
| **物理意義** | 無（經驗映射）| 有（光學近似）|
| **計算成本** | 極低（查表）| 中等（卷積運算）|
| **可擴展性** | 低（難以組合）| 高（模組化）|

### 2.2 簡化 vs 完整模擬

Phos 採用**簡化光學模型**，非完整的輻射傳輸方程 (RTE) 求解器：

```python
# 完整模擬（Phos 不做）
∂L/∂s = -σ_t L + σ_s ∫₄π p(ω→ω') L(ω') dω' + Q

# Phos 的簡化（線性疊加 + 卷積）
Response = Spectral_Response(image, film)
Output = Bloom(Response) + Grain(Response) + ToneMap(HD_Curve(Response))
```

**理由**：完整模擬需要波長分辨、角度積分、多次散射，計算成本高達數分鐘至數小時。Phos 在保留主要視覺特徵的前提下，將計算時間壓縮至秒級。

---

## 3. 物理基礎

### 3.1 光譜響應 (Spectral Response)

#### 3.1.1 原理

膠片乳劑層對不同波長光線的敏感度不同，類似於人眼的錐細胞：

```
R 層：主要吸收紅光（~650nm），但也對綠光有微弱響應
G 層：主要吸收綠光（~550nm），對紅藍有交叉響應
B 層：主要吸收藍光（~450nm），對綠光有微弱響應
```

#### 3.1.2 數學模型

對於彩色膠片，每層的響應為**加權線性組合**：

```python
Response_R = w_rr × R + w_rg × G + w_rb × B
Response_G = w_gr × R + w_gg × G + w_gb × B
Response_B = w_br × R + w_bg × G + w_bb × B
```

權重矩陣範例（Kodak Portra 400 近似）：

```
[R層]  [0.32  0.12  0.06]   [R_in]
[G層] = [0.08  0.35  0.10] × [G_in]
[B層]  [0.05  0.08  0.38]   [B_in]
```

**物理意義**：
- 對角線元素（0.32, 0.35, 0.38）：主響應（該層對對應波長的敏感度）
- 非對角線元素：交叉響應（色彩耦合，造成膠片獨特的色彩偏移）

#### 3.1.3 實作函數

```python
def spectral_response(image: np.ndarray, film: FilmProfile) -> Tuple:
    """
    計算膠片三層的光譜響應
    
    Args:
        image: 輸入影像 (H, W, 3), BGR 格式, 0-255 uint8
        film: 膠片配置（包含三層 EmulsionLayer）
        
    Returns:
        response_r, response_g, response_b, response_total (0-1 浮點數)
    """
    # 正規化到 [0, 1]
    r, g, b = image[:, :, 2] / 255.0, image[:, :, 1] / 255.0, image[:, :, 0] / 255.0
    
    # R 層響應（紅敏層）
    response_r = (film.red_layer.r_response_weight * r +
                  film.red_layer.g_response_weight * g +
                  film.red_layer.b_response_weight * b)
    
    # 類似計算 G, B 層...
    # response_total = (response_r + response_g + response_b) / 3
    
    return response_r, response_g, response_b, response_total
```

**重要註記**：
- 這裡的 `response` **不是**光度學單位（lux, cd/m²），而是**無量綱的相對響應值**。
- 早期版本誤用 `luminance` 命名，已在 v0.2.0 修正為 `spectral_response`。

---

### 3.2 Bloom / Halation 效果

#### 3.2.1 物理成因

**Bloom**：膠片乳劑層中的光散射（主要為 Mie 散射）  
**Halation**：光線穿過乳劑層，在背襯反射回來造成的光暈

真實膠片的散射機制：
- **Mie 散射**（主導）：銀鹽晶體尺寸 0.5-3 μm，尺寸參數 x = πd/λ ≈ 2.4-21
- Rayleigh 散射（次要）：僅在極小晶體或缺陷處發生
- **背層 Halation**：光穿透乳劑、基底、AH 層後在背襯反射（Anti-halation 層可抑制）

**v0.3.3 重要修正**：
- ✅ 散射機制從 Rayleigh（λ^-4）修正為 Mie（λ^-3.5）
- ✅ PSF 寬度從完全波長依賴（λ^-2）修正為小角散射（λ^-0.8）
- ✅ Bloom 與 Halation 分離為獨立模組

#### 3.2.2 簡化模型

Phos 使用**點擴散函數 (PSF, Point Spread Function)** 卷積近似：

```python
# 藝術模式（v0.1.x，保留）
Bloom_artistic = Gaussian_Blur(Response) × strength
Output = Response + Bloom_artistic  # ❌ 能量不守恆（+10%）

# 物理模式（v0.2.0+，新增）
Highlights = max(Response - threshold, 0)  # 提取高光
Scattered_Energy = Highlights × scattering_ratio  # 散射能量
PSF_normalized = Gaussian_PSF / ∑Gaussian_PSF  # 正規化（關鍵）
Bloom_physical = Conv(Scattered_Energy, PSF_normalized)
Output = Response - Scattered_Energy + Bloom_physical  # ✅ 能量守恆
```

**PSF 選擇**：

1. **Gaussian PSF** (預設)：
   ```python
   PSF(r) = exp(-r² / (2σ²))
   ```
   特性：柔和、對稱、數學簡單

2. **Exponential PSF** (可選)：
   ```python
   PSF(r) = exp(-|r| / λ)
   ```
   特性：中心集中、尾部長（更接近真實 Mie 散射）

#### 3.2.3 能量守恆驗證

```python
# 測試案例（tests/test_energy_conservation.py）
E_in = ∑∑ Response(x, y)
E_out = ∑∑ Output(x, y)
Error = |E_out - E_in| / E_in

# 測試結果
# 藝術模式：Error = 10.0% ❌
# 物理模式：Error < 0.01% ✅
```

#### 3.2.4 Mie 散射修正 (v0.3.3+, Decision #014)

**背景**：Phase 1 原設計假設 Rayleigh 散射（λ^-4），但經物理審查發現銀鹽晶體尺寸屬於 Mie 散射範圍。

**尺寸參數分析**：
```
銀鹽晶體直徑：d = 0.5-3 μm
可見光波長：λ = 0.45-0.65 μm
尺寸參數：x = πd/λ ≈ 2.4-21

結論：x > 1 → Mie 散射範圍（非 Rayleigh 的 x ≪ 1）
```

**散射能量修正**：
```python
# 舊模型（Rayleigh，錯誤）
η(λ) ∝ λ^-4
η_blue / η_red ≈ (650/450)^4 = 4.4x  # 過度誇張

# 新模型（Mie，正確）
η(λ) ∝ λ^-3.5
η_blue / η_red ≈ (650/450)^3.5 = 3.5x  # 符合實驗觀察
```

**PSF 寬度修正**：
```python
# 舊模型（完全波長依賴）
σ(λ) ∝ λ^-2
σ_blue / σ_red ≈ (650/450)^2 = 2.1x  # 視覺不自然

# 新模型（小角散射近似）
σ(λ) ∝ (λ_ref/λ)^0.8
σ_blue / σ_red ≈ (650/450)^0.8 = 1.27x  # 視覺合理
```

**雙段 PSF 結構**：

為更真實地模擬 Mie 相函數的前向散射特性，採用核心 + 尾部組合：

```python
# 核心（高斯，小角前向散射）
PSF_core(r) = exp(-r² / (2σ_core²))
σ_core(λ) = base_sigma_core × (λ_ref/λ)^0.8

# 尾部（指數，多次散射）
PSF_tail(r) = exp(-r / κ_tail)
κ_tail(λ) = base_kappa_tail × (λ_ref/λ)^0.6

# 加權組合（波長依賴能量分配）
ρ(λ) = core_ratio_per_wavelength  # 紅=0.75, 綠=0.70, 藍=0.65
PSF_total(r, λ) = ρ(λ) × PSF_core(r, λ) + (1-ρ(λ)) × PSF_tail(r, λ)
```

**參數解耦**：
- **能量權重指數**: 3.5（控制藍/紅散射能量比）
- **PSF 寬度指數**: 0.8（控制藍/紅 PSF 大小比）
- **可辨識性**: 兩參數獨立，避免「半徑變大」≈「能量變多」的混淆

**驗證結果** (tests/test_mie_validation.py):
```
能量比例 (B/R): 3.62x ✓ (目標 3.5x, 容差 3.2-3.8x)
PSF 寬度比 (B/R): 1.34x ✓ (目標 1.27x, 容差 1.20-1.35x)
能量守恆: < 0.01% ✓
向後兼容: mode="physical" 與 "mie_corrected" 共存 ✓
```

**效能影響**：
- 雙段 PSF 增加計算成本 +5%（核心用空域卷積，尾部用 FFT）
- 預估處理時間：0.8s → 0.84s（2000×3000 影像）

#### 3.2.5 Halation 獨立建模 (v0.3.2+, Decision #012)

**物理分離**：將 Bloom（乳劑內散射）與 Halation（背層反射）分為兩個獨立模組。

**Halation 光路**：
```
入射光 → 乳劑層（T_e）→ 基底層（T_b）→ AH 層（T_AH）
       ↓
   背襯板反射（R_bp）
       ↓
入射光 ← AH 層（T_AH）← 基底層（T_b）← 乳劑層（T_e）
```

**Beer-Lambert 分層穿透率**：
```python
# 單程穿透率
T_single(λ) = T_emulsion(λ) × T_base × T_AH(λ)

# 雙程有效係數（來回穿透 + 背襯反射）
f_h(λ) = [T_single(λ)]² × R_backplate

# 三層獨立配置
emulsion_transmittance_r/g/b: float   # 乳劑層 T_e(λ)，波長依賴
base_transmittance: float = 0.98      # 基底層 T_b，灰度
ah_layer_transmittance_r/g/b: float   # AH 層 T_AH(λ)，波長依賴
backplate_reflectance: float          # 背襯反射率 R_bp
```

**波長依賴特性**：
```
紅光 (650nm): T_e = 0.92, 穿透力強 → f_h 大
綠光 (550nm): T_e = 0.87, 穿透力中 → f_h 中
藍光 (450nm): T_e = 0.78, 穿透力弱 → f_h 小

結果: f_h(紅) > f_h(綠) > f_h(藍) （與 Bloom 相反！）
```

**AH 層作用**：

1. **無 AH 層**（CineStill800T）：
   ```python
   T_AH = (1.0, 1.0, 1.0)  # 完全透明
   f_h(紅) = 0.253  # 極強 Halation
   效果: 大光暈（150px）+ 高能量（15%）
   ```

2. **有 AH 層**（Portra400）：
   ```python
   T_AH = (0.30, 0.10, 0.05)  # 波長依賴抑制
   f_h(紅) = 0.0076  # 97% 被抑制
   效果: 標準光暈（80px）+ 標準能量（3%）
   ```

**Bloom vs Halation 對比**：

| 特性 | Bloom（乳劑內散射）| Halation（背層反射）|
|------|-------------------|-------------------|
| **物理機制** | Mie 散射 | Beer-Lambert 穿透 + 反射 |
| **空間尺度** | ~40 px（短距離）| 80-150 px（長距離）|
| **波長依賴** | 藍 > 紅（λ^-3.5）| 紅 > 藍（T_e 穿透）|
| **視覺特徵** | 內側藍色銳利光暈 | 外側紅色柔和光暈 |
| **能量級別** | 5-15%（中等）| 3-15%（可變）|
| **控制參數** | AH 層無關 | AH 層強抑制 |

**整合效果**（Dual-Halo Structure）：
```
組合結果: 內層藍色銳利（Bloom）+ 外層紅色柔和（Halation）
視覺特性: 立體感增強，色彩分離明顯
膠片特色: CineStill 極端雙光暈，Portra 溫和單光暈
```

**實作函數**：
```python
# Phos_0.3.0.py
def apply_bloom_mie_corrected(img, bloom_params):  # Line 1309-1429
    """Mie 散射修正版 Bloom"""
    
def apply_halation(img, halation_params):          # Line 1436-1527
    """Beer-Lambert 獨立 Halation"""
    
def apply_optical_effects_separated(img, bloom_params, halation_params):  # Line 1530-1583
    """整合 Bloom + Halation（避免重複計算）"""
```

**驗證測試** (tests/test_mie_halation_integration.py):
```
7/7 整合測試通過 ✅
- 參數相容性: Bloom + Halation 共存
- 波長依賴相反: Bloom (B>R) vs Halation (R>B)
- 空間尺度分離: ~40px vs 80-150px
- CineStill 極端案例: 1.88x 大光暈, 5x 強能量
```

---

### 3.3 H&D 特性曲線

#### 3.3.1 原理

**Hurter-Driffield Curve** 描述膠片的**非線性響應**：

```
曝光量 (H, Exposure) → 光學密度 (D, Density) → 透射率 (T, Transmittance)
```

標準公式（線性區段）：
```
D = γ × log₁₀(H) + D_fog
T = 10^(-D)
```

#### 3.3.2 三個區段

```
 D |           ╱--------  ← Shoulder（肩部，高光飽和）
   |         ╱
   |       ╱              ← Linear（線性區，γ 斜率）
   |     ╱
   |   ╱--                ← Toe（趾部，陰影壓縮）
   |__________________
      log₁₀(H)
```

- **Toe**：陰影區域，曲線向上彎曲（壓縮暗部對比，保留細節）
- **Linear**：主體區域，直線段（斜率 = γ，決定對比度）
- **Shoulder**：高光區域，曲線向下彎曲（防止過曝失去細節）

#### 3.3.3 Phos 實作

```python
def apply_hd_curve(response: np.ndarray, params: HDCurveParams) -> np.ndarray:
    """
    應用 H&D 特性曲線（簡化版）
    
    Args:
        response: 光譜響應 (0-1)
        params: H&D 曲線參數
        
    Returns:
        transmittance: 透射率 (0-1)
    """
    # 1. 避免 log(0)
    exposure = np.clip(response, 1e-10, None)
    
    # 2. 對數響應（線性區段）
    log_exposure = np.log10(exposure)
    density = params.gamma * log_exposure + offset
    
    # 3. Toe 曲線（Sigmoid 平滑過渡）
    if params.toe_enabled:
        toe_factor = 1 / (1 + np.exp(-params.toe_strength * (log_exposure + 2)))
        density = density * toe_factor
    
    # 4. Shoulder 曲線（指數飽和）
    if params.shoulder_enabled:
        shoulder_scale = params.D_max / params.shoulder_strength
        density = params.D_max * (1 - np.exp(-density / shoulder_scale))
    
    # 5. 限制密度範圍
    density = np.clip(density, params.D_min, params.D_max)
    
    # 6. 密度 → 透射率
    transmittance = 10 ** (-density)
    
    # 7. 正規化到 [0, 1]
    transmittance = (transmittance - T_min) / (T_max - T_min)
    
    return np.clip(transmittance, 0, 1)
```

**關鍵參數**：

| 參數 | 負片典型值 | 正片典型值 | 視覺效果 |
|-----|-----------|-----------|---------|
| `gamma` | 0.6-0.7 | 1.5-2.0 | 對比度（低→高）|
| `D_min` | 0.05-0.15 | 0.08-0.20 | 最暗處亮度 |
| `D_max` | 2.5-3.5 | 2.0-3.0 | 動態範圍上限 |
| `toe_strength` | 2.0-3.0 | 1.0-2.0 | 陰影柔和度 |
| `shoulder_strength` | 1.5-2.5 | 1.0-2.0 | 高光寬容度 |

#### 3.3.4 效果驗證

```python
# 測試：動態範圍壓縮（tests/test_hd_curve.py）
Input_Range = [1e-8, 1e0]  # 10^8 動態範圍
Output_Range = [0.001, 0.998]  # 壓縮至 ~10^3

Compression_Ratio = (1e8) / (0.998/0.001) ≈ 5.2×10^4

# 測試：Gamma 對比度影響
gamma = 0.6: 中調對比度 = 0.12 (柔和)
gamma = 2.0: 中調對比度 = 0.99 (鮮艷)
```

---

### 3.4 Poisson 顆粒噪聲

#### 3.4.1 物理原理

膠片顆粒的根源是**光子計數統計**與**銀鹽晶體分布**：

```
光子計數：N ~ Poisson(λ), where λ = 曝光量
標準差：σ = √λ
信噪比：SNR = λ / σ = √λ

相對噪聲：σ_rel = σ / λ = 1 / √λ
```

**關鍵特性**：
- 暗部（λ 小）：相對噪聲大 → 顆粒明顯
- 亮部（λ 大）：相對噪聲小 → 顆粒不明顯
- SNR ∝ √曝光量（物理正確）

#### 3.4.2 實作

```python
def generate_poisson_grain(response: np.ndarray, params: GrainParams) -> np.ndarray:
    """
    生成物理導向的 Poisson 顆粒噪聲
    
    Args:
        response: 光譜響應 (0-1)
        params: 顆粒參數
        
    Returns:
        grain: 顆粒噪聲 (-1 to 1)
    """
    # 1. 曝光量 → 光子計數期望值
    lambda_photons = response * params.exposure_level
    
    # 2. Poisson 分布近似（λ > 20 時用正態分布）
    # Poisson(λ) ≈ Normal(λ, √λ)
    photon_count = np.random.normal(lambda_photons, np.sqrt(lambda_photons))
    
    # 3. 相對噪聲
    noise_relative = (photon_count - lambda_photons) / (lambda_photons + 1e-10)
    
    # 4. 銀鹽顆粒空間相關性（高斯模糊）
    grain_size_pixels = params.grain_size * 0.5  # μm → 像素（簡化）
    noise_spatial = cv2.GaussianBlur(noise_relative, 
                                     ksize=(0, 0), 
                                     sigmaX=grain_size_pixels)
    
    # 5. 強度調整與正規化
    grain = noise_spatial * params.intensity
    grain = np.clip(grain, -1, 1)
    
    return grain
```

#### 3.4.3 藝術 vs 物理對比

| 特性 | 藝術模式 | Poisson 模式 |
|-----|---------|-------------|
| **噪聲峰值** | 中調（0.5 附近）| 暗部（低曝光）|
| **SNR 趨勢** | 平坦 | ∝ √曝光量 |
| **物理依據** | 無（視覺設計）| 光子統計 |
| **視覺效果** | 均勻、柔和 | 暗部粗糙、亮部細膩 |

測試數據：
```
區域        藝術模式 SNR    Poisson 模式 SNR
暗部(0.1)      0.80            0.15   ← Poisson 噪聲更明顯
中調(0.5)      0.25            0.71
亮部(0.9)      0.88            2.86   ← Poisson 噪聲更少
```

---

### 3.5 圖層混合

#### 3.5.1 原理

彩色膠片通常有**三層乳劑**（Red/Green/Blue 敏感層），最終影像為三層的**非線性組合**：

```python
Combined = (diffuse_r × Response_R^curve_r +
            diffuse_g × Response_G^curve_g +
            diffuse_b × Response_B^curve_b) / 3
```

#### 3.5.2 參數意義

- `diffuse_weight`（早期誤名 `diffuse_light`）：散射光權重
- `direct_weight`（早期誤名 `direct_light`）：直射光權重
- `response_curve`：非線性響應指數（類似 gamma）

**物理對應**（簡化）：
```
Total_Response = direct_weight × Direct_Transmission + 
                 diffuse_weight × Scattered_Light
```

**重要註記**：這些權重是**無量綱係數**，非真實光量（Watts 或 lux）。早期版本命名誤導，已在 v0.2.0 修正。

---

## 4. 計算模型

### 4.1 完整處理流程

```
輸入影像 (RGB, 0-255)
    ↓
[1] 光譜響應計算 (spectral_response)
    Response_R, Response_G, Response_B
    ↓
[2] 圖層組合 (combine_emulsion_layers)
    Combined = weighted_nonlinear_sum(Response_R/G/B)
    ↓
[3] Bloom 效果 (apply_bloom)
    ├─ 藝術模式：Combined + Gaussian_Blur(Combined)
    └─ 物理模式：Energy_Conserving_Scatter(Combined)
    ↓
[4] 顆粒噪聲 (apply_grain)
    ├─ 藝術模式：Weight-based Normal Noise
    └─ Poisson 模式：Photon_Count_Noise(Response_R/G/B)
    ↓
[5] H&D 曲線 (apply_hd_curve, 可選)
    Transmittance = HD_Transform(Combined)
    ↓
[6] 色調映射 (apply_tone_mapping)
    ├─ Reinhard: x / (1 + x)
    └─ Filmic: Shoulder_Toe_Curve(x)
    ↓
[7] 輸出處理
    ├─ Gamma 校正（顯示 gamma 2.2）
    ├─ Clipping & 正規化
    └─ 轉換為 RGB uint8
    ↓
輸出影像 (RGB, 0-255)
```

### 4.2 模式分支邏輯

```python
if film.physics_mode == PhysicsMode.ARTISTIC:
    # 保留現有行為（v0.1.x）
    bloom = apply_bloom_artistic(combined, film.bloom_params)
    grain = apply_grain_artistic(combined, film.grain_params)
    output = combined + bloom + grain
    # 跳過 H&D 曲線
    
elif film.physics_mode == PhysicsMode.PHYSICAL:
    # 物理導向（v0.2.0+）
    bloom = apply_bloom_conserved(combined, film.bloom_params)
    grain = generate_poisson_grain(response_r/g/b, film.grain_params)
    output_with_bloom_grain = combined + bloom + grain
    output = apply_hd_curve(output_with_bloom_grain, film.hd_curve_params)
    
elif film.physics_mode == PhysicsMode.HYBRID:
    # 自定義混合
    bloom = apply_bloom_X(...)  # 依 bloom_params.mode
    grain = apply_grain_X(...)  # 依 grain_params.mode
    output = ...
    if film.hd_curve_params.enabled:
        output = apply_hd_curve(output, film.hd_curve_params)
```

### 4.3 數值穩定性保障

```python
# 1. 避免 log(0) 或 log(負數)
exposure_safe = np.clip(exposure, 1e-10, None)
log_exposure = np.log10(exposure_safe)

# 2. 避免除以零
denominator_safe = denominator + 1e-10
result = numerator / denominator_safe

# 3. 範圍限制
output = np.clip(output, 0, 1)

# 4. NaN/Inf 檢測（開發階段）
assert not np.any(np.isnan(output))
assert not np.any(np.isinf(output))
```

---

## 5. 實作細節

### 5.1 關鍵函數位置

| 函數名稱 | 檔案 | 行數範圍 | 功能 |
|---------|-----|---------|------|
| `spectral_response()` | Phos_0.3.0.py | ~370-410 | 光譜響應計算 |
| `combine_emulsion_layers()` | Phos_0.3.0.py | ~692-723 | 圖層混合 |
| `apply_bloom_conserved()` | Phos_0.3.0.py | ~780-855 | 物理 Bloom |
| `apply_grain()` | Phos_0.3.0.py | ~471-538 | 顆粒噪聲入口 |
| `generate_poisson_grain()` | Phos_0.3.0.py | ~480-550 | Poisson 噪聲 |
| `apply_hd_curve()` | Phos_0.3.0.py | ~850-930 | H&D 曲線 |
| `optical_processing()` | Phos_0.3.0.py | ~973-1100 | 主流程整合 |

### 5.2 資料結構

```python
# film_models.py

@dataclass
class EmulsionLayer:
    """單層乳劑參數"""
    r_response_weight: float  # 紅光響應權重 (0-1)
    g_response_weight: float  # 綠光響應權重 (0-1)
    b_response_weight: float  # 藍光響應權重 (0-1)
    diffuse_weight: float     # 散射光權重係數
    direct_weight: float      # 直射光權重係數
    response_curve: float     # 非線性響應指數
    grain_intensity: float    # 顆粒強度

@dataclass
class FilmProfile:
    """完整膠片配置"""
    name: str
    red_layer: EmulsionLayer    # 紅敏層
    green_layer: EmulsionLayer  # 綠敏層
    blue_layer: EmulsionLayer   # 藍敏層
    panchromatic_layer: Optional[EmulsionLayer]  # 全色層（黑白）
    
    # 物理模式參數（v0.2.0+）
    physics_mode: PhysicsMode = PhysicsMode.ARTISTIC
    bloom_params: BloomParams = field(default_factory=BloomParams)
    grain_params: GrainParams = field(default_factory=GrainParams)
    hd_curve_params: HDCurveParams = field(default_factory=HDCurveParams)
    
    # 色調映射參數
    tone_mapping_params: ToneMappingParams = field(...)
```

### 5.3 效能優化技巧

#### 5.3.1 卷積加速

```python
# 方法 1: OpenCV GaussianBlur（最快）
bloom = cv2.GaussianBlur(image, ksize=(0, 0), sigmaX=radius)

# 方法 2: SciPy convolve2d（靈活）
from scipy.signal import convolve2d
bloom = convolve2d(image, PSF, mode='same', boundary='symm')

# 方法 3: FFT 卷積（大核心時）
from scipy.fft import fft2, ifft2
Bloom_FFT = ifft2(fft2(Image) * fft2(PSF))
```

Phos 預設使用 `cv2.GaussianBlur`（效能最佳）。

#### 5.3.2 並行處理

```python
# phos_core.py: 批次處理使用多核心
from concurrent.futures import ProcessPoolExecutor

def process_batch_parallel(images, film, num_workers=4):
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = executor.map(lambda img: process_image(img, film), images)
    return list(results)
```

#### 5.3.3 記憶體管理

```python
# 原地運算（減少記憶體分配）
response_r *= film.red_layer.diffuse_weight  # 原地乘法
response_r **= film.red_layer.response_curve  # 原地冪運算

# 釋放不需要的中間結果
del intermediate_result
```

---

## 6. 膠片建模

### 6.1 參數設計哲學

Phos 的膠片參數**並非**基於嚴格的實驗室測量，而是：

1. **文獻參考**：查閱廠商提供的 H&D 曲線、光譜敏感度圖
2. **視覺對標**：對比真實膠片掃描，調整參數至視覺接近
3. **藝術取向**：在物理正確性與美感間取得平衡

### 6.2 典型膠片參數範例

#### 6.2.1 Kodak Portra 400（人像負片）

```python
FilmProfile(
    name="Portra400",
    
    # 紅敏層（高權重，保留膚色細節）
    red_layer=EmulsionLayer(
        r_response_weight=0.32,  # 紅光主響應
        g_response_weight=0.12,  # 綠光交叉（柔和膚色）
        b_response_weight=0.06,  # 藍光輕微
        diffuse_weight=1.50,     # 高散射（柔和）
        direct_weight=0.92,
        response_curve=0.68,     # 低對比（負片典型）
        grain_intensity=0.12     # 細膩顆粒
    ),
    
    # H&D 曲線（寬容度高）
    hd_curve_params=HDCurveParams(
        gamma=0.62,              # 低對比（負片）
        D_min=0.08,              # 低霧度
        D_max=2.8,               # 高動態範圍
        toe_strength=2.5,        # 陰影柔和
        shoulder_strength=2.0    # 高光寬容
    ),
    
    # Bloom（輕微光暈）
    bloom_params=BloomParams(
        mode="physical",
        threshold=0.85,
        scattering_ratio=0.08    # 輕微散射
    ),
    
    # 顆粒（ISO 400 中等）
    grain_params=GrainParams(
        mode="poisson",
        grain_size=1.2,          # 微米
        intensity=0.6
    )
)
```

#### 6.2.2 Fujifilm Velvia 50（風景正片）

```python
FilmProfile(
    name="Velvia50",
    
    # 三層高對比、高飽和度
    red_layer=EmulsionLayer(
        r_response_weight=0.38,  # 高紅光響應
        g_response_weight=0.08,
        b_response_weight=0.04,
        diffuse_weight=1.20,     # 低散射（銳利）
        direct_weight=1.05,
        response_curve=1.50,     # 高對比（正片）
        grain_intensity=0.05     # 極細膩
    ),
    
    # H&D 曲線（高對比）
    hd_curve_params=HDCurveParams(
        gamma=1.85,              # 高對比（正片）
        D_min=0.10,
        D_max=2.5,
        toe_strength=1.0,        # 陰影深邃
        shoulder_strength=1.2
    ),
    
    # Bloom（極少）
    bloom_params=BloomParams(
        mode="physical",
        threshold=0.92,
        scattering_ratio=0.03
    ),
    
    # 顆粒（ISO 50 極細）
    grain_params=GrainParams(
        mode="poisson",
        grain_size=0.5,
        intensity=0.3
    )
)
```

### 6.3 黑白膠片特殊處理

```python
# 黑白膠片只有一層全色乳劑
FilmProfile(
    name="HP5Plus400",
    panchromatic_layer=EmulsionLayer(
        r_response_weight=0.35,  # 偏紅敏（經典黑白）
        g_response_weight=0.33,
        b_response_weight=0.28,
        # ... 其他參數
    ),
    red_layer=None,   # 彩色層留空
    green_layer=None,
    blue_layer=None
)
```

---

## 7. 三種模式

### 7.1 ARTISTIC 模式（預設）

**設計目標**：視覺美感優先，保留 v0.1.x 的討喜效果。

**特點**：
- ✅ Bloom：加法模式（能量增加 +10%）
- ✅ 顆粒：中調峰值（視覺均勻）
- ❌ H&D 曲線：不啟用
- ❌ 能量守恆：不保證

**適用場景**：
- 快速出圖（社交媒體、日常分享）
- 追求「華麗」、「討喜」效果
- 不在意物理正確性

### 7.2 PHYSICAL 模式（v0.2.0+）

**設計目標**：物理正確性優先，模擬真實膠片行為。

**特點**：
- ✅ Bloom：能量守恆（PSF 正規化）
- ✅ 顆粒：Poisson 統計（暗部峰值）
- ✅ H&D 曲線：對數響應 + Toe + Shoulder
- ✅ 能量守恆：< 0.01% 誤差

**適用場景**：
- 專業作品（需要物理一致性）
- 科學可視化（研究、教學）
- 模擬真實膠片特性

### 7.3 HYBRID 模式（實驗性）

**設計目標**：藝術與物理自由混合。

**範例配置**：

```python
# 範例 1：只啟用 H&D 曲線（保留藝術 Bloom/顆粒）
film.physics_mode = PhysicsMode.HYBRID
film.hd_curve_params.enabled = True
film.bloom_params.mode = "artistic"
film.grain_params.mode = "artistic"

# 範例 2：物理 Bloom + 藝術顆粒
film.bloom_params.mode = "physical"
film.grain_params.mode = "artistic"
film.hd_curve_params.enabled = False
```

---

## 8. 測試與驗證

### 8.1 測試架構

```
tests/
├── test_energy_conservation.py      # 能量守恆測試（5 tests）
├── test_hd_curve.py                  # H&D 曲線測試（8 tests）
├── test_poisson_grain.py             # Poisson 噪聲測試（7 tests）
├── test_integration.py               # 整合測試（6 tests）
├── test_mie_validation.py            # Mie 散射驗證（7 tests）✨ v0.3.3
├── test_mie_halation_integration.py  # Bloom + Halation 整合（7 tests）✨ v0.3.3
├── test_medium_physics_e2e.py        # 中等物理端到端（7 tests）✨ v0.3.2
├── test_halation.py                  # Halation 獨立測試（6 tests）✨ v0.3.2
└── test_p0_2_halation_beer_lambert.py # Beer-Lambert 驗證（5 tests）✨ v0.3.2

總計：183 tests，98.8% 通過率 (180 passed, 2 failed, 1 error)
```

**v0.3.3 新增測試**：
- ✅ Mie 散射能量比例驗證（B/R = 3.62x，目標 3.5x）
- ✅ PSF 寬度比例驗證（B/R = 1.34x，目標 1.27x）
- ✅ 雙段 PSF 結構測試（核心 + 尾部）
- ✅ Bloom + Halation 整合測試（空間分離、波長依賴相反）
- ✅ CineStill 極端案例驗證（1.88x 大光暈，5x 強能量）

### 8.2 關鍵測試案例

#### 8.2.1 能量守恆測試

```python
def test_energy_conservation():
    """驗證物理模式的 Bloom 不增加總能量"""
    image = np.random.rand(100, 100) * 0.5
    
    E_in = np.sum(image)
    bloom = apply_bloom_conserved(image, params)
    E_out = np.sum(bloom)
    
    error = abs(E_out - E_in) / E_in
    assert error < 0.0001, f"能量誤差: {error*100:.4f}%"
```

#### 8.2.2 H&D 曲線單調性測試

```python
def test_hd_curve_monotonicity():
    """驗證 H&D 曲線的單調遞減特性（曝光↑ → 透射率↓）"""
    exposures = np.logspace(-3, 0, 50)  # 0.001 ~ 1.0
    transmittances = [apply_hd_curve(e, params) for e in exposures]
    
    # 檢查單調性
    for i in range(len(transmittances) - 1):
        assert transmittances[i] >= transmittances[i+1], "違反單調性"
```

#### 8.2.3 Poisson SNR 測試

```python
def test_poisson_snr_vs_exposure():
    """驗證 SNR ∝ √曝光量"""
    exposures = [0.1, 0.5, 0.9]
    SNRs = []
    
    for exp in exposures:
        image = np.full((100, 100), exp)
        grain = generate_poisson_grain(image, params)
        SNR = exp / np.std(grain)
        SNRs.append(SNR)
    
    # 檢查 SNR 遞增
    assert SNRs[0] < SNRs[1] < SNRs[2], "Poisson SNR 特性不符"
```

#### 8.2.4 Mie 散射驗證測試 (v0.3.3)

```python
def test_mie_energy_ratios():
    """驗證 Mie 散射能量比例（λ^-3.5）"""
    # 計算藍/紅能量比例
    ratio_br = (650 / 450) ** 3.5
    
    # 實測比例
    measured_ratio = measured_energy_blue / measured_energy_red
    
    # 容差 ±10%
    assert 3.2 < measured_ratio < 3.8, f"能量比例: {measured_ratio:.2f}x"
    assert abs(measured_ratio - ratio_br) / ratio_br < 0.1

def test_psf_width_ratios():
    """驗證 PSF 寬度比例（λ^-0.8）"""
    # 計算藍/紅寬度比例
    ratio_br = (650 / 450) ** 0.8
    
    # 實測比例
    measured_ratio = measured_width_blue / measured_width_red
    
    # 容差 ±10%
    assert 1.20 < measured_ratio < 1.35, f"寬度比例: {measured_ratio:.2f}x"
```

#### 8.2.5 Bloom + Halation 整合測試 (v0.3.3)

```python
def test_bloom_halation_wavelength_opposite():
    """驗證 Bloom 與 Halation 的波長依賴相反"""
    # Bloom: 藍 > 紅（Mie 散射）
    bloom_ratio = bloom_energy_blue / bloom_energy_red
    assert bloom_ratio > 2.0, "Bloom 應該藍光更強"
    
    # Halation: 紅 > 藍（Beer-Lambert 穿透）
    halation_ratio = halation_energy_red / halation_energy_blue
    assert halation_ratio > 1.2, "Halation 應該紅光更強"

def test_spatial_scale_separation():
    """驗證 Bloom 與 Halation 的空間尺度分離"""
    # Bloom PSF: ~40 px
    bloom_hwhm = measure_psf_hwhm(bloom_psf)
    assert 30 < bloom_hwhm < 50, f"Bloom HWHM: {bloom_hwhm}px"
    
    # Halation PSF: 80-150 px
    halation_hwhm = measure_psf_hwhm(halation_psf)
    assert 70 < halation_hwhm < 160, f"Halation HWHM: {halation_hwhm}px"
    
    # 比例: 2.0x ~ 3.75x
    ratio = halation_hwhm / bloom_hwhm
    assert 2.0 < ratio < 4.0, f"空間尺度比: {ratio:.2f}x"
```

### 8.3 數值驗證

| 測試項目 | 目標 | 實測 | 狀態 |
|---------|-----|------|------|
| 能量守恆誤差 | < 0.01% | 0.0000% | ✅ |
| H&D 動態範圍壓縮 | ~10^4 | 5.2×10^4 | ✅ |
| Poisson 暗部 SNR | < 0.5 | 0.15 | ✅ |
| Poisson 亮部 SNR | > 2.0 | 2.86 | ✅ |
| FilmProfile 載入 | 13/13 | 13/13 | ✅ |
| 邊界條件（全黑/全白）| 無 NaN | 無 NaN | ✅ |
| **Mie 能量比 (B/R)** ✨ | **3.5x ±10%** | **3.62x** | ✅ |
| **PSF 寬度比 (B/R)** ✨ | **1.27x ±10%** | **1.34x** | ✅ |
| **Bloom 空間尺度** ✨ | **~40 px** | **35-45 px** | ✅ |
| **Halation 空間尺度** ✨ | **80-150 px** | **80-150 px** | ✅ |
| **Beer-Lambert 穿透** ✨ | **f_h(R) > f_h(B)** | **1.39x (CS), 12.7x (Portra)** | ✅ |
| **全局測試通過率** | **> 95%** | **98.8% (180/183)** | ✅ |

✨ = v0.3.2-0.3.3 新增驗證項目

---

## 9. 效能優化

### 9.1 效能基準

| 影像尺寸 | 藝術模式 | 物理模式 | Mie+Halation (v0.3.3) | 增量 |
|---------|---------|---------|---------------------|------|
| 1000×1000 | 0.18s | 0.20s | 0.21s | +5% |
| 2000×3000 | 0.70s | 0.76s | 0.80s | +5% |
| 4000×6000 | 2.80s | 3.05s | 3.20s | +5% |

測試環境：M1 MacBook Pro, 8 cores, 16GB RAM

**v0.3.3 效能影響**：
- Mie 雙段 PSF（核心 + 尾部）：+3%
- Halation 獨立計算（Beer-Lambert）：+2%
- 總增量：+5%（仍遠低於 10s 目標）

### 9.2 瓶頸分析

```python
# Profiling 結果（2000×3000 影像）

Function                    Time      %
-----------------------------------------
cv2.GaussianBlur           250ms    33%  ← Bloom 卷積
spectral_response          180ms    24%  ← 矩陣乘法
apply_hd_curve             120ms    16%  ← log10 運算
generate_poisson_grain      80ms    11%  ← 隨機數生成
combine_emulsion_layers     60ms     8%  ← 冪運算
其他                        60ms     8%
-----------------------------------------
Total (Physical Mode)      750ms   100%
```

### 9.3 優化策略

#### 9.3.1 已實作

- ✅ OpenCV 卷積（最快實作）
- ✅ NumPy 向量化運算（避免 Python 迴圈）
- ✅ 原地運算（減少記憶體分配）
- ✅ LRU 快取（FilmProfile 載入）

#### 9.3.2 未來改進

- 🔲 GPU 加速（CuPy / PyTorch）
- 🔲 C++ 擴展（關鍵函數）
- 🔲 多解析度處理（先處理縮圖）
- 🔲 增量計算（批次處理時共享 PSF）

---

## 10. 限制與未來方向

### 10.1 當前限制

#### 10.1.1 物理簡化

| 真實現象 | Phos 簡化 | 影響 |
|---------|----------|------|
| **波長依賴散射** | 無（RGB 獨立）| 缺少「藍光散射 > 紅光」效果 |
| **角度依賴** | 無（假設 Lambertian）| 無 Fresnel 反射 |
| **多次散射** | 無（單次卷積）| 長距離光暈尾部略短 |
| **Halation 分離** | 無（合併於 Bloom）| 無法獨立調整背層反射 |
| **互易律失效** | 無 | 長曝光/高速快門行為相同 |

#### 10.1.2 數值近似

- **H&D Toe/Shoulder**：使用 Sigmoid/Exponential 近似，非化學反應動力學
- **Poisson 正態近似**：λ < 20 時精度降低（極暗區域）
- **PSF 模型**：經驗公式（Gaussian/Exponential），非完整 Mie 理論

### 10.2 未來改進方向

#### 10.2.1 短期（v0.3.1-0.4.0）

- **UI 整合**：Streamlit 物理模式參數介面
- **膠片庫擴展**：新增 20+ 款經典膠片
- **批次處理優化**：多核心並行處理
- **即時預覽**：低解析度快速預覽
- ~~**波長依賴散射**：分離 R/G/B 的 PSF 參數~~ ✅ 完成於 v0.3.3 (Decision #014)
- ~~**Halation 獨立模型**：背層反射單獨計算~~ ✅ 完成於 v0.3.2 (Decision #012)

#### 10.2.2 中期（v0.5.0-0.6.0）

- **31 通道光譜積分**：更精確的色彩科學（380-780nm，步長 10nm）
- **Mie 散射查表**：預計算尺寸分布的散射相函數
- **互易律失效**：模擬長曝光特性
- **色溫校正**：Tungsten/Daylight 色彩轉換
- **FFT 加速卷積**：大半徑 PSF 效能優化

#### 10.2.3 長期（v1.0+）

- **完整 RTE 求解器**：輻射傳輸方程數值求解
- **光譜渲染**：380-780nm 波長分辨
- **GPU 加速**：CUDA/Metal 實作
- **機器學習輔助**：從真實膠片掃描學習參數

### 10.3 不會做的事

- ❌ **完全物理模擬**：非 Phos 定位（計算成本過高）
- ❌ **取代 LUT**：兩者共存（LUT 適合固定風格）
- ❌ **RAW 格式處理**：專注於 JPEG/PNG（已曝光影像）

---

## 附錄 A：術語表

| 術語 | 英文 | 定義 |
|-----|------|------|
| 光譜響應 | Spectral Response | 感光材料對不同波長的敏感度 |
| 光學密度 | Optical Density (D) | log₁₀(1/T)，T 為透射率 |
| H&D 曲線 | Hurter-Driffield Curve | 曝光量-密度特性曲線 |
| Bloom | Bloom | 膠片乳劑內的光散射 |
| Halation | Halation | 光線穿透乳劑後在背層反射 |
| PSF | Point Spread Function | 點光源成像後的擴散函數 |
| 顆粒 | Grain | 銀鹽晶體造成的噪聲 |
| Poisson 分布 | Poisson Distribution | 描述低頻率隨機事件的機率分布 |
| 色調映射 | Tone Mapping | HDR → SDR 的動態範圍壓縮 |
| 互易律失效 | Reciprocity Failure | 長/短曝光時的非線性響應 |

---

## 附錄 B：參數快速查詢

### Bloom 參數

```python
# 自然風格（輕微光暈）
bloom_params = BloomParams(
    mode="physical",
    threshold=0.85,
    scattering_ratio=0.08
)

# 電影風格（明顯光暈）
bloom_params = BloomParams(
    mode="physical",
    threshold=0.70,
    scattering_ratio=0.20
)

# Mie 修正模式（v0.3.3+，物理精確）
bloom_params = BloomParams(
    mode="physical",
    threshold=0.80,
    scattering_ratio=0.08,
    energy_conservation=True,
    energy_wavelength_exponent=3.5,      # Mie 散射（非 Rayleigh 的 4.0）
    psf_width_exponent=0.8,               # 小角散射（非 2.0）
    psf_dual_segment=True,                # 雙段 PSF（核心 + 尾部）
    psf_core_ratio_r=0.75,                # 紅光核心比例
    psf_core_ratio_g=0.70,                # 綠光核心比例
    psf_core_ratio_b=0.65,                # 藍光核心比例
    base_sigma_core=15.0,                 # 核心基準寬度
    base_kappa_tail=40.0                  # 尾部基準尺度
)
```

### Halation 參數 (v0.3.2+)

```python
# 標準膠片（有 AH 層，輕微 Halation）
halation_params = HalationParams(
    enabled=True,
    emulsion_transmittance_r=0.92,       # 乳劑層紅光穿透率
    emulsion_transmittance_g=0.87,       # 乳劑層綠光穿透率
    emulsion_transmittance_b=0.78,       # 乳劑層藍光穿透率
    base_transmittance=0.98,             # 基底層穿透率（灰度）
    ah_layer_transmittance_r=0.30,       # AH 層紅光穿透率
    ah_layer_transmittance_g=0.10,       # AH 層綠光穿透率
    ah_layer_transmittance_b=0.05,       # AH 層藍光穿透率（強抑制）
    backplate_reflectance=0.30,          # 背襯反射率
    psf_radius=80,                       # PSF 半徑（像素）
    psf_type="exponential",              # PSF 類型
    psf_decay_rate=0.15,                 # 指數衰減率
    energy_fraction=0.03                 # Halation 能量比例（3%）
)

# CineStill 風格（無 AH 層，極強 Halation）
halation_params = HalationParams(
    enabled=True,
    emulsion_transmittance_r=0.92,
    emulsion_transmittance_g=0.87,
    emulsion_transmittance_b=0.78,
    base_transmittance=0.98,
    ah_layer_transmittance_r=1.0,        # 無 AH 層（完全透明）
    ah_layer_transmittance_g=1.0,
    ah_layer_transmittance_b=1.0,
    backplate_reflectance=0.30,
    psf_radius=150,                      # 大光暈（1.88x 標準）
    psf_type="exponential",
    psf_decay_rate=0.15,
    energy_fraction=0.15                 # 強能量（5x 標準）
)
```

### H&D 曲線參數

```python
# 負片風格（柔和、寬容度高）
hd_params = HDCurveParams(
    gamma=0.65,
    D_min=0.08,
    D_max=3.0,
    toe_strength=2.5,
    shoulder_strength=2.0
)

# 正片風格（鮮艷、對比強）
hd_params = HDCurveParams(
    gamma=1.80,
    D_min=0.10,
    D_max=2.5,
    toe_strength=1.0,
    shoulder_strength=1.2
)
```

### 顆粒參數

```python
# ISO 100（極細膩）
grain_params = GrainParams(
    mode="poisson",
    grain_size=0.5,
    intensity=0.3
)

# ISO 400（中等顆粒）
grain_params = GrainParams(
    mode="poisson",
    grain_size=1.5,
    intensity=0.8
)

# ISO 1600+（粗糙顆粒）
grain_params = GrainParams(
    mode="poisson",
    grain_size=2.5,
    intensity=1.5
)
```

---

## 附錄 C：參考文獻

### 學術論文

1. **Beer-Lambert Law**: Swinehart, D. F. (1962). "The Beer-Lambert Law". *Journal of Chemical Education*.
2. **H&D Curve Theory**: Hurter, F., & Driffield, V. C. (1890). "Photo-Chemical Investigations and a New Method of Determination of the Sensitiveness of Photographic Plates". *Journal of the Society of Chemical Industry*.
3. **Mie Scattering Theory**: Mie, G. (1908). "Beiträge zur Optik trüber Medien, speziell kolloidaler Metallösungen". *Annalen der Physik*. 330(3): 377–445.
4. **Radiative Transfer**: Chandrasekhar, S. (1960). *Radiative Transfer*. Dover Publications.
5. **Poisson Statistics**: Robbins, H. (1955). "A Remark on Stirling's Formula". *The American Mathematical Monthly*.
6. **Miepython Library**: Prahl, S. (2024). "miepython: A Python module for Mie scattering calculations". [GitHub](https://github.com/scottprahl/miepython).

### 技術文檔

- Kodak Publication H-1: *Kodak Professional Black-and-White Films*
- Ilford Technical Document: *Understanding Film Sensitometry*
- Fujifilm: *Fujichrome Velvia Professional Film Technical Data*
- CineStill: *Technical Information - C-41 Process Color Negative Films*

### 線上資源

- Charles Poynton: [Gamma FAQ](http://poynton.ca/GammaFAQ.html)
- Bruce Lindbloom: [Color Space Conversions](http://brucelindbloom.com/)
- Cambridge in Colour: [Understanding Film Grain](https://www.cambridgeincolour.com/)
- Philip Laven: [MiePlot - Mie Scattering Calculator](http://www.philiplaven.com/mieplot.htm)

### Phos 專案決策文檔

- Decision #012: Beer-Lambert 分層穿透率結構 (2025-12-19)
- Decision #014: Mie 散射修正（Rayleigh → Mie）(2025-12-22)
- Decision #022: 棄用參數測試修復 (2025-12-22)

---

**文檔結束**

**維護**: lyco_p@163.com  
**版本**: v0.3.0  
**授權**: AGPL-3.0  
**專案地址**: https://github.com/LYCO6273/Phos

---

*最後更新：2025-12-19*
