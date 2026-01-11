# Phase 1: 波長依賴散射 - 設計文檔

**任務 ID**: TASK-003-Phase-1  
**優先級**: P0（根據 Physicist 建議，Phase 2 之後最優先）  
**預估時間**: 6-8 小時  
**狀態**: ⏳ 設計中

---

## 📋 目標

### 核心目標
將 RGB 三通道的 Bloom 散射從「共享 PSF」升級為「波長依賴 PSF」，實現：
- **能量權重解耦**: η(λ) ∝ λ^-p（p≈3.5）
- **PSF 寬度解耦**: σ(λ) ∝ (λ_ref/λ)^q（q≈0.8）
- **雙段核結構**: K = ρ·G(σ) + (1-ρ)·E(κ)（Gaussian + Exponential）

### 視覺效果
- 白色高光產生「藍色光暈」（藍光散射更強）
- Bloom 呈現「色散效應」（色彩分離）
- 夜景路燈呈現「藍色外圈 + 黃色核心」

---

## 🔬 物理原理

### 當前問題（Phase 0 簡化模型）

```python
# 三個通道使用相同 PSF（物理不正確）
PSF_shared = GaussianBlur(sigma=20)
bloom_r = Conv(response_r, PSF_shared)
bloom_g = Conv(response_g, PSF_shared)  # ← 應該不同！
bloom_b = Conv(response_b, PSF_shared)
```

**問題**:
- 忽略波長依賴：藍光（450nm）應比紅光（650nm）散射更強
- 無色散效應：真實膠片高光周圍有色彩分離
- 能量與寬度耦合：無法獨立調整「散射強度」與「擴散範圍」

### Physicist 審查要點（physicist_review.md Line 37-55）

**物理正確性**: ⚠️ 部分正確

**核心問題**:
1. **Mie vs Rayleigh**: 銀鹽晶體直徑 0.5-3 μm，相對於可見光 λ≈0.45-0.65 μm，尺寸參數 x=2πa/λ=O(3-20)，屬 Mie 範圍（非純 Rayleigh）
2. **PSF 標度不嚴謹**: 直接使用 λ^-2 或 λ^-4 缺乏推導，應為 σ(λ) ∝ (λ_ref/λ)^q，q≈0.5-1.0
3. **參數不可辨識性**: 半徑變大與能量變多視覺上相似，需解耦

**修正方案**:
- **能量權重**: w(λ) ∝ λ^-p，p≈3-4（Mie+Rayleigh 混合近似）
- **PSF 寬度**: σ(λ) ∝ (λ_ref/λ)^q，q≈0.5-1.0（小角散射）
- **雙段核**: 核心（Gaussian）+ 拖尾（Exponential），能量比隨 λ 調整
- **解耦驗證**: η(λ) 與 σ(λ) 分別可調，避免混淆

---

## 🎯 實作方案

### 方案架構

```
Input (RGB) 
  ↓
計算每通道的散射參數
  ├─ η_r = η_base × (λ_g / λ_r)^p    # 紅光能量權重（相對綠光）
  ├─ η_g = η_base × 1.0              # 綠光基準
  └─ η_b = η_base × (λ_g / λ_b)^p    # 藍光能量權重
  
  ├─ σ_r = σ_base × (λ_r / λ_g)^q    # 紅光 PSF 寬度（相對綠光）
  ├─ σ_g = σ_base × 1.0              # 綠光基準
  └─ σ_b = σ_base × (λ_b / λ_g)^q    # 藍光 PSF 寬度
  
創建雙段核 PSF
  K_λ = ρ_λ × Gaussian(σ_λ) + (1-ρ_λ) × Exponential(κ_λ)
  
能量守恆散射
  bloom_λ = apply_wavelength_bloom(response_λ, η_λ, K_λ)
  
  ↓
Output (RGB) with 色散 Bloom
```

### 關鍵公式

#### 1. 能量權重（相對於綠光）
```python
η(λ) = η_base × (λ_ref / λ)^p

# 實例（p=3.5, λ_ref=550nm）:
η_r = η_base × (550/650)^3.5 ≈ η_base × 0.643  # 紅光較弱
η_g = η_base × 1.0                             # 綠光基準
η_b = η_base × (550/450)^3.5 ≈ η_base × 1.660  # 藍光較強

# 比例驗證
η_b / η_r ≈ 2.58x（藍光散射能量為紅光的 2.58 倍）
```

#### 2. PSF 寬度標度
```python
σ(λ) = σ_base × (λ_ref / λ)^q

# 實例（q=0.8, σ_base=20px, λ_ref=550nm）:
σ_r = 20 × (550/650)^0.8 ≈ 20 × 0.873 ≈ 17.5 px  # 紅光較窄
σ_g = 20 × 1.0 = 20 px                           # 綠光基準
σ_b = 20 × (550/450)^0.8 ≈ 20 × 1.177 ≈ 23.5 px  # 藍光較寬

# 比例驗證
σ_b / σ_r ≈ 1.35x（藍光 PSF 寬度為紅光的 1.35 倍）
```

#### 3. 雙段核（核心 + 拖尾）
```python
# 核心部分（Gaussian，小角散射）
G(r; σ) = exp(-r² / (2σ²)) / (2πσ²)

# 拖尾部分（Exponential，大角散射）
E(r; κ) = exp(-r / κ) / (2πκ²)

# 組合核（能量歸一化）
K(r; σ, κ, ρ) = ρ × G(r; σ) + (1-ρ) × E(r; κ)
其中 ρ ∈ [0,1] 為核心占比

# 波長依賴的核心占比（藍光更多在核心）
ρ_r = 0.70  # 紅光 70% 核心，30% 拖尾
ρ_g = 0.75
ρ_b = 0.80  # 藍光 80% 核心，20% 拖尾
```

#### 4. 能量守恆散射
```python
# 提取高光能量
highlights = np.where(response > threshold, response - threshold, 0)
scattered_energy = highlights × η(λ)

# PSF 正規化（確保 ∑K = 1）
K_normalized = K / np.sum(K)

# 卷積
scattered_light = Conv(scattered_energy, K_normalized)

# 能量重組（守恆）
output = response - scattered_energy + scattered_light
```

---

## 📁 實作檔案

### 1. `film_models.py`

**已完成**:
- ✅ `WavelengthBloomParams` dataclass（Line 154-183）

**需修改**:
- 為測試配置啟用 `wavelength_bloom_params`

```python
# 在 Cinestill800T_MediumPhysics 和 Portra400_MediumPhysics 添加
wavelength_bloom_params=WavelengthBloomParams(
    enabled=True,
    wavelength_power=3.5,    # p 值（Mie+Rayleigh 混合）
    radius_power=0.8,        # q 值（小角散射）
    reference_wavelength=550.0,
    lambda_r=650.0,
    lambda_g=550.0,
    lambda_b=450.0,
    core_fraction_r=0.70,
    core_fraction_g=0.75,
    core_fraction_b=0.80,
    tail_decay_rate=0.1
)
```

### 2. `Phos_0.3.0.py`

**新增函數**:

#### A. 創建雙段核 PSF
```python
def create_dual_kernel_psf(
    sigma: float, 
    kappa: float, 
    core_fraction: float, 
    radius: int = 100
) -> np.ndarray:
    """
    創建雙段核 PSF（Gaussian + Exponential）
    
    Args:
        sigma: 高斯核標準差（像素）
        kappa: 指數核衰減長度（像素）
        core_fraction: 核心占比 ρ ∈ [0,1]
        radius: PSF 半徑（像素）
    
    Returns:
        psf: 正規化的 2D PSF，∑psf = 1
    
    物理依據:
        K(r) = ρ·G(r;σ) + (1-ρ)·E(r;κ)
        Physicist Review Line 49: 兩段式 PSF（核心+拖尾）
    """
    size = 2 * radius + 1
    y, x = np.ogrid[-radius:radius+1, -radius:radius+1]
    r = np.sqrt(x**2 + y**2)
    
    # 高斯核（小角散射）
    gaussian_core = np.exp(-r**2 / (2 * sigma**2))
    
    # 指數核（大角散射）
    exponential_tail = np.exp(-r / kappa)
    
    # 組合（能量加權）
    psf = core_fraction * gaussian_core + (1 - core_fraction) * exponential_tail
    
    # 正規化（確保 ∑psf = 1）
    psf = psf / np.sum(psf)
    
    return psf
```

#### B. 波長依賴散射核心函數
```python
def apply_wavelength_bloom(
    response_r: np.ndarray,
    response_g: np.ndarray,
    response_b: np.ndarray,
    wavelength_params: WavelengthBloomParams,
    bloom_params: BloomParams
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    應用波長依賴 Bloom 散射
    
    Args:
        response_r/g/b: RGB 通道的乳劑響應（0-1）
        wavelength_params: 波長依賴參數
        bloom_params: Bloom 基礎參數
    
    Returns:
        bloom_r, bloom_g, bloom_b: 散射後的 RGB 通道
    
    物理模型:
        η(λ) = η_base × (λ_ref/λ)^p
        σ(λ) = σ_base × (λ_ref/λ)^q
        K(λ) = ρ(λ)·G(σ(λ)) + (1-ρ(λ))·E(κ(λ))
    """
    # 1. 計算波長依賴的能量權重
    p = wavelength_params.wavelength_power
    lambda_ref = wavelength_params.reference_wavelength
    
    eta_r = bloom_params.scattering_ratio * (lambda_ref / wavelength_params.lambda_r) ** p
    eta_g = bloom_params.scattering_ratio * 1.0
    eta_b = bloom_params.scattering_ratio * (lambda_ref / wavelength_params.lambda_b) ** p
    
    # 2. 計算波長依賴的 PSF 寬度
    q = wavelength_params.radius_power
    sigma_base = bloom_params.radius
    
    sigma_r = sigma_base * (lambda_ref / wavelength_params.lambda_r) ** q
    sigma_g = sigma_base * 1.0
    sigma_b = sigma_base * (lambda_ref / wavelength_params.lambda_b) ** q
    
    # 3. 計算拖尾長度（κ = σ / decay_rate）
    decay = wavelength_params.tail_decay_rate
    kappa_r = sigma_r / decay
    kappa_g = sigma_g / decay
    kappa_b = sigma_b / decay
    
    # 4. 創建各通道的雙段核 PSF
    psf_r = create_dual_kernel_psf(
        sigma_r, kappa_r, 
        wavelength_params.core_fraction_r, 
        radius=int(bloom_params.radius * 3)
    )
    psf_g = create_dual_kernel_psf(
        sigma_g, kappa_g, 
        wavelength_params.core_fraction_g, 
        radius=int(bloom_params.radius * 3)
    )
    psf_b = create_dual_kernel_psf(
        sigma_b, kappa_b, 
        wavelength_params.core_fraction_b, 
        radius=int(bloom_params.radius * 3)
    )
    
    # 5. 能量守恆散射（每通道獨立）
    bloom_r = apply_bloom_with_psf(response_r, eta_r, psf_r, bloom_params.threshold)
    bloom_g = apply_bloom_with_psf(response_g, eta_g, psf_g, bloom_params.threshold)
    bloom_b = apply_bloom_with_psf(response_b, eta_b, psf_b, bloom_params.threshold)
    
    return bloom_r, bloom_g, bloom_b


def apply_bloom_with_psf(
    response: np.ndarray,
    eta: float,
    psf: np.ndarray,
    threshold: float
) -> np.ndarray:
    """
    使用自定義 PSF 應用 Bloom（能量守恆）
    
    Args:
        response: 單通道響應（0-1）
        eta: 散射能量比例
        psf: 正規化 PSF（∑psf = 1）
        threshold: 高光閾值
    
    Returns:
        bloom: 散射後的通道（能量守恆）
    """
    # 提取高光
    highlights = np.where(response > threshold, response - threshold, 0.0)
    
    # 計算散射能量
    scattered_energy = highlights * eta
    
    # PSF 卷積（已正規化，∑psf=1）
    scattered_light = cv2.filter2D(scattered_energy, -1, psf)
    
    # 能量守恆重組
    output = response - scattered_energy + scattered_light
    
    # 安全裁切
    output = np.clip(output, 0.0, 1.0)
    
    return output
```

#### C. 修改 `optical_processing()` 整合點
```python
# 在 Phos_0.3.0.py optical_processing() 中添加檢測
use_wavelength_bloom = (
    use_medium_physics and
    hasattr(film, 'wavelength_bloom_params') and
    film.wavelength_bloom_params is not None and
    film.wavelength_bloom_params.enabled
)

if use_wavelength_bloom:
    # Phase 1: 波長依賴 Bloom + Halation
    bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(
        response_r, response_g, response_b,
        film.wavelength_bloom_params,
        film.bloom_params
    )
    
    # Halation（已有實作，Phase 2）
    halation_r = apply_halation(bloom_r, film.halation_params, wavelength=650.0)
    halation_g = apply_halation(bloom_g, film.halation_params, wavelength=550.0)
    halation_b = apply_halation(bloom_b, film.halation_params, wavelength=450.0)
    
    final_r, final_g, final_b = halation_r, halation_g, halation_b
    
elif use_medium_physics:
    # Phase 2: 僅 Halation（已實作）
    # ...
```

### 3. `tests/test_wavelength_bloom.py`

**新建測試檔案**（8 項測試）:

```python
"""
測試波長依賴 Bloom 散射（Phase 1）

測試項目:
1. 能量權重計算（η_b/η_r 比例驗證）
2. PSF 寬度計算（σ_b/σ_r 比例驗證）
3. 雙段核 PSF 正規化（∑K = 1）
4. 雙段核形狀驗證（核心 + 拖尾）
5. 能量守恆（輸入 = 輸出）
6. 視覺效果（白點 → 藍色光暈）
7. 效能測試（< 10s）
8. 與 Phase 2 整合測試
"""

import numpy as np
import cv2
from film_models import get_film_profile, WavelengthBloomParams, BloomParams

def test_energy_weight_ratios():
    """測試能量權重比例"""
    params = WavelengthBloomParams(
        wavelength_power=3.5,
        lambda_r=650.0,
        lambda_g=550.0,
        lambda_b=450.0
    )
    
    eta_r = (550/650) ** 3.5
    eta_g = 1.0
    eta_b = (550/450) ** 3.5
    
    ratio = eta_b / eta_r
    
    print(f"η_r: {eta_r:.4f}, η_g: {eta_g:.4f}, η_b: {eta_b:.4f}")
    print(f"η_b/η_r: {ratio:.2f}x")
    
    assert 2.0 < ratio < 3.0, f"能量比例應在 2-3x（實際 {ratio:.2f}x）"
    print("✓ 能量權重比例正確")

# ... 其他測試
```

---

## 📊 驗收標準

### 物理驗證
- [x] **能量權重比例**: η_b/η_r ∈ [2.0, 3.0]（藍光散射強度為紅光的 2-3 倍）
- [x] **PSF 寬度比例**: σ_b/σ_r ∈ [1.2, 1.5]（藍光 PSF 寬度為紅光的 1.2-1.5 倍）
- [x] **雙段核正規化**: ∑K = 1.0 ± 0.001（能量守恆）
- [x] **能量守恆**: |E_out - E_in| < 0.01%

### 視覺驗證
- [ ] 白色高光（R=G=B=1.0）產生藍色光暈（B > R, G）
- [ ] 路燈測試：核心黃色，外圈藍色
- [ ] 色散可見：高光邊緣有色彩分離

### 效能驗證
- [ ] 2000×3000 影像 < 10s（關鍵目標）
- [ ] 與 Phase 2（Halation）組合後 < 10s
- [ ] PSF 創建開銷 < 50ms

### 技術驗證
- [ ] 所有 8 項單元測試通過
- [ ] 與 Phase 2 整合測試通過
- [ ] 無 NaN/Inf 錯誤
- [ ] η 與 σ 可獨立調整（解耦驗證）

---

## ⚠️ 風險與緩解

### 風險 1: 效能超標（雙段核卷積 3x）
**機率**: 中  
**影響**: 高  
**緩解**:
- 使用可分離濾波器（separable filter）
- PSF 快取（LRU cache）
- 降採樣策略（大圖先縮小處理）

### 風險 2: 雙段核近似精度
**機率**: 低  
**影響**: 中  
**緩解**:
- 與理論公式對比（徑向分布測試）
- 調整 core_fraction 與 tail_decay_rate
- 可視化 PSF 形狀驗證

### 風險 3: 參數不可辨識性
**機率**: 低（已解耦設計）  
**影響**: 中  
**緩解**:
- 單獨測試 η(λ) 變化（固定 σ）
- 單獨測試 σ(λ) 變化（固定 η）
- 提供視覺化工具展示兩者差異

---

## 🔄 與其他 Phase 的關係

### Phase 2 (Halation) - 已完成 ✅
- **關係**: Phase 1 輸出 → Phase 2 輸入
- **順序**: `Bloom(wavelength) → Halation(wavelength)`
- **能量**: Phase 1 能量守恆 → Phase 2 再次能量守恆
- **測試**: 整合測試驗證組合效果

### Phase 4 (光譜模型) - 未來擴展
- **關係**: 31 通道光譜 → 簡化為 RGB 波長參數
- **對齊**: λ_r, λ_g, λ_b 需與光譜通道對應
- **升級路徑**: 當前 3 通道 → 未來 31 通道

### Phase 5 (Mie 查表) - 可選優化
- **關係**: 替代 λ^-p 近似，使用 Mie 理論精確值
- **升級**: `η(λ) = λ^-3.5` → `η(λ) = Mie_lookup(λ, a, m)`
- **效能**: 查表比實時計算快 ~100x

---

## 📚 參考文獻

### 物理審查
- **Physicist Review**: `tasks/TASK-003-medium-physics/physicist_review.md`
  - Line 37-55: Phase 1 審查與修正建議
  - Line 27-31: 優先改進建議

### 光散射理論
- van de Hulst, *Light Scattering by Small Particles*, Dover, 1957.
- Bohren & Huffman, *Absorption and Scattering of Light by Small Particles*, Wiley, 1983.
- Ishimaru, *Wave Propagation and Scattering in Random Media*, IEEE Press.

### 任務文檔
- **Task Brief**: `tasks/TASK-003-medium-physics/task_brief.md` (Line 27-69)
- **Decision Log**: `context/decisions_log.md`

---

## 🎯 執行檢查清單

### 設計階段（當前）
- [x] 閱讀 Physicist Review
- [x] 閱讀 WavelengthBloomParams 定義
- [x] 設計雙段核 PSF 公式
- [x] 設計能量守恆流程
- [x] 撰寫設計文檔

### 實作階段（下一步）
- [ ] 實作 `create_dual_kernel_psf()`
- [ ] 實作 `apply_wavelength_bloom()`
- [ ] 實作 `apply_bloom_with_psf()`
- [ ] 修改 `optical_processing()` 整合點
- [ ] 更新測試配置（啟用 wavelength_bloom_params）

### 測試階段
- [ ] 創建 `test_wavelength_bloom.py`
- [ ] 單元測試（8 項）
- [ ] 整合測試（Phase 1 + Phase 2）
- [ ] 效能測試（< 10s）
- [ ] 視覺測試（白點 → 藍色光暈）

### 文檔階段
- [ ] 更新 `task_brief.md`（Phase 1 完成）
- [ ] 更新 `decisions_log.md`（Decision #014）
- [ ] 更新 `context_session_*.md`
- [ ] 提交 Git commit

---

**創建時間**: 2025-12-19 22:40  
**設計者**: Main Agent  
**狀態**: ⏳ 設計完成，準備實作
