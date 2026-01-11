# TASK-011: Beer-Lambert 參數標準化 (P1-4)

## 任務 ID
**TASK-011**  
**優先級**: 🟡 P1 (重要物理改進)  
**預估時間**: 1-2 天  
**創建時間**: 2025-12-24 06:50  
**負責人**: Main Agent

---

## 任務目標

標準化 Halation 模塊中的 Beer-Lambert 定律參數命名與計算邏輯，消除當前的命名混亂與物理不一致性。

**Physics Score 目標**: 8.5 → 8.7/10 (+0.2)

---

## 背景與動機

### 當前問題 (來自 PHYSICS_IMPROVEMENTS_ROADMAP.md)

```python
# film_models.py Line 165-173
# ❌ 命名混亂
HalationParams(
    wavelength_attenuation_r=0.7,  # 這是透過率？還是衰減係數？
    transmittance_r=0.7,  # 與上面重複？
    ah_absorption=0.95,  # 吸收率 = 1 - 透過率？
)
```

**核心問題**:
1. **參數命名不一致**: `attenuation` vs `transmittance` vs `absorption` 混用
2. **物理意義不明**: 是「單程」還是「雙程」？是「係數」還是「比例」？
3. **缺少單位註解**: 吸收係數 α (cm⁻¹) 還是透過率 T (無量綱)？
4. **雙程路徑未明確**: Halation 光線往返穿透乳劑 + 片基 + AH 層

### 物理基礎: Beer-Lambert 定律

$$
T(\lambda) = \exp(-\alpha(\lambda) \cdot L)
$$

- **T(λ)**: 透過率 (0-1, 無量綱)
- **α(λ)**: 吸收係數 (cm⁻¹ 或 μm⁻¹)
- **L**: 光程長度 (cm 或 μm)

### Halation 雙程光路

```
    ↓ 入射光 (I₀)
┌─────────────────┐
│   乳劑層 (T_em)  │ ← 單程穿透 T_em
├─────────────────┤
│  AH 層 (T_ah)   │ ← 單程穿透 T_ah
├─────────────────┤
│  片基 (反射 R)   │ ← 反射率 R
├─────────────────┤
│  AH 層 (T_ah)   │ ← 返程穿透 T_ah
├─────────────────┤
│   乳劑層 (T_em)  │ ← 返程穿透 T_em
└─────────────────┘
    ↑ Halation 光 (I_halo)
```

**Halation 能量分數**:
$$
f_{halo}(\lambda) = T_{em}^2(\lambda) \cdot T_{ah}^2(\lambda) \cdot R
$$

---

## 輸入與依賴

### 輸入
1. **當前參數結構**: `film_models.py` (Line 165-280, HalationParams)
2. **物理理論**: Beer-Lambert 定律
3. **真實數據** (參考):
   - CineStill 800T: 無 AH 層 → 紅光 Halation 強烈
   - Kodak Portra 400: 有 AH 層 → Halation 極弱
   - Fuji Pro 400H: 部分 AH 層 → 中等 Halation

### 依賴
- `film_models.py`: 主要修改目標
- `phos_core.py`: Halation 計算邏輯
- `tests/test_halation.py`: 現有測試套件
- `tests/test_p0_2_halation_beer_lambert.py`: Beer-Lambert 驗證

---

## 實作計畫

### Phase 1: 物理模型設計 (3 hours)

**子任務**:
1. 委派 **Physicist** 審查當前參數命名與物理一致性
2. 設計標準化參數結構（含單位、物理意義、雙程路徑）
3. 建立計算公式（透過率 → 散射能量分數）

**產出**:
- `physicist_review.md`: 物理審查報告
- `phase1_design.md`: 標準化設計文檔

**驗收標準**:
- ✅ 參數命名明確（transmittance, absorption_coefficient, path_length）
- ✅ 單位註解完整（無量綱 vs cm⁻¹）
- ✅ 雙程路徑公式明確
- ✅ Physicist 批准設計

---

### Phase 2: 代碼重構 (4 hours)

**子任務**:
1. 重構 `HalationParams` dataclass
2. 更新 `phos_core.py` 中的 Halation 計算邏輯
3. 更新所有膠片配置（22 個 FilmProfile）

**產出**:
- 修改 `film_models.py` (HalationParams 定義)
- 修改 `phos_core.py` (計算邏輯)
- 更新所有膠片配置參數

**驗收標準**:
- ✅ 所有參數有明確物理意義
- ✅ 計算邏輯符合 Beer-Lambert 雙程公式
- ✅ 向後相容（保留舊參數映射）
- ✅ 代碼風格一致（type hints, docstrings）

---

### Phase 3: 物理驗證測試 (3 hours)

**子任務**:
1. 更新 `tests/test_p0_2_halation_beer_lambert.py`
2. 新增雙程路徑驗證測試
3. 新增 CineStill 紅光 Halation 特徵測試
4. 能量守恆驗證

**產出**:
- 更新測試套件（新增 10+ 測試案例）
- 測試執行報告

**驗收標準**:
- ✅ 所有現有測試保持通過 (180+)
- ✅ 新增測試覆蓋雙程路徑 (5+ tests)
- ✅ CineStill vs Portra Halation 差異驗證 (2+ tests)
- ✅ 能量守恆: f_halo < 0.5 (單通道)

---

### Phase 4: 數值驗證與參數校準 (4 hours)

**子任務**:
1. 計算所有膠片的有效 Halation 能量分數
2. 驗證 CineStill 800T 紅光主導特性
3. 驗證 Portra 400 Halation 抑制特性
4. 微調參數以符合真實膠片特徵

**產出**:
- `phase4_calibration_report.md`: 參數校準報告
- 更新膠片配置（如需要）

**驗收標準**:
- ✅ CineStill 800T: f_halo_red > 0.15 (紅光明顯)
- ✅ Portra 400: f_halo_red < 0.05 (Halation 抑制)
- ✅ Velvia 50: f_halo < 0.03 (極弱 Halation)
- ✅ 所有膠片能量守恆

---

### Phase 5: 文檔更新 (2 hours)

**子任務**:
1. 更新 `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md` (Halation 章節)
2. 更新 `decisions_log.md` (Decision #029)
3. 更新 `PHYSICS_IMPROVEMENTS_ROADMAP.md` (P1-4 完成)
4. 創建完成報告

**產出**:
- 更新技術文檔
- Decision #029: Beer-Lambert 參數標準化
- `completion_report.md`

**驗收標準**:
- ✅ 技術文檔包含標準化參數定義
- ✅ 決策日誌記錄修改依據
- ✅ 路線圖標記 P1-4 完成
- ✅ Physics Score 更新至 8.7/10

---

## 驗收標準

### 1. 代碼品質
- ✅ 參數命名一致（transmittance, absorption_coefficient, reflectance）
- ✅ 所有參數有單位註解與物理意義
- ✅ 雙程路徑計算明確
- ✅ Type hints 完整
- ✅ Docstrings 詳細

### 2. 物理正確性
- ✅ Beer-Lambert 公式正確
- ✅ 雙程路徑能量計算正確
- ✅ 能量守恆驗證通過
- ✅ CineStill 紅光 Halation 特徵明顯
- ✅ Portra Halation 抑制明顯

### 3. 測試覆蓋率
- ✅ 所有現有測試保持通過 (180+)
- ✅ 新增雙程路徑測試 (5+)
- ✅ 新增膠片特徵驗證測試 (3+)
- ✅ 測試通過率 100%

### 4. 文檔完整性
- ✅ 技術文檔更新
- ✅ 決策日誌記錄
- ✅ 路線圖更新
- ✅ 完成報告創建

### 5. 效能指標
- ✅ 計算時間無明顯增加 (< 5%)
- ✅ 記憶體占用無增加
- ✅ 代碼行數減少或持平（消除冗餘）

---

## 已知限制與風險

### 已知限制
1. **缺少真實測試數據**: 無法精確校準每種膠片的 AH 層參數
2. **單層 AH 假設**: 真實 AH 層可能是多層結構（灰度漸變）
3. **忽略角度依賴**: 當前假設垂直入射，未考慮邊緣光線

### 風險與緩解

| 風險 | 機率 | 影響 | 緩解策略 |
|------|------|------|---------|
| **參數校準不準確** | 🟡 中 | 🟡 中 | 基於文獻與視覺對比微調 |
| **現有測試失敗** | 🟡 中 | 🔴 高 | 保留向後相容映射 |
| **效能退化** | 🟢 低 | 🟡 中 | 優化計算邏輯 |
| **視覺效果變化** | 🟡 中 | 🟡 中 | 提供回滾機制 |

---

## 時間盒限制

**總計**: 1-2 天 (16 小時)

| Phase | 預估時間 | 時間盒上限 |
|-------|---------|-----------|
| Phase 1: 物理設計 | 3h | 4h |
| Phase 2: 代碼重構 | 4h | 6h |
| Phase 3: 測試驗證 | 3h | 4h |
| Phase 4: 參數校準 | 4h | 5h |
| Phase 5: 文檔更新 | 2h | 3h |

**若超過時間盒**: 評估是否降級至 P2 優先級，或拆分為多個子任務

---

## 參考資料

### 文獻
- Bohren & Huffman (1983). *Absorption and Scattering of Light by Small Particles*.
- Hunt, R. W. G. (2004). *The Reproduction of Colour*, 6th ed. Chapter 18.

### 內部文檔
- `COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md` - Halation 理論
- `tasks/TASK-003-medium-physics/phase2_completion_report.md` - P0-2 Halation 實作
- `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md` - P1-4 問題描述

### 相關決策
- Decision #021: TASK-003 P0-2 Halation Beer-Lambert 模型
- Decision #029: (本次) Beer-Lambert 參數標準化

### 真實案例參考
- **CineStill 800T**: 無 AH 層，紅光 Halation 極強（霓虹燈效果）
- **Kodak Portra 400**: 有 AH 層，Halation 幾乎不可見
- **Fuji Pro 400H**: 部分 AH 層，中等 Halation

---

## Gate 條件

### Physics Gate (必須通過)
- ✅ Physicist 批准參數標準化設計
- ✅ Beer-Lambert 雙程公式物理正確
- ✅ 能量守恆驗證通過

### Debug Gate (必須通過)
- ✅ 所有現有測試保持通過
- ✅ 新增測試覆蓋關鍵路徑
- ✅ 無 NaN 或數值異常

### Performance Gate (必須通過)
- ✅ 計算時間增加 < 5%
- ✅ 記憶體占用無增加

### Reviewer Gate (最後檢查)
- ✅ 代碼風格一致
- ✅ 文檔完整
- ✅ 可維護性提升

**若任一 Gate 未通過**: 退回修正或開新子任務

---

## 下一步行動

### 立即執行 (P0)
1. ⏳ 委派 Physicist 審查當前 HalationParams 物理一致性
2. ⏳ 設計標準化參數結構（Phase 1）

### 短期 (P1)
3. ⏳ 實作代碼重構（Phase 2）
4. ⏳ 執行物理驗證測試（Phase 3）
5. ⏳ 參數校準與視覺驗證（Phase 4）

### 長期 (P2+)
6. ⏸️ 多層 AH 結構建模（進階）
7. ⏸️ 角度依賴散射（進階）

---

## 成功標準

**最小成功** (MVP):
- ✅ 參數命名標準化
- ✅ 雙程路徑計算正確
- ✅ 所有測試通過
- ✅ Physics Score +0.1

**完全成功**:
- ✅ 參數校準準確
- ✅ CineStill vs Portra 特徵明顯
- ✅ 代碼可維護性提升
- ✅ Physics Score +0.2

---

**任務創建**: 2025-12-24 06:50  
**負責**: Main Agent  
**狀態**: 📋 PLANNED → 等待 Physics Gate
