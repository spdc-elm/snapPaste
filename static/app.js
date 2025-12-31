/**
 * SnapPaste - 手机拍照，电脑粘贴
 * 支持缩放控制和拍照后编辑
 */

const UPLOAD_URL = '/api/upload';
const JPEG_QUALITY = 0.85;

// ============ DOM 元素 ============
const video = document.getElementById('camera');
const canvas = document.getElementById('canvas');
const captureBtn = document.getElementById('capture');
const statusEl = document.getElementById('status');
const errorOverlay = document.getElementById('error');
const errorMsg = document.getElementById('error-msg');
const retryBtn = document.getElementById('retry');
const fileInput = document.getElementById('file-input');

// 缩放控制
const zoomControl = document.getElementById('zoom-control');
const zoomSlider = document.getElementById('zoom-slider');
const zoomValue = document.querySelector('.zoom-value');

// 编辑视图
const cameraView = document.getElementById('camera-view');
const editView = document.getElementById('edit-view');
const editCanvas = document.getElementById('edit-canvas');
const cropBox = document.getElementById('crop-box');
const btnRotate = document.getElementById('btn-rotate');
const btnCrop = document.getElementById('btn-crop');
const btnCancel = document.getElementById('btn-cancel');
const btnConfirm = document.getElementById('btn-confirm');

// ============ 状态 ============
let stream = null;
let isSending = false;
let currentTrack = null;
let zoomCapabilities = null;

// 编辑状态
let editImage = null;  // 原始图片
let rotation = 0;      // 旋转角度 (0, 90, 180, 270)
let cropMode = false;  // 是否在裁剪模式
let cropRect = null;   // 裁剪区域 {x, y, w, h}

// ============ 摄像头初始化 ============
async function initCamera() {
  try {
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
    
    await new Promise((resolve) => {
      video.onloadedmetadata = resolve;
    });
    
    // 获取视频轨道和缩放能力
    currentTrack = stream.getVideoTracks()[0];
    await initZoomControl();
    
    hideError();
    console.log('摄像头已就绪');
  } catch (err) {
    console.error('摄像头初始化失败:', err);
    showError(getErrorMessage(err));
  }
}

// ============ 缩放控制 ============
let useNativeZoom = false;  // 是否使用原生缩放
let currentZoom = 1;        // 当前缩放值

async function initZoomControl() {
  // 始终显示缩放控制
  zoomSlider.min = 1;
  zoomSlider.max = 5;
  zoomSlider.step = 0.1;
  zoomSlider.value = 1;
  currentZoom = 1;
  updateZoomDisplay(1);
  zoomControl.classList.remove('hidden');
  
  // 尝试检测原生缩放支持
  if (currentTrack) {
    try {
      const capabilities = currentTrack.getCapabilities();
      if (capabilities.zoom) {
        zoomCapabilities = capabilities.zoom;
        zoomSlider.min = zoomCapabilities.min;
        zoomSlider.max = Math.min(zoomCapabilities.max, 5);
        zoomSlider.step = zoomCapabilities.step || 0.1;
        zoomSlider.value = zoomCapabilities.min;
        currentZoom = zoomCapabilities.min;
        updateZoomDisplay(zoomCapabilities.min);
        // 应用最小缩放
        await currentTrack.applyConstraints({
          advanced: [{ zoom: zoomCapabilities.min }]
        });
        useNativeZoom = true;
        console.log('使用原生缩放:', zoomCapabilities);
      } else {
        console.log('使用 CSS 缩放 (原生不支持)');
      }
    } catch (err) {
      console.log('使用 CSS 缩放 (检测失败):', err);
    }
  }
}

function updateZoomDisplay(value) {
  zoomValue.textContent = parseFloat(value).toFixed(1) + 'x';
}

async function setZoom(value) {
  const zoomVal = parseFloat(value);
  currentZoom = zoomVal;
  updateZoomDisplay(zoomVal);
  
  if (useNativeZoom && currentTrack && zoomCapabilities) {
    // 使用原生缩放
    try {
      await currentTrack.applyConstraints({
        advanced: [{ zoom: zoomVal }]
      });
      video.style.transform = '';  // 清除 CSS 缩放
    } catch (err) {
      console.error('原生缩放失败，回退到 CSS:', err);
      useNativeZoom = false;
      applyCssZoom(zoomVal);
    }
  } else {
    // 使用 CSS 缩放
    applyCssZoom(zoomVal);
  }
}

function applyCssZoom(value) {
  video.style.transform = `scale(${value})`;
  video.style.transformOrigin = 'center center';
}

// ============ 拍照 ============
async function capturePhoto() {
  if (isSending || !stream) return;
  
  // 闪光效果
  flashEffect();
  
  const ctx = canvas.getContext('2d');
  
  // 如果使用 CSS 缩放，需要裁剪中心区域
  if (!useNativeZoom && currentZoom > 1) {
    // 计算裁剪区域
    const cropW = video.videoWidth / currentZoom;
    const cropH = video.videoHeight / currentZoom;
    const cropX = (video.videoWidth - cropW) / 2;
    const cropY = (video.videoHeight - cropH) / 2;
    
    canvas.width = cropW;
    canvas.height = cropH;
    ctx.drawImage(video, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
  } else {
    // 原生缩放或无缩放，直接捕获
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
  }
  
  // 转换为图片对象
  const imageData = canvas.toDataURL('image/jpeg', JPEG_QUALITY);
  
  // 进入编辑模式
  enterEditMode(imageData);
}

// ============ 编辑模式 ============
function enterEditMode(imageDataUrl) {
  editImage = new Image();
  editImage.onload = () => {
    rotation = 0;
    cropMode = false;
    cropRect = null;
    cropBox.classList.add('hidden');
    btnCrop.classList.remove('active');
    
    // 先显示 editView，确保容器有尺寸
    cameraView.classList.add('hidden');
    editView.classList.remove('hidden');
    
    // 等待下一帧再绘制，确保 DOM 已更新布局
    requestAnimationFrame(() => {
      drawEditCanvas();
    });
  };
  editImage.src = imageDataUrl;
}

function exitEditMode() {
  editView.classList.add('hidden');
  cameraView.classList.remove('hidden');
  editImage = null;
  rotation = 0;
  cropMode = false;
  cropRect = null;
}

function drawEditCanvas() {
  if (!editImage) return;
  
  const ctx = editCanvas.getContext('2d');
  
  // 计算旋转后的尺寸
  const isRotated = rotation === 90 || rotation === 270;
  const imgW = isRotated ? editImage.height : editImage.width;
  const imgH = isRotated ? editImage.width : editImage.height;
  
  // 适应容器大小
  const container = editCanvas.parentElement;
  const maxW = container.clientWidth;
  const maxH = container.clientHeight;
  const scale = Math.min(maxW / imgW, maxH / imgH, 1);
  
  editCanvas.width = imgW * scale;
  editCanvas.height = imgH * scale;
  
  // 清空并绘制
  ctx.clearRect(0, 0, editCanvas.width, editCanvas.height);
  ctx.save();
  
  // 移动到中心点旋转
  ctx.translate(editCanvas.width / 2, editCanvas.height / 2);
  ctx.rotate((rotation * Math.PI) / 180);
  
  // 绘制图片（考虑旋转后的偏移）
  const drawW = isRotated ? editCanvas.height : editCanvas.width;
  const drawH = isRotated ? editCanvas.width : editCanvas.height;
  ctx.drawImage(editImage, -drawW / 2, -drawH / 2, drawW, drawH);
  
  ctx.restore();
  
  // 如果在裁剪模式，初始化裁剪框
  if (cropMode && !cropRect) {
    initCropBox();
  }
}

// ============ 旋转 ============
function rotateImage() {
  rotation = (rotation + 90) % 360;
  drawEditCanvas();
  
  // 重置裁剪框
  if (cropMode) {
    cropRect = null;
    initCropBox();
  }
}

// ============ 裁剪 ============
function toggleCropMode() {
  cropMode = !cropMode;
  btnCrop.classList.toggle('active', cropMode);
  
  if (cropMode) {
    initCropBox();
    cropBox.classList.remove('hidden');
  } else {
    cropBox.classList.add('hidden');
    cropRect = null;
  }
}

function initCropBox() {
  const rect = editCanvas.getBoundingClientRect();
  const padding = 40;
  
  cropRect = {
    x: padding,
    y: padding,
    w: rect.width - padding * 2,
    h: rect.height - padding * 2
  };
  
  updateCropBoxUI();
}

function updateCropBoxUI() {
  if (!cropRect) return;
  
  const canvasRect = editCanvas.getBoundingClientRect();
  const container = editCanvas.parentElement;
  const containerRect = container.getBoundingClientRect();
  
  // 计算 canvas 在容器中的偏移
  const offsetX = canvasRect.left - containerRect.left;
  const offsetY = canvasRect.top - containerRect.top;
  
  cropBox.style.left = (offsetX + cropRect.x) + 'px';
  cropBox.style.top = (offsetY + cropRect.y) + 'px';
  cropBox.style.width = cropRect.w + 'px';
  cropBox.style.height = cropRect.h + 'px';
}

// 裁剪框拖动
let dragStart = null;
let dragType = null; // 'move' | 'tl' | 'tr' | 'bl' | 'br'

function startCropDrag(e, type) {
  e.preventDefault();
  dragType = type;
  const touch = e.touches ? e.touches[0] : e;
  dragStart = {
    x: touch.clientX,
    y: touch.clientY,
    rect: { ...cropRect }
  };
  
  document.addEventListener('mousemove', onCropDrag);
  document.addEventListener('mouseup', endCropDrag);
  document.addEventListener('touchmove', onCropDrag);
  document.addEventListener('touchend', endCropDrag);
}

function onCropDrag(e) {
  if (!dragStart || !cropRect) return;
  
  const touch = e.touches ? e.touches[0] : e;
  const dx = touch.clientX - dragStart.x;
  const dy = touch.clientY - dragStart.y;
  
  const canvasRect = editCanvas.getBoundingClientRect();
  const minSize = 50;
  
  if (dragType === 'move') {
    cropRect.x = Math.max(0, Math.min(canvasRect.width - cropRect.w, dragStart.rect.x + dx));
    cropRect.y = Math.max(0, Math.min(canvasRect.height - cropRect.h, dragStart.rect.y + dy));
  } else {
    // 角落拖动调整大小
    const startRect = dragStart.rect;
    
    if (dragType.includes('l')) {
      const newX = Math.max(0, Math.min(startRect.x + startRect.w - minSize, startRect.x + dx));
      cropRect.w = startRect.w + (startRect.x - newX);
      cropRect.x = newX;
    }
    if (dragType.includes('r')) {
      cropRect.w = Math.max(minSize, Math.min(canvasRect.width - startRect.x, startRect.w + dx));
    }
    if (dragType.includes('t')) {
      const newY = Math.max(0, Math.min(startRect.y + startRect.h - minSize, startRect.y + dy));
      cropRect.h = startRect.h + (startRect.y - newY);
      cropRect.y = newY;
    }
    if (dragType.includes('b')) {
      cropRect.h = Math.max(minSize, Math.min(canvasRect.height - startRect.y, startRect.h + dy));
    }
  }
  
  updateCropBoxUI();
}

function endCropDrag() {
  dragStart = null;
  dragType = null;
  document.removeEventListener('mousemove', onCropDrag);
  document.removeEventListener('mouseup', endCropDrag);
  document.removeEventListener('touchmove', onCropDrag);
  document.removeEventListener('touchend', endCropDrag);
}

// ============ 发送图片 ============
async function sendEditedImage() {
  if (isSending) return;
  
  isSending = true;
  btnConfirm.disabled = true;
  showStatus('发送中...', 'sending');
  
  try {
    // 生成最终图片
    const finalCanvas = document.createElement('canvas');
    const ctx = finalCanvas.getContext('2d');
    
    // 计算最终尺寸
    const isRotated = rotation === 90 || rotation === 270;
    let srcW = editImage.width;
    let srcH = editImage.height;
    
    if (cropMode && cropRect) {
      // 计算裁剪区域在原图上的坐标
      const canvasRect = editCanvas.getBoundingClientRect();
      const scaleX = (isRotated ? editImage.height : editImage.width) / editCanvas.width;
      const scaleY = (isRotated ? editImage.width : editImage.height) / editCanvas.height;
      
      finalCanvas.width = cropRect.w * scaleX;
      finalCanvas.height = cropRect.h * scaleY;
      
      // 绘制裁剪后的图片
      ctx.save();
      ctx.translate(finalCanvas.width / 2, finalCanvas.height / 2);
      ctx.rotate((rotation * Math.PI) / 180);
      
      const cropX = cropRect.x * scaleX;
      const cropY = cropRect.y * scaleY;
      const cropW = cropRect.w * scaleX;
      const cropH = cropRect.h * scaleY;
      
      // 根据旋转调整源区域
      let sx, sy, sw, sh;
      if (rotation === 0) {
        sx = cropX; sy = cropY; sw = cropW; sh = cropH;
      } else if (rotation === 90) {
        sx = cropY; sy = editImage.height - cropX - cropW; sw = cropH; sh = cropW;
      } else if (rotation === 180) {
        sx = editImage.width - cropX - cropW; sy = editImage.height - cropY - cropH; sw = cropW; sh = cropH;
      } else {
        sx = editImage.width - cropY - cropH; sy = cropX; sw = cropH; sh = cropW;
      }
      
      const drawW = isRotated ? finalCanvas.height : finalCanvas.width;
      const drawH = isRotated ? finalCanvas.width : finalCanvas.height;
      ctx.drawImage(editImage, sx, sy, sw, sh, -drawW / 2, -drawH / 2, drawW, drawH);
      ctx.restore();
    } else {
      // 无裁剪，只应用旋转
      finalCanvas.width = isRotated ? srcH : srcW;
      finalCanvas.height = isRotated ? srcW : srcH;
      
      ctx.translate(finalCanvas.width / 2, finalCanvas.height / 2);
      ctx.rotate((rotation * Math.PI) / 180);
      ctx.drawImage(editImage, -srcW / 2, -srcH / 2);
    }
    
    // 转换为 Blob 并上传
    const blob = await new Promise(resolve => {
      finalCanvas.toBlob(resolve, 'image/jpeg', JPEG_QUALITY);
    });
    
    await uploadImage(blob);
    
    showStatus('已发送到剪贴板 ✓', 'success');
    vibrate();
    
    // 返回相机视图
    setTimeout(() => {
      exitEditMode();
      hideStatus();
    }, 1000);
    
  } catch (err) {
    console.error('发送失败:', err);
    showStatus('发送失败，请重试', 'error');
    setTimeout(hideStatus, 3000);
  } finally {
    isSending = false;
    btnConfirm.disabled = false;
  }
}

// ============ 工具函数 ============
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

function flashEffect() {
  let flash = document.querySelector('.flash');
  if (!flash) {
    flash = document.createElement('div');
    flash.className = 'flash';
    cameraView.appendChild(flash);
  }
  flash.classList.remove('active');
  void flash.offsetWidth;
  flash.classList.add('active');
}

function vibrate() {
  if ('vibrate' in navigator) {
    navigator.vibrate(50);
  }
}

function showStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = `status ${type}`;
}

function hideStatus() {
  statusEl.classList.add('hidden');
}

function showError(message) {
  errorMsg.textContent = message;
  errorOverlay.classList.remove('hidden');
}

function hideError() {
  errorOverlay.classList.add('hidden');
}

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

// ============ 事件绑定 ============
// 拍照按钮
captureBtn.addEventListener('click', capturePhoto);
captureBtn.addEventListener('touchend', (e) => {
  e.preventDefault();
  capturePhoto();
});

// 重试按钮
retryBtn.addEventListener('click', initCamera);

// 缩放滑块
zoomSlider.addEventListener('input', (e) => {
  setZoom(e.target.value);
});

// 阻止缩放滑块触发浏览器手势
zoomSlider.addEventListener('touchstart', (e) => {
  e.stopPropagation();
}, { passive: true });

zoomSlider.addEventListener('touchmove', (e) => {
  e.stopPropagation();
  e.preventDefault();  // 阻止页面滚动/手势
}, { passive: false });

// 编辑工具栏
btnRotate.addEventListener('click', rotateImage);
btnCrop.addEventListener('click', toggleCropMode);
btnCancel.addEventListener('click', exitEditMode);
btnConfirm.addEventListener('click', sendEditedImage);

// 裁剪框拖动
cropBox.addEventListener('mousedown', (e) => startCropDrag(e, 'move'));
cropBox.addEventListener('touchstart', (e) => startCropDrag(e, 'move'));

document.querySelectorAll('.crop-handle').forEach(handle => {
  const type = handle.classList.contains('tl') ? 'tl' :
               handle.classList.contains('tr') ? 'tr' :
               handle.classList.contains('bl') ? 'bl' : 'br';
  handle.addEventListener('mousedown', (e) => { e.stopPropagation(); startCropDrag(e, type); });
  handle.addEventListener('touchstart', (e) => { e.stopPropagation(); startCropDrag(e, type); });
});

// 文件选择（备选方案）
fileInput.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  const reader = new FileReader();
  reader.onload = (event) => {
    enterEditMode(event.target.result);
    errorOverlay.classList.add('hidden');
  };
  reader.readAsDataURL(file);
  fileInput.value = '';
});

// 窗口大小变化时重绘编辑画布
window.addEventListener('resize', () => {
  if (!editView.classList.contains('hidden') && editImage) {
    drawEditCanvas();
  }
});

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
  initCamera();
  registerServiceWorker();
});

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !stream && cameraView && !cameraView.classList.contains('hidden')) {
    initCamera();
  }
});
