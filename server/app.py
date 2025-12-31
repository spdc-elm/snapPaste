#!/usr/bin/env python3
"""
SnapPaste 电脑端服务器
手机拍照，电脑粘贴 - 局域网直传，亚秒级延迟
"""

import os
import sys
import ssl
import ipaddress

# 添加 server 目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, send_from_directory
import qrcode
from io import StringIO

from network import get_local_ip, get_server_url
from clipboard import image_to_clipboard, decode_base64_image


# 配置
PORT = 8443  # HTTPS 默认用 8443
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
CERT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "certs")

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


def print_banner(url: str, is_https: bool = False):
    """打印启动信息"""
    print("\n" + "=" * 50)
    print("  SnapPaste - 手机拍照，电脑粘贴")
    print("=" * 50)
    print(f"\n  服务器地址: {url}")
    if is_https:
        print("\n  [HTTPS 模式] 首次访问需信任证书")
    print("\n  用手机扫描下方二维码连接:\n")
    print_qrcode(url)
    print(f"\n  或在手机浏览器打开: {url}")
    print("\n  按 Ctrl+C 停止服务器")
    print("=" * 50 + "\n")


def generate_self_signed_cert():
    """生成自签名证书（如果不存在）"""
    cert_file = os.path.join(CERT_DIR, "cert.pem")
    key_file = os.path.join(CERT_DIR, "key.pem")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file
    
    # 创建证书目录
    os.makedirs(CERT_DIR, exist_ok=True)
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from datetime import datetime, timedelta
        
        # 生成私钥
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        
        # 获取本机 IP
        ip = get_local_ip()
        
        # 生成证书
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, f"SnapPaste ({ip})"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SnapPaste"),
        ])
        
        # 添加 SAN（Subject Alternative Name）以支持 IP 访问
        san = x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address(ip)),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ])
        
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=365))
            .add_extension(san, critical=False)
            .sign(key, hashes.SHA256())
        )
        
        # 保存私钥
        with open(key_file, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        # 保存证书
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        print(f"[INFO] 已生成自签名证书: {cert_file}")
        return cert_file, key_file
        
    except ImportError:
        print("[WARN] 未安装 cryptography，无法生成证书")
        print("[WARN] 请运行: pip install cryptography")
        return None, None


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SnapPaste 服务器")
    parser.add_argument("--no-https", action="store_true", help="使用 HTTP 模式（不推荐）")
    parser.add_argument("--port", type=int, default=None, help="端口号")
    args = parser.parse_args()
    
    # 获取局域网 IP
    ip = get_local_ip()
    
    # 确保静态目录存在
    if not os.path.exists(STATIC_DIR):
        os.makedirs(STATIC_DIR)
        print(f"[INFO] Created static directory: {STATIC_DIR}")
    
    use_https = not args.no_https
    port = args.port or (8443 if use_https else 8080)
    
    if use_https:
        # 尝试生成/加载证书
        cert_file, key_file = generate_self_signed_cert()
        
        if cert_file and key_file:
            url = f"https://{ip}:{port}"
            print_banner(url, is_https=True)
            
            # 创建 SSL 上下文
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert_file, key_file)
            
            # 启动 HTTPS 服务器
            app.run(
                host="0.0.0.0",
                port=port,
                debug=False,
                threaded=True,
                ssl_context=context
            )
        else:
            print("[WARN] 证书不可用，回退到 HTTP 模式")
            use_https = False
    
    if not use_https:
        url = f"http://{ip}:{port}"
        print_banner(url, is_https=False)
        print("\n  [警告] HTTP 模式下，手机浏览器可能无法调用摄像头")
        print("  [提示] 可使用文件选择器作为备选方案\n")
        
        app.run(
            host="0.0.0.0",
            port=port,
            debug=False,
            threaded=True
        )


if __name__ == "__main__":
    main()
