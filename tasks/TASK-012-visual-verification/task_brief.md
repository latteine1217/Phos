# TASK-012: Visual Verification of Physics Improvements
# 物理改進視覺驗證 (v0.4.0 → v0.4.1)

**Date**: 2025-12-24  
**Priority**: P1 (High - Milestone Verification)  
**Estimated Time**: 0.5-1 day  
**Status**: 🟡 In Progress

---

## 任務目標

驗證累積的 **5 個物理改進** (TASK-003/008/009/010/011) 在視覺效果上的影響，並生成對比文檔供使用者/開發者參考。

---

## 背景

### 累積的物理改進 (v0.4.0 → v0.4.1)

| Task | 改進項目 | Physics Score | 預期視覺影響 |
|------|---------|--------------|-------------|
| **TASK-003** | 介質物理 (Phase 4-5.5) | +0.6 | 光暈擴散更自然，層次更豐富 |
| **TASK-008** | 光譜亮度修正 | +0.0* | 亮度正確，色彩不偏暗 |
| **TASK-009** | Mie PSF 波長依賴 | +0.3 | 藍光外環明顯，紅光核心集中 |
| **TASK-010** | Mie 折射率修正 | +0.2 | 藍光 Halation ↑20×，色彩更中性 |
| **TASK-011** | Beer-Lambert 標準化 | +0.2 | CineStill vs Portra 差異明顯 |
| **總計** | - | **8.5 → 8.7** | **整體色彩/光暈改善** |

*TASK-008 修復 bug，未新增物理，但對視覺影響重大

---

## 驗證策略

### 方法 A: 版本對比 (v0.4.0 vs v0.4.1)
- **挑戰**: 需要 git checkout 回 v0.4.0，重新生成影像
- **優點**: 直接對比，差異明確
- **缺點**: 需要備份當前環境，耗時較長

### 方法 B: Feature Toggle 對比 (推薦)
- **方法**: 創建測試腳本，手動開關物理特性
- **優點**: 快速生成對比，單一環境
- **缺點**: 需要確保 toggle 邏輯正確

### 方法 C: 已有測試輸出對比
- **方法**: 使用 `test_outputs/` 已生成的影像
- **優點**: 最快（無需重新生成）
- **缺點**: 測試輸出可能不完整，缺少關鍵場景

**選擇**: **方法 B (Feature Toggle)** - 平衡速度與準確性

---

## 測試場景設計

### 標準場景 (Standard Scenarios)

| 場景 ID | 描述 | 測試目標 | 關鍵指標 |
|---------|------|---------|---------|
| **S1** | 純色卡 (R/G/B) | 光譜亮度修正 (TASK-008) | 亮度一致性 |
| **S2** | 灰階梯度 (0-100%) | Beer-Lambert 透射率 (TASK-011) | 線性度 |
| **S3** | 高光點源 (白點) | Mie 波長依賴 (TASK-009) | 藍光外環 vs 紅光核心 |
| **S4** | 逆光場景 (藍天) | Mie 折射率 (TASK-010) | 藍光 Halation 強度 |
| **S5** | 人像膚色 | 介質物理 (TASK-003) | 膚色自然度 |

### 邊界場景 (Edge Cases)

| 場景 ID | 描述 | 測試目標 | 風險驗證 |
|---------|------|---------|---------|
| **E1** | 極暗場景 (Lux < 1) | 曝光下限 | NaN/Inf 檢查 |
| **E2** | 極亮場景 (Lux > 1000) | 曝光上限 | 削波檢查 |
| **E3** | 飽和色彩 | 色域邊界 | Gamut clipping |
| **E4** | CineStill 紅暈極端值 | Beer-Lambert | 紅暈半徑 ~18px |
| **E5** | Portra 紅暈弱化 | Beer-Lambert | 紅暈半徑 ~10px |

---

## 執行計畫

### Phase 1: 測試腳本開發 (2-3 hours)

**檔案**: `scripts/visual_verification_v041.py`

**功能**:
1. **輸入影像生成**:
   - 使用 NumPy 生成標準場景 (S1-S5)
   - 載入 `test_outputs/` 中的邊界場景 (E1-E5)

2. **Feature Toggle 機制**:
   ```python
   class PhysicsFeatures:
       enable_mie_wavelength = True   # TASK-009
       enable_mie_v3 = True            # TASK-010
       enable_beer_lambert_v2 = True   # TASK-011
       enable_medium_physics = True    # TASK-003
       enable_spectral_fix = True      # TASK-008
   ```

3. **批次生成**:
   - 每個場景生成 6 個版本 (1 baseline + 5 toggles)
   - 輸出至 `test_outputs/visual_verification_v041/`

4. **元數據記錄**:
   ```python
   metadata = {
       "scene_id": "S3",
       "film": "Portra400_MediumPhysics_Mie",
       "features_enabled": [...],
       "metrics": {
           "mean_brightness": 0.45,
           "blue_halo_radius": 12.3,
           "red_halo_radius": 8.7,
           ...
       }
   }
   ```

**輸出**:
- `visual_verification_v041/` 資料夾
  - `S1_baseline.png`, `S1_mie_wavelength.png`, ...
  - `metadata.json` (所有場景的元數據)

---

### Phase 2: 視覺對比分析 (1-2 hours)

**工具**: Python (Matplotlib) 或 手動 (Preview/Photoshop)

**分析項目**:

#### 2.1 定量指標
| 指標 | 計算方法 | 預期範圍 | 驗收閾值 |
|------|---------|---------|---------|
| 亮度偏移 | `mean(v0.4.1) - mean(v0.4.0)` | -0.05 ~ +0.05 | < 0.1 ✅ |
| 色彩偏移 | `ΔE00(v0.4.1, v0.4.0)` | 2 ~ 8 | < 10 ✅ |
| 紅暈半徑比 | `r_CineStill / r_Portra` | > 1.5× | > 1.3× ✅ |
| 藍光外環強度 | `I_blue_outer / I_red_outer` | > 1.2× | > 1.0× ✅ |

#### 2.2 定性評估
- ✅ 色彩自然度 (膚色/天空/植物)
- ✅ 光暈真實感 (擴散程度/顏色分離)
- ✅ 細節保留 (紋理/邊緣)
- ⚠️ 異常檢查 (色帶/噪點/偽影)

---

### Phase 3: 報告生成 (1 hour)

**產出文檔**:

1. **技術報告** (`visual_verification_report.md`):
   - 對比影像表格 (before/after)
   - 定量指標統計
   - 關鍵發現與風險
   - 建議調整 (如有)

2. **使用者文檔** (`VISUAL_IMPROVEMENTS_V041.md`):
   - 面向使用者的改進說明
   - 視覺對比圖（精選 3-5 張）
   - 膠片選擇建議 (CineStill vs Portra)
   - 參數調整指南

3. **決策日誌更新** (`context/decisions_log.md`):
   - Decision #030: 視覺驗證結果
   - 包含關鍵指標、通過/失敗標準、下一步建議

---

## 驗收標準

### 1. 定量指標
- ✅ 亮度偏移 < 0.1 (10% 容忍)
- ✅ 色彩偏移 ΔE00 < 10 (CIEDE2000)
- ✅ CineStill vs Portra 紅暈比 > 1.3×
- ✅ 藍光外環 vs 紅光核心比 > 1.0×
- ✅ 無 NaN/Inf (邊界場景)

### 2. 定性評估
- ✅ 色彩自然度：3 位評估者 ≥ 7/10
- ✅ 光暈真實感：3 位評估者 ≥ 6/10
- ✅ 無明顯偽影：視覺檢查通過

### 3. 文檔完整度
- ✅ 技術報告完成 (含對比圖)
- ✅ 使用者文檔完成 (含建議)
- ✅ 決策日誌更新 (Decision #030)

---

## 風險與緩解

### 風險 1: 藍光 Halation 過強 (TASK-010)
**可能性**: MEDIUM (η_b 增加 20.8×)  
**影響**: 藍光外環過於明顯，不自然  
**緩解**:
- 定量測試: `I_blue_outer / I_red_outer` 應 < 2.0×
- 如超標: 調整 `mie_intensity` 參數 (0.7 → 0.5)

### 風險 2: 色彩偏移過大
**可能性**: LOW (TASK-008 已修復亮度)  
**影響**: 整體色調偏移 (偏冷/偏暖)  
**緩解**:
- 定量測試: ΔE00 < 10 (ColorChecker 平均)
- 如超標: 檢查光譜積分公式

### 風險 3: CineStill 紅暈過強
**可能性**: MEDIUM (f_h,red = 0.291)  
**影響**: 高光區域紅暈過度擴散  
**緩解**:
- 定量測試: 紅暈半徑 < 25px (512×512 影像)
- 如超標: 調整 `halation_radius` (20 → 18)

---

## 時間估算

| Phase | 任務 | 預估時間 | 優先級 |
|-------|------|---------|--------|
| Phase 1 | 測試腳本開發 | 2-3h | P0 |
| Phase 2 | 視覺對比分析 | 1-2h | P0 |
| Phase 3 | 報告生成 | 1h | P1 |
| **總計** | **TASK-012** | **4-6h** | - |

**快速路徑** (3h): 使用已有測試輸出 + 手動對比 + 簡化報告

---

## 下一步行動

### 立即執行 (Phase 1)
1. ⏳ 創建 `scripts/visual_verification_v041.py`
2. ⏳ 實作 Feature Toggle 機制
3. ⏳ 生成標準場景輸入影像 (S1-S5)
4. ⏳ 批次運行生成對比影像

### 短期 (Phase 2-3)
5. ⏳ 計算定量指標
6. ⏳ 定性評估（手動檢視）
7. ⏳ 生成報告與使用者文檔

### 可選 (長期)
8. ⏸️ A/B 測試（使用者盲測）
9. ⏸️ 真實膠片掃描對比
10. ⏸️ 整合進 CI/CD (自動視覺回歸測試)

---

## 參考資料

### 相關任務
- `tasks/TASK-003-medium-physics/` - 介質物理改進
- `tasks/TASK-008-spectral-brightness-fix/` - 光譜亮度修正
- `tasks/TASK-009-psf-wavelength-theory/` - Mie PSF 波長依賴
- `tasks/TASK-010-mie-refractive-index/` - Mie 折射率修正
- `tasks/TASK-011-beer-lambert-standardization/` - Beer-Lambert 標準化

### 技術文檔
- `docs/COMPUTATIONAL_OPTICS_TECHNICAL_DOC.md` - 物理模型說明
- `tasks/PHYSICS_IMPROVEMENTS_ROADMAP.md` - 物理改進路線圖
- `context/decisions_log.md` - 決策日誌

### 已有測試輸出
- `test_outputs/` - 現有測試影像（可能包含 v0.4.0 輸出）
- `archive/backups/` - 舊版本備份

---

## 元數據

**Task ID**: TASK-012  
**Created**: 2025-12-24 14:00  
**Owner**: Main Agent  
**Reviewer**: (待指定)  
**Physics Gate**: Not Required (驗證任務)  
**Estimated Completion**: 2025-12-24 18:00 (快速路徑)

---

**Status**: 🟡 Phase 1 準備中  
**Next**: 創建視覺驗證腳本
