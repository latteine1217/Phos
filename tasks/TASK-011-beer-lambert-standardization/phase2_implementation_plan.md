# TASK-011 Phase 2: 代碼重構實作計畫

**創建時間**: 2025-12-24 07:30  
**負責**: Main Agent  
**預估時間**: 4 hours  
**Physics Gate**: ✅ PASSED (conditional)

---

## §1 實作範圍總覽

### 1.1 目標

基於 Physicist Review (§3, §5) 的建議，完成以下重構：

1. **文檔強化**：明確 `HalationParams` 的物理意義與參數範圍
2. **計算邏輯標準化**：確保 `apply_halation()` 使用標準化簽名
3. **測試擴充**：新增雙程路徑與 CineStill/Portra 對比測試
4. **向後相容維護**：保留 Deprecated 參數映射並強化警告

### 1.2 不變原則

- ✅ **保留現有參數結構**（emulsion_transmittance_*, ah_layer_transmittance_*, 等）
- ✅ **保留 __post_init__ 向後相容邏輯**
- ✅ **不改變計算公式**（f_h = [T_e·T_b·T_AH]²·R_bp）
- ⚠️ **不修改膠片配置數值**（留給 Phase 4 校準）

### 1.3 影響檔案

**主要修改**：
- `film_models.py` (HalationParams docstring 強化)
- `Phos.py` (apply_halation 文檔更新)
- `tests/test_p0_2_halation_beer_lambert.py` (新增測試)

**不修改**：
- `phos_core.py` (無 Halation 相關代碼)
- 膠片配置 (22 個 FilmProfile)

---

## §2 文檔強化

### 2.1 film_models.py - HalationParams Docstring

**修改位置**: Line 102-128

**新增內容**：

```python
@dataclass
class HalationParams:
    """
    Halation（背層反射光暈）參數 - Beer-Lambert 一致版（v0.3.2, P0-2 重構, P1-4 標準化）
    
    物理機制：
        光穿透乳劑層與片基，到達背層或相機背板反射後回到乳劑，產生大範圍光暈。
        與 Bloom（乳劑內前向散射）分離建模。
    
    Beer-Lambert 雙程往返模型：
        光路徑：乳劑 → 片基 → AH層 → 背板（反射）→ AH層 → 片基 → 乳劑
        
        f_h(λ) = [T_e(λ) · T_b(λ) · T_AH(λ)]² · R_bp
        
        其中（單程透過率）：
        - T_e(λ) = exp(-α_e(λ) · L_e)  # 乳劑層單程透過率
        - T_b(λ) = exp(-α_b(λ) · L_b)  # 片基單程透過率
        - T_AH(λ) = exp(-α_AH(λ) · L_AH)  # AH層單程透過率
        - R_bp ∈ [0, 1]  # 背板反射率
    
    參數範圍（物理合理區間）：
        - emulsion_transmittance_r/g/b: 0.6–0.98（彩色乳劑）
        - base_transmittance: 0.95–0.995（TAC/PET 基材）
        - ah_layer_transmittance_r/g/b:
            · 有 AH（Portra, Velvia）: 0.02–0.35
            · 無 AH（CineStill 800T）: ≈1.0
        - backplate_reflectance: 0.05–0.50（黑絨布至金屬背板）
        - energy_fraction: 0.02–0.10（藝術縮放，非物理路徑參數）
    
    真實案例參考：
        - CineStill 800T（無 AH）: ah_layer_transmittance_r/g/b ≈ 1.0
          → f_h,red ≈ 0.24（24%）→ 強烈紅色光暈
        
        - Kodak Portra 400（有 AH）: ah_layer_transmittance_r/g/b ≈ 0.30/0.10/0.05
          → f_h,red ≈ 0.022（2.2%）→ Halation 幾乎不可見
    
    能量守恆：
        E_scattered = E_in · f_h(λ)
        E_out = E_in - E_scattered + PSF ⊗ E_scattered
        ∑E_out ≈ ∑E_in（誤差 < 0.05%）
    
    向後相容：
        舊參數（transmittance_r/g/b, ah_absorption）將自動轉換為新格式。
        詳見 __post_init__ 實作。
    
    參考文獻：
        - Beer-Lambert Law: T(λ) = exp(-α(λ)·L)
        - Bohren & Huffman (1983). Absorption and Scattering of Light by Small Particles.
        - Hunt, R. W. G. (2004). The Reproduction of Colour, 6th ed., Ch. 18.
        - Decision #029: TASK-011 Beer-Lambert 參數標準化
    """
    enabled: bool = True
    # ... (保持現有欄位定義不變)
```

**驗收**：
- ✅ 包含完整光路圖描述
- ✅ 包含參數範圍（Physicist Review §3）
- ✅ 包含真實案例（CineStill vs Portra）
- ✅ 包含參考文獻

---

### 2.2 Phos.py - apply_halation Docstring

**修改位置**: Line 1483-1508

**強化內容**：

```python
def apply_halation(lux: np.ndarray, halation_params, wavelength: float = 550.0) -> np.ndarray:
    """
    應用 Halation（背層反射）效果 - Beer-Lambert 一致版（P0-2 重構, P1-4 標準化）
    
    物理機制：
    1. 光穿透乳劑層與片基
    2. 通過/被 Anti-Halation 層吸收
    3. 到達背板反射
    4. 往返路徑產生大範圍光暈
    
    遵循 Beer-Lambert 定律（雙程往返）：
    - 單程透過率：T(λ) = exp(-α(λ)·L)
    - 雙程有效分數：f_h(λ) = [T_e(λ) · T_b(λ) · T_AH(λ)]² · R_bp
    
    計算流程：
    1. 根據 wavelength 插值計算 f_h(λ)（使用 effective_halation_r/g/b）
    2. 提取高光（threshold=0.5）
    3. 計算散射能量：E_scatter = highlights × f_h × energy_fraction
    4. 應用長尾 PSF（指數/Lorentzian/高斯）
    5. 能量守恆正規化
    6. 返回：lux - E_scatter + PSF(E_scatter)
    
    與 Bloom 的區別：
    - Bloom: 短距離（20-30 px），高斯核，乳劑內散射
    - Halation: 長距離（100-200 px），指數拖尾，背層反射
    
    Args:
        lux: 光度通道數據 (0-1 範圍)
        halation_params: HalationParams 對象（含單程透過率參數）
        wavelength: 當前通道的波長（nm），用於波長依賴插值
            - 450nm: 藍光（使用 effective_halation_b）
            - 550nm: 綠光（使用 effective_halation_g）
            - 650nm: 紅光（使用 effective_halation_r）
            - 其他：線性插值
        
    Returns:
        應用 Halation 後的光度數據（能量守恆，誤差 < 0.05%）
    
    能量守恆驗證：
        見 tests/test_p0_2_halation_beer_lambert.py:
        - test_halation_energy_conservation_global
        - test_halation_energy_conservation_local_window
    
    真實案例驗證：
        - CineStill 800T: f_h,red ≈ 0.24 → 強烈紅暈
        - Portra 400: f_h,red ≈ 0.022 → 幾乎無暈
        見 test_cinestill_vs_portra_red_halo_ratio
    
    Note:
        energy_fraction 為藝術縮放參數，與物理 f_h(λ) 分離，
        用於控制視覺效果強度（典型值 0.02-0.10）。
    """
    # ... (保持現有實作不變)
```

**驗收**：
- ✅ 明確計算流程（6 步驟）
- ✅ 明確參數物理意義
- ✅ 指向測試驗證
- ✅ 區分物理參數與藝術縮放

---

## §3 測試擴充

### 3.1 新增測試案例

**檔案**: `tests/test_p0_2_halation_beer_lambert.py`

**新增測試類別**: `TestDoublePassFormula`

```python
class TestDoublePassFormula:
    """雙程路徑公式驗證（Physicist Review §2）"""
    
    def test_double_pass_formula_manual_calculation(self):
        """測試雙程公式：f_h = [T_e·T_b·T_AH]²·R_bp（與手算對比）"""
        # 測試案例：Portra 400 參數
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.92,
            emulsion_transmittance_g=0.87,
            emulsion_transmittance_b=0.78,
            base_transmittance=0.98,
            ah_layer_transmittance_r=0.30,
            ah_layer_transmittance_g=0.10,
            ah_layer_transmittance_b=0.05,
            backplate_reflectance=0.30
        )
        
        # 手算期望值（Physicist Review §2 案例）
        T_single_r = 0.92 * 0.98 * 0.30  # = 0.27048
        f_h_expected_r = (T_single_r ** 2) * 0.30  # = 0.02194
        
        T_single_g = 0.87 * 0.98 * 0.10  # = 0.08526
        f_h_expected_g = (T_single_g ** 2) * 0.30  # = 0.00218
        
        T_single_b = 0.78 * 0.98 * 0.05  # = 0.03822
        f_h_expected_b = (T_single_b ** 2) * 0.30  # = 0.000438
        
        # 程式計算值
        f_h_actual_r = params.effective_halation_r
        f_h_actual_g = params.effective_halation_g
        f_h_actual_b = params.effective_halation_b
        
        # 驗證（允許 1e-6 浮點誤差）
        assert abs(f_h_actual_r - f_h_expected_r) < 1e-6, \
            f"Red: expected {f_h_expected_r:.6f}, got {f_h_actual_r:.6f}"
        assert abs(f_h_actual_g - f_h_expected_g) < 1e-6, \
            f"Green: expected {f_h_expected_g:.6f}, got {f_h_actual_g:.6f}"
        assert abs(f_h_actual_b - f_h_expected_b) < 1e-6, \
            f"Blue: expected {f_h_expected_b:.6f}, got {f_h_actual_b:.6f}"
    
    def test_cinestill_no_ah_layer(self):
        """測試 CineStill 800T（無 AH 層，T_AH=1）"""
        params = HalationParams(
            enabled=True,
            emulsion_transmittance_r=0.93,
            emulsion_transmittance_g=0.88,
            emulsion_transmittance_b=0.80,
            base_transmittance=0.98,
            ah_layer_transmittance_r=1.0,  # 無 AH
            ah_layer_transmittance_g=1.0,
            ah_layer_transmittance_b=1.0,
            backplate_reflectance=0.30
        )
        
        # 期望：f_h = [T_e·T_b]²·R_bp
        T_single_r = 0.93 * 0.98 * 1.0  # = 0.9114
        f_h_expected_r = (T_single_r ** 2) * 0.30  # ≈ 0.249
        
        f_h_actual_r = params.effective_halation_r
        
        assert abs(f_h_actual_r - f_h_expected_r) < 1e-6
        assert f_h_actual_r > 0.15, \
            f"CineStill red halation too weak: {f_h_actual_r:.3f} (expected > 0.15)"
    
    def test_no_backplate_reflection(self):
        """測試邊界條件：R_bp=0（黑背板，無 Halation）"""
        params = HalationParams(
            enabled=True,
            backplate_reflectance=0.0  # 黑背板
        )
        
        assert params.effective_halation_r == 0.0
        assert params.effective_halation_g == 0.0
        assert params.effective_halation_b == 0.0
    
    def test_parameter_range_validation(self):
        """測試參數範圍合法性（0 < T ≤ 1, 0 ≤ R ≤ 1）"""
        # 合法範圍
        params_valid = HalationParams(
            emulsion_transmittance_r=0.6,  # 下限
            base_transmittance=0.995,      # 上限
            ah_layer_transmittance_r=0.02, # 下限
            backplate_reflectance=0.5      # 中間值
        )
        assert 0.0 < params_valid.effective_halation_r <= 1.0
        
        # 邊界測試：T_AH=1（CineStill）
        params_no_ah = HalationParams(
            ah_layer_transmittance_r=1.0,
            ah_layer_transmittance_g=1.0,
            ah_layer_transmittance_b=1.0
        )
        assert params_no_ah.effective_halation_r > 0.0
```

### 3.2 強化現有測試

**修改**: `TestCineStillVsPortra.test_cinestill_vs_portra_red_halo_ratio`

**新增驗收標準**：
- ✅ 比例差異 > 5× (原 8-15×)
- ✅ CineStill f_h,red > 0.15（Physicist Review §4）
- ✅ Portra f_h,red < 0.05

```python
def test_cinestill_vs_portra_red_halo_ratio(self):
    """測試 CineStill vs Portra 紅暈比例（應 > 5× 差異）"""
    # CineStill 800T（無 AH）
    cinestill = HalationParams(
        enabled=True,
        emulsion_transmittance_r=0.93,
        ah_layer_transmittance_r=1.0,  # 無 AH
        ah_layer_transmittance_g=1.0,
        ah_layer_transmittance_b=1.0,
        backplate_reflectance=0.35
    )
    
    # Portra 400（有 AH）
    portra = HalationParams(
        enabled=True,
        emulsion_transmittance_r=0.92,
        ah_layer_transmittance_r=0.30,  # 有 AH
        ah_layer_transmittance_g=0.10,
        ah_layer_transmittance_b=0.05,
        backplate_reflectance=0.30
    )
    
    f_h_cinestill = cinestill.effective_halation_r
    f_h_portra = portra.effective_halation_r
    
    ratio = f_h_cinestill / (f_h_portra + 1e-9)
    
    # Physicist Review 驗收標準
    assert f_h_cinestill > 0.15, \
        f"CineStill red halation too weak: {f_h_cinestill:.3f} (expected > 0.15)"
    assert f_h_portra < 0.05, \
        f"Portra red halation too strong: {f_h_portra:.3f} (expected < 0.05)"
    assert ratio > 5.0, \
        f"CineStill/Portra ratio too small: {ratio:.1f}× (expected > 5×)"
```

---

## §4 向後相容維護

### 4.1 強化 Deprecation 警告

**修改位置**: `film_models.py` Line 168-213

**現有實作**: ✅ 已完整（保持不變）

**驗證點**：
- ✅ 舊參數自動映射邏輯正確
- ✅ 警告訊息明確（移除版本、轉換假設）
- ✅ stacklevel=2（指向調用點）

**新增文檔**（在 __post_init__ 前註解）：

```python
    # === 向後相容參數（Deprecated, 將在 v0.4.0 移除）===
    # 
    # 舊參數映射邏輯（Decision #029, P1-4）：
    # 
    # 1. transmittance_r/g/b（舊版「雙程」宣稱，但不含 AH）
    #    假設：transmittance = T_e² · T_b²（不含 T_AH）
    #    反推：T_e ≈ sqrt(transmittance / T_b²)
    #    風險：此假設僅對舊配置成立，新配置應直接使用單程參數
    # 
    # 2. ah_absorption（舊版線性近似）
    #    假設：T_AH ≈ 1 - α（線性近似，僅 α≪1 成立）
    #    風險：AH 層強吸收時不準確（如 Portra 藍光 α≈0.95）
    #    正確：應使用 T_AH = exp(-α·L)（Beer-Lambert）
    # 
    # 遷移指南：見 tasks/TASK-011-beer-lambert-standardization/
    # 
    transmittance_r: Optional[float] = None  # Deprecated
    transmittance_g: Optional[float] = None  # Deprecated
    transmittance_b: Optional[float] = None  # Deprecated
    ah_absorption: Optional[float] = None    # Deprecated
```

---

## §5 實作時程

### 5.1 時間分配

| 任務 | 預估時間 | 時間盒上限 |
|------|---------|-----------|
| §2 文檔強化 | 1h | 1.5h |
| §3 測試擴充 | 2h | 3h |
| §4 向後相容維護 | 0.5h | 1h |
| 測試執行與調整 | 0.5h | 1h |
| **總計** | **4h** | **6.5h** |

### 5.2 執行順序

1. **Step 1** (30 min): 更新 `film_models.py` HalationParams docstring
2. **Step 2** (30 min): 更新 `Phos.py` apply_halation docstring
3. **Step 3** (30 min): 新增向後相容文檔註解
4. **Step 4** (1.5h): 新增 `TestDoublePassFormula` 測試類別
5. **Step 5** (30 min): 強化 `TestCineStillVsPortra` 測試
6. **Step 6** (30 min): 執行測試並修正錯誤

---

## §6 驗收標準

### 6.1 代碼品質

- ✅ HalationParams docstring 包含完整光路圖、參數範圍、真實案例
- ✅ apply_halation docstring 包含計算流程、能量守恆說明
- ✅ 向後相容邏輯有完整文檔註解
- ✅ 所有修改符合專案 Code Style（中文註解、Type hints）

### 6.2 測試覆蓋率

- ✅ 新增測試：`test_double_pass_formula_manual_calculation`
- ✅ 新增測試：`test_cinestill_no_ah_layer`
- ✅ 新增測試：`test_no_backplate_reflection`
- ✅ 新增測試：`test_parameter_range_validation`
- ✅ 強化測試：`test_cinestill_vs_portra_red_halo_ratio`（新驗收標準）
- ✅ 所有現有測試保持通過（180+）

### 6.3 Physics Gate 條件達成

- ✅ 雙程公式驗證（手算 vs 程式，誤差 < 1e-6）
- ✅ CineStill vs Portra 對比（比例 > 5×）
- ✅ 參數範圍驗證（0 < T ≤ 1, 0 ≤ R ≤ 1）
- ✅ 邊界條件測試（R_bp=0, T_AH=1）

### 6.4 文檔完整性

- ✅ 參數物理意義明確（無歧義）
- ✅ 計算公式明確（Beer-Lambert 雙程）
- ✅ 真實案例明確（CineStill vs Portra）
- ✅ 向後相容策略明確（Deprecated 映射邏輯）

---

## §7 風險與緩解

| 風險 | 機率 | 影響 | 緩解策略 |
|------|------|------|---------|
| 新增測試失敗 | 🟡 中 | 🔴 高 | 先執行手算驗證，確保公式正確 |
| 浮點精度誤差 | 🟢 低 | 🟡 中 | 使用寬鬆閾值（1e-6） |
| Docstring 過長影響可讀性 | 🟢 低 | 🟢 低 | 結構化分段（物理機制/參數/案例） |
| 向後相容邏輯破壞舊配置 | 🟢 低 | 🔴 高 | 不修改 __post_init__ 實作 |

---

## §8 下一步（Phase 3）

Phase 2 完成後，進入 **Phase 3: 物理驗證測試**：

1. 執行所有 Halation 測試套件（180+）
2. 驗證 CineStill/Portra 比例差異（視覺+數值）
3. 能量守恆驗證（全局 + 局部）
4. 生成測試報告（通過率、覆蓋率、物理指標）

**Gate 條件**：
- ✅ 所有測試通過率 100%
- ✅ CineStill f_h,red > 0.15
- ✅ Portra f_h,red < 0.05
- ✅ 能量守恆誤差 < 0.05%

---

**創建**: 2025-12-24 07:30  
**狀態**: 📋 READY FOR IMPLEMENTATION  
**預計完成**: 2025-12-24 12:00
