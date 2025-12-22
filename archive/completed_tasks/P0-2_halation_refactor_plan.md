# P0-2: Halation 參數重構計畫（Beer-Lambert 一致性）

**Task ID**: TASK-007-P0-2  
**Priority**: 🔴 Critical  
**Physics Score Impact**: +0.8 → 7.8/10  
**Status**: In Progress  
**Created**: 2025-12-20  

---

## 📋 問題描述

### 當前實作問題（Physicist Assessment Line 189-219）

**1. 參數命名與含義不一致**
```python
# film_models.py Line 93-124
class HalationParams:
    transmittance_r: float = 0.7  # 宣稱「雙程往返」
    ah_absorption: float = 0.95   # 「吸收率」（非透過率！）
    backplate_reflectance: float = 0.3
```

**問題識別**：
- `transmittance_r/g/b` 宣稱包含 `T_e² · T_b² · T_AH²`（Line 102, 109）
- 但 `ah_absorption` 又作為獨立參數存在（Line 124, 401-403）
- 實作中（Line 1313）：`ah_factor = 1 - ah_absorption`（**違反 Beer-Lambert！**）

**2. 公式錯誤**
```python
# Phos_0.3.0.py Line 1313-1314
ah_factor = 1.0 - halation_params.ah_absorption  # ❌ 線性近似
total_factor = ah_factor * backplate_reflectance * transmittance
```

**Beer-Lambert 正確公式**：
```
T_AH(λ) = exp(-α_AH(λ) · L_AH)  # 指數衰減
f_h(λ) = [T_e(λ) · T_AH(λ) · T_b(λ)]² · R_bp  # 雙程往返
```

**當前錯誤**：使用線性 `T_AH ≈ 1 - α_AH`，僅在 `α_AH << 1` 時成立！

**3. 語義混淆**

| 參數名稱 | 當前含義 | 期望含義 | 量綱 |
|---------|---------|---------|-----|
| `transmittance_r` | `T_e² · T_b² · T_AH²`（未明確） | `T_e`（單程） | 無量綱 |
| `ah_absorption` | 吸收率 α（0-1） | `T_AH`（單程） | 無量綱 |
| `backplate_reflectance` | R_bp（正確） | R_bp（正確） | 無量綱 |

**4. 能量守恆風險**

當前實作（Line 1358-1361）：
```python
if total_energy_out > 1e-6:
    halation_layer = halation_layer * (total_energy_in / total_energy_out)
```

雖然有重標定，但若輸入公式錯誤（`ah_factor` 線性近似），可能導致：
- CineStill（`ah_absorption=0`）與 Portra（`ah_absorption=0.95`）的紅暈比例不符物理預期
- 能量分配偏差 2-10 倍（Physicist Assessment Line 198-199）

---

## 🎯 重構目標

### 目標 1：標準化參數命名（Beer-Lambert 一致）

**新 HalationParams 設計**：
```python
@dataclass
class HalationParams:
    """
    Halation（背層反射光暈）參數 - Beer-Lambert 一致版
    
    物理模型（雙程往返）：
        光路徑：乳劑 → 片基 → AH層 → 背板（反射）→ AH層 → 片基 → 乳劑
        
        f_h(λ) = [T_e(λ) · T_b(λ) · T_AH(λ)]² · R_bp
        
        其中：
        - T_e(λ) = exp(-α_e(λ) · L_e)  # 乳劑層單程透過率
        - T_b(λ) = exp(-α_b(λ) · L_b)  # 片基單程透過率
        - T_AH(λ) = exp(-α_AH(λ) · L_AH)  # AH層單程透過率
        - R_bp ∈ [0, 1]  # 背板反射率
        
    能量守恆：
        E_scattered = E_in · f_h(λ)
        E_out = E_in - E_scattered + PSF ⊗ E_scattered
        ∑E_out ≈ ∑E_in（誤差 < 0.05%）
    """
    enabled: bool = True
    
    # === 單程透過率（Single-pass transmittances）===
    # 使用者友好參數，已預設典型值
    emulsion_transmittance_r: float = 0.92   # T_e,r @ 650nm
    emulsion_transmittance_g: float = 0.87   # T_e,g @ 550nm
    emulsion_transmittance_b: float = 0.78   # T_e,b @ 450nm
    
    # 片基透過率（通常接近 1，TAC/PET 材質）
    base_transmittance: float = 0.98  # T_b（近似灰色）
    
    # Anti-Halation 層透過率
    ah_layer_transmittance_r: float = 0.30  # T_AH,r（強吸收紅光）
    ah_layer_transmittance_g: float = 0.10  # T_AH,g
    ah_layer_transmittance_b: float = 0.05  # T_AH,b
    
    # 背板反射率
    backplate_reflectance: float = 0.30  # R_bp（金屬壓片板）
    
    # === PSF 參數（長尾分布）===
    psf_radius: int = 100
    psf_type: str = "exponential"
    psf_decay_rate: float = 0.05
    
    # === 能量控制 ===
    energy_fraction: float = 0.05  # 全局縮放（藝術調整）
    
    # === 計算屬性（雙程往返）===
    @property
    def effective_halation_r(self) -> float:
        """紅光雙程 Halation 分數"""
        T_single = (self.emulsion_transmittance_r * 
                    self.base_transmittance * 
                    self.ah_layer_transmittance_r)
        return T_single ** 2 * self.backplate_reflectance
    
    @property
    def effective_halation_g(self) -> float:
        """綠光雙程 Halation 分數"""
        T_single = (self.emulsion_transmittance_g * 
                    self.base_transmittance * 
                    self.ah_layer_transmittance_g)
        return T_single ** 2 * self.backplate_reflectance
    
    @property
    def effective_halation_b(self) -> float:
        """藍光雙程 Halation 分數"""
        T_single = (self.emulsion_transmittance_b * 
                    self.base_transmittance * 
                    self.ah_layer_transmittance_b)
        return T_single ** 2 * self.backplate_reflectance
```

**關鍵改進**：
1. ✅ 全部參數使用「單程透過率」（0-1），符合 Beer-Lambert
2. ✅ 移除 `ah_absorption`（吸收率），改用 `ah_layer_transmittance_r/g/b`
3. ✅ 提供 `@property` 計算雙程有效分數（方便內部使用）
4. ✅ 保留 `energy_fraction` 全局縮放（藝術調整，向後相容）

### 目標 2：修正 apply_halation() 實作

**當前問題**（Line 1293-1314）：
```python
# ❌ 線性插值波長
if wavelength < 500:
    transmittance = halation_params.transmittance_b
elif wavelength < 600:
    transmittance = halation_params.transmittance_g
else:
    transmittance = halation_params.transmittance_r

# ❌ 線性近似 AH 層
ah_factor = 1.0 - halation_params.ah_absorption
total_factor = ah_factor * backplate_reflectance * transmittance
```

**新實作（Proposal）**：
```python
def apply_halation(
    lux: np.ndarray, 
    halation_params: HalationParams, 
    wavelength: float = 550.0
) -> np.ndarray:
    """
    應用 Halation（背層反射）效果 - Beer-Lambert 一致版
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        halation_params: HalationParams 對象
        wavelength: 當前通道的波長（nm）
        
    Returns:
        應用 Halation 後的光度數據（能量守恆）
    """
    if not halation_params.enabled:
        return lux
    
    # 1. 根據波長計算雙程有效分數
    # 使用線性插值（簡化實作）
    if wavelength <= 450:
        f_h = halation_params.effective_halation_b
    elif wavelength >= 650:
        f_h = halation_params.effective_halation_r
    else:
        # 450-650nm 線性插值
        if wavelength < 550:
            # 450-550: 藍→綠
            t = (wavelength - 450) / (550 - 450)
            f_h = (1 - t) * halation_params.effective_halation_b + \
                  t * halation_params.effective_halation_g
        else:
            # 550-650: 綠→紅
            t = (wavelength - 550) / (650 - 550)
            f_h = (1 - t) * halation_params.effective_halation_g + \
                  t * halation_params.effective_halation_r
    
    # 2. 提取高光能量（閾值 0.5）
    halation_threshold = 0.5
    highlights = np.maximum(lux - halation_threshold, 0)
    
    # 3. 應用雙程 Beer-Lambert 分數 + 藝術縮放
    halation_energy = highlights * f_h * halation_params.energy_fraction
    
    # 4. 應用長尾 PSF（保持當前實作）
    ksize = halation_params.psf_radius
    ksize = ksize if ksize % 2 == 1 else ksize + 1
    
    if halation_params.psf_type == "exponential":
        sigma_base = halation_params.psf_radius * halation_params.psf_decay_rate
        kernel_small = get_gaussian_kernel(sigma_base, ksize // 3)
        kernel_medium = get_gaussian_kernel(sigma_base * 2.0, ksize)
        kernel_large = get_gaussian_kernel(sigma_base * 4.0, ksize)
        
        halation_layer = (
            convolve_adaptive(halation_energy, kernel_small, method='spatial') * 0.5 +
            convolve_adaptive(halation_energy, kernel_medium, method='auto') * 0.3 +
            convolve_adaptive(halation_energy, kernel_large, method='fft') * 0.2
        )
    elif halation_params.psf_type == "lorentzian":
        sigma_long = halation_params.psf_radius * 0.3
        kernel = get_gaussian_kernel(sigma_long, ksize)
        halation_layer = convolve_adaptive(halation_energy, kernel, method='fft')
    else:
        sigma = halation_params.psf_radius * 0.15
        kernel = get_gaussian_kernel(sigma, ksize)
        halation_layer = convolve_adaptive(halation_energy, kernel, method='auto')
    
    # 5. 能量守恆正規化
    total_energy_in = np.sum(halation_energy)
    total_energy_out = np.sum(halation_layer)
    if total_energy_out > 1e-6:
        halation_layer = halation_layer * (total_energy_in / total_energy_out)
    
    # 6. 從原圖減去散射能量，加上散射後的光暈
    result = lux - halation_energy + halation_layer
    
    return np.clip(result, 0, 1)
```

**關鍵改進**：
1. ✅ 直接使用 `effective_halation_r/g/b` 屬性（已包含雙程公式）
2. ✅ 移除錯誤的線性近似 `ah_factor = 1 - ah_absorption`
3. ✅ 保持能量守恆邏輯（Line 4-5）
4. ✅ 保持 PSF 卷積邏輯不變（已驗證正確）

### 目標 3：向後相容的遷移策略

**問題**：現有膠片配置使用舊參數名稱，如何平滑遷移？

**方案 A：Deprecation Wrapper（推薦）**
```python
@dataclass
class HalationParams:
    # 新參數（Beer-Lambert 標準）
    emulsion_transmittance_r: float = 0.92
    emulsion_transmittance_g: float = 0.87
    emulsion_transmittance_b: float = 0.78
    base_transmittance: float = 0.98
    ah_layer_transmittance_r: float = 0.30
    ah_layer_transmittance_g: float = 0.10
    ah_layer_transmittance_b: float = 0.05
    backplate_reflectance: float = 0.30
    
    # 舊參數（向後相容，Deprecated）
    transmittance_r: Optional[float] = None
    transmittance_g: Optional[float] = None
    transmittance_b: Optional[float] = None
    ah_absorption: Optional[float] = None
    
    def __post_init__(self):
        """向後相容處理"""
        if self.transmittance_r is not None:
            # 偵測到舊參數，觸發警告並轉換
            warnings.warn(
                "HalationParams: 'transmittance_r/g/b' and 'ah_absorption' are deprecated. "
                "Please use 'emulsion_transmittance_*' and 'ah_layer_transmittance_*'. "
                "Automatic conversion applied (assuming old values = double-pass).",
                DeprecationWarning
            )
            # 假設舊值 = T_e² · T_b² · T_AH²（雙程）
            # 反推單程值（簡化：T_single = sqrt(T_double)）
            self.emulsion_transmittance_r = np.sqrt(self.transmittance_r / 0.98**2)  # 假設 T_b≈0.98
            # ... 類似處理 g, b
        
        if self.ah_absorption is not None:
            # 轉換吸收率 → 透過率（線性近似）
            warnings.warn(
                "HalationParams: 'ah_absorption' deprecated. Use 'ah_layer_transmittance_*'.",
                DeprecationWarning
            )
            # 簡化：T_AH ≈ 1 - α（保持舊行為）
            self.ah_layer_transmittance_r = 1.0 - self.ah_absorption
            self.ah_layer_transmittance_g = 1.0 - self.ah_absorption
            self.ah_layer_transmittance_b = 1.0 - self.ah_absorption
```

**方案 B：雙版本並存（Phase Transition）**
- 創建 `HalationParamsV2`（新標準）
- 保留 `HalationParams`（舊版本，標記 Deprecated）
- 在下一個大版本（v0.4.0）移除舊版

**推薦**：方案 A（單一類 + `__post_init__` 轉換），因為：
- 保持 API 簡潔
- 自動遷移使用者配置
- 測試覆蓋更容易

---

## 📐 物理驗證目標

### 1. 量綱一致性檢查

```python
def test_halation_dimensional_consistency():
    """驗證所有參數為無量綱（0-1 範圍）"""
    params = HalationParams()
    
    # 單程透過率：0-1
    assert 0 <= params.emulsion_transmittance_r <= 1
    assert 0 <= params.ah_layer_transmittance_r <= 1
    assert 0 <= params.base_transmittance <= 1
    
    # 反射率：0-1
    assert 0 <= params.backplate_reflectance <= 1
    
    # 雙程有效分數：0-1（自動滿足，因為乘積）
    assert 0 <= params.effective_halation_r <= 1
```

### 2. 能量守恆測試（全局 + 局部）

```python
def test_halation_energy_conservation():
    """驗證 Halation 能量守恆（誤差 < 0.05%）"""
    # 測試圖像：黑底白點
    img = np.zeros((256, 256))
    img[128, 128] = 1.0
    
    params = HalationParams(enabled=True, energy_fraction=0.05)
    result = apply_halation(img, params, wavelength=550)
    
    # 全局能量守恆
    energy_in = np.sum(img)
    energy_out = np.sum(result)
    global_error = abs(energy_out - energy_in) / energy_in
    assert global_error < 0.0005, f"Global energy error: {global_error:.6f}"
    
    # 局部窗口（64x64）
    window = result[96:160, 96:160]
    window_in = img[96:160, 96:160]
    local_error = abs(np.sum(window) - np.sum(window_in)) / np.sum(window_in)
    assert local_error < 0.001, f"Local energy error: {local_error:.6f}"
```

### 3. CineStill vs Portra 對比測試

```python
def test_cinestill_vs_portra_halation():
    """驗證 CineStill（無 AH 層）紅暈比 Portra 強 ~10 倍"""
    img = np.zeros((128, 128))
    img[64, 64] = 1.0
    
    # Portra 400：標準 AH 層（T_AH ~ 0.1）
    params_portra = HalationParams(
        ah_layer_transmittance_r=0.30,
        ah_layer_transmittance_g=0.10,
        ah_layer_transmittance_b=0.05,
        energy_fraction=0.03
    )
    
    # CineStill 800T：無 AH 層（T_AH ~ 1.0）
    params_cinestill = HalationParams(
        ah_layer_transmittance_r=1.0,  # 100% 穿透
        ah_layer_transmittance_g=1.0,
        ah_layer_transmittance_b=1.0,
        energy_fraction=0.15  # 更高能量比例
    )
    
    result_portra = apply_halation(img, params_portra, 650)
    result_cinestill = apply_halation(img, params_cinestill, 650)
    
    # 比較外圈紅暈強度（距中心 30-50 px）
    halo_portra = np.mean(result_portra[40:45, 64])
    halo_cinestill = np.mean(result_cinestill[40:45, 64])
    
    ratio = halo_cinestill / (halo_portra + 1e-9)
    assert 8 < ratio < 15, f"CineStill/Portra ratio: {ratio:.2f} (expected 8-15)"
```

### 4. 波長依賴驗證（藍暈外圈 > 紅暈核心）

```python
def test_wavelength_dependent_halo():
    """驗證白光點產生藍色外圈 + 黃色核心"""
    img = np.zeros((128, 128))
    img[64, 64] = 1.0
    
    params = HalationParams(
        emulsion_transmittance_r=0.92,
        emulsion_transmittance_g=0.87,
        emulsion_transmittance_b=0.78,
        ah_layer_transmittance_r=0.30,
        ah_layer_transmittance_g=0.10,
        ah_layer_transmittance_b=0.05
    )
    
    # RGB 三通道分別處理
    result_r = apply_halation(img, params, 650)
    result_g = apply_halation(img, params, 550)
    result_b = apply_halation(img, params, 450)
    
    # 檢查外圈（30-40 px）：藍光應更分散
    halo_r_outer = np.mean(result_r[40:45, 64])
    halo_b_outer = np.mean(result_b[40:45, 64])
    assert halo_b_outer > halo_r_outer, "Blue halo should be stronger at outer ring"
    
    # 檢查核心（0-10 px）：紅光應更集中
    halo_r_core = np.mean(result_r[62:67, 64])
    halo_b_core = np.mean(result_b[62:67, 64])
    assert halo_r_core > halo_b_core, "Red halo should be stronger at core"
```

---

## 🛠️ 實作計畫（Stepwise Execution）

### Step 1: 更新 `HalationParams` 類（film_models.py）

**檔案**：`/Users/latteine/Documents/coding/Phos/film_models.py`  
**修改範圍**：Line 93-151  

**操作**：
1. 新增參數：
   - `emulsion_transmittance_r/g/b`
   - `base_transmittance`
   - `ah_layer_transmittance_r/g/b`
2. 保留舊參數（標記 `Optional`，Deprecated）
3. 新增 `__post_init__` 向後相容邏輯
4. 新增 `@property` 計算雙程有效分數

**預期結果**：
- `HalationParams()` 可直接使用（預設值）
- 舊配置自動觸發 `DeprecationWarning` 並轉換
- 新配置使用標準 Beer-Lambert 參數

### Step 2: 更新 `apply_halation()` 函數（Phos_0.3.0.py）

**檔案**：`/Users/latteine/Documents/coding/Phos/Phos_0.3.0.py`  
**修改範圍**：Line 1263-1367  

**操作**：
1. 移除 Line 1313 的 `ah_factor = 1 - ah_absorption`
2. 改用 `halation_params.effective_halation_r/g/b`
3. 更新波長插值邏輯（450-550-650 三點線性）
4. 保持能量守恆與 PSF 卷積邏輯不變

**預期結果**：
- `apply_halation()` 直接調用 `@property`
- 物理公式正確（雙程 Beer-Lambert）
- 能量守恆維持 < 0.05%

### Step 3: 遷移膠片配置（film_models.py）

**檔案**：`/Users/latteine/Documents/coding/Phos/film_models.py`  
**修改範圍**：Line 355-460（`create_default_medium_physics_params`）  

**操作**：
1. 更新 `halation_params` 創建邏輯：
   ```python
   # 舊版（將移除）
   halation_params = HalationParams(
       transmittance_r=0.7,
       ah_absorption=0.95
   )
   
   # 新版（Beer-Lambert 標準）
   halation_params = HalationParams(
       emulsion_transmittance_r=0.92,
       emulsion_transmittance_g=0.87,
       emulsion_transmittance_b=0.78,
       ah_layer_transmittance_r=0.30,
       ah_layer_transmittance_g=0.10,
       ah_layer_transmittance_b=0.05,
       base_transmittance=0.98,
       backplate_reflectance=0.30,
       energy_fraction=0.03
   )
   ```
2. 為 CineStill 配置 `ah_layer_transmittance_* = 1.0`（無吸收）

**預期結果**：
- Portra/Ektachrome：標準紅暈（T_AH ~ 0.1-0.3）
- CineStill：極端紅暈（T_AH ~ 1.0）
- Velvia/Gold：調整值（中等）

### Step 4: 新增測試用例（tests/test_halation.py）

**檔案**：`/Users/latteine/Documents/coding/Phos/tests/test_halation.py`  
**操作**：新增測試（已存在則補充）  

**測試清單**：
1. `test_halation_dimensional_consistency()`
2. `test_halation_energy_conservation()`
3. `test_cinestill_vs_portra_halation()`
4. `test_wavelength_dependent_halo()`
5. `test_backward_compatibility()` - 驗證舊參數轉換

**預期結果**：
- 全部測試通過
- 覆蓋率 > 90%（Halation 分支）

### Step 5: 執行端到端驗證（E2E）

**腳本**：創建 `scripts/validate_p0_2_halation.py`  

**驗證項目**：
1. 載入 CineStill 800T vs Portra 400
2. 處理測試圖像（白點光源）
3. 輸出對比圖：
   - Portra: 適中紅暈
   - CineStill: 極端紅暈（~10 倍）
4. 能量守恆檢查（全局 + 局部）
5. 波長依賴檢查（藍外圈 vs 紅核心）

**成功指標**：
- 能量誤差 < 0.05%
- CineStill/Portra 紅暈比例 8-15 倍
- 視覺驗證：藍色外圈 + 黃色核心

### Step 6: 更新文檔與決策日誌

**操作**：
1. 更新 `context/decisions_log.md`：
   - 記錄 P0-2 重構動機
   - Beer-Lambert 公式推導
   - 向後相容策略
2. 更新 `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md`：
   - Section: Halation（更新公式）
3. 更新 `PHYSICAL_MODE_GUIDE.md`：
   - 新參數使用指南

---

## 📊 成功指標（Definition of Done）

### 必須滿足（Mandatory）

- [ ] `HalationParams` 類符合 Beer-Lambert 標準（單程透過率）
- [ ] `apply_halation()` 使用正確的雙程公式
- [ ] 所有單元測試通過（能量守恆 < 0.05%）
- [ ] CineStill vs Portra 紅暈比例 8-15 倍
- [ ] 舊配置自動轉換（向後相容）

### 應該滿足（Should）

- [ ] 端到端視覺驗證通過（藍外圈 + 黃核心）
- [ ] 文檔更新完整（技術文檔 + 決策日誌）
- [ ] 測試覆蓋率 > 90%（Halation 分支）

### 可選滿足（Optional）

- [ ] 效能優化（FFT 卷積保持不變，已優化）
- [ ] 進階參數：支援完整 Beer-Lambert（α, L）而非僅 T
- [ ] 實驗性：支援波長連續插值（非僅 RGB 三點）

---

## ⚠️ 風險與緩解

### 風險 1：向後相容性破壞

**風險**：使用者舊配置無法載入  
**緩解**：`__post_init__` 自動轉換 + `DeprecationWarning`  
**驗證**：`test_backward_compatibility()`  

### 風險 2：能量守恆退化

**風險**：新公式導致能量誤差增大  
**緩解**：保持 Line 1358-1361 的能量重標定邏輯  
**驗證**：`test_halation_energy_conservation()`（全局 + 局部）  

### 風險 3：視覺效果退化

**風險**：使用者覺得新版紅暈「太弱」或「太強」  
**緩解**：保留 `energy_fraction` 全局縮放（藝術調整）  
**驗證**：端到端視覺對比（CineStill 必須極端）  

### 風險 4：效能下降

**風險**：新插值邏輯增加計算量  
**緩解**：線性插值（O(1)），PSF 卷積保持 FFT 優化  
**驗證**：`test_performance.py` benchmark（應無明顯退化）  

---

## 📅 時間估計

| 步驟 | 預估時間 | 依賴 |
|-----|---------|-----|
| Step 1: 更新 `HalationParams` | 30 min | - |
| Step 2: 更新 `apply_halation()` | 20 min | Step 1 |
| Step 3: 遷移膠片配置 | 20 min | Step 1 |
| Step 4: 新增測試用例 | 40 min | Step 1-3 |
| Step 5: E2E 驗證 | 30 min | Step 1-4 |
| Step 6: 文檔更新 | 20 min | Step 5 |
| **總計** | **2.5 小時** | - |

---

## 🔗 參考資料

1. **Physicist Assessment**:  
   `/Users/latteine/Documents/coding/Phos/tasks/TASK-007-physics-enhancement/physicist_assessment.md`  
   Line 189-219（P0-2 問題描述）

2. **Beer-Lambert 理論**:  
   - 透過率公式：T(λ) = exp(-α(λ) · L)
   - 雙程往返：T_roundtrip = T²
   - 參考：[Wikipedia: Beer-Lambert Law](https://en.wikipedia.org/wiki/Beer%E2%80%93Lambert_law)

3. **當前實作**:  
   - `film_models.py` Line 93-151（HalationParams 類）
   - `Phos_0.3.0.py` Line 1263-1367（apply_halation 函數）
   - `film_models.py` Line 355-428（膠片配置工廠）

4. **相關測試**:  
   - `tests/test_halation.py`（現有基本測試）
   - `tests/test_energy_conservation.py`（能量守恆框架）

---

## ✅ 下一步

**立即行動**：開始 Step 1（更新 `HalationParams` 類）

**指令**：
```bash
cd /Users/latteine/Documents/coding/Phos
# 備份當前版本
cp film_models.py film_models.py.backup_pre_p0_2

# 開始實作（主 Agent 親自修改）
# （待主 Agent 確認後執行）
```

**驗收標準**：完成 Step 1 後，`HalationParams()` 可正常實例化，並通過量綱一致性測試。

---

**End of Plan**
