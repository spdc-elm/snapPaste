"""
网络工具模块 - 获取局域网 IP 地址
"""

import socket
import subprocess
import platform
import re


def get_all_local_ips() -> list:
    """
    获取本机所有局域网 IP 地址
    
    Returns:
        list of dict: [{"ip": "x.x.x.x", "name": "接口名", "has_gateway": bool}, ...]
    """
    system = platform.system()
    ips = []
    
    if system == "Windows":
        ips = _get_ips_windows()
    else:
        ips = _get_ips_unix()
    
    # 过滤掉回环地址和 APIPA 地址
    ips = [ip for ip in ips if not ip["ip"].startswith("127.") 
           and not ip["ip"].startswith("169.254.")]
    
    return ips


def _get_ips_windows() -> list:
    """Windows: 使用 ipconfig 获取所有 IP"""
    ips = []
    try:
        result = subprocess.run(
            ["ipconfig", "/all"],
            capture_output=True,
            text=True,
            encoding="gbk",  # Windows 中文编码
            errors="ignore",
            timeout=10
        )
        
        current_adapter = ""
        current_ip = ""
        has_gateway = False
        
        lines = result.stdout.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 适配器名称行：不以空格开头，以冒号结尾
            # 例如: "无线局域网适配器 WLAN:" 或 "以太网适配器 VMware Network Adapter VMnet1:"
            if line and not line[0].isspace() and stripped.endswith(":"):
                # 保存上一个适配器的信息
                if current_ip:
                    ips.append({
                        "ip": current_ip,
                        "name": current_adapter,
                        "has_gateway": has_gateway
                    })
                current_adapter = stripped.rstrip(":")
                current_ip = ""
                has_gateway = False
            
            # 检测 IPv4 地址行
            # 例如: "   IPv4 地址 . . . . . . . . . . . . : 10.196.7.192(首选)"
            elif "IPv4" in stripped and ":" in stripped:
                match = re.search(r":\s*(\d+\.\d+\.\d+\.\d+)", stripped)
                if match:
                    current_ip = match.group(1)
            
            # 检测默认网关（有实际 IP 地址表示有网关）
            # 例如: "   默认网关. . . . . . . . . . . . . : 10.196.0.1"
            elif ("默认网关" in stripped or "Default Gateway" in stripped) and ":" in stripped:
                # 检查冒号后面是否有 IP 地址
                after_colon = stripped.split(":", 1)[-1].strip()
                if re.match(r"\d+\.\d+\.\d+\.\d+", after_colon):
                    has_gateway = True
            
            i += 1
        
        # 保存最后一个适配器
        if current_ip:
            ips.append({
                "ip": current_ip,
                "name": current_adapter,
                "has_gateway": has_gateway
            })
            
    except Exception as e:
        print(f"[WARN] ipconfig failed: {e}")
    
    return ips


def _get_ips_unix() -> list:
    """Linux/macOS: 使用 ip 或 ifconfig 获取所有 IP"""
    ips = []
    
    # 尝试 ip route 获取默认网关接口
    default_iface = None
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=5
        )
        match = re.search(r"dev\s+(\S+)", result.stdout)
        if match:
            default_iface = match.group(1)
    except Exception:
        pass
    
    # 获取所有 IP
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        current_iface = ""
        for line in result.stdout.split("\n"):
            # 接口行: "2: eth0: <...>"
            iface_match = re.match(r"\d+:\s+(\S+):", line)
            if iface_match:
                current_iface = iface_match.group(1)
            
            # IP 行: "    inet 192.168.1.100/24 ..."
            ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", line)
            if ip_match and current_iface:
                ips.append({
                    "ip": ip_match.group(1),
                    "name": current_iface,
                    "has_gateway": current_iface == default_iface
                })
                
    except Exception:
        # 备用方案：使用 socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            ips.append({"ip": ip, "name": "default", "has_gateway": True})
        except Exception:
            pass
    
    return ips


def get_local_ip() -> str:
    """
    获取本机最佳局域网 IP 地址
    
    优先级：
    1. WLAN/Wi-Fi 接口（手机最可能连接的网络）
    2. 有默认网关的接口
    3. 非虚拟机网卡
    4. 第一个可用的局域网 IP
    """
    ips = get_all_local_ips()
    
    if not ips:
        # 最后的备用方案
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
    
    # WLAN/Wi-Fi 关键词
    wifi_keywords = ["wlan", "wi-fi", "wifi", "wireless", "无线"]
    
    # 虚拟网卡关键词
    virtual_keywords = ["vmware", "virtualbox", "vbox", "vmnet", "vethernet", 
                        "docker", "hyper-v", "wsl", "meta"]
    
    def is_wifi(name: str) -> bool:
        name_lower = name.lower()
        return any(kw in name_lower for kw in wifi_keywords)
    
    def is_virtual(name: str) -> bool:
        name_lower = name.lower()
        return any(kw in name_lower for kw in virtual_keywords)
    
    # 最优先：WLAN/Wi-Fi 接口
    for ip_info in ips:
        if is_wifi(ip_info["name"]) and not is_virtual(ip_info["name"]):
            return ip_info["ip"]
    
    # 次选：有网关 + 非虚拟
    for ip_info in ips:
        if ip_info["has_gateway"] and not is_virtual(ip_info["name"]):
            return ip_info["ip"]
    
    # 再次：有网关（可能是虚拟机桥接）
    for ip_info in ips:
        if ip_info["has_gateway"]:
            return ip_info["ip"]
    
    # 再次：非虚拟网卡
    for ip_info in ips:
        if not is_virtual(ip_info["name"]):
            return ip_info["ip"]
    
    # 最后：第一个可用的
    return ips[0]["ip"]


def get_server_url(ip: str, port: int, https: bool = False) -> str:
    """生成服务器完整 URL"""
    protocol = "https" if https else "http"
    return f"{protocol}://{ip}:{port}"


def print_all_ips():
    """打印所有可用 IP（调试用）"""
    ips = get_all_local_ips()
    print("\n可用的网络接口:")
    print("-" * 50)
    for ip_info in ips:
        gateway_mark = " [有网关]" if ip_info["has_gateway"] else ""
        print(f"  {ip_info['ip']:16} - {ip_info['name']}{gateway_mark}")
    print("-" * 50)
    print(f"  选择的 IP: {get_local_ip()}\n")


if __name__ == "__main__":
    print_all_ips()
