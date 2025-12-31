#!/usr/bin/env python3
"""
SnapPaste 电脑端服务器
手机拍照，电脑粘贴 - 局域网直传，亚秒级延迟
"""

import os
import sys

# 添加 server 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
import qrcode
from io import StringIO

from network import get_local_ip, get_server_url
from clipboard import image_to_clipboard, decode_base64_image


# 配置
PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")

# 创建 Flask 应用
app = Flask(__name__, static_folder=STATIC_DIR)


# ============ 路由 ============

@app.route("/")
def index():
    """提供手机端 HTML 页面"""
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    """提供静态文件"""
    return send_from_directory(STATIC_DIR, filename)


@app.route("/api/upload", methods=["POST"])
def upload():
    """
    接收图片并写入剪贴板
    
    支持两种格式：
    1. JSON: {"image": "base64_data"} 或 {"image": "data:image/png;base64,xxx"}
    2. Binary: 直接 POST 图片二进制数据
    """
    try:
        # 获取图片数据
        if request.is_json:
            # JSON 格式（Base64）
            data = request.get_json()
            if not data or "image" not in data:
                return jsonify({"success": False, "error": "Missing 'image' field"}), 400
            
            image_data = decode_base64_image(data["image"])
        
        elif request.content_type and request.content_type.startswith("image/"):
            # 直接二进制图片
            image_data = request.get_data()
        
        elif request.files and "image" in request.files:
            # multipart/form-data 文件上传
            file = request.files["image"]
            image_data = file.read()
        
        else:
            # 尝试作为原始数据处理
            image_data = request.get_data()
            if not image_data:
                return jsonify({
                    "success": False, 
                    "error": "No image data received"
                }), 400
        
        # 验证图片数据
        if len(image_data) < 100:
            return jsonify({
                "success": False, 
                "error": "Image data too small"
            }), 400
        
        # 直接写入剪贴板（不落盘）
        success = image_to_clipboard(image_data)
        
        if success:
            return jsonify({
                "success": True, 
                "message": "Image copied to clipboard",
                "size": len(image_data)
            })
        else:
            return jsonify({
                "success": False, 
                "error": "Failed to copy to clipboard"
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500


@app.route("/api/ping")
def ping():
    """健康检查端点"""
    return jsonify({"status": "ok", "service": "SnapPaste"})


# ============ 启动逻辑 ============

def print_qrcode(url: str):
    """在终端打印二维码"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=1,
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # 使用 ASCII 字符打印
    qr_str = StringIO()
    qr.print_ascii(out=qr_str, invert=True)
    print(qr_str.getvalue())


def print_banner(url: str):
    """打印启动信息"""
    print("\n" + "=" * 50)
    print("  SnapPaste - 手机拍照，电脑粘贴")
    print("=" * 50)
    print(f"\n  服务器地址: {url}")
    print("\n  用手机扫描下方二维码连接:\n")
    print_qrcode(url)
    print(f"\n  或在手机浏览器打开: {url}")
    print("\n  按 Ctrl+C 停止服务器")
    print("=" * 50 + "\n")


def main():
    """主函数"""
    # 获取局域网 IP
    ip = get_local_ip()
    url = get_server_url(ip, PORT)
    
    # 确保静态目录存在
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)
        print(f"[INFO] Created static directory: {STATIC_DIR}")
    
    # 打印启动信息和二维码
    print_banner(url)
    
    # 启动服务器
    app.run(
        host="0.0.0.0",  # 监听所有网络接口
        port=PORT,
        debug=False,
        threaded=True
    )


if __name__ == "__main__":
    main()
