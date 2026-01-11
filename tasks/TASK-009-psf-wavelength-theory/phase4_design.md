# Phase 4: 視覺驗證 - 設計文件

**日期**: 2025-12-23  
**任務**: TASK-009 P1-1 PSF 波長依賴理論推導  
**階段**: Phase 4 - 視覺驗證  
**預估時間**: 3 小時

---

## 目標

驗證 Mie 查表相比經驗公式的視覺效果差異，確保：
1. **物理正確性優先**: Mie 查表效果更接近真實膠卷
2. **視覺可接受性**: 藍光 Bloom 減弱不會造成不自然效果
3. **定量可追蹤**: PSNR/SSIM 數據記錄

---

## 測試策略

### 1. 測試場景設計 (3 個)

#### 場景 A: 藍天高光
**目的**: 檢測藍光 Bloom 減弱效果

**測試影像**: 
- 藍天 + 太陽（強烈藍光高光）
- 或使用 `test_outputs/input_blue_sky_scene.png` (如存在)

**預期差異**:
- 經驗公式: 藍天周圍有明顯藍色光暈
- Mie 查表: 藍色光暈減弱 93%，紅/黃光暈增強

---

#### 場景 B: 色彩平衡 (灰階卡)
**目的**: 檢測中性色偏移

**測試影像**:
- 使用 `test_outputs/input_gray_card_50.png`
- 或生成 50% 灰階卡

**預期差異**:
- 應該極小（灰階無色散）
- 檢查是否引入色偏

---

#### 場景 C: 色彩鮮豔場景
**目的**: 檢測色彩飽和場景的散射差異

**測試影像**:
- 純紅/綠/藍色塊
- 使用 `test_outputs/input_pure_red/green/blue.png`

**預期差異**:
- 紅色: 散射增強（η_r 相對更大）
- 藍色: 散射減弱（η_b 減小）
- 綠色: 中間值

---

### 2. 對比模式 (3 種)

#### A. 經驗公式模式
```python
film_profile = get_film_profile("Portra400")
film_profile.wavelength_bloom_params.use_mie_lookup = False
```

#### B. Mie 查表模式 (預設)
```python
film_profile = get_film_profile("Portra400")
# use_mie_lookup = True (預設)
```

#### C. 差異熱圖
```python
diff = np.abs(mie_output - empirical_output)
diff_heatmap = cv2.applyColorMap((diff * 255).astype(np.uint8), cv2.COLORMAP_JET)
```

---

### 3. 定量指標

#### PSNR (Peak Signal-to-Noise Ratio)
```python
def calculate_psnr(img1, img2):
    mse = np.mean((img1.astype(float) - img2.astype(float)) ** 2)
    if mse == 0:
        return float('inf')
    max_pixel = 255.0
    psnr = 20 * np.log10(max_pixel / np.sqrt(mse))
    return psnr
```

**解讀**:
- PSNR > 40 dB: 差異極小
- PSNR 30-40 dB: 差異可見但可接受
- PSNR < 30 dB: 差異顯著

---

#### SSIM (Structural Similarity Index)
```python
from skimage.metrics import structural_similarity as ssim

ssim_value = ssim(img1, img2, multichannel=True, channel_axis=2)
```

**解讀**:
- SSIM > 0.95: 幾乎相同
- SSIM 0.80-0.95: 相似但有差異
- SSIM < 0.80: 結構差異明顯

---

#### 色差 ΔE (CIE Lab)
```python
def calculate_delta_e(img1, img2):
    lab1 = cv2.cvtColor(img1, cv2.COLOR_RGB2LAB).astype(float)
    lab2 = cv2.cvtColor(img2, cv2.COLOR_RGB2LAB).astype(float)
    
    delta_e = np.sqrt(np.sum((lab1 - lab2) ** 2, axis=2))
    return delta_e.mean()
```

**解讀**:
- ΔE < 1: 人眼無法分辨
- ΔE 1-3: 輕微差異
- ΔE 3-6: 可見差異
- ΔE > 6: 明顯差異

---

### 4. 視覺評估準則

#### 主觀評分 (1-5 分)

| 指標 | 1 分 | 3 分 | 5 分 |
|------|------|------|------|
| **真實感** | 不自然 | 可接受 | 非常真實 |
| **色彩平衡** | 嚴重偏色 | 輕微偏移 | 完美中性 |
| **高光處理** | 過曝/假 | 可接受 | 柔和自然 |
| **整體品質** | 不可用 | 尚可 | 優秀 |

---

## 實作計畫

### Step 1: 準備測試影像 (30 分鐘)

#### 1.1 檢查現有測試影像
```bash
ls -lh test_outputs/input_*.png
```

**需要的影像**:
- ✅ `input_blue_sky_scene.png` (藍天)
- ✅ `input_gray_card_50.png` (50% 灰階)
- ✅ `input_pure_red/green/blue.png` (純色)

#### 1.2 如缺失，生成測試影像
```python
# 生成腳本: scripts/generate_test_images.py
import numpy as np
import cv2

# 藍天場景 (漸層 + 高光)
blue_sky = np.zeros((800, 1200, 3), dtype=np.uint8)
# ... (天空漸層 + 太陽高光)

# 50% 灰階卡
gray_card = np.full((800, 1200, 3), 128, dtype=np.uint8)

# 純色卡
red = np.zeros((800, 1200, 3), dtype=np.uint8)
red[:, :, 0] = 255  # 純紅
```

---

### Step 2: 生成對比圖 (1.5 小時)

#### 2.1 創建對比腳本
**檔案**: `scripts/compare_mie_vs_empirical.py`

```python
import cv2
import numpy as np
from film_models import get_film_profile
# ... (導入 Phos 處理函數)

def process_with_mode(input_image, use_mie=True):
    """使用指定模式處理影像"""
    profile = get_film_profile("Portra400")
    profile.wavelength_bloom_params.use_mie_lookup = use_mie
    
    # 處理影像（簡化流程，僅 wavelength bloom）
    # ... (調用 Phos 處理流程)
    
    return output_image

def generate_comparison(input_path, output_dir):
    """生成對比圖"""
    img = cv2.imread(input_path)
    
    # 經驗公式模式
    empirical = process_with_mode(img, use_mie=False)
    
    # Mie 查表模式
    mie = process_with_mode(img, use_mie=True)
    
    # 差異熱圖
    diff = np.abs(mie.astype(float) - empirical.astype(float))
    diff_norm = (diff / diff.max() * 255).astype(np.uint8)
    diff_heatmap = cv2.applyColorMap(diff_norm, cv2.COLORMAP_JET)
    
    # 並排拼接
    comparison = np.hstack([empirical, mie, diff_heatmap])
    
    # 保存
    cv2.imwrite(f"{output_dir}/comparison.png", comparison)
    
    return empirical, mie, diff
```

#### 2.2 批次生成對比圖
```bash
python3 scripts/compare_mie_vs_empirical.py \
  --input test_outputs/input_blue_sky_scene.png \
  --output tasks/TASK-009-psf-wavelength-theory/phase4_visual/

# 對 3 個場景分別運行
```

**輸出檔案** (每場景 3 張):
```
tasks/TASK-009-psf-wavelength-theory/phase4_visual/
├── blue_sky_empirical.png
├── blue_sky_mie.png
├── blue_sky_comparison.png (並排)
├── gray_card_empirical.png
├── gray_card_mie.png
├── gray_card_comparison.png
├── pure_colors_empirical.png
├── pure_colors_mie.png
└── pure_colors_comparison.png
```

---

### Step 3: 定量分析 (30 分鐘)

#### 3.1 計算指標
```python
# 添加到 compare_mie_vs_empirical.py

from skimage.metrics import structural_similarity as ssim

def analyze_metrics(empirical, mie):
    """計算 PSNR, SSIM, ΔE"""
    # PSNR
    mse = np.mean((empirical.astype(float) - mie.astype(float)) ** 2)
    psnr = 20 * np.log10(255.0 / np.sqrt(mse)) if mse > 0 else float('inf')
    
    # SSIM
    ssim_value = ssim(empirical, mie, multichannel=True, channel_axis=2)
    
    # ΔE (Lab 色差)
    lab1 = cv2.cvtColor(empirical, cv2.COLOR_BGR2LAB).astype(float)
    lab2 = cv2.cvtColor(mie, cv2.COLOR_BGR2LAB).astype(float)
    delta_e = np.sqrt(np.sum((lab1 - lab2) ** 2, axis=2)).mean()
    
    return {
        'psnr': psnr,
        'ssim': ssim_value,
        'delta_e': delta_e
    }
```

#### 3.2 生成指標報告
```python
# 輸出格式
metrics_report = {
    'blue_sky': {'psnr': 32.5, 'ssim': 0.92, 'delta_e': 4.2},
    'gray_card': {'psnr': 45.2, 'ssim': 0.98, 'delta_e': 1.1},
    'pure_colors': {'psnr': 28.3, 'ssim': 0.88, 'delta_e': 6.5}
}

# 保存為 JSON
with open('phase4_visual/metrics.json', 'w') as f:
    json.dump(metrics_report, f, indent=2)
```

---

### Step 4: 視覺評估 (30 分鐘)

#### 4.1 觀察對比圖
- 打開並排對比圖
- 檢查藍光 Bloom 減弱程度
- 評估色彩平衡

#### 4.2 填寫評估表
```markdown
### 場景 A: 藍天高光

**經驗公式**:
- 藍色光暈: ████████ (強)
- 整體觀感: 偏冷、藍光外溢

**Mie 查表**:
- 藍色光暈: ██ (弱)
- 整體觀感: 更溫暖、紅/黃光暈增強

**評分**:
- 真實感: Empirical 3/5, Mie 4/5
- 色彩平衡: Empirical 3/5, Mie 4/5
- 高光處理: Empirical 3/5, Mie 5/5
- 整體品質: Empirical 3/5, Mie 4/5
```

---

## 驗收標準

### 必達目標
- [ ] 生成 3 場景對比圖（共 9 張）
- [ ] 計算 PSNR/SSIM/ΔE 指標
- [ ] 完成視覺評估表
- [ ] 生成 `phase4_visual_verification.md` 報告

### 品質標準
- [ ] 對比圖清晰可辨（1200px 寬度以上）
- [ ] 定量指標完整記錄
- [ ] 視覺評估有理有據（非主觀臆測）
- [ ] 識別需要調整的參數（如 scatter_strength）

---

## 風險與緩解

### 風險 1: Streamlit 依賴問題
**描述**: Phos.py 依賴 Streamlit，無法直接腳本化

**緩解措施**:
- **方案 A**: 抽取核心處理函數（不依賴 Streamlit）
- **方案 B**: 使用現有測試影像（`test_outputs/`）
- **方案 C**: 手動運行 Streamlit UI 截圖（最後手段）

**選擇**: 方案 B（最快）+ 必要時方案 A

---

### 風險 2: 視覺差異過大
**描述**: 藍光 Bloom 減弱 93% 可能導致不自然

**緩解措施**:
- 記錄差異程度
- 建議調整 `scatter_strength` 參數
- 標記為「預期行為」而非 Bug

---

### 風險 3: 缺乏真實膠卷參考
**描述**: 無法確定哪個模型更接近真實 Portra400

**緩解措施**:
- 基於物理正確性（Mie 理論 > 經驗公式）
- 標記為「理論預期」
- 建議未來添加真實膠卷掃描對比

---

## 時間分配

| 步驟 | 任務 | 預估時間 |
|------|------|---------|
| 1 | 準備測試影像 | 30 分鐘 |
| 2 | 生成對比圖 | 1.5 小時 |
| 3 | 定量分析 | 30 分鐘 |
| 4 | 視覺評估 | 30 分鐘 |
| **總計** | | **3 小時** |

---

## 產出文件

```
tasks/TASK-009-psf-wavelength-theory/phase4_visual/
├── blue_sky_empirical.png
├── blue_sky_mie.png
├── blue_sky_comparison.png
├── gray_card_empirical.png
├── gray_card_mie.png
├── gray_card_comparison.png
├── pure_colors_empirical.png
├── pure_colors_mie.png
├── pure_colors_comparison.png
├── metrics.json
└── visual_assessment.md

tasks/TASK-009-psf-wavelength-theory/
└── phase4_visual_verification.md  (總結報告)
```

---

**設計完成時間**: 2025-12-24 00:00  
**開始執行**: 立即  
**預計完成**: 2025-12-24 03:00
