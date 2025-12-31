/**
 * SnapPaste - 手机拍照，电脑粘贴
 * 拍完即传，无需二次确认
 */

const UPLOAD_URL = '/api/upload';
const JPEG_QUALITY = 0.8;

// DOM 元素
const video = document.getElementById('camera');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('capture');
const statusEl = document.getElementById('status');
const errorOverlay = document.getElementById('error');
const errorMsg = document.getElementById('error-msg');
const retryBtn = document.getElementById('retry');
const fileInput = document.getElementById('file-input');

// 状态
let stream = null;
let isSending = false;

/**
 * 初始化摄像头
 */
async function initCamera() {
  try {
    // 优先使用后置摄像头
    const constraints = {
      video: {
        facingMode: { ideal: 'environment' },
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      },
      audio: false
    };
    
    stream = await navigator.mediaDevices.getUserMedia(constraints);
    video.srcObject = stream;
    
    // 等待视频加载
    await new Promise((resolve) => {
      video.onloadedmetadata = resolve;
    });
    
    hideError();
    console.log('摄像头已就绪');
  } catch (err) {
    console.error('摄像头初始化失败:', err);
    showError(getErrorMessage(err));
  }
}

/**
 * 获取友好的错误信息
 */
function getErrorMessage(err) {
  if (err.name === 'NotAllowedError') {
    return '请在浏览器设置中允许摄像头权限';
  }
  if (err.name === 'NotFoundError') {
    return '未找到可用的摄像头';
  }
  if (err.name === 'NotReadableError') {
    return '摄像头被其他应用占用';
  }
  return err.message || '未知错误';
}

/**
 * 拍照并发送
 */
async function captureAndSend() {
  if (isSending || !stream) return;
  
  isSending = true;
  captureBtn.disabled = true;
  captureBtn.classList.add('sending');
  
  try {
    // 闪光效果
    flashEffect();
    
    // 捕获图像
    const imageBlob = await captureImage();
    
    // 显示发送状态
    showStatus('发送中...', 'sending');
    
    // 发送到服务器
    await uploadImage(imageBlob);
    
    // 成功反馈
    showStatus('已发送到剪贴板 ✓', 'success');
    vibrate();
    
  } catch (err) {
    console.error('发送失败:', err);
    showStatus('发送失败，请重试', 'error');
  } finally {
    isSending = false;
    captureBtn.disabled = false;
    captureBtn.classList.remove('sending');
    
    // 3秒后隐藏状态
    setTimeout(hideStatus, 3000);
  }
}

/**
 * 捕获图像为 Blob
 */
function captureImage() {
  return new Promise((resolve, reject) => {
    try {
      // 设置 canvas 尺寸与视频一致
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      
      // 绘制当前帧
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      // 转换为 JPEG Blob
      canvas.toBlob(
        (blob) => {
          if (blob) {
            resolve(blob);
          } else {
            reject(new Error('图像捕获失败'));
          }
        },
        'image/jpeg',
        JPEG_QUALITY
      );
    } catch (err) {
      reject(err);
    }
  });
}

/**
 * 上传图片到服务器
 */
async function uploadImage(blob) {
  const formData = new FormData();
  formData.append('image', blob, 'photo.jpg');
  
  const response = await fetch(UPLOAD_URL, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  
  return response.json();
}

/**
 * 闪光效果
 */
function flashEffect() {
  // 创建闪光元素
  let flash = document.querySelector('.flash');
  if (!flash) {
    flash = document.createElement('div');
    flash.className = 'flash';
    document.getElementById('app').appendChild(flash);
  }
  
  // 触发动画
  flash.classList.remove('active');
  void flash.offsetWidth; // 强制重绘
  flash.classList.add('active');
}

/**
 * 震动反馈
 */
function vibrate() {
  if ('vibrate' in navigator) {
    navigator.vibrate(50);
  }
}

/**
 * 显示状态提示
 */
function showStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = `status ${type}`;
}

/**
 * 隐藏状态提示
 */
function hideStatus() {
  statusEl.classList.add('hidden');
}

/**
 * 显示错误
 */
function showError(message) {
  errorMsg.textContent = message;
  errorOverlay.classList.remove('hidden');
}

/**
 * 隐藏错误
 */
function hideError() {
  errorOverlay.classList.add('hidden');
}

/**
 * 注册 Service Worker
 */
async function registerServiceWorker() {
  if ('serviceWorker' in navigator) {
    try {
      await navigator.serviceWorker.register('sw.js');
      console.log('Service Worker 已注册');
    } catch (err) {
      console.warn('Service Worker 注册失败:', err);
    }
  }
}

// 事件绑定
captureBtn.addEventListener('click', captureAndSend);
retryBtn.addEventListener('click', initCamera);

// 文件选择（摄像头不可用时的备选方案）
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  try {
    showStatus('发送中...', 'sending');
    await uploadImage(file);
    showStatus('已发送到剪贴板 ✓', 'success');
    vibrate();
  } catch (err) {
    console.error('发送失败:', err);
    showStatus('发送失败，请重试', 'error');
  } finally {
    fileInput.value = ''; // 清空以便重复选择
    setTimeout(hideStatus, 3000);
  }
});

// 防止双击缩放
captureBtn.addEventListener('touchend', (e) => {
  e.preventDefault();
  captureAndSend();
});

// 初始化
document.addEventListener('DOMContentLoaded', () => {
  initCamera();
  registerServiceWorker();
});

// 页面可见性变化时重新初始化摄像头
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !stream) {
    initCamera();
  }
});
