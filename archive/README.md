# Archive 歷史記錄索引

本目錄包含已完成的任務、過時的文檔和備份檔案，用於歷史參考。

---

## 📂 目錄結構

```
archive/
├── backups/           # 代碼備份檔案（7 個）
├── completed_tasks/   # 已完成的任務文檔（17 個任務，TASK-001 到 TASK-017）
├── data/              # 實驗/舊版數據檔案（3 個）
├── docs/              # 過時的計劃與報告（11 個）
├── scripts/           # 診斷與測試腳本（13 個）
└── tests_legacy/      # 舊測試目錄（34 項測試，已棄用）
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

### 計劃與總結（11 個文件）
- `CLEANUP_PLAN.md` - 專案清理計劃（v0.4.1）
- `CLEANUP_SUMMARY.md` - 清理總結
- `PHASE3_COMPLETION_SUMMARY.md` - Phase 3 文檔清理總結（v0.6.2）
- `PHASE3_CODE_CLEANUP_PLAN.md` - Phase 3 代碼清理計劃（v0.6.3）✨
- `PHASE1_CLEANUP_PLAN.md` - Phase 1 清理計劃
- `PHASE1_COMPLETION_REPORT.md` - Phase 1 完成報告
- `KNOWN_ISSUES_RISKS.md` - 已知問題與風險

### 功能報告
- `PERFORMANCE_OPTIMIZATION_SUMMARY.md` - 性能優化總結
- `VISUAL_IMPROVEMENTS_V041.md` - v0.4.1 視覺改進
- `FILM_DESCRIPTIONS_FEATURE.md` - 膠片描述功能
- `UI_INTEGRATION_SUMMARY.md` - UI 整合總結（v0.3.0，已過時）

---

## 💾 備份檔案 (backups/)

舊版代碼備份（7 個檔案）：
- `Phos_0.3.0.py.backup_phase45` - Phase 4-5 前的備份
- `Phos_0.3.0.py.backup_pre_p0_2` - P0-2 前的備份
- `diagnose_color_brightness.py.bak` - 診斷腳本備份
- `film_models.py.backup_pre_medium_physics` - Medium Physics 前的備份
- `film_models.py.backup_pre_p0_2` - P0-2 前的備份
- `film_models.py.backup_pre_mie_default` - Mie 預設值前的備份（v0.6.4）✨
- `film_models.py.backup_phase1` - Phase 1 前的備份（v0.6.4）✨

---

## 🗄️ 數據檔案 (data/)

實驗/舊版數據（3 個檔案）：
- `mie_lookup_table_v1.npz` - Mie 散射查表 v1（已被 v2 取代）
- `mie_lookup_table_v2_backup.npz` - Mie 散射查表 v2 備份（v0.6.3）✨
- `mie_lookup_table_v3.npz` - Mie 散射查表 v3 實驗版（v0.6.3）✨

**主動數據**: 參見 `/data/` 目錄（4 個檔案：v2, film_spectral, cie_1931, smits_basis）

---

## 🔧 診斷腳本 (scripts/)

診斷與測試腳本（13 個檔案）：

### 數據生成診斷（已完成）
- `diagnose_color_brightness.py` - TASK-008 色彩亮度診斷
- `test_all_films_physical.py` - 物理模式完整測試
- `test_mie_visual.py` - Mie 散射視覺測試
- `test_v041_brightness.py` - v0.4.1 亮度驗證

### 特定任務診斷（v0.6.4）✨
- `diagnose_colorchecker_error.py` - 色彩檢測錯誤診斷
- `diagnose_green_brightness.py` - 綠色亮度問題診斷
- `test_blue_halation_v3.py` - TASK-011 藍色光暈測試
- `test_reciprocity_visual.py` - TASK-014 互易律視覺測試

### 效能分析與版本比較（v0.6.4）✨
- `compare_mie_versions.py` - Mie v1/v2/v3 比較（已完成）
- `benchmark_performance.py` - 效能基準測試
- `profile_performance.py` - 效能剖析工具
- `profile_real_workflow.py` - 真實工作流程剖析

### 版本特定驗證（v0.6.4）✨
- `visual_verification_v041.py` - v0.4.1 視覺驗證（已過時）

**主動腳本**: 參見 `/scripts/` 目錄（7 個活躍工具）

---

## 🧪 舊測試目錄 (tests_legacy/)

舊測試結構（v0.6.3 歸檔）✨：
- **34 項測試**: 部分測試依賴不存在的檔案（Phos_0.3.0.py, Phos_0.1.1.py）
- **3 個收集錯誤**: `test_integration.py`, `test_full_pipeline.py`, `test_refactor.py`
- **已被取代**: tests_refactored/ 完全覆蓋功能（286 測試 vs 34 測試）

### 測試檔案列表
- `test_integration.py` - 整合測試（引用舊版 Phos.py）
- `test_medium_physics_e2e.py` - 端到端測試
- `test_phase2_integration.py` - Phase 2 整合測試
- `test_spectral_model.py` - 光譜模型測試
- `debug/` - 7 個除錯腳本（部分已失效）

**主動測試**: 參見 `/tests_refactored/` 目錄（286 項測試，98.6% 通過率）

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

**最後更新**: 2025-01-11 (v0.6.4)  
**任務數量**: 17 個已完成任務  
**文檔數量**: 15+ 個歸檔文檔
