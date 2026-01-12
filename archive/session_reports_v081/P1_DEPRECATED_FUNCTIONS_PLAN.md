# P1 Task: Mark and Remove Deprecated Functions

## 目標
標記並規劃移除 Phos.py 中已被重構但仍保留的過時函數，減少代碼冗餘。

---

## 🔍 發現的過時函數

### 1. `apply_bloom_mie_corrected()` (Line ~680-800)
**狀態**: ⚠️ **完全未使用** - 候選刪除

**原因**:
- 已被重構到 `bloom_strategies.py::MieCorrectedBloomStrategy`
- 無任何調用（0 references）
- 完全重複的功能

**影響評估**:
- **風險**: 低（無調用）
- **測試覆蓋**: bloom_strategies 已有完整測試（21 tests, 100% pass）
- **向後相容**: 不影響（已通過 `apply_bloom()` 統一介面）

**行動計劃**:
1. 添加 `@deprecated` decorator
2. 添加 docstring 警告，指向新介面
3. 設定刪除時間表（v0.7.0）
4. 確認測試通過
5. v0.7.0 時刪除

### 2. `apply_bloom_with_psf()` (Line ~640-680)
**狀態**: ⚠️ **部分使用** - 候選重構

**使用情況**:
- 3 個調用點（需進一步檢查）
- 可能被 `bloom_strategies.py::PhysicalBloomStrategy` 取代

**行動計劃**:
1. 檢查 3 個調用點的上下文
2. 如果可以遷移到 `apply_bloom()`，則標記為 deprecated
3. 否則保留但添加註釋說明使用場景

### 3. `apply_wavelength_bloom()` (Line ~740-780)
**狀態**: ⚠️ **部分使用** - 候選重構

**使用情況**:
- 2 個調用點（需進一步檢查）
- 可能被 `bloom_strategies.py` 取代

**行動計劃**:
1. 檢查 2 個調用點的上下文
2. 評估是否可以遷移到統一介面

### 4. 註釋標記的「舊版函數」區域

**Location 1** (Line 329-330):
```python
# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 generate_grain() 統一介面
```
- **函數**: `apply_grain()`
- **實際狀態**: ❌ **標記錯誤** - 這個函數仍在活躍使用中
- **行動**: 移除「舊版函數」標記，因為這是主要的 grain 介面

**Location 2** (Line 567-568):
```python
# ==================== 舊版函數（向後相容，標記為棄用）====================
# 注意：以下函數保留以維持向後相容性，但建議使用 apply_bloom() 統一介面
```
- **函數**: `create_dual_kernel_psf()`, `apply_bloom_with_psf()`, etc.
- **實際狀態**: ⚠️ **部分過時**
  - `create_dual_kernel_psf()`: 仍在使用（被 bloom_strategies 調用）
  - `apply_bloom_mie_corrected()`: 完全未使用（候選刪除）
- **行動**: 更新註釋，只標記真正過時的函數

---

## 📋 實施步驟

### Phase 1: 調查與標記 (估計 30 分鐘)

#### Step 1.1: 檢查函數調用情況
```bash
# 檢查 apply_bloom_with_psf 的調用
rg "apply_bloom_with_psf\\(" --type py -C 3

# 檢查 apply_wavelength_bloom 的調用
rg "apply_wavelength_bloom\\(" --type py -C 3
```

#### Step 1.2: 創建 deprecated decorator
在 `Phos.py` 頂部添加：
```python
import warnings
from functools import wraps

def deprecated(reason: str, replacement: str = None, remove_in: str = None):
    """
    標記函數為過時
    
    Args:
        reason: 過時原因
        replacement: 建議的替代方案
        remove_in: 預計移除版本
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            msg = f"{func.__name__} is deprecated. {reason}"
            if replacement:
                msg += f" Use {replacement} instead."
            if remove_in:
                msg += f" Will be removed in {remove_in}."
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

#### Step 1.3: 標記確定過時的函數
```python
@deprecated(
    reason="This function has been refactored into bloom_strategies.MieCorrectedBloomStrategy",
    replacement="apply_bloom(lux, bloom_params) with mode='mie_corrected'",
    remove_in="v0.7.0"
)
def apply_bloom_mie_corrected(...):
    ...
```

### Phase 2: 測試驗證 (估計 10 分鐘)

```bash
# 運行所有測試，確認沒有破壞
pytest tests_refactored/ -v

# 檢查是否有 DeprecationWarning
pytest tests_refactored/ -W error::DeprecationWarning
```

### Phase 3: 文檔更新 (估計 10 分鐘)

1. 更新 `CHANGELOG.md`：
   ```markdown
   ### v0.6.4 - Deprecated Functions
   
   **Deprecated**:
   - `apply_bloom_mie_corrected()`: Use `apply_bloom()` with `mode='mie_corrected'`
   - Will be removed in v0.7.0
   ```

2. 更新 `BREAKING_CHANGES_v06.md`（如果需要）

3. 創建 `DEPRECATION_TIMELINE.md`：
   ```markdown
   # Deprecation Timeline
   
   | Function | Deprecated In | Remove In | Replacement |
   |----------|---------------|-----------|-------------|
   | apply_bloom_mie_corrected | v0.6.4 | v0.7.0 | apply_bloom() |
   ```

### Phase 4: Commit (估計 5 分鐘)

```bash
git add Phos.py CHANGELOG.md DEPRECATION_TIMELINE.md
git commit -m "refactor(v0.6.4): mark apply_bloom_mie_corrected as deprecated

- Add @deprecated decorator for proper deprecation warnings
- Function will be removed in v0.7.0
- Users should use apply_bloom() with mode='mie_corrected' instead
- All functionality preserved via bloom_strategies module

Tests: 303/303 passed (100%)
Breaking: None (deprecation warning only)"
```

---

## 🎯 成功指標

- [ ] 所有過時函數標記為 `@deprecated`
- [ ] 測試 100% 通過（無破壞性變更）
- [ ] 文檔更新完成（CHANGELOG, DEPRECATION_TIMELINE）
- [ ] 創建 v0.7.0 刪除計劃
- [ ] 向後相容性 100%（僅警告，不破壞）

---

## ⏰ 預計時間

- **Phase 1**: 30 分鐘（調查與標記）
- **Phase 2**: 10 分鐘（測試驗證）
- **Phase 3**: 10 分鐘（文檔更新）
- **Phase 4**: 5 分鐘（Commit）
- **Total**: ~55 分鐘

---

## 🔗 關聯任務

- **P0-1**: Strategy Pattern Refactoring（已完成） - 創建了新的 bloom_strategies
- **P1-2**: Refactor apply_grain()（下一步） - 可能會產生更多 deprecated functions
- **P2-1**: Code Cleanup（未來） - 實際刪除所有 deprecated functions in v0.7.0

---

## 📝 Notes

### Why Keep Deprecated Functions?
遵循 **"Never Break Userspace"** 原則：
- 給用戶時間遷移（至少一個 minor version）
- 提供清晰的遷移路徑（replacement 參數）
- 避免突然破壞現有代碼

### When to Remove?
在 v0.7.0 (下一個 minor version):
- 所有 deprecated functions 至少有一個版本的緩衝期
- 用戶有充足時間看到 DeprecationWarning
- 文檔已更新，指向新介面

---

**Created**: 2026-01-12  
**Status**: Planning  
**Next Step**: Execute Phase 1.1 (調查函數調用情況)
