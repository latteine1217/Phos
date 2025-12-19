# Phase 1 設計文檔：參數結構與模式設計

## 修改點識別

### 1. 需要修改的核心函數
- `luminance()` → `spectral_response()` (Line 368-407)
- `apply_bloom_to_channel()` → 新增 `apply_bloom_conserved()` (Line 654-689)
- `combine_layers_for_channel()` → 需分離 H&D 曲線 (Line 692-723)
- `optical_processing()` → 需添加物理模式分支 (Line 726+)

### 2. 需要修改的資料結構（film_models.py）
- `EmulsionLayer`: 參數重命名
  - `r/g/b_absorption` → `r/g/b_response_weight`
  - `diffuse_light` → `diffuse_weight`
  - `direct_light` → `direct_weight`
- `ToneMappingParams`: 與 H&D 曲線分離
- 新增 `HDCurveParams`: H&D 曲線專用參數
- 新增 `PhysicsMode`: 模式枚舉
- 新增 `BloomMode`: Bloom 模式枚舉

---

## 新參數結構設計

### 1. PhysicsMode (Enum)

```python
from enum import Enum

class PhysicsMode(str, Enum):
    """物理模式枚舉"""
    ARTISTIC = "artistic"  # 藝術模式（預設，現有行為）
    PHYSICAL = "physical"  # 物理模式（能量守恆、H&D 曲線）
    HYBRID = "hybrid"      # 混合模式（可調整混合比例）
```

### 2. HDCurveParams (Dataclass)

```python
@dataclass
class HDCurveParams:
    """
    H&D 曲線參數（Hurter-Driffield Characteristic Curve）
    
    膠片的非線性響應特性，描述曝光量與光學密度的關係
    """
    enabled: bool = False  # 是否啟用 H&D 曲線
    gamma: float = 0.65    # 膠片對比度（負片: 0.6-0.7, 正片: 1.5-2.0）
    D_min: float = 0.1     # 最小密度（基底+霧度）
    D_max: float = 3.0     # 最大密度（動態範圍上限）
    
    # Toe（趾部，陰影區域的壓縮）
    toe_enabled: bool = True
    toe_end: float = 0.2    # 趾部結束點（相對曝光量）
    toe_strength: float = 0.3  # 趾部彎曲強度
    
    # Shoulder（肩部，高光區域的壓縮）
    shoulder_enabled: bool = True
    shoulder_start: float = 2.5  # 肩部開始點（相對曝光量）
    shoulder_strength: float = 0.2  # 肩部彎曲強度
```

### 3. BloomParams (Dataclass)

```python
@dataclass
class BloomParams:
    """
    Bloom/Halation 效果參數
    """
    mode: str = "artistic"  # "artistic" 或 "physical"
    
    # 共用參數
    sensitivity: float = 1.0      # 敏感度（控制效果強度）
    radius: int = 20              # 擴散半徑
    
    # Artistic 模式專用
    artistic_strength: float = 1.0  # 藝術模式強度
    artistic_base: float = 0.05     # 基礎擴散
    
    # Physical 模式專用
    threshold: float = 0.8          # 高光閾值（超過此值才散射）
    scattering_ratio: float = 0.1   # 散射比例（多少能量被散射）
    psf_type: str = "gaussian"      # PSF 類型（gaussian/exponential）
    energy_conservation: bool = True  # 強制能量守恆
```

### 4. GrainParams (Dataclass)

```python
@dataclass
class GrainParams:
    """
    顆粒噪聲參數
    """
    mode: str = "artistic"  # "artistic" 或 "poisson"
    intensity: float = 0.18  # 顆粒強度
    
    # Poisson 模式專用
    exposure_level: float = 1000.0  # 假設的光子計數（用於 Poisson 分布）
    grain_size: float = 1.0         # 銀鹽顆粒大小（微米）
    grain_density: float = 1.0      # 顆粒密度（相對值）
```

---

## 向後相容策略

### 策略 1：使用 Optional 與預設值

```python
@dataclass
class FilmProfile:
    """擴展後的 FilmProfile"""
    # === 現有欄位（保持不變）===
    name: str
    color_type: str
    sensitivity_factor: float
    red_layer: Optional[EmulsionLayer]
    green_layer: Optional[EmulsionLayer]
    blue_layer: Optional[EmulsionLayer]
    panchromatic_layer: EmulsionLayer
    tone_params: ToneMappingParams
    
    # === 新增欄位（有預設值，向後相容）===
    physics_mode: PhysicsMode = PhysicsMode.ARTISTIC
    hd_curve_params: Optional[HDCurveParams] = None
    bloom_params: Optional[BloomParams] = None
    grain_params: Optional[GrainParams] = None
    
    def __post_init__(self):
        """初始化預設值"""
        if self.hd_curve_params is None:
            self.hd_curve_params = HDCurveParams()
        if self.bloom_params is None:
            self.bloom_params = BloomParams()
        if self.grain_params is None:
            self.grain_params = GrainParams(intensity=self.panchromatic_layer.grain_intensity)
```

### 策略 2：參數遷移函數

```python
def migrate_legacy_params(film: FilmProfile) -> FilmProfile:
    """
    將舊版參數遷移到新版結構
    
    確保載入 v0.2.0 配置時不會報錯
    """
    # 如果缺少新參數，使用預設值
    if not hasattr(film, 'physics_mode'):
        film.physics_mode = PhysicsMode.ARTISTIC
    
    if not hasattr(film, 'hd_curve_params'):
        film.hd_curve_params = HDCurveParams()
    
    # 從現有參數推斷 BloomParams
    if not hasattr(film, 'bloom_params'):
        film.bloom_params = BloomParams(
            sensitivity=film.sensitivity_factor,
            mode="artistic"
        )
    
    return film
```

---

## 修改優先級與依賴關係

### Phase 2（能量守恆 Bloom）依賴：
- ✅ BloomParams 設計
- ✅ PhysicsMode enum
- ⏳ apply_bloom_conserved() 實作

### Phase 3（H&D 曲線）依賴：
- ✅ HDCurveParams 設計
- ⏳ apply_hd_curve() 實作
- ⏳ 與 tone mapping 分離

### Phase 4（Poisson 噪聲）依賴：
- ✅ GrainParams 設計
- ⏳ generate_poisson_grain() 實作

### Phase 5（重命名）可獨立進行：
- 不依賴其他 Phase
- 但會影響所有調用點
- 建議在 Phase 2-4 完成後統一重命名

---

## 實作順序建議

1. **先實作新資料結構**（film_models.py）
   - 添加 PhysicsMode, HDCurveParams, BloomParams, GrainParams
   - 擴展 FilmProfile（向後相容）
   - 測試：能否正常載入現有配置

2. **實作 Bloom 能量守恆**（Phos_0.2.0.py）
   - 新增 apply_bloom_conserved()
   - 修改 optical_processing() 添加模式分支
   - 測試：能量守恆驗證

3. **實作 H&D 曲線**（Phos_0.2.0.py）
   - 新增 apply_hd_curve()
   - 在 optical_processing() 中作為獨立階段
   - 測試：對數響應、toe/shoulder

4. **（可選）實作 Poisson 噪聲**
   - 新增 generate_poisson_grain()
   - 測試：與現有 grain 對比

5. **統一重命名**
   - 使用 IDE 批次重構
   - 更新所有文檔

---

**下一步**：開始實作新資料結構（film_models.py）

**預估時間**：1-2 小時（設計 + 實作 + 測試向後相容性）
