import os
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from config import config

logger = logging.getLogger(__name__)

class FileCleanup:
    """文件清理服务，定时清理过期文件"""
    
    def __init__(self):
        self.upload_dir = Path(config.UPLOAD_DIR)
        self.output_dir = Path(config.OUTPUT_DIR)
        self.cleanup_task = None
        self.is_running = False
    
    def _is_file_expired(self, file_path: Path) -> bool:
        """检查文件是否过期
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否过期
        """
        try:
            # 获取文件的修改时间
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            expire_time = datetime.now() - timedelta(hours=config.FILE_EXPIRE_HOURS)
            
            return file_mtime < expire_time
        except Exception as e:
            logger.error(f"Error checking file expiry for {file_path}: {str(e)}")
            return False
    
    def _cleanup_directory(self, directory: Path) -> List[str]:
        """清理指定目录中的过期文件
        
        Args:
            directory: 目录路径
            
        Returns:
            被删除的文件列表
        """
        deleted_files = []
        
        if not directory.exists():
            return deleted_files
        
        try:
            for file_path in directory.iterdir():
                if file_path.is_file() and self._is_file_expired(file_path):
                    try:
                        file_path.unlink()
                        deleted_files.append(str(file_path))
                        logger.info(f"Deleted expired file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error deleting file {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {str(e)}")
        
        return deleted_files
    
    def cleanup_expired_files(self) -> dict:
        """清理所有过期文件
        
        Returns:
            清理结果统计
        """
        logger.info("Starting file cleanup process")
        
        # 清理上传目录
        deleted_uploads = self._cleanup_directory(self.upload_dir)
        
        # 清理输出目录
        deleted_outputs = self._cleanup_directory(self.output_dir)
        
        result = {
            "timestamp": datetime.now().isoformat(),
            "deleted_uploads": len(deleted_uploads),
            "deleted_outputs": len(deleted_outputs),
            "total_deleted": len(deleted_uploads) + len(deleted_outputs),
            "upload_files": deleted_uploads,
            "output_files": deleted_outputs
        }
        
        logger.info(f"Cleanup completed. Deleted {result['total_deleted']} files")
        return result
    
    async def _cleanup_loop(self):
        """定时清理循环"""
        while self.is_running:
            try:
                if config.ENABLE_CLEANUP:
                    self.cleanup_expired_files()
                
                # 等待下一次清理
                await asyncio.sleep(config.CLEANUP_INTERVAL_MINUTES * 60)
            except asyncio.CancelledError:
                logger.info("Cleanup loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {str(e)}")
                # 出错后等待一段时间再继续
                await asyncio.sleep(60)
    
    async def start_cleanup_service(self):
        """启动清理服务"""
        if not config.ENABLE_CLEANUP:
            logger.info("File cleanup is disabled")
            return
        
        if self.is_running:
            logger.warning("Cleanup service is already running")
            return
        
        self.is_running = True
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info(f"File cleanup service started. Interval: {config.CLEANUP_INTERVAL_MINUTES} minutes")
    
    async def stop_cleanup_service(self):
        """停止清理服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("File cleanup service stopped")
    
    def get_directory_stats(self) -> dict:
        """获取目录统计信息
        
        Returns:
            目录统计信息
        """
        def get_dir_info(directory: Path) -> dict:
            if not directory.exists():
                return {"exists": False, "file_count": 0, "total_size": 0}
            
            file_count = 0
            total_size = 0
            
            try:
                for file_path in directory.iterdir():
                    if file_path.is_file():
                        file_count += 1
                        total_size += file_path.stat().st_size
            except Exception as e:
                logger.error(f"Error getting directory stats for {directory}: {str(e)}")
            
            return {
                "exists": True,
                "file_count": file_count,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }
        
        return {
            "upload_dir": get_dir_info(self.upload_dir),
            "output_dir": get_dir_info(self.output_dir),
            "cleanup_enabled": config.ENABLE_CLEANUP,
            "cleanup_interval_minutes": config.CLEANUP_INTERVAL_MINUTES,
            "file_expire_hours": config.FILE_EXPIRE_HOURS,
            "service_running": self.is_running
        }

# 全局清理服务实例
cleanup_service = FileCleanup()