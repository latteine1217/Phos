# TASK-003: 中等物理模擬升級

**任務 ID**: TASK-003  
**優先級**: P0（高優先）  
**預估時間**: 3-5 天（完整實作 + 測試）  
**目標**: 從當前「簡化物理」（25%）升級至「中等物理」（50-60%）  
**時間約束**: 單張處理時間 < 10s（2000×3000 影像）

---

## 📋 任務概述

### 目標
將 Phos 從「物理啟發」升級至「中等物理模擬」，在保持實用性（< 10s 處理）的前提下，顯著提升物理準確度與視覺真實感。

### 成功指標
- ✅ **物理完整度**: 25% → 50-60%
- ✅ **視覺真實感**: +30-40%（主觀評估）
- ✅ **處理時間**: < 10s / 張（2000×3000）
- ✅ **能量守恆**: 維持 < 0.01% 誤差
- ✅ **測試覆蓋**: 新增 15+ 項測試
- ✅ **向後相容**: 現有 API 不破壞

---

## 🎯 核心改進項目

### Phase 1: 波長依賴散射 ⭐⭐⭐⭐⭐
**ROI**: 最高（+20% 時間，+30% 真實感）

#### 當前問題
```python
# RGB 三通道使用相同 PSF（不符合物理）
bloom_r = Conv(response_r, PSF_gaussian)
bloom_g = Conv(response_g, PSF_gaussian)  # ← 應該不同！
bloom_b = Conv(response_b, PSF_gaussian)
```

#### 物理原理
- **Rayleigh 散射**: σ_scatter ∝ λ⁻⁴
- 藍光（450nm）散射 >> 紅光（650nm）
- 散射比例: σ_blue / σ_red ≈ (650/450)⁴ ≈ 4.4x

#### 改進方案
```python
# 三個獨立 PSF，波長依賴
PSF_r = create_wavelength_psf(lambda_r=650nm, radius_base=20px)
PSF_g = create_wavelength_psf(lambda_g=550nm, radius_base=20px)
PSF_b = create_wavelength_psf(lambda_b=450nm, radius_base=20px)

# 藍光 PSF 半徑 > 紅光（更強散射）
radius_b = radius_base × (lambda_r / lambda_b) ** 2  # ≈ 2.1x
```

#### 預期效果
- 高光周圍出現「藍色光暈」（真實膠片特徵）
- Bloom 的「顏色分離」（色散效應）
- 夜景路燈呈現「藍色外圈」

#### 實作檔案
- `film_models.py`: 新增 `WavelengthBloomParams`
- `Phos_0.3.0.py`: 修改 `apply_bloom_conserved()`
- `tests/test_wavelength_bloom.py`: 新增測試

#### 驗收標準
- [ ] PSF 半徑比例符合 λ⁻² 關係
- [ ] 能量守恆維持（< 0.01% 誤差）
- [ ] 視覺測試：白色高光產生藍色光暈

---

### Phase 2: Halation 獨立建模 ⭐⭐⭐⭐⭐ ✅ **完成**
**ROI**: 極高（+10% 時間，+25% 真實感）  
**完成日期**: 2025-12-19  
**實際效能**: 0.136s（2000×3000），遠優於 10s 目標

#### 當前問題
```python
# Bloom 與 Halation 混合在一起
bloom = Conv(highlights, PSF_gaussian)  # 無法區分來源
```

#### 物理原理
- **Bloom**: 膠片乳劑層內的前向散射（Mie）
- **Halation**: 光線穿透乳劑，在背層（或相機背板）反射回來
- 特性差異：
  - Bloom: 短距離（10-30px），高頻細節
  - Halation: 長距離（50-150px），大範圍光暈

#### 改進方案
```python
# 分離計算
def apply_optical_effects(response, film):
    # 1. Bloom（乳劑內散射）
    bloom = apply_bloom_intra_emulsion(response, 
                                       psf_radius=20px, 
                                       scattering_ratio=0.08)
    
    # 2. Halation（背層反射）
    halation = apply_halation_back_reflection(response, 
                                              psf_radius=100px, 
                                              reflection_ratio=film.AH_layer_absorption,
                                              wavelength_dependent=True)
    
    # 3. 組合（能量守恆）
    total_scattered = bloom + halation
    result = response - (bloom_energy + halation_energy) + total_scattered
    
    return result
```

#### 參數設計
```python
@dataclass
class HalationParams:
    """背層反射參數"""
    enabled: bool = True
    
    # Anti-Halation 層吸收率（0 = 完全吸收，1 = 完全反射）
    AH_absorption: float = 0.95  # 標準膠片: 95% 吸收
    
    # 背層反射 PSF（長距離）
    psf_radius: int = 100  # 像素
    psf_type: str = "exponential"  # 長尾分布
    
    # 波長依賴（紅光更易穿透）
    wavelength_attenuation: Dict[str, float] = field(default_factory=lambda: {
        'r': 0.7,  # 紅光: 30% 衰減
        'g': 0.5,  # 綠光: 50% 衰減
        'b': 0.3   # 藍光: 70% 衰減
    })
```

#### 特殊案例：CineStill 800T
```python
# CineStill 移除了 AH 層（極端 Halation）
cinestill_halation = HalationParams(
    AH_absorption=0.0,  # 完全不吸收
    psf_radius=200,     # 極大光暈
    wavelength_attenuation={'r': 0.95, 'g': 0.90, 'b': 0.85}  # 紅光主導
)
```

#### 預期效果
- 夜景高光（路燈、霓虹燈）產生「雙層光暈」
  - 內層（Bloom）：小而銳利
  - 外層（Halation）：大而柔和
- CineStill 的「紅色巨型光暈」可精確重現

#### 實作檔案
- `film_models.py`: 新增 `HalationParams`
- `Phos_0.3.0.py`: 新增 `apply_halation_back_reflection()`
- `tests/test_halation.py`: 新增測試

#### 驗收標準
- [x] Bloom 與 Halation 可獨立調整 ✅
- [x] 能量守恆（總散射 = bloom + halation）✅ 誤差 0.0000%
- [x] CineStill 800T 的極端光暈可重現 ✅

#### 實作摘要（Phase 2 Complete）

**新增檔案**:
- `tests/test_phase2_integration.py` (245 lines) - 整合測試
- `tests/test_medium_physics_e2e.py` (285 lines) - 端到端測試
- `tests/test_halation.py` (195 lines) - 單元測試

**修改檔案**:
- `film_models.py`:
  - 新增 `HalationParams` dataclass (Line 92-114)
  - 新增 `WavelengthBloomParams` dataclass (Line 117-147)
  - 新增測試配置 `Cinestill800T_MediumPhysics`, `Portra400_MediumPhysics`
  - 修改 CineStill800T 配置（Line 388-504）
  
- `Phos_0.3.0.py`:
  - 新增 `apply_halation()` 函數 (Line 854-920) - Beer-Lambert 物理
  - 新增 `apply_optical_effects_separated()` (Line 922-951) - Bloom+Halation 分離
  - 修改 `optical_processing()` 整合點 (Line 1160-1173)
  
- `context/decisions_log.md`:
  - Decision #012: Halation 設計決策完整記錄

**物理實作**:
```python
# Beer-Lambert 雙程透過率
T(λ) = exp(-α(λ)L)
f_h(λ) = (1 - ah_absorption) × R_bp × T(λ)²

# CineStill (無 AH 層):
f_h(紅) = 0.722, f_h(藍) = 0.578, 比例 = 1.25x

# Portra400 (有 AH 層):
f_h(紅) = 0.007350, f_h(藍) = 0.001350, 比例 = 5.44x
AH 層抑制效果：99.0%
```

**測試結果**:
- ✅ 能量守恆：誤差 0.0000%
- ✅ 效能測試：2000×3000 在 0.136s（< 10s 目標 ✓）
- ✅ Beer-Lambert 驗證：紅光/藍光比例符合預期
- ✅ CineStill 極端參數：ah_absorption=0.0, psf_radius=200px
- ✅ 模式檢測：中等物理模式正確啟用

**如何使用**:
```python
# 在 UI 中選擇測試配置
film_profile = "Cinestill800T_MediumPhysics"  # 或 "Portra400_MediumPhysics"

# 程序化調用
from film_models import get_film_profile
cs = get_film_profile("Cinestill800T_MediumPhysics")
assert cs.physics_mode == PhysicsMode.PHYSICAL  # ✓
assert cs.halation_params.enabled == True       # ✓
```

**已知限制**:
- ⚠️ 原始膠片配置（非 `_MediumPhysics` 版本）仍為 `PhysicsMode.ARTISTIC`
- ⚠️ 實際影像處理測試需通過 UI 進行（Streamlit 依賴問題）
- ⚠️ PSF 使用三層高斯近似指數核（精確度 ~95%）

**參考文檔**:
- `tasks/TASK-003-medium-physics/physicist_review.md` (Line 63-92)
- `context/decisions_log.md` (Decision #012)

---

### Phase 3: 顆粒叢集效應 ⭐⭐⭐⭐
**ROI**: 高（+15% 時間，+20% 真實感）

#### 當前問題
```python
# 顆粒過於「均勻」（缺少真實感）
grain = np.random.normal(0, intensity, size=image.shape)
grain_spatial = GaussianBlur(grain, sigma=grain_size)  # 仍然均勻
```

#### 物理原理
- 銀鹽晶體在乳劑中**非均勻分布**
- 存在「叢集」(Clustering): 晶體聚集成團
- 真實膠片的顆粒有「塊狀感」（非白噪聲）

#### 改進方案
```python
def generate_clustered_grain(response, grain_params):
    """生成叢集顆粒噪聲"""
    
    # 1. Poisson 光子噪聲（基礎）
    photon_noise = generate_poisson_grain(response, grain_params)
    
    # 2. 叢集遮罩（低頻噪聲）
    cluster_noise = generate_perlin_noise(
        size=response.shape,
        octaves=3,           # 多尺度
        persistence=0.5,
        lacunarity=2.0,
        seed=random.randint(0, 1000)
    )
    
    # 3. 正規化叢集遮罩（0.5-1.5 範圍）
    cluster_mask = 0.5 + cluster_noise  # 平均值 = 1.0
    
    # 4. 調製顆粒強度（叢集區域顆粒更密集）
    grain_clustered = photon_noise * cluster_mask
    
    # 5. 銀鹽顆粒尺寸（高斯模糊）
    grain_final = GaussianBlur(grain_clustered, sigma=grain_params.grain_size)
    
    return grain_final
```

#### Perlin Noise 原理
- 多尺度自然噪聲（廣泛用於程序化紋理）
- 特性：連續、非週期、類似自然叢集
- 實作：使用 `opensimplex` 或 `noise` 套件

#### 參數設計
```python
@dataclass
class GrainParams:
    # ... 現有參數 ...
    
    # 叢集效應（新增）
    clustering_enabled: bool = True
    clustering_scale: float = 1.0      # 叢集強度（0-2）
    clustering_octaves: int = 3        # Perlin 噪聲層數
    clustering_persistence: float = 0.5  # 持續度
```

#### 預期效果
- 顆粒呈現「團塊狀」分布（非均勻白噪聲）
- 某些區域顆粒密集，某些區域稀疏
- 更接近真實膠片的「有機感」

#### 實作檔案
- `film_models.py`: 擴展 `GrainParams`
- `Phos_0.3.0.py`: 修改 `generate_poisson_grain()`
- `tests/test_grain_clustering.py`: 新增測試
- `requirements.txt`: 新增 `opensimplex==0.4.5`

#### 驗收標準
- [ ] 叢集效應可視化（FFT 頻譜分析）
- [ ] 顆粒分布的「方差」增加（非均勻性）
- [ ] 視覺測試：ISO 400 顆粒呈現「團塊感」

---

### Phase 4: 光譜模型（31 波長通道）⭐⭐⭐⭐
**ROI**: 高（+200% 時間，+40% 色彩準確度）

#### 當前問題
```python
# RGB 三通道，無波長分辨
response_r = 0.32*R + 0.12*G + 0.06*B  # 粗糙近似
```

#### 改進方案
```python
# 31 波長通道（380-780nm，每 13nm）
wavelengths = np.arange(380, 781, 13)  # [380, 393, ..., 767, 780]

def spectral_response_full(image_rgb, film):
    """完整光譜響應計算"""
    
    # 1. RGB → 光譜重建（使用 Smits 1999 算法）
    spectrum = rgb_to_spectrum(image_rgb)  # (H, W, 31)
    
    # 2. 膠片光譜敏感度曲線
    for layer in [film.red_layer, film.green_layer, film.blue_layer]:
        S_r = layer.spectral_sensitivity_curve(wavelengths)  # (31,)
        response = integrate_spectrum(spectrum * S_r, wavelengths)
    
    # 3. 光譜 → RGB（XYZ 中介）
    XYZ = spectrum_to_XYZ(response_spectrum, wavelengths)
    RGB_out = XYZ_to_RGB(XYZ, color_matrix=film.ICC_profile)
    
    return RGB_out
```

#### RGB → 光譜重建
使用 **Smits (1999)** 算法：
```python
# 預先計算的基底光譜（白、青、洋紅、黃、紅、綠、藍）
basis_spectra = {
    'white':   [1.0, 1.0, ..., 1.0],     # 平坦
    'cyan':    [1.0, 1.0, ..., 0.0],     # 長波衰減
    'magenta': [1.0, 0.0, ..., 1.0],     # 中波凹陷
    # ... 其他基底
}

def rgb_to_spectrum(rgb):
    """RGB → 31 通道光譜（快速近似）"""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    
    # 根據 RGB 值混合基底光譜
    if r <= g and r <= b:  # Cyan dominant
        spectrum = mix(basis_spectra['white'], basis_spectra['cyan'], ...)
    # ... 其他情況
    
    return spectrum  # (H, W, 31)
```

#### 膠片光譜敏感度曲線
```python
@dataclass
class EmulsionLayer:
    # ... 現有參數 ...
    
    # 光譜敏感度曲線（31 個波長點）
    spectral_sensitivity: np.ndarray = field(default_factory=lambda: 
        # 預設：高斯形狀（峰值依層而定）
        # Red layer: 峰值 650nm
        # Green layer: 峰值 550nm
        # Blue layer: 峰值 450nm
    )
```

#### 預期效果
- **色彩準確度大幅提升**（+40%）
- 可模擬「色溫影響」（鎢絲燈 vs 日光）
- 可模擬「濾鏡效果」（黃濾鏡、紅濾鏡）
- Bloom 的「顏色分離」更真實

#### 實作檔案
- `film_models.py`: 新增 `spectral_sensitivity` 欄位
- `Phos_0.3.0.py`: 新增 `spectral_response_full()`
- `color_utils.py`: 新建（RGB ↔ Spectrum ↔ XYZ 轉換）
- `tests/test_spectral_model.py`: 新增測試

#### 驗收標準
- [ ] RGB → Spectrum → RGB 往返誤差 < 5%
- [ ] 膠片光譜曲線符合廠商規格（Kodak/Fuji）
- [ ] 色溫偏移可驗證（D50 vs D65）

---

### Phase 5: Mie 散射查表 ⭐⭐⭐
**ROI**: 中（+100% 時間，+30% 散射真實感）

#### 當前問題
```python
# 經驗 PSF（無物理依據）
PSF_gaussian = exp(-r² / 2σ²)
```

#### 改進方案
```python
# 預計算 Mie 散射查表（離線生成）
def generate_mie_psf_lookup_table():
    """生成 Mie 散射 PSF 查表"""
    
    table = {}
    
    # 參數範圍
    wavelengths = [450, 550, 650]  # nm
    grain_diameters = np.linspace(0.5, 3.0, 10)  # μm
    n_AgBr = 2.253  # 銀鹽折射率
    
    for λ in wavelengths:
        for d in grain_diameters:
            # Mie 理論計算（使用 PyMieScatt）
            theta = np.linspace(0, np.pi, 180)  # 散射角
            S1, S2 = Mie_S1_S2(m=n_AgBr, 
                               wavelength=λ, 
                               diameter=d, 
                               angles=theta)
            
            # 散射相位函數
            phase_function = (|S1|² + |S2|²) / 2
            
            # 轉換為 2D PSF（徑向對稱）
            psf_2d = angular_to_spatial_psf(phase_function, theta)
            
            # 儲存
            table[(λ, d)] = psf_2d
    
    # 儲存為 NPZ 檔案
    np.savez_compressed('mie_psf_lookup.npz', **table)
```

#### 查表使用
```python
def get_mie_psf(wavelength, grain_diameter):
    """從查表取得 Mie PSF"""
    
    # 載入預計算表格（首次載入後快取）
    table = load_mie_lookup_table()
    
    # 線性插值
    psf = interpolate_2d(table, wavelength, grain_diameter)
    
    return psf
```

#### 預期效果
- 散射的「角度分布」更真實（前向 > 側向 > 後向）
- 長距離散射尾部更準確
- 依銀鹽粒徑自動調整 PSF

#### 實作檔案
- `scripts/generate_mie_lookup.py`: 離線生成腳本
- `data/mie_psf_lookup.npz`: 查表檔案（~50MB）
- `Phos_0.3.0.py`: 修改 `apply_bloom_conserved()`
- `requirements.txt`: 新增 `PyMieScatt==1.8.1`

#### 驗收標準
- [ ] 查表載入時間 < 100ms
- [ ] PSF 插值誤差 < 2%
- [ ] 視覺測試：散射尾部更長、更自然

---

### Phase 6: 整合測試與效能優化 ⭐⭐⭐⭐⭐
**ROI**: 必要（確保穩定性與效能目標）

#### 測試覆蓋
```python
# 新增測試檔案
tests/
├── test_wavelength_bloom.py         # 波長依賴散射（8 tests）
├── test_halation.py                 # Halation 獨立（6 tests）
├── test_grain_clustering.py         # 顆粒叢集（5 tests）
├── test_spectral_model.py           # 光譜模型（10 tests）
├── test_mie_scattering.py           # Mie 散射（4 tests）
├── test_medium_physics_integration.py  # 整合測試（8 tests）
└── test_performance_medium.py       # 效能基準（3 tests）

總計：+44 tests（當前 26 → 70）
```

#### 效能優化策略

##### 1. 並行卷積（GPU/多核心）
```python
# CPU 多核心
from concurrent.futures import ThreadPoolExecutor

def parallel_convolution(layers, psfs):
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(lambda args: cv2.filter2D(*args), 
                              zip(layers, psfs))
    return list(results)
```

##### 2. PSF 快取
```python
@lru_cache(maxsize=128)
def get_cached_psf(wavelength, radius, psf_type):
    """快取常用 PSF，避免重複計算"""
    return create_psf(wavelength, radius, psf_type)
```

##### 3. 降採樣策略
```python
def adaptive_resolution_processing(image, film):
    """大圖先降採樣處理，再升採樣"""
    
    if max(image.shape) > 3000:
        # 降至 2000px 處理（4x 加速）
        scale = 2000 / max(image.shape)
        small = cv2.resize(image, None, fx=scale, fy=scale)
        result_small = process_image(small, film)
        result = cv2.resize(result_small, image.shape[:2][::-1])
    else:
        result = process_image(image, film)
    
    return result
```

#### 效能目標驗證
```python
# tests/test_performance_medium.py

def test_performance_benchmark():
    """效能基準測試"""
    
    sizes = [
        (1000, 1000),
        (2000, 3000),
        (4000, 6000)
    ]
    
    targets = {
        (1000, 1000): 2.0,   # < 2s
        (2000, 3000): 10.0,  # < 10s ← 關鍵目標
        (4000, 6000): 40.0   # < 40s
    }
    
    for size in sizes:
        image = np.random.rand(*size, 3) * 255
        
        start = time.time()
        result = process_image_medium_physics(image, film)
        elapsed = time.time() - start
        
        assert elapsed < targets[size], \
            f"{size}: {elapsed:.2f}s > {targets[size]}s"
```

#### 驗收標準
- [ ] 所有 70 項測試通過
- [ ] 2000×3000 影像 < 10s
- [ ] 記憶體占用 < 4GB
- [ ] 無 NaN/Inf 錯誤

---

## 📊 專案時程規劃

### Week 1（3 天）
- ✅ Day 1: Phase 1（波長依賴散射）- 實作 + 測試
- ✅ Day 2: Phase 2（Halation 獨立）- 實作 + 測試
- ✅ Day 3: Phase 3（顆粒叢集）- 實作 + 測試

### Week 2（2 天）
- ✅ Day 4: Phase 4（光譜模型）- 實作 + 測試
- ✅ Day 5: Phase 5（Mie 散射）+ Phase 6（整合優化）

### 緩衝（可選）
- Day 6-7: Bug 修正、文檔更新、效能調校

---

## 🔧 技術棧與依賴

### 新增依賴
```bash
# requirements.txt
opensimplex==0.4.5         # Perlin/Simplex 噪聲（顆粒叢集）
PyMieScatt==1.8.1          # Mie 散射計算
colour-science==0.4.2      # 色彩科學（XYZ 轉換）
```

### 資料檔案
```
data/
├── mie_psf_lookup.npz          # Mie 散射 PSF 查表（50MB）
├── film_spectral_curves/       # 膠片光譜敏感度曲線
│   ├── kodak_portra_400.csv
│   ├── fuji_velvia_50.csv
│   └── ...
└── color_matching_functions/   # CIE 色彩匹配函數
    └── cie_1931_xyz.csv
```

---

## 📝 文檔更新

### 需更新文檔
1. `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md`
   - 新增「中等物理模式」章節
   - 更新差距分析（25% → 55%）
   
2. `PHYSICAL_MODE_GUIDE.md`
   - 新增 Halation 參數調整指南
   - 新增顆粒叢集參數說明
   
3. `README.md`
   - 更新功能列表
   - 新增「中等物理」模式介紹

4. 新建 `MEDIUM_PHYSICS_MODE_GUIDE.md`
   - 完整的中等物理模式使用指南
   - 參數調整範例
   - 與簡化模式的對比

---

## ⚠️ 風險與緩解

### 風險 1: 效能超標（> 10s）
**機率**: 中  
**影響**: 高  
**緩解**:
- 提前進行效能 profiling
- 準備降採樣策略
- GPU 加速備案（CuPy）

### 風險 2: 記憶體溢出（光譜模型 31 通道）
**機率**: 中  
**影響**: 高  
**緩解**:
- 分塊處理（Tile-based）
- 及時釋放中間結果
- 使用 float16（半精度）

### 風險 3: 色彩準確度難以驗證
**機率**: 低  
**影響**: 中  
**緩解**:
- 對比 ColorChecker 標準色卡
- 與商業軟體（VSCO, RNI）對比
- 使用者 A/B 測試

### 風險 4: 向後相容性破壞
**機率**: 低  
**影響**: 高  
**緩解**:
- 所有新功能預設關閉（opt-in）
- 保留 ARTISTIC 與 PHYSICAL 模式
- 新增 MEDIUM_PHYSICS 模式（獨立）

---

## ✅ 驗收檢查清單

### 功能驗收
- [ ] 波長依賴散射：藍色光暈可見
- [ ] Halation 獨立：雙層光暈可見
- [ ] 顆粒叢集：團塊感可見
- [ ] 光譜模型：色彩準確度提升（主觀）
- [ ] Mie 散射：散射尾部更長

### 技術驗收
- [ ] 能量守恆維持（< 0.01%）
- [ ] 所有 70 項測試通過
- [ ] 效能目標達成（< 10s）
- [ ] 記憶體占用 < 4GB
- [ ] 無 NaN/Inf/Warning

### 用戶驗收
- [ ] 與真實膠片掃描對比（視覺相似度 > 80%）
- [ ] 與商業軟體對比（不遜色）
- [ ] 社群反饋（Reddit r/analog, 攝影論壇）

---

## 🎯 下一步行動

### ✅ Phase 2 完成（2025-12-19）
- Halation 獨立建模實作完成
- Beer-Lambert 波長依賴實現
- 中等物理測試配置就緒
- 所有測試通過（能量守恆 0.0000% 誤差）

### 🚧 下一步：Phase 1 - 波長依賴散射

**優先級調整**（根據 Physicist 建議）:
```
原順序：Phase 1 → Phase 2 → ...
實際順序：Phase 2 ✅ → Phase 1 ⏳ → Phase 5 → Phase 4 → Phase 3 → Phase 6
```

**Phase 1 目標**: η(λ) 與 σ(λ) 解耦
- 能量權重：η(λ) ∝ λ^-3.5（Mie/Rayleigh 混合）
- PSF 寬度：σ(λ) ∝ (λ_ref/λ)^0.8
- 雙段核：K = ρ·G(σ) + (1-ρ)·E(κ)

**預估時間**: 1 天（8 小時）

**需要 Physicist sub-agent 協助**:
- 驗證波長指數（-3.5 vs -4）
- 審查 PSF 半徑標度（q=0.8）
- 提供雙段核混合比例 ρ 建議

**前置條件**:
- ✅ `WavelengthBloomParams` dataclass 已定義（film_models.py Line 117-147）
- ✅ Phase 2 能量守恆框架可復用
- ✅ 測試框架就緒（test_phase2_integration.py 作為模板）

---

**任務創建時間**: 2025-12-19 20:00  
**Phase 2 完成時間**: 2025-12-19 22:30  
**負責人**: Main Agent  
**當前狀態**: ✅ Phase 2 Complete | ⏳ Phase 1 Ready to Start
