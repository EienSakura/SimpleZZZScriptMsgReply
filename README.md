# SimpleZZZScriptMsgReply

基于 FastAPI + SQLite 的简易内容收集与按天展示系统。

## 功能说明

- 提供 `POST` 接口接收 JSON 数据并写入 SQLite。
- `image` 字段使用 base64 传图，服务端会解码后缓存到本地目录，并和数据库一样只保留最近 7 天。
- 仅保留最近 7 天的数据（写入和读取时会自动清理旧数据）。
- 提供前端页面按天查看内容，默认展示最新一天。
- 每条内容展示格式为：`title：content`、换行显示图片、分割线后显示下一条。

## 项目结构

- `main.py`：后端入口与 API。
- `requirements.txt`：Python 依赖列表。
- `static/index.html`：前端页面。
- `static/style.css`：前端样式。
- `data.db`：运行后自动生成的 SQLite 数据库文件。

## 环境要求

- Python 3.11+

## 创建与激活虚拟环境

### PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### CMD

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

## 安装依赖

```powershell
pip install -r requirements.txt
```

## 启动后端服务

```powershell
uvicorn main:app --reload
```

启动后访问：

- 前端页面：`http://127.0.0.1:8000/`
- Swagger 文档：`http://127.0.0.1:8000/docs`

## 使用 Docker Compose 部署

在项目根目录执行：

```powershell
docker compose up -d --build
```

查看日志：

```powershell
docker compose logs -f
```

停止并删除容器：

```powershell
docker compose down
```

说明：

- 服务端口映射为 `8000:8000`。
- 当前示例使用宿主机目录 `./.app_data` 持久化数据库和图片缓存。
- 容器内数据库路径由环境变量 `DB_PATH=/data/data.db` 指定。
- 容器内图片缓存路径由环境变量 `IMAGE_CACHE_DIR=/data/image_cache` 指定。

## 接口说明

### 1) 新增内容

- 方法：`POST`
- 路径：`/api/items`
- 请求体（JSON）：

```json
{
  "title": "示例标题",
  "content": "示例内容",
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "timestamp": "2026-03-08T12:00:00+08:00"
}
```

说明：

- `timestamp` 推荐使用 ISO-8601 格式。
- 也兼容 Unix 时间戳（秒或毫秒）。
- 服务只接受最近 7 天内的 `timestamp`。
- `image` 支持 `data:image/png;base64,...` 或纯 base64 字符串。

### 2) 获取可选日期

- 方法：`GET`
- 路径：`/api/days`

### 3) 按天查询内容

- 方法：`GET`
- 路径：`/api/items?day=YYYY-MM-DD`
- `day` 省略时，默认返回最新一天的数据。

## 快速测试（curl）

```bash
curl -X POST "http://127.0.0.1:8000/api/items" \
  -H "Content-Type: application/json" \
  -d "{\"title\":\"测试\",\"content\":\"第一行\\n第二行\",\"image\":\"https://picsum.photos/640/360\",\"timestamp\":\"2026-03-08T10:30:00+08:00\"}"
```

## 数据保留策略

- 系统会在启动、写入、读取时清理数据库中超出最近 7 天的数据。
- 判定依据为 `timestamp` 对应的事件时间。
- 图片缓存目录也会按 7 天策略同步清理。
