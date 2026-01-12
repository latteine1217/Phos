# P1-2: Grain Strategy Pattern Refactoring Plan

## 目標
重構 `generate_grain()` 函數（~110 lines）使用 Strategy Pattern，消除條件分支。

---

## 📊 現狀分析

### Current Implementation
**Function**: `generate_grain()` (Phos.py:245-357, ~110 lines)

**Structure**:
```python
def generate_grain(lux_channel, grain_params, sens=None):
    mode = grain_params.mode
    
    if mode == "artistic":
        # 70 lines: 藝術模式（中間調顆粒）
        ...
    elif mode == "poisson":
        # 45 lines: 物理模式（Poisson 噪聲）
        ...
    else:
        raise ValueError(...)
```

**Complexity**:
- Total: ~110 lines
- Artistic mode: ~70 lines
- Poisson mode: ~45 lines
- Conditional branching: if-elif-else

**Callers**:
- `apply_grain()`: Wrapper function (RGB/BW dispatch)
  - Color film: calls 3x (R, G, B channels)
  - BW film: calls 1x (total channel)

---

## 🎯 Strategy Pattern Design

### New Structure

```
grain_strategies.py (new module)
├── GrainStrategy (abstract base class)
│   ├── apply(lux_channel, grain_params, sens) -> ndarray
│   └── validate_params(grain_params)
├── ArtisticGrainStrategy
│   └── apply(): 中間調權重 + 正負噪聲
├── PoissonGrainStrategy
│   └── apply(): Poisson 統計 + 銀鹽顆粒
├── get_grain_strategy(grain_params) -> GrainStrategy
└── generate_grain(lux_channel, grain_params, sens) -> ndarray (wrapper)
```

### Benefits
- **Good Taste**: Eliminate if-elif-else branching
- **Simplicity**: Each strategy <50 lines
- **Testability**: Independent unit tests per strategy
- **Extensibility**: Easy to add new grain modes (e.g., "spectral")

---

## 📋 Implementation Steps

### Phase 1: Create grain_strategies.py (~30 min)

#### Step 1.1: Define GrainStrategy Base Class
```python
from abc import ABC, abstractmethod
import numpy as np
from film_models import GrainParams

class GrainStrategy(ABC):
    """
    顆粒生成策略抽象基類
    
    每個策略代表一種顆粒生成方法：
    - Artistic: 視覺導向（中間調最明顯）
    - Poisson: 物理導向（光子計數統計）
    """
    
    @abstractmethod
    def apply(
        self, 
        lux_channel: np.ndarray, 
        grain_params: GrainParams,
        sens: Optional[float] = None
    ) -> np.ndarray:
        """
        應用顆粒效果
        
        Args:
            lux_channel: 光度通道 (0-1 範圍)
            grain_params: 顆粒參數
            sens: 敏感度（僅 artistic 模式使用）
            
        Returns:
            噪聲 ([-1, 1] 範圍)
        """
        pass
    
    def validate_params(self, grain_params: GrainParams) -> None:
        """驗證參數（子類可覆寫）"""
        pass
```

#### Step 1.2: Implement ArtisticGrainStrategy
```python
class ArtisticGrainStrategy(GrainStrategy):
    """
    藝術模式顆粒（視覺導向）
    
    物理假設：
        - 中間調顆粒最明顯（美學選擇）
        - 正負噪聲對稱（視覺平衡）
        - 輕微模糊（柔和質感）
    """
    
    def apply(self, lux_channel, grain_params, sens=None):
        if sens is None:
            raise ValueError("Artistic mode requires 'sens' parameter")
        
        # 複製原有邏輯（lines 292-309）
        ...
```

#### Step 1.3: Implement PoissonGrainStrategy
```python
class PoissonGrainStrategy(GrainStrategy):
    """
    Poisson 模式顆粒（物理導向）
    
    物理假設：
        - Poisson 統計（光子計數）
        - 暗部噪聲更明顯（σ ∝ √λ）
        - 銀鹽顆粒空間相關性
    """
    
    def apply(self, lux_channel, grain_params, sens=None):
        # 複製原有邏輯（lines 314-354）
        ...
```

#### Step 1.4: Factory Function
```python
def get_grain_strategy(grain_params: GrainParams) -> GrainStrategy:
    """
    工廠函數：根據模式選擇策略
    
    Args:
        grain_params: 顆粒參數（包含 mode）
        
    Returns:
        對應的策略實例
        
    Raises:
        ValueError: 未知的模式
    """
    mode = grain_params.mode
    
    if mode == "artistic":
        return ArtisticGrainStrategy()
    elif mode == "poisson":
        return PoissonGrainStrategy()
    else:
        raise ValueError(f"Unknown grain mode: {mode}")

def generate_grain(
    lux_channel: np.ndarray,
    grain_params: GrainParams,
    sens: Optional[float] = None
) -> np.ndarray:
    """
    統一介面（向後相容）
    
    委派給對應的策略類
    """
    strategy = get_grain_strategy(grain_params)
    return strategy.apply(lux_channel, grain_params, sens)
```

### Phase 2: Update Phos.py (~10 min)

#### Step 2.1: Add Import
```python
from grain_strategies import generate_grain
```

#### Step 2.2: Remove Original Implementation
Delete lines 245-357 (`generate_grain()` definition)

#### Step 2.3: Keep apply_grain() Unchanged
No changes needed - it already calls `generate_grain()`

### Phase 3: Create Tests (~40 min)

#### Test File: `tests_refactored/test_grain_strategies.py`

**Test Coverage**:
1. **Strategy Initialization** (2 tests)
   - Artistic strategy creation
   - Poisson strategy creation

2. **Artistic Mode** (5 tests)
   - Mid-tone weighting (weights highest at 0.5)
   - Sens parameter requirement (ValueError if missing)
   - Output range ([-1, 1])
   - Blur smoothing (variance reduction)
   - Deterministic with seed

3. **Poisson Mode** (5 tests)
   - Dark area has more noise (σ ∝ √λ)
   - Bright area has less relative noise
   - Output range ([-1, 1])
   - Grain size effect (larger size → smoother)
   - Sens parameter ignored (no effect)

4. **Factory Function** (3 tests)
   - Returns correct strategy for "artistic"
   - Returns correct strategy for "poisson"
   - Raises ValueError for unknown mode

5. **Unified Interface** (2 tests)
   - generate_grain() delegates correctly
   - Backward compatibility with old code

6. **Edge Cases** (3 tests)
   - Zero image (all black)
   - Saturated image (all white)
   - Single pixel

**Total**: 20 tests

### Phase 4: Validation (~10 min)

```bash
# Run new tests
pytest tests_refactored/test_grain_strategies.py -v

# Run all tests (regression)
pytest tests_refactored/ -v

# Check coverage
pytest --cov=grain_strategies --cov-report=term tests_refactored/test_grain_strategies.py
```

### Phase 5: Documentation & Commit (~10 min)

#### Update Files:
- `CHANGELOG.md`: Add Grain Strategy Pattern section
- `Phos.py`: Update imports
- `README.md`: Mention grain_strategies (if needed)

#### Commit Message:
```
refactor(v0.6.4): decompose generate_grain() into Strategy Pattern

**P1-2 Task Complete**: Grain Strategy Pattern Refactoring

**What Changed**:
- Refactored generate_grain() (110 lines → 2 strategies)
- Created grain_strategies.py module (350+ lines)
- Artistic mode: ~40 lines (mid-tone weighting)
- Poisson mode: ~40 lines (light statistics)
- Factory pattern: eliminate if-elif-else

**New Module**: grain_strategies.py
- GrainStrategy (abstract base class)
- ArtisticGrainStrategy (visual-oriented)
- PoissonGrainStrategy (physics-based)
- get_grain_strategy() (factory)
- generate_grain() (unified interface)

**Tests**: 20 tests, 100% pass
- Strategy behavior
- Mode-specific physics
- Factory dispatch
- Edge cases

**Benefits**:
- Code reduction: 110 → 10 lines (wrapper)
- Each strategy <50 lines
- Independent testability
- Easy to extend (new modes)

**Breaking**: None (API unchanged)
**Philosophy**: Good Taste + Simplicity ✅

Ref: bloom_strategies.py (template)
```

---

## 📊 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| generate_grain() reduction | >90% | TBD |
| Strategy line count | <50 lines each | TBD |
| Test coverage | 100% | TBD |
| Tests passing | 100% | TBD |
| Backward compatibility | 100% | TBD |
| Regression tests | >95% pass | TBD |

---

## ⏰ Timeline

- **Phase 1**: Create grain_strategies.py (30 min)
- **Phase 2**: Update Phos.py (10 min)
- **Phase 3**: Create tests (40 min)
- **Phase 4**: Validation (10 min)
- **Phase 5**: Documentation & Commit (10 min)
- **Total**: ~100 minutes (1.5 hours)

---

## 🔗 References

- **Template**: `bloom_strategies.py` (P0-1 完成)
- **Philosophy**: AGENTS.md Lesson 8 (Strategy Pattern)
- **Deprecation**: P1-1 (deprecated decorator已準備好)

---

**Created**: 2026-01-12  
**Status**: Planning Complete  
**Next Step**: Execute Phase 1 (Create grain_strategies.py)
