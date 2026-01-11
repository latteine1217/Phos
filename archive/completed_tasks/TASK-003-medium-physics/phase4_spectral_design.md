# Phase 4: 光譜模型升級設計文件

**任務 ID**: TASK-003-Phase-4  
**優先級**: P0（高優先）  
**預估時間**: 2 天（16 小時）  
**目標**: RGB → 光譜積分 → RGB，提升色彩準確度 +40%  
**時間約束**: 處理時間增幅 < 100%（< 4.2s for 2000×3000）

---

## 🎯 任務目標

### 核心目標
將當前的 **RGB 三通道模型** 升級為 **31 通道光譜模型**，實現：
1. **色彩準確度提升 +40%**（相對於真實膠片）
2. **支援色溫模擬**（鎢絲燈 2800K vs 日光 5500K）
3. **支援濾鏡效果**（黃濾鏡、紅濾鏡、偏振鏡）
4. **Bloom 色彩分離更真實**（光譜域卷積）

### 成功指標
- ✅ **色彩準確度**: ΔE2000 < 5（專業級標準）
- ✅ **記憶體占用**: < 10x RGB（透過分塊處理）
- ✅ **處理時間**: < 4.2s（2000×3000，目標 2x RGB baseline）
- ✅ **能量守恆**: < 0.01% 誤差（光譜積分不破壞）
- ✅ **向後相容**: 標準 RGB 模式仍可用

---

## 📐 物理原理

### 當前 RGB 模型的限制

**問題 1: 色溫無法準確模擬**
```python
# 當前方法：簡單 RGB 縮放
rgb_tungsten = rgb_daylight * [1.2, 1.0, 0.8]  # ❌ 不符合黑體輻射
```

**問題 2: 濾鏡效果不準確**
```python
# 當前方法：乘法模型
rgb_filtered = rgb * filter_color  # ❌ 忽略光譜交互作用
```

**問題 3: 膠片光譜敏感度被簡化**
```python
# 當前方法：固定 RGB 權重
lux_r = 0.8*R + 0.1*G + 0.15*B  # ❌ 無法反映真實曲線
```

### 光譜模型原理

#### 1. RGB → 光譜重建（Smits 1999）

**算法**: RGB to Spectrum Reconstruction
- **輸入**: RGB (0-1)
- **輸出**: 光譜 S(λ), λ ∈ [380nm, 720nm], 31 點
- **方法**: 基向量線性組合

```python
# 基向量（預先計算）
basis_white = [w_380, w_390, ..., w_720]  # 白色光譜
basis_cyan = [c_380, c_390, ..., c_720]   # 青色光譜
basis_magenta = [m_380, m_390, ..., m_720]
basis_yellow = [y_380, y_390, ..., y_720]
basis_red = [r_380, r_390, ..., r_720]
basis_green = [g_380, g_390, ..., g_720]
basis_blue = [b_380, b_390, ..., b_720]

# 重建
def rgb_to_spectrum(rgb):
    r, g, b = rgb
    
    # 選擇基向量組合（根據 RGB 比例）
    if r <= g and r <= b:
        # 青色主導
        spectrum = (
            (1 - r) * basis_cyan +
            r * (g * basis_green + (1-g) * basis_white) * ...
        )
    elif g <= r and g <= b:
        # 洋紅色主導
        spectrum = ...
    # ... 其他情況
    
    return spectrum  # shape: (31,)
```

**優點**:
- 保證物理可實現（非負）
- 平滑光譜（無振盪）
- 精確重建 RGB 顏色

**數據來源**:
- Smits (1999) 論文：[An RGB-to-Spectrum Conversion for Reflectances](https://www.cs.utah.edu/~bes/papers/color/)
- 預計算基向量存儲為 `data/smits_basis_spectra.npz`

#### 2. 膠片光譜敏感度曲線

**數據來源**: Kodak/Fuji 官方 Datasheet

**Kodak Portra 400 範例**:
```python
# 紅色層（Red-sensitive layer）
sensitivity_r = {
    380nm: 0.0,   # UV: 無感光
    450nm: 0.05,  # 藍光: 微弱感光（交叉敏感）
    550nm: 0.10,  # 綠光: 微弱
    650nm: 0.95,  # 紅光: 主峰
    720nm: 0.30   # 近紅外: 衰減
}

# 綠色層（Green-sensitive layer）
sensitivity_g = {
    450nm: 0.20,  # 藍光: 交叉敏感
    550nm: 0.90,  # 綠光: 主峰
    650nm: 0.15   # 紅光: 微弱
}

# 藍色層（Blue-sensitive layer）
sensitivity_b = {
    380nm: 0.40,  # UV: 感光（無 UV 濾鏡時）
    450nm: 0.95,  # 藍光: 主峰
    550nm: 0.25,  # 綠光: 交叉敏感
    650nm: 0.05   # 紅光: 微弱
}
```

**關鍵特徵**:
- **交叉敏感**: 藍色層對綠光有反應（真實膠片特性）
- **不對稱**: 各層主峰寬度不同
- **膠片差異**: Portra vs Velvia vs Tri-X 曲線完全不同

**數據文件**: `data/film_spectral_sensitivity.npz`

#### 3. 光譜積分 → XYZ → RGB

**標準觀察者匹配函數**（CIE 1931）:
```python
# 載入 CIE 1931 31 點數據
cie_x = [x_380, x_390, ..., x_720]  # X 匹配函數
cie_y = [y_380, y_390, ..., y_720]  # Y 匹配函數（亮度）
cie_z = [z_380, z_390, ..., z_720]  # Z 匹配函數

# 光譜積分
def spectrum_to_xyz(spectrum, illuminant=D65):
    """
    spectrum: (31,) 反射率 R(λ)
    illuminant: (31,) 光源 SPD L(λ)
    """
    # 積分
    X = sum(spectrum * illuminant * cie_x * delta_lambda)
    Y = sum(spectrum * illuminant * cie_y * delta_lambda)
    Z = sum(spectrum * illuminant * cie_z * delta_lambda)
    
    return (X, Y, Z)

# XYZ → sRGB（標準轉換矩陣）
def xyz_to_rgb(xyz):
    X, Y, Z = xyz
    
    # 線性 RGB
    r_linear =  3.2406 * X - 1.5372 * Y - 0.4986 * Z
    g_linear = -0.9689 * X + 1.8758 * Y + 0.0415 * Z
    b_linear =  0.0557 * X - 0.2040 * Y + 1.0570 * Z
    
    # Gamma 校正（sRGB）
    rgb = apply_srgb_gamma([r_linear, g_linear, b_linear])
    
    return rgb
```

**數據文件**: `data/cie_1931_31points.npz`

---

## 🏗️ 架構設計

### 整體流程

```
輸入影像 (RGB, H×W×3)
    ↓
[1] RGB → 光譜重建 (Smits 1999)
    → 光譜影像 (H×W×31)
    ↓
[2] 套用光源光譜（色溫模擬）
    → 光譜影像 × Illuminant SPD
    ↓
[3] 膠片光譜響應卷積
    → 乳劑層曝光 (H×W×3 通道，但來自光譜積分)
    ↓
[4] 光學效果（Bloom, Halation）
    → 在光譜域或響應域卷積
    ↓
[5] 光譜積分 → XYZ → sRGB
    → 輸出影像 (RGB, H×W×3)
```

### 記憶體優化策略

**問題**: 31 通道 × 2000×3000 = 186 MB（vs RGB 18 MB，10x）

**解決方案**:
1. **分塊處理（Tile-based）**:
```python
tile_size = 512  # 每次處理 512×512 區塊
for y in range(0, H, tile_size):
    for x in range(0, W, tile_size):
        tile_rgb = image[y:y+tile_size, x:x+tile_size]
        tile_spectrum = rgb_to_spectrum(tile_rgb)  # 僅佔 512×512×31 = 7.9 MB
        # ... 處理 ...
        result[y:y+tile_size, x:x+tile_size] = spectrum_to_rgb(tile_spectrum)
```

2. **float16 半精度**:
```python
spectrum = rgb_to_spectrum(rgb).astype(np.float16)  # 記憶體減半
```

3. **光譜降維（選項）**:
```python
# 31 通道 → 16 通道（PCA 壓縮）
spectrum_reduced = pca_compress(spectrum_31, n_components=16)
```

### 效能優化策略

**目標**: 處理時間 < 4.2s（2x RGB baseline 2.1s）

**瓶頸分析**:
| 步驟 | RGB 模型 | 光譜模型（原始） | 優化後 |
|------|---------|-----------------|--------|
| 1. 光譜重建 | 0ms | ~500ms | **100ms** (查表) |
| 2. 膠片響應 | 100ms | ~800ms | **200ms** (向量化) |
| 3. 光學效果 | 1400ms | ~4200ms (31 通道卷積) | **1800ms** (分塊+float16) |
| 4. XYZ 積分 | 0ms | ~300ms | **150ms** (NumPy優化) |
| **總計** | **2.1s** | **5.8s** | **2.25s** ✅ |

**優化技術**:
1. **查表法替代 Smits 算法**:
```python
# 預計算 256×256×256 RGB 組合的光譜
spectrum_lut = load_spectrum_lut("data/rgb_to_spectrum_lut.npz")
spectrum = spectrum_lut[r_idx, g_idx, b_idx]  # O(1) 查表
```

2. **光譜卷積降維**:
```python
# 不在 31 通道做卷積，而是在 3 通道做
# 利用光譜響應的低秩特性（PCA）
response_rgb = integrate_spectrum_fast(spectrum, sensitivity_curves)
bloomed_rgb = convolve(response_rgb, psf)  # 僅 3 通道
```

3. **JIT 編譯（Numba）**:
```python
from numba import jit

@jit(nopython=True, parallel=True)
def batch_rgb_to_spectrum(rgb_array):
    # 編譯為機器碼，加速 3-5x
    ...
```

---

## 📂 數據準備

### 需要生成的數據文件

#### 1. Smits 基向量
**文件**: `data/smits_basis_spectra.npz`  
**內容**:
```python
{
    'wavelengths': [380, 390, 400, ..., 720],  # 31 點
    'basis_white': [...],
    'basis_cyan': [...],
    'basis_magenta': [...],
    'basis_yellow': [...],
    'basis_red': [...],
    'basis_green': [...],
    'basis_blue': [...]
}
```
**生成腳本**: `scripts/generate_smits_basis.py`

#### 2. 膠片光譜敏感度
**文件**: `data/film_spectral_sensitivity.npz`  
**內容**:
```python
{
    'wavelengths': [380, 390, ..., 720],
    
    # 彩色負片
    'Portra400_r': [...],
    'Portra400_g': [...],
    'Portra400_b': [...],
    
    'Ektar100_r': [...],
    'Ektar100_g': [...],
    'Ektar100_b': [...],
    
    # 黑白負片
    'TriX400': [...],  # 單通道全色
    'HP5Plus400': [...],
    
    # 反轉片
    'Velvia50_r': [...],
    'Velvia50_g': [...],
    'Velvia50_b': [...]
}
```
**數據來源**:
- Kodak 官方 Datasheet（PDF 數位化）
- Fuji 技術文件
- 若無官方數據，使用典型曲線（文獻參考）

**生成腳本**: `scripts/generate_film_spectra.py`

#### 3. CIE 1931 標準觀察者
**文件**: `data/cie_1931_31points.npz`  
**內容**:
```python
{
    'wavelengths': [380, 390, ..., 720],
    'x_bar': [...],  # X 匹配函數
    'y_bar': [...],  # Y 匹配函數（亮度）
    'z_bar': [...]   # Z 匹配函數
}
```
**數據來源**: CIE 官方數據（公開）  
**生成腳本**: `scripts/generate_cie_data.py`

#### 4. RGB to Spectrum LUT（選項，效能優化）
**文件**: `data/rgb_to_spectrum_lut.npz`（大文件，~500 MB）  
**內容**: 256×256×256 → 31 映射  
**生成腳本**: `scripts/generate_spectrum_lut.py`（需 ~1 小時）

---

## 🛠️ 實作計畫

### Milestone 1: 數據生成（Day 1, 4h）

#### 任務 1.1: CIE 1931 數據
```bash
python3 scripts/generate_cie_data.py
# 輸出: data/cie_1931_31points.npz (< 1KB)
```

**驗證**:
```python
import numpy as np
data = np.load('data/cie_1931_31points.npz')
assert data['wavelengths'].shape == (31,)
assert data['x_bar'].shape == (31,)
# 檢查 Y 積分 = 683 lm/W（標準值）
```

#### 任務 1.2: Smits 基向量
```bash
python3 scripts/generate_smits_basis.py
# 輸出: data/smits_basis_spectra.npz (~2KB)
```

**驗證**:
```python
# 測試 RGB(1,1,1) → 白色光譜
spectrum_white = rgb_to_spectrum([1, 1, 1])
assert np.allclose(spectrum_white, data['basis_white'])

# 測試 RGB(1,0,0) → 紅色光譜
spectrum_red = rgb_to_spectrum([1, 0, 0])
# 檢查主峰在 650nm
assert spectrum_red[np.argmax(spectrum_red)] > 0.9
```

#### 任務 1.3: 膠片光譜敏感度
```bash
python3 scripts/generate_film_spectra.py
# 輸出: data/film_spectral_sensitivity.npz (~10KB)
```

**數據來源**:
1. **優先**: Kodak/Fuji 官方 Datasheet（PDF 數位化）
2. **替代**: 文獻參考曲線（典型值）
3. **降級**: 基於 RGB 權重的合成曲線（保留當前行為）

**驗證**:
```python
data = np.load('data/film_spectral_sensitivity.npz')

# 檢查 Portra400 紅色層主峰在 650nm
portra_r = data['Portra400_r']
peak_idx = np.argmax(portra_r)
assert data['wavelengths'][peak_idx] == 650

# 檢查歸一化
assert 0.9 <= np.max(portra_r) <= 1.0
```

### Milestone 2: 核心函數實作（Day 1, 4h）

#### 任務 2.1: RGB to Spectrum
**文件**: `phos_core.py` 新增函數

```python
def rgb_to_spectrum(rgb: np.ndarray, method='smits') -> np.ndarray:
    """
    將 RGB 轉換為 31 點光譜
    
    Args:
        rgb: RGB 影像 (H, W, 3) 或單點 (3,)，值域 [0, 1]
        method: 'smits' (精確) 或 'lut' (快速)
    
    Returns:
        spectrum: (H, W, 31) 或 (31,)，值域 [0, 1]
    
    Example:
        >>> rgb = np.array([1.0, 0.5, 0.2])
        >>> spectrum = rgb_to_spectrum(rgb)
        >>> spectrum.shape
        (31,)
    """
    # 載入基向量
    basis_data = load_smits_basis()  # 快取
    
    # Smits 算法實作
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    
    # 根據 RGB 比例選擇基向量組合
    # （詳細實作參考 Smits 1999 論文）
    ...
    
    return spectrum
```

#### 任務 2.2: Spectrum to XYZ
**文件**: `phos_core.py`

```python
def spectrum_to_xyz(
    spectrum: np.ndarray, 
    illuminant_spd: np.ndarray = None
) -> np.ndarray:
    """
    光譜積分 → XYZ 色彩空間
    
    Args:
        spectrum: 光譜 (H, W, 31) 或 (31,)
        illuminant_spd: 光源光譜功率分布 (31,)，預設 D65
    
    Returns:
        xyz: (H, W, 3) 或 (3,)，XYZ 色彩值
    """
    # 載入 CIE 1931 匹配函數
    cie_data = load_cie_1931()  # 快取
    x_bar = cie_data['x_bar']
    y_bar = cie_data['y_bar']
    z_bar = cie_data['z_bar']
    delta_lambda = 10  # nm
    
    # 預設光源 D65
    if illuminant_spd is None:
        illuminant_spd = get_illuminant_d65()
    
    # 光譜積分
    X = np.sum(spectrum * illuminant_spd * x_bar * delta_lambda, axis=-1)
    Y = np.sum(spectrum * illuminant_spd * y_bar * delta_lambda, axis=-1)
    Z = np.sum(spectrum * illuminant_spd * z_bar * delta_lambda, axis=-1)
    
    return np.stack([X, Y, Z], axis=-1)
```

#### 任務 2.3: XYZ to sRGB
**文件**: `phos_core.py`

```python
def xyz_to_srgb(xyz: np.ndarray) -> np.ndarray:
    """
    XYZ → sRGB 標準轉換
    
    Args:
        xyz: (H, W, 3) 或 (3,)
    
    Returns:
        rgb: (H, W, 3) 或 (3,)，值域 [0, 1]
    """
    # 標準轉換矩陣（D65 白點）
    M = np.array([
        [ 3.2406, -1.5372, -0.4986],
        [-0.9689,  1.8758,  0.0415],
        [ 0.0557, -0.2040,  1.0570]
    ])
    
    # 線性 RGB
    rgb_linear = np.dot(xyz, M.T)
    
    # sRGB Gamma 校正
    def srgb_gamma(c):
        return np.where(
            c <= 0.0031308,
            12.92 * c,
            1.055 * np.power(c, 1/2.4) - 0.055
        )
    
    rgb = srgb_gamma(rgb_linear)
    
    return np.clip(rgb, 0, 1)
```

### Milestone 3: 膠片響應整合（Day 1-2, 4h）

#### 任務 3.1: 光譜域膠片響應
**文件**: `film_models.py` 新增 `SpectralSensitivityParams`

```python
@dataclass
class SpectralSensitivityParams:
    """
    膠片光譜敏感度參數
    
    支援兩種模式：
    1. 'spectral': 使用真實 31 點光譜曲線（精確）
    2. 'rgb': 使用 RGB 權重（向後相容，快速）
    """
    mode: str = "rgb"  # "spectral" 或 "rgb"
    
    # Spectral 模式專用
    spectral_curve_r: Optional[np.ndarray] = None  # (31,) 紅色層敏感度
    spectral_curve_g: Optional[np.ndarray] = None  # (31,) 綠色層
    spectral_curve_b: Optional[np.ndarray] = None  # (31,) 藍色層
    
    # RGB 模式專用（向後相容）
    r_response_weight: float = 0.8
    g_response_weight: float = 0.1
    b_response_weight: float = 0.15
    # ... 其他 RGB 參數
```

#### 任務 3.2: 膠片響應計算函數
**文件**: `Phos_0.3.0.py` 新增函數

```python
def compute_film_response_spectral(
    spectrum: np.ndarray,
    film: FilmProfile
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    光譜域膠片響應計算（替代 RGB 域）
    
    Args:
        spectrum: 光譜影像 (H, W, 31)
        film: 膠片配置
    
    Returns:
        lux_r, lux_g, lux_b: 各層響應 (H, W)
    
    Example:
        >>> spectrum = rgb_to_spectrum(rgb_image)  # (H, W, 31)
        >>> lux_r, lux_g, lux_b = compute_film_response_spectral(spectrum, film)
        >>> lux_r.shape
        (H, W)
    """
    # 載入膠片光譜敏感度
    sensitivity = load_film_sensitivity(film.name)
    curve_r = sensitivity['r']  # (31,)
    curve_g = sensitivity['g']
    curve_b = sensitivity['b']
    
    # 光譜積分（矩陣乘法）
    # lux_r = ∫ spectrum(λ) · sensitivity_r(λ) dλ
    lux_r = np.sum(spectrum * curve_r, axis=-1)  # (H, W, 31) → (H, W)
    lux_g = np.sum(spectrum * curve_g, axis=-1)
    lux_b = np.sum(spectrum * curve_b, axis=-1)
    
    return lux_r, lux_g, lux_b
```

### Milestone 4: 主流程整合（Day 2, 4h）

#### 任務 4.1: 修改 `process_film_simulation()`
**文件**: `Phos_0.3.0.py`

```python
def process_film_simulation(
    image_rgb: np.ndarray,
    film: FilmProfile,
    use_spectral: bool = True  # 新增開關
) -> np.ndarray:
    """
    膠片模擬主函數
    
    Args:
        image_rgb: 輸入影像 (H, W, 3)
        film: 膠片配置
        use_spectral: True=光譜模式, False=RGB模式（向後相容）
    
    Returns:
        output_rgb: 輸出影像 (H, W, 3)
    """
    if not use_spectral:
        # 向後相容：RGB 模式（當前流程）
        return process_film_simulation_rgb(image_rgb, film)
    
    # === 光譜模式 ===
    
    # Step 1: RGB → 光譜重建
    spectrum = rgb_to_spectrum(image_rgb)  # (H, W, 31)
    
    # Step 2: 套用光源光譜（色溫模擬）
    illuminant = get_illuminant(color_temp=5500)  # D65 日光
    spectrum_illuminated = spectrum * illuminant
    
    # Step 3: 膠片光譜響應
    lux_r, lux_g, lux_b = compute_film_response_spectral(
        spectrum_illuminated, film
    )
    
    # Step 4: 光學效果（當前流程，不變）
    if film.physics_mode == PhysicsMode.PHYSICAL:
        lux_r, lux_g, lux_b = apply_optical_effects_separated(
            lux_r, lux_g, lux_b, film
        )
    
    # Step 5: H&D 曲線 / Tone Mapping（當前流程）
    ...
    
    # Step 6: 顆粒（當前流程）
    ...
    
    # Step 7: 最終轉換（當前使用簡單 stack，光譜模式可改為 XYZ 積分）
    output_rgb = np.stack([lux_r, lux_g, lux_b], axis=-1)
    
    return output_rgb
```

#### 任務 4.2: 分塊處理（記憶體優化）
**文件**: `phos_core.py`

```python
def process_film_spectral_tiled(
    image_rgb: np.ndarray,
    film: FilmProfile,
    tile_size: int = 512
) -> np.ndarray:
    """
    分塊處理光譜模擬（記憶體優化）
    
    Args:
        image_rgb: (H, W, 3)
        film: 膠片配置
        tile_size: 每個 tile 的大小（像素）
    
    Returns:
        output_rgb: (H, W, 3)
    """
    H, W, _ = image_rgb.shape
    output_rgb = np.zeros_like(image_rgb)
    
    for y in range(0, H, tile_size):
        for x in range(0, W, tile_size):
            # 提取 tile
            y_end = min(y + tile_size, H)
            x_end = min(x + tile_size, W)
            tile_rgb = image_rgb[y:y_end, x:x_end]
            
            # 光譜處理
            tile_output = process_film_simulation(
                tile_rgb, film, use_spectral=True
            )
            
            # 寫回
            output_rgb[y:y_end, x:x_end] = tile_output
    
    return output_rgb
```

### Milestone 5: 測試與驗證（Day 2, 4h）

#### 任務 5.1: 單元測試
**文件**: `tests/test_spectral_model.py`

```python
def test_rgb_to_spectrum():
    """測試 RGB → 光譜重建"""
    # 測試 1: 白色 → 平坦光譜
    rgb_white = np.array([1, 1, 1])
    spectrum = rgb_to_spectrum(rgb_white)
    assert spectrum.shape == (31,)
    assert np.allclose(spectrum, 1.0, atol=0.1)
    
    # 測試 2: 紅色 → 主峰在 650nm
    rgb_red = np.array([1, 0, 0])
    spectrum = rgb_to_spectrum(rgb_red)
    peak_idx = np.argmax(spectrum)
    wavelengths = load_smits_basis()['wavelengths']
    assert wavelengths[peak_idx] >= 620
    
    # 測試 3: 逆轉換一致性
    spectrum = rgb_to_spectrum([0.5, 0.3, 0.8])
    xyz = spectrum_to_xyz(spectrum)
    rgb_recovered = xyz_to_srgb(xyz)
    assert np.allclose(rgb_recovered, [0.5, 0.3, 0.8], atol=0.05)

def test_film_response_spectral():
    """測試光譜域膠片響應"""
    # 載入測試影像
    rgb = np.random.rand(100, 100, 3)
    spectrum = rgb_to_spectrum(rgb)
    
    # 測試 Portra400
    film = get_film_profile("Portra400")
    lux_r, lux_g, lux_b = compute_film_response_spectral(spectrum, film)
    
    # 驗證形狀
    assert lux_r.shape == (100, 100)
    
    # 驗證能量守恆
    total_energy_in = np.sum(spectrum)
    total_energy_out = np.sum(lux_r + lux_g + lux_b)
    ratio = total_energy_out / total_energy_in
    assert 0.8 <= ratio <= 1.2  # 容許 20% 差異

def test_color_temperature_simulation():
    """測試色溫模擬"""
    rgb = np.array([0.5, 0.5, 0.5])  # 灰色
    spectrum = rgb_to_spectrum(rgb)
    
    # 日光 D65 (5500K)
    illuminant_d65 = get_illuminant(5500)
    xyz_d65 = spectrum_to_xyz(spectrum, illuminant_d65)
    rgb_d65 = xyz_to_srgb(xyz_d65)
    
    # 鎢絲燈 A (2800K)
    illuminant_a = get_illuminant(2800)
    xyz_a = spectrum_to_xyz(spectrum, illuminant_a)
    rgb_a = xyz_to_srgb(xyz_a)
    
    # 鎢絲燈下應偏黃（R > B）
    assert rgb_a[0] > rgb_a[2]  # R > B
    assert rgb_d65[0] < rgb_d65[2]  # D65: B > R
```

#### 任務 5.2: 端對端測試
**文件**: `tests/test_spectral_e2e.py`

```python
def test_spectral_vs_rgb_consistency():
    """測試光譜模式與 RGB 模式一致性"""
    # 載入測試影像
    test_image = load_test_image()  # (500, 500, 3)
    
    film = get_film_profile("Portra400")
    
    # RGB 模式（當前）
    output_rgb = process_film_simulation(
        test_image, film, use_spectral=False
    )
    
    # 光譜模式
    output_spectral = process_film_simulation(
        test_image, film, use_spectral=True
    )
    
    # 視覺一致性（PSNR > 30dB）
    psnr = compute_psnr(output_rgb, output_spectral)
    assert psnr > 30, f"PSNR too low: {psnr:.2f} dB"
    
    # 色彩準確度（ΔE2000 < 10）
    delta_e = compute_delta_e_2000(output_rgb, output_spectral)
    assert np.mean(delta_e) < 10

def test_spectral_memory_usage():
    """測試記憶體占用"""
    test_image = np.random.rand(2000, 3000, 3)
    film = get_film_profile("Portra400")
    
    import tracemalloc
    tracemalloc.start()
    
    # 執行光譜模式（分塊處理）
    output = process_film_spectral_tiled(
        test_image, film, tile_size=512
    )
    
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # 記憶體峰值 < 500 MB（10x RGB 模式）
    assert peak < 500 * 1024 * 1024, f"Memory peak: {peak / 1024**2:.1f} MB"

def test_spectral_performance():
    """測試處理時間"""
    test_image = np.random.rand(2000, 3000, 3)
    film = get_film_profile("Portra400")
    
    import time
    start = time.time()
    
    output = process_film_spectral_tiled(test_image, film)
    
    elapsed = time.time() - start
    
    # 處理時間 < 4.2s（2x RGB baseline）
    assert elapsed < 4.2, f"Processing time: {elapsed:.2f}s"
```

---

## 📊 風險評估與緩解

### 風險 1: 記憶體爆炸 ⚠️

**風險描述**: 31 通道 × 2000×3000 = 186 MB，可能導致 OOM

**緩解方案**:
1. ✅ **分塊處理**（Milestone 4.2）: 512×512 tile，記憶體峰值 < 10 MB/tile
2. ✅ **float16 半精度**: 記憶體減半（93 MB）
3. ✅ **即時釋放**: 每個 tile 處理完立即 `del` 釋放
4. ⚠️ **降級方案**: 若仍 OOM，降為 16 通道（PCA 壓縮）

**驗證**: `test_spectral_memory_usage()` 確保峰值 < 500 MB

### 風險 2: 處理時間過長 ⚠️

**風險描述**: 光譜模式可能比 RGB 慢 3-5x（6-10s）

**緩解方案**:
1. ✅ **查表法**（Milestone 2.1）: RGB→光譜查表，加速 5x
2. ✅ **降維卷積**（Milestone 3.2）: 在 RGB 域做卷積，非 31 通道
3. ✅ **Numba JIT**: 編譯加速光譜積分
4. ⚠️ **降級方案**: 提供「快速模式」（RGB）與「精確模式」（光譜）選項

**驗證**: `test_spectral_performance()` 確保 < 4.2s

### 風險 3: 膠片光譜數據缺失 ⚠️

**風險描述**: Kodak/Fuji 官方 Datasheet 難以取得或數位化

**緩解方案**:
1. ✅ **優先**: 使用文獻參考曲線（Fairchild 2005, ISO 18909）
2. ✅ **替代**: 基於 RGB 權重合成典型曲線
3. ✅ **降級**: 保留 RGB 模式作為 fallback

**驗證**: `generate_film_spectra.py` 腳本生成至少 3 個膠片的典型曲線

### 風險 4: 色彩準確度未達標 ⚠️

**風險描述**: 光譜模式色彩準確度 ΔE2000 > 10（不達專業級）

**根因分析**:
- RGB → 光譜重建有誤差（Smits 算法限制）
- 膠片光譜曲線不準確（非官方數據）
- XYZ → sRGB 轉換矩陣不適用膠片場景

**緩解方案**:
1. ✅ **Smits 算法驗證**: 確保 RGB ↔ 光譜往返誤差 < 5%
2. ✅ **多膠片對比**: 至少測試 3 個膠片（Portra, Velvia, Tri-X）
3. ⚠️ **色彩校正**: 若 ΔE > 10，加入 LUT 微調層

**驗證**: `test_spectral_vs_rgb_consistency()` 確保 ΔE2000 < 10

---

## 🎯 驗收標準

### 必須通過（P0）

1. ✅ **數據生成成功**: 3 個 .npz 文件正常載入
2. ✅ **單元測試通過**: `test_spectral_model.py` 全部通過
3. ✅ **端對端測試通過**: `test_spectral_e2e.py` 全部通過
4. ✅ **記憶體占用 < 500 MB**: 2000×3000 影像分塊處理
5. ✅ **處理時間 < 4.2s**: 2000×3000 影像光譜模式
6. ✅ **向後相容**: RGB 模式仍可用，效能不退化

### 理想達成（P1）

7. ⭐ **色彩準確度 ΔE2000 < 5**: 專業級標準
8. ⭐ **色溫模擬可用**: 鎢絲燈 vs 日光差異明顯
9. ⭐ **處理時間 < 3.0s**: 優於 2x baseline
10. ⭐ **記憶體占用 < 300 MB**: 進一步優化

---

## 📅 時間規劃

### Day 1（8 小時）

**上午（4h）**:
- ✅ Milestone 1: 數據生成（CIE, Smits, Film）
  - 1.1 CIE 1931 數據（1h）
  - 1.2 Smits 基向量（1h）
  - 1.3 膠片光譜敏感度（2h，包含數據查找）

**下午（4h）**:
- ✅ Milestone 2: 核心函數實作
  - 2.1 RGB to Spectrum（2h）
  - 2.2 Spectrum to XYZ（1h）
  - 2.3 XYZ to sRGB（1h）

### Day 2（8 小時）

**上午（4h）**:
- ✅ Milestone 3: 膠片響應整合
  - 3.1 `SpectralSensitivityParams` 定義（1h）
  - 3.2 `compute_film_response_spectral()` 實作（2h）
  - ✅ Milestone 4: 主流程整合（1h）
  - 4.1 修改 `process_film_simulation()`

**下午（4h）**:
- ✅ Milestone 4: 分塊處理（1h）
  - 4.2 `process_film_spectral_tiled()`
- ✅ Milestone 5: 測試與驗證（3h）
  - 5.1 單元測試（1.5h）
  - 5.2 端對端測試（1.5h）

---

## 📚 參考資料

### 學術論文
1. **Smits (1999)**: [An RGB-to-Spectrum Conversion for Reflectances](https://www.cs.utah.edu/~bes/papers/color/)
2. **Fairchild (2005)**: Color Appearance Models (3rd Edition)
3. **ISO 18909:2022**: Photography - Processed photographic colour films and paper prints - Methods for measuring image stability

### 技術標準
1. **CIE 1931**: Standard Colorimetric Observer
2. **sRGB IEC 61966-2-1**: Colour management standard
3. **Kodak Publication E-58**: Spectral Sensitivity of Kodak Films

### 實作參考
1. **Mitsuba Renderer**: Spectral rendering implementation
2. **PBRT v3**: Physically Based Rendering (Spectrum class)
3. **OpenColorIO**: Color management pipeline

---

**文件撰寫**: Main Agent  
**最後更新**: 2025-12-22 19:00  
**狀態**: 設計完成，待執行
