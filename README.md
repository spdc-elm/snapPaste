# SnapPaste

手机拍照，电脑粘贴 - 局域网直传，亚秒级延迟

## 特性

- **快** - 局域网直传，图片不落盘，直接进剪贴板
- **简单** - 扫码即连，无需安装 App
- **流畅** - 拍完即传，无需二次确认

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务器
python run.py
```

启动后终端会显示二维码，手机扫码即可使用。

## 使用方法

1. 电脑运行 `python run.py`
2. 手机扫描终端显示的二维码
3. 点击拍照按钮
4. 图片自动发送到电脑剪贴板
5. 在电脑上 Ctrl+V 粘贴

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
- pywin32 - Windows 剪贴板（仅 Windows）

## 架构

```
手机 (PWA) ──HTTP POST──> 电脑 (Flask) ──> 系统剪贴板
```

## License

MIT
