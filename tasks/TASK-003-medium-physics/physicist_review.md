# Phos 中等物理升級（TASK-003）物理審查報告

版本: 2025-12-19
責任角色: 資深物理科研專家（光學/散射/色彩科學）

---

## 背景

- 專案: Phos – 計算光學膠片模擬系統
- 目標: 從「簡化物理」（~25%）升級到「中等物理」（50–60%）
- 約束: 2000×3000 影像，處理時間 < 10s；視覺逼真優先、物理啟發為主
- 審查範圍: Phase 1–6 的核心物理假設與數值設計，重點驗證散射、Halation、光譜模型、顆粒叢集與 Mie 查表方案

方法/依據見文末「參考文獻」，並以經典散射理論（Rayleigh/Mie）、輻射傳輸與色彩科學（CIE/Smits）為基礎，兼顧效能。

---

## 1. 總體評價

- 物理正確性評分: 7.0 / 10
  - 優點: 能量守恆明確；將 Bloom 與 Halation 分離；引入波長依賴與光譜流程；提出 Mie 查表。
  - 風險: 在膠片乳劑的粒徑範圍（0.5–3 μm）多數情形不屬於 Rayleigh；PSF 半徑的 λ 次方關係過於簡化；Halation 參數需遵從 Beer–Lambert；材料折射率與介質相對折射率需校正；光譜敏感度不應用簡單高斯代替真實曲線。
- 可行性評分: 8.5 / 10
  - 在 <10s 約束下，採用三波段 PSF、兩層核（短程 Gaussian + 長尾 Exponential/Lorentzian）、Smits 31 通道與離線 Mie 查表，均具工程可落地性。
- 優先改進建議（由高到低）
  1) 更正散射機制：在乳劑內以「Mie 主導、Rayleigh 為輔」的權重與標度；PSF 能量權重依 λ^-4（或查表）而非單純半徑 ∝ λ^2。
  2) Halation 以 Beer–Lambert 管線明確化（T、R、路徑長度），將「wavelength_attenuation」重命名為「transmittance」並由 α(λ)、L 推得。
  3) 使用相對折射率 m = n_particle(λ)/n_medium(λ)（銀鹽/明膠），並在 Mie 查表與任何 Rayleigh 公式中統一此定義。
  4) 光譜敏感度曲線優先使用廠商實測 CSV；暫無資料時用 2–3 個偏斜高斯/對數常態的混合，避免單峰高斯過度理想化。
  5) 顆粒叢集以 1/f^β 的空間譜目標（β≈1–2）校準 Perlin/ Simplex 噪聲的參數，並與 ISO（顆粒尺寸與方差）建立一對一關係。

---

## 2. 逐項審查（Phase-by-Phase）

### Phase 1: 波長依賴散射

物理正確性: ⚠️ 部分正確

問題分析:
- 乳劑中銀鹵化物晶體直徑 0.5–3 μm，相對於可見光 λ≈0.45–0.65 μm，其尺寸參數 x=2πa/λ=O(3–20)，多數非 Rayleigh（x≪1）而是 Mie/小角前向散射主導；直接採用 Rayleigh σ∝λ^-4 作為機制描述不嚴謹。
- 以 λ 的冪次去縮放 PSF 半徑（例如 λ^-2 或 λ^-4）缺乏嚴謹推導。多次小角散射下，模糊寬度與運輸平均自由程 l* 和角度分布均相關，經驗上「半徑隨短波變大」是對的，但次方不應武斷。
- 650/450 nm 作為 RGB 代表值可接受，但需在文件中標註其僅為代表中心波長，實作上應與 Phase 4 的 31 通道一致化。

修正建議:
- 機制層次：
  - 乳劑內散射以「Mie（前向）+ 少量各向」建模：能量權重 w(λ) 可先用正規化的 λ^-p（p≈3–4）作快速近似，或直接取自 Mie 查表的積分散射截面；半徑標度建議 σ(λ) ∝ (λ_ref/λ)^q，q≈0.5–1.0（小角散射的角度隨 λ 減小而增大，非 λ^-2 或 λ^-4）。
  - 兩段式 PSF：核心（Gaussian，小角）+ 尾部（exponential/Lorentzian），兩者的能量比與尺度隨 λ 調整。
- 參數解耦：將「散射能量分數 η(λ)」與「核寬度 σ(λ)」分開估計，避免不可辨識性（半徑變大可視上近似能量變多）。
- 與 Phase 4 對齊：若啟用 31 通道，令 η(λ_i)、σ(λ_i) 逐波長賦值（可三色下采樣至 R/G/B 通道用於卷積）。
- 驗證：
  - 「白點刀口」測試（knife-edge）量測跨波段的 MTF 落差；
  - 藍/紅通道 PSF 的半高寬比 HWHM_b/HWHM_r 目標 1.5–2.5（視覺合理），而能量比積分近似符合 λ^-p（p≈3–4）。

參考文獻:
- van de Hulst, Light Scattering by Small Particles, Dover, 1957.
- Bohren & Huffman, Absorption and Scattering of Light by Small Particles, Wiley, 1983.
- Ishimaru, Wave Propagation and Scattering in Random Media, IEEE Press.

---

### Phase 2: Halation 獨立建模

物理正確性: ✅ 大致正確（需參數定義更嚴謹）

問題分析:
- 機制描述正確：Bloom（乳劑內前向散射）與 Halation（穿透至背層/相機背板反射再回到乳劑）為不同路徑。
- PSF 半徑比例（~1:5）在一般掃描解析度下「視覺可行」，但應與像素尺寸/膠片厚度對應；長尾分布（exponential/Lorentzian）優於單高斯。
- 「波長依賴衰減係數」需改為 Beer–Lambert 形式：T(λ)=exp(-α(λ)L)，且 Halation路徑是雙程（往返穿透）。
- Anti-Halation 層吸收 95%：對於有 rem-jet 的電影片常見 90–99% 可見光抑制；對一般彩色負片（無 rem-jet）以 AH 染料實現，可能較低（~60–90%，與 λ 有關）。

修正建議:
- 管線化 Halation 能量：
  - 前向透過乳劑與片基的透過率 T_e(λ)、T_b(λ)；
  - AH 層（或背面塗層）透過 T_AH(λ)=exp(-α_AH(λ) L_AH)；
  - 背板反射 R_bp（0–0.9，取決於相機內壁/壓片板）；
  - 往返路徑的總系數 f_h(λ) ≈ T_e T_b T_AH · R_bp · T_AH T_b T_e_back。
  - 實作時可折合為 f_h(λ)=k · exp(-α_eff(λ) L_eff)，k、α_eff 可由器材/片種近似。
- 參數命名：將 wavelength_attenuation 更名為 transmittance 或 exp(-αL)，避免語義歧義；明確 η_bloom(λ)、η_halation(λ) 與 PSF 正規化。
- 能量守恆：
  - output(λ) = (1-η_b-η_h)·input(λ) + η_b·(input⊗PSF_b(λ)) + η_h·(input⊗PSF_h(λ))。
  - Σkernel=1；邊界採用能量重分配（見關鍵公式驗證）。
- 數值建議：
  - 比例：Bloom 核尺度 σ_bloom ≈ 2–6 px；Halation 尺度 κ_h ≈ 20–80 px（exponential 半徑）；
  - AH 吸收：一般彩負片 α_AH 對藍/綠較強、對紅較弱；rem-jet 片種可近似 95–99% 抑制（k 極小）。

參考文獻:
- Mees & James, The Theory of the Photographic Process, 4th ed., 1977.
- Kodak motion picture film datasheets (rem-jet anti-halation backing).
- Stavenga et al., Beer–Lambert optics in layered media（通用層狀吸收傳輸原理）。

---

### Phase 3: 顆粒叢集效應

物理正確性: ✅ 基本合理（建議加上頻譜校準）

問題分析:
- 銀鹽晶體空間分布確有叢集/團塊感，Perlin/Simplex 可作為低頻調製的程序化近似，但需限制其頻譜特性避免人工週期感。
- 真實膠片顆粒的空間功率譜常呈 1/f^β（β≈1–2）趨勢；且與 ISO（顆粒尺寸與分布寬度）相關。
- Ostwald ripening 影響晶體尺寸分布（多為製程面），可抽象為顆粒尺寸的對數常態分布＋叢集強度增強。

修正建議:
- 頻譜目標：以 FFT 驗證輸出噪聲的功率譜斜率 β，調校 octaves / persistence / lacunarity，使 β 落在 1–2；
- ISO 關聯：
  - 增加尺寸分布寬度（σ_size）與叢集方差（Var_cluster）隨 ISO 增加；
  - 對數常態粒徑分布 + 叢集遮罩乘法（如方案）是合理折衷；
  - 提供「等效 RMS 顆粒度」指標對齊實測（如 RMS granularity at 1.0 density）。

參考文獻:
- Mees & James, The Theory of the Photographic Process.
- Dainty & Shaw, Image Science: Principles, Analysis and Evaluation of Photographic-type Imaging Systems.

---

### Phase 4: 光譜模型（31 通道）

物理正確性: ✅ 大致正確（關鍵點需加強）

問題分析:
- Smits (1999) 的 RGB→光譜重建屬「可視覺合理」的近似，對於平滑光譜與標準照明下，往返誤差通常在低單位數 ΔE（~3–6）範圍，但對窄帶光源/高度飽和色可能偏大。
- 31 通道（約 13 nm 間隔）對可見光範圍的平滑積分通常足夠；對極窄帶源可能不足，但與膠片情境相符（膠片/照明多為寬帶）。
- 膠片敏感度曲線非單峰對稱高斯，常具偏斜與肩部，且層間重疊明顯；單一高斯近似會影響色彩交互敏感度與膠片特有色相偏移。
- Stokes shift（螢光發射）對攝影乳劑捕捉階段可忽略：乳劑主要是吸收/散射，顯影後的染料為吸收濾色元件，非發光體。

修正建議:
- 優先採用廠商光譜敏感度 CSV（Kodak/Fuji 公開圖表數位化）。無資料時用「2–3 個偏斜高斯/對數常態混合」擬合單層曲線，並交叉層間重疊。
- 往返誤差測試：sRGB → Smits → 31 通道 → XYZ → sRGB（D65）ΔE00 < 5 作為驗收；並加入 ColorChecker 24 色塊平均與最大 ΔE。
- 與 Phase 1 的波長散射耦合：每一波長通道施加 η(λ)、PSF(λ)，再積分至層響應。

參考文獻:
- Smits, A. (1999). An RGB to Spectrum Conversion for Reflectances. (SIGGRAPH note)
- CIE 1931/1964 color matching functions；colour-science 文檔
- Kodak/Fuji 片種數據表（光譜敏感度/染料光譜）

---

### Phase 5: Mie 散射查表

物理正確性: ⚠️ 部分正確（需關鍵修正）

問題分析:
- 尺度：d=0.5–3 μm、λ=450–650 nm ⇒ 尺寸參數 x=πd/λ≈2.4–21，屬 Mie 範圍，採用 Mie 理論恰當。
- 折射率：應使用「相對折射率」m(λ)=n_particle(λ)/n_medium(λ)。乳劑介質為明膠/水相，n_medium≈1.33–1.52（可取 1.50±0.02）；銀鹵化物 n_AgBr(λ)≈2.2–2.4（可見光，有色散）。直接用 m=n_AgBr（相對空氣）不正確。
- 顆粒形狀：AgX 晶體多為立方/八面體，Mie 假設球形；但對大量隨機取向與粒徑分布的平均 PSF，徑向對稱近似可接受。
- 相位函數轉空間 PSF：需使用小角近似與幾何關係（角度 θ→影像半徑 r 取決於層厚/散射深度/放大），不可直接等同。

修正建議:
- 生成查表時：
  - 使用 m(λ)=n_AgBr(λ)/n_gelatin(λ)；n_gelatin≈1.50；引入 AgBr 的色散（可用文獻曲線或簡單 Cauchy 擬合）。
  - 粒徑採對數常態分布（平均與 σ 由 ISO/片種決定），對 S1、S2 的強度在粒徑上加權平均，生成「有效相位函數」。
  - 角度→空間映射：r≈z_eff·tanθ（小角），z_eff 取乳劑幾何平均深度或調參；然後以圓對稱積分生成 2D PSF，並正規化。
- 快速近似：在實時模式中以「雙段核」參數由查表插值得到（核心 σ、尾部尺度 κ、能量分比 ρ），而不直接用全尺寸 PSF。

參考文獻:
- Bohren & Huffman (1983)
- van de Hulst (1957)
- Palik, Handbook of Optical Constants of Solids（銀鹵化物、明膠/水相折射率資料）

---

### Phase 6: 整合測試與效能優化

物理正確性: ✅ 合理

建議補充:
- 邊界能量守恆測試：卷積邊界（reflect/constant/replicate）會改變總能量，需做「邊界補償正規化」測試（見下文公式）。
- 查表快取：Mie 轉參數（σ、κ、ρ）的小型表（<1 MB）更利於 100 ms 內載入。

---

## 3. 關鍵公式驗證

1) Rayleigh 散射截面（僅作極小粒徑參考，a≪λ）
- 對半徑 a 的球形粒子、相對折射率 m：
  σ_R(λ) = (8π/3) k^4 a^6 |(m^2-1)/(m^2+2)|^2，其中 k=2π/λ。
- 在膠片乳劑多不滿足 a≪λ，因此僅作 λ 依賴的上限估計。

2) 能量守恆的散射–卷積結構（逐波長）
- 對每個 λ 或每個通道 c：
  I_out^c = (1-η_b^c-η_h^c) I_in^c + η_b^c (I_in^c ⊗ K_b^c) + η_h^c (I_in^c ⊗ K_h^c)
- 條件：
  - 0 ≤ η_b^c, η_h^c，且 η_b^c+η_h^c ≤ 1；
  - PSF 核 K_b^c, K_h^c 非負且 Σ_ij K = 1；
  - 邊界補償：若使用零填充或鏡像，需以有效重疊核權重對卷積結果做每像素再正規化，確保總和守恆。

3) PSF 正規化與單位
- 離散核需滿足 Σ K = 1；對雙段核 K = ρ K_core + (1-ρ) K_tail，分別正規化。
- 角度相位函數 P(θ) 到空間核 K(r) 的守恆：2π∫ P(θ) sinθ dθ = 2π∫ K(r) r dr（在小角/等能映射近似下）。

4) Beer–Lambert（Halation）
- T(λ) = exp(-α(λ)L)；雙程透過為 T^2；若含背板反射 R_bp，總係數 f_h(λ) ≈ T_total^2 R_bp（再乘以層回程透過）。

5) 波長依賴關係（建議）
- 散射能量分數 η(λ) ∝ λ^-p（p≈3–4），以保持藍>綠>紅；
- PSF 寬度 σ(λ) ∝ (λ_ref/λ)^q（q≈0.5–1.0）；以視覺測試校準 q。

---

## 4. 數值範圍檢查

- 銀鹽晶體尺寸（直徑 d）: 0.2–1.0 μm（低 ISO），至 1–3 μm（高 ISO/推進）；本案 0.5–3 μm 屬合理上限。
- 明膠/介質折射率 n_medium: 1.48–1.52（可見光）；
- AgBr 折射率 n_AgBr(λ): 約 2.2–2.4（可見光，隨 λ 有正常色散）；相對折射率 m ≈ 1.45–1.60。
- 散射比例 σ_blue/σ_red：
  - Rayleigh 上限: (650/450)^4 ≈ 4.3；
  - Mie 現實：常低於此值（~1.5–3），依粒徑/分布而變；建議以查表或擬合。
- PSF 半徑比例（Bloom vs Halation）：
  - 視覺建議 1:5–1:10；需與像素尺寸對應（例如 12 μm/px 時，20 px ≈ 0.24 mm、100 px ≈ 1.2 mm，偏大但在低解析輸出可接受）。

---

## 5. 缺失物理（未考慮但可接受的簡化）

- 偏振效應：Mie 相位函數具偏振依賴；對非偏振照明與多重散射平均後影響小，可忽略。
- 多次散射的嚴格處理：以單次散射+卷積近似；在薄層與小 η 下可接受。
- 顆粒形狀與各向異性：以球形平均近似；視覺差異可忽略。
- 溫度影響：對短時曝光與室溫變化小，忽略。
- 介質吸收（層間）細節：以有效 α_eff(λ) 匯總。

---

## 6. 效能 vs 精度權衡評估

- 可接受的簡化（誤差 < 5%）
  - PSF 核正規化 + 能量守恆的卷積結構；
  - 31 通道光譜積分（平滑源）；
  - Halation 使用雙程 Beer–Lambert 係數的單核長尾。
- 風險簡化（誤差 5–15%）
  - 將散射機制全部以 λ^-4 權重表示（對 d~μm 的 Mie 範圍偏保守）；
  - 單一高斯敏感度曲線（建議改為混合峰）。
- 不可接受（誤差 > 15%）
  - 使用絕對折射率 m=n_AgBr（忽略介質）在 Mie 計算；
  - PSF 半徑用 λ^-2 或 λ^-4 直接縮放且同時將能量也按同函數縮放（雙重錯配）。

---

## 7. 測試與驗證建議

- 物理量測試
  - 能量守恆（多通道、多核、邊界補償後的整體能量誤差 < 0.01%）。
  - PSF 正規化（ΣK=1；雙段核各自正規化）。
  - 波長依賴：η(450)/η(650) 目標 3–4（可配置）；HWHM_b/HWHM_r 目標 1.5–2.5。
  - 光譜往返：ColorChecker D65 下 ΔE00 平均 < 5，最大 < 8。
  - 顆粒頻譜：輸出噪聲功率譜斜率 β∈[1,2]；RMS 顆粒度隨 ISO 單調增。
  - Halation 路徑：亮點近暗背景的徑向能量分配曲線，長尾呈指數/洛倫茲形，且紅通道尾部占比最大。
- 驗證資料
  - 實拍/掃描對比（CineStill 800T 無 AH 的極端紅色 halation 作為視覺基準案例）。
  - 廠商光譜敏感度曲線 CSV；CIE CMFs；色卡。
- 數值穩定
  - 無 NaN/Inf；所有核在 16-bit 浮點下無下溢；卷積採 tile 化避免 >4 GB。

---

## 可操作的修正方案（含驗證）

1) 波長依賴散射（Phase 1）
- 實作：
  - 定義 η_c 與 σ_c 分離：對 r/g/b 或 31 通道聚合到 3 通道；η_c ∝ λ_c^-p 正規化使平均 η 固定；σ_c ∝ (λ_ref/λ_c)^q。
  - 雙段核：K_c = ρ_c G(σ_c) + (1-ρ_c) E(κ_c)，ρ_c、κ_c 由 λ 或查表給定。
- 驗證：
  - 白點刀口法量測跨通道 MTF；
  - 能量守恆；
  - 藍外圈視覺測試（路燈）。

2) Halation（Phase 2）
- 實作：
  - 以 T(λ)=exp(-α(λ)L) 形成 f_h(λ)=k T(λ)^2 R_bp（可含層回程修正）；
  - 以 exponential 長尾核，半徑與能量隨 λ 設定；CineStill 設 α→0、k↑。
- 驗證：
  - 徑向能量曲線；
  - CineStill 紅光暈再現；
  - 整體守恆。

3) Mie 查表（Phase 5）
- 實作：
  - 用 m(λ)=n_AgBr(λ)/n_gelatin(λ)；粒徑對數常態分布加權；
  - 角度→空間：r=z_eff tanθ；求得（σ, κ, ρ）的壓縮表示存檔，線性插值。
- 驗證：
  - 與全 Mie PSF 的 PSNR/SSIM 誤差；
  - 插值誤差 < 2%；
  - 視覺長尾更自然。

4) 光譜模型（Phase 4）
- 實作：
  - 優先讀入 CSV 曲線；無則用 2–3 峰混合擬合；
  - Smits 31 通道往返測試 ΔE00 門檻；
  - 與 Phase 1/2 之 λ 依賴一致。
- 驗證：
  - ColorChecker；
  - D50/D65 轉換下的色溫偏移可預測。

5) 顆粒叢集（Phase 3）
- 實作：
  - Perlin/Simplex 參數掃描，使功率譜 β 命中目標；
  - ISO → {d_mean, σ_d, Var_cluster} 對映表。
- 驗證：
  - FFT 斜率；
  - 視覺 A/B 與高 ISO 片種比對。

---

## 風險

- 模型不可辨識性：η 與 σ/κ 同時調整可能產生等效視覺效果，需以能量守恆與 MTF 測試分離校準。
- 數值邊界：長尾核在大圖像上可能造成邊界能量丟失或累積，需實作 per-pixel 有效權重正規化。
- 資料依賴：缺乏片種光譜曲線時，擬合可能導致色彩偏差；需提供「通用曲線」與「片種專屬曲線」兩種路徑。
- 效能：31 通道 + 雙層卷積在 2000×3000 圖上接近上限；需快取與降採樣策略。

---

## 可驗證指標（KPIs）

- 能量守恆誤差 < 0.01%（整圖、分通道）
- ΔE00（sRGB→Smits→sRGB, D65）：平均 < 5，最大 < 8
- HWHM 比例：HWHM_b/HWHM_r ∈ [1.5, 2.5]
- η 比例：η_b/η_r ∈ [2.0, 4.5]（可配置，預設 ~3.5）
- Halation 長尾：徑向能量在 20–150 px 區間呈近似指數衰減，紅通道尾部占比最大
- 顆粒功率譜：β ∈ [1, 2]；RMS 顆粒度隨 ISO 單調增
- 效能：2000×3000 < 10 s；記憶體 < 4 GB；查表載入 < 100 ms

---

## 下一步（實作優先序）

1) Phase 2 參數更正（Beer–Lambert + 命名 + 守恆測試）
2) Phase 1 重新標度：η 與 σ 解耦；q≈0.8 預設；雙段核
3) Phase 5 查表以相對折射率與角→空間映射；導出（σ, κ, ρ）表
4) Phase 4 導入 CSV 曲線 + ΔE 測試；Smits 往返基準
5) Phase 3 FFT 驗證 + ISO 對映表
6) Phase 6 邊界能量補償與效能 profiling（快取/降採樣）

---

## 參考文獻與資料來源

- Bohren, C. F., & Huffman, D. R. (1983). Absorption and Scattering of Light by Small Particles. Wiley.
- van de Hulst, H. C. (1957). Light Scattering by Small Particles. Dover.
- Ishimaru, A. Wave Propagation and Scattering in Random Media. IEEE Press.
- Mees, C. E. K., & James, T. H. (1977). The Theory of the Photographic Process (4th ed.). Macmillan.
- Palik, E. D. Handbook of Optical Constants of Solids. Academic Press.（AgBr/AgCl、明膠/水相折射率）
- Smits, B. (1999). An RGB to Spectrum Conversion for Reflectances. SIGGRAPH Technical Note.
- CIE 1931/1964 標準觀察者與色度學資料；colour-science 套件文檔。
- Kodak/Fujifilm 片種技術資料表（光譜敏感度、反射/透射曲線、rem-jet 描述）。

---

附註：本報告在「物理啟發、可實作」的原則下提出折衷模型與驗證路線，避免為追求理論完美而超出 10s/張的效能約束。