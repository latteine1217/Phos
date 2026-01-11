# v0.6.0 Breaking Changes

## 🚨 Removed Deprecated Functions

The following functions, deprecated in v0.5.0, have been removed:

### Grain Functions
- ❌ `generate_grain_for_channel()` → Use `generate_grain(lux, GrainParams(mode="artistic"), sens=sens)`
- ❌ `generate_poisson_grain()` → Use `generate_grain(lux, grain_params)`

### Bloom Functions  
- ❌ `apply_bloom_to_channel()` → Use `apply_bloom(lux, BloomParams(mode="artistic", ...))`
- ❌ `apply_bloom_conserved()` → Use `apply_bloom(lux, bloom_params)`

---

## 📦 Migration Guide

### Before (v0.5.x)
```python
# These still worked with deprecation warnings
noise = generate_grain_for_channel(lux, 0.5)
bloom = apply_bloom_to_channel(lux, sens, rads, strg, base, blur_scale, blur_sigma_scale)
```

### After (v0.6.0)
```python
from film_models import GrainParams, BloomParams

# Use unified interfaces
params = GrainParams(mode="artistic", intensity=0.18)
noise = generate_grain(lux, params, sens=0.5)

params = BloomParams(mode="artistic", sensitivity=sens, radius=rads, 
                      artistic_strength=strg, artistic_base=base)
bloom = apply_bloom(lux, params)
```

---

## 🔍 How to Check Your Code

Search for deprecated function usage:
```bash
rg "generate_grain_for_channel|generate_poisson_grain|apply_bloom_to_channel|apply_bloom_conserved" \
   --type py --glob '!tests*'
```

If found, follow migration guide above.

---

## 📊 Impact

- **Lines Removed**: ~154 lines of deprecated code
- **Functions Removed**: 4 deprecated wrappers
- **Tests Updated**: 7 call sites updated to use unified interfaces
- **Breaking Changes**: Only affects code still using old deprecated functions

---

## 🎯 Benefits

1. **Simpler API**: Single `generate_grain()` and `apply_bloom()` functions
2. **Better Type Safety**: All parameters in dataclasses (GrainParams, BloomParams)
3. **Less Code**: 154 fewer lines to maintain
4. **Cleaner Codebase**: Zero deprecated functions remaining

---

**Version**: v0.6.0  
**Date**: 2025-01-11  
**Deprecation Period**: ~2 months (v0.5.0 released November 2024)

---

## 🧹 v0.6.3 Code Cleanup (2025-01-12)

### Technical Debt Removal

**Removed obsolete comments from `film_models.py`**:
- ❌ Deleted 18 lines of outdated migration notes in `HalationParams` (lines 296-313)
- ❌ Removed reference to "will be removed in v0.4.0" (already v0.6.3)
- ✅ Preserved actual migration guide in `BREAKING_CHANGES_v06.md` (this file)

**Context**: 
The removed comments referenced v0.5.0 parameter migration (`transmittance_r/g/b` → `emulsion_transmittance_r/g/b`) which:
1. Was completed in v0.5.0 (2 versions ago)
2. Had proper migration guide in `docs/BREAKING_CHANGES_v05.md`
3. No longer needed inline duplication (Git history preserves details)

**Migration Guide for v0.5.0 Parameter Changes**:

If you still have old code using deprecated Halation parameters:

```python
# ❌ Old (v0.4.x and earlier)
HalationParams(
    transmittance_r=0.85,  # REMOVED
    transmittance_g=0.80,  # REMOVED
    transmittance_b=0.75,  # REMOVED
    ah_absorption=0.7      # REMOVED
)

# ✅ New (v0.5.0+, Beer-Lambert standard)
HalationParams(
    emulsion_transmittance_r=0.92,  # Single-pass, physically accurate
    emulsion_transmittance_g=0.87,
    emulsion_transmittance_b=0.78,
    ah_layer_transmittance_r=0.30,  # Replaces ah_absorption
    ah_layer_transmittance_g=0.10,
    ah_layer_transmittance_b=0.05,
    base_transmittance=0.98
)
```

**Conversion formula** (if migrating from v0.4.x):
```python
# Approximate conversion (assumes base_transmittance ≈ 0.98)
T_e ≈ sqrt(transmittance_old / 0.98²)
T_AH ≈ 1 - ah_absorption  # Linear approximation for small absorption
```

**Impact**:
- **Lines Removed**: 18 lines of redundant comments
- **File Size**: `film_models.py` reduced from 2612 → 2594 lines (-0.7%)
- **Readability**: Improved code-to-comment ratio
- **Tests**: ✅ All 59 tests in `test_film_profiles.py` pass
- **Breaking Changes**: None (only comment removal)

**Philosophy Alignment**:
> "能刪掉的程式碼，才是好設計" — Git 歷史已保留所有資訊，無需在程式碼中重複文檔。
