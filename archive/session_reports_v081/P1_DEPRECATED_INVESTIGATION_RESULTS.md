# P1 Task Update: Deprecated Functions Investigation Results

## 調查結論 (2026-01-12)

經過詳細調查，發現標記為「舊版函數」的代碼**並非全部過時**，而是代表不同的執行路徑。

---

## 🔍 函數狀態詳細分析

### 1. `apply_bloom_mie_corrected()` 
**狀態**: ✅ **確認過時** - 可安全標記為 deprecated

**證據**:
- 0 個調用點（僅有定義）
- 功能已完全被 `bloom_strategies.MieCorrectedBloomStrategy` 取代
- 測試已覆蓋新實作（21 tests, 100% pass）

**行動**: 標記為 `@deprecated`, remove in v0.7.0

---

### 2. `apply_wavelength_bloom()` 
**狀態**: ❌ **仍在使用** - 不可標記為 deprecated

**調用路徑**:
```
optical_processing() (Line 1615)
  └─ if use_wavelength_bloom:  # Legacy medium physics mode
      └─ apply_wavelength_bloom(response_r, response_g, response_b, ...)
```

**使用場景**:
- **條件**: `use_medium_physics=True` AND `wavelength_bloom_params.enabled=True`
- **用途**: Legacy "中等物理模式" (TASK-003 Phase 1+2)
- **區別**: 與新的 `apply_bloom()` (from bloom_strategies) 是**並行路徑**，非重複

**並行執行路徑**:
```python
if use_wavelength_bloom:
    # Path 1: Legacy medium physics (波長依賴)
    bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(...)
    
elif use_physical_bloom:
    # Path 2: New physical mode (策略模式)
    bloom_r = apply_bloom(response_r, film.bloom_params)  # from bloom_strategies
    bloom_g = apply_bloom(response_g, film.bloom_params)
    bloom_b = apply_bloom(response_b, film.bloom_params)
```

**決策**: **保留**，這是向後相容的必要路徑

---

### 3. `apply_bloom_with_psf()`
**狀態**: ❌ **仍在使用** - 不可標記為 deprecated

**調用路徑**:
```
apply_wavelength_bloom() (Line 716-718)
  └─ bloom_r = apply_bloom_with_psf(response_r, eta_r, psf_r, threshold)
  └─ bloom_g = apply_bloom_with_psf(response_g, eta_g, psf_g, threshold)
  └─ bloom_b = apply_bloom_with_psf(response_b, eta_b, psf_b, threshold)
```

**使用場景**:
- 被 `apply_wavelength_bloom()` 內部調用
- 處理單個通道的 PSF 卷積
- Legacy medium physics 模式的核心組件

**決策**: **保留**，作為 `apply_wavelength_bloom()` 的 helper function

---

### 4. `create_dual_kernel_psf()`
**狀態**: ✅ **共享工具** - 新舊代碼都在使用

**調用情況**:
- 被 `apply_wavelength_bloom()` 調用（legacy path）
- 被 `bloom_strategies.py` 測試調用（但實際策略類可能不直接調用）

**決策**: **保留**，這是共享的工具函數

---

## 📊 函數關係圖

```
Phos.py Function Hierarchy
├── optical_processing() [Main entry point]
│   ├─ [Path 1: Legacy Medium Physics]
│   │   ├─ apply_wavelength_bloom()
│   │   │   ├─ create_dual_kernel_psf()  # Shared utility
│   │   │   └─ apply_bloom_with_psf()    # Helper for wavelength bloom
│   │   └─ apply_halation()
│   │
│   ├─ [Path 2: New Physical Mode]
│   │   └─ apply_bloom()  # from bloom_strategies
│   │       ├─ ArtisticBloomStrategy
│   │       ├─ PhysicalBloomStrategy
│   │       └─ MieCorrectedBloomStrategy
│   │
│   └─ [Path 3: Legacy Artistic/Medium]
│       └─ apply_optical_effects_separated()
│
└── [ORPHAN - Truly Deprecated]
    └─ apply_bloom_mie_corrected()  # 0 callers, duplicate of MieCorrectedBloomStrategy
```

---

## ✅ 最終決策

### 可以 Deprecate 的函數
1. ✅ **`apply_bloom_mie_corrected()`** (Line ~1050-1150)
   - 原因: 完全未使用，功能已被 bloom_strategies 取代
   - 行動: 添加 `@deprecated`, 標記 remove in v0.7.0

### 必須保留的函數
1. ❌ **`apply_wavelength_bloom()`** (Line ~730-820)
   - 原因: Legacy medium physics 模式的主要介面
   - 註釋更新: 標明這是 legacy path，建議新代碼使用 `apply_bloom()`

2. ❌ **`apply_bloom_with_psf()`** (Line ~640-680)
   - 原因: `apply_wavelength_bloom()` 的內部 helper
   - 註釋更新: 標明這是 internal helper

3. ❌ **`create_dual_kernel_psf()`** (Line ~575-635)
   - 原因: 共享工具函數
   - 無需修改

---

## 🛠️ 修正的實施計劃

### Step 1: 修正誤導性註釋

**修改 Line 329-330**:
```python
# ❌ Before (誤導)
# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 generate_grain() 統一介面

# ✅ After (準確)
# ==================== Grain Generation ====================
# apply_grain(): 主要的 grain 生成介面，支持 artistic/poisson 模式
```

**修改 Line 567-568**:
```python
# ❌ Before (誤導)
# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 apply_bloom() 統一介面

# ✅ After (準確)
# ==================== Legacy Medium Physics Path ====================
# 注意：以下函數用於 legacy medium physics 模式（wavelength-dependent bloom）
# 新代碼建議使用 apply_bloom() 統一介面（from bloom_strategies）
# 保留原因：向後相容性，現有配置文件可能依賴此路徑
```

### Step 2: 標記真正過時的函數

```python
@deprecated(
    reason="This function has been refactored into bloom_strategies.MieCorrectedBloomStrategy",
    replacement="apply_bloom(lux, bloom_params) with mode='mie_corrected'",
    remove_in="v0.7.0"
)
def apply_bloom_mie_corrected(...):
    """
    **DEPRECATED**: Use apply_bloom() with mode='mie_corrected' instead.
    This function will be removed in v0.7.0.
    
    應用 Mie 散射修正的 Bloom 效果（Decision #014: Phase 1 修正）
    
    [原有 docstring ...]
    """
    # Redirect to new implementation
    return apply_bloom(lux, bloom_params)
```

### Step 3: 添加明確的路徑說明

在 `optical_processing()` 添加註釋：
```python
# Bloom processing - Multiple execution paths
if use_wavelength_bloom:
    # ============ Path 1: Legacy Medium Physics ============
    # Uses wavelength-dependent bloom (TASK-003 Phase 1+2)
    # Functions: apply_wavelength_bloom() + apply_bloom_with_psf()
    # Note: Kept for backward compatibility with existing configs
    bloom_r, bloom_g, bloom_b = apply_wavelength_bloom(...)
    
elif use_physical_bloom:
    # ============ Path 2: New Physical Mode ============
    # Uses strategy pattern (bloom_strategies.py)
    # Recommended for new code
    bloom_r = apply_bloom(response_r, film.bloom_params)
    bloom_g = apply_bloom(response_g, film.bloom_params)
    bloom_b = apply_bloom(response_b, film.bloom_params)
```

---

## 📈 預期成果

### Code Quality
- ✅ 移除誤導性的「舊版函數」標籤
- ✅ 標記 1 個真正過時的函數（`apply_bloom_mie_corrected`）
- ✅ 保留必要的 legacy paths（向後相容）
- ✅ 添加清晰的執行路徑註釋

### Backward Compatibility
- ✅ 100% 向後相容（僅添加 deprecation warning）
- ✅ 現有配置文件繼續正常工作
- ✅ Legacy medium physics 模式仍可用

### Documentation
- ✅ 更新 CHANGELOG.md（v0.6.4）
- ✅ 創建 DEPRECATION_TIMELINE.md
- ✅ 更新函數 docstrings

---

## ⏰ 修正的時間估算

- **Step 1**: 修正註釋（5 分鐘）
- **Step 2**: 添加 `@deprecated` decorator（10 分鐘）
- **Step 3**: 添加執行路徑註釋（5 分鐘）
- **Step 4**: 測試驗證（10 分鐘）
- **Step 5**: 文檔更新（5 分鐘）
- **Step 6**: Commit（5 分鐘）
- **Total**: ~40 分鐘（比原計劃減少 15 分鐘）

---

## 🔑 關鍵學習

### Lesson Learned
> **"標記為'舊版'不等於過時"**  
> 在複雜系統中，可能存在多個並行的執行路徑，每個路徑服務於不同的使用場景。  
> 刪除代碼前必須：
> 1. 確認 0 個調用點（使用 `rg` 搜尋）
> 2. 檢查是否有 legacy 配置依賴
> 3. 評估向後相容性影響

### Philosophy Application
- **Pragmatism ✅**: 保留必要的 legacy paths，避免破壞現有用戶
- **Never Break Userspace ✅**: 即使代碼看起來「舊」，仍可能是必要的
- **Good Taste**: 用清晰的註釋區分 legacy vs new，而非一律刪除

---

**Updated**: 2026-01-12  
**Status**: Investigation Complete → Ready for Implementation  
**Next Step**: Execute Step 1 (修正註釋)
