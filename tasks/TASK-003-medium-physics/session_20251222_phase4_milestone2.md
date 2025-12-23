# Phase 4 Session Summary - 2025-12-22

## 📅 會話資訊
- **日期**: 2025-12-22
- **時長**: ~3 小時
- **任務**: TASK-003 Phase 4 Milestone 2 - 光譜模型核心函數實作
- **狀態**: 75% 完成，有阻塞問題需解決

---

## ✅ 本次會話完成項目

### 1. 核心函數實作 (100%)
成功在 `phos_core.py` 實作三個光譜轉換函數：

#### `rgb_to_spectrum()` (Line 460-545)
- **算法**: Smits (1999) 7 基向量插值
- **輸入**: RGB (H,W,3) 或 (3,)
- **輸出**: 光譜 (H,W,31) 或 (31,)，380-770nm，13nm 間隔
- **測試結果**: 
  - ✅ 主色（紅綠藍）完美重建
  - ✅ 白色/黑色正確
  - ❌ 效能問題：15s for 2000×3000 (目標 <2s)

#### `spectrum_to_xyz()` (Line 548-605)
- **算法**: CIE 1931 光譜積分 + D65 照明體
- **功能**: 31 通道光譜 → XYZ 三刺激值
- **測試結果**:
  - ✅ 白色光譜正確
  - ✅ 自定義照明體支援
  - ⚠️ 歸一化策略待優化

#### `xyz_to_srgb()` (Line 608-660)
- **算法**: IEC 61966-2-1:1999 (sRGB standard)
- **功能**: XYZ → sRGB with gamma correction
- **測試結果**:
  - ✅ D65 白點正確
  - ✅ 值域裁剪正確
  - ⚠️ Gamma 校正可能影響往返

### 2. 數據載入函數 (100%)
實作三個快取化數據載入函數：

- ✅ `load_smits_basis()` - Smits 基向量 (7×31)
- ✅ `load_cie_1931()` - CIE 1931 匹配函數 (3×31)
- ✅ `get_illuminant_d65()` - D65 日光光譜 (31)

### 3. 測試套件建立 (100%)
創建完整測試文件 `tests/test_spectral_model.py` (410 行):

**測試覆蓋**:
- 22 個測試案例
- 5 個測試類別
- 通過率: **77% (17/22)**

**測試分類**:
| 類別 | 通過/總數 | 通過率 |
|------|----------|--------|
| 數據載入 | 3/3 | 100% ✅ |
| RGB→Spectrum | 7/7 | 100% ✅ |
| Spectrum→XYZ | 3/3 | 100% ✅ |
| XYZ→sRGB | 3/3 | 100% ✅ |
| 往返一致性 | 1/4 | 25% ❌ |
| 效能測試 | 0/2 | 0% ❌ |

### 4. 文件產出 (100%)
- ✅ `phase4_milestone2_progress.md` - 詳細進度報告
- ✅ `context/decisions_log.md` - 決策 #020, #021 記錄
- ✅ `phos_core.py` - +295 行程式碼
- ✅ `tests/test_spectral_model.py` - +410 行測試程式碼

---

## ⚠️ 發現的問題與解決歷程

### 問題 #1: Smits 算法邏輯錯誤 (已解決 ✅)
**現象**: RGB(1,0,0) 轉換為 Magenta 光譜（錯誤），而非 Red 光譜

**根因**: 
- 初始實作錯誤理解 Smits 算法
- 將 "最小分量" 當作 "主導色"
- 導致 RGB(1,0,0) 被判定為 "b==g 最小 → Magenta"

**除錯過程**:
1. 發現白色被放大 3 倍（三個條件都匹配）
2. 改為嚴格互斥條件（`<` 而非 `<=`）
3. 發現純紅色產生 Magenta（完全錯誤）
4. 重新閱讀 Smits 論文，理解正確邏輯
5. 修正為：最小分量 → 缺失色 → 互補色組合

**解決方案**:
```python
# 正確邏輯：
if b <= r and b <= g:  # 藍色最小 → 黃色調
    spectrum = white*b + yellow*min(r-b, g-b) + red/green*(r-g)
```

**驗證結果**:
- ✅ RGB(1,0,0) → Red basis (100% 匹配)
- ✅ RGB(0,1,0) → Green basis (100% 匹配)
- ✅ RGB(0,0,1) → Blue basis (100% 匹配)
- ✅ RGB(1,1,1) → White basis (100% 匹配)

### 問題 #2: 往返一致性誤差 (未解決 🔴)
**現象**:
```
RGB(1.0, 1.0, 1.0) → RGB(1.00, 0.996, 0.929)  # Blue -7%
RGB(0.25, 0.25, 0.25) → RGB(0.56, 0.54, 0.50)  # 124% 亮度誤差
```

**嘗試過的方案**:
1. ❌ 移除 XYZ 歸一化 → 灰階值過曝
2. ❌ 使用 Y_max 歸一化 → 色彩平衡破壞
3. ⚠️ 使用 Y_white 歸一化 → 白色正確，灰階變亮

**當前假設**:
問題可能在於 **sRGB gamma 校正** 的非線性：
```python
# sRGB gamma: y = x^(1/2.4)
0.25^(1/2.4) ≈ 0.53  # 不是 0.25！
```

**待驗證**:
1. Smits 基向量是否針對線性 RGB（非 sRGB）
2. 是否需要在輸入前做 sRGB → Linear RGB
3. 或在輸出後做 Linear RGB → sRGB

**阻塞影響**:
- 🔴 **Blocker for Milestone 3**: 灰階誤差 >20%
- 📊 測試失敗: 3/4 往返測試失敗

### 問題 #3: 效能不佳 (未解決 🔴)
**現象**:
- 2000×3000 影像: 15.0s (目標 <2.0s)
- 需要 **8x 加速**

**根因**:
- 大量 `np.where()` 條件判斷
- Boolean indexing 產生多次陣列拷貝
- 未向量化的邏輯分支

**可能解決方案**:
1. **向量化優化**: 預計算所有 mask，單次應用
2. **JIT 編譯**: 使用 Numba `@jit` 加速
3. **LUT 查表**: 預計算 256×256×256 → 31 通道（需 2GB 記憶體）
4. **分塊處理**: Tile-based processing

**阻塞影響**:
- 🟡 **P1 for Milestone 4**: 整體流程效能目標 <4.2s

---

## 📊 進度指標

### Milestone 2 完成度: 75%
```
✅ 函數實作        100%  (3/3)
✅ 數據載入        100%  (3/3)
✅ 測試創建        100%  (22 tests)
⚠️  測試通過率      77%   (17/22)
❌ 往返一致性       25%   (1/4)
❌ 效能達標         0%    (0/2)
```

### 程式碼貢獻
- **新增**: ~705 行
  - `phos_core.py`: +295 行
  - `tests/test_spectral_model.py`: +410 行
- **修改**: 0 行（無破壞性變更）

### 測試覆蓋
- **單元測試**: 22 個
- **通過**: 17 個 (77%)
- **失敗**: 5 個 (23%)
  - 3 個往返測試
  - 2 個效能測試

---

## 🎯 下一步行動計畫

### 立即任務 (Next Session, P0)
1. **修正往返一致性** (預估 1-2 小時)
   - 查閱 Smits 論文關於 RGB 色彩空間定義
   - 測試 Linear RGB 往返
   - 實作 sRGB ↔ Linear RGB 轉換（如需要）
   - 目標: 所有灰階值誤差 <5%

2. **效能分析** (預估 30 分鐘)
   - 使用 `cProfile` 找出瓶頸
   - 確認是否為 boolean indexing 問題
   - 評估向量化 vs JIT vs LUT 方案

### 中期任務 (Milestone 3)
完成 Milestone 2 後：
1. 整合膠片光譜敏感度曲線
2. 實作光譜卷積與膠片響應
3. 更新主流程（`Phos_0.3.0.py`）

### 長期任務 (Milestone 4-5)
1. 分塊處理優化（記憶體控制）
2. 端到端測試與驗證
3. 效能基準測試

---

## 💡 技術洞察與學習

### 1. Smits 算法理解深化
- ✅ 正確邏輯：最小分量 → 缺失色 → 互補色組合
- ✅ 7 個基向量組合可覆蓋 RGB 色域
- ⚠️ 基向量是針對**線性 RGB** 還是 **sRGB** 需確認

### 2. 色彩空間陷阱
- ⚠️ sRGB 的 gamma 非線性會導致往返誤差
- ⚠️ XYZ 歸一化需謹慎處理白點與亮度關係
- ✅ D65 白點 XYZ ≈ (0.95, 1.00, 1.09) 已驗證正確

### 3. NumPy 效能最佳化
- ❌ 大量 `np.where()` 和 boolean indexing 很慢
- ✅ `@lru_cache` 可有效減少重複載入
- 🔄 需探索 einsum / JIT / LUT 等加速方案

---

## 📚 參考文獻

1. Smits, B. (1999). "An RGB-to-Spectrum Conversion for Reflectances". *Journal of Graphics Tools*, 4(4), 11-22.
2. CIE 15:2004. "Colorimetry, 3rd Edition". Commission Internationale de l'Éclairage.
3. IEC 61966-2-1:1999. "Multimedia systems and equipment - Colour measurement and management - Part 2-1: sRGB".
4. Lindbloom, B. "RGB/XYZ Matrices". http://www.brucelindbloom.com/

---

## ✅ 會話檢查清單

- [x] 核心函數實作完成
- [x] 單元測試創建
- [x] 主色正確性驗證
- [x] 進度報告撰寫
- [x] 決策日誌更新
- [ ] 往返一致性達標 (🔴 Blocker)
- [ ] 效能目標達成 (🔴 Blocker)
- [ ] Milestone 2 完全完成

---

**總結**: 本次會話成功實作了光譜模型的三個核心函數，並驗證了主色轉換的正確性（77% 測試通過）。主要阻塞問題為灰階往返誤差（24%）和效能不足（8x 慢於目標）。下次會話需優先解決往返一致性問題，查明是否為 sRGB gamma 或 XYZ 歸一化策略問題。

**預計剩餘時間**: Milestone 2 完成需 2-3 小時，Milestone 3-5 需額外 8-10 小時。
