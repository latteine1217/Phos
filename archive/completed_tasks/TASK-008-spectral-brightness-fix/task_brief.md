# TASK-008: 修復光譜模型亮度損失問題

**創建時間**: 2025-12-23 14:15  
**優先級**: 🔴 High  
**狀態**: 🟡 In Progress  
**類型**: Bug Fix + Physics Verification

---

## 📋 任務目標

修復 Phase 4 (v0.4.0) 光譜膠片模擬導致的顯著亮度損失問題（22%-65%）。

**成功指標**:
1. ✅ 50% 灰卡亮度變化 <10%
2. ✅ 藍天場景亮度變化 <15%
3. ✅ 白卡保持 255（無變化）
4. ✅ 所有 `test_spectral_*.py` 測試通過
5. ✅ Physicist Gate 審查通過

---

## 🔍 問題描述

### **症狀**

根據 `scripts/diagnose_color_brightness.py` 測試結果：

| 測試場景 | Simple 模式 | Spectral 模式 | 亮度損失 |
|---------|------------|---------------|----------|
| 50% 灰卡 | +9.9% | **-50.0%** | 🔴 59.9% |
| 藍天場景 | +11.6% | **-35.9%** | 🔴 47.5% |
| 純綠色 | -5.6% | **-65.0%** | 🔴 59.4% |
| 純紅色 | -4.7% | **-28.6%** | 🔴 23.9% |
| 灰階條 | +6.0% | **-22.9%** | 🔴 28.9% |

### **影響範圍**

- **受影響模組**: `phos_core.py` (RGB→Spectrum→Film RGB pipeline)
- **受影響函數**:
  - `rgb_to_spectrum()` - Smits 算法
  - `apply_film_spectral_sensitivity()` - 膠片感光度應用
  - `spectrum_to_xyz()` / `xyz_to_srgb()` - 色彩空間轉換
- **受影響用戶**: 所有啟用「膠片光譜敏感度」功能的用戶

### **根本原因假設**

1. ❌ **RGB→Spectrum 能量未守恆**: Smits 算法可能未保持總輻射能量
2. ❌ **膠片敏感度曲線過暗**: `film_spectral_sensitivity.npz` 數值偏低
3. ❌ **正規化錯誤**: `normalize=True` 參數導致錯誤縮放
4. ❌ **CIE XYZ 轉換問題**: Spectrum→XYZ 積分缺少歸一化係數

---

## 🎯 修復策略

### **Phase 1: 診斷與驗證（預估 30 分鐘）**

**委派**: Debug Engineer Sub-agent

**任務**:
1. 追蹤 RGB(128,128,128) 在管線各階段的能量
2. 驗證 Smits 算法的光譜積分 vs 輸入亮度
3. 檢查膠片敏感度曲線的絕對數值
4. 驗證 Spectrum→XYZ 轉換的參考白點

**輸出**: `debug_spectral_pipeline.md`（含數值追蹤表）

---

### **Phase 2: 物理審查（預估 20 分鐘）**

**委派**: Physicist Sub-agent

**任務**:
1. 審查 Smits RGB→Spectrum 的物理正確性
2. 驗證膠片敏感度曲線的合理性（與真實膠片數據對比）
3. 確認 CIE 1931 色度匹配函數的使用
4. 提供物理正確的修正方案

**輸出**: `physicist_spectral_review.md`（含修正建議）

---

### **Phase 3: 實作修復（預估 60 分鐘）**

**負責**: Main Agent (我)

**修復步驟**:

#### **3.1 添加能量守恆驗證**
```python
def rgb_to_spectrum(rgb, method='smits', verify_energy=True):
    """RGB → Spectrum 轉換（新增能量驗證）"""
    spectrum = _smits_core(rgb)
    
    if verify_energy:
        # 驗證：Spectrum 積分 ≈ RGB 亮度
        input_lum = 0.299*R + 0.587*G + 0.114*B
        spectrum_lum = np.sum(spectrum * CIE_Y_curve, axis=-1) / normalizer
        
        energy_error = abs(spectrum_lum - input_lum) / (input_lum + 1e-6)
        if energy_error > 0.1:  # >10% 誤差
            warnings.warn(f"Spectrum energy loss: {energy_error*100:.1f}%")
    
    return spectrum
```

#### **3.2 修正膠片敏感度曲線**
```python
# 方案 A: 整體縮放校正
film_curves = load_film_sensitivity('Portra400')
calibration_factor = compute_white_point_calibration(film_curves)
film_curves['red'] *= calibration_factor
film_curves['green'] *= calibration_factor
film_curves['blue'] *= calibration_factor

# 方案 B: 基於真實膠片數據重新生成
# （如 Physicist 建議數據錯誤）
```

#### **3.3 修正 `apply_film_spectral_sensitivity()`**
```python
def apply_film_spectral_sensitivity(spectrum, film_curves, normalize=True):
    """應用膠片感光度（修正版）"""
    # 計算 RGB 響應（光譜積分）
    R = np.sum(spectrum * film_curves['red'], axis=-1)
    G = np.sum(spectrum * film_curves['green'], axis=-1)
    B = np.sum(spectrum * film_curves['blue'], axis=-1)
    
    if normalize:
        # 修正：使用 D65 白點校準
        white_spectrum = load_d65_spectrum()
        white_R = np.sum(white_spectrum * film_curves['red'])
        white_G = np.sum(white_spectrum * film_curves['green'])
        white_B = np.sum(white_spectrum * film_curves['blue'])
        
        # 正規化：確保白點 → (1, 1, 1)
        R = R / white_R
        G = G / white_G
        B = B / white_B
    
    return np.stack([R, G, B], axis=-1)
```

#### **3.4 添加白點往返測試**
```python
def test_white_roundtrip():
    """測試：白色 RGB → Spectrum → Film RGB → 白色"""
    white_rgb = np.array([1.0, 1.0, 1.0])
    
    spectrum = rgb_to_spectrum(white_rgb)
    film_curves = load_film_sensitivity('Portra400')
    output_rgb = apply_film_spectral_sensitivity(spectrum, film_curves)
    
    error = np.abs(output_rgb - white_rgb).max()
    assert error < 0.05, f"White point error: {error:.3f}"
```

---

### **Phase 4: 回歸測試（預估 20 分鐘）**

**測試項目**:
1. ✅ 重新運行 `scripts/diagnose_color_brightness.py`
2. ✅ 確保 50% 灰卡亮度變化 <10%
3. ✅ 確保藍天場景亮度變化 <15%
4. ✅ 執行 `tests/test_spectral_model.py`（如存在）
5. ✅ 執行 `tests/test_film_spectral_sensitivity.py`
6. ✅ 視覺檢查：處理真實照片並比對

---

### **Phase 5: Reviewer Gate（預估 15 分鐘）**

**委派**: Reviewer Sub-agent

**檢查項目**:
1. 物理正確性（Physicist 意見已整合？）
2. 能量守恆驗證（測試覆蓋？）
3. 向後相容性（`normalize=True/False` 行為？）
4. 效能影響（新增驗證開銷？）
5. 文檔更新（`PHYSICAL_MODE_GUIDE.md`？）

**輸出**: `review_spectral_fix.md`（通過/拒絕 + 建議）

---

## 📊 驗收標準

### **功能測試**

| 測試 | 目標 | 當前 | 修復後 |
|-----|------|------|--------|
| 50% 灰卡亮度變化 | <10% | -50.0% 🔴 | <10% ✅ |
| 藍天場景亮度變化 | <15% | -35.9% 🔴 | <15% ✅ |
| 白卡亮度變化 | 0% | 0% ✅ | 0% ✅ |
| 純紅色亮度變化 | <20% | -28.6% 🔴 | <20% ✅ |
| 純綠色亮度變化 | <20% | -65.0% 🔴 | <20% ✅ |
| 純藍色亮度變化 | <20% | +108.7% 🔴 | <20% ✅ |

### **物理測試**

- [ ] 白點往返誤差 <5%
- [ ] RGB(0.5,0.5,0.5) 往返誤差 <10%
- [ ] 色度座標偏移 <0.05 (CIE xy)
- [ ] 能量守恆誤差 <1%

### **回歸測試**

- [ ] `tests/test_spectral_model.py`: 全通過
- [ ] `tests/test_film_spectral_sensitivity.py`: 全通過
- [ ] `scripts/diagnose_color_brightness.py`: Spectral 模式誤差 <15%

---

## 📁 相關文件

### **輸入**
- `test_outputs/diagnostic_report.txt` - 問題診斷報告
- `docs/DIAGNOSTIC_RESULTS_20251223.md` - 完整分析
- `phos_core.py` (Line 200-650) - 光譜模型實作
- `data/film_spectral_sensitivity.npz` - 膠片數據
- `data/cie_1931_31points.npz` - CIE 色度匹配函數

### **輸出**（本任務產出）
- `tasks/TASK-008/debug_spectral_pipeline.md` - Debug 追蹤
- `tasks/TASK-008/physicist_spectral_review.md` - 物理審查
- `tasks/TASK-008/review_spectral_fix.md` - Reviewer 報告
- `tasks/TASK-008/fix_implementation.md` - 實作細節
- `tests/test_spectral_energy_conservation.py` - 新增測試

---

## ⏱️ 時間盒

**總預估時間**: 2.5 小時

- Phase 1 (Debug): 30 分鐘
- Phase 2 (Physicist): 20 分鐘
- Phase 3 (Implementation): 60 分鐘
- Phase 4 (Testing): 20 分鐘
- Phase 5 (Review): 15 分鐘
- Buffer: 5 分鐘

**實際開始**: 2025-12-23 14:15  
**預計完成**: 2025-12-23 16:45

---

## 🚨 風險與阻斷

### **風險 1: 膠片數據本身錯誤**
**機率**: Medium  
**影響**: High  
**緩解**: Physicist 提供真實膠片光譜數據參考

### **風險 2: Smits 算法固有限制**
**機率**: Low  
**影響**: High  
**緩解**: 考慮替代算法（如 Meng 2015, Jakob 2019）

### **風險 3: 修正破壞現有測試**
**機率**: Medium  
**影響**: Medium  
**緩解**: 完整回歸測試 + 向後相容參數

---

## 📝 決策記錄

### **決策 #1: 使用白點校準正規化**
**理由**: 確保 D65 白點輸入 → RGB(1,1,1) 輸出  
**替代方案**: 基於灰卡校準（拒絕，不符合色彩科學標準）

### **決策 #2: 保留 `normalize` 參數**
**理由**: 向後相容性 + 給用戶選擇權  
**影響**: `normalize=False` 時輸出絕對值（可能 >1.0）

---

**創建者**: Main Agent  
**審查者**: TBD (Physicist, Reviewer)  
**狀態**: 🟡 待執行 Phase 1
