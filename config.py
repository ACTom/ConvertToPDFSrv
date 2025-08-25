import os
from typing import Optional

class Config:
    """应用配置类，管理所有环境变量"""
    
    # API配置
    API_KEY: str = os.getenv("API_KEY", "your-api-key-here")
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    
    # 文件存储配置
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "outputs")
    
    # 清理配置
    ENABLE_CLEANUP: bool = os.getenv("ENABLE_CLEANUP", "true").lower() == "true"
    CLEANUP_INTERVAL_MINUTES: int = int(os.getenv("CLEANUP_INTERVAL_MINUTES", "30"))
    FILE_EXPIRE_HOURS: int = int(os.getenv("FILE_EXPIRE_HOURS", "1"))  # 文件过期时间
    
    # LibreOffice配置
    SOFFICE_PATH: str = os.getenv("SOFFICE_PATH", "soffice")
    CONVERSION_TIMEOUT: int = int(os.getenv("CONVERSION_TIMEOUT", "300"))  # 转换超时时间(秒)
    
    # 日志配置
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        try:
            # 检查端口范围
            if not (1 <= cls.PORT <= 65535):
                raise ValueError(f"Invalid port: {cls.PORT}")
            
            # 检查清理间隔
            if cls.CLEANUP_INTERVAL_MINUTES <= 0:
                raise ValueError(f"Invalid cleanup interval: {cls.CLEANUP_INTERVAL_MINUTES}")
            
            # 检查文件过期时间
            if cls.FILE_EXPIRE_HOURS <= 0:
                raise ValueError(f"Invalid file expire hours: {cls.FILE_EXPIRE_HOURS}")
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

# 全局配置实例
config = Config()