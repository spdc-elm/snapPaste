# SnapPaste

手机拍照，电脑粘贴 - 局域网直传，亚秒级延迟

## 特性

- **快** - 局域网直传，图片不落盘，直接进剪贴板
- **简单** - 扫码即连，无需安装 App
- **流畅** - 拍完即传，无需二次确认
- **安全** - HTTPS 加密，自动生成证书

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器（HTTPS 模式，推荐）
python run.py

# 或使用 HTTP 模式（摄像头可能不可用）
python run.py --no-https
```

启动后终端会显示二维码，手机扫码即可使用。

## 使用方法

1. 电脑运行 `python run.py`
2. 手机扫描终端显示的二维码
3. **首次访问**：浏览器会提示证书不安全，点击"高级" → "继续访问"
4. 允许摄像头权限
5. 点击拍照按钮
6. 图片自动发送到电脑剪贴板
7. 在电脑上 Ctrl+V 粘贴

## 为什么需要 HTTPS？

浏览器安全策略要求：`getUserMedia`（摄像头 API）只能在以下环境使用：
- `https://` 任意地址
- `http://localhost`

局域网 IP（如 `http://192.168.x.x`）会被拒绝访问摄像头。

本工具会自动生成自签名证书启用 HTTPS，首次访问时信任证书即可。

## 命令行参数

```bash
python run.py [选项]

选项：
  --no-https    使用 HTTP 模式（不推荐，摄像头可能不可用）
  --port PORT   指定端口号（HTTPS 默认 8443，HTTP 默认 8080）
```

## 系统要求

**电脑端：**
- Python 3.8+
- Windows / Linux / macOS

**手机端：**
- 任意现代浏览器（Chrome、Safari、Firefox 等）
- 需与电脑在同一局域网

## 依赖

- Flask - Web 服务器
- qrcode - 二维码生成
- Pillow - 图片处理
- cryptography - HTTPS 证书生成
- pywin32 - Windows 剪贴板（仅 Windows）

## 架构

```
手机 (PWA) ──HTTPS POST──> 电脑 (Flask) ──> 系统剪贴板
```

## License

MIT
