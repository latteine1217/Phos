# 顏色顯示修復測試指南

**修復日期**: 2025-12-20  
**修復版本**: Phos v0.3.0  
**問題**: Streamlit UI 中顯示顏色反轉（藍天顯示為紅/橙色）

---

## 快速測試步驟

### 1. 啟動 Streamlit（如果已運行，請重啟）

```bash
cd /Users/latteine/Documents/coding/Phos
streamlit run Phos_0.3.0.py
```

### 2. 使用標準測試圖像

**測試圖像**: `test_blue_sky_input.png`（已包含在專案中）

- 上半部：純藍天（BGR=[255,100,100]）
- 下半部：灰色建築（BGR=[128,128,128]）

### 3. 處理流程

1. 在 Streamlit UI 中點擊「Browse files」
2. 上傳 `test_blue_sky_input.png`
3. 選擇任一底片配置（建議：Portra400_MediumPhysics）
4. 點擊「開始處理」或等待自動處理

### 4. 驗證結果

#### ✅ 正確結果（修復後）

**Streamlit 顯示**:
- 上半部應顯示**藍色/藍紫色**天空
- 下半部應顯示灰色建築
- 顏色自然，無明顯色偏

**下載檔案**:
- 用任何圖像查看器打開下載的 JPEG
- 應與 Streamlit 顯示一致（藍色天空）

#### ❌ 錯誤結果（修復前）

**Streamlit 顯示**:
- 上半部顯示**紅色/橙色**天空 ← BUG
- 下半部可能顯示青色/綠色
- 顏色明顯異常

**下載檔案**:
- 可能是正確的（藍色天空）← 表示問題在顯示層

---

## 詳細驗證（進階）

### 檢查色彩通道分布

使用 Python 腳本分析下載的圖像：

```bash
python3 <<'PYTHON'
import cv2
import numpy as np

# 讀取下載的圖像
img = cv2.imread('Phos_<film_name>_<date>.jpg')

# 計算通道平均值
b_mean = img[..., 0].mean()
g_mean = img[..., 1].mean()
r_mean = img[..., 2].mean()

print(f"Blue channel mean: {b_mean:.1f}")
print(f"Green channel mean: {g_mean:.1f}")
print(f"Red channel mean: {r_mean:.1f}")
print(f"R-B difference: {r_mean - b_mean:.1f}")

# 判斷
if b_mean > r_mean + 20:
    print("✅ 正確：藍色通道主導（藍天）")
elif r_mean > b_mean + 20:
    print("❌ 錯誤：紅色通道主導（顏色反轉）")
else:
    print("⚠️  中性：R/B 接近（可能是灰色主導的圖像）")
PYTHON
```

**預期輸出**（修復後）:
```
Blue channel mean: 160-170
Green channel mean: 120-130
Red channel mean: 115-125
R-B difference: -40 to -50
✅ 正確：藍色通道主導（藍天）
```

---

## 測試不同底片配置

為確保修復在所有模式下都生效，請測試：

| 底片配置 | 物理模式 | 波長依賴 | 預期結果 |
|---------|---------|---------|---------|
| Portra400 | ✅ | ✅ | 藍天正常 |
| Portra400_MediumPhysics | ✅ | ✅ | 藍天正常 |
| Portra400_MediumPhysics_Mie | ✅ | ✅ (Mie) | 藍天正常 |
| Velvia50 | ❌ | ❌ | 藍天正常 |
| Cinestill800T | ❌ | ❌ | 藍天正常（可能偏藍綠） |

---

## 常見問題 (FAQ)

### Q1: 修復後顏色看起來還是有點偏？

**A**: 這是正常的！底片模擬會產生色調偏移（色溫、色偏），這是底片特性的一部分。重點是：
- ✅ 藍天不應變成紅天
- ✅ 紅花不應變成藍花
- ✅ 灰色應保持中性（不應變成青色或橙色）

### Q2: 不同瀏覽器結果不同？

**A**: 修復後應該在所有瀏覽器中一致。如果仍有差異：
1. 清除瀏覽器快取並重啟 Streamlit
2. 檢查瀏覽器的色彩管理設定
3. 嘗試隱私模式/無痕模式

### Q3: 下載的圖像顏色正確，但 Streamlit 顯示錯誤？

**A**: 如果出現這種情況，表示修復未生效。請確認：
1. 是否重啟了 Streamlit（修改後必須重啟）
2. 是否使用了正確的檔案（`Phos_0.3.0.py`）
3. 檢查 Line 2387 是否為：`st.image(film_rgb, channels="RGB", width=800)`

### Q4: 我可以自己製作測試圖像嗎？

**A**: 可以！建議包含：
- 純色區域（純藍、純紅、純綠）
- 灰階梯度（黑→白）
- 真實照片（風景、人像等）

---

## 技術細節

### 修復內容

**檔案**: `Phos_0.3.0.py`  
**位置**: Line 2383-2390

**修改前**:
```python
st.image(film_image, channels="BGR", width=800)
film_rgb = cv2.cvtColor(film_image, cv2.COLOR_BGR2RGB)  # 僅下載用
```

**修改後**:
```python
film_rgb = cv2.cvtColor(film_image, cv2.COLOR_BGR2RGB)  # 顯示+下載共用
st.image(film_rgb, channels="RGB", width=800)
```

### 根本原因

Streamlit 的 `channels="BGR"` 參數在某些環境下（特定瀏覽器版本、OS、Streamlit 版本組合）會被忽略，導致：
- BGR 數據被按 RGB 順序解釋
- 藍色通道（B）被誤認為紅色通道（R）
- 紅色通道（R）被誤認為藍色通道（B）

### 解決方案

統一在 Python 端轉換為標準 RGB 格式，不依賴瀏覽器端的參數：
1. OpenCV 內部處理仍使用 BGR（效能、相容性）
2. 輸出給 Streamlit 前轉換為 RGB
3. 明確指定 `channels="RGB"`（或省略，預設就是 RGB）

---

## 回報問題

如果測試後仍發現問題，請提供：

1. **測試圖像**: 原始輸入檔案
2. **輸出結果**: 
   - Streamlit 顯示的截圖
   - 下載的 JPEG 檔案
3. **環境資訊**:
   ```bash
   streamlit --version
   python --version
   pip show opencv-python
   ```
4. **瀏覽器**: 名稱 + 版本（Chrome 120, Safari 17, etc.）
5. **作業系統**: macOS 14.1, Windows 11, etc.

---

**測試完成日期**: _______________  
**測試者**: _______________  
**結果**: ⬜ 通過  ⬜ 失敗  
**備註**: _______________
