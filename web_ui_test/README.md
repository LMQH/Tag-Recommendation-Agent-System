# Web UI 测试界面

AI 自动装修助手的前端测试界面，用于测试和演示 API 功能，分析各个接口的使用详情。

## 功能特性

- 💬 流式对话交互
- 📝 会话管理（新建、查看历史会话）
- 🔍 会话搜索
- ⚙️ 接口配置

## 快速开始

### 启动服务（使用本地 HTTP 服务器）

双击运行 `start.bat`，或使用命令行：

```bash
python -m http.server 13100
```

### 访问界面

打开浏览器访问：http://localhost:13100/main.html

### 停止服务

双击运行 `stop.bat`，或在运行 `start.bat` 的终端中按 `Ctrl+C`

## 配置说明

在界面中点击"接口配置"按钮，可以配置：

- API 基础地址
- 认证 Token（如需要）

## 目录结构

```
web_ui_test/
├── main.html          # 主页面
├── assets/            # 静态资源
│   ├── css/          # 样式文件
│   ├── js/           # JavaScript 文件
│   └── lib/          # 第三方库
├── data/              # 推荐数据保存目录（自动创建）
├── start.bat         # 启动脚本
└── stop.bat          # 停止脚本
```

## 推荐数据保存

点击"确认并保存推荐数据"按钮后：

- **现代浏览器（Chrome/Edge）**：会弹出目录选择对话框，请选择 `web_ui_test` 目录，系统会自动创建 `data` 文件夹并保存文件
- **其他浏览器**：文件会下载到浏览器的默认下载目录，请手动将文件移动到 `web_ui_test/data/` 文件夹

保存的文件格式：`recommendation_{session_id}_{timestamp}.json`

## 注意事项

- 需要 Python 3.x 环境
- 默认端口：13100（可在 `start.bat` 中修改）
- 仅用于本地测试，不适用于生产环境
