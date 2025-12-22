# TASK-003 Phase 4: 光譜模型（31 波長通道）

**任務 ID**: TASK-003-Phase-4  
**優先級**: P1（高優先）  
**ROI**: ⭐⭐⭐⭐（+200% 時間，+40% 色彩準確度）  
**預估時間**: 1.5 天（12 小時）  
**狀態**: ⏳ 設計中

---

## 📋 任務概述

### 目標
將當前 RGB 三通道模型升級為 **31 波長通道光譜模型**，顯著提升色彩準確度與物理真實感。

### 成功指標
- ✅ RGB → Spectrum → RGB 往返誤差 < 5%
- ✅ 色彩準確度提升 +40%（主觀評估）
- ✅ 處理時間 < 10s（2000×3000 影像）
- ✅ 記憶體占用 < 4GB
- ✅ 能量守恆維持（< 0.01% 誤差）

---

## 🎯 核心概念

### 當前問題
```python
# RGB 三通道，無波長分辨
response_r = red_layer.r_response_weight * R + \
             red_layer.g_response_weight * G + \
             red_layer.b_response_weight * B  # 粗糙近似
```

**限制**：
- 無法模擬「色溫影響」（鎢絲燈 vs 日光）
- 無法模擬「濾鏡效果」（黃濾鏡、紅濾鏡）
- Bloom 的「顏色分離」不夠真實
- 色彩準確度受限於 RGB 色域

### 光譜模型原理

#### 1. 波長通道劃分
```
380nm ───────────────────────────────────────── 780nm
  |     |     |     |     |     |     |     |
 UV    藍    青    綠    黃    橙    紅    近紅外

31 通道：380, 393, 406, ..., 767, 780 nm（每 13nm）
```

#### 2. 處理流程
```
輸入影像（RGB）
    ↓
RGB → Spectrum 重建（Smits 1999 算法）
    ↓
光譜響應計算（膠片敏感度曲線）
    ↓
Spectrum → XYZ → RGB（色彩空間轉換）
    ↓
輸出影像（RGB）
```

#### 3. 關鍵方程

**RGB → Spectrum（Smits 1999）**：
```
S(λ) = w_white · S_white(λ) + 
       w_cyan · S_cyan(λ) + 
       w_magenta · S_magenta(λ) + 
       w_yellow · S_yellow(λ) + 
       w_red · S_red(λ) + 
       w_green · S_green(λ) + 
       w_blue · S_blue(λ)

權重 w_* 由 RGB 值決定（分段線性插值）
```

**膠片光譜響應**：
```
Response = ∫ S(λ) · T(λ) · Sensitivity(λ) dλ

S(λ): 入射光譜
T(λ): 透過率（Beer-Lambert）
Sensitivity(λ): 膠片敏感度曲線
```

**Spectrum → XYZ**：
```
X = k · ∫ S(λ) · x̄(λ) dλ
Y = k · ∫ S(λ) · ȳ(λ) dλ
Z = k · ∫ S(λ) · z̄(λ) dλ

x̄, ȳ, z̄: CIE 1931 色彩匹配函數
k: 歸一化常數
```

---

## 🏗️ 架構設計

### 新增模組：`color_utils.py`

```python
"""
色彩科學工具模組

功能：
1. RGB ↔ Spectrum 轉換
2. Spectrum ↔ XYZ 轉換
3. XYZ ↔ RGB 轉換
4. 光譜積分運算
"""

import numpy as np
from typing import Tuple, Optional

# ============================================================
# 1. 常數定義
# ============================================================

# 波長範圍（380-780nm，每 13nm）
WAVELENGTHS = np.arange(380, 781, 13)  # (31,)

# CIE 1931 色彩匹配函數（在 WAVELENGTHS 位置插值）
CIE_X_BAR = np.array([...])  # (31,)
CIE_Y_BAR = np.array([...])  # (31,)
CIE_Z_BAR = np.array([...])  # (31,)

# Smits (1999) 基底光譜
BASIS_SPECTRA = {
    'white':   np.array([...]),  # (31,)
    'cyan':    np.array([...]),
    'magenta': np.array([...]),
    'yellow':  np.array([...]),
    'red':     np.array([...]),
    'green':   np.array([...]),
    'blue':    np.array([...])
}


# ============================================================
# 2. RGB → Spectrum 轉換
# ============================================================

def rgb_to_spectrum(rgb: np.ndarray) -> np.ndarray:
    """
    將 RGB 影像轉換為光譜影像（Smits 1999）
    
    Args:
        rgb: RGB 影像 (H, W, 3)，值域 [0, 1]
    
    Returns:
        spectrum: 光譜影像 (H, W, 31)，值域 [0, 1]
    
    原理：
        根據 RGB 值選擇基底光譜並混合
        - RGB 接近 (1,1,1) → white
        - RGB 接近 (0,1,1) → cyan
        - RGB 接近 (1,0,0) → red
        - 其他 → 混合多個基底
    """
    pass


# ============================================================
# 3. Spectrum → XYZ 轉換
# ============================================================

def spectrum_to_xyz(spectrum: np.ndarray) -> np.ndarray:
    """
    將光譜轉換為 XYZ 色彩空間
    
    Args:
        spectrum: 光譜 (H, W, 31)
    
    Returns:
        xyz: XYZ 色彩 (H, W, 3)
    
    原理：
        X = k · Σ spectrum(λ) · x̄(λ) · Δλ
        Y = k · Σ spectrum(λ) · ȳ(λ) · Δλ
        Z = k · Σ spectrum(λ) · z̄(λ) · Δλ
    """
    pass


# ============================================================
# 4. XYZ → RGB 轉換
# ============================================================

def xyz_to_rgb(xyz: np.ndarray, 
               color_space: str = 'sRGB') -> np.ndarray:
    """
    將 XYZ 轉換為 RGB（使用標準色彩矩陣）
    
    Args:
        xyz: XYZ 色彩 (H, W, 3)
        color_space: 'sRGB', 'AdobeRGB', 'ProPhotoRGB'
    
    Returns:
        rgb: RGB 影像 (H, W, 3)
    
    原理：
        [R]   [M]   [X]
        [G] = [M] × [Y]
        [B]   [M]   [Z]
        
        M: 色彩空間轉換矩陣
    """
    pass


# ============================================================
# 5. 光譜積分工具
# ============================================================

def integrate_spectrum(spectrum: np.ndarray, 
                      weight: np.ndarray) -> np.ndarray:
    """
    計算光譜積分（梯形法則）
    
    Args:
        spectrum: 光譜 (H, W, 31)
        weight: 權重函數 (31,)，如膠片敏感度曲線
    
    Returns:
        integral: 積分結果 (H, W)
    
    原理：
        I = ∫ spectrum(λ) · weight(λ) dλ
          ≈ Σ spectrum(λ) · weight(λ) · Δλ
    """
    pass
```

---

### 修改模組：`film_models.py`

```python
@dataclass
class EmulsionLayer:
    """
    膠片感光乳劑層
    
    v0.4.0 新增：光譜敏感度曲線（Phase 4）
    """
    # ... 現有欄位 ...
    
    # Phase 4: 光譜敏感度曲線（31 個波長點）
    spectral_sensitivity: Optional[np.ndarray] = None  # (31,)
    
    def __post_init__(self):
        """初始化光譜敏感度曲線（如未指定）"""
        if self.spectral_sensitivity is None:
            # 預設：高斯形狀
            # Red layer: 峰值 650nm
            # Green layer: 峰值 550nm
            # Blue layer: 峰值 450nm
            self.spectral_sensitivity = self._default_spectral_curve()
    
    def _default_spectral_curve(self) -> np.ndarray:
        """生成預設光譜敏感度曲線（高斯分布）"""
        from color_utils import WAVELENGTHS
        
        # 根據層類型決定峰值波長
        # 這裡需要額外資訊來判斷是 R/G/B 層
        # 暫時使用簡化邏輯
        peak_wavelength = 550  # 預設綠光
        sigma = 50  # nm
        
        curve = np.exp(-((WAVELENGTHS - peak_wavelength) ** 2) / (2 * sigma ** 2))
        return curve / curve.max()  # 歸一化
```

---

### 修改模組：`Phos_0.3.0.py`

```python
def spectral_response_full(image_rgb: np.ndarray, 
                          film: FilmProfile) -> Tuple[np.ndarray, ...]:
    """
    完整光譜響應計算（Phase 4）
    
    Args:
        image_rgb: 輸入影像 (H, W, 3)，RGB，[0, 1]
        film: 膠片配置
    
    Returns:
        (response_r, response_g, response_b): 三層響應 (H, W)
    
    流程：
        1. RGB → Spectrum (31 通道)
        2. 對每層計算光譜積分
        3. 返回三層響應（仍然是單通道）
    
    注意：
        - 輸出仍然是 RGB 三通道（與現有流程相容）
        - 但內部使用光譜計算，色彩準確度更高
    """
    from color_utils import rgb_to_spectrum, integrate_spectrum
    
    # 1. RGB → Spectrum
    spectrum = rgb_to_spectrum(image_rgb)  # (H, W, 31)
    
    # 2. 計算各層響應
    response_r = integrate_spectrum(spectrum, film.red_layer.spectral_sensitivity)
    response_g = integrate_spectrum(spectrum, film.green_layer.spectral_sensitivity)
    response_b = integrate_spectrum(spectrum, film.blue_layer.spectral_sensitivity)
    
    return response_r, response_g, response_b


def spectral_reconstruction(response_r: np.ndarray,
                           response_g: np.ndarray,
                           response_b: np.ndarray,
                           film: FilmProfile) -> np.ndarray:
    """
    從三層響應重建 RGB 影像（光譜路徑）
    
    Args:
        response_r/g/b: 三層響應 (H, W)
    
    Returns:
        rgb_reconstructed: RGB 影像 (H, W, 3)
    
    流程：
        1. 從響應重建光譜（逆運算）
        2. Spectrum → XYZ → RGB
    
    注意：
        - 這是簡化版（真實膠片無法精確逆轉）
        - 使用「推測性重建」（基於膠片特性）
    """
    from color_utils import spectrum_to_xyz, xyz_to_rgb
    
    # 1. 推測光譜（使用各層敏感度曲線加權）
    # 簡化：假設各層獨立，光譜為三層貢獻之和
    spectrum_reconstructed = (
        response_r[:, :, None] * film.red_layer.spectral_sensitivity +
        response_g[:, :, None] * film.green_layer.spectral_sensitivity +
        response_b[:, :, None] * film.blue_layer.spectral_sensitivity
    )
    
    # 2. Spectrum → XYZ
    xyz = spectrum_to_xyz(spectrum_reconstructed)
    
    # 3. XYZ → RGB
    rgb = xyz_to_rgb(xyz, color_space='sRGB')
    
    return rgb
```

---

## 📊 數據準備

### 1. CIE 1931 色彩匹配函數

**來源**: CIE 官方資料  
**檔案**: `data/color_matching_functions/cie_1931_xyz.csv`

```csv
wavelength,x_bar,y_bar,z_bar
380,0.0014,0.0000,0.0065
390,0.0042,0.0001,0.0201
400,0.0143,0.0004,0.0679
...
770,0.0000,0.0000,0.0000
780,0.0000,0.0000,0.0000
```

**處理**：插值到 31 個波長點（380, 393, ..., 780 nm）

### 2. Smits (1999) 基底光譜

**來源**: Smits, Brian. "An RGB-to-Spectrum Conversion for Reflectances." Journal of Graphics Tools (1999).

**基底光譜**：
- White: 平坦（全波段 1.0）
- Cyan: 短波高，長波低
- Magenta: 短波高，中波低，長波高
- Yellow: 短波低，長波高
- Red: 長波高（600-780nm）
- Green: 中波高（500-600nm）
- Blue: 短波高（380-500nm）

**檔案**: `data/smits_basis_spectra.npz`

### 3. 膠片光譜敏感度曲線

**來源**: 
- Kodak: [Kodak Publication H-1: Kodak Filters](https://www.kodak.com/...)
- Fujifilm: [Fujifilm Technical Data](https://www.fujifilm.com/...)

**檔案**: `data/film_spectral_curves/`
```
kodak_portra_400_red.csv
kodak_portra_400_green.csv
kodak_portra_400_blue.csv
fuji_velvia_50_red.csv
...
```

**格式**:
```csv
wavelength,sensitivity
380,0.001
393,0.005
406,0.015
...
650,0.950  # Red layer 峰值
...
780,0.002
```

---

## 🚨 風險與緩解

### 風險 1: 記憶體溢出（31 通道 vs 3 通道）
**機率**: 高  
**影響**: 高

**記憶體估算**:
```
2000 × 3000 × 31 通道 × 4 bytes (float32) = 744 MB
加上中間變數（3-5x）= 2-4 GB
```

**緩解策略**:

1. **使用 float16（半精度）**:
```python
spectrum = rgb_to_spectrum(image_rgb).astype(np.float16)  # 372 MB
```

2. **分塊處理（Tile-based）**:
```python
def process_spectral_tiled(image, film, tile_size=512):
    """分塊處理，避免整張影像載入"""
    H, W = image.shape[:2]
    result = np.zeros((H, W, 3), dtype=np.float32)
    
    for y in range(0, H, tile_size):
        for x in range(0, W, tile_size):
            tile = image[y:y+tile_size, x:x+tile_size]
            result_tile = process_spectral_full(tile, film)
            result[y:y+tile_size, x:x+tile_size] = result_tile
    
    return result
```

3. **及時釋放中間結果**:
```python
spectrum = rgb_to_spectrum(image)
response = integrate_spectrum(spectrum, sensitivity)
del spectrum  # 立即釋放
gc.collect()
```

### 風險 2: 效能超標（+200% 時間）
**機率**: 中  
**影響**: 高

**當前基準**: 2000×3000 影像 ~2s  
**預期**: 2s × 3 = 6s（仍在 10s 目標內）

**緩解策略**:

1. **向量化運算（避免迴圈）**:
```python
# Bad: 逐像素迴圈
for i in range(H):
    for j in range(W):
        spectrum[i, j, :] = rgb_to_spectrum_pixel(image[i, j])

# Good: 向量化
spectrum = rgb_to_spectrum(image)  # 一次處理整張影像
```

2. **預計算與快取**:
```python
@lru_cache(maxsize=32)
def get_film_spectral_curves(film_name):
    """快取膠片光譜曲線，避免重複載入"""
    return load_spectral_curves(film_name)
```

3. **降採樣選項**（用戶可選）:
```python
if enable_spectral_mode and image.shape[0] > 3000:
    # 提示用戶：大圖可能較慢
    st.warning("光譜模式處理大圖較慢（預估 15s），建議縮小至 3000px")
```

### 風險 3: RGB → Spectrum 重建誤差
**機率**: 中  
**影響**: 中

**問題**: RGB 是低維（3 通道），Spectrum 是高維（31 通道），存在「欠定問題」（underdetermined）。

**緩解策略**:

1. **使用 Smits 1999 算法**（經典方法，誤差 ~5%）
2. **添加往返測試**:
```python
def test_rgb_spectrum_roundtrip():
    """RGB → Spectrum → XYZ → RGB 往返測試"""
    rgb_original = np.array([0.8, 0.3, 0.2])
    
    spectrum = rgb_to_spectrum(rgb_original)
    xyz = spectrum_to_xyz(spectrum)
    rgb_reconstructed = xyz_to_rgb(xyz)
    
    error = np.mean(np.abs(rgb_original - rgb_reconstructed))
    assert error < 0.05, f"往返誤差過大: {error:.4f}"
```

3. **視覺對比驗證**（ColorChecker 標準色卡）

---

## 📝 實作步驟

### Phase 4.1: 設計光譜模型架構 ⏳

**任務**:
- 創建 `color_utils.py` 骨架
- 定義常數（WAVELENGTHS, CIE_X_BAR, etc.）
- 設計函數介面

**產出**:
- `color_utils.py` (~200 lines, 未實作)

**時間**: 1 hour

---

### Phase 4.2: 實作 RGB → Spectrum 轉換 ⏳

**任務**:
- 實作 Smits 1999 算法
- 準備基底光譜數據
- 測試往返誤差

**產出**:
- `rgb_to_spectrum()` 函數
- `data/smits_basis_spectra.npz`
- `tests/test_rgb_to_spectrum.py`

**時間**: 3 hours

**驗收**:
```python
def test_rgb_to_spectrum_basic():
    # 測試純色
    rgb_red = np.array([1, 0, 0])
    spectrum = rgb_to_spectrum(rgb_red)
    
    # 紅色應在長波段有高值
    assert spectrum[WAVELENGTHS > 600].mean() > 0.7
    assert spectrum[WAVELENGTHS < 500].mean() < 0.3
```

---

### Phase 4.3: 實作 Spectrum → XYZ → RGB 轉換 ⏳

**任務**:
- 實作 `spectrum_to_xyz()`
- 實作 `xyz_to_rgb()`
- 準備 CIE 1931 數據

**產出**:
- `spectrum_to_xyz()`, `xyz_to_rgb()` 函數
- `data/color_matching_functions/cie_1931_xyz.csv`
- `tests/test_spectrum_to_rgb.py`

**時間**: 2 hours

**驗收**:
```python
def test_spectrum_to_rgb_roundtrip():
    """RGB → Spectrum → XYZ → RGB 往返測試"""
    rgb_original = np.array([[[0.8, 0.3, 0.2]]])  # (1, 1, 3)
    
    spectrum = rgb_to_spectrum(rgb_original)
    xyz = spectrum_to_xyz(spectrum)
    rgb_reconstructed = xyz_to_rgb(xyz)
    
    error = np.mean(np.abs(rgb_original - rgb_reconstructed))
    assert error < 0.05  # < 5% 誤差
```

---

### Phase 4.4: 建立膠片光譜敏感度曲線數據 ⏳

**任務**:
- 查找 Kodak/Fuji 官方資料
- 整理為標準格式 CSV
- 創建高斯近似（如無官方資料）

**產出**:
- `data/film_spectral_curves/*.csv`
- `scripts/generate_spectral_curves.py`（生成高斯近似）

**時間**: 2 hours

**範例（高斯近似）**:
```python
def generate_gaussian_spectral_curve(peak_wavelength: float, 
                                     sigma: float = 50) -> np.ndarray:
    """生成高斯形狀的光譜敏感度曲線"""
    curve = np.exp(-((WAVELENGTHS - peak_wavelength) ** 2) / (2 * sigma ** 2))
    return curve / curve.max()

# Portra 400
red_curve = generate_gaussian_spectral_curve(650, sigma=60)
green_curve = generate_gaussian_spectral_curve(550, sigma=50)
blue_curve = generate_gaussian_spectral_curve(450, sigma=55)
```

---

### Phase 4.5: 修改 EmulsionLayer 新增 spectral_sensitivity ⏳

**任務**:
- 修改 `film_models.py`
- 為所有現有膠片生成光譜曲線
- 更新 `__post_init__` 邏輯

**產出**:
- `film_models.py` (+50 lines)
- 所有膠片配置包含 `spectral_sensitivity`

**時間**: 1 hour

---

### Phase 4.6: 整合到主處理流程並測試 ⏳

**任務**:
- 實作 `spectral_response_full()`
- 修改 `optical_processing()` 添加光譜模式開關
- 創建測試配置（如 `Portra400_Spectral`）

**產出**:
- `Phos_0.3.0.py` (+150 lines)
- `tests/test_spectral_integration.py`

**時間**: 2 hours

**開關設計**:
```python
@dataclass
class FilmProfile:
    # ... 現有欄位 ...
    
    # Phase 4: 光譜模式開關
    use_spectral_model: bool = False  # 預設關閉（向後相容）
```

---

### Phase 4.7: 記憶體優化（分塊處理、float16）⏳

**任務**:
- 實作分塊處理
- 測試 float16 精度損失
- 添加記憶體監控

**產出**:
- `process_spectral_tiled()` 函數
- `tests/test_spectral_memory.py`

**時間**: 2 hours

**驗收**:
```python
def test_spectral_memory_usage():
    """測試記憶體占用"""
    import psutil
    
    process = psutil.Process()
    mem_before = process.memory_info().rss / 1024 / 1024  # MB
    
    image = np.random.rand(2000, 3000, 3).astype(np.float32)
    result = process_spectral_full(image, film)
    
    mem_after = process.memory_info().rss / 1024 / 1024
    mem_used = mem_after - mem_before
    
    assert mem_used < 4096, f"記憶體占用過大: {mem_used:.0f} MB"
```

---

### Phase 4.8: 測試與驗證（色彩準確度、效能）⏳

**任務**:
- 色彩準確度測試（ColorChecker 24）
- 效能基準測試（< 10s）
- 視覺對比測試（Spectral vs RGB）

**產出**:
- `tests/test_spectral_accuracy.py`
- `tests/test_spectral_performance.py`
- 視覺對比報告

**時間**: 2 hours

**驗收**:
```python
def test_spectral_performance():
    """效能基準測試"""
    image = np.random.rand(2000, 3000, 3).astype(np.float32)
    film = get_film_profile("Portra400_Spectral")
    
    start = time.time()
    result = process_image_spectral(image, film)
    elapsed = time.time() - start
    
    assert elapsed < 10.0, f"處理時間超標: {elapsed:.2f}s"
```

---

## 📚 參考資料

### 學術文獻
1. **Smits, Brian (1999)**. "An RGB-to-Spectrum Conversion for Reflectances." *Journal of Graphics Tools* 4(4):11-22.
2. **CIE 15:2004**. "Colorimetry, 3rd edition." Commission Internationale de l'Éclairage.
3. **Meng et al. (2015)**. "Efficient Spectral Rendering with Hardware-accelerated Lookup Tables." *ACM TOG*.

### 技術資源
- **colour-science**: https://colour-science.org/
- **CIE Data**: http://www.cie.co.at/
- **Kodak Technical Data**: https://www.kodak.com/en/motion/page/technical-information

### 實作參考
- Mitsuba 3 Renderer（光譜渲染器）
- Blender Cycles（色彩管理）
- RawTherapee（光譜重建）

---

## ✅ 驗收檢查清單

### 功能驗收
- [ ] RGB → Spectrum 轉換正確（往返誤差 < 5%）
- [ ] Spectrum → XYZ → RGB 轉換正確
- [ ] 膠片光譜敏感度曲線就緒（至少 3 種膠片）
- [ ] 光譜模式可開關（向後相容）
- [ ] 色彩準確度提升（主觀評估 +40%）

### 技術驗收
- [ ] 處理時間 < 10s（2000×3000）
- [ ] 記憶體占用 < 4GB
- [ ] 能量守恆維持（< 0.01% 誤差）
- [ ] 無 NaN/Inf 錯誤
- [ ] 所有測試通過（15+ 項）

### 文檔驗收
- [ ] `color_utils.py` 完整文檔字串
- [ ] README 更新（光譜模式說明）
- [ ] COMPUTATIONAL_OPTICS_TECHNICAL_DOC 更新
- [ ] 新增 SPECTRAL_MODE_GUIDE.md

---

**設計完成時間**: 2025-12-20 01:45  
**預計開始時間**: 2025-12-20 02:00  
**負責人**: Main Agent  
**狀態**: ⏳ 設計完成，準備實作
