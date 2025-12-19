# Phos 物理模型審查報告

**審查日期**: 2025-12-19  
**最後更新**: 2025-12-19（修正散射理論與測試斷言錯誤）  
**審查者**: 物理學家 (計算光學專家)  
**專案版本**: v0.2.0  
**審查範圍**: 簡化光學模型的物理一致性

> **聲明**：本報告針對 Phos 作為「簡化光學模型」的物理一致性進行審查，而非要求其成為嚴格的物理模擬器。審查重點為：量綱一致性、能量守恆、參數語義清晰度，以及與膠片成像的定性對應關係。

---

## 📋 執行摘要 Executive Summary

Phos 專案聲稱基於「計算光學」原理模擬胶片成像，但經過詳細審查，發現**多處物理模型存在嚴重問題**，包括量綱不一致、能量不守恆、以及缺乏物理意義的參數設定。

**總體評級**: ⚠️ **需要重大修正** (3/10)

**關鍵問題**:
1. ❌ 光度計算缺乏物理單位
2. ❌ 能量守恆未被遵守
3. ❌ 吸收係數物理意義不明確
4. ❌ 光暈效果缺乏光學理論基礎
5. ⚠️ Tone mapping 與光學模型混淆

---

## 🔬 詳細審查

### 1. 光度計算 (Luminance Calculation)

#### 📍 位置
`Phos_0.2.0.py`, lines 368-407

#### 📝 當前實現
```python
def luminance(image: np.ndarray, film: FilmProfile):
    # 分離 RGB 通道
    r_float = r.astype(np.float32) / 255.0
    g_float = g.astype(np.float32) / 255.0
    b_float = b.astype(np.float32) / 255.0
    
    # 模擬不同乳劑層的吸收特性（光譜敏感度的線性組合）
    lux_r = r_r * r_float + r_g * g_float + r_b * b_float
    lux_g = g_r * r_float + g_g * g_float + g_b * b_float
    lux_b = b_r * r_float + b_g * g_float + b_b * b_float
```

#### ❌ 物理問題

**1. 量綱混亂 (Dimensional Inconsistency)**

**問題**: 函數名為 `luminance`（光度），但實際上計算的不是真實的光度。

**物理定義**:
- **光度 (Luminance)**: $L_v = \frac{d^2\Phi_v}{dA \cdot d\Omega \cdot \cos\theta}$，單位：cd/m²（坎德拉/平方米）
- **輻射度 (Radiance)**: $L_e = \frac{d^2\Phi_e}{dA \cdot d\Omega \cdot \cos\theta}$，單位：W/(m²·sr)

**當前實現**:
- 輸入：RGB 值（無量綱，0-1 範圍）
- 輸出：`lux_r/g/b`（無量綱，0-1 範圍）
- **沒有任何物理單位**

**建議**:
```python
def spectral_response(image: np.ndarray, film: FilmProfile):
    """
    計算胶片感光層的光譜響應（Spectral Response）
    
    注意：這不是真實的光度計算，而是數位影像的相對響應。
    若要計算真實光度，需要：
    1. 相機的光譜響應函數
    2. 場景的絕對照度
    3. 曝光參數（ISO, 快門速度, 光圈）
    """
```

**2. "吸收係數"的物理意義不明確**

**當前參數** (`film_models.py`):
```python
red_layer=EmulsionLayer(
    r_absorption=0.77,  # 這是什麼？
    g_absorption=0.12,
    b_absorption=0.18,
    ...
)
```

**物理問題**:
- 這些數字沒有物理意義：
  - 如果是「吸收係數」，應該是 $\alpha$（單位：1/m）
  - 如果是「吸收率」，應該滿足 Beer-Lambert Law: $I = I_0 e^{-\alpha d}$
  - 如果是「量子效率」（Quantum Efficiency），應該是光子轉電子的比例

**真實的胶片光譜響應**:
- 應該是**光譜敏感度曲線** $S(\lambda)$，單位：相對響應 (arbitrary units)
- 彩色胶片有三層乳劑，每層對應不同波長峰值：
  - 紅敏層：峰值 ~600-700 nm
  - 綠敏層：峰值 ~500-600 nm
  - 藍敏層：峰值 ~400-500 nm

**建議**:
```python
@dataclass
class SpectralSensitivity:
    """光譜敏感度（無量綱相對響應）"""
    lambda_peak: float  # 峰值波長 (nm)
    response_r: float   # 紅色通道相對響應 (0-1)
    response_g: float   # 綠色通道相對響應 (0-1)
    response_b: float   # 藍色通道相對響應 (0-1)
    bandwidth: float    # 響應帶寬 (nm)
```

**3. 線性組合的物理基礎**

**當前公式**:
```python
lux_r = r_r * r_float + r_g * g_float + r_b * b_float
```

**物理解釋**:
- 這實際上是**色彩空間轉換**，不是光學過程
- 類似於從 RGB 轉換到 XYZ 色彩空間
- 但缺乏標準化（不遵守 CIE 標準）

**真實的光學過程** (Lambert-Beer Law):
$$
I(\lambda) = I_0(\lambda) \cdot e^{-\sum_i \alpha_i(\lambda) \cdot d_i}
$$

其中：
- $I_0(\lambda)$: 入射光譜
- $\alpha_i(\lambda)$: 第 i 層的吸收係數（波長相關）
- $d_i$: 第 i 層厚度

---

### 2. 光暈效果 (Bloom/Halation)

#### 📍 位置
`Phos_0.2.0.py`, lines 654-689

#### 📝 當前實現
```python
def apply_bloom_to_channel(lux, sens, rads, strg, base, blur_scale, blur_sigma_scale):
    # 創建權重（高光區域權重更高）
    weights = (base + lux ** 2) * sens
    
    # 創建光暈層（使用高斯模糊模擬光的擴散）
    bloom_layer = cv2.GaussianBlur(lux * weights, (ksize, ksize), sens * blur_sigma_scale)
    
    # 應用光暈
    bloom_effect = bloom_layer * weights * strg
    bloom_effect = bloom_effect / (1.0 + bloom_effect)  # 避免過曝
```

#### ⚠️ 物理問題

**1. "Halation" vs "Bloom" 的混淆**

**真實的胶片光暈 (Halation)**:
- **物理原因**: 光線穿過乳劑層 → 反射於片基背面 → 再次曝光乳劑層
- **特徵**: 僅出現在**高光周圍**，形成紅色或黃色光暈
- **方向性**: 具有特定的角度分布（不是簡單的高斯分布）

**數位影像的 Bloom**:
- **物理原因**: CCD/CMOS 電荷溢出（Charge Blooming）
- **特徵**: 沿垂直或水平方向擴散（取決於感光元件結構）

**當前實現的問題**:
- 使用高斯模糊模擬「光的擴散」是**過度簡化**
- 真實的點擴散函數 (PSF) 應該考慮：
  - 菲涅耳衍射
  - 多層乳劑的散射
  - 片基的反射率

**2. 權重公式缺乏物理依據**

**當前公式**:
```python
weights = (base + lux ** 2) * sens
```

**物理問題**:
- 為什麼是 `lux ** 2`？沒有物理解釋
- 為什麼高光區域權重更高？應該是「曝光量超過閾值才產生光暈」
- `base` 和 `sens` 的物理意義是什麼？

**真實的散射機制**：

膠片中的光散射主要來自：
1. **乳劑層內的 Rayleigh 散射**（粒徑 << 波長）：
   - 相函數：$P(\theta) \propto (1 + \cos^2\theta)$
   - 波長依賴：散射強度 $\propto \lambda^{-4}$（短波長散射更強）
   - 適用於銀鹽微晶（~0.1-1 μm）與藍光（~450 nm）

2. **背層反射造成的 Halation**：
   - 光線穿透乳劑層 → 片基背面反射 → 二次曝光
   - 特徵：高光周圍的紅/黃色暈（長波長穿透力強）
   - 非對稱 PSF（依賴入射角與片基厚度）

3. **工程近似**：
   - 對膠片成像，嚴格的 Mie 理論計算過於複雜（需數值求解）
   - 實用方法：以經驗 PSF（高斯核、雙指數核）近似，並強制能量守恆
   - 關鍵：PSF 需正規化（$\int PSF = 1$），確保散射不增減總能量

**3. 能量守恆問題**

**當前實現**:
```python
bloom_effect = bloom_layer * weights * strg
bloom_effect = bloom_effect / (1.0 + bloom_effect)  # 避免過曝
```

**物理問題**:
- 光暈效果應該**從高光區域吸取能量**，然後**重新分配到周圍**
- 當前實現只是「增加」能量，沒有「減去」原始高光的能量
- **違反能量守恆定律**

**正確的能量守恆**:
$$
\int I_{input}(x, y) \, dx \, dy = \int I_{output}(x, y) \, dx \, dy
$$

**建議實現**:
```python
# 1. 計算散射能量（從高光區域）
scattered_energy = extract_highlights(lux) * scattering_coefficient

# 2. 應用點擴散函數（PSF）
bloom_layer = convolve(scattered_energy, PSF)

# 3. 從原始影像減去散射能量
lux_corrected = lux - scattered_energy

# 4. 加上散射後的光暈
result = lux_corrected + bloom_layer
```

---

### 3. 胶片顆粒 (Film Grain)

#### 📍 位置
`Phos_0.2.0.py`, lines 426-456

#### 📝 當前實現
```python
def generate_grain_for_channel(lux_channel, sens):
    # 創建正負噪聲（使用平方正態分佈產生更自然的顆粒）
    noise = np.random.normal(0, 1, lux_channel.shape)
    noise = noise ** 2
    noise = noise * np.random.choice([-1, 1], lux_channel.shape)
    
    # 創建權重圖（中等亮度區域權重最高）
    weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
    
    # 應用權重和敏感度
    weighted_noise = noise * weights * sens
```

#### ✅ 相對合理，但有改進空間

**1. 噪聲分布的選擇**

**當前**: 平方正態分布 + 隨機正負號

**物理背景**:
- 胶片顆粒源自**銀鹽晶體的隨機分布**（Poisson Process）
- 真實的噪聲應該是 **Poisson 噪聲**（光子噪聲）+ **Grain Noise**

**Poisson 噪聲**:
$$
\sigma_{Poisson} = \sqrt{N_{photons}}
$$

**建議**:
```python
# 使用 Poisson 分布模擬光子噪聲
photon_count = lux_channel * exposure_level  # 假設線性關係
poisson_noise = np.random.poisson(photon_count) - photon_count

# 銀鹽顆粒噪聲（與亮度相關）
grain_size = film.grain_size  # 微米
grain_density = film.grain_density  # 顆粒/mm²
grain_noise = generate_grain_pattern(grain_size, grain_density)
```

**2. 權重分布的物理意義**

**當前**: 中等亮度區域權重最高
```python
weights = (0.5 - np.abs(lux_channel - 0.5)) * 2
```

**物理觀察**:
- 這與實際觀察**部分一致**：胶片顆粒在中間調最明顯
- 但真實原因是：
  - **陰影**: 噪聲被低訊號淹沒（低 SNR）
  - **高光**: 顆粒被飽和掩蓋
  - **中間調**: 噪聲最可見（最佳 SNR）

**建議**: 使用基於訊噪比 (SNR) 的模型
```python
# 計算訊噪比
signal = lux_channel * exposure_level
noise_std = np.sqrt(signal + dark_current + read_noise)
SNR = signal / noise_std

# 顆粒可見度與 SNR 相關
visibility = SNR / (1 + SNR)  # 0-1 範圍
```

---

### 4. 散射光與直射光組合

#### 📍 位置
`Phos_0.2.0.py`, lines 692-723

#### 📝 當前實現
```python
def combine_layers_for_channel(bloom, lux, layer, ...):
    # 散射光 + 直射光（非線性響應）
    result = bloom * layer.diffuse_light + np.power(lux, layer.response_curve) * layer.direct_light
```

#### ❌ 物理問題

**1. "diffuse_light" 和 "direct_light" 的物理意義不明確**

**參數值** (`film_models.py`):
```python
EmulsionLayer(
    diffuse_light=1.48,  # 這是什麼？為什麼 > 1？
    direct_light=0.95,   # 這是什麼？
    response_curve=1.18, # 這是什麼？
    ...
)
```

**物理問題**:
- `diffuse_light=1.48` 代表什麼？如果是「權重」，為什麼大於 1？
- 如果是「散射係數」，單位應該是什麼？
- 為什麼「散射光」和「直射光」可以**直接相加**？

**真實的光學模型**:

散射光和直射光應該遵守 **Radiative Transfer Equation (RTE)**:

$$
\frac{dI}{ds} = -\mu_t I + \mu_s \int I(\mathbf{s}') p(\mathbf{s}' \rightarrow \mathbf{s}) \, d\Omega'
$$

其中：
- $\mu_t$: 總衰減係數（吸收 + 散射）
- $\mu_s$: 散射係數
- $p$: 相函數（散射角度分布）

**簡化模型**（適用於胶片）:
$$
I_{total} = I_{direct} \cdot e^{-\tau} + I_{scattered}
$$

其中：
- $\tau = \mu_t \cdot d$: 光學厚度
- $I_{direct} \cdot e^{-\tau}$: 經過衰減的直射光
- $I_{scattered}$: 多次散射的累積

**2. "response_curve" 的物理意義**

**當前實現**:
```python
np.power(lux, layer.response_curve)
```

**物理解釋**:
- 這似乎是在模擬**胶片的非線性響應**（Film Characteristic Curve）
- 但真實的胶片響應應該是 **H&D 曲線**（Hurter-Driffield Curve）:

$$
D = \gamma \log_{10}(H) + D_{fog}
$$

其中：
- $D$: 光學密度（Optical Density）
- $H$: 曝光量（Exposure）
- $\gamma$: 胶片對比度
- $D_{fog}$: 基底霧度

**建議**:
```python
def film_response(exposure, film_params):
    """
    胶片特性曲線（H&D Curve）
    
    Args:
        exposure: 曝光量（相對單位）
        film_params: 胶片參數（gamma, Dmin, Dmax）
    
    Returns:
        optical_density: 光學密度
    """
    # 對數響應（胶片的核心特性）
    density = film_params.gamma * np.log10(exposure + 1e-6) + film_params.Dmin
    
    # 限制在動態範圍內
    density = np.clip(density, film_params.Dmin, film_params.Dmax)
    
    return density
```

---

### 5. Tone Mapping 的物理意義

#### 📍 位置
`Phos_0.2.0.py`, lines 492-623

#### ⚠️ 概念混淆

**問題**: Tone Mapping 是**顯示端的技術**，不是**胶片的物理特性**

**Tone Mapping 的目的**:
- 將 HDR（高動態範圍）影像映射到 LDR（低動態範圍）顯示器
- 這是**後處理技術**，與胶片的物理過程無關

**胶片的真實過程**:
1. **曝光**: 光子 → 銀鹽晶體 → 潛影
2. **顯影**: 化學反應 → 銀顆粒沉積 → 光學密度
3. **掃描/投影**: 光學密度 → 透射光強度 → 數位信號

**當前實現的問題**:
- Reinhard 和 Filmic 是**數位影像處理技術**
- 它們模擬的是**人眼對亮度的感知**或**電影膠片的色調**
- 不應該與「光度計算」、「光暈效果」混在一起

**建議**:
- 將 Tone Mapping 視為**獨立的後處理步驟**
- 先完成「物理模擬」（光學過程），再進行「色調映射」（顯示優化）

```python
# 物理模擬
optical_density = film_simulation(image, film_params)

# 色調映射（可選）
display_image = tone_mapping(optical_density, tone_style)
```

---

## 🔍 量綱分析 (Dimensional Analysis)

### 當前模型的量綱追蹤

| 步驟 | 變數 | 當前量綱 | 應有量綱 |
|------|------|---------|----------|
| 輸入 | RGB | 無量綱 (0-1) | cd/m² 或 W/m²·sr |
| 光譜響應 | lux_r/g/b | 無量綱 (0-1) | 無量綱（相對響應可接受） |
| 光暈 | bloom | 無量綱 (0-1) | cd/m² 或 W/m²·sr |
| 組合 | result | 無量綱 (0-1) | cd/m² 或 W/m²·sr |
| 輸出 | final_image | 0-255 (uint8) | 0-255 (顯示值) |

**結論**: 整個計算流程**沒有物理單位**，所有數值都是無量綱的「相對值」。

**影響**:
1. ✅ 優點：計算簡單，不需要處理單位轉換
2. ❌ 缺點：無法進行物理驗證，參數缺乏實際意義
3. ❌ 問題：稱為「計算光學」有誤導性

---

## 📊 能量守恆檢驗

### 測試：光暈效果是否守恆能量？

**假設輸入**:
```python
input_image = np.array([[0.0, 0.0, 0.0],
                        [0.0, 1.0, 0.0],
                        [0.0, 0.0, 0.0]])

total_energy_in = np.sum(input_image)  # = 1.0
```

**當前實現的輸出** (理論分析):
```python
# 光暈效果會「增加」能量到周圍像素
bloom = apply_bloom(...) # 產生光暈
output_image = input_image + bloom  # 相加

total_energy_out = np.sum(output_image)  # > 1.0 ❌
```

**結論**: **能量不守恆**

**正確的實現**:
```python
# 1. 提取高光能量
highlight_energy = extract_highlights(input_image) * scattering_ratio

# 2. 從原圖減去
input_corrected = input_image - highlight_energy

# 3. 應用散射
bloom = convolve(highlight_energy, PSF)

# 4. 組合
output_image = input_corrected + bloom

# 驗證
assert np.isclose(np.sum(input_image), np.sum(output_image))  # ✅
```

---

## 🎯 建議改進方案

### 優先級 1: 高 (必須修正)

#### 1.1 明確說明模型的限制

**建議**: 在文檔中明確說明：
> "Phos 使用**簡化的光學模型**來模擬胶片效果，不是嚴格的物理模擬。所有計算均為**相對值**，不具備真實的物理單位。"

**修改位置**:
- `README.md`
- `Phos_0.2.0.py` 檔案頂部註解

#### 1.2 修正函數與變數命名

**建議**:
```python
# ❌ 誤導性命名
def luminance(image, film):
    ...

# ✅ 清晰命名
def spectral_response(image, film):
    """
    計算胶片感光層的相對光譜響應
    
    注意：這不是真實的光度計算，而是基於 RGB 值的色彩空間轉換。
    """
    ...
```

**其他需要修正的命名**:
- `lux_r/g/b` → `response_r/g/b` 或 `channel_r/g/b`
- `apply_bloom` → `apply_halation_effect`
- `diffuse_light` → `diffuse_weight` 或 `scattering_gain`
- `direct_light` → `direct_weight` 或 `transmission`

#### 1.3 添加能量守恆

**建議**: 修改光暈效果以守恆能量

```python
def apply_bloom_to_channel_conserved(lux, params):
    """
    應用光暈效果（守恆能量版本）
    """
    # 1. 提取高光區域（超過閾值）
    threshold = params.bloom_threshold  # 例如 0.8
    highlights = np.maximum(lux - threshold, 0)
    
    # 2. 計算散射能量（比例）
    scattering_ratio = params.scattering_ratio  # 例如 0.1（10% 散射）
    scattered_energy = highlights * scattering_ratio
    
    # 3. 應用點擴散函數
    bloom_layer = cv2.GaussianBlur(scattered_energy, (ksize, ksize), sigma)
    
    # 4. 從原圖減去散射能量
    lux_corrected = lux - scattered_energy
    
    # 5. 加上散射後的光暈
    result = lux_corrected + bloom_layer
    
    # 6. 驗證能量守恆
    assert np.isclose(np.sum(lux), np.sum(result), rtol=1e-3), "能量不守恆！"
    
    return result
```

### 優先級 2: 中 (建議改進)

#### 2.1 使用 Poisson 噪聲模擬胶片顆粒

```python
def generate_grain_for_channel_physical(lux_channel, film_params):
    """
    基於 Poisson 統計的胶片顆粒
    """
    # 假設線性響應區域
    photon_count = lux_channel * film_params.exposure_level
    
    # Poisson 噪聲（光子噪聲）
    photon_noise = np.random.poisson(photon_count) / film_params.exposure_level
    
    # 銀鹽顆粒噪聲（固定模式噪聲）
    grain_pattern = generate_grain_pattern(
        grain_size=film_params.grain_size,
        grain_density=film_params.grain_density,
        image_shape=lux_channel.shape
    )
    
    # 組合
    total_noise = photon_noise + grain_pattern * film_params.grain_intensity
    
    return total_noise
```

#### 2.2 實現 H&D 曲線（胶片特性曲線）

```python
def apply_film_characteristic_curve(exposure, film_params):
    """
    應用 Hurter-Driffield 曲線（胶片的非線性響應）
    
    Args:
        exposure: 相對曝光量（無量綱）
        film_params: 包含 gamma, Dmin, Dmax, shoulder, toe
    
    Returns:
        optical_density: 光學密度（無量綱）
    """
    # 對數響應（線性區域）
    log_exposure = np.log10(exposure + 1e-6)
    density = film_params.gamma * log_exposure + film_params.D0
    
    # Shoulder（肩部）- 高光壓縮
    shoulder_mask = density > film_params.shoulder_start
    density[shoulder_mask] = apply_shoulder_curve(
        density[shoulder_mask],
        film_params.shoulder_start,
        film_params.Dmax
    )
    
    # Toe（趾部）- 陰影提升
    toe_mask = density < film_params.toe_end
    density[toe_mask] = apply_toe_curve(
        density[toe_mask],
        film_params.Dmin,
        film_params.toe_end
    )
    
    # 限制動態範圍
    density = np.clip(density, film_params.Dmin, film_params.Dmax)
    
    return density
```

#### 2.3 分離物理模擬與色調映射

```python
# 主處理流程
def process_image_physical(image, film_params, tone_style):
    # ===== 階段 1: 物理模擬 =====
    
    # 1.1 光譜響應（色彩空間轉換）
    response = spectral_response(image, film_params)
    
    # 1.2 光暈效果（能量守恆）
    halation = apply_halation_conserved(response, film_params)
    
    # 1.3 胶片顆粒（Poisson 噪聲）
    grain = generate_grain_physical(halation, film_params)
    noisy_response = halation + grain
    
    # 1.4 胶片特性曲線（H&D Curve）
    optical_density = apply_film_characteristic_curve(noisy_response, film_params)
    
    # ===== 階段 2: 顯示映射 =====
    
    # 2.1 從光學密度轉換到透射率
    transmission = 10 ** (-optical_density)
    
    # 2.2 色調映射（可選）
    if tone_style == "filmic":
        display_image = apply_filmic_tone_mapping(transmission, film_params)
    elif tone_style == "reinhard":
        display_image = apply_reinhard_tone_mapping(transmission, film_params)
    else:
        display_image = transmission
    
    # 2.3 轉換到顯示範圍
    output = (display_image * 255).astype(np.uint8)
    
    return output
```

### 優先級 3: 低 (長期改進)

#### 3.1 引入真實的物理單位

**目標**: 讓模型具備可驗證性

**需要的資訊**:
1. 相機的 ISO 設定（感光度）
2. 快門速度（曝光時間）
3. 光圈大小（f-number）
4. 場景亮度（cd/m² 或 lux）

**轉換公式（近似）**:
$$
H = \frac{L \cdot t \cdot \pi}{4 \cdot f^2 \cdot (1 + m)^2}
$$

其中：
- $H$: 曝光量（lux·s）
- $L$: 場景亮度（cd/m²）
- $t$: 曝光時間（s）
- $f$: f-number（光圈值）
- $m$: 放大倍率（macro 攝影時考慮）

**適用條件**：
- 薄透鏡近似
- 朗伯特（Lambertian）表面
- 忽略鏡頭透過率（T-stop vs f-stop）
- 遠距拍攝（$m \approx 0$）
- 用於相對曝光量估算，非絕對校準

#### 3.2 實現基於波長的光譜模型

**目標**: 真實的光譜響應

```python
# 定義波長範圍
wavelengths = np.arange(380, 780, 10)  # nm

# 胶片的光譜敏感度曲線
sensitivity_curve_r = gaussian(wavelengths, center=650, width=50)
sensitivity_curve_g = gaussian(wavelengths, center=550, width=50)
sensitivity_curve_b = gaussian(wavelengths, center=450, width=50)

# 場景的光譜功率分布（SPD）
scene_spd = estimate_spd_from_rgb(rgb_values)

# 計算響應
response_r = np.sum(scene_spd * sensitivity_curve_r)
response_g = np.sum(scene_spd * sensitivity_curve_g)
response_b = np.sum(scene_spd * sensitivity_curve_b)
```

#### 3.3 實現點擴散函數 (PSF)

**目標**: 更真實的光暈效果

```python
def calculate_psf(film_params):
    """
    計算點擴散函數（工程近似）
    
    注意：
    - 若各機制可視為獨立線性系統，總 PSF = PSF₁ ⊗ PSF₂ ⊗ PSF₃（卷積）
    - 需在空間不變線性系統（LSI）假設下使用
    - 總 PSF 需正規化以守恆能量：∫ PSF = 1
    """
    # 1. 衍射（Airy Disk，適用於小光圈）
    psf_diffraction = airy_disk(aperture, wavelength)
    
    # 2. 乳劑層散射（經驗近似：高斯核或雙指數核）
    # 注意：嚴格的 Mie 散射需數值求解，此處用經驗 PSF
    psf_scattering = gaussian_kernel(sigma=film_params.scattering_radius)
    
    # 3. 片基反射（Halation，色依賴）
    psf_halation = exponential_kernel(
        decay=film_params.halation_decay,
        color_weight=film_params.halation_color  # 紅/黃偏移
    )
    
    # 4. 組合（卷積鏈，假設 LSI）
    psf_total = convolve(psf_diffraction, psf_scattering)
    psf_total = convolve(psf_total, psf_halation)
    
    # 5. 正規化（守恆能量）
    psf_total = psf_total / np.sum(psf_total)
    
    return psf_total
```

---

## 📋 驗證測試建議

### 測試 1: 能量守恆驗證

```python
def test_energy_conservation():
    """測試光暈效果是否守恆能量"""
    # 創建測試影像（單一亮點）
    test_image = np.zeros((100, 100))
    test_image[50, 50] = 1.0
    
    # 計算總能量
    energy_in = np.sum(test_image)
    
    # 應用光暈
    result = apply_bloom(test_image, film_params)
    energy_out = np.sum(result)
    
    # 驗證（允許 1% 誤差）
    assert np.isclose(energy_in, energy_out, rtol=0.01), \
        f"能量不守恆：輸入={energy_in}, 輸出={energy_out}"
```

### 測試 2: 量綱一致性

```python
def test_dimensional_consistency():
    """檢查所有中間變數的量綱"""
    image = load_test_image()
    
    # 追蹤每一步的量綱
    response = spectral_response(image, film)
    assert response.min() >= 0 and response.max() <= 1, "響應值超出範圍"
    
    halation = apply_halation(response, film)
    assert halation.min() >= 0, "光暈不應該有負值"
    
    # ... 其他步驟
```

### 測試 3: 物理參數的合理性

```python
def test_parameter_ranges():
    """驗證所有物理參數在合理範圲內"""
    film = get_film_profile("NC200")
    
    # 光譜響應權重應該在 0-1 範圍（若參數名為 absorption，應改名為 response_weight）
    # 注意：若為真實吸收係數 α（單位 1/m），則無此限制
    assert 0 <= film.red_layer.r_absorption <= 1, "光譜響應權重應在 [0,1]"
    assert 0 <= film.red_layer.g_absorption <= 1
    assert 0 <= film.red_layer.b_absorption <= 1
    
    # 顆粒強度應該是非負數
    assert film.red_layer.grain_intensity >= 0
    
    # 膠片 H&D 曲線的 gamma（若實作）
    # 注意：膠片 gamma ≠ 顯示 gamma (2.2)
    # 負片典型值：0.6-0.7；正片典型值：1.5-2.0
    if hasattr(film, 'hd_gamma'):
        assert 0.5 <= film.hd_gamma <= 2.5, "膠片 gamma 應在合理範圍"
    
    # 若有顯示 tone mapping gamma，應分開測試
    if hasattr(film.tone_params, 'display_gamma'):
        assert 1.8 <= film.tone_params.display_gamma <= 2.6, "顯示 gamma 應接近 2.2"
```

---

## 📚 參考文獻與理論基礎

### 必讀文獻

1. **胶片光學理論**:
   - Hunt, R. W. G., & Pointer, M. R. (2011). *Measuring Colour*. Wiley.
   - James, T. H. (1977). *The Theory of the Photographic Process* (4th ed.). Macmillan.

2. **點擴散函數 (PSF)**:
   - Goodman, J. W. (2005). *Introduction to Fourier Optics* (3rd ed.). Roberts & Company.

3. **Tone Mapping**:
   - Reinhard, E., et al. (2010). *High Dynamic Range Imaging: Acquisition, Display, and Image-Based Lighting* (2nd ed.). Morgan Kaufmann.

4. **光譜響應**:
   - CIE (Commission Internationale de l'Éclairage) Technical Reports on Colorimetry

### 相關標準

- **ISO 5800**: Photography — Colour negative films for still photography — Determination of ISO speed
- **ISO 6:1993**: Photography — Black-and-white pictorial still camera negative film/process systems — Determination of ISO speed

---

## 🎯 總結與建議

### 當前狀態

**優點** ✅:
1. 程式架構清晰，模組化良好
2. 視覺效果可能不錯（這是藝術性的）
3. 處理流程完整

**缺點** ❌:
1. **「計算光學」宣稱與實際簡化模型不符**
2. 能量不守恆（Bloom 效果純加法）
3. 量綱與物理單位未明確定義
4. 參數語義不清（「吸收係數」應為「響應權重」）
5. Tone Mapping 與膠片物理過程混淆

### 改進路徑

#### 路徑 A: 藝術導向（保持現狀，調整說明）

**適用**: 如果目標是「好看」而非「物理正確」

**建議**:
1. 修改文檔說明，不要聲稱「計算光學」
2. 改為「基於胶片特性的藝術風格模擬」
3. 參數命名改為「權重」、「強度」等藝術術語

**優點**: 最小改動，維持現有視覺效果  
**缺點**: 失去「物理正確」的賣點

#### 路徑 B: 科學導向（重構物理模型）

**適用**: 如果目標是「物理正確的模擬」

**建議**:
1. 實現真正的光學模型（光譜響應、H&D 曲線、能量守恆）
2. 引入物理單位與量綱管理
3. 提供參數的物理解釋與驗證

**優點**: 真正的「計算光學」，可發表學術論文  
**缺點**: 需要大量重構，可能影響視覺效果

#### 路徑 C: 混合導向（實用主義）**推薦**

**適用**: 平衡「視覺效果」與「物理一致性」

**建議**:
1. 保留當前的視覺效果（藝術性優先）
2. 修正明顯的物理問題（能量守恆、參數命名）
3. 添加「物理模式」作為進階選項
4. 文檔中明確標示：
   - 「簡化光學模型」（而非「嚴格物理模擬」）
   - 區分「藝術模式」（預設）vs「物理模式」（實驗性）
5. 逐步改進：先修正能量守恆與 H&D 曲線，再考慮波長域模型

**優點**: 兼顧兩者，漸進改善，保持實用性  
**缺點**: 需維護兩套邏輯，但可透過共用底層實作降低複雜度

---

## 🔖 附錄：物理常數與單位

### 光度學單位

| 物理量 | 符號 | 單位 | 定義 |
|--------|------|------|------|
| 光通量 | Φ | lumen (lm) | 光功率 |
| 光強度 | I | candela (cd) | lm/sr |
| 照度 | E | lux (lx) | lm/m² |
| 光亮度 | L | cd/m² | cd/m² |
| 光出度 | M | lm/m² | 發出的光通量 |

### 胶片相關常數

| 參數 | 典型值 | 說明 |
|------|--------|------|
| ISO 100 曝光量 | 10 lux·s | H = 10 lux·s |
| ISO 400 曝光量 | 2.5 lux·s | 4倍敏感度 |
| 動態範圍 | 6-10 stops | 負片：~10 stops |
| Gamma（H&D 曲線） | 0.6-0.7 (負片), 1.5-2.0 (正片) | 膠片對比度（≠ 顯示 gamma 2.2） |
| 顆粒大小 | 0.5-2.0 μm | ISO 依賴 |

---

**審查完成日期**: 2025-12-19  
**最後更新**: 2025-12-19（修正散射理論、測試斷言、曝光公式錯誤）  
**建議優先級**: 路徑 C（混合導向）  
**預估改進時間**: 2-3 週（視選擇路徑而定）

**勘誤說明**：
- 原報告中 Mie 散射公式存在錯誤（波長依賴 λ⁴ 應為 λ⁻⁴），已修正為定性描述與工程近似建議
- 測試斷言中的 gamma 概念混用已澄清（膠片 gamma vs 顯示 gamma）
- 曝光公式已標註適用條件（薄透鏡、m≈0 等近似）

**審查者簽名**: 物理學家 (計算光學專家)

---

## 📋 實施進度追蹤 Implementation Progress

**最後更新**: 2025-12-19 21:00  
**實施路徑**: Path C（混合導向 - 保留藝術模式，添加物理模式）

### ✅ 已完成項目 Completed Items

#### 1. ✅ Section 3.2 - 能量守恆問題 (Energy Conservation)
**狀態**: 已實作 Phase 2 (2025-12-19 18:00)  
**實作內容**:
- 新增 `apply_bloom_conserved()` 函數（能量守恆版本）
- PSF 正規化：∫ PSF = 1
- 能量守恆驗證：誤差 < 0.01%
- 向後相容：藝術模式保留原行為（允許能量違反）

**測試結果**:
```
物理模式能量誤差: 0.0000%  ✅
藝術模式能量增加: +10.0%   ⚠️ (預期行為，視覺導向)
```

**文件位置**: 
- 實作：`Phos_0.2.0.py` Line ~780
- 測試：`tests/test_energy_conservation.py` (5/5 passed)

---

#### 2. ✅ Section 3.3 - 膠片顆粒 (Film Grain) - Poisson 統計
**狀態**: 已實作 Phase 4 (2025-12-19 20:00)  
**實作內容**:
- 新增 `generate_poisson_grain()` 函數（光子計數統計）
- Poisson 分布：λ = 曝光量 × scale_factor
- 正態近似：λ > 20 時（效能優化）
- 銀鹽顆粒空間相關性：高斯模糊模擬
- SNR ∝ √曝光量（物理正確）

**測試結果**:
```
暗部 SNR: 0.15   ← 噪聲明顯
亮部 SNR: 2.86   ← 噪聲抑制
顆粒尺寸 0.5→3.0: 空間相關性 0.01→0.97  ✅
```

**文件位置**:
- 實作：`Phos_0.2.0.py` Line ~480
- 測試：`tests/test_poisson_grain.py` (7/7 passed)

---

#### 3. ✅ Section 3.4 - H&D 特性曲線 (Characteristic Curve)
**狀態**: 已實作 Phase 3 (2025-12-19 19:30)  
**實作內容**:
- 新增 `apply_hd_curve()` 函數
- 對數響應：D = gamma × log₁₀(H) + offset
- Toe 曲線：陰影壓縮（soft compression）
- Shoulder 曲線：高光壓縮（asymptotic to D_max）
- 密度 → 透射率：T = 10^(-D)
- 動態範圍壓縮：10^8 → 10^3（5.2×10^4 倍）

**測試結果**:
```
對數響應單調性: ✅
Toe 效果（陰影提升）: +0.278 透射率  ✅
Gamma 對比度關係: 0.6→2.0, 對比度 0.12→0.99  ✅
動態範圍壓縮: 10^8 → 10^3  ✅
```

**文件位置**:
- 實作：`Phos_0.2.0.py` Line ~850
- 測試：`tests/test_hd_curve.py` (8/8 passed)

---

#### 4. ✅ Section 5.1 - 命名問題 (Naming Issues)
**狀態**: 已實作 Phase 5 (2025-12-19 21:00)  
**實作內容**:
- `luminance()` → `spectral_response()`（非光度，而是光譜響應）
- `lux_r/g/b/total` → `response_r/g/b/total`（移除誤導性單位）
- `*_absorption` → `*_response_weight`（非吸收係數，是響應權重）
- `*_light` → `*_weight`（非光量，是混合權重）
- 全域重新命名：301 處跨 5 個檔案

**測試結果**:
```
所有測試通過: 26/26  ✅
向後相容性: FilmProfile 結構不變  ✅
```

**文件位置**:
- 修改檔案：`Phos_0.2.0.py`, `phos_core.py`, `film_models.py`
- 決策記錄：`context/decisions_log.md` Decision #010

---

#### 5. ✅ Phase 1 - 參數結構設計
**狀態**: 已實作 (2025-12-19 18:00)  
**實作內容**:
- 新增 `PhysicsMode` enum (ARTISTIC/PHYSICAL/HYBRID)
- 新增 `HDCurveParams`, `BloomParams`, `GrainParams` dataclass
- 擴展 `FilmProfile`（向後相容）
- 預設為 ARTISTIC 模式（不影響現有行為）

**測試結果**:
```
FilmProfile 載入: 7/7 成功  ✅
向後相容性: 100%  ✅
```

**文件位置**:
- 實作：`film_models.py` (+100 lines)
- 測試：所有測試通過

---

#### 6. ✅ Phase 6 - 整合測試與效能驗證
**狀��**: 已實作 (2025-12-19 21:00)  
**實作內容**:
- 整合測試：Artistic/Physical/Hybrid 模式
- 效能基準測試：2000×3000 影像
- FilmProfile 相容性測試：7 款底片
- 邊界條件測試：零/極值/異常輸入

**測試結果**:
```
整合測試: 6/6 通過  ✅
單元測試: 20/20 通過  ✅
總計: 26/26 通過  ✅
效能（估算）: Artistic ~0.7s, Physical ~0.8s (2000×3000)
FilmProfile 載入: 7/7 成功  ✅
```

**文件位置**:
- 測試：`tests/test_integration.py` (6 tests)
- 報告：`context/decisions_log.md` Decision #007-#010

---

### ⏳ 待辦項目 Pending Items

#### 1. ⏳ Section 2.1 - 光暈效果 (Bloom/Halation) - 散射模型
**當前狀態**: 部分完成（能量守恆已實作，散射模型待改進）  
**已實作**:
- ✅ 能量守恆 PSF
- ✅ 高光提取與閾值控制
- ✅ Gaussian/Exponential PSF 選項

**待改進**:
- ⏳ 更真實的 PSF 模型（當前為經驗公式）
- ⏳ Halation 效果（底層反射）vs Bloom（內部散射）分離
- ⏳ 波長依賴散射（紅光比藍光散射更明顯）

**優先級**: Medium（當前經驗模型已足夠視覺化）

---

#### 2. ⏳ Section 4.1 - 圖層混合邏輯
**當前狀態**: 保留原實作（藝術導向）  
**問題**:
- `diffuse_weight=1.48` 超過 1.0（物理意義不明）
- 混合權重缺乏理論依據

**建議**:
- 添加物理模式下的權重正規化（∑ weight = 1）
- 保留藝術模式的自由度（可超過 1.0）

**優先級**: Low（不影響核心功能）

---

#### 3. ⏳ 使用者介面更新
**當前狀態**: 尚未實作  
**待辦**:
- Streamlit UI 添加「Physics Mode」開關
- 參數調整介面（Bloom/H&D/Grain）
- 藝術 vs 物理模式對比視圖

**優先級**: High（提升使用者體驗）

---

#### 4. ⏳ 使用者文檔
**當前狀態**: 部分完成  
**已完成**:
- ✅ 物理審查報告 (`PHYSICS_REVIEW.md`)
- ✅ 決策日誌 (`context/decisions_log.md`)

**待辦**:
- ⏳ 物理模式使用指南 (`PHYSICAL_MODE_GUIDE.md`)
- ⏳ README 更新（Physical Mode 說明）
- ⏳ API 文檔更新（函數重新命名）

**優先級**: High（用戶需要指引）

---

### 📊 總體進度 Overall Progress

**核心物理改進**: 85% 完成  
- ✅ 能量守恆 (100%)
- ✅ H&D 曲線 (100%)
- ✅ Poisson 顆粒 (100%)
- ✅ 命名修正 (100%)
- ⏳ 散射模型 (70%)
- ⏳ 圖層混合 (50%)

**測試覆蓋率**: 100% (26/26 tests)  
**文檔完成度**: 60%  
**UI 整合**: 0%  

**預估剩餘工作**: 2-3 天（文檔 + UI）

---

**下一步建議 Next Steps**:
1. 更新 `README.md` - 添加 Physical Mode 使用範例
2. 創建 `PHYSICAL_MODE_GUIDE.md` - 詳細參數調整指南
3. 實作 Streamlit UI 支援（Physical Mode 開關）
4. 創建視覺對比範例（Artistic vs Physical）

---

**備註 Notes**:
- 所有實作均保持向後相容性（預設 ARTISTIC 模式）
- 測試套件全部通過（26/26）
- 效能開銷可接受（Physical vs Artistic: ~+8%）
