import os
import subprocess
import tempfile
import uuid
import asyncio
from pathlib import Path
from typing import Optional, Tuple
import logging
from config import config

logger = logging.getLogger(__name__)

class PDFConverter:
    """PDF转换器，使用LibreOffice进行文件转换"""
    
    def __init__(self):
        self.upload_dir = Path(config.UPLOAD_DIR)
        self.output_dir = Path(config.OUTPUT_DIR)
        
        # 确保目录存在
        self.upload_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
    
    def _generate_unique_filename(self, original_filename: str, extension: str = ".pdf") -> str:
        """生成唯一的文件名"""
        unique_id = str(uuid.uuid4())
        name_without_ext = Path(original_filename).stem
        return f"{name_without_ext}_{unique_id}{extension}"
    
    def _run_soffice_command(self, input_file: Path, output_dir: Path) -> Tuple[bool, str]:
        """执行soffice转换命令"""
        try:
            cmd = [
                config.SOFFICE_PATH,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(output_dir),
                str(input_file)
            ]
            
            logger.info(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.CONVERSION_TIMEOUT
            )
            
            if result.returncode == 0:
                logger.info(f"Conversion successful for {input_file.name}")
                return True, "Conversion successful"
            else:
                error_msg = f"Conversion failed: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = f"Conversion timeout after {config.CONVERSION_TIMEOUT} seconds"
            logger.error(error_msg)
            return False, error_msg
        except FileNotFoundError:
            error_msg = f"LibreOffice not found at {config.SOFFICE_PATH}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error during conversion: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def convert_to_pdf(self, file_content: bytes, filename: str) -> Tuple[bool, str, Optional[str]]:
        """同步转换文件为PDF
        
        Args:
            file_content: 文件内容
            filename: 原始文件名
            
        Returns:
            Tuple[success, message, output_filename]
        """
        try:
            # 保存上传的文件
            unique_input_name = self._generate_unique_filename(filename, Path(filename).suffix)
            input_file = self.upload_dir / unique_input_name
            
            with open(input_file, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Saved input file: {input_file}")
            
            # 执行转换
            success, message = self._run_soffice_command(input_file, self.output_dir)
            
            if success:
                # 查找生成的PDF文件
                expected_pdf_name = Path(unique_input_name).stem + ".pdf"
                output_file = self.output_dir / expected_pdf_name
                
                if output_file.exists():
                    return True, "Conversion completed successfully", expected_pdf_name
                else:
                    return False, "PDF file not found after conversion", None
            else:
                return False, message, None
                
        except Exception as e:
            error_msg = f"Error during conversion: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    async def convert_to_pdf_async(self, file_content: bytes, filename: str) -> Tuple[bool, str, Optional[str]]:
        """异步转换文件为PDF
        
        Args:
            file_content: 文件内容
            filename: 原始文件名
            
        Returns:
            Tuple[success, message, output_filename]
        """
        try:
            # 保存上传的文件
            unique_input_name = self._generate_unique_filename(filename, Path(filename).suffix)
            input_file = self.upload_dir / unique_input_name
            
            with open(input_file, 'wb') as f:
                f.write(file_content)
            
            logger.info(f"Saved input file: {input_file}")
            
            # 异步执行转换命令
            cmd = [
                config.SOFFICE_PATH,
                "--headless",
                "--convert-to", "pdf",
                "--outdir", str(self.output_dir),
                str(input_file)
            ]
            
            logger.info(f"Running async command: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=config.CONVERSION_TIMEOUT
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return False, f"Conversion timeout after {config.CONVERSION_TIMEOUT} seconds", None
            
            if process.returncode == 0:
                # 查找生成的PDF文件
                expected_pdf_name = Path(unique_input_name).stem + ".pdf"
                output_file = self.output_dir / expected_pdf_name
                
                if output_file.exists():
                    logger.info(f"Async conversion successful for {filename}")
                    return True, "Conversion completed successfully", expected_pdf_name
                else:
                    return False, "PDF file not found after conversion", None
            else:
                error_msg = f"Async conversion failed: {stderr.decode()}"
                logger.error(error_msg)
                return False, error_msg, None
                
        except Exception as e:
            error_msg = f"Error during async conversion: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def get_file_path(self, filename: str, file_type: str = "output") -> Optional[Path]:
        """获取文件路径
        
        Args:
            filename: 文件名
            file_type: 文件类型 ('upload' 或 'output')
            
        Returns:
            文件路径或None
        """
        if file_type == "upload":
            file_path = self.upload_dir / filename
        else:
            file_path = self.output_dir / filename
        
        return file_path if file_path.exists() else None
    
    def delete_file(self, filename: str, file_type: str = "output") -> bool:
        """删除文件
        
        Args:
            filename: 文件名
            file_type: 文件类型 ('upload' 或 'output')
            
        Returns:
            是否删除成功
        """
        try:
            file_path = self.get_file_path(filename, file_type)
            if file_path:
                file_path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {str(e)}")
            return False

# 全局转换器实例
converter = PDFConverter()