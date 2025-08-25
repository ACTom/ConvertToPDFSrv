# Office to PDF Converter API

一个基于 FastAPI 的 Office 文档转 PDF 服务，使用 LibreOffice 进行文档转换。

## 功能特性

- ✅ 支持多种 Office 文档格式（DOC, DOCX, XLS, XLSX, PPT, PPTX, ODT, ODS, ODP）
- ✅ 提供同步和异步转换接口
- ✅ 文件下载接口
- ✅ 自动定时清理过期文件
- ✅ 环境变量配置
- ✅ API 密钥认证
- ✅ 自动生成 API 文档
- ✅ 完整的错误处理和日志记录

## 系统要求

- Python 3.8+
- LibreOffice（用于文档转换）

### 安装 LibreOffice

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install libreoffice
```

**CentOS/RHEL:**
```bash
sudo yum install libreoffice
```

**macOS:**
```bash
brew install --cask libreoffice
```

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd ConvertToPDFSrv
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
创建 `.env` 文件或设置环境变量：

```bash
# API 配置
API_KEY=your-secure-api-key-here
PORT=8000
HOST=0.0.0.0

# 文件存储配置
UPLOAD_DIR=uploads
OUTPUT_DIR=outputs

# 清理配置
ENABLE_CLEANUP=true
CLEANUP_INTERVAL_MINUTES=30
FILE_EXPIRE_HOURS=24

# LibreOffice 配置
SOFFICE_PATH=soffice
CONVERSION_TIMEOUT=300

# 日志配置
LOG_LEVEL=INFO
```

### 4. 启动服务
```bash
python main.py
```

或使用 uvicorn：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档
启动服务后，访问以下地址查看自动生成的 API 文档：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API 接口

### 认证
所有 API 接口都需要在请求头中包含 API 密钥：
```
Authorization: Bearer your-api-key-here
```

### 主要接口

#### 1. 同步转换
```http
POST /convert/sync
Content-Type: multipart/form-data
Authorization: Bearer your-api-key-here

file: [Office文档文件]
```

响应：
```json
{
  "success": true,
  "message": "Conversion completed successfully",
  "download_url": "/download/document_uuid.pdf",
  "filename": "document_uuid.pdf"
}
```

#### 2. 异步转换
```http
POST /convert/async
Content-Type: multipart/form-data
Authorization: Bearer your-api-key-here

file: [Office文档文件]
```

响应：
```json
{
  "success": true,
  "message": "Conversion task started",
  "task_id": "uuid-task-id"
}
```

#### 3. 查询任务状态
```http
GET /task/{task_id}
Authorization: Bearer your-api-key-here
```

响应：
```json
{
  "task_id": "uuid-task-id",
  "status": "completed",
  "message": "Conversion completed successfully",
  "download_url": "/download/document_uuid.pdf",
  "filename": "document_uuid.pdf"
}
```

#### 4. 下载文件
```http
GET /download/{filename}
Authorization: Bearer your-api-key-here
```

#### 5. 系统统计
```http
GET /stats
Authorization: Bearer your-api-key-here
```

#### 6. 手动清理
```http
POST /cleanup
Authorization: Bearer your-api-key-here
```

## 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `API_KEY` | `your-api-key-here` | API 访问密钥 |
| `PORT` | `8000` | 服务端口 |
| `HOST` | `0.0.0.0` | 服务主机地址 |
| `UPLOAD_DIR` | `uploads` | 上传文件存储目录 |
| `OUTPUT_DIR` | `outputs` | 转换后文件存储目录 |
| `ENABLE_CLEANUP` | `true` | 是否启用定时清理 |
| `CLEANUP_INTERVAL_MINUTES` | `30` | 清理间隔（分钟） |
| `FILE_EXPIRE_HOURS` | `24` | 文件过期时间（小时） |
| `SOFFICE_PATH` | `soffice` | LibreOffice 可执行文件路径 |
| `CONVERSION_TIMEOUT` | `300` | 转换超时时间（秒） |
| `LOG_LEVEL` | `INFO` | 日志级别 |

### 支持的文件格式

- **Word 文档**: `.doc`, `.docx`
- **Excel 表格**: `.xls`, `.xlsx`
- **PowerPoint 演示文稿**: `.ppt`, `.pptx`
- **OpenDocument**: `.odt`, `.ods`, `.odp`

## 部署

### Docker 部署

项目已包含完整的Docker配置文件：
- `Dockerfile` - Docker镜像构建文件
- `docker-compose.yml` - Docker Compose配置
- `.dockerignore` - Docker构建忽略文件

#### 方式一：使用 Docker Compose（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

#### 方式二：直接使用 Docker

```bash
# 构建镜像
docker build -t office-to-pdf .

# 运行容器
docker run -d \
  --name office-to-pdf-service \
  -p 8000:8000 \
  -e API_KEY=your-secure-api-key-here \
  -v $(pwd)/data/uploads:/app/uploads \
  -v $(pwd)/data/outputs:/app/outputs \
  office-to-pdf

# 查看日志
docker logs -f office-to-pdf-service
```

#### Docker环境变量配置

在 `docker-compose.yml` 中修改环境变量，或创建 `.env` 文件：

```bash
# .env 文件示例
API_KEY=your-secure-api-key-here
PORT=8000
ENABLE_CLEANUP=true
CLEANUP_INTERVAL_MINUTES=30
FILE_EXPIRE_HOURS=24
LOG_LEVEL=INFO
```

### 生产环境部署

使用 Gunicorn 部署：
```bash
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 监控和日志

- 应用日志会输出到控制台
- 可通过 `LOG_LEVEL` 环境变量调整日志级别
- 建议在生产环境中使用日志收集工具（如 ELK Stack）

## 故障排除

### 常见问题

1. **LibreOffice 未找到**
   - 确保已安装 LibreOffice
   - 检查 `SOFFICE_PATH` 环境变量是否正确

2. **转换超时**
   - 增加 `CONVERSION_TIMEOUT` 值
   - 检查系统资源是否充足

3. **文件权限问题**
   - 确保应用有读写 `UPLOAD_DIR` 和 `OUTPUT_DIR` 的权限

4. **API 认证失败**
   - 检查请求头中的 `Authorization` 是否正确
   - 确认 `API_KEY` 环境变量设置正确

## 开发

### 项目结构
```
ConvertToPDFSrv/
├── main.py              # FastAPI 应用主文件
├── config.py            # 配置管理
├── converter.py         # PDF 转换器
├── cleanup.py           # 文件清理服务
├── requirements.txt     # Python 依赖
├── README.md           # 项目文档
├── uploads/            # 上传文件目录
└── outputs/            # 转换后文件目录
```

### 运行测试
```bash
# 安装测试依赖
pip install pytest pytest-asyncio httpx

# 运行测试
pytest
```

## 许可证

MIT License