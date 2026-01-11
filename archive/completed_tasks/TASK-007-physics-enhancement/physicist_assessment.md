# Phos 物理理論加強計畫（Physicist Assessment & Enhancement Plan）

作者：資深物理科研專家（計算光學與膠片科學）  
日期：2025-12-20  
版本：v1.0  
目標：將 Phos 的物理正確性由 7.0/10 提升至 8.5-9.0/10，並建立可驗證、可擴展的技術框架。

---

## 1. 現狀分析（Current State）

- 當前物理正確性評分：7.0/10
  - 理由：
    - ✅ 能量守恆（Bloom 物理模式，PSF 正規化）穩定達成，誤差 < 0.01%
    - ✅ H&D（Hurter-Driffield）特性曲線基本符合負片/正片行為，Toe/Shoulder 具備單調性與數值穩定性
    - ✅ Poisson 顆粒統計正確呈現暗部顆粒增強、亮部顆粒減弱的物理趨勢
    - ✅ Medium Physics：Bloom/Halation 分離的管線已建置，具備波長依賴入口（Phase 1）和 Mie 查表入口（Phase 5）
    - ⚠️ PSF 波長依賴次方關係為經驗式（p≈3.5、q≈0.8），缺乏嚴格理論推導與 ISO-顆粒關聯的閉環
    - ⚠️ Halation 參數命名與 Beer-Lambert（T=exp(-αL)）的對應不一致，存在混淆與重複字段
    - ⚠️ Mie 查表生成端有相對折射率（relative refractive index）使用錯誤（以空氣為介質，而非明膠），導致散射權重與角度分布偏離

- 已實現的物理機制清單：
  - Bloom（散射）
    - 能量守恆版（Energy-Conserving PSF Convolution）
    - 雙段核 PSF（Gaussian + Exponential Tail）
    - 波長依賴入口（Phase 1）與 Mie Lookup 入口（Phase 5）
  - Halation（背層反射）
    - Beer-Lambert 概念性實作（多尺度高斯近似長尾）
    - 能量守恆重標定（in/out energy matching）
  - Poisson Grain（泊松顆粒噪聲）
    - 光子計數統計與空間相關性（Gaussian blur of noise）
  - H&D Curve（Hurter-Driffield 特性）
    - Toe/Shoulder/Linear 區段、對數響應、密度→透射率
  - Tone Mapping（Reinhard/Filmic）
  - Spectral Sensitivity（Phase 4.5 實驗性：RGB↔Spectrum roundtrip with film curves）

- 現存的物理問題分類：
  - 🔴 Critical（導致明顯不一致）
    1. Mie 散射相對折射率（m = n_particle / n_medium）使用錯誤介質（空氣），應為明膠/水相，導致 η(λ)、σ(λ) 查表偏差 20-50%，共振峰位置錯置，藍紅散射比例失真。
    2. Halation 參數命名與含義不一致（transmittance vs absorption vs attenuation），雙程（往返）能量的計算與 Beer-Lambert 公式未一致化，易致能量不守恆或視覺行為不連貫。
  - 🟡 Important（影響準確度）
    1. PSF 波長依賴次方關係（η ∝ λ^-p、σ ∝ λ^-q）缺乏理論推導與 ISO/粒徑分布的耦合；目前的 p=3.5 與 q=0.8 屬經驗設置。
    2. 粒徑分布未與 ISO 明確關聯，導致散射強度與顆粒感在不同膠片之間的跨片一致性欠佳。
    3. 光譜敏感度曲線在核心流程中仍以線性權重近似（Matrix weights），多峰非對稱形狀與層間串擾尚未全面落地於主流程（Phase 4.5 實驗性，尚需 ΔE 檢驗）。
  - 🟢 Nice-to-have（進階特性）
    1. 互易律失效（Reciprocity Failure）：長/短曝光的化學動力學非線性
    2. 色溫/照明光源適應（Daylight vs Tungsten）：von Kries/Bradford 適應矩陣整合
    3. 多次散射（Multiple Scattering）迭代卷積：延長 halation 尾部，降低整體對比
    4. 角度依賴散射（Directional PSF）：前向散射占優 + Lorentzian 尾部

---

## 2. 優先改進項目（Priority Enhancements）

以下根據 PHYSICS_IMPROVEMENTS_ROADMAP 與 Phos_0.3.0 實作現況，重新排序與細化：

### P0 - Critical Fixes（必須修正，2-3天）

1) 🔴 問題：Mie 散射相對折射率使用錯誤介質（空氣）
- 問題描述：scripts/generate_mie_lookup.py 中以 n_agbr 相對「空氣」建立 m，而銀鹵化物粒子實際浸潤於明膠（n≈1.50-1.52）中；相對折射率 m(λ) 應為 n_AgBr(λ)/n_gelatin。
- 根本原因：誤解 Mie 參數 m 的定義與介質環境設定，導致散射截面與相函數求值偏差。
- 影響量化：
  - η(λ) 比例可能偏差 20-50%，藍/綠/紅散射能量比例錯誤；
  - σ(λ)（PSF 寬度）因角度分布改變而偏差 10-30%；
  - 視覺：白光高光的藍暈強度/半徑誤判，Mie 振盪峰相對位置錯置，導致夜景路燈、霓虹、逆光高光的色散表現偏假。
- 修正方案：
  - 公式：m(λ) = n_AgBr(λ) / n_gelatin
    - n_AgBr(λ) 建議採用 Palik 光學常數插值（可見光 400-700nm）；
    - n_gelatin ≈ 1.50（可做溫度/濕度微調，初期固定）。
  - 代碼層級（生成查表側）：
    - 在 scripts/generate_mie_lookup.py 中，改用 m_relative = n_agbr_air(λ) / n_gelatin；
    - 使用 wavelength_nm 向量化生成 x = 2πa/λ（a 依 ISO 粒徑分布代表值），m = complex(m_relative, k)（若需引入吸收，k>0）；
    - 生成 v3 查表：sigma(λ, ISO)，kappa(λ, ISO)，rho(λ, ISO)，eta(λ, ISO)。
  - Python 示例：
    ```python
    # 修正相對折射率
    n_gelatin = 1.50
    def n_agbr_nm(wavelength_nm: float) -> float:
        # Palik-based linearized approximation (placeholder)
        # e.g., n(λ) ≈ 2.20 + 0.08*(550/λ)
        return 2.20 + 0.08 * (550.0 / wavelength_nm)
    m_rel = n_agbr_nm(550.0) / n_gelatin  # ≈ 1.47
    # pass m_rel into Mie solver
    ```
- 驗證方法：
  - 單元測試：test_mie_relative_index（1.4 < m < 1.7 @ 550nm）
  - 功能測試：compare_mie_versions.py 對比 v2 vs v3，檢查 η_b/η_r（期望 1.5-4.0）與 σ_b/σ_r（期望 1.2-2.0）
  - 視覺驗證：白點光源在黑底的高光暈色散（藍暈外圈更顯著，核心偏黃）

2) 🔴 問題：Halation 參數命名與 Beer-Lambert 不一致
- 問題描述：film_models.HalationParams 中存在 transmittance_r/g/b 與 wavelength_attenuation_r 等混用，ah_absorption 的含義與雙程透過率的乘法關係未嚴格落地。
- 根本原因：將「吸收（α）」與「透射率（T）」、單程/雙程的能量路徑混合命名，導致認知與實作不一致。
- 影響量化：
  - 能量分配在 halation 分支的比例可能上下相差 2-10 倍；
  - Portra vs CineStill 的紅暈差異無法穩定重現（AH 層的影響被弱化/強化不一致）。
- 修正方案：
  - 以 Beer-Lambert 標準化參數：
    - Emulsion single-pass transmittance: T_e,r/g/b
    - AH layer single-pass transmittance: T_AH,r/g/b（或給吸收係數 α_AH,r/g/b 與厚度 L_AH）
    - Base single-pass transmittance（如片基/背層）：T_b,r/g/b（若需要）
    - Backplate reflectance: R_bp（0-1）
  - Halation effective fraction（雙程近似）：
    - f_h(λ) = (T_e(λ) · T_AH(λ) · T_b(λ))^2 · R_bp
  - 在 apply_halation() 中，移除「模糊命名」並明確採用上式，保留能量守恆的 in/out normalization。
  - Python 公式實作（擬）：
    ```python
    def halation_fraction(lambda_nm: float, params: HalationParams) -> float:
        T_e = params.emulsion_transmittance(lambda_nm)
        T_ah = params.ah_transmittance(lambda_nm)
        T_b = params.base_transmittance(lambda_nm)
        return (T_e * T_ah * T_b)**2 * params.backplate_reflectance
    ```
- 驗證方法：
  - 單元測試：test_beer_lambert_energy（halation_energy 合理範圍 0-10%）
  - 功能測試：CineStill 800T 無 AH 層 vs Portra 400 有 AH 層（紅暈能量至少相差 ~10x）
  - 視覺驗證：紅色通道 halation 能量 > 藍色通道（夜景路燈）

3) 🔴 問題：能量管線邊界條件與守恆性檢查不足（Halation 分支）
- 問題描述：apply_halation() 在多尺度核近似指數拖尾時，雖有能量重標定，但 T_r/g/b 的來源與雙程定義不一致，可能導致局部過曝或負值裁切頻繁。
- 根本原因：Halation 能量分支的 in/out 計算未與 Bloom 的節點對齊，且散射閾值與能量係數的設置與參數意義混合。
- 影響量化：局部像素的能量守恆誤差可達 1-3%，導致高光區域邊界 halo 不自然。
- 修正方案：
  - 明確「高光提取→halation_energy→卷積→能量重標定→合成」的順序；
  - 使用與 Bloom 相同的能量守恆形式：output = input - E_scattered + conv(E_scattered, PSF)；
  - 將 halation_fraction 與 threshold、energy_fraction 聯繫為無量綱乘子，避免與 T 的物理量綱混合。
- 驗證方法：
  - 單元測試：區域能量守恆（局部窗口 sum 誤差 < 0.1%）
  - 整體測試：test_energy_conservation 擴展至 halation 分支（Bloom+Halation 合成後總能量誤差 < 0.05%）


### P1 - Important Improvements（建議實作，1-2週）

1) 🟡 問題：PSF 波長依賴模型缺乏理論依據與分段一致性
- 問題描述：目前 η ∝ (λ_ref/λ)^p，σ ∝ (λ_ref/λ)^q（p=3.5, q=0.8）為經驗式；對於 x=2πa/λ（a≈0.5-3μm）落在 Mie 範圍的膠片，應採用 Mie 查表或分段模型（Rayleigh/Mie/Geometric）。
- 根本原因：尚未建立 ISO→粒徑分布→Mie/Rayleigh 切換→PSF 參數 的閉環。
- 影響量化：藍/紅散射比值與 PSF 寬度的比例可能偏離真實 10-30%。
- 修正方案：
  - 方案 A：全程使用 Mie 查表（v3），將 η(λ, ISO)、σ(λ, ISO)、ρ(λ, ISO)、κ(λ, ISO) 由查表提供；
  - 方案 B：分段混合模型：
    - Rayleigh（a < 0.3μm）：η ∝ λ^-4，σ_angular ≈ 常數；
    - Mie 過渡（0.3μm ≤ a ≤ 2μm）：由查表插值；
    - 幾何光學（a > 2μm）：η ∝ λ^-1，前向散射近似加權。
  - 接口設計：apply_wavelength_bloom() 根據 film.ISO 和派生粒徑決定使用的段。
- 驗證方法：
  - 數值：η(450)/η(650) 在 1.5-4.0；σ(450)/σ(650) 在 1.2-2.0；
  - 視覺：白高光呈現「核心偏黃、外圈偏藍」；
  - 回歸：與 v2/v3 查表版本比對，偏差 < 10%。

2) 🟡 問題：ISO-粒徑分布與顆粒/散射未統一
- 問題描述：film_models 粒徑與 ISO 未建立可重現的公式關聯；顆粒強度、散射比例、Mie 粒徑輸入分離設定。
- 根本原因：缺少 derive_physical_params_from_iso() 的統一入口。
- 影響量化：不同片型在「同 ISO」下的顆粒度/散射度跨片一致性差，顆粒/暈行為不穩定。
- 修正方案：
  - 建立 derive_physical_params_from_iso(iso) → {d_mean, d_sigma, scattering_ratio, grain_intensity, mie_eta/sigma}；
  - 在 get_cached_film_profile() 載入時對應更新 film.bloom_params、grain_params 與 wavelength_bloom_params。
- 驗證方法：
  - 單調性：RMS granularity 隨 ISO 單調遞增；
  - 視覺：ISO 3200 > ISO 800 > ISO 400 的顆粒顯著性；
  - 數值：Poisson 模式在暗部 SNR 與 ISO 交互下的合理性。

3) 🟡 問題：光譜敏感度曲線（multi-peak, asymmetric）未全面整合
- 問題描述：Phase 4.5 的色譜 roundtrip 與 film 名錄曲線尚未在主流程作為標準路徑；目前 spectral_response() 仍是線性權重近似。
- 根本原因：未進行 ColorChecker ΔE 驗證與誤差控制，擔心效能與穩定性。
- 影響量化：ΔE 可能較多片型在 5-10 之間，無法重現片型獨特色相偏移（Velvia 綠、Portra 肤色長尾等）。
- 修正方案：
  - 引入廠商 CSV（Kodak/Fuji/Ilford）曲線，或以 2-3 峰 skewed Gaussian 混合形式建模；
  - 在 optical_processing() 前/後進行光譜處理（建議後期調整以減少 roundtrip 誤差）。
- 驗證方法：
  - ColorChecker ΔE00（目標 < 5）；
  - 色彩適應矩陣穩定性（Bradford）對應片型；
  - 片型特徵色相測試（Velvia 綠、Ektar 紅）。


### P2 - Advanced Features（可選，1-2月）

1) 🟢 互易律失效（Reciprocity Failure）
- 問題描述：長/短曝光時化學反應動力學導致 E_eff = I · t^p（p < 1）
- 根本原因：銀鹽感光過程非瞬時，短時/長時條件下反應路徑不同。
- 影響量化：曝光補償可達 +1/3EV（10s）至 +1EV（60s）。
- 修正方案：apply_reciprocity_failure(exposure_time, intensity)
  - 公式：p = f(t)，短時 p≈0.95、長時 p≈0.85 - 0.05·log10(t)
- 驗證方法：
  - 片型案例對比（T-Max、Velvia）補償曲線；
  - 人為合成的長曝光白點 vs 短曝光白點對比。

2) 🟢 色溫/照明光源適應
- 問題描述：日光膠片（D65）在鎢絲（3200K）偏黃，需 von Kries/Bradford 適應矩陣。
- 修正方案：apply_color_temperature_adaptation()，以 planck_locus + Bradford Matrix 變換。
- 驗證方法：
  - 標準灰卡在 3200K/5500K 下 ΔE 減小；
  - 片型在不同光源下的色相偏移合理（CineStill 800T 在日光偏藍）。

3) 🟢 多次散射（Multiple Scattering）
- 問題描述：現為單次散射；真實可能 2-5 次。
- 修正方案：apply_multiple_scattering(image, psf_single, n=3)，每次散射能量遞減。
- 驗證方法：
  - 長距離 halation 尾部更長、對比度降低；
  - 能量守恆擴展檢查（多次迭代後誤差 < 0.1%）。

4) 🟢 角度依賴散射（Directional PSF）
- 問題描述：Lambertian 簡化忽略 Mie 前向散射主導。
- 修正方案：directional_psf(angle, λ) 混合 forward Gaussian + wide-angle power-law tail。
- 驗證方法：
  - 角度分布的合成點源測試；
  - 對比文獻的相函數形狀（定性）。

---

## 3. 實作順序建議（Implementation Roadmap）

- 階段劃分：
  - 短期（Week 1）：P0 全部修正 → 目標分數 7.8/10
  - 中期（Week 2-3）：P1 主要改進（Mie v3 + ISO閉環 + Spectral CSV/混合）→ 8.5/10
  - 長期（1-2 月）：P2 進階特性 → 9.0/10

- 每階段交付與驗證指標：
  - 短期：
    - 交付：Mie v3 查表（m=AgBr/gelatin）、Halation 參數重構、能量守恆測試擴展
    - 指標：η_b/η_r ∈ [1.5, 4.0]；σ_b/σ_r ∈ [1.2, 2.0]；總能量誤差 < 0.05%
  - 中期：
    - 交付：apply_wavelength_bloom 接入查表/分段模型；derive_physical_params_from_iso 實作；Spectral sensitivity CSV 支援 + ΔE 測試
    - 指標：ColorChecker ΔE00 < 5；ISO-RMS 顆粒度單調；v2/v3 差異 < 10%
  - 長期：
    - 交付：互易律失效、色溫適應、多次散射、方向依賴 PSF
    - 指標：長曝光補償曲線與文獻一致；灰卡 ΔE 跨光源 < 3；halation 尾部延長且能量守恆 < 0.1%

- 依賴關係圖（文字描述）：
  - P0-1（Mie v3）→ P1-1（PSF 分段）→ P1-2（ISO 閉環）→ P1-3（Spectral CSV/混合）→ P2（互易/色溫/多次/角度）
  - Halation 參數重構 → Halation 能量守恆擴展 → P2 多次散射

---

## 4. 測試驗證框架（Validation Framework）

- 物理一致性測試：
  - 量綱一致性：
    - Halation/Bloom 的能量分支使用無量綱係數（η、f_h）與歸一化 PSF（∑PSF=1）；
    - Beer-Lambert：T=exp(-αL) 層級檢查（α：cm⁻¹；L：cm；T：無量綱）。
  - 守恆律：
    - Output = Input - E_scattered + Conv(E_scattered)；
    - 全圖能量誤差 < 0.05%；局部窗（64×64）誤差 < 0.1%。
  - 單調性：
    - H&D：曝光↑ → 透射率↓（單調遞減）；
    - ISO：顆粒 RMS ↑；
    - 波長依賴：η_b/η_r、σ_b/σ_r 在合理區間。

- 數值驗證測試：
  - 查表對比：compare_mie_versions（v2 vs v3）偏差 < 10%；
  - 色卡對比：ColorChecker ΔE00 < 5；
  - 片型特徵：CineStill 紅暈至少為藍通道 2×；Velvia 綠色飽和提升明顯。

- 視覺驗證測試：
  - 夜景路燈白點：核心偏黃、外圈偏藍；
  - 逆光高光人像：Portra 柔和肩部、皮膚紅層長尾；
  - 黑白片：HP5/Tri-X 的顆粒與對比差異。

- Python 測試示例：
  ```python
  def test_mie_relative_index():
      m = calculate_relative_index(wavelength=550)
      assert 1.4 < m < 1.7

  def test_halation_energy_conservation():
      # 將 halation 分支納入總能量測試
      img = np.random.rand(256, 256).astype(np.float32)
      params = HalationParams(...)
      out = apply_halation(img, params, wavelength=650)
      err = abs(out.sum() - img.sum()) / img.sum()
      assert err < 0.0005

  def test_iso_grain_monotonic():
      g50 = derive_granularity(50)
      g400 = derive_granularity(400)
      g1600 = derive_granularity(1600)
      assert g50 < g400 < g1600
  ```

---

## 5. 風險評估（Risk Assessment）

- 破壞性變更風險（向後相容性）：
  - 風險：Mie v3 導致視覺輸出改變；Halation 參數重構破壞舊配置；Spectral CSV 引入運算時間與色彩差異。
  - 緩解：保留舊模式（ARTISTIC/HYBRID）、版本化查表（v1/v2/v3），提供開關與回退，文檔說明差異。

- 視覺品質退化風險：
  - 風險：物理準確性提升可能減少「討喜」光暈與顏色；
  - 緩解：提供 artistic 增益參數，允許在物理基準上增益（non-conserving）分支可選；HYBRID 允許自由混合。

- 計算成本增加風險：
  - 風險：Mie 查表插值、多次散射迭代、Spectral roundtrip 增加處理時間 10-50%；
  - 緩解：
    - 查表快取（_MIE_LOOKUP_TABLE_CACHE）
    - 自適應卷積（FFT for large kernels）
    - 多解析度預覽，低解析度先行、最終高精度再算。

---

## 6. 關鍵決策點（Decision Gates）

- 目標物理正確性分數：建議 8.5（中期目標）→ 9.0（長期目標）
- 可接受的效能開銷：
  - 中期（P1 完成）：+10-20%
  - 長期（P2 完成）：+20-50%（視是否啟用多次散射/光譜處理）
- 視覺品質 vs 物理準確度的權衡：
  - 原則：能量守恆與參數物理定義優先；
  - 範圍：允許在 HYBRID/ARTISTIC 模式下引入非守恆增益以滿足藝術目的，但物理模式下嚴格守恆；
  - 單獨開關：Spectral sensitivity、Mie lookup、Halation 長尾等可獨立開啟與權重調整。

---

## 7. 方法/依據（Methods / Rationale）

- 物理理論依據：
  - Beer-Lambert 定律：T(λ) = exp(-α(λ)·L)
  - Mie 散射理論：相對折射率 m = n_particle / n_medium，尺寸參數 x = 2πa/λ
  - Poisson 統計：SNR ∝ √曝光量，暗部噪聲比例高
  - H&D 曲線：D = γ·log10(H) + D_fog，Toe/Shoulder 非線性過渡

- 數值方法：
  - PSF 卷積（cv2.filter2D / FFT）保證能量守恆（∑PSF=1）
  - 雙段核組合（Gaussian + Exponential）
  - 插值查表（雙線性）用於 Mie σ、κ、ρ、η
  - Spectral roundtrip（RGB→Spectrum→RGB with film curves）

- 可辨識性（Identifiability）：
  - 將輸入參數分層：
    - 物理常數（n(λ)、α、L）
    - 派生參數（T、η、σ、ρ、κ）
    - 視覺權重（diffuse_weight、direct_weight、grain_intensity）
  - 測試覆蓋到上述分層，確保每一層的影響可區分、可追蹤。

---

## 8. 公式與程式碼細化（Equations & Code）

- 方程式（LaTeX）：
  - 散射能量守恆：
    $$
    I_{out} = I_{in} - E_s + (PSF * E_s), \quad \sum PSF = 1
    $$
  - Beer-Lambert 雙程近似：
    $$
    f_h(\lambda) = \left[T_e(\lambda) T_{AH}(\lambda) T_b(\lambda)\right]^2 R_{bp}
    $$
  - Mie 相對折射率：
    $$
    m(\lambda) = \frac{n_{AgBr}(\lambda)}{n_{gelatin}}, \quad x = \frac{2\pi a}{\lambda}
    $$
  - H&D：
    $$
    D = \gamma \log_{10}(H) + D_{fog}, \quad T = 10^{-D}
    $$

- 程式碼範例（Python）：
  ```python
  def energy_conserving_scatter(channel, eta, psf):
      highlights = np.maximum(channel - 0.85, 0.0)
      E = eta * highlights
      S = cv2.filter2D(E, -1, psf, borderType=cv2.BORDER_REFLECT)
      out = channel - E + S
      return np.clip(out, 0, 1)

  def halation_fraction(lambda_nm, params):
      T_e = params.emulsion_transmittance(lambda_nm)
      T_ah = params.ah_transmittance(lambda_nm)
      T_b = params.base_transmittance(lambda_nm)
      return (T_e * T_ah * T_b)**2 * params.backplate_reflectance

  def apply_halation_strict(lux, params, lambda_nm):
      f = halation_fraction(lambda_nm, params)
      highlights = np.maximum(lux - 0.5, 0)
      E = highlights * f * params.energy_fraction
      psf = get_long_tail_psf(params)
      S = convolve_adaptive(E, psf, method='auto')
      # renormalize energy
      if S.sum() > 1e-6:
          S *= (E.sum() / S.sum())
      return np.clip(lux - E + S, 0, 1)
  ```

---

## 9. 關鍵結論（Key Conclusions）

- Mie 相對折射率修正（AgBr/gelatin）是提升物理準確性的關鍵第一步；不修正會導致藍紅散射比例與共振結構錯誤，視覺偏差明顯。
- Halation 參數需全面採用 Beer-Lambert 的單程/雙程定義，避免命名與物理意義混亂；並以能量守恆形式合成。
- PSF 波長依賴與 ISO-粒徑閉環是中期達到 8.5/10 的關鍵；Spectral sensitivity 的 CSV/混合模型是提升片型差異與色彩準確度的必要步驟。

---

## 10. 風險與緩解（Risks & Mitigations）

- 視覺偏移風險：透過 HYBRID/ARTISTIC 模式保留原有風格；提供調參面板允許使用者折衷。
- 效能風險：採用查表快取、自適應卷積、低解析度預覽；將 Spectral roundtrip 作為可選開關。
- 測試負擔：建立標準測試樣例（ColorChecker、白點燈、ISO 梯度），持續集成。

---

## 11. 可驗證指標（Measurable KPIs）

- 能量守恆誤差（Bloom+Halation）：< 0.05%
- 色彩準確度（ColorChecker ΔE00）：< 5.0
- 波長散射比例：η_b/η_r ∈ [1.5, 4.0]；σ_b/σ_r ∈ [1.2, 2.0]
- ISO-顆粒單調性：RMS granularity ↑ 與 ISO ↑ 單調一致
- 效能開銷：物理模式 +10-20%，進階功能 +20-50%

---

## 12. 下一步（Next Steps）

- 立即行動（2-3 天）：
  - 修正 Mie 生成腳本的相對折射率（v3）並重生成查表；
  - 重構 Halation 參數命名與雙程公式，穩固能量守恆；
  - 增加測試：halation 能量守恆、Mie 比例檢查。

- 短期（1-2 週）：
  - 接入 Mie v3 查表或分段模型；
  - derive_physical_params_from_iso() 實作，統一顆粒/散射；
  - 引入 Spectral sensitivity CSV/混合，建立 ΔE 測試。

- 中長期（1-2 月）：
  - 互易律、色溫適應、多次散射、方向 PSF。

---

## 13. 參考（References）

- Palik, Handbook of Optical Constants of Solids（AgBr 折射率）
- Bohren, C. F., & Huffman, D. R. (1983). Absorption and Scattering of Light by Small Particles.
- Swinehart, D. F. (1962). The Beer-Lambert Law. Journal of Chemical Education.
- Hurter, F., & Driffield, V. C. (1890). Photo-Chemical Investigations... Journal of the Society of Chemical Industry.
- Chandrasekhar, S. (1960). Radiative Transfer. Dover.
- Robbins, H. (1955). A Remark on Stirling's Formula. American Mathematical Monthly.
- Kodak Publication H-1; Ilford Sensitometry; Fujifilm Velvia Technical Data.
- Bruce Lindbloom: Color Space Conversions; Charles Poynton: Gamma FAQ.

---

（完）