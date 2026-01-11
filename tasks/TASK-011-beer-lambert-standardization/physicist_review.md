# TASK-011 Physicist Review: Halation Beer-Lambert 參數標準化

## §1 當前實作物理審查

- 參數命名問題列表
  - 舊參數混用（已在代碼中標示 Deprecated）：
    - transmittance_r/g/b（語義不清：單程或雙程？是否包含 AH/片基？）
    - ah_absorption（吸收率 vs 透過率，線性近似不符合 Beer-Lambert）
  - 路線圖與歷史文檔提到的 wavelength_attenuation_r（現行代碼中已不見，但曾造成「係數 vs 比例」混亂）
  - 新版參數已趨於一致：emulsion_transmittance_*, base_transmittance, ah_layer_transmittance_*, backplate_reflectance（均為單程、無量綱）

- 物理意義不明確之處
  - 舊參數的「雙程」宣稱未明確分層，導致不可辨識性：無法分辨乳劑、片基、AH 層各自貢獻。
  - ah_absorption 線性近似（T≈1−α）僅在 α≪1 成立，不適合 AH 層的強吸收工況（尤其紅光）。
  - energy_fraction（藝術縮放）需與雙程能量分數解耦以保持可驗證性：其物理解釋為畫面層級的能量重分配比例，非光學路徑層級參數。

- Beer-Lambert 應用檢查
  - 現行 HalationParams 文檔與計算屬性 effective_halation_* 使用：
    - f_h(λ) = [T_e(λ) · T_b(λ) · T_AH(λ)]² · R_bp（雙程）——正確。
    - 單程透過率定義為無量綱 T(λ)=exp(−αL)，符合定律。
  - 舊參數映射：
    - transmittance_r/g/b 被視作 T_e²·T_b²（不含 AH）再反推單程 T_e；此假設有風險但保留向後相容。
    - ah_absorption → T_AH ≈ 1−α 的線性近似（不嚴謹），但保留舊行為並在文檔中警告。

- 能量守恆檢查
  - 文檔宣告 Bloom/PSF 流程總能量誤差 <0.05%（需在 tests/test_halation.py 與 test_p0_2_halation_beer_lambert.py 中持續驗證）。
  - 建議新增針對 Halation 單獨能量守恆測試：對單色輸入，檢查散射能量組分與殘留直通能量之和接近輸入能量（允許 PSF 邊界截斷誤差 <0.5%）。

## §2 Beer-Lambert 雙程光路模型

- ASCII 光路圖
```
I₀ (scene light)
   ↓
┌───────────────────────┐
│ Emulsion layer (T_e)  │  ← 單程穿透 T_e(λ)
├───────────────────────┤
│ Base layer (T_b)      │  ← 單程穿透 T_b(λ)
├───────────────────────┤
│ Anti-Halation (T_AH)  │  ← 單程穿透 T_AH(λ)
├───────────────────────┤
│ Backplate (Reflect R) │  ← 反射率 R_bp
├───────────────────────┤
│ Anti-Halation (T_AH)  │  ← 返程穿透 T_AH(λ)
├───────────────────────┤
│ Base layer (T_b)      │  ← 返程穿透 T_b(λ)
├───────────────────────┤
│ Emulsion layer (T_e)  │  ← 返程穿透 T_e(λ)
└───────────────────────┘
   ↑
I_halo (返回乳劑形成光暈)
```

- 數學公式推導（逐步）
  1. 單程透過率（Beer-Lambert）：
     - T_e(λ)=exp(−α_e(λ)·L_e)
     - T_b(λ)=exp(−α_b(λ)·L_b)
     - T_AH(λ)=exp(−α_AH(λ)·L_AH)
  2. 往程到背板的光強：I_fwd(λ)=I₀ · T_e · T_b · T_AH。
  3. 背板反射：I_ref(λ)=I_fwd · R_bp。
  4. 返程回到乳劑：I_back(λ)=I_ref · T_AH · T_b · T_e。
  5. 有效 Halation 能量分數：
     - f_h(λ)=I_back/I₀=[T_e · T_b · T_AH]² · R_bp。
  6. 若 AH 層缺失（CineStill 800T），令 T_AH→1：
     - f_h(λ)=[T_e · T_b]² · R_bp。

- 真實案例計算（示例數值）
  - 公用：T_b=0.98, R_bp=0.30。
  - CineStill 800T（無 AH）：T_AH=1。
    - 假設 T_e,r=0.92, T_e,g=0.87, T_e,b=0.78。
    - f_h,r ≈ (0.92·0.98)²·0.30 ≈ (0.902)²·0.30 ≈ 0.8136·0.30 ≈ 0.244 → 強紅暈。
    - f_h,g ≈ (0.87·0.98)²·0.30 ≈ (0.853)²·0.30 ≈ 0.727·0.30 ≈ 0.218。
    - f_h,b ≈ (0.78·0.98)²·0.30 ≈ (0.764)²·0.30 ≈ 0.584·0.30 ≈ 0.175。
    - 註：示例顯示強 Halation；實務上 800T 的紅暈更強，可能由背板反射率與乳劑紅通道更高透過率造成。
  - Portra 400（有 AH）：假設 T_AH,r=0.30, T_AH,g=0.10, T_AH,b=0.05。
    - f_h,r ≈ (0.92·0.98·0.30)²·0.30 ≈ (0.271)²·0.30 ≈ 0.073·0.30 ≈ 0.022。
    - f_h,g ≈ (0.87·0.98·0.10)²·0.30 ≈ (0.085)²·0.30 ≈ 0.0072·0.30 ≈ 0.0022。
    - f_h,b ≈ (0.78·0.98·0.05)²·0.30 ≈ (0.038)²·0.30 ≈ 0.0014·0.30 ≈ 4.3e−4。
    - 結論：Portra 值顯著低，符合「Halation 幾乎不可見」。

## §3 標準化參數設計

- 建議的參數命名（英文 + 中文註解，無量綱除非另註）
  - emulsion_transmittance_r/g/b：乳劑層單程透過率 T_e(λ_r/g/b)
  - base_transmittance：片基單程透過率 T_b（通常灰色、近 1）
  - ah_layer_transmittance_r/g/b：AH 層單程透過率 T_AH(λ_r/g/b)
  - backplate_reflectance：背板反射率 R_bp（0-1）
  - energy_fraction：畫面級能量比例縮放（藝術控制，與物理分離）
  - 可選（進階）：absorption_coefficient_e/b/ah_[r/g/b]（cm⁻¹），path_length_e/b/ah（cm）——若轉為係數/長度驅動，計算 T=exp(−αL)。

- 每個參數的物理意義（含單位）
  - T_*：無量綱，單程透過率。
  - R_bp：無量綱，反射率。
  - α_*（選用）：cm⁻¹，材料吸收係數。
  - L_*（選用）：cm，光程長度（厚度/有效路徑）。

- 參數數值範圍（合理區間）
  - emulsion_transmittance_r/g/b：0.6–0.98（彩色乳劑在可見光區）
  - base_transmittance：0.95–0.995（TAC/PET 基材）
  - ah_layer_transmittance_r/g/b：
    - 有 AH：0.02–0.35（藍最低、紅較高但仍顯著衰減）
    - 無 AH（CineStill）：≈1.0（所有波段）
  - backplate_reflectance：0.05–0.50（黑絨布至金屬背板）
  - energy_fraction：0.02–0.10（視覺控制）

- 計算公式（從參數到有效 Halation 能量）
  - 單程聚合：T_single(λ) = T_e(λ) · T_b · T_AH(λ)
  - 雙程：f_h(λ) = [T_single(λ)]² · R_bp
  - 若使用 α,L：T_e(λ)=exp(−α_e(λ)L_e)、T_AH 同理；再帶入上式。

## §4 校準指南

- 從真實膠片特徵反推參數
  - 蒐集長曝光高反差場景（街燈、霓虹、金屬反光）掃描。
  - 在紅、綠、藍通道分離後估計 Halation 光暈強度相對主峰能量（近似 f_h(λ)）。
  - 已知相機背板材質估計 R_bp（或作為自由參數由視覺擬合）。
  - 以 Portra 400 作基準：調低 T_AH_* 直至 f_h 達 <0.05（紅），<0.01（綠/藍）。

- CineStill 800T 參數建議（無 AH 層）
  - ah_layer_transmittance_r/g/b ≈ 1.0。
  - backplate_reflectance：0.30–0.50（視相機背板）。
  - emulsion_transmittance_r/g/b：偏高（紅>綠>藍）；初值可用 0.93/0.88/0.80。
  - 目標驗證：f_h,red > 0.15。

- Kodak Portra 400 參數建議（有 AH 層）
  - ah_layer_transmittance_r/g/b ≈ 0.30/0.10/0.05（示例）。
  - backplate_reflectance：0.20–0.35。
  - emulsion_transmittance_r/g/b：0.92/0.87/0.78（示例）。
  - 目標驗證：f_h,red < 0.05，f_h,blue ≪ 0.01。

- 驗證方法（能量守恆、視覺特徵）
  - 能量守恆：對單色輸入，總輸出能量（直通 + PSF 散射）≈ 輸入能量（允差 <0.5%）。
  - 視覺：
    - CineStill：紅色高亮周圍寬範圍暈光明顯。
    - Portra：同場景暈光極弱或不可見。

## §5 實作建議

- 代碼結構建議（dataclass 設計）
  - 保持 HalationParams 為「單程透過率」定義，維持可辨識性與簡潔。
  - 可加入選用結構 HalationOpticalCoefficients（α_e/b/ah_[r/g/b], L_e/b/ah），並提供互相轉換工具函數：transmittance ↔ coefficients。
  - 明確標註 Deprecated 欄位的移除版本（v0.4.0），並保留警告與自動映射。

- 計算邏輯建議（函數簽名）
  - def halation_fraction(T_e_rgb: tuple[float,float,float], T_b: float, T_ah_rgb: tuple[float,float,float], R_bp: float) -> tuple[float,float,float]
  - 若提供 α,L：def transmittance_from_coeff(alpha_rgb: tuple[float,float,float], L: float) -> tuple[float,float,float]

- 測試驗證建議（物理測試案例）
  - test_halation_double_pass_formula：對比手算 f_h 與程式輸出（R,G,B 三通道）。
  - test_halation_energy_conservation：單色輸入能量誤差 <0.5%。
  - test_cinestill_vs_portra_halo_ratio：紅通道 f_h 比例差異達 >5×。
  - 邊界測試：T_AH→1（無 AH，CineStill）、R_bp→0（黑背板，無 Halation）。

- 向後相容策略
  - 保留 __post_init__ 自動映射，但在文檔與警告明確：舊 transmittance_* 被視為 T_e²·T_b²，不含 AH；ah_absorption 線性近似僅臨時維持。
  - 在 v0.4.0 移除舊欄位，提供遷移指南。

## §6 物理風險評估

- 已知限制
  - 缺少材料級 α(λ) 與 L 的真實數據；依靠經驗範圍與視覺校準。
  - 單層 AH 假設；真片可能為多層或漸變結構。
  - 忽略入射角與偏振依賴；邊緣場景可能有差異。

- 數值不確定性
  - 參數校準相對不確定性 ±10–20%（缺乏地面真值）。
  - 能量守恆測試中的 PSF 邊界截斷可能引入 0.1–0.5% 誤差。

- 邊界條件注意事項
  - T_* 必須 ∈ (0,1]；禁止 ≤0 或 >1（數值穩定性）。
  - R_bp ∈ [0,1]；高反射設定需與場景對應。
  - 當 T_AH→1（無 AH）且 R_bp 高時，f_h 可達 0.2–0.3；需配合 energy_fraction 控制視覺效果，避免過曝感。

## 可驗證指標

- 方程式正確性：f_h(λ)=[T_e(λ)·T_b·T_AH(λ)]²·R_bp 與程式輸出一致（偏差 < 1e−6）。
- 邊界/初始條件一致性：T_*、R_bp 合法區間檢查（測試覆蓋）。
- 量綱與無因次化：所有 T_*、R_bp 無量綱；若使用 α,L，單位 cm⁻¹ 與 cm 明確。
- 守恆性與穩定性：能量守恆誤差 <0.5%；不產生 NaN/Inf。
- 可辨識性：分層參數可單獨調整並產生可觀測影響（乳劑 vs AH vs 背板）。

## 下一步

- 在 Phase 2 重構中：
  - 完成 HalationParams 的文檔強化與（可選）係數模式支持。
  - 更新 phos_core.py 的 Halation 計算函式以使用標準化簽名。
  - 擴充與更新測試：新增雙程路徑與 CineStill/Portra 對比測試。

## 參考

- Beer-Lambert Law: T(λ)=exp(−α(λ)·L)
- Bohren & Huffman (1983). Absorption and Scattering of Light by Small Particles.
- Hunt, R. W. G. (2004). The Reproduction of Colour, 6th ed., Ch. 18.
