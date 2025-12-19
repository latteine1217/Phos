"""
Phos Batch Processing Module

批量處理模塊 - 支援多張照片同時處理

Author: @LYCO6273
Version: 0.2.0 (Development)
"""

import io
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
import numpy as np
from PIL import Image

from film_models import FilmProfile


@dataclass
class BatchResult:
    """批量處理結果"""
    filename: str
    success: bool
    image_data: Optional[np.ndarray] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0


class BatchProcessor:
    """批量處理器"""
    
    def __init__(self, max_workers: Optional[int] = None):
        """
        初始化批量處理器
        
        Args:
            max_workers: 最大並行工作數（None = CPU 核心數）
        """
        self.max_workers = max_workers
        
    def process_single_image(
        self,
        image_file,
        film_profile: FilmProfile,
        process_func: Callable,
        settings: dict
    ) -> BatchResult:
        """
        處理單張圖像
        
        Args:
            image_file: 上傳的圖像文件（Streamlit UploadedFile）
            film_profile: 胶片配置
            process_func: 處理函數（來自 phos_core 或主程序）
            settings: 處理設定字典
            
        Returns:
            BatchResult: 處理結果
        """
        import time
        start_time = time.time()
        
        try:
            # 讀取圖像
            image = Image.open(image_file)
            image_array = np.array(image)
            
            # 執行胶片模擬處理
            result_array = process_func(image_array, film_profile, settings)
            
            processing_time = time.time() - start_time
            
            return BatchResult(
                filename=image_file.name,
                success=True,
                image_data=result_array,
                processing_time=processing_time
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            return BatchResult(
                filename=image_file.name,
                success=False,
                error_message=str(e),
                processing_time=processing_time
            )
    
    def process_batch_sequential(
        self,
        image_files: List,
        film_profile: FilmProfile,
        process_func: Callable,
        settings: dict,
        progress_callback: Optional[Callable] = None
    ) -> List[BatchResult]:
        """
        順序處理批量圖像（適合小批量或記憶體受限情況）
        
        Args:
            image_files: 圖像文件列表
            film_profile: 胶片配置
            process_func: 處理函數
            settings: 處理設定
            progress_callback: 進度回調函數 callback(current, total, filename)
            
        Returns:
            List[BatchResult]: 處理結果列表
        """
        results = []
        total = len(image_files)
        
        for idx, image_file in enumerate(image_files, 1):
            if progress_callback:
                progress_callback(idx, total, image_file.name)
            
            result = self.process_single_image(
                image_file, film_profile, process_func, settings
            )
            results.append(result)
        
        return results
    
    def process_batch_parallel(
        self,
        image_files: List,
        film_profile: FilmProfile,
        process_func: Callable,
        settings: dict,
        progress_callback: Optional[Callable] = None
    ) -> List[BatchResult]:
        """
        並行處理批量圖像（適合大批量，更快）
        
        Args:
            image_files: 圖像文件列表
            film_profile: 胶片配置
            process_func: 處理函數
            settings: 處理設定
            progress_callback: 進度回調函數
            
        Returns:
            List[BatchResult]: 處理結果列表
        """
        results = []
        total = len(image_files)
        completed = 0
        
        # 注意：ProcessPoolExecutor 可能在 Streamlit 中有問題
        # 可能需要改用 ThreadPoolExecutor
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任務
            future_to_file = {
                executor.submit(
                    self.process_single_image,
                    image_file,
                    film_profile,
                    process_func,
                    settings
                ): image_file
                for image_file in image_files
            }
            
            # 收集結果
            for future in as_completed(future_to_file):
                completed += 1
                image_file = future_to_file[future]
                
                if progress_callback:
                    progress_callback(completed, total, image_file.name)
                
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # 如果並行處理失敗，創建錯誤結果
                    results.append(BatchResult(
                        filename=image_file.name,
                        success=False,
                        error_message=f"並行處理錯誤: {str(e)}"
                    ))
        
        return results


def create_zip_archive(
    results: List[BatchResult],
    film_name: str,
    output_format: str = "jpg",
    quality: int = 95
) -> bytes:
    """
    創建 ZIP 壓縮檔
    
    Args:
        results: 批量處理結果列表
        film_name: 胶片名稱（用於檔名）
        output_format: 輸出格式 ('jpg', 'png')
        quality: JPEG 質量 (1-100)
        
    Returns:
        bytes: ZIP 檔案的二進制數據
    """
    # 創建記憶體中的 ZIP 檔案
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for result in results:
            if result.success and result.image_data is not None:
                # 生成輸出檔名
                base_name = result.filename.rsplit('.', 1)[0]
                output_filename = f"{base_name}_{film_name}.{output_format}"
                
                # 將 NumPy 陣列轉換為圖像
                image = Image.fromarray(result.image_data.astype(np.uint8))
                
                # 保存到記憶體緩衝區
                img_buffer = io.BytesIO()
                if output_format.lower() == 'jpg':
                    image.save(img_buffer, format='JPEG', quality=quality)
                else:
                    image.save(img_buffer, format='PNG')
                
                # 添加到 ZIP
                zip_file.writestr(output_filename, img_buffer.getvalue())
    
    # 返回 ZIP 二進制數據
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def generate_zip_filename(film_name: str) -> str:
    """
    生成 ZIP 檔案名稱
    
    Args:
        film_name: 胶片名稱
        
    Returns:
        str: ZIP 檔案名稱
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"Phos_Batch_{film_name}_{timestamp}.zip"


def validate_batch_size(num_files: int, max_size: int = 50) -> Tuple[bool, str]:
    """
    驗證批量處理大小
    
    Args:
        num_files: 文件數量
        max_size: 最大允許數量
        
    Returns:
        Tuple[bool, str]: (是否有效, 錯誤訊息)
    """
    if num_files == 0:
        return False, "請至少上傳一張照片"
    
    if num_files > max_size:
        return False, f"批量處理最多支援 {max_size} 張照片，您上傳了 {num_files} 張"
    
    return True, ""


def estimate_processing_time(num_files: int, avg_time_per_image: float = 2.0) -> str:
    """
    預估處理時間
    
    Args:
        num_files: 文件數量
        avg_time_per_image: 每張圖平均處理時間（秒）
        
    Returns:
        str: 時間估計描述
    """
    total_seconds = num_files * avg_time_per_image
    
    if total_seconds < 60:
        return f"約 {int(total_seconds)} 秒"
    elif total_seconds < 3600:
        minutes = int(total_seconds / 60)
        return f"約 {minutes} 分鐘"
    else:
        hours = int(total_seconds / 3600)
        minutes = int((total_seconds % 3600) / 60)
        return f"約 {hours} 小時 {minutes} 分鐘"


# 使用範例（在 Streamlit 應用中）
"""
# 在 Phos_0.2.0.py 中使用

import streamlit as st
from phos_batch import BatchProcessor, create_zip_archive, generate_zip_filename

# 初始化批量處理器
batch_processor = BatchProcessor(max_workers=4)

# 多文件上傳
uploaded_files = st.file_uploader(
    "上傳照片（支援批量）",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files and len(uploaded_files) > 1:
    st.info(f"已上傳 {len(uploaded_files)} 張照片")
    
    if st.button("開始批量處理"):
        # 進度條
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        def update_progress(current, total, filename):
            progress = current / total
            progress_bar.progress(progress)
            status_text.text(f"處理中: {filename} ({current}/{total})")
        
        # 執行批量處理
        results = batch_processor.process_batch_sequential(
            uploaded_files,
            film_profile,
            process_function,
            settings,
            progress_callback=update_progress
        )
        
        # 顯示結果
        success_count = sum(1 for r in results if r.success)
        st.success(f"完成！成功處理 {success_count}/{len(results)} 張照片")
        
        # 創建 ZIP 下載
        if success_count > 0:
            zip_data = create_zip_archive(results, film_profile.name)
            zip_filename = generate_zip_filename(film_profile.name)
            
            st.download_button(
                label="📦 下載全部照片 (ZIP)",
                data=zip_data,
                file_name=zip_filename,
                mime="application/zip"
            )
"""
