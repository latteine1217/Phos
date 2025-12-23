# Physicist Review: Spectral Brightness Fix (TASK-008)

作者: Physics Reviewer
日期: 2025-12-23
狀態: 審查完成（含決議）

---

## 背景

問題: Spectral 模式輸出顯著偏暗（約 22%–65%）
根因: `apply_film_spectral_sensitivity()` 回傳 Linear RGB，調用端誤當 sRGB 顯示，缺少 IEC 61966-2-1:1999 gamma 編碼
修復: 在該函數內於正規化之後、裁剪與重塑之前加入 sRGB gamma 編碼

參考與對照文件:
- 調試報告: tasks/TASK-008-spectral-brightness-fix/debug_playbook.md（亮度追蹤、守恆驗證）
- 修復實作: tasks/TASK-008-spectral-brightness-fix/fix_implementation.md（實作位置 Line 951-959）
- 程式碼: phos_core.py
  - rgb_to_spectrum(): 行 511-519（sRGB→Linear 反伽馬）
  - xyz_to_srgb(): 行 754-760（sRGB gamma 參考）
  - apply_film_spectral_sensitivity(): 行 936-960（正規化 + 新增 gamma），行 952-960（gamma 核心）

---

## 方法/依據

- 審閱三份文件內容與 phos_core.py 指定程式段，逐條對照:
  - 色彩空間流程與數學公式（sRGB 反/正伽馬、Smits 1999 光譜重建）
  - 光譜積分與正規化（白色平坦光譜）
  - gamma 分段閾值與數值穩定性
- 檢核關鍵實測數據（Debug Playbook 第 22–33 行、36–51 行、108–132 行、135–171 行）
- 與 IEC 61966-2-1:1999、CIE 1931 以及 Smits (1999) 理論一致性比對

---

## 關鍵結論（Physical Correctness Assessment）

總結判定: 通過（Approve with minor notes）

1) 色彩空間一致性: 通過
- 物理層輸出應為線性量，膠片敏感度積分的正確物理輸出確為 Linear RGB:
  R = \(\int S(\lambda)\,S_{red}(\lambda)\,\mathrm{d}\lambda\)、G、B 同理。
- 現實顯示需要 sRGB gamma 編碼；於 `apply_film_spectral_sensitivity()` 內部執行可視為「掃描/顯示階段」的映射，若該函數被定位為“光譜→顯示圖像”的終端，位置正確。
- 公式與 xyz_to_srgb() 一致: `c <= 0.0031308: 12.92c；else: 1.055 c^{1/2.4}-0.055`（phos_core.py 行 952-960；xyz_to_srgb 行 754-760）。閾值、指數、係數符合 IEC 61966-2-1:1999。

2) 能量守恆: 通過（線性域）
- Debug Playbook 證據: sRGB 0.5 經反伽馬變為 Linear 約 0.216（第 22–33 行），Smits 重建光譜後以 CIE ȳ 積分得到的 Y 與 0.216 一致（第 38–51 行）。Smits 在線性域守恆無誤。
- Gamma 編碼僅為顯示非線性重映射，對線性域能量守恆不構成破壞；「能量守恆」的核對應在 gamma 前完成。
- 白點往返: sRGB(1,1,1) → Spectrum → Film Linear → sRGB(1,1,1) 成立（第 108–119 行）。

3) 物理模型完整性: 基本正確
- 管線順序：sRGB 圖像 → 反伽馬至 Linear → Smits RGB→Spectrum（反射率近似） → 與膠片敏感度積分（線性曝光量） → gamma 編碼顯示。符合「攝影/掃描」的抽象流程。
- 注意: `apply_film_spectral_sensitivity()` 未引入照明 SPD 權重（如 D65）。由於 Smits 重建的是可行反射率以重現原 sRGB，而非攝影機 SPD，省略 SPD 屬可接受的簡化，但會導致與標準 XYZ 路徑在部分色域出現差異（見紅/綠純色案例）。

4) 膠片物理: 通過（帶備註）
- 敏感度曲線峰值歸一化至 1，積分量級與 CIE ȳ 同階（Debug Playbook 第 87–105 行）。
- 正規化邏輯: 以「平坦白色光譜」作參考，對 R/G/B 通道各自歸一化（phos_core.py 行 936–950）。這在「三層感光乳劑獨立曝光」假設下合理，可保留膠片色彩個性。
- Portra400 紅層敏感度積分較高（sum≈13.89 > 綠 12.45 > 藍 7.97），符合該系列偏暖、膚色優化的設計取向。純色亮度偏差（如紅色偏亮）是「特性」而非 Bug。

5) 數值精度與穩定性: 通過
- 反/正伽馬閾值分別為 0.04045 與 0.0031308，公式正確；在 `np.power()` 前以 `np.maximum(c,0)` 抑制負值（phos_core.py 行 957-959），避免 NaN。
- float32 精度對本流程足夠，31 點矩形積分（Δλ=13nm）與分段函數無明顯數值風險。

---

## 修復方案評價

- Gamma 編碼位置: 正確。放在「通道正規化之後、裁剪與形狀還原之前」可確保：
  - 以線性量進行光譜積分與白點正規化（物理正確）
  - 將最終輸出轉為 sRGB 便於顯示與下游一致性
- 公式符合標準: 是。與 `xyz_to_srgb()` 完全一致（係數與閾值）。
- 與現有 API 一致性：`xyz_to_srgb()` 返回 sRGB；本函數亦改為返回 sRGB，提高一致性。
- 可替代方案：
  1) 新增 `apply_gamma: bool=True` 參數（Debug Playbook 建議的 Option A），預設 True 以維持顯示正確；需要 Linear 輸出的離線流程可設 False。這可減少將來擴展（例如在 film RGB 空間進一步做物理處理）時的耦合風險。
  2) 保留現修復，改在文檔中明示「返回 sRGB」與「用途定位為顯示端」。

---

## 潛在問題識別（與對應物理解釋）

1) 純紅/純綠亮度偏差
- 現象: 修復後純紅亮度 +52%，純綠約 -18.8%（fix_implementation.md 第 102–119 行）。
- 解釋: 膠片三層敏感度曲線與 CIE 觀察者函數不同，且本流程未做「攝影機到顯示器」的 3×3 色彩校正矩陣；因此在飽和主波長附近，通道加權與 sRGB 視覺亮度有系統性偏差。此為「膠片特性」，非守恆問題。

2) Smits 算法的固有限制
- Smits (1999) 以 7 基向量上採樣可實現的反射率，能在標準觀察者與 D65 條件下重建原 RGB，但對極端光譜或飽和純色的色度/亮度再現存在偏差；此外，本流程將該反射率直接送入「膠片」而非 CIE 觀察者，模型差異會被放大。

3) 敏感度曲線數據可信度
- 當前曲線為合成/正規化數據（峰值=1），其形狀決定了最終色彩個性；若需更高準確度（尤其是純色再現），需以實測或廠商數據替換，並配合 3×3 色彩校正。

4) 「能量守恆」的驗證域
- 能量守恆應在「線性域」檢驗（gamma 前）。Debug 指標中「在 sRGB 空間」的表述（Debug Playbook 第 304–310 行）應修正為「在 Linear 空間」。

---

## 改進建議

短期（立即可行）
- A. API/文檔一致性：在 `apply_film_spectral_sensitivity()` 的 Docstring 明確標註「返回 sRGB（已 gamma 編碼）」；或補充 `apply_gamma` 參數並標出預設 True。並在 PHYSICAL_MODE_GUIDE 中更新流程圖（已在 fix_implementation.md 建議）。
- B. 測試修訂：
  - 將“線性性”測試改為「線性域檢查」或「單調性」檢查（見 fix_implementation.md 測試 3 建議）。
  - 能量守恆相關斷言改在 gamma 前（線性域）。
- C. 指標措辭修正：將「能量守恆：Y_output/Y_input ≈ 1.0（在 sRGB 空間）」改為「在 Linear 空間」。

中長期（理論完善方向）
- D. 3×3 色彩校正矩陣（相機 Profile 類比）：在 D65 下，以一組代表性反射率樣本（如 Munsell、Macbeth 24 色卡、或對 Smits 基底的系統掃描）擬合線性「film RGB → Linear sRGB」的 3×3 矩陣 M，使得
  $$\mathbf{c}_{sRGB}^{lin} \approx M\,\mathbf{c}_{film}^{lin}$$
  再做 sRGB gamma。可顯著減少純紅/綠偏差，同時保留膠片色彩個性（曲線形狀在 M 中被整體線性校正）。
- E. 照明體敏感: 在 `apply_film_spectral_sensitivity()` 提供可選 `illuminant_spd`，使積分改為
  $$R = \int R_{obj}(\lambda)\,E_{illum}(\lambda)\,S_{red}(\lambda)\,\mathrm{d}\lambda$$
  與標準觀察者路徑一致。預設仍為平坦（維持現行視覺風格），但可作科學驗證。
- F. 更精確的 RGB→Spectrum 上採樣：評估 Jakob & Hanika (2019) 或後續工作，以改善飽和與窄帶情形的重建誤差。

---

## 風險

- 介面行為變更風險（中）: 若既有調用端假設返回 Linear，將出現「雙重 gamma」或其他非線性堆疊。緩解：
  - 明確文檔與 Changelog 標註 Breaking Change
  - 或引入 `apply_gamma` 開關，預設 True
- 色彩偏移感知（低）: 純色與高度飽和色塊的亮度/色度與標準 sRGB 流程不同，源於膠片敏感度特性。緩解：提供可選 3×3 校正矩陣。
- 數值（低）: 低於 0 的微小數值（數值誤差）在 `np.maximum` 已處理；float32 足夠。

---

## 可驗證指標（驗收準則）

功能與數值
- 50% 灰往返: sRGB(0.5,0.5,0.5) → … → sRGB 誤差 < 1%（Debug 實測 0%）。
- 白點往返: sRGB(1,1,1) → … → sRGB 誤差 = 0%。
- 線性能量守恆: 在 gamma 前，Y_spectrum / Y_input_linear ∈ [0.98, 1.02]（圖像均值層面）。
- 非負性: Film Linear 與最終 sRGB 皆 ≥ 0。

視覺場景
- 藍天場景平均亮度偏差 < 15%（修復後實測 9%）。
- 50% 灰卡平均亮度偏差 < 10%（修復後 7.7%）。

邊界/穩定性
- 小於閾值區段: 對 0–0.0031308 線性段輸入，輸出為 12.92×c（抽樣測試 1024 點，最大誤差 < 1e-6）。
- 單調性: 對任意單色通道 c∈[0,1]，輸出單調遞增且 < 1。

---

## 下一步

1) 文檔與 API
- 更新 `phos_core.py::apply_film_spectral_sensitivity()` Docstring：明確返回 sRGB；或新增 `apply_gamma` 參數（預設 True）。
- 更新 PHYSICAL_MODE_GUIDE 與 CHANGELOG（fix_implementation.md 已列清單）。

2) 測試
- 調整“線性性”測試為線性域或單調性測試；將「能量守恆」驗證移至 gamma 前。

3) 研究性改進（可選）
- 設計並驗證 3×3 線性色彩校正矩陣（film RGB → linear sRGB）。
- 增設 `illuminant_spd` 選項以供科學驗證。

---

## 最終決議

✅ 批准進入生產（Approve）
- 條件: 文檔標註返回色彩空間；或在近期版本提供 `apply_gamma` 參數以降低介面風險。
- 理由: 色彩空間流程正確、與 xyz_to_srgb 一致；Smits 線性域能量守恆通過；數值穩定；修復有效消除亮度損失。

---

## 參考

- IEC 61966-2-1:1999, sRGB Standard (gamma: piecewise 12.92/1.055, threshold 0.0031308)
- B. Smits, 1999, "An RGB-to-Spectrum Conversion for Reflectances"
- CIE 1931 2° Standard Observer（x̄(λ), ȳ(λ), z̄(λ)）
- 本專案程式碼與文檔:
  - phos_core.py: rgb_to_spectrum() 行 511–519；xyz_to_srgb() 行 736–771；apply_film_spectral_sensitivity() 行 936–969（gamma 於 952–960）
  - tasks/TASK-008-spectral-brightness-fix/debug_playbook.md
  - tasks/TASK-008-spectral-brightness-fix/fix_implementation.md
