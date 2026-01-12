# 光譜校正工具套件

完整的物理理論驗證與光譜響應校正工具集。

## 📁 工具清單

### 1. 物理理論驗證器 (`physics_validator.py`)
**功能**：驗證光譜響應係數是否符合物理理論

**測試項目**：
- ✓ 能量守恆（Energy Conservation）
- ✓ 行正規化（Row Normalization）
- ✓ 非負性（Non-negativity）
- ✓ 對角線主導性（Diagonal Dominance）
- ✓ 單調性（Monotonicity）
- ✓ 線性疊加（Linearity - Grassmann's Laws）
- ✓ 交叉響應範圍（Cross-response Range）

**使用方式**：
```bash
# 驗證單個膠片
python tools/physics_validator.py --film Portra400

# 驗證所有膠片
python tools/physics_validator.py

# 安靜模式（僅顯示摘要）
python tools/physics_validator.py --quiet
```

---

### 2. 綜合校正工具 (`comprehensive_calibration_tool.py`)
**功能**：自動校正光譜響應係數，消除灰階色偏

**校正策略**：
- **策略 1**: Row Normalization（僅行正規化）
- **策略 2**: Diagonal Enhancement（僅對角增強）
- **策略 3**: Hybrid（推薦）- 行正規化 + 15% 對角增強
- **策略 4**: Conservative（保守）- 行正規化 + 10% 對角增強
- **策略 5**: Aggressive（激進）- 行正規化 + 25% 對角增強

**使用方式**：
```bash
# 校正所有膠片（使用策略3）
python tools/comprehensive_calibration_tool.py --all --strategy 3

# 校正單個膠片並導出代碼
python tools/comprehensive_calibration_tool.py --film Portra400 --export

# 比較所有策略
python tools/comprehensive_calibration_tool.py --film Velvia50 --compare-strategies

# 安靜模式
python tools/comprehensive_calibration_tool.py --all --quiet
```

---

### 3. 視覺化工具 (`calibration_visualizer.py`)
**功能**：生成校正前後對比圖表

**生成圖表**：
- 原始 vs 校正後矩陣熱力圖
- 行和比較（能量守恆）
- 灰階響應曲線
- 色偏分析
- 對角線主導性
- 性能指標摘要表

**依賴**：
```bash
pip install matplotlib
```

**使用方式**：
```bash
# 為單個膠片生成報告
python tools/calibration_visualizer.py --film Portra400

# 為所有彩色膠片生成報告
python tools/calibration_visualizer.py --all

# 指定輸出目錄
python tools/calibration_visualizer.py --all --output-dir ./reports

# 高解析度輸出
python tools/calibration_visualizer.py --film Ektar100 --dpi 300
```

**輸出範例**：
- `calibration_report_Portra400_strategy3.png` (3000×2000 px @ 150 DPI)

---

### 4. 一鍵測試套件 (`run_all_calibration_tests.py`)
**功能**：運行所有驗證與校正測試

**測試流程**：
1. 物理理論驗證（13款膠片）
2. 光譜響應校正（8款彩色膠片）
3. 生成視覺化報告（可選）
4. 導出校正後的代碼（可選）
5. 生成完整報告

**使用方式**：
```bash
# 運行所有測試（基本）
python tools/run_all_calibration_tests.py

# 運行測試 + 生成視覺化
python tools/run_all_calibration_tests.py --visualize

# 運行測試 + 導出代碼
python tools/run_all_calibration_tests.py --export

# 完整測試（所有功能）
python tools/run_all_calibration_tests.py --strategy 3 --visualize --export

# 安靜模式
python tools/run_all_calibration_tests.py --quiet
```

**輸出檔案**：
- `calibration_test_results.json` - JSON格式測試結果
- `calibrated_coefficients.txt` - 校正後的係數（可選）
- `calibration_reports/` - 視覺化報告目錄（可選）

---

## 🧪 Pytest 整合

### 運行校正測試套件
```bash
# 運行所有校正相關測試
pytest tests_refactored/test_calibration_suite.py -v

# 僅運行物理驗證測試
pytest tests_refactored/test_calibration_suite.py -m physics

# 僅運行校正品質測試
pytest tests_refactored/test_calibration_suite.py -m calibration

# 跳過慢速測試
pytest tests_refactored/test_calibration_suite.py -m "not slow"

# 性能基準測試
pytest tests_refactored/test_calibration_suite.py --benchmark-only
```

### 測試標記（Test Markers）
- `physics` - 物理理論驗證測試
- `calibration` - 光譜校正測試
- `regression` - 迴歸測試
- `performance` - 性能測試
- `slow` - 慢速測試

---

## 📊 測試報告範例

### 物理驗證報告
```
================================================================================
  物理理論驗證：Portra400
================================================================================

✓ Energy Conservation (Grayscale Neutrality): White (1,1,1) → (1.0000, 1.0000, 1.0000), deviation=0.0001
✓ Row Normalization (Red Layer): Row sum = 1.0000, deviation from 1.0 = 0.0000
✓ Row Normalization (Green Layer): Row sum = 1.0000, deviation from 1.0 = 0.0000
✓ Row Normalization (Blue Layer): Row sum = 1.0000, deviation from 1.0 = 0.0000
✓ Non-negativity (Red-R): Coefficient = 0.8010
...
✓ Diagonal Dominance: Diagonal/Off-diagonal ratio = 10.23 (target >= 5.0)
✓ Monotonicity (Red Output): Monotonic
✓ Linearity (Grassmann's Laws): Max linearity error = 0.000001
✓ Cross-response Range (Red layer → G input): Cross-response = 0.0790 (max 0.25)

--------------------------------------------------------------------------------
測試總數: 21
通過測試: 21 (100.0%)
錯誤: 0
警告: 0

✓ 所有測試通過！物理理論完全正確。
================================================================================
```

### 校正報告
```
================================================================================
  校正膠片: Portra400
================================================================================

策略: Hybrid (Recommended)
描述: 混合策略：行正規化 + 15% 對角增強

指標                       | 原始         | 校正後       | 改善
--------------------------------------------------------------------------------
灰階偏差                   | 0.0800       | 0.0001       |   99.9%
行不平衡                   | 0.0750       | 0.0000       |  100.0%
對角主導                   | 8.50         | 10.23        |   20.4%

純白輸出:
  原始:   (1.0700, 1.1500, 1.0300)
  校正後: (1.0000, 1.0001, 1.0000)

Status: ✓ PASS - Excellent color neutrality
```

---

## 📈 效能指標

### 單個膠片驗證（M1 Mac）
- 物理驗證：~5ms
- 光譜校正：~2ms
- 視覺化生成：~500ms（含磁碟IO）

### 批次處理（8款彩色膠片）
- 完整驗證：~50ms
- 完整校正：~20ms
- 生成所有視覺化：~4s

---

## 🔧 配置選項

### 物理驗證閾值
```python
# 在 physics_validator.py 中修改
validate_energy_conservation(tolerance=0.002)  # 灰階偏差 < 0.2%
validate_row_normalization(tolerance=0.02)     # 行和偏差 < 2%
validate_diagonal_dominance(min_ratio=5.0)     # 對角/非對角 > 5
```

### 校正策略參數
```python
# 在 comprehensive_calibration_tool.py 中添加新策略
STRATEGIES[6] = CalibrationStrategy(
    name="Custom Strategy",
    description="自訂策略描述",
    normalize_rows=True,
    enhance_diagonal=0.20,
    target_row_sum=1.0
)
```

---

## 📝 常見問題

### Q: 為什麼黑白膠片被跳過？
A: 黑白膠片使用單一 `panchromatic_layer`，沒有 RGB 三層結構，不需要光譜響應校正。

### Q: 如何選擇校正策略？
A: 
- **策略 3（推薦）**：平衡校正效果與膠片風格
- **策略 4（保守）**：更保守，適合追求原汁原味
- **策略 5（激進）**：最大化色彩分離，適合極致色彩準確度

### Q: 校正後需要手動更新 film_models.py 嗎？
A: 是的。工具會生成代碼，需手動複製到 `film_models.py` 中對應位置。

### Q: 視覺化報告需要 X11 環境嗎？
A: 不需要。工具使用 `matplotlib` 的 `Agg` 後端，可在無 GUI 環境運行。

---

## 🎯 驗收標準

### 物理正確性
- ✓ 能量守恆：灰階偏差 < 0.2%
- ✓ 行正規化：行和偏差 < 2%
- ✓ 非負性：所有係數 >= 0
- ✓ 單調性：無逆轉
- ✓ 線性性：誤差 < 5%

### 色彩中性
- ✓ 優秀：灰階偏差 < 0.2%
- ✓ 良好：灰階偏差 < 1.0%
- ⚠ 需改進：灰階偏差 >= 1.0%

### 對角線主導性
- ✓ 優秀：對角/非對角比 > 10
- ✓ 良好：對角/非對角比 > 5
- ⚠ 警告：對角/非對角比 < 5

---

## 📚 物理理論參考

### 能量守恆
- **來源**: Judd, Wright & Pitt (1964) "Color Vision and Colorimetry"
- **原理**: 對於灰階輸入（R=G=B），輸出也應該是灰階（R'=G'=B'）

### 單調性
- **來源**: Hunt (2004) "The Reproduction of Colour"
- **原理**: 增加輸入亮度，輸出亮度也應該增加（Beer-Lambert Law）

### 線性疊加
- **來源**: Grassmann's Laws (1853)
- **原理**: M(aI₁ + bI₂) = aM(I₁) + bM(I₂)

---

## 🛠️ 開發者指南

### 添加新的物理驗證測試
1. 在 `PhysicsValidator` 類中添加新方法 `validate_xxx()`
2. 返回 `ValidationResult` 或 `List[ValidationResult]`
3. 在 `run_all_validations()` 中調用
4. 在 `test_calibration_suite.py` 中添加對應測試

### 添加新的校正策略
1. 在 `STRATEGIES` 字典中添加新策略
2. 在 `ComprehensiveCalibrator.apply_strategy()` 中實現邏輯
3. 運行測試驗證效果

---

## 📦 依賴

**必需**：
- numpy >= 1.20
- film_models (內部模組)

**可選**：
- matplotlib >= 3.0 (視覺化功能)
- pytest >= 7.0 (測試框架)
- pytest-benchmark >= 4.0 (性能測試)

---

## 📄 授權

本工具套件遵循 Phos 專案的 AGPL-3.0 授權條款。
