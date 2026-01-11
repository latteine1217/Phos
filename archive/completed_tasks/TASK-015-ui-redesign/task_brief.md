# TASK-015: UI Redesign for Improved Usability

## 任務概述

**任務 ID**: TASK-015  
**建立時間**: 2025-12-24 14:45  
**優先級**: P1 (High)  
**類型**: UX Improvement  
**預估時間**: 3-5 days  
**負責人**: Main Agent  

---

## 背景與動機

### 當前狀態
- **版本**: v0.4.2 (Reciprocity Failure 完成)
- **Physics Score**: 8.9/10 ⭐⭐⭐⭐
- **UI 複雜度**: 高（20+ 參數，6 個 expanders）
- **目標用戶**: 80% 休閒用戶 + 15% 愛好者 + 5% 研究者

### 核心問題
經過 TASK-014 完成後發現，當前 UI 存在以下問題：

1. **資訊過載**：
   - Physics 模式暴露 20+ 參數
   - 6 個嵌套 expanders（Bloom, H&D, Grain, Spectral, Reciprocity, Film Selection）
   - 新用戶需 2+ 分鐘才能完成第一張影像處理

2. **視覺層級不清**：
   - 所有 expanders 外觀相同，無優先級指示
   - 關鍵參數（如互易律失效的曝光時間）與次要調整（如 Bloom radius）視覺權重相同
   - 實驗性功能與穩定功能無視覺區分

3. **漸進式揭露不足**：
   - 預設狀態所有 expanders 收合
   - 使用者必須展開每個區塊才能發現功能
   - 無法預覽 expander 內容摘要

4. **認知負擔高**：
   - 直接暴露專業術語（「Schwarzschild 定律」「泊松顆粒」「Beer-Lambert」）
   - 說明文字過長（互易律失效說明 200+ 字）
   - 缺少簡易模式 vs 專家模式切換

5. **工作流程分散**：
   - 相關設定分散於多個 expanders
   - 曝光相關：互易律失效（expander 5） + H&D 曲線（expander 2） + Bloom（expander 1）
   - 色彩相關：光譜模擬（expander 4） + 膠片選擇（頂部） + 色調映射（頂部）

### 專案目標回顧
基於 README.md 與專案文檔：

- **核心定位**: "No LUTs, we calculate LUX" - 基於計算光學的膠片模擬
- **目標用戶**:
  - 80% 休閒用戶：需要 Instagram 風格的膠片效果，最小配置
  - 15% 愛好者：想實驗參數，理解部分物理原理
  - 5% 研究者：測試物理準確性，複製文獻結果

- **關鍵價值**:
  1. 物理準確性（Physics Score 8.9/10）✅
  2. 易用性（目前較弱，過度複雜）❌
  3. 教育性（說明文字豐富但壓倒性）⚠️
  4. 美學（強烈的珊瑚紅/深色主題）✅

---

## 任務目標

### 主要目標
1. **降低入門門檻**：新用戶 30 秒內完成第一張影像處理
2. **保留專家功能**：所有現有功能保持可存取，無破壞性變更
3. **改善視覺層級**：清晰區分簡易/進階/實驗性功能
4. **優化工作流程**：相關參數邏輯分組，減少認知負擔

### 可衡量指標
- **操作步驟**: 3 步內完成基本處理（選膠片 → 上傳 → 產生）
- **參數暴露**: 簡易模式 ≤ 5 個控制項，專家模式保留所有
- **視覺層級**: 3 層清晰區分（Quick / Custom / Expert）
- **回應時間**: UI 互動 < 100ms（目前 ~50ms，保持）

### 非目標
- ❌ 不新增物理模型或算法
- ❌ 不修改核心處理邏輯（`phos_core.py`, `film_models.py`）
- ❌ 不重寫 Streamlit 框架（使用現有 API）
- ❌ 不創建自訂 React 組件（維持 Python-only）

---

## 設計策略

### 選定方案: Option C - Smart Defaults + Override

**核心概念**：一鍵「魔法模式」+ 專家覆蓋選項

```
主要控制項 (Quick Mode):
├─ 膠片預設選擇（自動配置所有參數）
├─ 膠片強度滑桿 (0-200%)
│   ├─ 0%: 最小膠片效果
│   ├─ 100%: 預設校準外觀
│   └─ 200%: 誇張膠片特徵
├─ 曝光時間（> 1s 自動啟用互易律失效）
└─ "自訂設定" 按鈕 → 展開當前細粒度控制

覆蓋面板 (Expert Mode, 預設隱藏):
└─ 當前細粒度控制項（所有 expanders）
```

**優點**：
- ✅ 初學者立即可用性
- ✅ 保留專家存取權限
- ✅ 清晰的漸進式揭露
- ✅ 無破壞性變更

**挑戰**：
- ⚠️ 「魔法滑桿」行為需明確定義
- ⚠️ 需設計比例縮放邏輯（grain, bloom, halation 如何隨 strength 變化）

---

## 實施階段

### Phase 1: Quick Wins (0.5 day, 4 hours)

**目標**: 在不重構的前提下改善當前 UI

**內容**:
1. **視覺徽章** (1h)
   - 🆕 新功能徽章（Reciprocity, Spectral）
   - ⚠️ 實驗性功能警告
   - ⚡ 效能密集功能標記

2. **簡化互易律失效 UI** (1h)
   - 替換對數滑桿為預設按鈕：[正常 1s] [長曝 10s] [超長曝 60s] [自訂...]
   - 將 EV 預覽移出 expander（啟用時永久可見）
   - 簡化說明文字至 50 字內

3. **重置為預設值按鈕** (1h)
   - 每個 expander 新增「重設」按鈕
   - 全域「重設所有參數」按鈕
   - 使用者可安心實驗

4. **Expander 重組** (1h)
   - 合併相關功能：
     - "Bloom（光暈）" + "Halation" → "光散射效果"
     - "H&D 曲線" + "互易律失效" → "曝光響應"
   - 保持獨立：Grain, Spectral Simulation

**驗收標準**:
- ✅ 互易律失效操作步驟 5 → 2 步
- ✅ 每個 expander 都有重置按鈕
- ✅ 新功能有視覺徽章
- ✅ 無破壞性變更，所有測試通過

---

### Phase 2: Modular Refactoring (1 day, 8 hours)

**目標**: 將 UI 代碼模組化，提升可維護性

**內容**:
1. **建立 `ui_components.py`** (3h)
   - 抽取 UI 構建函數：
     ```python
     def render_film_selector(films: List[FilmProfile]) -> str
     def render_physics_controls(film: FilmProfile, mode: str) -> dict
     def render_processing_area() -> None
     ```
   - 減少 `Phos.py` 主檔案行數（目標：3087 → 2500 lines）

2. **建立 `state_manager.py`** (2h)
   - 集中化狀態管理：
     ```python
     class PhosState:
         film_profile: FilmProfile
         rendering_mode: PhysicsMode
         parameters: dict
         
         def reset_to_defaults() -> None
         def save_preset(name: str) -> None
         def load_preset(name: str) -> None
     ```

3. **抽取 CSS 至獨立檔案** (1h)
   - 建立 `styles/phos_theme.css`
   - 新增組件專屬樣式（徽章、快速模式面板）
   - 維持珊瑚紅 (#FF6B6B) + 深色漸層主題

4. **建立 `presets.py`** (2h)
   - 預設配置（人像、風景、街拍、夜景）
   - 每個預設包含：膠片選擇 + 強度 + 顆粒 + 色調
   - 範例：
     ```python
     PORTRAIT_PRESET = {
         "film": "Portra400_MediumPhysics_Mie",
         "strength": 100,
         "grain_intensity": 0.5,
         "tone_mapping": "photographic"
     }
     ```

**驗收標準**:
- ✅ `Phos.py` 減少至 2500 lines 以下
- ✅ UI 代碼分離至獨立模組
- ✅ 狀態管理集中化
- ✅ 所有功能正常運作

---

### Phase 3: Quick Mode Implementation (1 day, 8 hours)

**目標**: 實作簡易模式 vs 專家模式切換

**內容**:
1. **Quick Mode Toggle** (2h)
   - 側邊欄頂部新增切換開關：
     ```python
     use_quick_mode = st.toggle("🎯 Quick Mode", value=True, 
                                 help="簡化控制項，適合快速使用")
     ```
   - 預設開啟 Quick Mode（80% 用戶）

2. **Quick Mode Panel** (3h)
   - 顯示內容：
     - 膠片選擇器（下拉選單，含縮圖預覽）
     - 膠片強度滑桿（0-200%，預設 100%）
     - 曝光時間選擇器（預設按鈕 + 自訂）
     - 顆粒強度滑桿（0-100%）
     - 「產生影像」大按鈕
   - 設計：簡潔卡片式布局，< 5 個控制項

3. **Film Strength Slider Logic** (2h)
   - 定義縮放行為：
     ```python
     # strength = 100 時使用預設值
     # strength != 100 時按比例調整
     grain_intensity = base_grain * (strength / 100)
     bloom_threshold = base_bloom_threshold * (100 / strength)  # 反向
     halation_params.mie_intensity = base_mie * (strength / 100)
     ```
   - 邊界條件：0% = 接近原始影像，200% = 極致膠片效果

4. **Smart Reciprocity** (1h)
   - 邏輯：
     - 若 `exposure_time > 1s`：自動顯示警告 + 啟用互易律失效
     - 預設按鈕：[正常 <1s] [長曝 10s] [超長曝 60s]
     - 點擊「自訂」展開完整 expander

**驗收標準**:
- ✅ Quick Mode 預設開啟
- ✅ 控制項數量 ≤ 5
- ✅ 膠片強度滑桿正常縮放所有參數
- ✅ 曝光時間 > 1s 自動啟用互易律失效
- ✅ 無破壞性變更

---

### Phase 4: Expert Mode Polish (0.5 day, 4 hours)

**目標**: 優化專家模式體驗

**內容**:
1. **Expander 組織優化** (1.5h)
   - 重新分組：
     - **光散射效果**: Bloom + Halation（合併）
     - **曝光響應**: H&D Curve + Reciprocity Failure（合併）
     - **膠片顆粒**: Grain（獨立）
     - **光譜模擬**: Spectral Sensitivity（獨立）
   - 每個 expander 新增摘要預覽（收合時可見）

2. **即時參數監控** (1.5h)
   - 顯示當前「Physics Score 貢獻」（每個模組）
   - 顯示估計處理時間（基於參數設定）
   - 範例：
     ```
     📊 Bloom（光暈）參數  [Physics: +0.5] [Est: 120ms]
     ```

3. **互動式物理視覺化** (1h)
   - H&D 曲線圖表（隨 gamma/toe/shoulder 參數即時更新）
   - 互易律失效補償圖表（曝光時間 vs EV）
   - 使用 `st.line_chart()` 或 `plotly`

**驗收標準**:
- ✅ Expanders 重組為 4 個（從 6 個）
- ✅ 每個 expander 有摘要預覽
- ✅ 即時參數監控正常顯示
- ✅ 至少 2 個互動式圖表

---

### Phase 5: Documentation & Testing (0.5 day, 4 hours)

**目標**: 完成文檔更新與驗收測試

**內容**:
1. **使用者文檔** (1.5h)
   - 建立 `docs/UI_GUIDE_V050.md`
   - 內容：Quick Mode 使用、Expert Mode 解說、預設配置、常見問題
   - 截圖：Quick Mode 範例、Expert Mode 範例

2. **技術文檔** (1h)
   - 更新 `context/decisions_log.md`（Decision #047: UI Redesign Strategy）
   - 更新 `README.md`（版本 v0.4.2 → v0.5.0）
   - 建立 `docs/UI_DESIGN_SYSTEM.md`（設計代幣與模式）

3. **UI 測試** (1h)
   - 手動測試所有模式切換
   - 驗證參數重置功能
   - 驗證預設配置載入
   - 截圖對比（改版前/後）

4. **效能基準測試** (0.5h)
   - 驗證無效能退化
   - 測試 UI 回應時間（< 100ms）
   - 測試影像處理時間（< 5s）

**驗收標準**:
- ✅ 完整使用者文檔（含截圖）
- ✅ 技術文檔更新
- ✅ 所有 UI 模式通過手動測試
- ✅ 效能無退化

---

## 驗收標準

### 功能驗收
- ✅ Quick Mode 預設開啟，≤ 5 個控制項
- ✅ Expert Mode 保留所有現有功能
- ✅ 膠片強度滑桿正確縮放參數
- ✅ 自動互易律失效觸發（曝光 > 1s）
- ✅ 每個 expander 有重置按鈕
- ✅ 預設配置正常載入

### 使用性驗收
- ✅ 新用戶 30 秒內完成第一張影像
- ✅ 操作步驟：3 步（選膠片 → 上傳 → 產生）
- ✅ UI 回應時間 < 100ms
- ✅ 無混淆或錯誤操作

### 技術驗收
- ✅ 所有現有測試通過（310/312）
- ✅ 無破壞性變更
- ✅ `Phos.py` 減少至 2500 lines
- ✅ UI 代碼模組化完成

### 文檔驗收
- ✅ 使用者指南（含截圖）
- ✅ 技術文檔更新（decisions_log, README）
- ✅ 設計系統文檔（UI_DESIGN_SYSTEM.md）

---

## 風險與緩解

### 風險 1: 「魔法滑桿」行為不可預測
- **可能性**: MEDIUM
- **影響**: 使用者困惑，參數縮放不符預期
- **緩解**: 
  - 明確定義縮放公式（線性 vs 對數）
  - 提供即時預覽（縮圖）
  - 文檔說明每個參數如何縮放

### 風險 2: Streamlit 框架限制
- **可能性**: HIGH
- **影響**: 布局控制受限，無法實現理想設計
- **緩解**:
  - 使用 CSS 自訂樣式（`st.markdown(unsafe_allow_html=True)`）
  - 接受框架限制，優先功能性而非完美視覺
  - 考慮未來遷移至 Gradio（長期）

### 風險 3: 效能退化
- **可能性**: LOW
- **影響**: UI 回應變慢，影像處理時間增加
- **緩解**:
  - 使用 `@st.cache_data` 快取預設配置
  - 避免在 UI 中執行重運算
  - Phase 5 效能基準測試

### 風險 4: 向後相容性破壞
- **可能性**: LOW
- **影響**: 現有用戶工作流程中斷
- **緩解**:
  - 所有現有功能保留（僅重組）
  - 提供「經典模式」選項（保留舊 UI）
  - 充分測試所有參數組合

---

## 時間估算

| Phase | 任務 | 預估時間 |
|-------|------|---------|
| Phase 1 | Quick Wins | 4 hours |
| Phase 2 | Modular Refactoring | 8 hours |
| Phase 3 | Quick Mode Implementation | 8 hours |
| Phase 4 | Expert Mode Polish | 4 hours |
| Phase 5 | Documentation & Testing | 4 hours |
| **總計** | **UI Redesign** | **28 hours (3.5 days)** |

**實際預估**: 3-5 days（包含測試與除錯時間）

---

## 成功指標

### 使用性指標
- **首次使用時間**: < 30 秒（當前 ~2 分鐘）
- **每次使用調整參數數**: < 5（初學者，當前 ~10+）
- **使用者滿意度**: 「易用性」評分 > 4/5

### 技術指標
- **代碼可維護性**: UI 代碼分割至 < 200 行模組
- **測試覆蓋率**: UI 組件 > 80% 測試覆蓋
- **效能**: 頁面載入 < 2s，參數變更 < 100ms

### 採用指標
- **模式使用比例**: Quick Mode 70% / Expert Mode 30%（預測）
- **功能發現率**: > 20% 使用者啟用互易律失效
- **錯誤率**: 無效參數錯誤 < 5%

---

## 依賴與前置條件

### 前置條件
- ✅ TASK-014 完成（Reciprocity Failure）
- ✅ v0.4.2 穩定版發布
- ✅ 所有 P0/P1 物理改進完成

### 依賴項
- Streamlit 1.28+ (當前版本)
- Python 3.13 (當前環境)
- NumPy, OpenCV (無變更)

### 後續任務
- TASK-016: 預設配置庫（可選）
- TASK-017: 批次處理 UI 改進（可選）
- TASK-018: 效能優化（如有需要）

---

## 參考資料

### 相關文件
- `Phos.py` (Line 2400-2800: 當前 UI 代碼)
- `film_models.py` (膠片配置定義)
- `README.md` (專案定位與目標)
- `context/context_session_20251224.md` (本次會話上下文)

### 設計靈感
- **Lightroom Classic**: 簡易/進階面板切換
- **Instagram**: 預設濾鏡 + 調整滑桿
- **Photoshop Camera Raw**: 基本/進階選項卡

### 技術參考
- Streamlit 文檔: https://docs.streamlit.io/
- Streamlit 組件: https://streamlit.io/components
- CSS Glassmorphism: 當前主題使用

---

## 備註

1. **設計哲學**: 遵循專案「Good Taste」原則 - 簡潔優雅，消除不必要複雜度
2. **向後相容**: 絕對不破壞現有功能（"Never Break Userspace"）
3. **實用主義**: 解決真實問題（80% 使用者被複雜 UI 阻擋），不追求理論完美
4. **簡潔性**: 複雜度是萬惡之源 - 目標減少 20% UI 代碼行數

---

**建立時間**: 2025-12-24 14:45  
**預期完成**: 2025-12-27 (3-5 days)  
**版本目標**: v0.5.0 (UI Redesign)
