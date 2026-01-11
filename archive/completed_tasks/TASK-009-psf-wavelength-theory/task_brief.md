# TASK-009: PSF 波長依賴理論嚴格推導 (P1-1)

## 任務概述
**優先級**: P1 (重要物理改進)  
**目標**: 將 PSF 波長依賴從經驗公式改為基於 Mie 散射理論的嚴格推導  
**預期時間**: 2-3 天  
**Physics Score Impact**: 8.0 → 8.3 (+0.3)

---

## 背景與動機

### 當前問題 (Phase 1 實作)

**現有實作** (`Phos.py` 或早期版本):
```python
# 經驗公式
wavelength_power = 3.5  # η(λ) ∝ λ^-3.5
radius_power = 0.8      # σ(λ) ∝ λ^-0.8
```

**物理問題**:
1. **λ^-3.5 介於 Rayleigh (λ^-4) 與 Mie (λ^-1 to λ^-2) 之間**
   - 但 AgBr 粒徑 0.5-3μm 時，多數在 Mie 範圍（x=2πa/λ ≈ 3-20）
   - 應基於 Mie 理論而非插值猜測

2. **PSF 半徑 ∝ λ^-0.8 缺乏理論支持**
   - 應從 Mie 角度分布推導
   - 或從 Mie lookup table 直接查詢

3. **與 Mie lookup table 不一致**
   - 已有 `data/mie_lookup_table_v2.npz` (10λ × 20ISO)
   - 但未在所有配置中統一使用
   - 仍有配置使用經驗公式

---

## 目標與驗收標準

### 功能目標
1. ✅ **選項 A: 全面啟用 Mie 查表** (推薦)
   - 將所有彩色膠片配置改為 `use_mie_lookup=True`
   - 棄用經驗公式分支
   - 統一使用 `lookup_mie_params(wavelength, iso)`

2. ⏳ **選項 B: 分段模型** (備選，若需快速模式)
   ```python
   if particle_size < 0.3:  # Rayleigh
       eta = k * wavelength**(-4)
       sigma_angular = constant
   elif particle_size < 2.0:  # Mie transition
       eta, sigma = mie_lookup(particle_size, wavelength)
   else:  # Large particle (geometric)
       eta = k * wavelength**(-1)
       sigma = forward_scattering_approx(particle_size, wavelength)
   ```

### 驗收標準

#### Phase 1: 現狀調查與分析 (4 小時)
- [ ] 統計當前使用 `use_mie_lookup=True` vs `False` 的膠片數量
- [ ] 對比經驗公式 vs Mie 查表的 η(λ) 差異（百分比）
- [ ] 分析 `data/mie_lookup_table_v2.npz` 覆蓋範圍（ISO 50-6400, λ 400-700nm）
- [ ] 記錄到 `phase1_analysis.md`

#### Phase 2: 全面啟用 Mie 查表 (6 小時)
- [ ] 修改所有彩色膠片配置: `use_mie_lookup=True`
- [ ] 更新預設值: `WavelengthBloomParams(use_mie_lookup=True)`
- [ ] 移除或標記棄用經驗公式分支（保留註解以便回滾）
- [ ] 單元測試: 驗證所有配置正確載入 Mie 查表

#### Phase 3: 物理驗證 (4 小時)
- [ ] **η(450nm) / η(650nm) 範圍測試**: 應在 1.5-4.0（視 ISO 而定）
- [ ] **σ(450nm) / σ(650nm) 範圍測試**: 應在 1.2-2.0
- [ ] **能量守恆**: 總散射能量 < 15% (scatter_ratio 上限)
- [ ] **Mie 振盪特徵**: η(λ) 應有非單調變化（x ≈ 5-10 範圍）

#### Phase 4: 視覺驗證 (3 小時)
- [ ] 創建對比腳本: 經驗公式 vs Mie 查表
- [ ] 測試場景:
  - 藍天（藍光散射主導）
  - 霓虹燈（紅光散射主導）
  - 灰階梯度（中性場景）
- [ ] 測量差異: PSNR, SSIM, 色相偏移
- [ ] 記錄到 `phase4_visual_comparison.md`

#### Phase 5: 效能測試 (2 小時)
- [ ] 基準測試: 2000×3000 影像處理時間
- [ ] 對比: 經驗公式 vs Mie 查表開銷
- [ ] 目標: Mie 查表開銷 < +10% (預期 ~0.2ms/次)
- [ ] 記錄到 `phase5_performance.md`

#### Phase 6: 文檔更新 (2 小時)
- [ ] 更新 `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md`: 移除經驗公式說明，添加 Mie 查表章節
- [ ] 更新 `PHYSICAL_MODE_GUIDE.md`: 用戶無需手動選擇，預設啟用
- [ ] 更新 `PHYSICS_IMPROVEMENTS_ROADMAP.md`: 標記 Item #3 完成
- [ ] 創建 `tasks/TASK-009-psf-wavelength-theory/completion_report.md`

---

## 實作計畫

### 階段 1: 現狀調查 (4 小時)

**調查內容**:
1. 搜尋所有 `use_mie_lookup` 出現位置
2. 統計 `*_MediumPhysics` 配置數量
3. 檢查是否有硬編碼 `wavelength_power=3.5` 的地方

**輸出**: `phase1_analysis.md`

---

### 階段 2: 全面啟用 Mie 查表 (6 小時)

**修改檔案**: `film_models.py`

**變更清單**:
1. **更新預設值** (Line ~213):
   ```python
   @dataclass
   class WavelengthBloomParams:
       use_mie_lookup: bool = True  # 改為 True
       mie_lookup_path: str = "data/mie_lookup_table_v2.npz"
   ```

2. **更新所有膠片配置** (8 款彩色膠片):
   ```python
   # Portra400, Ektar100, Cinestill800T, Velvia50,
   # Gold200, ProImage100, Superia400, NC200
   wavelength_bloom_params=WavelengthBloomParams(
       use_mie_lookup=True,  # 統一啟用
       iso_value=400
   )
   ```

3. **標記經驗公式分支為 deprecated** (`Phos.py` or `phos_core.py`):
   ```python
   if wavelength_bloom_params.use_mie_lookup:
       # Mie 查表分支（推薦）
       eta_r, sigma_r, kappa_r, rho_r = lookup_mie_params(...)
   else:
       # ⚠️ DEPRECATED: 經驗公式（保留以便回滾）
       warnings.warn("經驗公式已棄用，請使用 use_mie_lookup=True")
       eta_r = ... λ^-3.5
   ```

**測試**:
```bash
python3 -c "
from film_models import FILM_PROFILES
for name, profile in FILM_PROFILES.items():
    if profile.wavelength_bloom_params:
        print(f'{name}: use_mie={profile.wavelength_bloom_params.use_mie_lookup}')
"
# 預期: 所有彩色膠片輸出 True
```

**輸出**: `phase2_implementation.md`

---

### 階段 3: 物理驗證 (4 小時)

**創建測試**: `tests/test_mie_wavelength_physics.py`

```python
import pytest
import numpy as np
from phos_core import lookup_mie_params

class TestMieWavelengthPhysics:
    """驗證 Mie 查表的物理一致性"""
    
    def test_eta_ratio_bounds(self):
        """η(450nm) / η(650nm) 應在 1.5-4.0 範圍"""
        for iso in [100, 400, 800, 1600]:
            eta_b, _, _, _ = lookup_mie_params(wavelength=450, iso=iso)
            eta_r, _, _, _ = lookup_mie_params(wavelength=650, iso=iso)
            ratio = eta_b / eta_r
            assert 1.5 <= ratio <= 4.0, f"ISO {iso}: η_b/η_r = {ratio:.2f}"
    
    def test_sigma_ratio_bounds(self):
        """σ(450nm) / σ(650nm) 應在 1.2-2.0 範圍"""
        for iso in [100, 400, 800]:
            _, sigma_b, _, _ = lookup_mie_params(wavelength=450, iso=iso)
            _, sigma_r, _, _ = lookup_mie_params(wavelength=650, iso=iso)
            ratio = sigma_b / sigma_r
            assert 1.2 <= ratio <= 2.0, f"ISO {iso}: σ_b/σ_r = {ratio:.2f}"
    
    def test_mie_oscillation_presence(self):
        """驗證 Mie 振盪特徵（非單調）"""
        wavelengths = np.linspace(400, 700, 30)
        etas = [lookup_mie_params(wl, iso=400)[0] for wl in wavelengths]
        
        # 計算一階導數，應有正負變化
        deta = np.diff(etas)
        sign_changes = np.sum(np.diff(np.sign(deta)) != 0)
        
        assert sign_changes >= 2, "缺少 Mie 振盪特徵"
    
    def test_energy_conservation(self):
        """總散射能量不超過 scatter_ratio 上限"""
        for iso in [100, 400, 1600]:
            eta_r, _, _, _ = lookup_mie_params(650, iso)
            eta_g, _, _, _ = lookup_mie_params(550, iso)
            eta_b, _, _, _ = lookup_mie_params(450, iso)
            
            # 平均能量（簡化）
            avg_eta = (eta_r + eta_g + eta_b) / 3
            assert avg_eta < 0.15, f"ISO {iso}: avg_eta = {avg_eta:.3f} > 15%"
```

**運行測試**:
```bash
pytest tests/test_mie_wavelength_physics.py -v
```

**輸出**: `phase3_physics_validation.md`

---

### 階段 4: 視覺驗證 (3 小時)

**創建腳本**: `scripts/compare_empirical_vs_mie.py`

```python
"""
對比經驗公式 vs Mie 查表的視覺效果
"""
import cv2
import numpy as np
from phos_core import process_image_spectral_mode
from film_models import get_film_profile

def compare_modes(input_image_path: str, output_dir: str):
    """處理同一影像，對比兩種方法"""
    
    # 載入測試影像
    img = cv2.imread(input_image_path)
    
    # 方法 1: 經驗公式（臨時修改配置）
    film = get_film_profile("Portra400")
    film.wavelength_bloom_params.use_mie_lookup = False
    result_empirical = process_image_spectral_mode(img, film)
    
    # 方法 2: Mie 查表
    film.wavelength_bloom_params.use_mie_lookup = True
    result_mie = process_image_spectral_mode(img, film)
    
    # 計算差異
    diff = cv2.absdiff(result_mie, result_empirical)
    psnr = cv2.PSNR(result_mie, result_empirical)
    
    # 保存結果
    cv2.imwrite(f"{output_dir}/empirical.png", result_empirical)
    cv2.imwrite(f"{output_dir}/mie.png", result_mie)
    cv2.imwrite(f"{output_dir}/diff.png", diff * 5)  # 放大差異
    
    print(f"PSNR: {psnr:.2f} dB")
    print(f"Mean difference: {np.mean(diff):.2f}")
```

**測試場景**:
1. 藍天影像（test_blue_sky.jpg）
2. 霓虹燈夜景（test_neon.jpg）
3. 灰階梯度（test_gradient.png）

**輸出**: `phase4_visual_comparison.md` + PNG 對比圖

---

### 階段 5: 效能測試 (2 小時)

**創建測試**: `tests/test_mie_performance.py`

```python
import time
import numpy as np
from phos_core import lookup_mie_params

def test_lookup_performance():
    """測試 Mie 查表效能"""
    
    # 模擬 1000 次查詢（處理一張影像的典型次數）
    start = time.perf_counter()
    for _ in range(1000):
        eta, sigma, kappa, rho = lookup_mie_params(
            wavelength=np.random.uniform(400, 700),
            iso=np.random.choice([100, 400, 800])
        )
    elapsed = time.perf_counter() - start
    
    avg_time_ms = elapsed / 1000 * 1000
    print(f"Average lookup time: {avg_time_ms:.4f} ms")
    assert avg_time_ms < 0.5, f"查表過慢: {avg_time_ms:.4f} ms > 0.5 ms"
```

**輸出**: `phase5_performance.md`

---

## 風險評估與回滾策略

### 風險 1: 視覺效果差異過大
**可能性**: 中  
**影響**: 高（用戶可能偏好經驗公式的視覺效果）

**緩解策略**:
- 保留經驗公式分支（標記 deprecated）
- 添加配置選項 `WavelengthBloomParams.force_empirical_formula=True`
- 在 UI 中添加「使用經驗公式」checkbox（進階選項）

**回滾步驟**:
```bash
git revert <commit-hash>
# 或手動改回: use_mie_lookup=False
```

### 風險 2: Mie 查表覆蓋範圍不足
**可能性**: 低  
**影響**: 中（某些極端 ISO 或波長無法查詢）

**當前覆蓋**:
- ISO: 50-6400 (20 點)
- 波長: 400-700nm (10 點)
- 雙線性插值精度: η 平均誤差 2.16%

**緩解策略**:
- 在查表函數中添加邊界檢查
- 超出範圍時回退經驗公式 + 發出 warning

### 風險 3: 效能退化
**可能性**: 低  
**影響**: 低（當前插值僅 0.02ms/次）

**預期開銷**:
- 單次查表: ~0.02ms
- 每張影像: ~1000 次查詢 → +20ms
- 相對總時間 (~4s): +0.5%

**緩解策略**:
- 添加 LRU cache (已實作 `@lru_cache`)
- 考慮預先計算常用 ISO 的查表

---

## 預期成果

### 物理正確性提升
- **當前**: 8.0/10 (P0 + P1-2 完成)
- **P1-1 完成後**: **8.3/10** (+0.3)
- **路線圖目標**: 8.5/10 (P1 全部完成)

### 程式碼清理
- 移除經驗公式硬編碼魔術數字 (3.5, 0.8)
- 統一散射模型（Mie 理論）
- 減少條件分支（`if use_mie_lookup` 成為預設）

### 測試覆蓋
- 新增 `test_mie_wavelength_physics.py` (~8 tests)
- 更新 `test_medium_physics_e2e.py` (驗證 Mie 查表路徑)
- 總測試數: 180 → 188 (+4.4%)

---

## 時間線

| 階段 | 預估時間 | 累積時間 | 里程碑 |
|------|---------|---------|-------|
| Phase 1: 現狀調查 | 4 小時 | 4h | `phase1_analysis.md` 完成 |
| Phase 2: 啟用 Mie | 6 小時 | 10h | 所有配置改為 `use_mie_lookup=True` |
| Phase 3: 物理驗證 | 4 小時 | 14h | 8/8 物理測試通過 |
| Phase 4: 視覺驗證 | 3 小時 | 17h | 對比圖生成，PSNR 記錄 |
| Phase 5: 效能測試 | 2 小時 | 19h | 基準測試通過 (<+10%) |
| Phase 6: 文檔更新 | 2 小時 | 21h | Roadmap 標記完成 |
| **總計** | **21 小時** | - | **P1-1 完成** |

**預計完成日期**: 2025-12-26 (3 天後)

---

## 依賴與阻塞

### 依賴項
- ✅ `data/mie_lookup_table_v2.npz` 已生成（Phase 5.2 完成）
- ✅ `lookup_mie_params()` 函數已實作（Phase 5.3）
- ✅ 所有膠片配置已有 `wavelength_bloom_params`（Phase 5.4）

### 阻塞因素
- ❌ 無阻塞

---

## 驗收檢查表

### 功能完整性
- [ ] 所有彩色膠片配置 `use_mie_lookup=True`
- [ ] 經驗公式分支標記為 deprecated
- [ ] 無硬編碼 `wavelength_power=3.5` 殘留

### 測試覆蓋
- [ ] 8/8 物理驗證測試通過
- [ ] 單元測試覆蓋率 > 95%
- [ ] 效能基準測試通過 (<+10%)

### 物理正確性
- [ ] η(450nm)/η(650nm) ∈ [1.5, 4.0]
- [ ] σ(450nm)/σ(650nm) ∈ [1.2, 2.0]
- [ ] Mie 振盪特徵存在（非單調）
- [ ] 能量守恆 < 15%

### 文檔完整性
- [ ] `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md` 更新
- [ ] `PHYSICS_IMPROVEMENTS_ROADMAP.md` Item #3 標記完成
- [ ] `completion_report.md` 創建
- [ ] `context/decisions_log.md` Decision #025 記錄

---

## 相關文件
- **路線圖**: `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md` (Item #3)
- **Mie 實作**: `tasks/TASK-003-medium-physics/phase5_design.md`
- **查表生成**: `scripts/generate_mie_lookup.py`
- **測試**: `tests/test_mie_lookup.py`, `tests/test_mie_validation.py`
- **決策日誌**: `context/decisions_log.md` (Decision #016-018)

---

**任務創建**: 2025-12-23  
**創建者**: Main Agent  
**狀態**: 🟡 Ready to Start  
**Physics Score 目標**: 8.0 → 8.3 (+0.3)
