# TASK-014: 互易律失效 (Reciprocity Failure) 實作

**任務ID**: TASK-014  
**優先級**: P2-1 (Medium-High)  
**創建時間**: 2025-12-24  
**預估時間**: 3-5 hours  
**Physics Score 影響**: 8.7 → **9.0/10** (+0.3)

---

## 📋 任務目標

實作**互易律失效 (Reciprocity Failure)** 物理效應，模擬膠片在長曝光/短曝光時的非線性響應。

### 核心物理原理

**Schwarzschild 定律**: `E_eff = I·t^p`

- **正常曝光** (1/1000s - 1s): `p = 1.0` (線性響應)
- **長曝光** (> 1s): `p < 1.0` (需增加曝光補償)
- **極短曝光** (< 1/1000s): `p < 1.0` (高速攝影失效)

**物理原因**:
- 化學反應動力學非即時
- 潛影形成需時間累積
- 顯影過程中間產物濃度影響

---

## 🎯 驗收標準

### 1. 物理正確性
- ✅ 實作 Schwarzschild 定律 (`p` 參數可調)
- ✅ 長曝光 (10s) 補償 +1/3 - +1 EV
- ✅ 極短曝光 (1/10000s) 補償 +1/3 EV
- ✅ 正常範圍 (1/1000s - 1s) 無補償

### 2. 膠片特性差異
- ✅ 現代膠片 (T-Max, Delta): p ≈ 0.90-0.95
- ✅ 傳統膠片 (Tri-X, HP5): p ≈ 0.85-0.90
- ✅ 彩色膠片 (Portra, Ektar): 通道獨立 p 值

### 3. 測試覆蓋
- ✅ 單元測試: 10+ tests
- ✅ 整合測試: 3+ 膠片配置
- ✅ 視覺測試: 長曝光場景 (星空、瀑布)

### 4. 效能要求
- ✅ 計算開銷 < 5% (相對 v0.4.1 baseline)
- ✅ 記憶體無額外分配

---

## 📐 實作設計

### Phase 1: 物理模型設計 (1h)

#### 1.1 參數定義
```python
@dataclass
class ReciprocityFailureParams:
    """互易律失效參數"""
    
    # Schwarzschild 指數（波長相關，彩色膠片）
    p_red: float = 0.95      # 紅通道
    p_green: float = 0.90    # 綠通道
    p_blue: float = 0.85     # 藍通道
    
    # 或單一指數（黑白膠片）
    p_mono: Optional[float] = None
    
    # 臨界曝光時間（秒）
    t_critical_low: float = 0.001   # < 1ms 開始失效
    t_critical_high: float = 1.0    # > 1s 開始失效
    
    # 失效程度調節
    failure_strength: float = 1.0   # 0.0 = 無失效, 1.0 = 完全失效
```

#### 1.2 核心公式
```python
def apply_reciprocity_failure(
    intensity: np.ndarray,      # 影像強度 (0-1)
    exposure_time: float,       # 曝光時間（秒）
    params: ReciprocityFailureParams
) -> np.ndarray:
    """應用互易律失效效應"""
    
    # 計算 Schwarzschild 指數
    if exposure_time < params.t_critical_low:
        # 極短曝光失效
        p = 1.0 - (1.0 - 0.95) * params.failure_strength
    elif exposure_time > params.t_critical_high:
        # 長曝光失效（隨時間對數衰減）
        log_t = np.log10(exposure_time)
        p = 1.0 - (0.05 + 0.05 * log_t) * params.failure_strength
        p = np.clip(p, 0.75, 1.0)  # 限制範圍
    else:
        # 正常範圍，無失效
        p = 1.0
    
    # 應用 Schwarzschild 定律
    # E_eff = I·t^p
    # 正規化：保持 t=1s 時無影響
    effective_intensity = intensity * (exposure_time ** (p - 1.0))
    
    # 通道獨立處理（彩色膠片）
    if params.p_mono is None:
        # 分通道調整
        p_channels = np.array([params.p_red, params.p_green, params.p_blue])
        effective_intensity = intensity * (exposure_time ** (p_channels - 1.0))
    
    return np.clip(effective_intensity, 0, 1)
```

#### 1.3 曝光補償建議
```python
def calculate_exposure_compensation(
    exposure_time: float,
    params: ReciprocityFailureParams
) -> float:
    """計算需要的曝光補償（EV）"""
    
    if exposure_time <= 1.0:
        return 0.0  # 無需補償
    
    # 基於 p 值計算補償
    p = calculate_p_value(exposure_time, params)
    
    # 補償公式: EV_comp = log2(t^(1-p))
    compensation_ev = np.log2(exposure_time ** (1.0 - p))
    
    return compensation_ev

# 範例：
# 10s 曝光, p=0.90 → EV_comp = log2(10^0.1) ≈ +0.33 EV
# 60s 曝光, p=0.85 → EV_comp = log2(60^0.15) ≈ +1.0 EV
```

---

### Phase 2: 整合到現有流程 (1h)

#### 2.1 FilmProfile 擴展
```python
# film_models.py

@dataclass
class FilmProfile:
    """膠片配置檔案"""
    
    # 現有參數...
    halation_params: HalationParams
    wavelength_params: WavelengthBloomParams
    grain_params: GrainParams
    
    # 🆕 新增互易律失效參數
    reciprocity_params: Optional[ReciprocityFailureParams] = None
    
    def __post_init__(self):
        # 如未提供，使用預設值
        if self.reciprocity_params is None:
            self.reciprocity_params = ReciprocityFailureParams()
```

#### 2.2 Streamlit UI 整合
```python
# Phos.py - UI 控制

with st.sidebar.expander("⏱️ 互易律失效 (Reciprocity Failure)", expanded=False):
    enable_reciprocity = st.checkbox(
        "啟用互易律失效效應",
        value=False,
        help="模擬長曝光時的膠片非線性響應"
    )
    
    if enable_reciprocity:
        exposure_time = st.slider(
            "曝光時間 (秒)",
            min_value=0.0001,  # 1/10000s
            max_value=300.0,   # 5 分鐘
            value=1.0,
            step=0.1,
            format="%.4f s",
            help="模擬曝光時間（秒）"
        )
        
        # 顯示建議補償
        if exposure_time > 1.0:
            comp_ev = calculate_exposure_compensation(
                exposure_time,
                film_profile.reciprocity_params
            )
            st.info(f"💡 建議曝光補償: +{comp_ev:.2f} EV")
```

#### 2.3 處理流程插入點
```python
# Phos.py - 主處理流程

def process_image(image, film_profile, settings):
    """影像處理主流程"""
    
    # 1. RGB → Spectrum (如啟用 spectral)
    spectrum = rgb_to_spectrum(image)
    
    # 🆕 2. 應用互易律失效（在 H&D 曲線前）
    if settings.enable_reciprocity:
        spectrum = apply_reciprocity_failure(
            spectrum,
            settings.exposure_time,
            film_profile.reciprocity_params
        )
    
    # 3. 光譜響應
    response = apply_spectral_response(spectrum, film_profile)
    
    # 4. H&D 曲線
    response = apply_hd_curve(response, film_profile)
    
    # 5. Halation/Bloom/Grain
    # ...
```

---

### Phase 3: 真實膠片參數校準 (1h)

#### 3.1 參考數據來源

**文獻參考**:
1. **Kodak Technical Publication** (2007): 
   - *Reciprocity Characteristics of KODAK Films*
   - 提供 T-Max, Tri-X, Ektar, Portra 等膠片數據

2. **Ilford Datasheet**:
   - HP5 Plus, Delta 100/400
   - 提供曝光時間 vs 補償表格

3. **Fuji Technical Data**:
   - Velvia 50/100, Provia 100F
   - 已知 Velvia 長曝光失效嚴重

#### 3.2 膠片配置範例

```python
# film_models.py - 真實膠片配置

# 現代 T 型黑白膠片（低失效）
TMax400_Reciprocity = ReciprocityFailureParams(
    p_mono=0.95,             # 現代膠片失效小
    t_critical_high=10.0,    # 10s 以上才明顯
    failure_strength=0.7
)

# 傳統黑白膠片（中失效）
TriX400_Reciprocity = ReciprocityFailureParams(
    p_mono=0.88,
    t_critical_high=1.0,     # 1s 以上開始失效
    failure_strength=1.0
)

# 彩色負片（通道獨立）
Portra400_Reciprocity = ReciprocityFailureParams(
    p_red=0.95,              # 紅層較穩定
    p_green=0.90,
    p_blue=0.85,             # 藍層最敏感
    t_critical_high=1.0,
    failure_strength=0.8
)

# 正片（高失效）
Velvia50_Reciprocity = ReciprocityFailureParams(
    p_red=0.88,
    p_green=0.85,
    p_blue=0.82,             # Velvia 失效嚴重
    t_critical_high=0.5,     # 0.5s 以上開始
    failure_strength=1.0
)
```

#### 3.3 驗證方法

```python
# tests/test_reciprocity_failure.py

def test_exposure_compensation():
    """驗證曝光補償計算"""
    params = Portra400_Reciprocity
    
    # 10s 曝光應需 +0.3 ~ +0.5 EV 補償
    comp = calculate_exposure_compensation(10.0, params)
    assert 0.3 <= comp <= 0.5
    
    # 60s 曝光應需 +0.8 ~ +1.2 EV 補償
    comp = calculate_exposure_compensation(60.0, params)
    assert 0.8 <= comp <= 1.2

def test_reciprocity_monotonic():
    """驗證曝光時間越長，效果越弱（單調性）"""
    params = TriX400_Reciprocity
    intensity = np.ones((100, 100))
    
    result_1s = apply_reciprocity_failure(intensity, 1.0, params)
    result_10s = apply_reciprocity_failure(intensity, 10.0, params)
    result_60s = apply_reciprocity_failure(intensity, 60.0, params)
    
    # 長曝光應導致有效強度下降
    assert np.mean(result_1s) > np.mean(result_10s) > np.mean(result_60s)
```

---

### Phase 4: 測試與驗證 (1h)

#### 4.1 單元測試清單

```python
# tests/test_reciprocity_failure.py

class TestReciprocityFailure:
    """互易律失效測試套件"""
    
    def test_normal_range_no_effect(self):
        """正常曝光範圍 (0.001-1s) 應無影響"""
        params = ReciprocityFailureParams()
        intensity = np.ones((100, 100))
        
        for t in [0.001, 0.01, 0.1, 1.0]:
            result = apply_reciprocity_failure(intensity, t, params)
            np.testing.assert_allclose(result, intensity, rtol=1e-6)
    
    def test_long_exposure_darkening(self):
        """長曝光應導致變暗（需補償）"""
        params = ReciprocityFailureParams(p_mono=0.90)
        intensity = np.ones((100, 100)) * 0.5
        
        result = apply_reciprocity_failure(intensity, 10.0, params)
        
        # 有效強度應降低
        assert np.mean(result) < 0.5
        
        # 但不應降低超過 20%
        assert np.mean(result) > 0.4
    
    def test_channel_independence(self):
        """彩色膠片通道應獨立處理"""
        params = ReciprocityFailureParams(
            p_red=0.95,
            p_green=0.90,
            p_blue=0.85
        )
        intensity = np.ones((100, 100, 3)) * 0.5
        
        result = apply_reciprocity_failure(intensity, 10.0, params)
        
        # 藍通道衰減 > 綠通道 > 紅通道
        assert np.mean(result[:,:,2]) < np.mean(result[:,:,1]) < np.mean(result[:,:,0])
    
    def test_energy_conservation(self):
        """能量應守恆（僅重新分配，不新增）"""
        params = ReciprocityFailureParams(p_mono=0.90)
        intensity = np.random.rand(100, 100)
        
        result = apply_reciprocity_failure(intensity, 10.0, params)
        
        # 結果應在 [0, 1] 範圍內
        assert np.all(result >= 0)
        assert np.all(result <= 1)
    
    def test_schwarzschild_formula(self):
        """驗證 Schwarzschild 定律公式正確性"""
        params = ReciprocityFailureParams(p_mono=0.90)
        I = 0.5
        t = 10.0
        
        result = apply_reciprocity_failure(
            np.array([[I]]), t, params
        )[0, 0]
        
        # E_eff = I·t^(p-1) (正規化至 t=1)
        expected = I * (t ** (0.90 - 1.0))
        np.testing.assert_allclose(result, expected, rtol=1e-6)
```

#### 4.2 視覺驗證測試

```python
# scripts/test_reciprocity_visual.py

def test_long_exposure_scene():
    """視覺測試：長曝光星空場景"""
    
    # 創建測試場景（星空）
    scene = create_star_field(
        size=(1024, 1024),
        num_stars=100,
        brightness=0.8
    )
    
    # 測試不同曝光時間
    exposure_times = [1.0, 10.0, 30.0, 60.0, 120.0]
    
    for t in exposure_times:
        result = process_image(
            scene,
            film_profile=Portra400,
            exposure_time=t,
            enable_reciprocity=True
        )
        
        # 保存對比圖
        save_comparison(
            scene, result,
            f"test_outputs/reciprocity_t{t}s.png"
        )
    
    print("✅ 視覺測試完成，請檢查 test_outputs/")
```

---

## 🔍 已知限制與假設

### 限制 1: 簡化 Schwarzschild 模型
- **假設**: 單一 `p` 值描述整個失效曲線
- **現實**: 真實膠片可能有多段曲線（如 Ilford 資料表）
- **影響**: 極端曝光時間（> 300s）誤差可能較大

### 限制 2: 缺少溫度依賴
- **假設**: 室溫（20°C）條件
- **現實**: 低溫會加劇互易律失效
- **緩解**: 未來可新增溫度參數（P3 優先級）

### 限制 3: 無間歇曝光效應
- **假設**: 連續曝光
- **現實**: 間歇曝光（如閃光燈多次觸發）行為不同
- **影響**: 多重曝光、閃光攝影場景不適用

---

## 📊 Physics Score 影響分析

### 當前 (v0.4.1): 8.7/10

**分數構成**:
```
8.7/10 = 基礎 6.0 + 物理正確性 2.7
├─ Halation/Bloom (光學) +2.0
├─ H&D 曲線 (光化學) +2.0
├─ 光譜模型 +2.0
└─ 進階物理 +2.7
   ├─ Mie 散射 +0.8
   ├─ 波長依賴 PSF +0.6
   ├─ Beer-Lambert 標準化 +0.2
   ├─ 介質物理 +0.6
   ├─ 光譜靈敏度 +0.3
   └─ 能量守恆 +0.2
```

### TASK-014 完成後: 9.0/10 (+0.3)

**新增分數**:
```
9.0/10 = 基礎 6.0 + 物理正確性 3.0
└─ 進階物理 +3.0
   ├─ (現有) +2.7
   └─ 互易律失效 +0.3  ⬅️ 新增
      ├─ Schwarzschild 定律實作 +0.15
      ├─ 真實膠片參數校準 +0.10
      └─ 通道獨立處理 +0.05
```

**評分理由**:
- ✅ 實作經典物理定律（Schwarzschild 1900）
- ✅ 基於真實膠片數據校準
- ✅ 彩色膠片通道獨立處理
- ✅ 可驗證性高（曝光補償表格對比）

---

## 🎯 驗收檢查清單

### Phase 1: 設計 (1h)
- [ ] ReciprocityFailureParams 定義完成
- [ ] apply_reciprocity_failure() 實作完成
- [ ] 單元測試 10+ 項完成
- [ ] 物理公式推導文檔完成

### Phase 2: 整合 (1h)
- [ ] FilmProfile 擴展完成
- [ ] Streamlit UI 控制完成
- [ ] 主處理流程插入完成
- [ ] 效能影響 < 5%

### Phase 3: 校準 (1h)
- [ ] 5+ 膠片配置完成
- [ ] 參考文獻引用完整
- [ ] 曝光補償表格驗證通過

### Phase 4: 測試 (1h)
- [ ] 10+ 單元測試通過
- [ ] 3+ 視覺測試完成
- [ ] 能量守恆驗證通過
- [ ] 無回歸錯誤

### Phase 5: 文檔 (30min)
- [ ] decisions_log.md 更新 (Decision #039)
- [ ] PHYSICS_IMPROVEMENTS_ROADMAP.md 更新 (P2-1 完成)
- [ ] COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md 新增章節
- [ ] 完成報告創建

---

## 📚 參考資料

### 學術文獻
1. **Schwarzschild, K. (1900)**. *"On the Deviations from the Law of Reciprocity for Bromide of Silver Gelatine"*. Astrophysical Journal, 11, 89-91.

2. **Todd, H. N., & Zakia, R. D. (1974)**. *Photographic Sensitometry: The Study of Tone Reproduction*. Morgan & Morgan.

3. **Hunt, R. W. G. (2004)**. *The Reproduction of Colour* (6th ed.). Wiley. (Chapter 12: Photographic Systems)

### 廠商技術文件
1. **Kodak** (2007). *Reciprocity Characteristics of KODAK Films*. Publication CIS-61.
   - T-Max 100/400, Tri-X, Ektar, Portra 數據

2. **Ilford** (2023). *HP5 Plus / Delta 100/400 Technical Data*.
   - 曝光時間 vs 補償表格

3. **Fuji** (2018). *Velvia 50/100, Provia 100F Technical Information*.
   - 已知 Velvia 長曝光失效較嚴重

### 線上資源
1. **The Massive Dev Chart**: https://www.digitaltruth.com/devchart.php
   - 膠片特性資料庫

2. **Film Photography Project**: https://filmphotographyproject.com/
   - 真實使用者長曝光經驗

---

## 🚦 風險評估

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|-------|------|---------|
| 參數校準不準確 | MEDIUM | HIGH | 基於多份文獻交叉驗證 |
| 極端曝光時間誤差大 | HIGH | LOW | 文檔化適用範圍 (0.001s-300s) |
| 效能影響超標 | LOW | MEDIUM | 簡化計算，避免複雜分支 |
| 使用者困惑（新參數） | MEDIUM | LOW | 提供預設值與詳細說明 |

---

## ⏱️ 時間分配

| 階段 | 預估時間 | 實際時間 | 狀態 |
|------|---------|---------|------|
| Phase 1: 設計 | 1.0h | - | ⏳ Pending |
| Phase 2: 整合 | 1.0h | - | ⏳ Pending |
| Phase 3: 校準 | 1.0h | - | ⏳ Pending |
| Phase 4: 測試 | 1.0h | - | ⏳ Pending |
| Phase 5: 文檔 | 0.5h | - | ⏳ Pending |
| **總計** | **4.5h** | **-** | **-** |

---

## ✅ 完成標準

**TASK-014 被視為完成，當且僅當**:
1. ✅ 所有單元測試通過 (100%)
2. ✅ 3+ 視覺測試輸出正常
3. ✅ Physics Score 達到 9.0/10
4. ✅ 效能影響 < 5%
5. ✅ 文檔完整更新
6. ✅ 無破壞性變更（向後相容）

---

**任務創建**: 2025-12-24  
**負責 Agent**: Main Agent  
**下一步**: Phase 1 - 設計與實作
