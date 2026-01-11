# 測試文件重構計畫

## 📊 現狀分析

**當前結構 (2024-01-11)**:
- 測試文件數: 28 個
- 測試函數數: 299 個
- 總行數: ~10,000 行
- 問題: 文件過多、邏輯重複、維護困難

## 🎯 重構目標

### 原則
1. **Simplicity**: 複雜性是萬惡之源 → 減少文件數量
2. **Single Responsibility**: 每個文件專注單一模組
3. **No Duplication**: 消除重複測試邏輯
4. **Backward Compatible**: 保持覆蓋率不下降 (299 tests → 299 tests)

### 目標結構
**28 files → 12 files** (57% reduction)

---

## 📁 新架構設計

### 核心層級分類

```
tests/
├── conftest.py                           # Pytest fixtures (保持不變)
│
├── 🔬 物理核心 (Physics Core)
│   ├── test_physics_core.py             # ✅ NEW: 合併 3 個文件
│   │   ├── Energy Conservation (5 tests)
│   │   ├── H&D Curve (8 tests)
│   │   └── Poisson Grain (7 tests)
│   │   → 來源: test_energy_conservation.py, test_hd_curve.py, test_poisson_grain.py
│   │
│   └── test_reciprocity.py               # ✅ NEW: 合併 2 個文件
│       ├── Reciprocity Failure (41 tests)
│       └── Integration Tests (18 tests)
│       → 來源: test_reciprocity_failure.py, test_reciprocity_integration.py
│
├── 🌈 光學效果 (Optical Effects)
│   ├── test_optical_effects.py           # ✅ NEW: 合併 4 個文件
│   │   ├── Halation (10 tests)
│   │   ├── Beer-Lambert Model (19 tests)
│   │   ├── Wavelength Bloom (8 tests)
│   │   └── Mie-Halation Integration (檢查重複後保留)
│   │   → 來源: test_halation.py, test_p0_2_halation_beer_lambert.py,
│   │            test_wavelength_bloom.py, test_mie_halation_integration.py
│   │
│   └── test_mie_scattering.py            # ✅ NEW: 合併 3 個文件
│       ├── Mie Lookup (tests)
│       ├── Mie Validation (7 tests)
│       └── Mie Physics (8 tests)
│       → 來源: test_mie_lookup.py, test_mie_validation.py, test_mie_wavelength_physics.py
│
├── 🎞️ 膠片配置 (Film Profiles)
│   ├── test_film_profiles.py             # ✅ NEW: 合併 3 個文件
│   │   ├── Film Models (13 tests)
│   │   ├── ISO Unification (21 tests)
│   │   └── Create Film from ISO (25 tests)
│   │   → 來源: test_film_models.py, test_iso_unification.py, test_create_film_from_iso.py
│   │
│   └── test_spectral_film.py             # ✅ NEW: 合併 4 個文件
│       ├── Film Spectra (tests)
│       ├── Film Spectral Sensitivity (25 tests)
│       ├── Spectral Sensitivity (15 tests)
│       └── RGB to Spectrum (tests)
│       → 來源: test_film_spectra.py, test_film_spectral_sensitivity.py,
│                test_spectral_sensitivity.py, test_rgb_to_spectrum.py
│
├── 🔄 整合測試 (Integration)
│   ├── test_integration_e2e.py           # ✅ NEW: 合併 4 個文件
│   │   ├── Core Integration (6 tests)
│   │   ├── Medium Physics E2E (tests)
│   │   ├── Phase2 Integration (tests)
│   │   └── Spectral Model (22 tests)
│   │   → 來源: test_integration.py, test_medium_physics_e2e.py,
│   │            test_phase2_integration.py, test_spectral_model.py
│   │
│   └── test_colorchecker.py              # 🔄 RENAME: 保持獨立
│       ├── Delta E Validation (tests)
│       → 來源: test_colorchecker_delta_e.py
│
├── ⚡ 效能測試 (Performance)
│   ├── test_performance.py               # 🔄 KEEP: 保持不變
│   │   ├── Benchmark Tests
│   │   └── Memory Tests
│   │
│   └── test_fft_convolution.py           # 🔄 KEEP: 演算法測試
│       ├── FFT Convolution (tests)
│
└── archive/                              # 📦 歸檔舊文件
    └── old_tests/
        ├── test_energy_conservation.py   # 已合併到 test_physics_core.py
        ├── test_hd_curve.py
        ├── test_poisson_grain.py
        └── ...（所有被合併的文件）
```

---

## 📊 文件映射表

| 新文件 | 來源文件 (28 → 12) | 測試數 | 優先級 |
|--------|-------------------|--------|--------|
| `test_physics_core.py` | energy_conservation, hd_curve, poisson_grain | ~20 | P0 🔴 |
| `test_reciprocity.py` | reciprocity_failure, reciprocity_integration | ~59 | P0 🔴 |
| `test_optical_effects.py` | halation, p0_2_halation, wavelength_bloom, mie_halation | ~45 | P0 🔴 |
| `test_mie_scattering.py` | mie_lookup, mie_validation, mie_wavelength_physics | ~20 | P1 🟡 |
| `test_film_profiles.py` | film_models, iso_unification, create_film_from_iso | ~59 | P1 🟡 |
| `test_spectral_film.py` | film_spectra, film_spectral_sensitivity, spectral_sensitivity, rgb_to_spectrum | ~50 | P1 🟡 |
| `test_integration_e2e.py` | integration, medium_physics_e2e, phase2_integration, spectral_model | ~35 | P2 🟢 |
| `test_colorchecker.py` | colorchecker_delta_e | ~10 | P2 🟢 |
| `test_performance.py` | (保持不變) | ~5 | P2 🟢 |
| `test_fft_convolution.py` | (保持不變) | ~5 | P2 🟢 |

**總計**: 28 files → **12 files** (減少 57%)

---

## 🚀 執行計畫

### Phase 1: 核心物理測試 (P0, 1-2 小時)
- [ ] 創建 `test_physics_core.py`
- [ ] 遷移 energy_conservation, hd_curve, poisson_grain
- [ ] 創建 `test_reciprocity.py`
- [ ] 遷移 reciprocity_failure, reciprocity_integration
- [ ] 運行測試確保通過

### Phase 2: 光學效果測試 (P0, 1-2 小時)
- [ ] 創建 `test_optical_effects.py`
- [ ] 遷移 halation, p0_2_halation, wavelength_bloom
- [ ] 創建 `test_mie_scattering.py`
- [ ] 遷移 mie_lookup, mie_validation, mie_wavelength_physics
- [ ] 運行測試確保通過

### Phase 3: 膠片配置測試 (P1, 1 小時)
- [ ] 創建 `test_film_profiles.py`
- [ ] 遷移 film_models, iso_unification, create_film_from_iso
- [ ] 創建 `test_spectral_film.py`
- [ ] 遷移 film_spectra, film_spectral_sensitivity, spectral_sensitivity, rgb_to_spectrum

### Phase 4: 整合測試 (P2, 30 分鐘)
- [ ] 創建 `test_integration_e2e.py`
- [ ] 遷移 integration, medium_physics_e2e, phase2_integration, spectral_model
- [ ] 重命名 colorchecker_delta_e → colorchecker

### Phase 5: 驗證與歸檔 (30 分鐘)
- [ ] 運行完整測試套件: `pytest tests/ -v`
- [ ] 確認覆蓋率: `pytest --cov=. tests/`
- [ ] 歸檔舊文件: `mkdir -p tests/archive/old_tests && mv tests/test_old_*.py tests/archive/`
- [ ] 更新 README.md 測試章節

---

## ✅ 驗證清單

### 測試覆蓋率
- [ ] 測試總數不變: 299 tests
- [ ] 所有測試通過: 0 failed
- [ ] 覆蓋率不下降: ≥98%

### 代碼品質
- [ ] 無重複邏輯 (DRY)
- [ ] 每個文件 < 800 行
- [ ] 清晰的模組邊界

### 文檔更新
- [ ] README.md 測試章節
- [ ] 更新測試執行指令
- [ ] 添加遷移指南

---

## 📝 注意事項

### 向後相容
- **不刪除舊文件**，先歸檔到 `tests/archive/`
- 保留 `conftest.py` 不動（共享 fixtures）
- 遷移後驗證測試 ID 一致性（pytest 使用 node ID）

### 重複邏輯識別
- Halation 測試：`test_halation.py` vs `test_p0_2_halation_beer_lambert.py`
  - 後者是 Beer-Lambert 重構版本，更完整
  - **合併策略**：保留後者的詳細測試，前者的簡單測試作為 smoke tests
  
- Spectral 測試：4 個文件高度重疊
  - **合併策略**：按功能分層（光譜轉換 vs 膠片敏感度）

### 測試命名規範
```python
# 新命名規範（模組_子模組_測試點）
def test_physics_energy_conservation_bloom():
    """測試 Bloom 能量守恆"""
    ...

def test_optical_halation_beer_lambert_transmittance():
    """測試 Halation Beer-Lambert 穿透率"""
    ...

def test_film_iso_unification_grain_intensity():
    """測試 ISO 統一推導顆粒強度"""
    ...
```

---

## 🎯 成功指標

| 指標 | 目標 | 現狀 | 進度 |
|------|------|------|------|
| 文件數量 | ≤12 | 28 | 0% |
| 測試總數 | 299 | 299 | ✅ |
| 平均文件行數 | ~500 | ~360 | ⚠️ (會增加) |
| 重複邏輯 | 0% | ~15% | 0% |
| 執行時間 | <30s | ~25s | ✅ |

**最終目標**: 減少 57% 文件，保持 100% 覆蓋率，提升 50% 可維護性

---

**創建時間**: 2024-01-11  
**預計完成**: 2024-01-11 (4-5 小時)  
**負責人**: AI Assistant
