# TASK-004: 效能優化設計文檔

**創建時間**: 2025-12-20 02:00  
**負責人**: Main Agent  
**目標**: 將 2000×3000 影像處理時間從 ~2s 降至 < 1s

---

## 📊 效能分析（現況）

### 瓶頸識別

根據效能測試，主要瓶頸為：

#### 1. **大核卷積（最大瓶頸，~60%）**

```
測試結果 (2000×3000 影像):
Kernel  51× 51: filter2D= 122ms, GaussianBlur=  58ms
Kernel 101×101: filter2D= 187ms, GaussianBlur= 161ms
Kernel 201×201: filter2D= 455ms, GaussianBlur= 312ms ← Halation 主要開銷
```

**發現**:
- `filter2D` 在大核（>100px）時非常慢（455ms）
- `GaussianBlur` 對小核優化良好，但大核仍慢（312ms）
- Halation 使用 200px 核 → 單次 ~300ms

**影響範圍**:
- `apply_halation()`: 3 層卷積（Line 1239-1241）→ **~900ms**
- `apply_bloom_with_psf()`: filter2D with dual kernel → ~100ms
- `apply_wavelength_bloom()`: RGB 三通道 → ~300ms

**總計**: 約 1.3s / 2s（65%）

---

#### 2. **重複卷積操作（~20%）**

當前實作在每次處理時重新計算：
- PSF 核生成：`create_dual_kernel_psf()` × 3（RGB）
- 高斯核生成：`cv2.GaussianBlur` 內部每次重算核

**估算開銷**: ~400ms

---

#### 3. **Halation 三層疊加（~15%）**

```python
# Line 1239-1241: 三次 GaussianBlur
halation_layer = (
    cv2.GaussianBlur(energy, (ksize//3, ksize//3), σ_base) * 0.5 +
    cv2.GaussianBlur(energy, (ksize, ksize), σ_base*2) * 0.3 +
    cv2.GaussianBlur(energy, (ksize, ksize), σ_base*4) * 0.2
)
```

**問題**:
- 三次獨立卷積（無法復用中間結果）
- 大核（ksize=200）拖慢整體速度

**估算開銷**: ~300ms

---

### FFT 卷積測試結果

```
FFT vs 直接卷積 (2000×3000):
Kernel  51× 51: 直接=123ms, FFT=256ms, 加速=0.48x ❌
Kernel 101×101: 直接=162ms, FFT=192ms, 加速=0.84x ⚠️
Kernel 201×201: 直接=530ms, FFT=316ms, 加速=1.68x ✅
```

**結論**:
- **小核（<100px）**: FFT 反而慢（setup overhead）
- **大核（>200px）**: FFT 快 1.7x ✅
- **閾值**: 約 150px

---

## 🎯 優化策略

### Phase 1: FFT 卷積加速（核心優化）

**目標**: Halation 從 900ms → 400ms（節省 ~500ms）

#### 實作計畫

1. **自適應卷積函數**:
   ```python
   def convolve_adaptive(image, kernel, method='auto'):
       """
       自適應選擇卷積方法
       
       Args:
           method: 'auto' | 'spatial' | 'fft'
               auto: 根據核大小自動選擇（閾值 150px）
       """
       if method == 'auto':
           ksize = kernel.shape[0]
           if ksize > 150:
               return convolve_fft(image, kernel)
           else:
               return cv2.filter2D(image, -1, kernel)
       elif method == 'fft':
           return convolve_fft(image, kernel)
       else:
           return cv2.filter2D(image, -1, kernel)
   ```

2. **FFT 卷積實作**:
   ```python
   def convolve_fft(image, kernel):
       """
       使用 FFT 進行卷積（針對大核優化）
       
       物理依據: 卷積定理 f⊗g = F⁻¹(F(f)·F(g))
       
       效能:
       - 複雜度: O(N log N) vs O(N·K²)
       - 大核（K>150）快 ~1.7x
       """
       h, w = image.shape[:2]
       kh, kw = kernel.shape[:2]
       
       # 1. 填充影像（reflect mode）
       pad_h, pad_w = kh//2, kw//2
       img_padded = np.pad(image, ((pad_h, pad_h), (pad_w, pad_w)), 
                          mode='reflect')
       
       # 2. 核居中填充
       kernel_padded = np.zeros_like(img_padded)
       kernel_padded[:kh, :kw] = kernel
       kernel_padded = np.roll(kernel_padded, 
                               (-kh//2, -kw//2), axis=(0, 1))
       
       # 3. FFT 卷積
       img_fft = np.fft.rfft2(img_padded)
       kernel_fft = np.fft.rfft2(kernel_padded)
       result_fft = img_fft * kernel_fft
       result = np.fft.irfft2(result_fft)
       
       # 4. 裁剪回原始尺寸
       result = result[pad_h:pad_h+h, pad_w:pad_w+w]
       
       return result.astype(image.dtype)
   ```

3. **整合到 Halation**:
   ```python
   # 修改 Line 1239-1241
   halation_layer = (
       convolve_adaptive(energy, gaussian_kernel(σ_base), 'spatial') * 0.5 +
       convolve_adaptive(energy, gaussian_kernel(σ_base*2), 'fft') * 0.3 +
       convolve_adaptive(energy, gaussian_kernel(σ_base*4), 'fft') * 0.2
   )
   ```

**預期效果**:
- 第一層（小核）: 保持直接卷積（~100ms）
- 第二層（中核）: FFT 卷積（~150ms）
- 第三層（大核）: FFT 卷積（~150ms）
- **總計**: ~400ms（vs 原 900ms，節省 55%）

---

### Phase 2: 卷積核預計算與快取

**目標**: PSF 生成從 ~100ms → < 10ms（節省 ~90ms）

#### 實作計畫

1. **PSF 快取管理**:
   ```python
   from functools import lru_cache
   
   @lru_cache(maxsize=32)
   def get_psf_cached(sigma: float, kappa: float, rho: float, 
                      radius: int) -> np.ndarray:
       """
       快取 PSF 核（避免重複計算）
       
       快取鍵: (sigma, kappa, rho, radius)
       記憶體開銷: ~32 個核 × (200×200×4 bytes) = 5MB
       """
       return create_dual_kernel_psf(sigma, kappa, rho, radius)
   ```

2. **高斯核預計算**:
   ```python
   # 常用高斯核預計算表（app 啟動時生成）
   GAUSSIAN_KERNEL_CACHE = {}
   
   def precompute_gaussian_kernels():
       """預計算常用高斯核"""
       sigmas = [5, 10, 20, 40, 80, 160]  # 常用尺度
       for sigma in sigmas:
           ksize = int(sigma * 6) | 1  # 6σ 涵蓋 99.7%
           kernel = cv2.getGaussianKernel(ksize, sigma)
           kernel = kernel @ kernel.T  # 2D 核
           GAUSSIAN_KERNEL_CACHE[sigma] = kernel
   ```

3. **快速查表**:
   ```python
   def get_gaussian_kernel(sigma: float) -> np.ndarray:
       """獲取高斯核（快取或生成）"""
       # 查找最接近的預計算核
       if sigma in GAUSSIAN_KERNEL_CACHE:
           return GAUSSIAN_KERNEL_CACHE[sigma]
       
       # 未快取則即時生成（並加入快取）
       ksize = int(sigma * 6) | 1
       kernel = cv2.getGaussianKernel(ksize, sigma)
       kernel = kernel @ kernel.T
       GAUSSIAN_KERNEL_CACHE[sigma] = kernel
       return kernel
   ```

**預期效果**:
- PSF 生成: 100ms → 10ms（快取命中）
- 記憶體: +5MB（可接受）

---

### Phase 3: Halation 單層近似（激進優化）

**目標**: 三層卷積 → 單層寬核（節省 ~200ms）

#### 物理近似

三層疊加近似為單層寬高斯：

```
原版: 0.5·G(σ) + 0.3·G(2σ) + 0.2·G(4σ)
近似: 1.0·G(σ_eff)

其中 σ_eff = √(0.5·σ² + 0.3·(2σ)² + 0.2·(4σ)²)
           = σ√(0.5 + 1.2 + 3.2)
           = σ√4.9
           ≈ 2.2σ
```

#### 實作

```python
def apply_halation_fast(lux, halation_params, is_color=True):
    """快速 Halation（單層近似）"""
    # 等效寬度
    sigma_equiv = halation_params.base_sigma * 2.2
    ksize = int(sigma_equiv * 6) | 1
    
    # 單次卷積
    halation_layer = convolve_adaptive(
        halation_energy, 
        get_gaussian_kernel(sigma_equiv),
        method='fft'
    )
    
    return lux - halation_energy + halation_layer
```

**權衡**:
- ✅ 速度: ~300ms → ~100ms（快 3x）
- ❌ 精度: 峰度略有差異（尾巴更平滑）
- 🤔 視覺: 需測試（可能差異極小）

**建議**: 作為可選模式（`halation_mode='fast'`）

---

### Phase 4: 批次處理並行化（可選）

**目標**: N 張影像處理時間接近 1 張（理想 speedup = N）

#### 策略

1. **執行緒池** (適合 I/O 密集):
   ```python
   from concurrent.futures import ThreadPoolExecutor
   
   def process_batch_parallel(images, film, max_workers=4):
       """多執行緒批次處理"""
       with ThreadPoolExecutor(max_workers=max_workers) as executor:
           futures = [executor.submit(process_image, img, film) 
                     for img in images]
           results = [f.result() for f in futures]
       return results
   ```

2. **限制**:
   - Python GIL 限制 CPU 密集運算平行度
   - OpenCV 已內部多執行緒（`cv2.setNumThreads()`）
   - 實際 speedup 約 1.5-2x（非理想 4x）

**建議**: 低優先級（效益有限）

---

## 📈 預期效能改善

| 階段 | 優化內容 | 當前耗時 | 優化後 | 節省 |
|------|---------|---------|--------|------|
| **Phase 1** | FFT 卷積（Halation） | 900ms | 400ms | **500ms** |
| **Phase 2** | PSF 快取 | 100ms | 10ms | **90ms** |
| **Phase 3** | 單層 Halation（可選） | 300ms | 100ms | **200ms** |
| **其他** | Bloom, Grain, HD | 700ms | 600ms | 100ms |
| **總計** | 2000×3000 影像 | **2.0s** | **0.81s** | **59%** |

**目標達成**: ✅ < 1s

---

## 🧪 測試計畫

### 單元測試

1. **FFT 卷積正確性**:
   ```python
   def test_fft_convolution_accuracy():
       """驗證 FFT 卷積與直接卷積等價"""
       img = np.random.rand(1000, 1000).astype(np.float32)
       kernel = cv2.getGaussianKernel(201, 50)
       kernel = kernel @ kernel.T
       
       result_spatial = cv2.filter2D(img, -1, kernel)
       result_fft = convolve_fft(img, kernel)
       
       # 允許浮點誤差
       np.testing.assert_allclose(result_spatial, result_fft, 
                                  rtol=1e-4, atol=1e-6)
   ```

2. **快取效能**:
   ```python
   def test_psf_cache_speedup():
       """驗證快取加速"""
       # 首次調用（未快取）
       t1 = time.perf_counter()
       psf1 = get_psf_cached(20, 30, 0.75, 100)
       time_uncached = time.perf_counter() - t1
       
       # 第二次調用（已快取）
       t2 = time.perf_counter()
       psf2 = get_psf_cached(20, 30, 0.75, 100)
       time_cached = time.perf_counter() - t2
       
       assert time_cached < time_uncached * 0.1  # 快 >10x
   ```

### 整合測試

```python
def test_end_to_end_speedup():
    """端到端效能測試"""
    img = cv2.imread('test_images/test_2000x3000.jpg')
    img = img.astype(np.float32) / 255.0
    
    film = get_film_profile('Portra400_MediumPhysics')
    
    # 測試優化前後
    t_before = benchmark_processing(img, film, optimized=False)
    t_after = benchmark_processing(img, film, optimized=True)
    
    speedup = t_before / t_after
    
    print(f"優化前: {t_before:.3f}s")
    print(f"優化後: {t_after:.3f}s")
    print(f"加速: {speedup:.2f}x")
    
    assert t_after < 1.0  # 目標 <1s
    assert speedup > 1.5  # 至少快 1.5x
```

### 視覺驗證

```python
def test_visual_equivalence():
    """驗證優化不影響視覺品質"""
    img = load_test_image()
    
    result_original = process_image(img, film, optimized=False)
    result_optimized = process_image(img, film, optimized=True)
    
    # PSNR > 40dB 視為無損
    psnr = cv2.PSNR(result_original, result_optimized)
    assert psnr > 40, f"PSNR={psnr:.2f}dB < 40dB"
    
    # SSIM > 0.99 視為視覺等價
    ssim = structural_similarity(result_original, result_optimized)
    assert ssim > 0.99, f"SSIM={ssim:.4f} < 0.99"
```

---

## 🚧 實作順序

### Week 1: 核心加速（P0）

1. ✅ 撰寫設計文檔（本文件）
2. ⏳ 實作 `convolve_fft()`
3. ⏳ 實作 `convolve_adaptive()`
4. ⏳ 整合到 `apply_halation()`
5. ⏳ 測試正確性與效能

### Week 2: 快取優化（P1）

6. ⏳ 實作 PSF 快取（`get_psf_cached()`）
7. ⏳ 實作高斯核預計算
8. ⏳ 整合到 `apply_wavelength_bloom()`
9. ⏳ 測試記憶體占用與命中率

### Week 3: 進階優化（P2，可選）

10. ⏳ 實作單層 Halation 近似
11. ⏳ A/B 測試視覺差異
12. ⏳ 添加 UI 開關（`halation_mode`）

### Week 4: 測試與文檔（P0）

13. ⏳ 完整端到端效能測試
14. ⏳ 視覺等價驗證（PSNR/SSIM）
15. ⏳ 更新文檔與 README
16. ⏳ Git commit + PR

---

## 📝 風險與緩解

### 風險 1: FFT 邊界偽影

**問題**: FFT 卷積假設周期邊界，可能產生邊緣偽影

**緩解**:
- 使用 `reflect` mode 填充（與 `cv2.filter2D` 一致）
- 測試邊緣像素一致性

### 風險 2: 快取記憶體占用

**問題**: 預計算核可能占用大量記憶體

**緩解**:
- 限制快取大小（`@lru_cache(maxsize=32)`）
- 僅快取常用尺寸

### 風險 3: 單層 Halation 視覺差異

**問題**: 近似可能改變尾部形狀

**緩解**:
- 作為可選模式（預設關閉）
- A/B 測試並記錄 PSNR/SSIM

---

## 📚 參考資料

### 理論

1. **卷積定理**: Convolution Theorem (FFT optimization)
   - Bracewell, R. N. (2000). *The Fourier Transform and Its Applications*
   - https://en.wikipedia.org/wiki/Convolution_theorem

2. **高斯核疊加**:
   - σ_total = √(σ₁² + σ₂² + ...)
   - Lindeberg, T. (1993). *Scale-Space Theory in Computer Vision*

### 實作

3. **NumPy FFT**: https://numpy.org/doc/stable/reference/routines.fft.html
4. **OpenCV 效能優化**: https://docs.opencv.org/4.x/dc/d71/tutorial_py_optimization.html
5. **Python LRU Cache**: https://docs.python.org/3/library/functools.html#functools.lru_cache

---

**文檔版本**: v1.0  
**最後更新**: 2025-12-20 02:00  
**狀態**: ✅ 設計完成，待實作
