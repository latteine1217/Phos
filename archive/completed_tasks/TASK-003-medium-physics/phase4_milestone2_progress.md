# Phase 4 Milestone 2 Progress Report

**Date**: 2025-12-22  
**Status**: 75% Complete (Core Functions Implemented, Roundtrip Issues Remaining)

## ✅ Completed Tasks

### 1. Core Function Implementation
All three core spectral conversion functions have been successfully implemented in `phos_core.py`:

#### ✅ `rgb_to_spectrum()`
- **Location**: `phos_core.py` Line 460-545
- **Algorithm**: Smits (1999) basis vector interpolation
- **Status**: **Working correctly** for primary colors
- **Test Results**:
  - RGB(1,0,0) → Red basis ✅
  - RGB(0,1,0) → Green basis ✅
  - RGB(0,0,1) → Blue basis ✅
  - RGB(1,1,1) → White basis ✅
  - RGB(0,0,0) → Zero spectrum ✅
- **Known Issues**: 
  - Performance: 15s for 2000×3000 image (target <2s) ❌
  - Needs vectorization optimization

#### ✅ `spectrum_to_xyz()`
- **Location**: `phos_core.py` Line 548-605
- **Algorithm**: CIE 1931 spectral integration with D65 illuminant
- **Status**: Working, but normalization needs refinement
- **Test Results**:
  - White spectrum → XYZ ✅
  - Image spectrum → XYZ ✅
  - Custom illuminant support ✅

#### ✅ `xyz_to_srgb()`
- **Location**: `phos_core.py` Line 608-660
- **Algorithm**: IEC 61966-2-1:1999 (sRGB standard) with gamma correction
- **Status**: Working correctly
- **Test Results**:
  - D65 white point → RGB(1,1,1) ✅
  - Value clipping ✅
  - Image conversion ✅

### 2. Data Loading Functions
All helper functions implemented and tested:

- ✅ `load_smits_basis()` - Cached Smits basis vectors
- ✅ `load_cie_1931()` - CIE 1931 color matching functions  
- ✅ `get_illuminant_d65()` - D65 daylight spectrum (6504K)

### 3. Test Suite Created
- **File**: `tests/test_spectral_model.py` (410 lines)
- **Test Coverage**: 22 tests
- **Current Pass Rate**: 17/22 (77%)

## ⚠️ Remaining Issues

### Issue #1: Roundtrip Consistency (High Priority)
**Problem**: RGB → Spectrum → XYZ → RGB往返後，灰階值和某些顏色有誤差

**Current Status**:
- White RGB(1,1,1): Error 7% on blue channel ❌
- Gray RGB(0.25,0.25,0.25): Recovered as RGB(0.56,0.54,0.50) (124% brighter) ❌
- Primary colors: Perfect roundtrip ✅

**Root Cause Analysis**:
The issue is in the XYZ normalization strategy. Two competing requirements:
1. **Absolute luminance preservation**: Gray values should maintain relative brightness
2. **White point normalization**: RGB(1,1,1) should map to D65 white point XYZ=(0.95,1.0,1.09)

**Attempted Solutions**:
1. ❌ No normalization → Gray values become overexposed
2. ❌ Y_max normalization → Breaks color balance (blue channel shifts)
3. ❌ Y_white normalization → Gray values become brighter

**Next Steps**:
1. Review CIE XYZ→RGB conversion matrix (check if D65 white point is correctly encoded)
2. Verify sRGB gamma correction implementation
3. Consider separating "colorimetric XYZ" (absolute) from "display XYZ" (relative to white point)
4. Reference: Check if we need CIE XYZ → sRGB adaptation (chromatic adaptation transform)

**Possible Solution**:
The XYZ→RGB matrix assumes XYZ is already normalized such that the white point Y=1. But our integration produces Y≈114 for white. We need to normalize by the illuminant's Y value, not the scene's Y_max.

Current normalization:
```python
Y_white = sum(illuminant * y_bar * delta_lambda)  # = 113.8
xyz = xyz / Y_white
```

This makes white surface → Y=1, but breaks gray value linearity. 

**Correct approach**: The issue might be in `xyz_to_srgb()`. The transformation matrix expects Y=1 for white, but we're feeding it Y=0.25 for 25% gray, which after gamma correction becomes √0.25 ≈ 0.56 (too bright).

**ACTION REQUIRED**: Investigate if the issue is in gamma correction, not normalization.

### Issue #2: Performance (Medium Priority)
**Problem**: `rgb_to_spectrum()` is too slow

**Benchmark**:
- Current: 15.0s for 2000×3000 image
- Target: <2.0s (8x speedup needed)

**Root Cause**:
Heavy use of `np.where()` and boolean indexing in Smits algorithm creates multiple array copies.

**Optimization Strategies**:
1. **Vectorize mask operations**: Pre-compute all masks, then apply in single pass
2. **Remove redundant operations**: Avoid repeated `r[mask_b_min, None]` indexing
3. **Use einsum**: Replace manual broadcasting with optimized `einsum`
4. **JIT compilation**: Use Numba `@jit` decorator
5. **Lookup table (LUT)**: Pre-compute 256×256×256 RGB→Spectrum table (~2GB memory)

**Next Steps**:
1. Profile with `cProfile` to identify bottleneck
2. Implement vectorized version without boolean indexing
3. Consider tile-based processing for large images

### Issue #3: Test Coverage
**Passing Tests**: 17/22 (77%)
**Failing Tests**:
- ❌ `test_white_roundtrip` - 7% blue channel error
- ❌ `test_gray_values_roundtrip` - Gray value brightness error
- ❌ `test_image_roundtrip` - MAE 50% (unacceptable)
- ❌ `test_rgb_to_spectrum_speed` - 15s vs 2s target
- ❌ `test_spectrum_to_xyz_speed` - 2.85s vs 1s target

**Passing Test Categories**:
- ✅ Data loading (3/3)
- ✅ RGB→Spectrum correctness (7/7)
- ✅ Spectrum→XYZ basic functionality (3/3)
- ✅ XYZ→sRGB basic functionality (3/3)
- ⚠️ Roundtrip consistency (1/4) - only primary colors pass
- ❌ Performance (0/2)

## 📊 Overall Progress

### Milestone 2 Completion: 75%
```
✅ Function implementation     100% (3/3 functions)
✅ Data loading helpers        100% (3/3 helpers)
✅ Unit tests created          100% (22 tests)
⚠️  Test pass rate              77% (17/22 passing)
❌ Performance targets          0% (0/2 targets met)
```

### Blocking Issues for Milestone 3
Before proceeding to Milestone 3 (Film Response Integration), we must resolve:
1. **P0 - Roundtrip consistency**: Gray value preservation
2. **P1 - Performance**: At least 5x speedup needed

## 🔧 Technical Debt

### Code Quality
- ✅ Type hints: All functions properly annotated
- ✅ Docstrings: Comprehensive documentation with examples
- ✅ Error handling: Input validation present
- ⚠️  Performance: Needs optimization
- ⚠️  Test coverage: 77% (target: >95%)

### Files Modified
1. `phos_core.py`: +295 lines (spectral functions)
2. `tests/test_spectral_model.py`: +410 lines (new test file)
3. Total LOC added: ~705 lines

## 📝 Decision Log Entry

### Decision #020: Smits Algorithm Implementation Strategy
**Date**: 2025-12-22  
**Context**: Implementing RGB→Spectrum conversion for Phase 4 spectral model

**Decision**:
- Use Smits (1999) algorithm with 7 basis vectors (white, red, green, blue, cyan, magenta, yellow)
- Identify minimum RGB component to determine color category
- Apply basis vector combination based on component relationships

**Rationale**:
- Smits algorithm guarantees non-negative spectra (physically realizable)
- Smooth spectral curves (no oscillations like polynomial fitting)
- Exact reconstruction for basis colors
- Reasonable accuracy for arbitrary colors (typically <10% error)

**Alternatives Considered**:
1. ❌ Polynomial fitting: Can produce negative values
2. ❌ Gaussian basis: Doesn't guarantee exact primary color reconstruction
3. ❌ Machine learning (neural network): Overkill, not interpretable

**Implementation Challenges**:
1. Initial confusion about "minimum component" logic (debugged and fixed)
2. Boolean mask operations causing performance issues (needs optimization)
3. Roundtrip error due to XYZ normalization strategy (under investigation)

**Outcome**: Core algorithm working correctly for primary colors, but needs performance optimization and roundtrip refinement.

---

### Decision #021: XYZ Normalization Strategy (Pending)
**Date**: 2025-12-22  
**Status**: ⚠️ Under Investigation

**Problem**: How to normalize XYZ values to ensure:
1. RGB(1,1,1) → XYZ → RGB(1,1,1) (white point preservation)
2. RGB(0.5,0.5,0.5) → XYZ → RGB(0.5,0.5,0.5) (gray value linearity)

**Options**:
1. **Divide by Y_white** (current): White point correct, but gray values too bright
2. **Divide by Y_max**: Gray values correct, but color balance breaks
3. **No normalization**: Overexposure for low values
4. **Chromatic adaptation**: Full CIE adaptation transform (complex)

**Next Steps**:
1. Verify if issue is in `xyz_to_srgb()` gamma correction
2. Check if D65 white point is correctly encoded in transformation matrix
3. Review CIE 15:2004 standard for correct normalization practice
4. Consider separating "scene-referred" vs "display-referred" color spaces

---

## 🎯 Next Session Action Plan

### Immediate Tasks (1-2 hours)
1. **Fix Roundtrip Issue**:
   - Debug `xyz_to_srgb()` gamma correction
   - Verify D65 white point in transformation matrix
   - Test alternative normalization strategies
   - Target: <5% error for all gray values

2. **Optimize Performance** (if time permits):
   - Profile `rgb_to_spectrum()` with `cProfile`
   - Implement vectorized version without boolean indexing
   - Target: <5s for 2000×3000 image (3x speedup minimum)

### Future Tasks (Milestone 3)
Once roundtrip and performance are fixed:
1. Integrate spectral model with film response functions
2. Load film spectral sensitivity curves from `data/film_spectral_sensitivity.npz`
3. Implement spectral convolution with film curves
4. Update `Phos_0.3.0.py` main pipeline

## 📚 References

1. Smits, B. (1999). "An RGB-to-Spectrum Conversion for Reflectances". Journal of Graphics Tools, 4(4), 11-22.
2. CIE 15:2004. "Colorimetry, 3rd Edition". Commission Internationale de l'Éclairage.
3. IEC 61966-2-1:1999. "Multimedia systems and equipment - Colour measurement and management - Part 2-1: Colour management - Default RGB colour space - sRGB".
4. Lindbloom, B. "RGB/XYZ Matrices". http://www.brucelindbloom.com/

---

**Summary**: Core spectral functions are **implemented and working** for basic cases. Main blockers are roundtrip accuracy for gray values and performance optimization. Estimated 2-3 hours needed to resolve before moving to Milestone 3.
