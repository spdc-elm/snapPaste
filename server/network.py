"""
网络工具模块 - 获取局域网 IP 地址
"""

import socket


def get_local_ip() -> str:
    """
    获取本机局域网 IP 地址
    
    通过创建 UDP socket 连接外部地址来确定本机使用的网络接口 IP
    这种方法不会真正发送数据，只是让系统选择正确的网络接口
    """
    try:
        # 创建 UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到外部地址（不会真正发送数据）
        s.connect(("8.8.8.8", 80))
        # 获取本机 IP
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # 备用方案：获取主机名对应的 IP
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                raise ValueError("Got loopback address")
            return ip
        except Exception:
            return "127.0.0.1"


def get_server_url(ip: str, port: int) -> str:
    """生成服务器完整 URL"""
    return f"http://{ip}:{port}"


if __name__ == "__main__":
    ip = get_local_ip()
    print(f"Local IP: {ip}")
    print(f"Server URL: {get_server_url(ip, 8080)}")
