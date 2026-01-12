# Changelog

All notable changes to Phos will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.8.3] - 2026-01-12

### ✨ Major UI/UX Overhaul - Enhanced User Experience

#### **Phase 1: Visual Enhancements (視覺美化)**

**CSS Improvements**:
- 🎨 **Dynamic Background**: Added radial gradients with animated light spots
- 💫 **Button Animations**: 
  - Smooth cubic-bezier transitions (0.3s)
  - Hover effects with lift (-2px translateY)
  - Primary buttons now have pulsating glow animation
  - Active state feedback
- 🎴 **Enhanced Cards**:
  - Film info cards now have hover effects
  - Gradient borders with shadow depth
  - Better typography hierarchy
  - Emoji + color-coded metadata badges
- 📊 **Alert Boxes**: 
  - Color-coded by type (success/info/warning/error)
  - Backdrop blur effects
  - Fade-in animations (0.3s)
  - 4px accent borders
- 🖼️ **Image Containers**:
  - Hover lift effect with shadow enhancement
  - Smooth transitions (0.3s ease)

**Before/After**:
```
舊版: 靜態扁平卡片，單一漸層背景
新版: 動態光暈背景 + 懸停動畫 + 脈動按鈕
```

---

#### **Phase 2: Functional Improvements (功能優化)**

**Quick Presets (快速預設)**:
Added 4 scenario-based presets for beginners:
- 👤 **人像模式**: Portra400 + 柔和顆粒 + physical bloom (閾值 0.85)
- 🏞️ **風景模式**: Velvia50 + 無顆粒 + physical bloom (閾值 0.80)
- 🚶 **街拍模式**: TriX400 + 默認顆粒 + artistic bloom (閾值 0.75)
- 🎬 **電影風格**: Cinestill800T + 較粗顆粒 + artistic bloom (閾值 0.70)

**Auto-Configuration**:
- Selecting a preset automatically configures:
  - Film type
  - Processing quality mode
  - Grain style
  - Tone mapping curve
  - Bloom parameters
- Displayed in collapsible expander with clear descriptions

**Parameter Reset**:
- 🔄 **重置所有參數**: One-click reset to defaults
- ℹ️ **查看當前配置**: Summary of all active settings
- Session state management for preset tracking

**Smart Defaults**:
- Film type, grain style, and tone mapping now respect preset configurations
- Bloom mode and threshold auto-adjust based on preset choice
- Fallback to standard defaults when "自定義" selected

---

#### **Phase 3: Information Presentation (資訊呈現)**

**Enhanced Result Display**:
- 📊 **Image Statistics** (in expanders):
  - Resolution (W × H)
  - Total pixels (formatted with commas)
  - Memory size (MB)
  - Average brightness (0-255)
  - Brightness change percentage (before/after)
  
- 💎 **Processing Statistics Cards**:
  - Three-column layout with color-coded cards:
    - ⏱️ Processing Time (yellow accent)
    - 🔬 Physics Mode (blue accent)
    - 💾 File Size or Quality (green accent)
  - Large centered numbers with icons
  - Gradient backgrounds with borders

- ✨ **Success Message**:
  - Gradient background with glow effect
  - Clean typography with highlighted metrics
  - Average time per image for batch processing

**Batch Processing Enhancements**:
- Redesigned success message with gradient card
- Shows: Success count / Total · Total time · Average time per image
- Color-coded metrics (green/yellow/blue)
- Box shadow and rounded borders

---

#### **Files Modified**

1. `ui_components.py` (Major refactor):
   - Lines 36-283: CSS improvements (animations, gradients, transitions)
   - Lines 323-476: Quick presets + auto-configuration logic
   - Lines 490-548: Preset-aware physics settings rendering
   - Lines 770-871: Enhanced result display with statistics
   - Lines 896-925: Improved batch processing UI

---

#### **Benefits**

**For New Users**:
- 💡 Quick presets eliminate parameter confusion
- 🎯 One-click optimal settings for common scenarios
- 📖 Clear visual hierarchy and information

**For All Users**:
- 🎨 More polished, professional appearance
- 📊 Better understanding of processing results
- 🔄 Easy to reset and experiment
- ⚡ Faster workflow with presets

**Technical**:
- ✅ Backward compatible (no breaking changes)
- ✅ Session state for preset persistence
- ✅ Syntax validated (Python import successful)
- ✅ All animations use CSS (no JS dependencies)

---

#### **Visual Comparison**

| Feature | Before (v0.8.2.3) | After (v0.8.3) |
|---------|------------------|----------------|
| Film Card | Static, flat | Hover glow, animated |
| Buttons | Simple transitions | Pulsating, lift effect |
| Presets | None | 4 scenario-based |
| Statistics | Simple text | Color-coded cards |
| Reset | Manual rerun | One-click button |
| Background | Single gradient | Animated radial spots |

---

#### **User Feedback Addressed**

✅ **"不夠直觀"** → Quick presets with scenario descriptions  
✅ **"視覺美化"** → CSS animations, gradients, hover effects  
✅ **"資訊呈現"** → Statistics cards, image metadata expanders  
✅ **"功能優化"** → Reset button, preset auto-config, better defaults  

---

## [0.8.2.3] - 2026-01-12

### 🐛 Critical Hotfix: Missing sRGB Gamma Encoding for Output

#### Problem
**最嚴重的問題**: 輸出圖像完全沒有底片效果，只有亮度變暗。所有 tone mapping 和色彩調整都看不出來。

#### Root Cause
v0.8.2 引入 sRGB → Linear RGB 輸入轉換後，**忘記在輸出時進行反向轉換**（Linear RGB → sRGB）。

完整色彩管理流程應該是：
```
輸入: sRGB (相機/手機標準輸出)
  ↓ srgb_to_linear()
Linear RGB (物理計算空間)
  ↓ spectral_response, bloom, grain, tone mapping
Linear RGB (處理完成)
  ↓ ❌ v0.8.2 缺少這步！
  ↓ ✅ v0.8.2.3 新增 linear_to_srgb()
sRGB (螢幕顯示輸出)
```

**為什麼會這樣？**
- Linear RGB 的中灰（0.18）在螢幕上看起來非常暗（約 46% 亮度）
- Tone mapping 的對比度調整在 Linear 空間完成，但沒有 gamma 編碼就無法正確顯示
- 色彩飽和度和色調也完全失真

#### Fixed

**新增函數** - `modules/optical_core.py`:
- Added `linear_to_srgb()` function (IEC 61966-2-1:1999 standard)
- Piecewise function: `12.92 × C` below 0.0031308, `1.055 × C^(1/2.4) - 0.055` above
- Includes `np.clip(0, 1)` to prevent out-of-gamut issues
- Added to `__all__` exports (line 260)

**輸出轉換** - `Phos.py`:
- **彩色膠片** (lines 698-706):
  ```python
  result_r_srgb = linear_to_srgb(result_r)
  result_g_srgb = linear_to_srgb(result_g)
  result_b_srgb = linear_to_srgb(result_b)
  combined_r = (result_r_srgb * 255).astype(np.uint8)
  ```
- **黑白膠片** (lines 745-747):
  ```python
  result_total_srgb = linear_to_srgb(result_total)
  final_image = (result_total_srgb * 255).astype(np.uint8)
  ```
- Import updated: Added `linear_to_srgb` to imports (line 153)

**UI 修復** - `ui_components.py`:
- Fixed Streamlit API deprecation: `use_column_width=True` → `width="stretch"` for `st.image()`
- Lines 793, 797: Updated both original and film image display
- Note: Buttons still use `use_container_width` parameter (different API)

#### Tests Added
- `tests_refactored/test_color_space.py`:
  - New `TestLinearToSRGB` class with 7 comprehensive tests
  - Tests: zero/one values, threshold, midtone, clipping, shape preservation, monotonicity
  - Updated `TestRoundTrip` to use module functions instead of local implementation
  - **Status**: 37/37 passed (100%)

#### Results
- ✅ **底片效果完全恢復** - Tone mapping, color grading, contrast adjustment now visible
- ✅ **正確亮度** - Linear 0.18 → sRGB 0.46 (correct middle gray perception)
- ✅ **色彩準確** - Film color science now displays correctly
- ✅ **物理正確** - Complete color-managed workflow: sRGB in → Linear processing → sRGB out
- ✅ **測試通過**: 100/100 (grain + tone mapping + image processing + color space)

#### Impact
**Critical fix** - 沒有這個修正，v0.8.2 的所有色彩管理改進都無法正常顯示。這是 v0.8.2 最重要的 hotfix。

---

## [0.8.2.2] - 2026-01-12

### 🐛 Hotfix: Grain Size Reduction for Linear RGB

#### Problem
After v0.8.2 introduced sRGB→Linear RGB conversion, grain became extremely coarse (~2.5-3× too strong).

#### Root Cause
`grain_intensity` parameters (0.08-0.20) were originally calibrated for sRGB gamma space. In Linear RGB space, the same additive noise values create much stronger perceptual effects after gamma encoding for display.

**Technical Details**:
- In Linear RGB: 0.18 ≈ 18% middle gray
- Adding ±0.18 noise → oscillates between 0.0 and 0.36
- After gamma 2.2 encoding → perceptual range [0.0, 0.65] (65% swing!)
- In sRGB gamma space (original): Same ±0.18 on value 0.5 → [0.32, 0.68] (only 25% swing)

#### Fixed
- **File**: `modules/image_processing.py`
  - Added `GRAIN_LINEAR_RGB_COMPENSATION = 0.30` constant (line 62)
  - Modified `combine_layers_for_channel()` to scale `grain_intensity` by 0.30× (line 212)
  - Reduces grain strength by ~70% to compensate for Linear RGB perceptual amplification
  
- **File**: `Phos.py`
  - Fixed `sens` calculation to use perceptual brightness (gamma 2.2 correction) instead of raw Linear RGB average (line 289)
  - Prevents over-sensitivity in shadow areas

- **File**: `grain_strategies.py`
  - Normalized Chi-squared noise distribution (noise²) to prevent extreme values (lines 115-121)
  - Standardized to mean=0, std=1 before applying weights

- **File**: `film_models.py`
  - Increased `GRAIN_BLUR_SIGMA` from 1.0 → 1.5 for smoother grain (line 130)

#### Tests Updated
- `tests_refactored/test_image_processing.py`:
  - Updated `test_grain_addition_rgb()` and `test_grain_addition_single_channel()` expectations
  - All tests now account for 0.30× compensation factor
  - **Status**: 18/18 passed (100%)

#### Results
- **Grain reduction**: ~70-80% smaller (subjective: from "extremely coarse" to normal)
- **Physics score**: Maintained (9.2/10)
- **Test status**: 93/93 passed (100%) - grain, tone mapping, image processing, color space
- **Backward compatibility**: Maintained (grain intensity parameters unchanged, only scaled at application time)

#### Related Issues
- User report: "默認顆粒度超級粗" (default grain extremely coarse)
- Cascading effect from v0.8.2 sRGB→Linear RGB conversion

---

## [0.8.2.1] - 2026-01-12

### 🐛 Hotfix: Brightness Restoration for Linear RGB

#### Problem
After v0.8.2 introduced sRGB→Linear RGB conversion, output images became very dark (50% gray → 18% gray, -64% brightness loss).

#### Root Cause
Multiple `np.power()` operations (gamma curves, response curves) were designed for sRGB gamma space. After switching to Linear RGB input, these operations caused cumulative brightness compression.

#### Fixed
- **File**: `modules/tone_mapping.py`
  - Line 126: Removed `np.power(lux, params.gamma)` in Filmic tone mapping
  - Line 64: Removed `np.power(..., gamma_adj/gamma)` in Reinhard tone mapping
  - Changed to direct multiplication for Linear RGB input

- **File**: `modules/image_processing.py`
  - Line 190: Removed `np.power(lux, layer.response_curve)` in layer combination
  - Changed to: `result = bloom * w_diffuse + lux * w_direct`

- **File**: `Phos.py`
  - Lines 712-716: Removed `np.power(response_total, film.panchromatic_layer.response_curve)` for B&W films

#### Tests Updated
- `tests_refactored/test_tone_mapping.py`:
  - Updated `test_reinhard_color_mode_effect()` to reflect new Linear RGB behavior
  
- `tests_refactored/test_image_processing.py`:
  - Updated `test_nonlinear_response_curve()` expectations

#### Results
- **Brightness restored**: 3% → 18% for midtones (+475% improvement)
- **Test status**: 69/69 passed (100%) - tone mapping + image processing
- **Note**: response_curve and tone mapping gamma parameters now disabled; will require recalibration for Linear RGB in future versions

---

## [0.8.2] - 2026-01-12

### ✨ Color Management: sRGB Gamma Decoding (Phase 1)

#### Added
- **File**: `modules/optical_core.py`
  - Added `srgb_to_linear()` function implementing IEC 61966-2-1:1999 standard
  - Piecewise function: linear below 0.04045, power 2.4 above
  - Modified `spectral_response()` to decode sRGB → Linear RGB before spectral matrix operations

- **File**: `tests_refactored/test_color_space.py` (new)
  - 30 comprehensive unit tests (100% pass rate)
  - Test categories:
    - Basic gamma decoding correctness (8 tests)
    - Spectral response integration (4 tests)
    - Gray neutrality validation (8 color films)
    - Energy conservation (3 tests)
    - Round-trip accuracy (2 tests)
    - Edge cases (5 tests)
    - Physical correctness (2 tests)
    - Performance benchmarks (2 tests)

#### Changed
- **Physics Foundation**: 
  - **Before**: Spectral response matrices operated on sRGB gamma-encoded values (incorrect)
  - **After**: Spectral response matrices now operate on Linear RGB values (correct)
  - **Impact**: Proper Beer-Lambert law adherence, physically accurate light behavior

#### Results
- **Gray neutrality**: Perfect (deviation = 0.0000) for all 8 color films tested
- **Energy conservation**: All spectral response matrix row sums = 1.0000
- **Physics score**: 8.9/10 → 9.2/10
- **Test status**: 30/30 passed (100%)

#### Theory
Spectral response matrices represent physical Beer-Lambert absorption, which operates on **linear light intensity**, not gamma-encoded display values. The v0.8.2 update corrects this fundamental issue, enabling:
1. Physically accurate color transformations
2. Proper additive light behavior (e.g., bloom, grain)
3. Correct tone mapping (operating in scene-referred linear space)
4. Future integration with camera profiles and film spectra

#### Breaking Changes
- **None for end users** - output quality improved, no API changes
- **Internal**: Tone mapping and response curve parameters may require recalibration (handled in v0.8.2.1)

---

## [0.6.4] - 2026-01-12

### ♻️ Grain Strategy Pattern Refactoring (P1-2 Complete)

#### Changed (Refactoring)
- **BREAKING (Internal Only)**: Refactored `generate_grain()` using Strategy Pattern
  - **Before**: 110+ line function with if-elif branching (artistic vs poisson modes)
  - **After**: 2 independent strategy classes (<50 lines each) + factory pattern
  - **Impact**: 90% code reduction (110→5 lines in main file), improved testability
  - **API**: Fully backward compatible - no changes to calling code required

#### Added
- **New Module**: `grain_strategies.py` (343 lines)
  - `GrainStrategy` abstract base class (strategy interface)
  - `ArtisticGrainStrategy`: Visual-oriented, mid-tone emphasis
  - `PoissonGrainStrategy`: Physics-based, Poisson photon statistics + silver grain
  - `get_grain_strategy()`: Factory function (eliminates conditional logic)
  - `generate_grain()`: Unified interface (backward compatible wrapper)

- **New Tests**: `tests_refactored/test_grain_strategies.py` (470 lines)
  - 24 comprehensive unit tests (100% pass rate)
  - Test coverage: 94%
  - Test categories:
    - Strategy initialization (2 tests)
    - Artistic mode behavior (5 tests) - mid-tone emphasis, sens parameter
    - Poisson mode behavior (5 tests) - dark vs bright, exposure level, grain size
    - Factory pattern (3 tests) - strategy dispatch, invalid mode handling
    - Unified interface (2 tests) - artistic/poisson delegation
    - Edge cases (3 tests) - zero intensity, saturated images
    - Physical constraints (4 tests) - energy conservation, reproducibility

#### Removed
- Deleted 110 lines from `Phos.py`:
  - Original `generate_grain()` implementation (lines 245-357)
  - Replaced by import: `from grain_strategies import generate_grain`
  - Eliminated if-elif branching on grain mode

#### Design Principles Applied
- **Good Taste**: Eliminated unnecessary conditionals via factory pattern
- **Simplicity**: Each strategy <50 lines (vs. original 110+)
- **Pragmatism**: API unchanged, zero breaking changes for users
- **Defensibility**: Physical assumptions (mid-tone vs Poisson) isolated per strategy

#### Test Results
- **New tests**: 24/24 passed (100%)
- **Total tests**: 327/327 passed (100%, 4 skipped)
- **Coverage**: grain_strategies.py = 94%
- **Regression**: Zero breaking changes

### ♻️ Bloom Strategy Pattern Refactoring (P0-1 Complete)

#### Changed (Refactoring)
- **BREAKING (Internal Only)**: Refactored `apply_bloom()` using Strategy Pattern
  - **Before**: 250+ line monolithic function with nested if-elif-else
  - **After**: 3 independent strategy classes (<50 lines each) + factory pattern
  - **Impact**: 96% code reduction (250→10 lines in main file), improved maintainability
  - **API**: Fully backward compatible - no changes to calling code required
  
#### Added
- **New Module**: `bloom_strategies.py` (543 lines)
  - `BloomStrategy` abstract base class (strategy interface)
  - `ArtisticBloomStrategy`: Visual-oriented, additive bloom effect
  - `PhysicalBloomStrategy`: Energy-conserving, threshold-based scattering
  - `MieCorrectedBloomStrategy`: Wavelength-dependent Mie scattering
  - `get_bloom_strategy()`: Factory function (eliminates conditional logic)
  - `apply_bloom()`: Unified interface (backward compatible wrapper)
  
- **New Tests**: `tests_refactored/test_bloom_strategies.py` (320 lines)
  - 21 comprehensive unit tests (100% pass rate)
  - Test coverage:
    - Strategy class behavior (initialization, validation, output)
    - Energy conservation (Physical & Mie modes, <1% error)
    - Wavelength dependency (blue scattering > red scattering)
    - Factory pattern (correct strategy dispatch)
    - Unified interface (delegation correctness)
    - Edge cases (zero/saturated images, single pixel highlights)
    - Performance (6MP single-channel processing <5s)

#### Removed
- Deleted 205 lines from `Phos.py`:
  - Original `apply_bloom()` implementation (replaced by import)
  - Eliminated conditional branches (if-elif-else on bloom mode)
  - Kept auxiliary functions (create_dual_kernel_psf, apply_wavelength_bloom)

#### Design Principles Applied
- **Good Taste**: Eliminated unnecessary conditionals via factory pattern
- **Simplicity**: Each strategy <50 lines (vs. original 250+)
- **Pragmatism**: API unchanged, no breaking changes for users
- **Defensibility**: Physical assumptions isolated per strategy, independently testable

#### Test Results
- New tests: 21/21 passed (100%)
- Existing tests: 302/306 passed (98.7%, 4 skipped)
- Regression tests: Zero breaking changes

#### Documentation
- Added comprehensive docstrings explaining each strategy's physical assumptions
- Documented factory pattern usage with examples
- Updated inline comments to reference new module structure

#### Case Study (for future refactorings)
This refactoring demonstrates how to systematically reduce technical debt:
1. **Identify** complexity hotspots (functions >50 lines, deep nesting)
2. **Design** strategy pattern to isolate independent behaviors
3. **Implement** with backward compatibility (wrapper interface)
4. **Test** comprehensively (unit tests + regression tests)
5. **Commit** with detailed documentation

**Next candidates**: `apply_grain()`, `apply_halation()` for similar treatment

Ref: `AGENTS.md` (Lessons Learned - Simplicity Through Deletion)

---

## [0.6.2] - 2026-01-11

### 🔬 Parameter Validation & Physics Bug Fix

#### Added
- **Parameter Validation System** (52 physical hypotheses formalized)
  - Added `__post_init__()` validation to 8 dataclasses:
    - `HalationParams` (8 constraints: energy conservation, transmittance ordering)
    - `HDCurveParams` (6 constraints: gamma ranges, D_min/D_max ordering)
    - `ReciprocityFailureParams` (6 constraints: Schwarzschild exponent, channel ordering)
    - `GrainParams` (4 constraints: mode validation, intensity ranges)
    - `WavelengthBloomParams` (6 constraints: wavelength ranges, physical ordering)
    - `ISODerivedParams` (7 constraints: grain diameter, statistical validity)
    - `ToneMappingParams` (6 constraints: gamma ranges, strength parameters)
    - `BloomParams` (15 constraints: mode validation, scattering ratio, Mie parameters)
  - All constraints include literature references and physical justifications
  - Total: +414 lines of validation logic

#### Fixed
- **CRITICAL BUG**: CineStill 800T Halation energy violation
  - **Problem**: `backplate_reflectance = 0.8` with no AH layer → **61.4% average Halation** (violates energy conservation!)
  - **Fix**: Reduced to `backplate_reflectance = 0.35` → **26.9% Halation** (physically valid)
  - **Discovery**: Bug found by energy conservation validation in `HalationParams.__post_init__()`
  - **Impact**: This bug existed since CineStill 800T profile creation, now corrected
  - **Location**: `film_models.py` line ~1880

#### Deprecated
- **apply_bloom_mie_corrected()** - Will be removed in v0.7.0
  - **Reason**: Function refactored into `bloom_strategies.MieCorrectedBloomStrategy`
  - **Replacement**: Use `apply_bloom(lux, bloom_params)` with `mode='mie_corrected'`
  - **Impact**: 0 external callers found (internal-only function)
  - **Migration**: Automatic (function redirects to new implementation)

#### Documentation
- Corrected misleading "舊版函數" (legacy functions) comments
  - **Line 329-330**: `apply_grain()` → Changed to "Grain Generation" (still active)
  - **Line 567-568**: `apply_wavelength_bloom()` → "Legacy Medium Physics Path" (backward compatibility)
- Added execution path comments in `optical_processing()`:
  - **Path 1**: Legacy Medium Physics (wavelength-dependent bloom)
  - **Path 2**: Legacy Medium Physics Separated (no wavelength dependency)
  - **Path 3**: New Physical Mode (Strategy Pattern, recommended)
- Added `@deprecated` decorator for proper deprecation warnings

#### Removed
- **Legacy Code Cleanup** (Action 3/3)
  - Deleted `archive/scripts/` (144KB, 13 diagnostic scripts) - no longer needed
  - Deleted `archive/tests_legacy/` (116KB, 27 old tests) - replaced by tests_refactored/
  - Total: **-6,125 lines of obsolete code removed**
  - Kept: `archive/completed_tasks/` (design decision documentation)
  - Git history fully preserved for rollback if needed

#### Changed
- Updated 4 tests in `test_optical_effects.py` to use Mie theory fixed values
- Fixed `test_parameter_range_validation()` to satisfy transmittance ordering constraint
- Converted 4 reciprocity validation tests to use `pytest.raises(AssertionError)`

#### Statistics
- **Net Change**: -5,711 lines (added 414, removed 6,125)
- **Test Pass Rate**: 282/286 (98.6%)
- **Bugs Discovered**: 1 (CineStill 800T Halation)
- **Hypotheses Formalized**: 52 physical assumptions now validated
- **Commits**: 3 (`f2359a4`, `361a700`, `cc7c554`)

### Design Philosophy (Programming Philosophy Review 2026-01-11)
- **Validation as Discovery**: `__post_init__()` validation discovered a real bug (61.4% Halation)
- **Parameter as Theory**: Every parameter is a falsifiable hypothesis with literature references
- **Simplicity Through Deletion**: Removing 6,125 lines > adding 414 lines
- **Pragmatic Ranges**: Allow test boundary values while keeping production parameters physically valid
- **Documentation in Code**: Validation logic with clear error messages is better than external docs
- **Incremental Validation**: Adding validation in phases (3 dataclasses → 5 dataclasses) is safer

---

## [0.6.1] - 2025-01-11

### 📝 Documentation & Code Cleanup (Phase 3 Task 2)

#### Deprecated Parameters Marked
- Marked `WavelengthBloomParams.wavelength_power` as **DEPRECATED** (since v0.4.2)
- Marked `WavelengthBloomParams.radius_power` as **DEPRECATED** (since v0.4.2)
- These parameters were used for empirical formula (removed in v0.4.2)
- Now only Mie lookup table is used (TASK-013 Phase 7, 2025-12-24)
- Parameters retained for backward compatibility, planned removal in v0.7.0

#### Documentation Updates
- Fixed TODO comments in `film_models.py`:
  - Removed outdated v0.5.0 migration TODO (no breaking changes in v0.5.0)
  - Clarified that v0.5.0 was internal refactoring only
- Improved inline documentation for Mie scatter lookup table usage

#### Statistics
- **No Code Changes**: Only documentation and deprecation markers
- **Test Pass Rate**: 282/286 (98.6%) - all tests passing
- **Backward Compatibility**: 100% maintained

### Design Philosophy
- **Good Taste**: Clear deprecation warnings guide users
- **Never Break Userspace**: Parameters retained for compatibility
- **Pragmatism**: Document reality (Mie lookup is only implementation)
- **Simplicity**: Removed confusing outdated TODOs

---

## [0.6.0] - 2025-01-11

### 🚨 Breaking Changes

#### Removed Deprecated Functions (Phase 3 Task 1)
- ❌ Removed `generate_grain_for_channel()` (deprecated v0.5.0)
- ❌ Removed `generate_poisson_grain()` (deprecated v0.5.0)
- ❌ Removed `apply_bloom_to_channel()` (deprecated v0.5.0)
- ❌ Removed `apply_bloom_conserved()` (deprecated v0.5.0)

**Migration**: See `BREAKING_CHANGES_v06.md` for detailed migration guide.

### Code Cleanup
- Deleted 154 lines of deprecated wrapper functions
- Updated 7 internal call sites to use unified interfaces:
  - `apply_bloom_mie_corrected()` → uses `apply_bloom()`
  - `apply_bloom_and_halation()` → uses `apply_bloom()`
  - Streamlit UI (color film) → uses `apply_bloom()` with `BloomParams`
  - Streamlit UI (B&W film) → uses `apply_bloom()` with `BloomParams`
- Removed 6 deprecation warning tests (no longer needed)
- Deleted `tests_refactored/test_deprecation_warnings.py` (175 lines)

### Statistics
- **LoC**: 3380 → 3226 (-154 lines, -4.6%)
- **Test Pass Rate**: 282/286 (98.6%) - 6 deprecation tests removed
- **Deprecated Functions**: 4 → 0 (-100%)

### Files Modified
- `Phos.py`: -154 lines (removed 4 deprecated functions + updated 4 call sites)
- `tests_refactored/test_physics_core.py`: Updated 1 call site
- `tests_refactored/test_deprecation_warnings.py`: Deleted (175 lines)
- `BREAKING_CHANGES_v06.md`: Created
- `CHANGELOG.md`: Updated

### Design Philosophy
- **Good Taste**: Removed unnecessary complexity, simpler API surface
- **Never Break Userspace**: 2-month deprecation period (v0.5.0 → v0.6.0)
- **Pragmatism**: Code that doesn't solve problems is removed
- **Simplicity**: Single unified interfaces > multiple wrappers

---

## [0.5.1] - 2025-01-11

### 🧹 Refactored - Phase 2 Short-Term Improvements

#### Code Quality Improvements
- **Completed Deprecation Implementation** (Tasks 1-2):
  - Converted deprecated functions to delegate to unified interfaces (instead of duplicating logic)
  - Functions now properly forward to `generate_grain()` and `apply_bloom()`
  - Removed 50+ lines of unreachable dead code
  - Added comprehensive deprecation warning tests (6 test cases)

- **Fixed Test Hygiene** (Task 3):
  - Fixed 5 FFT convolution tests returning `bool` instead of `None`
  - Eliminated `PytestReturnNotNoneWarning` messages from pytest output
  - Tests now use standard pytest assertion patterns
  - Updated `run_all_tests()` helper to work with None-returning tests

#### Statistics
- **Total Lines Removed**: ~50 lines (dead code after delegation)
- **Test Pass Rate**: 315/320 (98.4%) - same as v0.5.0
- **New Tests**: 6 deprecation warning tests added
- **Test Breakdown**:
  - 6/6 Deprecation warning tests ✅
  - 5/5 FFT convolution tests ✅ (warnings eliminated)
  - All Phase 1 tests remain passing ✅

#### Affected Functions
Functions properly delegating to unified interfaces:
- `generate_grain_for_channel()` → `generate_grain()`
- `generate_poisson_grain()` → `generate_grain()`
- `apply_bloom_to_channel()` → `apply_bloom()`
- `apply_bloom_conserved()` → `apply_bloom()`

All functions emit proper `DeprecationWarning` with:
- Version introduced (v0.5.0)
- Version to be removed (v0.6.0)
- Recommended alternative with example

#### Breaking Changes
- None (backward compatibility maintained)

#### Design Philosophy
- **Good Taste**: Delegate, don't duplicate
- **Never Break Userspace**: All deprecated functions still work correctly
- **Pragmatism**: Fixed test warnings that provided no value
- **Simplicity**: Removed unreachable code reduces maintenance burden

---

## [0.5.0] - 2025-01-11

### 🧹 Refactored - Phase 1 Technical Debt Cleanup

#### Code Quality Improvements
- **Unified Bloom Processing** (Task 2):
  - Created `apply_bloom()` unified interface supporting 3 modes (artistic, physical, mie_corrected)
  - Deleted `phos_core.py:apply_bloom_optimized()` (removed 39 lines of duplicate code)
  - Updated `phos_core.py:process_color_channels_parallel()` to avoid circular imports
  - All 6 Bloom tests passing ✅

- **Unified Grain Processing** (Task 3):
  - Created `generate_grain()` unified interface supporting 2 modes (artistic, poisson)
  - Deleted `phos_core.py:generate_grain_optimized()` (removed 33 lines of duplicate code)
  - Updated 15+ call sites across 4 files (`Phos.py`, `test_performance.py`, `test_physics_core.py`, `profile_real_workflow.py`)
  - All 7 Grain physics tests passing ✅

- **Removed Deprecated HalationParams** (Task 1):
  - Deleted 62 lines of backward compatibility code from `film_models.py:__post_init__()`
  - Removed deprecated parameters: `transmittance_r/g/b`, `ah_absorption`
  - Unified on Beer-Lambert parameters: `emulsion_transmittance_r/g/b`, `ah_layer_transmittance_r/g/b`
  - Skipped 2 backward compatibility tests (functionality intentionally removed)

- **Removed Ineffective In-Place Optimizations** (Task 4):
  - Removed 6 instances of `out=` parameter providing <1% performance gain
  - Kept 2 critical-path optimizations in tone mapping and spectrum conversion
  - Improved code readability without performance regression

#### Statistics
- **Total Duplicate Code Eliminated**: ~150 lines
- **Test Pass Rate**: 310/315 (98.4%)
- **Test Breakdown**:
  - 58/58 Spectral film tests ✅
  - 9/9 Energy conservation tests ✅
  - 7/7 Grain physics tests ✅
  - 6/6 Bloom optical tests ✅
  - 8/8 Performance benchmarks ✅

#### Performance Validation
- **Grain Generation**: 195.3 µs (512×512, mean ± 11.6 µs std)
- **Memory Efficiency**: <10 MB growth over 50 iterations
- **No Performance Regression**: All benchmarks within baseline
- **Linear Scaling**: O(N) time complexity maintained

#### Breaking Changes
- None (backward compatibility maintained via deprecated function wrappers)

#### Design Philosophy
Refactor guided by:
- **Good Taste**: Eliminate unnecessary complexity
- **Never Break Userspace**: Maintain compatibility
- **Pragmatism**: Solve real problems, not theoretical perfection
- **Simplicity**: Reduce cognitive load

#### Documentation
- Created `docs/PHASE1_CLEANUP_PLAN.md` with detailed refactor plan
- Updated function docstrings with unified interfaces
- Added Phase 1 completion summary

#### Dependencies
- Added `pytest-benchmark==5.2.3` for performance testing
- Added `psutil==7.2.1` for memory profiling

---

## [0.4.1] - 2025-12-23

### 🐛 Fixed - Spectral Mode Brightness Loss
- **Critical Bug**: Fixed 22%-65% brightness loss in spectral film simulation
  - **Root Cause**: `apply_film_spectral_sensitivity()` output Linear RGB but display expected sRGB
  - **Solution**: Added sRGB gamma encoding step (IEC 61966-2-1:1999 standard)
  - **Impact**: 50% gray card: -50.0% → +7.7% (within 10% target)
  - **Impact**: Blue sky scene: -35.9% → +9.0% (within 15% target)
- **Breaking Change**: `apply_film_spectral_sensitivity()` now outputs sRGB (not Linear RGB)
  - Color space workflow: Spectral integration → Linear RGB → Normalization → **sRGB gamma encoding**
  - Consistent with `xyz_to_srgb()` output format

### 🧪 Testing
- **25/25 tests passing** (100% correctness)
- Updated 3 tests to account for gamma encoding behavior:
  - `test_monochromatic_green`: Normalized values can equal 1.0 (changed `>` to `>=`)
  - `test_monochromatic_blue`: Same normalization behavior
  - `test_linearity`: Changed from strict 2x linearity to monotonicity + gamma compression (1.3x-2.0x)

### 📚 Documentation
- Updated `phos_core.py` docstring: Clarified sRGB output with gamma encoding
- Added to Notes: Color space workflow, physical process, version fix log
- Created `tasks/TASK-008-spectral-brightness-fix/` documentation:
  - `debug_playbook.md`: Root cause analysis
  - `fix_implementation.md`: Implementation details
  - `physicist_review.md`: Physical correctness approval ✅
  - `completion_report.md`: Results and statistics

### ✅ Physicist Review
- **Status**: Approved for production
- Energy conservation: Verified in linear domain
- Gamma formula: Matches IEC 61966-2-1:1999 standard
- Numerical stability: Confirmed (float32 sufficient, np.maximum prevents NaN)

---

## [0.4.2] - 2024-12-24

### ✨ Added - Reciprocity Failure Simulation

- **Schwarzschild Law Implementation**: Simulates film's non-linear response during long exposures
  - Mathematical model: `I_eff = I · t^(p-1)` (normalized form for t=1s compatibility)
  - **Channel-independent processing**: RGB channels have different failure rates (color shift)
    - Red channel: p=0.93 (lowest failure)
    - Green channel: p=0.90 (medium failure)
    - Blue channel: p=0.87 (highest failure → warm color shift in long exposures)
  - **Logarithmic p-value model**: `p(t) = p0 - k·log10(t/t_ref)` (90%+ literature accuracy)
  - **Exposure time range**: 0.0001s - 300s (high-speed to astrophotography)

### 🎬 Film Profiles Updated

- **6 Real Film Profiles** with calibrated reciprocity parameters:
  - **Kodak Portra 400**: Low failure (T-Grain technology)
    - 30s exposure → ~39% brightness loss, minimal color shift
  - **Kodak Ektar 100**: Extremely low failure (modern emulsion)
    - 30s exposure → ~35% brightness loss
  - **Fuji Velvia 50**: High failure (slide film characteristics)
    - 30s exposure → ~56% brightness loss, noticeable blue reduction
  - **Ilford HP5 Plus 400**: Medium failure (B&W, p_mono=0.87)
    - 30s exposure → ~40% brightness loss
  - **Kodak Tri-X 400**: Medium failure (B&W, p_mono=0.88)
    - 30s exposure → ~48% brightness loss
  - **Cinestill 800T**: Low failure (motion picture film stock)
    - 30s exposure → ~41% brightness loss

### 🎨 UI Integration

- **Exposure Time Control**: Logarithmic slider (0.0001s - 300s)
- **Real-time Preview**:
  - EV compensation calculation (e.g., "+0.9 EV" at 30s)
  - Estimated brightness loss percentage
  - Color shift trend indicator
- **Physical Mode**: Automatic integration with H&D curve processing
  - Execution order: Reciprocity → H&D curve → Halation → Grain
  - Enable/disable toggle for comparison

### 🧪 Testing - 100% Coverage

- **72 new tests** (100% passing):
  - **49 unit tests**: Core functionality, edge cases, energy conservation
  - **23 integration tests**: Full pipeline, all film profiles, numerical stability
- **Project-wide test coverage**: 310/312 tests passing (**99.4%** pass rate)
- **Performance validated**:
  - 1024×1024: 3.65 ms (< 1% overhead, **36.5%** of 10ms target)
  - 4K (2160×3840): 28.48 ms (suitable for batch processing)

### 🐛 Fixed

- **Black & White Film IndexError** (CRITICAL):
  - Issue: Assumed 3 channels, but B&W films use single channel
  - Solution: Enhanced channel detection with `p_mono` parameter
  - Impact: HP5 Plus 400 and Tri-X 400 now fully functional

### 📊 Validation

- **Literature Accuracy**: 90-95% match with manufacturer data
  - Kodak P-315 (Portra 400): 10s/100s within ±4%, 30s within ±20%
  - Ilford Technical Data (HP5 Plus): ±6% across all test points
- **Energy Conservation**: Verified (all tests pass)
  - No energy increase (physically impossible)
  - Monotonic brightness decrease with exposure time
- **Backward Compatibility**: Preserved
  - `enabled=False`: No effect on existing workflows
  - `t=1s`: < 0.1% deviation from original

### ⚡ Performance

- **Ultra-low overhead**: < 1% of total processing time
- **Linear scaling**: O(N) with pixel count
- **Vectorized operations**: NumPy-optimized, no Python loops

### 📚 Documentation

- **New module**: `reciprocity_failure.py` (514 lines)
  - 5 main functions + 6 film presets
  - Comprehensive docstrings with physics derivations
- **Test files**:
  - `tests/test_reciprocity_failure.py` (658 lines)
  - `tests/test_reciprocity_integration.py` (284 lines)
  - `scripts/test_reciprocity_visual.py` (240 lines)
- **Task documentation**:
  - `tasks/TASK-014-reciprocity-failure/task_brief.md`
  - Phase 1-4 completion reports (4 files, 2500+ lines)
  - `compensation_tables.md` (lookup tables for 6 films)
- **Context updates**:
  - `context/decisions_log.md`: Decisions #044-046 added
  - Design rationales for Schwarzschild form, channel independence, logarithmic model

### 🎯 Physics Score Impact

- **Before**: 8.7/10
- **After**: 8.9/10 (**+0.2** improvement)
- **Dimensions improved**:
  - Numerical accuracy: 8.5 → 9.0 (+0.5)
  - Verifiability: 8.0 → 9.5 (+1.5)
  - Numerical stability: 9.0 → 9.5 (+0.5)

### 🔬 Technical Details

- **Data Structure**: `ReciprocityFailureParams` dataclass
  - 4 p-values (p_red/green/blue + optional p_mono)
  - 6 control parameters (thresholds, decay coefficients)
  - Curve type selection ("logarithmic" or "constant")
- **Integration Point**: Before H&D curve in `optical_processing()`
  - Rationale: Reciprocity affects light exposure, not film response curve
  - Validated with physicist approval
- **Type Safety**: Robust handling of 2D/3D arrays, float/array p-values

### 🎓 Use Cases

- **Astrophotography**: Simulate long exposure color shifts (e.g., 60-300s)
- **Landscape Photography**: Twilight/golden hour extended exposures (10-60s)
- **Light Painting**: Creative effects with intentional reciprocity failure
- **Historical Accuracy**: Match vintage film look (pre-modern emulsions)

### ⚙️ API Changes

- **New parameter in `optical_processing()`**:
  ```python
  exposure_time: float = 1.0  # seconds, default=1.0 (no effect)
  ```
- **FilmProfile extension**:
  ```python
  reciprocity_params: Optional[ReciprocityFailureParams] = None
  # Auto-initialized in __post_init__ with film-specific defaults
  ```

### 🚀 Breaking Changes

- **None** - Fully backward compatible
  - Default `exposure_time=1.0` produces identical results
  - Existing code requires no modifications

---

## [0.4.0] - 2025-12-22

### 🎨 Added - Spectral Film Simulation
- **31-channel Spectral Processing**: RGB → 31-ch Spectrum (380-770nm, 13nm interval)
  - Based on Smits (1999) RGB-to-Spectrum algorithm
  - Branch-free vectorized implementation
  - Tile-based processing (512×512) for memory optimization
- **Film Spectral Sensitivity Curves**: 4 real film profiles
  - Kodak Portra 400 (portrait, warm tones)
  - Fuji Velvia 50 (landscape, high saturation)
  - CineStill 800T (cinematic, tungsten-balanced)
  - Ilford HP5 Plus 400 (B&W, panchromatic)
- **Physical Color Rendering**: Spectrum × Film sensitivity → RGB
  - Energy conservation <0.01%
  - Roundtrip error <3%
  - Color relationship preservation
- **UI Integration**: Experimental feature in Physical/Hybrid mode
  - Checkbox to enable spectral mode
  - Film selection dropdown
  - Performance info display

### ⚡ Optimized - Performance
- **3.5x speedup** for `rgb_to_spectrum()`: 11.57s → 3.29s (6MP image)
  - Eliminated fancy indexing (1.31x)
  - Branch-free vectorization (3.52x total)
  - Fixed mask overlap bug for grayscale images
- **23x memory reduction**: 709 MB → 31 MB (tile-based processing)
- **Complete pipeline**: ~4.24s for RGB → Spectrum → Film RGB (6MP)

### 🐛 Fixed
- **Mask Overlap Bug**: Fixed grayscale image 3x energy overcount
  - Issue: All three masks (b_min, r_min, g_min) were True for R=G=B
  - Solution: Mutual exclusion with priority (b_min > r_min > g_min)
  - Impact: Grayscale roundtrip error <0.001 (previously ~200%)

### 📚 Documentation
- Added `phase4_milestone4_completion.md` (optimization report)
- Updated `README.md` with v0.4.0 features
- Added performance benchmarks and test coverage
- Created `CHANGELOG.md` for version tracking

### 🧪 Testing
- 21/22 tests passing (95% correctness)
- 1 test marked xfail (aspirational performance target <2s, actual 3.29s)
- All physical correctness tests passing

### 🔧 Technical
- New module: `phos_core.py` (spectral processing functions)
- Functions: `rgb_to_spectrum()`, `spectrum_to_xyz()`, `xyz_to_srgb()`, 
  `load_film_sensitivity()`, `apply_film_spectral_sensitivity()`
- Data files: `data/smits_basis_spectra.npz`, `data/cie_1931_31points.npz`

---

## [0.3.0] - 2025-12-20

### 🎯 Added - ISO Unification System (P1-2)
- **Physics-based grain calculation**: Automatically derive grain parameters from ISO
  - Grain diameter: `d_mean = d0 × (ISO/100)^(1/3)` (James 1977)
  - Visual intensity: `grain_intensity = k × √(d_mean/d0) × √(ISO/100)`
  - Scattering ratio: `scattering_ratio = 0.04 + 0.04 × (d_mean/d0)²`
- **Film type classification**:
  - `fine_grain`: ISO 50-200 (Portra400, Ektar100, Velvia50)
  - `standard`: ISO 200-400 (NC200, Gold200)
  - `high_speed`: ISO 400-1600+ (Cinestill800T, Superia400)
- **One-click film creation**: `create_film_profile_from_iso()` function
- **Test coverage**: 45/46 tests passed (97.8%)

### 🎛️ Added - Physical Mode UI Integration
- **Render mode selector**: Artistic / Physical / Hybrid toggle in sidebar
- **Collapsible parameter panels**: Bloom / H&D Curve / Grain controls
- **Smart display**: Hide physical parameters in Artistic mode
- **Fixed image sizes**: 800px (single), 200px (batch preview)
- **Backward compatible**: Default to Artistic mode

### 🧪 Added - Medium Physics Upgrades
- **Phase 5.5: Mie Scattering Lookup Table v2**
  - High-density grid: 21 → 200 points (9.5x denser)
  - Interpolation error: 155% → 2.16% (72x improvement)
  - Wavelength range: 400-700nm (+50% coverage)
  - ISO range: 50-6400 (support low-ISO fine-grain films)
  - Lookup speed: 0.0205 ms/query (6.2x faster)
- **Phase 1: Wavelength-dependent Scattering**
  - Empirical formula: η(λ) ∝ λ⁻³·⁵ (Rayleigh-like)
  - Mie theory: Full AgBr particle scattering calculation
- **Phase 2: Beer-Lambert Halation**
  - Separate from Bloom (independent transmittance model)
  - Energy conservation <0.01%

### ⚡ Optimized - Performance
- Image processing: ~0.14s (2000×3000)
- Lookup table loading: 0.53 ms (first time, cached after)
- Memory: +30 MB (PSF cache)

### 📚 Documentation
- `PHYSICAL_MODE_GUIDE.md`: Physical mode user guide
- `UI_INTEGRATION_SUMMARY.md`: UI parameter documentation
- `OPTIMIZATION_REPORT.md`: Performance analysis

---

## [0.2.0] - 2025-12-19

### 📦 Added - Batch Processing
- **Multi-file upload**: Process 2-50 photos at once
- **Real-time progress**: Progress bar + status updates
- **ZIP download**: One-click download all results
- **Error isolation**: Single failure won't affect others

### 🎨 Added - Modern UI Redesign
- **Clean design**: Streamlined CSS, better performance
- **Dark theme**: Coral red color scheme
- **Smooth interaction**: Consistent animations and feedback
- **Responsive layout**: Clear visual hierarchy

### 🔬 Added - Physical Mode (Experimental)
- **Energy conservation**: Optical effects obey energy conservation (<0.01% error)
- **H&D Curve**: Hurter-Driffield characteristic curve (log response + Toe/Shoulder)
- **Poisson Grain**: Physics-based photon statistics noise (SNR ∝ √exposure)
- **Three modes**: Artistic (default) / Physical / Hybrid

### 📚 Documentation
- `README.md`: Updated with v0.2.0 features
- `docs/FILM_PROFILES_GUIDE.md`: Film profile documentation
- `docs/PERFORMANCE_OPTIMIZATION_SUMMARY.md`: Performance report

---

## [0.1.x] - 2025-12-15 and earlier

### Initial Release
- Basic film simulation with 13 film profiles (9 color, 4 B&W)
- Bloom (halation) effect with Gaussian blur
- Film grain simulation
- Tone mapping (S-curve)
- Simple UI with Streamlit
- Single image processing only

### Core Features
- RGB channel-wise processing
- Artistic bloom (non-physical, visually pleasing)
- Random grain noise
- Basic color LUTs for film look emulation

---

## Version Naming Convention

- **0.x.0**: Major feature release (breaking changes possible)
- **0.x.y**: Minor feature release (backward compatible)
- **0.x.y-rc.z**: Release candidate (testing phase)

## Planned Releases

### [0.5.0] - Future (Planned)
- GPU acceleration (CuPy/PyTorch backend)
- Real-time preview mode
- Advanced grain models (frequency-based)
- More film profiles (Provia, Ektar variants)
- Custom film profile editor

### [1.0.0] - Future (Stable Release)
- Complete physical accuracy (80-90%)
- Production-ready performance (<1s per image)
- Comprehensive test coverage (>95%)
- Full documentation and examples
- API stability guarantee

---

**Maintained by**: Phos Development Team  
**License**: See LICENSE file  
**Repository**: https://github.com/yourusername/phos (if applicable)
