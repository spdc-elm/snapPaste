"""
剪贴板操作模块 - 将图片直接写入 Windows 剪贴板（不落盘）
"""

import io
import platform
import subprocess
import base64
from typing import Union


def image_to_clipboard(image_data: bytes) -> bool:
    """
    将图片数据直接写入系统剪贴板（内存操作，不创建临时文件）
    
    Args:
        image_data: 图片的二进制数据（PNG/JPEG 格式）
    
    Returns:
        bool: 成功返回 True，失败返回 False
    """
    system = platform.system()
    
    if system == "Windows":
        return _windows_clipboard(image_data)
    elif system == "Linux":
        return _linux_clipboard(image_data)
    elif system == "Darwin":
        return _macos_clipboard(image_data)
    else:
        raise NotImplementedError(f"Unsupported platform: {system}")


def _windows_clipboard(image_data: bytes) -> bool:
    """Windows: 使用 win32clipboard 直接写入剪贴板"""
    try:
        # 优先尝试 win32clipboard（更高效）
        import win32clipboard
        from PIL import Image
        
        # 从内存加载图片
        img = Image.open(io.BytesIO(image_data))
        
        # 转换为 BMP 格式（Windows 剪贴板原生支持）
        output = io.BytesIO()
        # 转换为 RGB 模式（BMP 不支持 RGBA）
        if img.mode == "RGBA":
            # 创建白色背景
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")
        
        img.save(output, format="BMP")
        bmp_data = output.getvalue()
        
        # BMP 文件头是 14 字节，剪贴板需要的是 DIB 数据（跳过文件头）
        dib_data = bmp_data[14:]
        
        # 写入剪贴板
        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
        finally:
            win32clipboard.CloseClipboard()
        
        return True
        
    except ImportError:
        # 备用方案：使用 PowerShell
        return _windows_powershell(image_data)


def _windows_powershell(image_data: bytes) -> bool:
    """Windows 备用方案：通过 PowerShell 写入剪贴板"""
    try:
        # 将图片数据转为 Base64
        b64_data = base64.b64encode(image_data).decode('utf-8')
        
        # PowerShell 脚本：从 Base64 加载图片并写入剪贴板
        ps_script = f'''
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$bytes = [Convert]::FromBase64String("{b64_data}")
$ms = New-Object System.IO.MemoryStream(,$bytes)
$img = [System.Drawing.Image]::FromStream($ms)
[System.Windows.Forms.Clipboard]::SetImage($img)
$ms.Dispose()
$img.Dispose()
'''
        
        # 执行 PowerShell（通过 stdin 传递脚本，避免命令行长度限制）
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "-"],
            input=ps_script,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"PowerShell clipboard error: {e}")
        return False


def _linux_clipboard(image_data: bytes) -> bool:
    """Linux: 使用 xclip 写入剪贴板"""
    try:
        # 通过 stdin 传递图片数据，避免临时文件
        process = subprocess.Popen(
            ["xclip", "-selection", "clipboard", "-t", "image/png"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(input=image_data, timeout=10)
        return process.returncode == 0
    except FileNotFoundError:
        # 尝试 xsel
        try:
            process = subprocess.Popen(
                ["xsel", "--clipboard", "--input", "--type", "image/png"],
                stdin=subprocess.PIPE
            )
            process.communicate(input=image_data, timeout=10)
            return process.returncode == 0
        except Exception as e:
            print(f"Linux clipboard error: {e}")
            return False
    except Exception as e:
        print(f"Linux clipboard error: {e}")
        return False


def _macos_clipboard(image_data: bytes) -> bool:
    """macOS: 使用 osascript + 内存操作"""
    try:
        from PIL import Image
        import subprocess
        
        # 从内存加载并转换为 TIFF（macOS 剪贴板原生支持）
        img = Image.open(io.BytesIO(image_data))
        output = io.BytesIO()
        img.save(output, format="TIFF")
        tiff_data = output.getvalue()
        
        # 使用 osascript 写入剪贴板
        # 通过 stdin 传递数据
        script = '''
            set theImage to (read POSIX file "/dev/stdin" as TIFF picture)
            set the clipboard to theImage
        '''
        
        # macOS 需要不同的方法，使用 pbcopy 的变体
        # 实际上 macOS 没有简单的方法通过命令行写入图片
        # 最可靠的方式是使用 PyObjC
        try:
            from AppKit import NSPasteboard, NSPasteboardTypeTIFF, NSData
            
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            
            ns_data = NSData.dataWithBytes_length_(tiff_data, len(tiff_data))
            pasteboard.setData_forType_(ns_data, NSPasteboardTypeTIFF)
            return True
        except ImportError:
            print("macOS requires PyObjC for clipboard image support")
            return False
            
    except Exception as e:
        print(f"macOS clipboard error: {e}")
        return False


def decode_base64_image(data: Union[str, bytes]) -> bytes:
    """
    解码 Base64 图片数据
    
    支持带 data URI 前缀和不带前缀的格式
    """
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    
    # 移除 data URI 前缀（如果有）
    if data.startswith("data:"):
        # 格式: data:image/png;base64,xxxxx
        data = data.split(",", 1)[1]
    
    return base64.b64decode(data)


if __name__ == "__main__":
    # 测试代码
    print(f"Platform: {platform.system()}")
    print("Clipboard module ready")
