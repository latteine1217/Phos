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
