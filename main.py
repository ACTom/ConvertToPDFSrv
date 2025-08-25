import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from config import config
from converter import converter
from cleanup import cleanup_service

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="Office to PDF Converter API",
    description="一个将Office文档转换为PDF的API服务，支持同步和异步转换",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API密钥验证
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """验证API密钥"""
    if credentials.credentials != config.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return credentials.credentials

# 响应模型
class ConversionResponse(BaseModel):
    """转换响应模型"""
    success: bool
    message: str
    task_id: Optional[str] = None
    download_url: Optional[str] = None
    filename: Optional[str] = None

class TaskStatusResponse(BaseModel):
    """任务状态响应模型"""
    task_id: str
    status: str  # 'processing', 'completed', 'failed'
    message: str
    download_url: Optional[str] = None
    filename: Optional[str] = None

class CleanupStatsResponse(BaseModel):
    """清理统计响应模型"""
    upload_dir: dict
    output_dir: dict
    cleanup_enabled: bool
    cleanup_interval_minutes: int
    file_expire_hours: int
    service_running: bool

# 存储异步任务状态
async_tasks = {}

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Starting Office to PDF Converter API")
    
    # 验证配置
    if not config.validate():
        logger.error("Configuration validation failed")
        raise RuntimeError("Invalid configuration")
    
    # 启动清理服务
    await cleanup_service.start_cleanup_service()
    
    logger.info(f"API server starting on {config.HOST}:{config.PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Shutting down Office to PDF Converter API")
    
    # 停止清理服务
    await cleanup_service.stop_cleanup_service()

@app.get("/", summary="健康检查")
async def root():
    """API健康检查端点"""
    return {
        "message": "Office to PDF Converter API is running",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/convert/sync", response_model=ConversionResponse, summary="同步转换文档")
async def convert_sync(
    file: UploadFile = File(..., description="要转换的Office文档"),
    api_key: str = Depends(verify_api_key)
):
    """同步转换Office文档为PDF
    
    - **file**: 上传的Office文档文件
    - 返回转换结果和下载链接
    """
    try:
        # 检查文件类型
        allowed_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(allowed_extensions)}"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # 执行转换
        success, message, output_filename = converter.convert_to_pdf(file_content, file.filename)
        
        if success:
            download_url = f"/download/{output_filename}"
            return ConversionResponse(
                success=True,
                message=message,
                download_url=download_url,
                filename=output_filename
            )
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in sync conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/convert/async", response_model=ConversionResponse, summary="异步转换文档")
async def convert_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="要转换的Office文档"),
    api_key: str = Depends(verify_api_key)
):
    """异步转换Office文档为PDF
    
    - **file**: 上传的Office文档文件
    - 返回任务ID，可通过任务状态接口查询进度
    """
    try:
        # 检查文件类型
        allowed_extensions = ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.odt', '.ods', '.odp']
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file_ext}. Supported types: {', '.join(allowed_extensions)}"
            )
        
        # 读取文件内容
        file_content = await file.read()
        
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        # 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 初始化任务状态
        async_tasks[task_id] = {
            "status": "processing",
            "message": "Conversion in progress",
            "filename": None,
            "created_at": datetime.now()
        }
        
        # 添加后台任务
        background_tasks.add_task(process_async_conversion, task_id, file_content, file.filename)
        
        return ConversionResponse(
            success=True,
            message="Conversion task started",
            task_id=task_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in async conversion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

async def process_async_conversion(task_id: str, file_content: bytes, filename: str):
    """处理异步转换任务"""
    try:
        success, message, output_filename = await converter.convert_to_pdf_async(file_content, filename)
        
        if success:
            async_tasks[task_id] = {
                "status": "completed",
                "message": message,
                "filename": output_filename,
                "created_at": async_tasks[task_id]["created_at"]
            }
        else:
            async_tasks[task_id] = {
                "status": "failed",
                "message": message,
                "filename": None,
                "created_at": async_tasks[task_id]["created_at"]
            }
            
    except Exception as e:
        logger.error(f"Error in async conversion task {task_id}: {str(e)}")
        async_tasks[task_id] = {
            "status": "failed",
            "message": f"Conversion failed: {str(e)}",
            "filename": None,
            "created_at": async_tasks[task_id]["created_at"]
        }

@app.get("/task/{task_id}", response_model=TaskStatusResponse, summary="查询任务状态")
async def get_task_status(
    task_id: str,
    api_key: str = Depends(verify_api_key)
):
    """查询异步转换任务状态
    
    - **task_id**: 任务ID
    - 返回任务状态和结果
    """
    if task_id not in async_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = async_tasks[task_id]
    download_url = None
    
    if task["status"] == "completed" and task["filename"]:
        download_url = f"/download/{task['filename']}"
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        message=task["message"],
        download_url=download_url,
        filename=task["filename"]
    )

@app.get("/download/{filename}", summary="下载转换后的PDF文件")
async def download_file(
    filename: str,
    api_key: str = Depends(verify_api_key)
):
    """下载转换后的PDF文件
    
    - **filename**: 文件名
    - 返回PDF文件
    """
    file_path = converter.get_file_path(filename, "output")
    
    if not file_path:
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )

@app.get("/stats", response_model=CleanupStatsResponse, summary="获取系统统计信息")
async def get_stats(
    api_key: str = Depends(verify_api_key)
):
    """获取系统统计信息
    
    - 返回文件目录统计和清理服务状态
    """
    stats = cleanup_service.get_directory_stats()
    return CleanupStatsResponse(**stats)

@app.post("/cleanup", summary="手动执行文件清理")
async def manual_cleanup(
    api_key: str = Depends(verify_api_key)
):
    """手动执行文件清理
    
    - 立即清理过期文件
    - 返回清理结果
    """
    try:
        result = cleanup_service.cleanup_expired_files()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in manual cleanup: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=False,
        log_level=config.LOG_LEVEL.lower()
    )