# TASK-002: 物理模型改進實作

**任務 ID**: TASK-002  
**創建日期**: 2025-12-19  
**負責人**: Main Agent（實作者）  
**優先級**: High  
**預估時間**: 1-2 週  
**狀態**: 🔄 Planning

---

## 📋 任務目標

基於 PHYSICS_REVIEW.md（已修正）的建議，實作「路徑 C：混合導向」的物理模型改進：
1. 修正能量守恆問題（Bloom/Halation 效果）
2. 實作 H&D 曲線（膠片特性曲線）
3. 改進顆粒噪聲（Poisson 統計）
4. 分離物理模擬與色調映射
5. 修正命名與參數語義

**核心原則**：
- ✅ 保留現有視覺效果作為預設（藝術模式）
- ✅ 新增「物理模式」作為進階選項
- ✅ 確保向後相容（不破壞現有參數與配置）
- ✅ 漸進改進（分階段實作與測試）

---

## 🎯 驗收標準

### 階段 1: 能量守恆的 Bloom（必須）
- [ ] Bloom 效果通過能量守恆測試：`∑ E_in ≈ ∑ E_out`（誤差 < 1%）
- [ ] 提供兩種模式：`artistic`（現有）vs `physical`（守恆）
- [ ] 視覺效果：物理模式下高光周圍有暈影，但總亮度不增加
- [ ] 效能：處理時間增加 < 10%

### 階段 2: H&D 曲線（必須）
- [ ] 實作 Hurter-Driffield 曲線：`D = γ log10(H) + D_fog`
- [ ] 參數化：gamma（0.6-0.7 負片）、Dmin、Dmax、toe/shoulder
- [ ] 與現有 tone mapping 分離（獨立處理階段）
- [ ] 提供開關：`use_hd_curve: bool`

### 階段 3: Poisson 噪聲（建議）
- [ ] 實作 Poisson 噪聲模型：`σ = √(N_photons)`
- [ ] 疊加銀鹽顆粒結構噪聲
- [ ] 與現有 grain 效果對比測試
- [ ] 提供開關：`use_poisson_grain: bool`

### 階段 4: 命名與語義修正（必須）
- [ ] `luminance()` → `spectral_response()`
- [ ] `lux_r/g/b` → `response_r/g/b`
- [ ] `r/g/b_absorption` → `r/g/b_response_weight`（並標註為無量綱）
- [ ] `diffuse_light`/`direct_light` → `diffuse_weight`/`direct_weight`
- [ ] 更新所有文檔與註解

### 階段 5: 測試與驗證（必須）
- [ ] 能量守恆測試（單位測試）
- [ ] H&D 曲線測試（對數響應、toe/shoulder）
- [ ] 視覺回歸測試（確保藝術模式不變）
- [ ] 效能基準測試（2000×3000 圖片 < 5 秒）
- [ ] 文檔更新（README、TESTING_GUIDE）

---

## 📥 輸入資料

1. **程式碼**：
   - `Phos_0.2.0.py`（主程式）
   - `film_models.py`（資料結構）
   - `phos_core.py`（核心處理邏輯）

2. **參考文檔**：
   - `PHYSICS_REVIEW.md`（已修正，物理基礎）
   - `physicist_review_of_review.md`（錯誤分析）
   - `context/decisions_log.md`（決策記錄）

3. **現有測試**：
   - `tests/test_film_models.py`
   - `tests/test_performance.py`

---

## 🔧 實作計畫

### Phase 1: 準備與規劃（1 天）
1. ✅ 創建任務目錄與 task_brief.md
2. ⏳ 閱讀現有程式碼，識別修改點
3. ⏳ 設計新參數結構（向後相容）
4. ⏳ 設計模式切換機制（`PhysicsMode` enum）

### Phase 2: 能量守恆 Bloom（2-3 天）
1. ⏳ 實作 `apply_bloom_conserved()` 函數
2. ⏳ 添加高光提取邏輯（閾值 + 比例）
3. ⏳ 實作 PSF 正規化（∫ PSF = 1）
4. ⏳ 能量守恆單元測試
5. ⏳ 視覺對比測試（artistic vs physical）

### Phase 3: H&D 曲線（2-3 天）
1. ⏳ 設計 `HDCurveParams` dataclass
2. ⏳ 實作 `apply_hd_curve()` 函數
3. ⏳ 實作 toe/shoulder 非線性部分
4. ⏳ 從光學密度轉換到透射率（`T = 10^{-D}`）
5. ⏳ 與 tone mapping 分離（獨立管線階段）
6. ⏳ 單元測試（對數響應、範圍限制）

### Phase 4: Poisson 噪聲（1-2 天，可選）
1. ⏳ 實作 `generate_poisson_grain()` 函數
2. ⏳ 疊加固定顆粒模式（銀鹽結構）
3. ⏳ 與現有 grain 對比測試
4. ⏳ 提供開關與參數調整

### Phase 5: 命名與重構（1-2 天）
1. ⏳ 批次重命名（使用 IDE 重構工具）
2. ⏳ 更新所有調用點
3. ⏳ 更新文檔與註解
4. ⏳ 回歸測試（確保功能不變）

### Phase 6: 測試與文檔（1-2 天）
1. ⏳ 撰寫完整單元測試
2. ⏳ 視覺回歸測試（截圖對比）
3. ⏳ 效能基準測試
4. ⏳ 更新 README（物理模式說明）
5. ⏳ 更新 TESTING_GUIDE（新測試案例）

---

## 🚨 風險與緩解

### 風險 1: 視覺效果退化
**描述**: 物理模式可能不如藝術模式「好看」  
**緩解**: 
- 藝術模式為預設，保留現有效果
- 物理模式作為進階選項，供進階用戶選擇
- 提供混合參數（`physics_strength: 0.0-1.0`）漸進混合

### 風險 2: 效能下降
**描述**: 新的物理計算可能拖慢處理速度  
**緩解**:
- 使用向量化 NumPy 操作（避免迴圈）
- 僅在需要時啟用物理模式
- 效能基準測試：若降幅 > 20%，回滾或優化

### 風險 3: 參數相容性
**描述**: 新參數結構可能破壞現有配置  
**緩解**:
- 使用 `dataclasses` 的 `field(default=...)`
- 提供參數遷移函數（`migrate_v020_to_v021()`）
- 向後相容測試（載入 v0.2.0 配置）

### 風險 4: 測試覆蓋不足
**描述**: 新功能可能引入未檢測的 bug  
**緩解**:
- 每個階段獨立測試後再合併
- 視覺回歸測試（截圖 hash 比對）
- 手動測試計畫（至少 5 張真實照片）

---

## 📊 時間盒（Time-boxing）

- **總時限**: 10 天（2025-12-19 至 2025-12-29）
- **每日檢查點**: 下午 5:00 更新進度至 `task_brief.md`
- **中期檢查**: Day 5（2025-12-24）評估是否需調整範圍
- **最終交付**: Day 10（2025-12-29）或用戶決定提前結束

**若超時處理**:
- 優先保證 Phase 2（能量守恆）+ Phase 5（命名修正）
- Phase 4（Poisson）可延後或取消
- 與用戶溝通，調整範圍或延長時限

---

## 🔗 相關文件

- `PHYSICS_REVIEW.md` - 物理審查報告（已修正）
- `tasks/TASK-001-v020-verification/physicist_review_of_review.md` - 審查的審查
- `context/decisions_log.md` - 決策日誌
- `context/context_session_20251219.md` - 全域上下文

---

## 📝 備註

- 本任務採用「路徑 C：混合導向」，非「路徑 B：完全重構」
- 重點為「物理一致性」而非「絕對物理準確」
- 保持實用主義：視覺效果 > 理論完美
- 用戶可隨時要求調整優先級或範圍

---

**創建者**: Main Agent  
**最後更新**: 2025-12-19 16:50
