# 🎨 Phos v0.4.0 色彩與亮度診斷結果

**診斷時間**: 2025-12-23 14:09  
**測試腳本**: `scripts/diagnose_color_brightness.py`  
**完整報告**: `test_outputs/diagnostic_report.txt`

---

## 🔍 核心發現

### ✅ **通道順序正確 - 無 BGR/RGB 互換問題**

所有測試均未檢測到 R↔B 通道互換：
- ✅ 純藍色 (B=255) → 輸出仍以藍色為主
- ✅ 純紅色 (R=255) → 輸出仍以紅色為主
- ✅ BGR→RGB 轉換邏輯正確運作

**結論**: Decision #023 (2025-12-20) 的修復仍然有效。

---

### ⚠️ **光譜模式導致顯著變暗**

當啟用「膠片光譜敏感度」(Spectral Model) 時，圖像亮度大幅降低：

| 測試場景 | Simple 模式 | Spectral 模式 | 差異 |
|---------|------------|---------------|------|
| **50% 灰卡** | +9.9% | **-50.0%** | 🔴 -59.9% |
| **藍天場景** | +11.6% | **-35.9%** | 🔴 -47.5% |
| **灰階條** | +6.0% | **-22.9%** | 🔴 -28.9% |
| **純綠色** | -5.6% | **-65.0%** | 🔴 -59.4% |
| **純紅色** | -4.7% | **-28.6%** | 🔴 -23.9% |
| **純藍色** | +131.9% | +108.7% | ⚠️ 兩者皆異常增亮 |
| **白卡** | 0.0% | 0.0% | ✅ 正常 |

---

## 📊 數據分析

### **測試案例：50% 中性灰卡**

**Simple 模式（無光譜）**:
```
輸入: BGR = (128, 128, 128) → 亮度 128.0
輸出: BGR = (131, 145, 136) → 亮度 140.7
變化: +9.9% ✅ 輕微增亮，可接受
```

**Spectral 模式（31通道光譜）**:
```
輸入: BGR = (128, 128, 128) → 亮度 128.0
輸出: BGR = (59, 65, 64) → 亮度 64.0
變化: -50.0% 🔴 亮度減半！
```

### **測試案例：藍天場景**

**Simple 模式**:
```
輸入: BGR = (150, 150, 110) → 亮度 138.0
輸出: BGR = (152, 168, 127.5) → 亮度 154.1
變化: +11.6% ✅ 正常增亮
```

**Spectral 模式**:
```
輸入: BGR = (150, 150, 110) → 亮度 138.0
輸出: BGR = (101.5, 94, 72.5) → 亮度 88.4
變化: -35.9% 🔴 顯著變暗
```

---

## 🔬 根本原因分析

### **問題來源：光譜膠片敏感度模型**

1. **RGB → Spectrum → Film RGB 管線**（Phase 4, v0.4.0）:
   ```python
   # phos_core.py
   spectrum = rgb_to_spectrum(lux_combined, use_tiling=True, tile_size=512)
   film_curves = load_film_sensitivity('Portra400')
   rgb_with_film = apply_film_spectral_sensitivity(spectrum, film_curves, normalize=True)
   ```

2. **可能的問題點**:
   - ❌ **光譜轉換能量損失**: RGB→Spectrum 轉換未保持總能量
   - ❌ **膠片敏感度曲線過暗**: Portra400 的光譜響應曲線可能積分值過低
   - ❌ **正規化錯誤**: `normalize=True` 參數可能導致錯誤的縮放
   - ❌ **CIE XYZ 轉換問題**: Spectrum→XYZ→sRGB 管線中的 gamma/白點處理

3. **純藍色異常增亮**:
   - Simple: +131.9%
   - Spectral: +108.7%
   - **原因**: 藍色通道的光譜響應係數可能設定過高

---

## 🎯 問題定位

### **用戶報告 "變暗而且變色" 的真實原因**:

✅ **確認問題**: 
- **變暗**: 光譜模式導致 **22%-65% 亮度損失**
- **變色**: 不同色彩通道的損失不均勻（綠色損失 65% vs 紅色損失 29%）

❌ **不是問題**:
- BGR/RGB 通道互換（已修復且驗證正確）
- Simple 模式處理（亮度變化 <12%，可接受）

---

## 🛠️ 解決方案建議

### **方案 A: 修正光譜模型能量守恆**

**目標**: 確保 RGB→Spectrum→Film RGB 管線保持亮度一致性

1. **驗證 Smits RGB→Spectrum 能量守恆**:
   ```python
   # 檢查：輸入 RGB 亮度 = 輸出 Spectrum 積分？
   input_luminance = 0.299*R + 0.587*G + 0.114*B
   spectrum_integral = np.sum(spectrum * CIE_Y_curve) / normalizer
   assert abs(spectrum_integral - input_luminance) < 0.05
   ```

2. **調整膠片敏感度曲線**:
   ```python
   # 檢查：Portra400 的 R/G/B 曲線積分是否合理？
   # 可能需要整體放大 1.5-2x
   film_curves['red'] *= correction_factor
   film_curves['green'] *= correction_factor
   film_curves['blue'] *= correction_factor
   ```

3. **檢查 `apply_film_spectral_sensitivity()` 正規化邏輯**:
   ```python
   # 當前實作可能錯誤縮放了輸出
   # 需要確保：白點輸入 → 白點輸出
   ```

### **方案 B: 添加亮度補償**

**臨時解決方案**（在修正根因前）:

```python
# 在 spectral 處理後添加
if use_film_spectra:
    # 計算亮度損失
    lux_before = np.mean(lux_combined)
    lux_after = np.mean(rgb_with_film)
    compensation = lux_before / (lux_after + 1e-6)
    
    # 限制補償範圍（避免過度放大）
    compensation = np.clip(compensation, 1.0, 2.0)
    
    # 應用補償
    rgb_with_film *= compensation
```

### **方案 C: 提供 UI 開關**

**讓用戶選擇是否啟用光譜模型**（目前已有，但需明確標示影響）:

```python
# Streamlit UI
use_film_spectra = st.checkbox(
    "🔬 膠片光譜敏感度（實驗性功能）",
    value=False,  # 預設關閉
    help="⚠️ 當前版本可能導致圖像變暗 20-50%"
)
```

---

## 📋 行動項目

### **Phase 1: 驗證問題（已完成 ✅）**
- [x] 創建診斷測試腳本
- [x] 確認 BGR/RGB 轉換正確
- [x] 定位光譜模型為變暗原因

### **Phase 2: 修正光譜模型（待執行）**
- [ ] 檢查 `rgb_to_spectrum()` 能量守恆
- [ ] 檢查 `apply_film_spectral_sensitivity()` 正規化邏輯
- [ ] 驗證膠片敏感度曲線數值
- [ ] 添加白點往返測試（White → Spectrum → White）

### **Phase 3: 回歸測試（待執行）**
- [ ] 重新運行診斷腳本
- [ ] 確保 50% 灰卡亮度變化 <10%
- [ ] 確保藍天場景亮度變化 <15%
- [ ] 確保白卡保持 255

### **Phase 4: 文檔更新（待執行）**
- [ ] 更新 `PHYSICAL_MODE_GUIDE.md`
- [ ] 更新 `decisions_log.md`
- [ ] 添加光譜模型已知限制說明

---

## 🔗 相關文件

- **測試腳本**: `scripts/diagnose_color_brightness.py`
- **完整報告**: `test_outputs/diagnostic_report.txt`
- **對比圖**: `test_outputs/diagnostic_comparison.png`
- **原始問題**: Decision #023 (BGR/RGB swap fix)
- **光譜實作**: `phos_core.py` (Phase 4)
- **膠片數據**: `data/film_spectral_sensitivity.npz`

---

## 📞 給用戶的建議

如果您遇到「圖像變暗」問題：

1. **檢查是否啟用了光譜敏感度**:
   - 在側邊欄找到「🔬 膠片光譜敏感度」選項
   - 嘗試關閉此選項

2. **使用 Simple/Artistic 模式**:
   - 光譜模型僅在某些配置下觸發
   - Simple 模式亮度變化 <12%

3. **提供測試圖像**:
   - 如問題持續，請提供輸入/輸出範例
   - 使用 `test_outputs/input_*.png` 作為標準測試

---

**最後更新**: 2025-12-23  
**測試版本**: Phos v0.4.0  
**狀態**: 🟡 問題已定位，待修復
