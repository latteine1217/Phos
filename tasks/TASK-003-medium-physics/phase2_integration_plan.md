# Phase 2 整合測試計劃

**目標**: 驗證 Mie Bloom + Halation 同時運作的正確性與效能  
**前置條件**:
- ✅ Phase 1 (Mie 散射) 已實作並通過驗證
- ✅ Halation 已實作並通過驗證（2025-12-19）
- ⏳ 整合測試待創建

---

## 🎯 測試目標

### 1. **功能正確性**
- Bloom (Mie) 與 Halation 可以同時啟用
- 兩種效果的參數獨立可調
- 視覺上呈現「雙層光暈」（內層銳利 Bloom + 外層柔和 Halation）

### 2. **物理一致性**
- **能量守恆**: Bloom + Halation 總能量不超過輸入
- **波長依賴**: 兩種效果皆遵循各自的波長規則
  - Bloom: 藍光散射 > 紅光（λ^-3.5）
  - Halation: 紅光穿透 > 藍光（Beer-Lambert）

### 3. **效能指標**
- 2000×3000 影像處理時間 < 10s（目標）
- 記憶體占用 < 4GB
- 與單獨效果相比開銷 < 150%（1 + 1 = 2，非 2.5）

---

## 📋 測試案例設計

### Test 1: 參數載入與配置
```python
def test_mie_halation_parameters_loaded():
    """驗證 Mie + Halation 配置正確載入"""
    
    # Cinestill800T: Mie Bloom + 極端 Halation
    cs = get_film_profile("Cinestill800T")
    
    # Bloom 參數（Mie 模式）
    assert cs.bloom_params.mode == "physical"
    assert cs.bloom_params.energy_wavelength_exponent == 3.5
    assert cs.bloom_params.psf_width_exponent == 0.8
    
    # Halation 參數（無 AH 層）
    assert cs.halation_params.enabled == True
    assert cs.halation_params.ah_layer_transmittance_r == 1.0  # 無 AH 層
    assert cs.halation_params.psf_radius == 150
    
    # Portra400: Mie Bloom + 標準 Halation
    portra = get_film_profile("Portra400")
    
    assert portra.bloom_params.mode == "physical"
    assert portra.halation_params.enabled == True
    assert portra.halation_params.ah_layer_transmittance_r < 1.0  # 有 AH 層
```

### Test 2: 能量守恆（Bloom + Halation）
```python
def test_energy_conservation_combined():
    """驗證 Bloom + Halation 同時啟用時能量守恆"""
    
    # 創建測試影像（中心高光點）
    img = np.zeros((500, 500, 3), dtype=np.float32)
    img[240:260, 240:260, :] = 1.0  # 中心 20×20 白色亮點
    
    # 測試參數
    bloom_params = BloomParams(
        mode="mie_corrected",
        threshold=0.8,
        base_scattering_ratio=0.08,
        energy_conservation=True
    )
    
    halation_params = HalationParams(
        enabled=True,
        emulsion_transmittance_r=0.9,
        emulsion_transmittance_g=0.85,
        emulsion_transmittance_b=0.8,
        ah_layer_transmittance_r=0.3,  # 有 AH 層
        backplate_reflectance=0.3,
        psf_radius=100,
        energy_fraction=0.05
    )
    
    # 處理（需要實際調用 Phos 函數）
    result = apply_bloom_and_halation(img, bloom_params, halation_params)
    
    # 能量守恆驗證
    energy_in = np.sum(img)
    energy_out = np.sum(result)
    error = abs(energy_out - energy_in) / energy_in
    
    assert error < 0.01, f"Energy error: {error*100:.3f}% (should < 1%)"
```

### Test 3: 波長依賴驗證
```python
def test_wavelength_dependence_combined():
    """驗證 Bloom 與 Halation 波長依賴互不干擾"""
    
    # 純紅色高光
    img_red = np.zeros((300, 300, 3), dtype=np.float32)
    img_red[140:160, 140:160, 0] = 1.0  # R=1, G=0, B=0
    
    # 純藍色高光
    img_blue = np.zeros((300, 300, 3), dtype=np.float32)
    img_blue[140:160, 140:160, 2] = 1.0  # R=0, G=0, B=1
    
    # 處理
    result_red = apply_bloom_and_halation(img_red, bloom_params, halation_params)
    result_blue = apply_bloom_and_halation(img_blue, bloom_params, halation_params)
    
    # Bloom 驗證：藍光散射 > 紅光
    bloom_radius_red = measure_psf_radius(result_red[:, :, 0])
    bloom_radius_blue = measure_psf_radius(result_blue[:, :, 2])
    assert bloom_radius_blue > bloom_radius_red, \
        "Blue Bloom should be wider (Mie scattering)"
    
    # Halation 驗證：紅光穿透 > 藍光
    halation_intensity_red = measure_halo_intensity(result_red[:, :, 0])
    halation_intensity_blue = measure_halo_intensity(result_blue[:, :, 2])
    assert halation_intensity_red > halation_intensity_blue, \
        "Red Halation should be stronger (Beer-Lambert)"
```

### Test 4: 雙層光暈特徵
```python
def test_dual_halo_feature():
    """驗證雙層光暈（內層 Bloom + 外層 Halation）"""
    
    # 白色點光源
    img = np.zeros((600, 600, 3), dtype=np.float32)
    img[295:305, 295:305, :] = 1.0  # 中心 10×10 白點
    
    # 處理
    result = apply_bloom_and_halation(img, bloom_params, halation_params)
    
    # 徑向剖面分析
    profile = extract_radial_profile(result, center=(300, 300))
    
    # 檢測兩個峰值區域
    # 1. 內層峰（Bloom, r ≈ 20-40px）
    bloom_peak_idx = np.argmax(profile[10:50]) + 10
    
    # 2. 外層峰（Halation, r ≈ 80-120px）
    halation_peak_idx = np.argmax(profile[60:150]) + 60
    
    assert halation_peak_idx > bloom_peak_idx * 2, \
        "Halation radius should be significantly larger than Bloom"
    
    # 檢測「谷底」（Bloom 與 Halation 之間）
    valley_idx = bloom_peak_idx + 20
    valley_value = profile[valley_idx]
    assert valley_value < profile[bloom_peak_idx] * 0.5, \
        "Valley should exist between Bloom and Halation"
```

### Test 5: CineStill 極端案例
```python
def test_cinestill_extreme_halation():
    """驗證 CineStill 800T 的極端紅色光暈"""
    
    cs = get_film_profile("Cinestill800T")
    
    # 白色街燈（模擬夜景）
    img = np.zeros((800, 800, 3), dtype=np.float32)
    img[390:410, 390:410, :] = 1.0  # 20×20 白色高光
    
    # 處理
    result = apply_bloom_and_halation(
        img, 
        cs.bloom_params, 
        cs.halation_params
    )
    
    # 外圍光暈分析（r = 200-300px）
    outer_ring = extract_ring_region(result, center=(400, 400), r_inner=200, r_outer=300)
    
    # 紅色通道應佔主導
    mean_r = np.mean(outer_ring[:, :, 0])
    mean_g = np.mean(outer_ring[:, :, 1])
    mean_b = np.mean(outer_ring[:, :, 2])
    
    assert mean_r > mean_g * 1.2, "Red channel should dominate in CineStill halo"
    assert mean_r > mean_b * 1.5, "Red should be much stronger than blue"
    
    # 光暈半徑應達到 150px 以上
    halo_radius = measure_psf_radius(result[:, :, 0], threshold=0.01)
    assert halo_radius > 150, f"CineStill halo radius: {halo_radius}px (should > 150px)"
```

### Test 6: 效能基準測試
```python
def test_performance_combined():
    """驗證 Bloom + Halation 效能目標"""
    
    sizes = [
        (1000, 1000),   # 小圖
        (2000, 3000),   # 目標尺寸
    ]
    
    targets = {
        (1000, 1000): 2.0,   # < 2s
        (2000, 3000): 10.0,  # < 10s ← 關鍵目標
    }
    
    for size in sizes:
        # 隨機影像
        img = np.random.rand(*size, 3).astype(np.float32)
        img = np.clip(img * 1.5, 0, 1)  # 增加高光
        
        # 計時
        start = time.time()
        result = apply_bloom_and_halation(img, bloom_params, halation_params)
        elapsed = time.time() - start
        
        print(f"  {size}: {elapsed:.3f}s (target: < {targets[size]}s)")
        
        assert elapsed < targets[size], \
            f"Performance target missed: {elapsed:.2f}s > {targets[size]}s"
```

### Test 7: 參數獨立性
```python
def test_parameter_independence():
    """驗證 Bloom 與 Halation 參數可獨立調整"""
    
    img = create_test_image_with_highlights()
    
    # 測試 1: 僅 Bloom
    bloom_only = apply_bloom_and_halation(
        img,
        bloom_params=BloomParams(mode="mie_corrected", ...),
        halation_params=HalationParams(enabled=False)
    )
    
    # 測試 2: 僅 Halation
    halation_only = apply_bloom_and_halation(
        img,
        bloom_params=BloomParams(mode="physical", base_scattering_ratio=0.0),
        halation_params=HalationParams(enabled=True, ...)
    )
    
    # 測試 3: 兩者同時啟用
    combined = apply_bloom_and_halation(
        img,
        bloom_params=BloomParams(mode="mie_corrected", ...),
        halation_params=HalationParams(enabled=True, ...)
    )
    
    # 驗證疊加性（近似線性）
    # combined ≈ bloom_only + halation_only - original
    difference = combined - (bloom_only + halation_only - img)
    relative_error = np.mean(np.abs(difference)) / np.mean(img)
    
    assert relative_error < 0.1, \
        f"Effects should be approximately additive (error: {relative_error*100:.1f}%)"
```

---

## 🔧 輔助函數設計

### 徑向剖面提取
```python
def extract_radial_profile(image: np.ndarray, center: Tuple[int, int], 
                           channel: int = 0) -> np.ndarray:
    """提取徑向亮度剖面"""
    cy, cx = center
    max_radius = min(cy, cx, image.shape[0]-cy, image.shape[1]-cx)
    
    profile = []
    for r in range(max_radius):
        # 圓環上的點
        mask = create_circular_mask(image.shape[:2], center, r, r+1)
        values = image[mask, channel]
        profile.append(np.mean(values))
    
    return np.array(profile)
```

### PSF 半徑測量
```python
def measure_psf_radius(channel: np.ndarray, threshold: float = 0.01) -> float:
    """測量 PSF 半徑（FWHM 或閾值半徑）"""
    center = np.unravel_index(np.argmax(channel), channel.shape)
    profile = extract_radial_profile(channel[..., None], center, 0)
    
    # 找到首次低於閾值的半徑
    above_threshold = profile > (np.max(profile) * threshold)
    radius = np.where(~above_threshold)[0][0] if np.any(~above_threshold) else len(profile)
    
    return radius
```

### 光暈強度測量
```python
def measure_halo_intensity(channel: np.ndarray, r_inner: int = 60, 
                           r_outer: int = 150) -> float:
    """測量外圍光暈強度（排除中心 Bloom）"""
    center = np.unravel_index(np.argmax(channel), channel.shape)
    mask = create_ring_mask(channel.shape, center, r_inner, r_outer)
    
    return np.mean(channel[mask])
```

---

## 🎯 驗收標準

### 必須通過（P0）
- [ ] 所有 7 個測試通過
- [ ] 能量守恆誤差 < 1%
- [ ] 2000×3000 影像 < 10s
- [ ] 無 NaN/Inf 錯誤

### 應該通過（P1）
- [ ] Bloom 與 Halation 視覺上可區分
- [ ] CineStill 紅色光暈特徵明顯
- [ ] 參數獨立性誤差 < 10%

### 最好通過（P2）
- [ ] 效能開銷 < 150%（相比單獨效果）
- [ ] 記憶體占用 < 4GB
- [ ] 視覺對比測試（與真實底片）

---

## 📁 實作計劃

### 1. 創建測試文件
```bash
tests/test_mie_halation_integration.py  # 主測試文件（300 行）
tests/utils/optical_analysis.py          # 輔助函數（150 行）
```

### 2. 實作輔助函數
- `extract_radial_profile()`
- `measure_psf_radius()`
- `measure_halo_intensity()`
- `create_ring_mask()`
- `create_test_image_with_highlights()`

### 3. 實作整合測試
- Test 1-7（如上設計）
- 每個測試約 30-50 行

### 4. 驗證與調試
- 運行測試，記錄失敗案例
- 調整參數範圍（如容差、閾值）
- 視覺化中間結果（保存為圖片）

---

## ⏱️ 預估時間

| 任務 | 時間 | 優先級 |
|------|------|--------|
| 輔助函數實作 | 1h | P0 |
| 測試 1-3（參數、能量、波長） | 1.5h | P0 |
| 測試 4-5（雙層光暈、CineStill） | 1.5h | P1 |
| 測試 6-7（效能、獨立性） | 1h | P1 |
| 調試與優化 | 1h | P0 |
| **總計** | **6h** | - |

---

## 🚧 已知挑戰

### 1. **Phos_0.3.0.py 導入問題**
- 檔名有點號，Python 無法直接導入
- **解決方案**: 使用 `exec()` 動態載入，或創建測試用封裝函數

### 2. **apply_bloom_mie_corrected() 未與 Halation 整合**
- 目前兩個函數獨立
- **解決方案**: 創建 `apply_bloom_and_halation()` 整合函數

### 3. **視覺驗證主觀性**
- 「雙層光暈」特徵難以量化
- **解決方案**: 使用徑向剖面曲線，檢測峰值數量與位置

---

## 📚 參考資料

- **Phase 1 完成報告**: `tasks/TASK-003-medium-physics/phase1_completion_report.md`
- **Halation 實作**: `Phos_0.3.0.py` (Line 854-920)
- **Mie 散射實作**: `Phos_0.3.0.py` (Line 1309-1429)
- **Decision #012**: Halation 設計決策
- **Decision #014**: Mie 散射修正

---

**計劃創建時間**: 2025-12-22 23:55  
**預計開始時間**: 2025-12-22 24:00  
**預計完成時間**: 2025-12-23 06:00 (6 小時)  
**負責人**: Main Agent  
**審查者**: Physicist (物理正確性), Performance Engineer (效能驗證)
