# Archive 歷史記錄索引

本目錄包含已完成的任務、過時的文檔和備份檔案，用於歷史參考。

---

## 📂 目錄結構

```
archive/
├── backups/           # 代碼備份檔案
├── completed_tasks/   # 已完成的任務文檔（TASK-001 到 TASK-015）
├── data/              # 舊版數據檔案
├── docs/              # 過時的計劃與報告
└── scripts/           # 一次性診斷腳本
```

---

## 📋 已完成任務清單 (completed_tasks/)

### Phase 0: 基礎驗證
- **P0-2**: Halation 重構計劃
- **P1-2**: ISO 統一化計劃
- **TASK-001**: v0.2.0 驗證

### Phase 1: 物理改進
- **TASK-002**: 物理改進（Phase 1-6）
- **TASK-003**: 中等物理升級（Medium Physics）
- **TASK-005**: 光譜敏感度驗證

### Phase 2: 性能與視覺
- **TASK-004**: 性能優化（GPU 框架分析）
- **TASK-006**: PSF 波長 Mie 散射
- **TASK-007**: 物理增強評估

### Phase 3: 光譜與校正
- **TASK-008**: 光譜亮度修復（v0.4.1）
- **TASK-009**: PSF 波長理論（Phase 1-5）
- **TASK-010**: Mie 折射率修正（v3 查表）

### Phase 4: 標準化與驗證
- **TASK-011**: Beer-Lambert 標準化（Phase 1-4）
- **TASK-012**: 視覺驗證
- **TASK-013**: 修復已知問題（Phase 1-8）

### Phase 5: 進階功能
- **TASK-014**: 互易律失效（Reciprocity Failure）
- **TASK-015**: UI 重新設計（審計）

---

## 📄 歸檔文檔 (docs/)

### 計劃與總結
- `CLEANUP_PLAN.md` - 專案清理計劃（v0.4.1）
- `CLEANUP_SUMMARY.md` - 清理總結
- `PHASE3_COMPLETION_SUMMARY.md` - Phase 3 完成總結
- `PHASE1_CLEANUP_PLAN.md` - Phase 1 清理計劃
- `PHASE1_COMPLETION_REPORT.md` - Phase 1 完成報告
- `KNOWN_ISSUES_RISKS.md` - 已知問題與風險

### 功能報告
- `PERFORMANCE_OPTIMIZATION_SUMMARY.md` - 性能優化總結
- `VISUAL_IMPROVEMENTS_V041.md` - v0.4.1 視覺改進
- `FILM_DESCRIPTIONS_FEATURE.md` - 膠片描述功能

### 診斷報告（一次性）
- `BUGFIX_SUMMARY_20251220.md` - Bug 修復總結
- `COLOR_FIX_TEST_GUIDE.md` - 顏色修復測試指南
- `DIAGNOSTIC_RESULTS_20251223.md` - 診斷結果
- `OPTIMIZATION_REPORT.md` - 優化報告
- `UI_INTEGRATION_SUMMARY.md` - UI 整合總結

---

## 💾 備份檔案 (backups/)

舊版代碼備份：
- `Phos_0.3.0.py.backup_phase45`
- `Phos_0.3.0.py.backup_pre_p0_2`
- `film_models.py.backup_pre_medium_physics`
- `film_models.py.backup_pre_p0_2`

---

## 🗄️ 舊版數據 (data/)

- `mie_lookup_table_v1.npz` - Mie 散射查表 v1（已被 v3 取代）

---

## 🔧 診斷腳本 (scripts/)

一次性診斷與測試腳本：
- `diagnose_color_brightness.py` - TASK-008 專用
- `test_all_films_physical.py` - 物理模式測試
- `test_mie_visual.py` - Mie 視覺測試
- `test_v041_brightness.py` - v0.4.1 亮度測試

---

## 📌 使用說明

### 查找特定任務
```bash
# 查看 TASK-013 完成報告
cat archive/completed_tasks/TASK-013-fix-known-issues/phase7_completion_report.md
```

### 查看歷史決策
所有任務都包含：
- `task_brief.md` - 任務簡介
- `phase*_design.md` - 設計文檔
- `*_completion_report.md` - 完成報告
- `physicist_review.md` - 物理學家審查（如果適用）

### 恢復舊版代碼
```bash
# 比較當前版本與舊版
diff Phos.py archive/backups/Phos_0.3.0.py.backup_phase45
```

---

## ⚠️ 注意事項

1. **不要修改 archive/ 中的檔案** - 僅供參考
2. **不要在 archive/ 中開發** - 使用主目錄的活躍檔案
3. **如需引用** - 複製到主目錄後再修改

---

**最後更新**: 2025-01-11 (v0.6.1)  
**任務數量**: 15 個已完成任務  
**文檔數量**: 15+ 個歸檔文檔
