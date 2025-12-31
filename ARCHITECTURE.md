# SnapPaste 项目架构文档

## 概述

SnapPaste 是一个轻量级的局域网图片传输工具，实现"手机拍照，电脑粘贴"的核心功能。

### 核心理念

| 原则 | 实现 |
|------|------|
| **快** | 局域网直传，图片不落盘，直接写入剪贴板 |
| **简单** | 扫码即连，无需安装 App，纯 Web 技术 |
| **流畅** | 拍照后可编辑（旋转/裁剪），确认后发送 |

### 技术栈

- **电脑端**: Python 3.8+ (Flask)
- **手机端**: 纯静态 HTML/CSS/JS (PWA)
- **通信**: HTTPS (自签名证书)

---

## 目录结构

```
snapPaste/
├── run.py                 # 入口脚本
├── requirements.txt       # Python 依赖
├── README.md              # 用户文档
├── ARCHITECTURE.md        # 本文档
│
├── server/                # 电脑端服务器
│   ├── __init__.py
│   ├── app.py             # Flask 主应用
│   ├── clipboard.py       # 剪贴板操作（跨平台）
│   └── network.py         # 网络工具（IP 检测）
│
├── static/                # 手机端 PWA
│   ├── index.html         # 主页面
│   ├── style.css          # 样式
│   ├── app.js             # 核心逻辑
│   ├── manifest.json      # PWA 配置
│   └── sw.js              # Service Worker
│
└── certs/                 # SSL 证书（自动生成，gitignore）
    ├── cert.pem
    └── key.pem
```

---

## 架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          手机端 (PWA)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  摄像头预览  │  │  缩放控制   │  │      编辑模式           │  │
│  │  (video)    │  │  (slider)   │  │  旋转 / 裁剪 / 确认     │  │
│  └──────┬──────┘  └─────────────┘  └───────────┬─────────────┘  │
│         │                                       │                │
│         └───────────── 拍照 ────────────────────┘                │
│                          │                                       │
│                    ┌─────▼─────┐                                 │
│                    │  Canvas   │                                 │
│                    │  处理图片  │                                 │
│                    └─────┬─────┘                                 │
│                          │ JPEG Blob                             │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                    HTTPS POST
                    /api/upload
                           │
┌──────────────────────────┼───────────────────────────────────────┐
│                          ▼                                       │
│                   ┌─────────────┐                                │
│                   │  Flask 服务  │                                │
│                   │   (app.py)   │                                │
│                   └──────┬──────┘                                │
│                          │                                       │
│            ┌─────────────┼─────────────┐                        │
│            ▼             ▼             ▼                        │
│     ┌───────────┐ ┌───────────┐ ┌───────────┐                   │
│     │ 静态文件   │ │ 图片接收   │ │ 二维码    │                   │
│     │ 服务      │ │ 端点      │ │ 生成      │                   │
│     └───────────┘ └─────┬─────┘ └───────────┘                   │
│                         │                                        │
│                   ┌─────▼─────┐                                  │
│                   │ clipboard │                                  │
│                   │   .py     │                                  │
│                   └─────┬─────┘                                  │
│                         │                                        │
│      ┌──────────────────┼──────────────────┐                    │
│      ▼                  ▼                  ▼                    │
│ ┌─────────┐      ┌─────────────┐     ┌──────────┐               │
│ │ Windows │      │    Linux    │     │  macOS   │               │
│ │win32clip│      │   xclip     │     │ PyObjC   │               │
│ └─────────┘      └─────────────┘     └──────────┘               │
│                                                                  │
│                    电脑端 (Python)                                │
└──────────────────────────────────────────────────────────────────┘
```

---

## 模块详解

### 1. server/app.py - Flask 主应用

**职责**:
- 提供静态文件服务（手机端 PWA）
- 接收图片上传 (`POST /api/upload`)
- 生成并显示二维码
- 管理 HTTPS 证书

**主要路由**:

| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 返回手机端页面 |
| `/<path>` | GET | 静态文件服务 |
| `/api/upload` | POST | 接收图片，写入剪贴板 |
| `/api/ping` | GET | 健康检查 |

**命令行参数**:
```bash
python run.py [--no-https] [--port PORT]
```

### 2. server/clipboard.py - 剪贴板模块

**职责**: 跨平台将图片数据直接写入系统剪贴板（不落盘）

**平台支持**:

| 平台 | 实现方式 |
|------|----------|
| Windows | `win32clipboard` (DIB 格式) 或 PowerShell |
| Linux | `xclip` / `xsel` |
| macOS | `PyObjC` (NSPasteboard) |

**关键函数**:
```python
def image_to_clipboard(image_data: bytes) -> bool
def decode_base64_image(data: str) -> bytes
```

### 3. server/network.py - 网络工具

**职责**: 检测本机局域网 IP，智能选择最佳地址

**IP 选择优先级**:
1. WLAN/Wi-Fi 接口（手机最可能连接的网络）
2. 有默认网关的接口
3. 非虚拟网卡（排除 VMware、Docker 等）
4. 第一个可用地址

**关键函数**:
```python
def get_all_local_ips() -> list[dict]  # 获取所有 IP
def get_local_ip() -> str               # 获取最佳 IP
```

### 4. static/app.js - 手机端核心逻辑

**职责**: 摄像头控制、拍照、编辑、上传

**主要功能模块**:

```
┌─────────────────────────────────────────────┐
│                  app.js                     │
├─────────────────────────────────────────────┤
│  摄像头初始化                                │
│  ├── initCamera()                           │
│  └── initZoomControl()                      │
├─────────────────────────────────────────────┤
│  拍照                                        │
│  └── capturePhoto()                         │
├─────────────────────────────────────────────┤
│  编辑模式                                    │
│  ├── enterEditMode() / exitEditMode()       │
│  ├── rotateImage()                          │
│  ├── toggleCropMode()                       │
│  └── 裁剪框拖动 (startCropDrag/onCropDrag)  │
├─────────────────────────────────────────────┤
│  上传                                        │
│  ├── sendEditedImage()                      │
│  └── uploadImage()                          │
└─────────────────────────────────────────────┘
```

---

## 数据流

### 拍照 → 粘贴 完整流程

```
1. [手机] 用户点击拍照按钮
      │
2. [手机] video 帧 → canvas → JPEG dataURL
      │
3. [手机] 进入编辑模式（可选旋转/裁剪）
      │
4. [手机] 用户点击确认
      │
5. [手机] canvas → JPEG Blob
      │
6. [手机] fetch POST /api/upload (multipart/form-data)
      │
7. [电脑] Flask 接收 → 读取 bytes
      │
8. [电脑] clipboard.image_to_clipboard(bytes)
      │
9. [电脑] 图片进入系统剪贴板
      │
10. [电脑] 用户 Ctrl+V 粘贴
```

### 图片格式转换

```
手机端:
  video frame → canvas → JPEG (quality=0.85)

电脑端 (Windows):
  JPEG bytes → PIL.Image → BMP (DIB) → win32clipboard
```

---

## 安全设计

### 为什么需要 HTTPS？

浏览器安全策略限制：`getUserMedia()` (摄像头 API) 只能在"安全上下文"中使用：
- `https://` 任意地址 ✓
- `http://localhost` ✓
- `http://192.168.x.x` ✗ (局域网 IP 被拒绝)

### 自签名证书

- 首次运行自动生成（使用 `cryptography` 库）
- 证书包含局域网 IP 的 SAN (Subject Alternative Name)
- 有效期 365 天
- 存储在 `certs/` 目录（已 gitignore）

### 首次使用

用户需要在手机浏览器中手动信任证书：
1. 访问 `https://<IP>:8443`
2. 浏览器警告"不安全"
3. 点击"高级" → "继续访问"
4. 后续访问不再提示

---

## 扩展点

### 潜在功能扩展

| 功能 | 实现思路 |
|------|----------|
| 多图批量传输 | 队列 + 进度显示 |
| 历史记录 | localStorage 存储最近传输 |
| 双向传输 | 电脑端截图 → 手机下载 |
| 文字 OCR | 集成 Tesseract.js |
| 局域网发现 | mDNS/Bonjour 自动发现 |

### 代码扩展点

1. **新增剪贴板平台**: 在 `clipboard.py` 添加 `_xxx_clipboard()` 函数
2. **新增编辑工具**: 在 `app.js` 添加工具函数，更新 `edit-toolbar`
3. **修改 IP 检测**: 调整 `network.py` 的优先级逻辑

---

## 依赖说明

### Python 依赖 (requirements.txt)

| 包 | 用途 |
|----|------|
| flask | Web 服务器 |
| qrcode | 二维码生成 |
| Pillow | 图片处理（格式转换） |
| cryptography | HTTPS 证书生成 |
| pywin32 | Windows 剪贴板（仅 Windows） |

### 浏览器 API

| API | 用途 |
|-----|------|
| `navigator.mediaDevices.getUserMedia()` | 摄像头访问 |
| `MediaStreamTrack.applyConstraints()` | 缩放控制 |
| `canvas.toBlob()` | 图片编码 |
| `fetch()` | HTTP 上传 |
| `navigator.vibrate()` | 触觉反馈 |

---

## 开发指南

### 本地开发

```bash
# 创建虚拟环境
conda create -n snappaste python=3.11
conda activate snappaste

# 安装依赖
pip install -r requirements.txt

# 启动服务器
python run.py

# HTTP 模式（调试用）
python run.py --no-https --port 8080
```

### 调试技巧

1. **查看所有 IP**: 运行 `python -c "from server.network import print_all_ips; print_all_ips()"`
2. **测试剪贴板**: 运行 `python server/clipboard.py`
3. **手机端调试**: Chrome DevTools 远程调试

---

## 版本历史

| 版本 | 功能 |
|------|------|
| v0.1 | MVP: 拍照 → 剪贴板 |
| v0.2 | HTTPS 支持，解决摄像头权限问题 |
| v0.3 | 缩放控制，拍照后编辑（旋转/裁剪） |
