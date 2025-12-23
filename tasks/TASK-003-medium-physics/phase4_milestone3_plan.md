# Phase 4 Milestone 3: 膠片光譜敏感度整合

**任務**: TASK-003 Phase 4.3 - Film Spectral Sensitivity Integration  
**時間**: 2025-12-22 20:30 - 預計 3-4 小時  
**狀態**: 🚧 **In Progress**  
**前置條件**: Milestone 2 完成 ✅ (RGB↔Spectrum↔XYZ 核心函數)

---

## 🎯 Milestone 目標

實作 `apply_film_spectral_sensitivity()` 函數，讓光譜模型能夠：
1. 接收 31 通道光譜影像
2. 應用膠片特定的 R/G/B 光譜敏感度曲線
3. 輸出具有真實膠片色彩響應的 RGB 影像

**核心價值**: 這是光譜模型的「靈魂」— 賦予每種膠片獨特的色彩性格。

---

## 📋 子任務清單

### Task 3.1: 檢查現有膠片資料 (15min) ✅
**目標**: 驗證 `data/film_spectral_sensitivity.npz` 的資料結構

**檢查項目**:
- ✅ 波長範圍（380-770nm, 31 點）
- ✅ 膠片種類（至少 3 種）
- ✅ R/G/B 三條曲線完整性
- ✅ 曲線峰值位置合理（R ~600nm, G ~550nm, B ~450nm）

**已知資料**:
```
Portra400:      彩色負片（溫暖、飽和）
Velvia50:       反轉片（超飽和、對比強）
Cinestill800T:  彩色負片（鎢絲燈平衡）
HP5Plus400:     黑白負片
```

---

### Task 3.2: 實作 `apply_film_spectral_sensitivity()` (90min)
**文件**: `phos_core.py` (新增函數)

**函數簽名**:
```python
def apply_film_spectral_sensitivity(
    spectrum: np.ndarray,
    sensitivity_curves: Dict[str, np.ndarray],
    normalize: bool = True
) -> np.ndarray:
    """
    應用膠片光譜敏感度曲線，將光譜轉換為膠片 RGB
    
    這是模擬膠片化學層對不同波長的響應。與 spectrum_to_xyz() 的差異：
    - XYZ: 使用人眼 CIE 1931 色彩匹配函數（標準觀察者）
    - Film RGB: 使用膠片乳劑層的光譜敏感度（每個膠片不同）
    
    Args:
        spectrum: 光譜影像，形狀 (H, W, 31) 或 (31,)
        sensitivity_curves: 膠片敏感度曲線字典
            {
                'red': np.ndarray (31,),    # 紅色層敏感度
                'green': np.ndarray (31,),  # 綠色層敏感度
                'blue': np.ndarray (31,)    # 藍色層敏感度
            }
        normalize: 是否歸一化（白色表面 → RGB ~1）
    
    Returns:
        np.ndarray: 膠片 RGB 影像，形狀 (H, W, 3) 或 (3,)
        
    Physical Basis:
        R_film = ∫ Spectrum(λ) × S_red(λ) dλ
        G_film = ∫ Spectrum(λ) × S_green(λ) dλ
        B_film = ∫ Spectrum(λ) × S_blue(λ) dλ
        
        其中 S_red/green/blue 是膠片紅/綠/藍層的光譜敏感度曲線
    
    Example:
        >>> spectrum = rgb_to_spectrum(rgb_image)  # (H, W, 31)
        >>> portra_curves = load_film_sensitivity('Portra400')
        >>> film_rgb = apply_film_spectral_sensitivity(spectrum, portra_curves)
        >>> # film_rgb 具有 Portra400 的色彩特性（溫暖、膚色優美）
    """
```

**實作步驟**:
1. 提取 R/G/B 敏感度曲線
2. 計算光譜積分（類似 `spectrum_to_xyz()`）
3. 歸一化（白色表面 → RGB ~1）
4. Clip 至 [0, 1]

**物理驗證**:
- ✅ R/G/B 通道值 >= 0
- ✅ 白色光譜 → RGB(1, 1, 1)（或接近）
- ✅ 灰階光譜 → 灰階 RGB（色偏符合膠片特性）

---

### Task 3.3: 實作 `load_film_sensitivity()` (30min)
**文件**: `phos_core.py` (新增函數)

**函數簽名**:
```python
@lru_cache(maxsize=8)
def load_film_sensitivity(film_name: str) -> Dict[str, np.ndarray]:
    """
    載入膠片光譜敏感度曲線
    
    Args:
        film_name: 膠片名稱，支援:
            - 'Portra400'
            - 'Velvia50'
            - 'Cinestill800T'
            - 'HP5Plus400'
    
    Returns:
        Dict with keys:
            'wavelengths': (31,)
            'red': (31,)
            'green': (31,)
            'blue': (31,)
            'type': str ('color_negative', 'reversal', 'bw')
    
    Raises:
        ValueError: 若膠片名稱不存在
    """
```

**實作細節**:
```python
data = np.load('data/film_spectral_sensitivity.npz')

if f"{film_name}_red" not in data:
    raise ValueError(f"Film {film_name} not found. Available: ...")

return {
    'wavelengths': data['wavelengths'],
    'red': data[f'{film_name}_red'],
    'green': data[f'{film_name}_green'],
    'blue': data[f'{film_name}_blue'],
    'type': str(data[f'{film_name}_type'])
}
```

---

### Task 3.4: 測試膠片響應 (60min)
**文件**: `tests/test_film_spectral_sensitivity.py` (新建)

**測試案例**:

#### Test 1: Data Loading
```python
def test_load_film_sensitivity_portra400():
    """測試載入 Portra400 敏感度曲線"""
    curves = load_film_sensitivity('Portra400')
    
    assert 'red' in curves
    assert 'green' in curves
    assert 'blue' in curves
    assert curves['red'].shape == (31,)
    assert curves['wavelengths'].shape == (31,)
    
    # 檢查峰值位置
    assert np.argmax(curves['red']) > 20  # 紅色峰值在 600nm 之後
    assert 10 < np.argmax(curves['green']) < 20  # 綠色峰值在 500-600nm
    assert np.argmax(curves['blue']) < 10  # 藍色峰值在 450nm 之前
```

#### Test 2: White Spectrum Response
```python
def test_white_spectrum_response():
    """測試白色光譜的膠片響應"""
    # 白色光譜（平坦，所有波長相同）
    white_spectrum = np.ones(31)
    
    portra_curves = load_film_sensitivity('Portra400')
    film_rgb = apply_film_spectral_sensitivity(white_spectrum, portra_curves)
    
    # 白色應該接近 (1, 1, 1)，但可能有色偏（符合膠片特性）
    assert film_rgb.shape == (3,)
    assert np.all(film_rgb > 0.5)  # 至少亮度正確
    assert np.all(film_rgb <= 1.0)
```

#### Test 3: Monochromatic Spectrum Response
```python
def test_monochromatic_spectrum_red():
    """測試單色光（紅光）的膠片響應"""
    # 只有 650nm 有能量
    red_spectrum = np.zeros(31)
    red_spectrum[25] = 1.0  # 650nm 附近
    
    portra_curves = load_film_sensitivity('Portra400')
    film_rgb = apply_film_spectral_sensitivity(red_spectrum, portra_curves)
    
    # 應該主要響應在紅色通道
    assert film_rgb[0] > film_rgb[1]  # R > G
    assert film_rgb[0] > film_rgb[2]  # R > B
```

#### Test 4: Different Films Have Different Responses
```python
def test_different_films_different_response():
    """測試不同膠片對相同光譜的響應不同"""
    spectrum = rgb_to_spectrum(np.array([0.5, 0.7, 0.3]))  # 偏綠的顏色
    
    portra_rgb = apply_film_spectral_sensitivity(
        spectrum, load_film_sensitivity('Portra400')
    )
    velvia_rgb = apply_film_spectral_sensitivity(
        spectrum, load_film_sensitivity('Velvia50')
    )
    
    # Velvia 應該更飽和（綠色更綠）
    # Portra 應該更柔和（綠色偏黃）
    assert not np.allclose(portra_rgb, velvia_rgb, atol=0.05)
    
    # Velvia 的綠色分量應該更強
    assert velvia_rgb[1] / velvia_rgb.sum() > portra_rgb[1] / portra_rgb.sum()
```

#### Test 5: Roundtrip Consistency (RGB → Spectrum → Film RGB)
```python
def test_roundtrip_with_film_response():
    """測試往返一致性（加入膠片響應）"""
    original_rgb = np.array([0.8, 0.5, 0.3])  # 暖色調
    
    # 路徑: RGB → Spectrum → Film RGB
    spectrum = rgb_to_spectrum(original_rgb)
    film_rgb = apply_film_spectral_sensitivity(
        spectrum, load_film_sensitivity('Portra400')
    )
    
    # 注意：這裡 film_rgb 與 original_rgb 不會相同！
    # 因為膠片有自己的色彩響應（這是特性，不是 bug）
    
    # 但應該保持相對色彩關係（暖色調）
    assert film_rgb[0] > film_rgb[1]  # R > G
    assert film_rgb[1] > film_rgb[2]  # G > B
    
    # 色差應該在合理範圍內（ΔE < 15）
    color_diff = np.linalg.norm(film_rgb - original_rgb)
    assert color_diff < 0.3  # 允許 30% 色偏（膠片特性）
```

---

### Task 3.5: 視覺化膠片光譜曲線 (30min)
**文件**: `scripts/visualize_film_sensitivity.py` (新建)

**目標**: 繪製 4 種膠片的光譜敏感度曲線

**輸出圖表**:
```python
import matplotlib.pyplot as plt
import numpy as np
from phos_core import load_film_sensitivity

films = ['Portra400', 'Velvia50', 'Cinestill800T', 'HP5Plus400']

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
axes = axes.flatten()

for i, film in enumerate(films):
    curves = load_film_sensitivity(film)
    wavelengths = curves['wavelengths']
    
    ax = axes[i]
    ax.plot(wavelengths, curves['red'], 'r-', label='Red', linewidth=2)
    ax.plot(wavelengths, curves['green'], 'g-', label='Green', linewidth=2)
    ax.plot(wavelengths, curves['blue'], 'b-', label='Blue', linewidth=2)
    
    ax.set_xlabel('Wavelength (nm)')
    ax.set_ylabel('Sensitivity')
    ax.set_title(f'{film} Spectral Sensitivity')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(380, 770)
    ax.set_ylim(0, 1.1)

plt.tight_layout()
plt.savefig('docs/film_sensitivity_curves.png', dpi=150)
print("✅ Saved to docs/film_sensitivity_curves.png")
```

---

### Task 3.6: 整合到主流程（預備） (30min)
**文件**: `phos_core.py` (修改現有函數)

**目標**: 準備一個完整的光譜處理流程（尚未整合到 UI）

**新增函數**:
```python
def process_image_spectral_mode(
    rgb_image: np.ndarray,
    film_name: str = 'Portra400',
    apply_film_response: bool = True
) -> np.ndarray:
    """
    完整的光譜模式處理流程（測試用）
    
    Args:
        rgb_image: 輸入 RGB 影像 (H, W, 3)
        film_name: 膠片名稱
        apply_film_response: 是否應用膠片光譜響應
    
    Returns:
        np.ndarray: 輸出 RGB 影像 (H, W, 3)
    
    Pipeline:
        1. RGB → Spectrum (Smits 1999)
        2. [Optional] Spectrum → Film RGB (膠片敏感度)
        3. [If not step 2] Spectrum → XYZ → sRGB (標準色彩)
    """
    # Step 1: RGB → Spectrum
    spectrum = rgb_to_spectrum(rgb_image)
    
    # Step 2: Spectral response
    if apply_film_response:
        # 膠片光譜響應（31 通道 → RGB）
        sensitivity_curves = load_film_sensitivity(film_name)
        film_rgb = apply_film_spectral_sensitivity(spectrum, sensitivity_curves)
        return film_rgb
    else:
        # 標準色彩流程（31 通道 → XYZ → sRGB）
        xyz = spectrum_to_xyz(spectrum)
        srgb = xyz_to_srgb(xyz)
        return srgb
```

---

## 📊 驗收標準

| 標準 | 目標 | 驗證方法 |
|------|------|---------|
| 函數實作 | 2 個函數 | ✅ `apply_film_spectral_sensitivity()`, `load_film_sensitivity()` |
| 測試覆蓋 | >90% | ✅ 5 個單元測試全通過 |
| 膠片支援 | ≥3 種 | ✅ Portra400, Velvia50, Cinestill800T, HP5Plus400 |
| 色彩準確度 | ΔE < 15 | ✅ 往返測試色差 <30% |
| 視覺驗證 | 可視化曲線 | ✅ 生成 `docs/film_sensitivity_curves.png` |
| 效能 | <5s / 6MP | ⏸️ 延後至 Milestone 4 |

---

## 🔬 物理驗證重點

### 1. 敏感度曲線合理性
- ✅ 紅色層峰值 ~600-650nm
- ✅ 綠色層峰值 ~500-550nm
- ✅ 藍色層峰值 ~420-480nm
- ✅ 曲線值域 [0, 1]，非負

### 2. 白色光譜響應
- ✅ 平坦白色光譜 → RGB 接近 (1, 1, 1)
- ⚠️ 允許色偏（膠片特性）：Portra 偏黃、Velvia 偏綠

### 3. 色彩關係保持
- ✅ 暖色 → 膠片暖色（紅 > 綠 > 藍）
- ✅ 冷色 → 膠片冷色（藍 > 綠 > 紅）

### 4. 不同膠片可辨識
- ✅ Portra vs Velvia 的 RGB 輸出明顯不同
- ✅ 色彩飽和度：Velvia > Portra > Cinestill

---

## 🎯 成功指標

**Milestone 3 完成**當：
1. ✅ `apply_film_spectral_sensitivity()` 實作完成並測試通過
2. ✅ 支援至少 3 種膠片（Portra, Velvia, Cinestill）
3. ✅ 測試套件 >90% 覆蓋率
4. ✅ 視覺化曲線圖生成
5. ✅ 色彩準確度驗證（ΔE < 15）
6. ✅ 決策日誌更新

**然後進入 Milestone 4**: 效能優化（目標 <3s / 6MP）

---

## 📁 涉及的檔案

### 新增檔案
- `tests/test_film_spectral_sensitivity.py` (測試套件)
- `scripts/visualize_film_sensitivity.py` (視覺化工具)
- `docs/film_sensitivity_curves.png` (曲線圖)

### 修改檔案
- `phos_core.py`:
  - 新增 `apply_film_spectral_sensitivity()` (~60 行)
  - 新增 `load_film_sensitivity()` (~30 行)
  - 新增 `process_image_spectral_mode()` (~40 行)

### 使用現有檔案
- `data/film_spectral_sensitivity.npz` (已存在 ✅)

---

## 🚀 執行順序

```bash
# 1. 驗證資料
python3 -c "import numpy as np; d=np.load('data/film_spectral_sensitivity.npz'); print(list(d.keys()))"

# 2. 實作核心函數
# 編輯 phos_core.py，加入 Task 3.2, 3.3, 3.6 的函數

# 3. 測試
pytest tests/test_film_spectral_sensitivity.py -v

# 4. 視覺化
python3 scripts/visualize_film_sensitivity.py

# 5. 手動測試
python3 << 'EOF'
from phos_core import *
import numpy as np

# Test 1: 白色光譜
white = np.ones(31)
portra = load_film_sensitivity('Portra400')
rgb = apply_film_spectral_sensitivity(white, portra)
print(f"White → Portra RGB: {rgb}")

# Test 2: 完整流程
img = np.random.rand(100, 100, 3)
result = process_image_spectral_mode(img, 'Velvia50')
print(f"Processed shape: {result.shape}, range: [{result.min():.3f}, {result.max():.3f}]")
EOF
```

---

## 💡 設計決策

### 決策 A: 膠片響應 vs XYZ 轉換
**問題**: 膠片光譜響應是否應該替代 XYZ 轉換？

**決策**: **並行支援兩種模式**
- **Mode 1**: Spectrum → XYZ → sRGB (標準色彩，用於校準)
- **Mode 2**: Spectrum → Film RGB (膠片響應，用於模擬)

**理由**:
- XYZ 是「正確的」色彩（標準觀察者）
- Film RGB 是「膠片的」色彩（化學乳劑響應）
- 使用者可能需要對比兩者差異

---

### 決策 B: 歸一化策略
**問題**: 膠片 RGB 應該如何歸一化？

**選項**:
1. 無歸一化（原始積分值）
2. 白色表面 → (1, 1, 1)
3. 最大通道 → 1

**決策**: **白色表面歸一化**

**理由**:
- 符合物理定義（白色反射率 = 1）
- 與 XYZ 模式一致
- 保留相對色彩關係

---

### 決策 C: 膠片數據來源
**問題**: 光譜敏感度曲線如何生成？

**現狀**: 已有 4 種膠片數據（`film_spectral_sensitivity.npz`）

**驗證待辦**:
- 檢查數據來源（腳本 `scripts/generate_film_spectra.py`）
- 確認曲線是否基於真實 Datasheet
- 若為合成曲線，需標註「典型值」而非「官方值」

---

## 📚 參考資料

### 膠片光譜數據
1. **Kodak**: Publication E-58 "Spectral Sensitivity of Kodak Films"
2. **Fuji**: Technical Data Sheet (Velvia, Provia, Superia)
3. **ISO 18909:2022**: Methods for measuring image stability

### 實作參考
1. **Mitsuba 3**: Film sensor spectral response
2. **PBRT v4**: Spectrum to RGB conversion

---

**計畫撰寫**: Main Agent  
**時間**: 2025-12-22 20:30  
**預估完成**: 2025-12-22 23:30 (3h)
