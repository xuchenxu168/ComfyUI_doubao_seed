"""
Doubao-Seed 节点
基于ComfyUI_Comfly项目的Doubao Seedream4实现
集成多家API调用，支持图像生成和视频生成功能
"""

import os
import json
import requests
import time
import random
import base64
import io
import subprocess
from PIL import Image
import torch
import numpy as np
from typing import Optional, Dict, Any, List, Tuple
import urllib3
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import tempfile
import shutil
from urllib.parse import urlparse
from fractions import Fraction

# 导入ComfyUI的视频类型 - 使用官方标准
try:
    from comfy_api.input_impl import VideoFromFile
    HAS_COMFYUI_VIDEO = True
    print("[SeedReam4API] 信息：✅ ComfyUI官方视频类型导入成功")
except ImportError as e:
    try:
        # 尝试旧版本路径
        from comfy_api.latest._input_impl.video_types import VideoFromComponents
        from comfy_api.latest._util import VideoComponents
        HAS_COMFYUI_VIDEO = True
        print("[SeedReam4API] 信息：✅ ComfyUI视频类型导入成功（旧版本）")
        # 创建VideoFromFile的兼容类
        class VideoFromFile:
            def __init__(self, file_or_components):
                if hasattr(file_or_components, 'images'):
                    # 这是VideoComponents对象
                    self.components = file_or_components
                    self.file_path = None  # 组件模式没有文件路径
                else:
                    # 这是文件路径或BytesIO
                    self.file_path = file_or_components
                    self.file = file_or_components  # 保持向后兼容
            def get_dimensions(self):
                if hasattr(self, 'components'):
                    return self.components.images.shape[2], self.components.images.shape[1]
                else:
                    # 从文件读取尺寸
                    return (512, 512)  # 默认尺寸
    except ImportError:
        HAS_COMFYUI_VIDEO = False
        print(f"[SeedReam4API] 警告：⚠️ ComfyUI视频类型导入失败: {e}")
        # 创建简单的替代类
        class VideoFromFile:
            def __init__(self, file_path):
                self.file_path = file_path
            def get_dimensions(self):
                return (512, 512)  # 默认尺寸

# 尝试导入视频处理库
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    _log_warning("OpenCV未安装，视频处理功能受限")

try:
    import imageio
    HAS_IMAGEIO = True
except ImportError:
    HAS_IMAGEIO = False

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def create_ssl_compatible_session():
    """创建SSL兼容的requests session"""
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    # 创建自定义的HTTPAdapter
    class SSLAdapter(HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            # 创建更宽松的SSL上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            # 支持更多SSL协议版本和密码套件
            try:
                ssl_context.minimum_version = ssl.TLSVersion.TLSv1
                ssl_context.maximum_version = ssl.TLSVersion.TLSv1_3
            except AttributeError:
                # 兼容旧版本Python
                pass

            # 设置更宽松的密码套件
            try:
                ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
            except ssl.SSLError:
                try:
                    ssl_context.set_ciphers('ALL:!aNULL:!eNULL:!EXPORT:!DES:!RC4:!MD5:!PSK:!SRP:!CAMELLIA')
                except ssl.SSLError:
                    pass  # 使用默认密码套件

            # 禁用各种SSL检查
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            kwargs['ssl_context'] = ssl_context
            return super().init_poolmanager(*args, **kwargs)

    # 应用适配器
    adapter = SSLAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    # 设置超时和其他选项
    session.verify = False  # 禁用SSL验证

    return session

# 全局常量和配置
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEEDREAM4_CONFIG_FILE = 'SeedReam4_config.json'

def _log_info(message):
    print(f"[SeedReam4API] 信息：{message}")

def _log_warning(message):
    print(f"[SeedReam4API] 警告：{message}")

def _log_error(message):
    print(f"[SeedReam4API] 错误：{message}")

def get_seedream4_config():
    """获取SeedReam4配置文件"""
    config_path = os.path.join(CURRENT_DIR, SEEDREAM4_CONFIG_FILE)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config
        else:
            _log_warning(f"未找到SeedReam4配置文件 {SEEDREAM4_CONFIG_FILE}，使用默认配置")
            return get_default_config()
    except Exception as e:
        _log_error(f"读取SeedReam4配置文件失败: {e}")
        return get_default_config()

def get_default_config():
    """获取默认配置"""
    return {
        "api_key": "",
        "base_url": "https://ai.comfly.chat/v1",
        "proxy": "None",
        "default_model": "doubao-seedream-4-0-250828",
        "timeout": 900,
        "max_retries": 3,
        "mirror_sites": {
            "comfly": {
                "url": "https://ai.comfly.chat/v1",
                "api_key": "",
                "api_format": "comfly",
                "models": ["doubao-seedream-4-0-250828"],
                "video_models": ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"],
                "description": "Comfly官方API，支持SeedReam4.0模型和Seedance视频生成"
            },
            "t8_mirror": {
                "url": "https://ai.t8star.cn",
                "api_key": "",
                "api_format": "volcengine",
                "models": ["doubao-seedream-4-0-250828"],
                "video_models": ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"],
                "description": "T8镜像站，使用火山引擎官方格式API"
            },
            "volcengine": {
                "url": "https://ark.cn-beijing.volces.com",
                "api_key": "",
                "api_format": "volcengine",
                "models": ["doubao-seedream-4-0-250828"],
                "video_models": ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"],
                "description": "火山引擎官方API，支持图像和视频生成"
            }
        },
        "size_mapping": {
            "1K": {
                "1:1": "1024x1024",
                "4:3": "1152x864",
                "3:4": "864x1152",
                "16:9": "1280x720",
                "9:16": "720x1280",
                "2:3": "832x1248",
                "3:2": "1248x832",
                "21:9": "1512x648",
                "9:21": "648x1512"
            },
            "2K": {
                "1:1": "2048x2048",
                "4:3": "2048x1536",
                "3:4": "1536x2048",
                "16:9": "2048x1152",
                "9:16": "1152x2048",
                "2:3": "1536x2048",
                "3:2": "2048x1536",
                "21:9": "2048x864",
                "9:21": "864x2048"
            },
            "4K": {
                "1:1": "4096x4096",
                "4:3": "4096x3072",
                "3:4": "3072x4096",
                "16:9": "4096x2304",
                "9:16": "2304x4096",
                "2:3": "3072x4096",
                "3:2": "4096x3072",
                "21:9": "4096x1728",
                "9:21": "1728x4096"
            }
        },
        "resolution_factors": {
            "1K": 1,
            "2K": 2,
            "4K": 4
        }
    }

def save_seedream4_config(config):
    """保存SeedReam4配置"""
    config_path = os.path.join(CURRENT_DIR, SEEDREAM4_CONFIG_FILE)
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        _log_info("SeedReam4配置保存成功")
    except Exception as e:
        _log_error(f"保存SeedReam4配置失败: {e}")

def get_mirror_site_config(mirror_site_name: str) -> Dict[str, str]:
    """根据镜像站名称或URL获取对应的配置"""
    config = get_seedream4_config()
    mirror_sites = config.get('mirror_sites', {})

    # 检查是否是直接的URL
    if validate_api_url(mirror_site_name):
        # 直接使用提供的URL
        api_format = "comfly"  # 默认格式

        # 根据URL特征判断API格式
        if "t8star.cn" in mirror_site_name:
            api_format = "volcengine"  # T8镜像站使用火山引擎官方格式
        elif "volcengine" in mirror_site_name or "volces.com" in mirror_site_name:
            api_format = "volcengine"
        elif "openrouter" in mirror_site_name:
            api_format = "openrouter"
        elif "api4gpt" in mirror_site_name:
            api_format = "api4gpt"

        return {
            "url": mirror_site_name,
            "api_key": "",
            "api_format": api_format,
            "models": [],
            "video_models": ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"],
            "description": f"直接URL: {mirror_site_name}"
        }

    # 检查是否是预定义的镜像站名称
    if mirror_site_name in mirror_sites:
        site_config = mirror_sites[mirror_site_name]
        return {
            "url": site_config.get("url", ""),
            "api_key": site_config.get("api_key", ""),
            "api_format": site_config.get("api_format", "comfly"),
            "models": site_config.get("models", []),
            "video_models": site_config.get("video_models", ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"]),
            "description": site_config.get("description", "")
        }

    # 如果没找到，返回默认配置
    return {
        "url": "https://ai.comfly.chat/v1",
        "api_key": "",
        "api_format": "comfly",
        "models": ["doubao-seedream-4-0-250828"],
        "video_models": ["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"],
        "description": "默认Comfly配置"
    }

def validate_api_key(api_key):
    """验证API key格式"""
    return api_key and len(api_key.strip()) > 10

def validate_api_url(url):
    """验证API URL格式"""
    if not url or not url.strip():
        return False
    url = url.strip().rstrip('/')
    return url.startswith('http://') or url.startswith('https://')

def tensor2pil(tensor):
    """将tensor转换为PIL图像 - 支持ComfyUI的[B, H, W, C]格式"""
    if tensor is None:
        _log_warning("⚠️ tensor2pil: 输入tensor为None")
        return None
    if isinstance(tensor, list):
        return [tensor2pil(img) for img in tensor]

    try:
        # 确保tensor是4维的
        if len(tensor.shape) == 3:
            tensor = tensor.unsqueeze(0)

        # 如果是batch，处理多图情况（这里只处理单图转换，多图拼接在image_to_base64中处理）
        if len(tensor.shape) == 4 and tensor.shape[0] > 1:
            # 对于tensor2pil函数，我们只转换第一张图像
            # 多图拼接逻辑在image_to_base64函数中处理
            tensor = tensor[0:1]

        # 现在应该是 [1, H, W, C] 格式，去掉batch维度
        if len(tensor.shape) == 4:
            tensor = tensor.squeeze(0)  # 变成 [H, W, C]

        # 检查是否需要转换通道顺序
        if len(tensor.shape) == 3:
            # 如果最后一个维度不是3（RGB通道），可能是[C, H, W]格式
            if tensor.shape[-1] != 3 and tensor.shape[0] == 3:
                tensor = tensor.permute(1, 2, 0)  # [C, H, W] -> [H, W, C]

        # 转换为numpy数组
        if hasattr(tensor, 'cpu'):
            # PyTorch tensor
            np_image = tensor.cpu().numpy()
        else:
            # 已经是numpy数组
            np_image = tensor

        # 确保数据类型和范围正确
        if np_image.dtype != np.uint8:
            if np_image.max() <= 1.0:
                np_image = (np_image * 255).astype(np.uint8)
            else:
                np_image = np.clip(np_image, 0, 255).astype(np.uint8)

        # 如果是灰度图像，转换为RGB
        if len(np_image.shape) == 2:
            np_image = np.stack([np_image] * 3, axis=-1)
        elif np_image.shape[-1] == 1:
            np_image = np.repeat(np_image, 3, axis=-1)

        pil_image = Image.fromarray(np_image)

        return pil_image

    except Exception as e:
        _log_error(f"❌ tensor2pil转换失败: {e}")
        import traceback
        traceback.print_exc()
        return None

def pil2tensor(image):
    """将PIL图像转换为tensor - 参考ComfyUI_Comfly的实现"""
    if image is None:
        return None
    if isinstance(image, list):
        if len(image) == 0:
            return torch.empty(0)
        return torch.cat([pil2tensor(img) for img in image], dim=0)
    
    # 转换为RGB
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    elif image.mode != 'RGB':
        image = image.convert('RGB')
    
    # 转换为numpy数组并归一化到[0, 1]
    img_array = np.array(image).astype(np.float32) / 255.0
    
    # 返回tensor，格式为[1, H, W, 3] - 这是ComfyUI的标准格式
    return torch.from_numpy(img_array)[None,]

def create_blank_tensor(width=1024, height=1024):
    """创建正确格式的空白tensor - 参考ComfyUI_Comfly的实现"""
    blank_image = Image.new('RGB', (width, height), color='white')
    np_image = np.array(blank_image).astype(np.float32) / 255.0
    # 返回tensor，格式为[1, H, W, 3] - 这是ComfyUI的标准格式
    return torch.from_numpy(np_image)[None,]

def ensure_tensor_format(tensor):
    """确保tensor格式完全符合ComfyUI要求 - 格式为[1, H, W, 3]"""
    if tensor is None:
        return create_blank_tensor()
    
    original_shape = tensor.shape
    _log_info(f"🔍 输入tensor形状: {original_shape}")
    
    # 处理特殊情况：如果tensor形状是 (1, 1, 2048) 或类似格式
    if len(tensor.shape) == 3 and tensor.shape[1] == 1 and tensor.shape[2] > 1000:
        _log_warning(f"⚠️ 检测到异常tensor形状: {tensor.shape}，可能是1D数据被错误reshape")
        return create_blank_tensor()
    
    # 确保是4维tensor，格式为[1, H, W, 3]
    if len(tensor.shape) != 4:
        if len(tensor.shape) == 3:
            # 检查是否是 (H, W, 3) 格式
            if tensor.shape[-1] == 3:
                tensor = tensor.unsqueeze(0)
                _log_info(f"🔧 添加batch维度: {tensor.shape}")
            else:
                _log_error(f"❌ 无法修复tensor维度: {original_shape}")
                return create_blank_tensor()
        else:
            _log_error(f"❌ 无法修复tensor维度: {original_shape}")
            return create_blank_tensor()
    
    # 确保是 (batch, height, width, channels) 格式
    if tensor.shape[-1] != 3:
        if tensor.shape[1] == 3:  # 如果是 (batch, channels, height, width) 格式
            tensor = tensor.permute(0, 2, 3, 1)
            _log_info(f"🔧 重新排列tensor维度: {tensor.shape}")
        else:
            _log_error(f"❌ 无法修复tensor通道维度: {tensor.shape}")
            return create_blank_tensor()
    
    # 确保数据类型正确
    if tensor.dtype != torch.float32:
        tensor = tensor.float()
        _log_info(f"🔧 转换tensor数据类型: {tensor.dtype}")
    
    # 确保值范围正确 (0-1)
    if tensor.min() < 0 or tensor.max() > 1:
        tensor = torch.clamp(tensor, 0, 1)
        _log_info(f"🔧 限制tensor值范围: {tensor.min().item():.3f} 到 {tensor.max().item():.3f}")
    
    # 确保没有异常值
    if torch.isnan(tensor).any() or torch.isinf(tensor).any():
        _log_error("❌ tensor包含异常值，使用空白tensor替代")
        return create_blank_tensor()
    
    # 最终验证 - 确保是[1, H, W, 3]格式
    if len(tensor.shape) != 4 or tensor.shape[-1] != 3:
        _log_error(f"❌ 最终tensor格式仍然不正确: {tensor.shape}")
        return create_blank_tensor()
    
    _log_info(f"✅ tensor格式验证通过: {tensor.shape}")
    return tensor

def image_to_base64(image_tensor, max_size=2048, return_data_url=True):
    """将tensor转换为base64字符串，支持自动压缩和多图拼接

    Args:
        image_tensor: 输入的图像tensor
        max_size: 最大尺寸限制
        return_data_url: 是否返回完整的data URL格式，False则只返回base64字符串
    """
    if image_tensor is None:
        return None

    # 如果是batch，将多张图像水平拼接成一张大图
    if len(image_tensor.shape) == 4 and image_tensor.shape[0] > 1:
        _log_info(f"🔍 检测到多图batch输入 {image_tensor.shape}，将拼接成一张大图")

        # 将每张图像转换为PIL图像
        pil_images = []
        for i in range(image_tensor.shape[0]):
            single_tensor = image_tensor[i:i+1]  # 保持4D格式
            pil_img = tensor2pil(single_tensor)
            if pil_img is not None:
                pil_images.append(pil_img)

        if not pil_images:
            return None

        # 水平拼接图像
        total_width = sum(img.width for img in pil_images)
        max_height = max(img.height for img in pil_images)

        # 创建拼接后的大图
        combined_image = Image.new('RGB', (total_width, max_height), (255, 255, 255))
        x_offset = 0
        for img in pil_images:
            combined_image.paste(img, (x_offset, 0))
            x_offset += img.width

        pil_image = combined_image
        _log_info(f"🔧 多图拼接完成: {len(pil_images)}张图 -> {pil_image.size}")
    else:
        pil_image = tensor2pil(image_tensor)
        if pil_image is None:
            return None

    # 检查图像尺寸，如果过大则压缩
    original_size = pil_image.size
    if max(original_size) > max_size:
        # 计算新尺寸，保持宽高比
        ratio = max_size / max(original_size)
        new_size = (int(original_size[0] * ratio), int(original_size[1] * ratio))
        pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
        _log_info(f"🔧 图像压缩: {original_size} -> {new_size}")

    buffered = io.BytesIO()
    # 使用JPEG格式压缩大图像，PNG格式保留小图像
    if max(pil_image.size) > 1024:
        # 对于图像编辑，使用更高质量的JPEG
        quality = 90 if max(original_size) > max_size else 85
        pil_image.save(buffered, format="JPEG", quality=quality, optimize=True)
        format_prefix = "data:image/jpeg;base64,"
    else:
        pil_image.save(buffered, format="PNG", optimize=True)
        format_prefix = "data:image/png;base64,"

    image_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

    # 验证base64字符串的有效性
    try:
        # 尝试解码验证
        base64.b64decode(image_base64)
    except Exception as e:
        _log_warning(f"⚠️ Base64编码验证失败: {e}")
        return None

    if return_data_url:
        return f"{format_prefix}{image_base64}"
    else:
        return image_base64

def download_video_from_url(video_url: str, output_dir: str = None) -> str:
    """从URL下载视频文件"""
    try:
        if not video_url or not video_url.strip():
            raise ValueError("视频URL为空")

        # 解析URL获取文件名
        parsed_url = urlparse(video_url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:
            filename = f"video_{int(time.time())}.mp4"

        # 确定输出目录
        if output_dir is None:
            # 使用ComfyUI的输出目录
            try:
                import folder_paths
                output_dir = folder_paths.get_output_directory()
            except:
                output_dir = tempfile.gettempdir()

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        # 完整的输出路径
        output_path = os.path.join(output_dir, filename)

        _log_info(f"🔽 开始下载视频: {video_url}")
        _log_info(f"📁 保存路径: {output_path}")

        # 下载视频
        response = requests.get(video_url, stream=True, timeout=300)
        response.raise_for_status()

        # 写入文件
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        file_size = os.path.getsize(output_path)
        _log_info(f"✅ 视频下载完成: {filename} ({file_size / 1024 / 1024:.2f} MB)")

        return output_path

    except Exception as e:
        _log_error(f"视频下载失败: {e}")
        return None

def video_to_comfyui_video(video_path: str):
    """将视频文件转换为ComfyUI VIDEO对象 - 使用官方标准VideoFromFile"""
    try:
        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"视频文件不存在: {video_path}")

        _log_info(f"🎬 开始创建ComfyUI VideoFromFile对象: {video_path}")

        # 使用ComfyUI官方标准：直接从文件路径创建VideoFromFile对象
        video_obj = VideoFromFile(video_path)

        _log_info("✅ 创建ComfyUI标准VideoFromFile对象成功")

        # 测试get_dimensions方法
        try:
            dimensions = video_obj.get_dimensions()
            _log_info(f"📊 视频尺寸: {dimensions}")
        except Exception as e:
            _log_warning(f"⚠️ 无法获取视频尺寸: {e}")

        return video_obj

    except Exception as e:
        _log_error(f"创建VideoFromFile对象失败: {e}")
        return None

def create_video_path_wrapper(file_path):
    """创建一个视频路径包装器，用于UtilNodes兼容性"""
    # 直接返回文件路径字符串，让UtilNodes的os.path.basename()能正常工作
    return file_path

def extract_video_last_frame(video_path, output_path=None):
    """
    提取视频的最后一帧图像

    Args:
        video_path: 视频文件路径
        output_path: 输出图片路径，如果为None则自动生成

    Returns:
        str: 输出图片的路径，失败返回None
    """
    try:
        import subprocess
        import tempfile
        from pathlib import Path

        if not os.path.exists(video_path):
            _log_error(f"视频文件不存在: {video_path}")
            return None

        # 如果没有指定输出路径，自动生成
        if output_path is None:
            video_name = Path(video_path).stem
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"{video_name}_last_frame_{int(time.time())}.jpg")

        _log_info(f"🎬 正在提取视频尾帧: {video_path}")

        # 方法1：使用FFmpeg的select=eof过滤器
        cmd1 = [
            'ffmpeg',
            '-i', video_path,           # 输入视频
            '-vf', 'select=eof',        # 选择最后一帧
            '-vsync', 'vfr',            # 可变帧率
            '-frames:v', '1',           # 只输出1帧
            '-y',                       # 覆盖输出文件
            output_path
        ]

        try:
            result = subprocess.run(
                cmd1,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info(f"✅ 尾帧提取成功: {output_path}")
                return output_path
        except:
            pass

        # 方法2：如果方法1失败，使用时长计算方法
        _log_info("🔄 尝试备用方法提取尾帧...")

        # 获取视频时长
        duration_cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0',
            video_path
        ]

        duration_result = subprocess.run(
            duration_cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if duration_result.returncode == 0:
            try:
                duration = float(duration_result.stdout.strip())
                seek_time = max(0, duration - 0.1)  # 提取最后0.1秒前的帧

                cmd2 = [
                    'ffmpeg',
                    '-ss', str(seek_time),
                    '-i', video_path,
                    '-frames:v', '1',
                    '-y',
                    output_path
                ]

                result = subprocess.run(
                    cmd2,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0 and os.path.exists(output_path):
                    _log_info(f"✅ 尾帧提取成功 (备用方法): {output_path}")
                    return output_path
            except:
                pass

        _log_error("❌ 所有尾帧提取方法都失败了")
        return None

    except Exception as e:
        _log_error(f"提取视频尾帧失败: {str(e)}")
        return None

def merge_videos_with_ffmpeg(video_paths, output_path=None):
    """使用ffmpeg合并多个视频文件"""
    try:
        import subprocess
        import tempfile

        if not video_paths or len(video_paths) < 2:
            _log_warning("⚠️ 视频数量不足，无需合并")
            return video_paths[0] if video_paths else None

        # 验证所有视频文件存在
        valid_paths = []
        for path in video_paths:
            if path and os.path.exists(path):
                valid_paths.append(path)
            else:
                _log_warning(f"⚠️ 视频文件不存在，跳过: {path}")

        if len(valid_paths) < 2:
            _log_warning("⚠️ 有效视频数量不足，无需合并")
            return valid_paths[0] if valid_paths else None

        # 生成输出文件路径 - 使用ComfyUI输出目录
        if not output_path:
            timestamp = int(time.time())
            try:
                import folder_paths
                output_dir = folder_paths.get_output_directory()
            except ImportError:
                # 推断ComfyUI输出目录
                current_dir = os.path.dirname(os.path.abspath(__file__))
                path_parts = current_dir.split(os.sep)
                comfyui_root = None

                for i in range(len(path_parts) - 1, -1, -1):
                    potential_root = os.sep.join(path_parts[:i+1])
                    if os.path.exists(os.path.join(potential_root, "main.py")):
                        comfyui_root = potential_root
                        break

                if comfyui_root:
                    output_dir = os.path.join(comfyui_root, "output")
                    os.makedirs(output_dir, exist_ok=True)
                else:
                    import tempfile
                    output_dir = tempfile.gettempdir()
            except:
                import tempfile
                output_dir = tempfile.gettempdir()
            output_path = os.path.join(output_dir, f"merged_continuous_video_{timestamp}.mp4")

        _log_info(f"🎬 开始合并{len(valid_paths)}个视频文件...")
        _log_info(f"📁 输出路径: {output_path}")

        # 创建ffmpeg输入文件列表
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            for path in valid_paths:
                # 使用绝对路径并转义特殊字符
                abs_path = os.path.abspath(path).replace('\\', '/')
                f.write(f"file '{abs_path}'\n")
            input_list_path = f.name

        try:
            # 构建ffmpeg命令
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', input_list_path,
                '-c', 'copy',  # 直接复制流，不重新编码
                '-y',  # 覆盖输出文件
                output_path
            ]

            _log_info(f"🔧 执行ffmpeg命令: {' '.join(cmd)}")

            # 执行ffmpeg命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode == 0:
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    _log_info(f"✅ 视频合并成功: {output_path} (大小: {file_size} bytes)")
                    return output_path
                else:
                    _log_error("❌ ffmpeg执行成功但输出文件不存在")
                    return None
            else:
                _log_error(f"❌ ffmpeg执行失败: {result.stderr}")
                return None

        finally:
            # 清理临时文件
            try:
                os.unlink(input_list_path)
            except:
                pass

    except subprocess.TimeoutExpired:
        _log_error("❌ ffmpeg执行超时")
        return None
    except FileNotFoundError:
        _log_error("❌ 未找到ffmpeg，请确保已安装ffmpeg并添加到PATH")
        return None
    except Exception as e:
        _log_error(f"❌ 视频合并失败: {str(e)}")
        return None

def get_resolution_dimensions(resolution, aspect_ratio):
    """根据分辨率和宽高比获取实际像素尺寸

    Args:
        resolution: "480p", "720p", "1080p"
        aspect_ratio: "16:9", "4:3", "1:1", "3:4", "9:16", "21:9"

    Returns:
        tuple: (width, height) 或 None
    """
    # Seedance 1.0 pro 支持的分辨率和宽高比对应表
    resolution_map = {
        "480p": {
            "16:9": (864, 480),
            "4:3": (736, 544),
            "1:1": (640, 640),
            "3:4": (544, 736),
            "9:16": (480, 864),
            "21:9": (960, 416)
        },
        "720p": {
            "16:9": (1248, 704),
            "4:3": (1120, 832),
            "1:1": (960, 960),
            "3:4": (832, 1120),
            "9:16": (704, 1248),
            "21:9": (1504, 640)
        },
        "1080p": {
            "16:9": (1920, 1088),
            "4:3": (1664, 1248),
            "1:1": (1440, 1440),
            "3:4": (1248, 1664),
            "9:16": (1088, 1920),
            "21:9": (2176, 928)
        }
    }

    if resolution in resolution_map and aspect_ratio in resolution_map[resolution]:
        dimensions = resolution_map[resolution][aspect_ratio]
        _log_info(f"🔍 分辨率计算: {resolution} + {aspect_ratio} = {dimensions[0]}x{dimensions[1]}")
        return dimensions
    else:
        _log_warning(f"⚠️ 不支持的分辨率或宽高比组合: {resolution} + {aspect_ratio}")
        # 返回默认值
        default_dimensions = (1248, 704)  # 720p 16:9
        _log_info(f"🔧 使用默认分辨率: {default_dimensions[0]}x{default_dimensions[1]}")
        return default_dimensions

def create_blank_video_object(frames=30, height=512, width=512):
    """创建空白视频对象 - 使用临时文件创建VideoFromFile"""
    try:
        _log_info(f"🎬 创建空白视频文件: {frames}帧, {width}x{height}")

        # 创建临时视频文件
        temp_video_path = os.path.join(tempfile.gettempdir(), f"blank_video_{int(time.time())}.mp4")

        # 使用OpenCV创建空白视频文件
        if HAS_CV2:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, 30.0, (width, height))

            # 创建黑色帧
            blank_frame = np.zeros((height, width, 3), dtype=np.uint8)

            for _ in range(frames):
                out.write(blank_frame)

            out.release()
            _log_info(f"✅ 空白视频文件创建成功: {temp_video_path}")
        else:
            # 如果没有OpenCV，创建一个最小的MP4文件
            _log_warning("⚠️ 没有OpenCV，创建简单的空白视频对象")
            # 这里我们仍然需要一个有效的视频文件路径
            # 作为回退，我们创建一个虚拟路径
            temp_video_path = "blank_video.mp4"

        # 创建ComfyUI VideoFromFile对象
        video_obj = VideoFromFile(temp_video_path)
        return video_obj

    except Exception as e:
        _log_error(f"创建空白视频对象失败: {e}")
        # 最后的回退：创建一个简单的VideoFromFile对象
        return VideoFromFile("blank_video.mp4")

def call_comfly_api(api_url, api_key, payload, timeout=900):
    """调用Comfly API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # 调试信息
    _log_info(f"🔍 Comfly API调用:")
    _log_info(f"   - 端点: {api_url}/images/generations")
    _log_info(f"   - 模型: {payload.get('model', 'N/A')}")
    _log_info(f"   - 包含图像: {'image' in payload and bool(payload.get('image'))}")
    if 'image' in payload and payload.get('image'):
        _log_info(f"   - 图像数量: {len(payload['image'])}")
        _log_info(f"   - 第一张图像长度: {len(payload['image'][0]) if payload['image'] else 0}")

    try:
        # 使用SSL兼容的session
        session = create_ssl_compatible_session()
        response = session.post(
            f"{api_url}/images/generations",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        return response
    except Exception as e:
        _log_error(f"Comfly API调用失败: {e}")
        return None

def call_openai_compatible_api(api_url, api_key, payload, timeout=900):
    """调用OpenAI兼容API - 支持T8图像编辑"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    try:
        # 检查是否是T8镜像站
        if "t8star.cn" in api_url or "ai.t8star.cn" in api_url:
            # 检查是否有图像输入
            has_images = "image" in payload and payload["image"]

            # 对于T8，图生图也使用images/generations端点，而不是chat/completions
            # 只有特定的图像编辑任务才使用chat/completions
            use_chat_endpoint = False  # 暂时禁用chat端点，统一使用images/generations

            if has_images and use_chat_endpoint:
                # 图像编辑：使用chat/completions端点（暂时禁用）
                url = "https://ai.t8star.cn/v1/chat/completions"
                _log_info(f"🎨 T8图像编辑端点: {url}")

                # 构建T8图像编辑的payload格式
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": payload.get("prompt", "")
                            }
                        ]
                    }
                ]

                # 添加图像到消息中
                image_urls = payload.get("image", [])
                if isinstance(image_urls, str):
                    image_urls = [image_urls]

                for image_url in image_urls:
                    messages[0]["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    })

                t8_payload = {
                    "model": payload.get("model", "doubao-seedream-4-0-250828"),
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.7
                }

                _log_info(f"🎨 T8图像编辑请求: 模型={t8_payload.get('model')}, 消息数={len(t8_payload.get('messages', []))}")

            else:
                # 图像生成：使用images/generations端点
                url = "https://ai.t8star.cn/v1/images/generations"
                _log_info(f"🖼️ T8图像生成端点: {url}")

                # 构建T8图像生成的payload格式
                t8_payload = {
                    "prompt": payload.get("prompt", ""),
                    "model": payload.get("model", "doubao-seedream-4-0-250828"),
                    "response_format": payload.get("response_format", "url")
                }

                # 添加可选参数
                if "size" in payload:
                    t8_payload["size"] = payload["size"]
                if "n" in payload:
                    t8_payload["n"] = payload["n"]
                if "seed" in payload and payload["seed"] != -1:
                    t8_payload["seed"] = payload["seed"]
                if "watermark" in payload:
                    t8_payload["watermark"] = payload["watermark"]
                if "tail_on_partial" in payload:
                    t8_payload["tail_on_partial"] = payload["tail_on_partial"]

                # 添加图像输入支持（图生图）
                if has_images:
                    t8_payload["image"] = payload["image"]
                    _log_info(f"🖼️ T8图生图请求: 包含 {len(payload['image'])} 张输入图像")
                    _log_info(f"🔍 图像数据类型: {type(payload['image'])}")
                    if payload['image']:
                        _log_info(f"🔍 第一张图像数据长度: {len(payload['image'][0]) if payload['image'][0] else 0} 字符")

                _log_info(f"🖼️ T8图像生成请求: 模型={t8_payload.get('model')}, 提示词长度={len(t8_payload.get('prompt', ''))}")

        elif api_url.endswith('/v1/chat/completions'):
            url = api_url.replace('/v1/chat/completions', '/v1/images/generations')
            _log_info(f"🔗 转换聊天端点为图像生成端点: {url}")
            t8_payload = payload
        else:
            # 其他OpenAI兼容API
            url = f"{api_url}/v1/images/generations"
            _log_info(f"🔗 使用标准OpenAI端点: {url}")
            t8_payload = payload

        # 尝试多种连接方式解决SSL问题
        response = None
        last_error = None

        # 方法1：禁用所有SSL验证的简单方式
        try:
            import urllib3
            urllib3.disable_warnings()

            # 设置环境变量禁用SSL验证
            import os
            os.environ['PYTHONHTTPSVERIFY'] = '0'
            os.environ['CURL_CA_BUNDLE'] = ''

            response = requests.post(
                url,
                headers=headers,
                json=t8_payload,
                timeout=timeout,
                verify=False,
                stream=False
            )
            _log_info(f"✅ 简单SSL禁用方式成功")

        except Exception as simple_error:
            last_error = simple_error
            _log_warning(f"简单SSL禁用失败: {simple_error}")

            # 方法2：使用SSL兼容的session
            try:
                session = create_ssl_compatible_session()
                response = session.post(
                    url,
                    headers=headers,
                    json=t8_payload,
                    timeout=timeout
                )
                _log_info(f"✅ SSL兼容session成功")

            except Exception as ssl_error:
                last_error = ssl_error
                _log_warning(f"SSL兼容session失败: {ssl_error}")

                # 方法3：使用curl作为备用方案
                try:
                    import subprocess
                    import tempfile

                    # 将payload写入临时文件
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                        json.dump(t8_payload, f)
                        temp_file = f.name

                    # 构建curl命令
                    curl_cmd = [
                        'curl', '-k', '-X', 'POST',
                        '-H', 'Content-Type: application/json',
                        '-H', f'Authorization: Bearer {headers["Authorization"].split(" ")[1]}',
                        '-d', f'@{temp_file}',
                        '--connect-timeout', '30',
                        '--max-time', str(timeout),
                        url
                    ]

                    result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout)

                    # 清理临时文件
                    os.unlink(temp_file)

                    if result.returncode == 0:
                        # 创建模拟response对象
                        class MockResponse:
                            def __init__(self, text, status_code=200):
                                self.text = text
                                self.status_code = status_code
                            def json(self):
                                return json.loads(self.text)

                        response = MockResponse(result.stdout)
                        _log_info(f"✅ curl备用方案成功")
                    else:
                        raise Exception(f"curl失败: {result.stderr}")

                except Exception as curl_error:
                    _log_warning(f"curl备用方案失败: {curl_error}")
                    raise last_error  # 抛出最后一个错误

        _log_info(f"🔍 T8 API响应状态: {response.status_code}")
        if response.status_code != 200:
            _log_error(f"❌ T8 API错误: {response.status_code} - {response.text}")

        return response

    except Exception as e:
        _log_error(f"OpenAI兼容API调用失败: {e}")
        return None

def call_api4gpt_api(api_url, api_key, payload, timeout=900):
    """调用API4GPT API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.post(
            f"{api_url}/v1/images/generations",
            headers=headers,
            json=payload,
            timeout=timeout,
            verify=False
        )
        return response
    except Exception as e:
        _log_error(f"API4GPT API调用失败: {e}")
        return None

def call_openrouter_api(api_url, api_key, payload, timeout=900):
    """调用OpenRouter API"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    try:
        response = requests.post(
            f"{api_url}/images/generations",
            headers=headers,
            json=payload,
            timeout=timeout,
            verify=False
        )
        return response
    except Exception as e:
        _log_error(f"OpenRouter API调用失败: {e}")
        return None


def call_volcengine_api(api_url, api_key, payload, timeout=900):
    """调用火山引擎API"""
    try:
        # 火山引擎API使用特定的认证方式
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ComfyUI-SeedReam4API/1.0"
        }
        
        # 火山引擎的图像生成API端点
        endpoint = f"{api_url}/images/generations"
        
        # 构建火山引擎特定的请求载荷
        volcengine_payload = {
            "model": payload.get("model", "doubao-seedream-4-0-250828"),
            "prompt": payload.get("prompt", ""),
            "size": payload.get("size", "1024x1024"),
            "n": payload.get("n", 1),
            "response_format": payload.get("response_format", "url"),
            "quality": "hd",  # 火山引擎支持hd质量
            "style": "vivid"  # 火山引擎支持vivid风格
        }
        
        # 添加可选参数
        if "seed" in payload and payload["seed"] != -1:
            volcengine_payload["seed"] = payload["seed"]
        
        if "watermark" in payload:
            volcengine_payload["watermark"] = payload["watermark"]

        if "tail_on_partial" in payload:
            volcengine_payload["tail_on_partial"] = payload["tail_on_partial"]
        
        # 处理图像输入（用于图像编辑）
        if "image" in payload and payload["image"]:
            volcengine_payload["image"] = payload["image"]
            _log_info(f"🔍 火山引擎图像输入: 数量={len(payload['image'])}, 第一张长度={len(payload['image'][0]) if payload['image'] else 0}")

        _log_info(f"🔗 调用火山引擎API: {endpoint}")
        _log_info(f"🔍 火山引擎请求: 模型={volcengine_payload.get('model')}, 提示词长度={len(volcengine_payload.get('prompt', ''))}")
        _log_info(f"🔍 火山引擎payload包含图像: {'image' in volcengine_payload}")
        
        response = requests.post(
            endpoint,
            headers=headers,
            json=volcengine_payload,
            timeout=timeout,
            verify=False
        )
        
        _log_info(f"🔍 火山引擎API响应状态: {response.status_code}")
        if response.status_code != 200:
            _log_error(f"❌ 火山引擎API错误: {response.text}")
        
        return response
    except Exception as e:
        _log_error(f"火山引擎API调用异常: {e}")
        return None

def call_video_api(api_url, api_key, payload, api_format="comfly", timeout=900):
    """调用视频生成API"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ComfyUI-SeedanceAPI/1.0"
        }

        # 根据API格式确定端点 - 使用各镜像站的实际端点
        if api_format == "comfly":
            # Comfly的视频端点，使用v2/videos/generations
            if api_url.endswith('/v1'):
                endpoint = f"{api_url[:-3]}/v2/videos/generations"  # 使用 /v2/videos/generations
            else:
                endpoint = f"{api_url}/v2/videos/generations"
        elif api_format == "openai":
            # T8镜像站使用v2端点
            if "t8star.cn" in api_url:
                # T8的视频端点，处理URL版本号
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations"  # 替换v1为v2
                else:
                    endpoint = f"{api_url}/v2/videos/generations"
            else:
                endpoint = f"{api_url}/v1/videos/generations"

        elif api_format == "volcengine":
            # 火山引擎官方API、T8镜像站和Comfly镜像站
            if "t8star.cn" in api_url:
                # T8镜像站使用特殊的端点路径
                endpoint = f"{api_url}/seedance/v3/contents/generations/tasks"
            elif "comfly.chat" in api_url:
                # Comfly镜像站使用火山引擎格式端点
                endpoint = f"{api_url.replace('/v1', '').replace('/v2', '')}/seedance/v3/contents/generations/tasks"
            else:
                # 火山引擎官方API
                endpoint = f"{api_url}/contents/generations/tasks"
        else:
            # 默认处理：检查是否是T8或Comfly
            if "t8star.cn" in api_url:
                # T8使用v2端点
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations"
                else:
                    endpoint = f"{api_url}/v2/videos/generations"
            else:
                # 默认使用Comfly格式
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations"
                else:
                    endpoint = f"{api_url}/v2/videos/generations"

        _log_info(f"🎬 调用视频生成API: {endpoint}")
        _log_info(f"🔍 视频API格式: {api_format}")

        # 根据不同格式提取提示词长度
        prompt_length = 0
        if "prompt" in payload:
            prompt_length = len(payload.get('prompt', ''))
        elif "content" in payload:
            # 火山引擎格式：从content数组中提取text
            for item in payload.get('content', []):
                if item.get('type') == 'text':
                    prompt_length = len(item.get('text', ''))
                    break

        _log_info(f"🔍 视频请求: 模型={payload.get('model')}, 提示词长度={prompt_length}")

        if "image" in payload and payload["image"]:
            _log_info(f"🔍 视频输入图像: 数量={len(payload['image'])}")
        elif "first_frame" in payload and "last_frame" in payload:
            _log_info(f"🔍 视频首尾帧模式")
        elif "content" in payload:
            _log_info(f"🔍 视频content模式: 内容数量={len(payload['content'])}")

        # 调试：打印实际发送的payload结构
        _log_info(f"🔍 实际发送的payload键: {list(payload.keys())}")
        if "content" in payload:
            _log_info(f"🔍 content数组长度: {len(payload['content'])}")
            for i, item in enumerate(payload['content']):
                _log_info(f"🔍 content[{i}]: type={item.get('type')}, role={item.get('role', 'N/A')}")

        # 调试：测试JSON序列化
        try:
            import json
            json_str = json.dumps(payload, ensure_ascii=False)
            _log_info(f"🔍 JSON序列化成功，长度: {len(json_str)}")
            # 重新解析验证
            parsed_payload = json.loads(json_str)
            _log_info(f"🔍 JSON解析后的键: {list(parsed_payload.keys())}")
            if "content" in parsed_payload:
                _log_info(f"🔍 解析后content数组长度: {len(parsed_payload['content'])}")
        except Exception as json_e:
            _log_error(f"❌ JSON序列化失败: {json_e}")

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
            verify=False
        )

        _log_info(f"🔍 视频API响应状态: {response.status_code}")
        if response.status_code != 200:
            _log_error(f"❌ 视频API错误: {response.text}")

        return response

    except Exception as e:
        _log_error(f"视频生成API调用失败: {e}")
        return None

def call_multi_ref_video_api(api_url, api_key, payload, api_format="comfly", timeout=900):
    """调用多图参考视频生成API - 统一使用火山引擎格式端点"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ComfyUI-SeedanceAPI/1.0"
        }

        # 多图参考功能统一使用火山引擎格式的端点
        if api_format == "volcengine":
            # 火山引擎官方API
            endpoint = f"{api_url}/contents/generations/tasks"
        elif api_format == "comfly":
            # Comfly镜像站使用火山引擎官方格式端点
            if "comfly.chat" in api_url:
                # Comfly的火山引擎格式端点
                endpoint = f"{api_url.replace('/v1', '').replace('/v2', '')}/seedance/v3/contents/generations/tasks"
            else:
                endpoint = f"{api_url}/seedance/v3/contents/generations/tasks"
        else:
            # 其他格式默认使用火山引擎格式
            endpoint = f"{api_url}/contents/generations/tasks"

        _log_info(f"🎬 调用多图参考视频生成API: {endpoint}")
        _log_info(f"🔍 多图参考API格式: {api_format}")

        # 根据不同格式提取提示词长度
        prompt_length = 0
        if "content" in payload:
            # 火山引擎格式：从content数组中提取text
            for item in payload.get('content', []):
                if item.get('type') == 'text':
                    prompt_length = len(item.get('text', ''))
                    break

        _log_info(f"🔍 多图参考请求: 模型={payload.get('model')}, 提示词长度={prompt_length}")
        _log_info(f"🔍 多图参考content模式: 内容数量={len(payload.get('content', []))}")

        # 调试：打印实际发送的payload结构
        _log_info(f"🔍 实际发送的payload键: {list(payload.keys())}")
        if "content" in payload:
            _log_info(f"🔍 content数组长度: {len(payload['content'])}")
            for i, item in enumerate(payload['content']):
                _log_info(f"🔍 content[{i}]: type={item.get('type')}, role={item.get('role', 'N/A')}")

        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
            verify=False
        )

        _log_info(f"🔍 多图参考API响应状态: {response.status_code}")
        if response.status_code != 200:
            _log_error(f"❌ 多图参考API错误: {response.text}")

        return response

    except Exception as e:
        _log_error(f"多图参考视频生成API调用失败: {e}")
        return None

def call_video_task_status(api_url, api_key, task_id, api_format="comfly", timeout=60):
    """查询视频生成任务状态"""
    try:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "ComfyUI-SeedanceAPI/1.0"
        }

        # 根据API格式确定查询端点
        if api_format == "comfly":
            # Comfly的查询端点，使用v2/videos/generations
            if api_url.endswith('/v1'):
                endpoint = f"{api_url[:-3]}/v2/videos/generations/{task_id}"
            else:
                endpoint = f"{api_url}/v2/videos/generations/{task_id}"
        elif api_format == "openai":
            # T8镜像站使用v2端点
            if "t8star.cn" in api_url:
                # T8的查询端点，处理URL版本号
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations/{task_id}"  # 替换v1为v2
                else:
                    endpoint = f"{api_url}/v2/videos/generations/{task_id}"
            else:
                endpoint = f"{api_url}/v1/videos/generations/{task_id}"

        elif api_format == "volcengine":
            # 火山引擎官方API、T8镜像站和Comfly镜像站
            if "t8star.cn" in api_url:
                # T8镜像站使用特殊的查询端点路径
                endpoint = f"{api_url}/seedance/v3/contents/generations/tasks/{task_id}"
            elif "comfly.chat" in api_url:
                # Comfly镜像站使用火山引擎格式查询端点
                endpoint = f"{api_url.replace('/v1', '').replace('/v2', '')}/seedance/v3/contents/generations/tasks/{task_id}"
            else:
                # 火山引擎官方API
                endpoint = f"{api_url}/contents/generations/tasks/{task_id}"
        else:
            # 默认处理：检查是否是T8或Comfly
            if "t8star.cn" in api_url:
                # T8使用v2端点
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations/{task_id}"
                else:
                    endpoint = f"{api_url}/v2/videos/generations/{task_id}"
            else:
                # 默认使用Comfly格式
                if api_url.endswith('/v1'):
                    endpoint = f"{api_url[:-3]}/v2/videos/generations/{task_id}"
                else:
                    endpoint = f"{api_url}/v2/videos/generations/{task_id}"

        _log_info(f"🔍 查询视频任务状态: {endpoint}")

        response = requests.get(
            endpoint,
            headers=headers,
            timeout=timeout,
            verify=False
        )

        return response

    except requests.exceptions.SSLError as e:
        _log_warning(f"SSL错误，尝试忽略SSL验证: {e}")
        try:
            # 尝试使用更宽松的SSL设置
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=timeout,
                verify=False
            )
            return response
        except Exception as e2:
            _log_error(f"查询视频任务状态失败（SSL重试后）: {e2}")
            return None
    except Exception as e:
        _log_error(f"查询视频任务状态失败: {e}")
        return None

class SeedReam4APINode:
    """SeedReam4API 节点类"""
    
    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = list(mirror_sites.keys())
        
        if not mirror_options:
            mirror_options = ["comfly", "t8_mirror"]
        
        # 保留前三个镜像站选项（包括火山引擎）
        mirror_options = [opt for opt in mirror_options if opt in ["comfly", "t8_mirror", "volcengine"]]
        
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A beautiful landscape"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "model": (["doubao-seedream-4-0-250828"], {"default": "doubao-seedream-4-0-250828"}),
                "response_format": (["url", "b64_json"], {"default": "url"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9", "9:21", "Custom"], {"default": "1:1"}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "api_key": ("STRING", {"default": ""}),
                "max_images": ("INT", {"default": 1, "min": 1, "max": 15, "step": 1}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "watermark": ("BOOLEAN", {"default": True}),
                "stream": ("BOOLEAN", {"default": False}),
                "tail_on_partial": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "image1": ("IMAGE",),
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
                "sequential_image_generation": (["disabled", "auto"], {"default": "disabled"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "response", "image_url")
    FUNCTION = "generate_image"
    CATEGORY = "Ken-Chen/Doubao"
    
    def __init__(self):
        self.config = get_seedream4_config()
        self.timeout = self.config.get('timeout', 900)
        self.max_retries = self.config.get('max_retries', 3)
        self.size_mapping = self.config.get('size_mapping', {})
        self.resolution_factors = self.config.get('resolution_factors', {})
    
    def get_headers(self, api_key):
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def generate_image(self, prompt, mirror_site, model, response_format="url", resolution="1K",
                      aspect_ratio="1:1", width=1024, height=1024, api_key="",
                      max_images=1, seed=-1, watermark=True, stream=False, tail_on_partial=True,
                      image1=None, image2=None, image3=None, image4=None, image5=None,
                      sequential_image_generation="disabled"):
        """生成图像"""
        
        # 获取镜像站配置
        site_config = get_mirror_site_config(mirror_site)
        api_url = site_config.get("url", "").strip()
        api_format = site_config.get("api_format", "comfly")
        
        # 使用镜像站的API key（如果提供了的话）
        if site_config.get("api_key") and not api_key.strip():
            api_key = site_config["api_key"]
            _log_info(f"🔑 自动使用镜像站API Key: {api_key[:8]}...")
        
        if not api_key.strip():
            error_message = "API key not found"
            _log_error(error_message)
            blank_tensor = create_blank_tensor()
            return (blank_tensor, error_message, "")
        
        if not validate_api_url(api_url):
            error_message = "Invalid API URL"
            _log_error(error_message)
            blank_tensor = create_blank_tensor()
            return (blank_tensor, error_message, "")
        
        _log_info(f"🔗 使用镜像站: {mirror_site} ({api_url})")
        
        try:
            # 计算最终尺寸
            if aspect_ratio == "Custom":
                scale_factor = self.resolution_factors.get(resolution, 1)
                scaled_width = int(width * scale_factor)
                scaled_height = int(height * scale_factor)
                final_size = f"{scaled_width}x{scaled_height}"
                _log_info(f"使用自定义尺寸: {final_size}")
            else:
                if resolution in self.size_mapping and aspect_ratio in self.size_mapping[resolution]:
                    final_size = self.size_mapping[resolution][aspect_ratio]
                else:
                    final_size = "1024x1024"
                    _log_warning(f"未找到 {resolution} 和 {aspect_ratio} 的组合，使用 {final_size}")
            
            # 构建请求载荷
            payload = {
                "model": model,
                "prompt": prompt,
                "response_format": response_format,
                "size": final_size,
                "watermark": watermark,
                "stream": stream,
                "tail_on_partial": tail_on_partial
            }
            
            if sequential_image_generation == "auto":
                payload["sequential_image_generation"] = sequential_image_generation
                payload["n"] = max_images
                
            if seed != -1:
                payload["seed"] = seed
            
            # 处理输入图像
            image_urls = []
            for img in [image1, image2, image3, image4, image5]:
                if img is not None:
                    batch_size = img.shape[0]
                    for i in range(batch_size):
                        single_image = img[i:i+1]
                        image_base64 = image_to_base64(single_image)
                        if image_base64:
                            image_urls.append(image_base64)
            
            if image_urls:
                payload["image"] = image_urls
            
            # 根据API格式调用相应的API
            response = None
            for attempt in range(self.max_retries):
                try:
                    if api_format == "comfly":
                        response = call_comfly_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "openai":
                        response = call_openai_compatible_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "api4gpt":
                        response = call_api4gpt_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "openrouter":
                        response = call_openrouter_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "volcengine":
                        response = call_volcengine_api(api_url, api_key, payload, self.timeout)
                    else:
                        response = call_comfly_api(api_url, api_key, payload, self.timeout)
                    
                    if response and response.status_code == 200:
                        break
                    elif response:
                        _log_warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {response.status_code} - {response.text}")
                    else:
                        _log_warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): 无响应")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                        
                except Exception as e:
                    _log_warning(f"API调用异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
            
            if not response or response.status_code != 200:
                error_message = f"API Error: {response.status_code if response else 'No response'} - {response.text if response else 'Connection failed'}"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            result = response.json()
            # 只记录响应的基本结构，避免显示大量base64数据
            if "choices" in result:
                _log_info("🔍 API响应格式: T8图像编辑格式 (choices)")
            elif "data" in result:
                _log_info(f"🔍 API响应格式: 标准图像生成格式 (data, {len(result['data'])} 项)")
            else:
                _log_info(f"🔍 API响应格式: 未知格式，包含键: {list(result.keys())}")

            # 检查是否是T8图像编辑响应（chat/completions格式）
            if "choices" in result and result["choices"]:
                # T8图像编辑响应格式
                _log_info("🎨 检测到T8图像编辑响应格式")
                choice = result["choices"][0]
                content = choice.get("message", {}).get("content", "")

                # 从响应中提取图像URL（T8图像编辑会在文本中返回图像URL）
                import re

                # 尝试多种URL提取模式
                image_urls_found = []

                # 模式1：Markdown格式 ![alt](url)
                markdown_pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
                markdown_urls = re.findall(markdown_pattern, content)
                image_urls_found.extend(markdown_urls)

                # 模式2：直接的图像URL
                direct_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp)'
                direct_urls = re.findall(direct_pattern, content)
                image_urls_found.extend(direct_urls)

                # 模式3：任何包含图像相关域名的URL（更宽泛的匹配）
                domain_pattern = r'https?://[^\s<>"\)]+(?:tos-cn-beijing\.volces\.com|ark-content-generation)[^\s<>"\)]*'
                domain_urls = re.findall(domain_pattern, content)
                image_urls_found.extend(domain_urls)

                # 去重
                image_urls_found = list(set(image_urls_found))

                _log_info(f"🔍 提取到的图像URL: {image_urls_found}")

                generated_images = []
                image_urls = []

                if image_urls_found:
                    for image_url in image_urls_found:
                        try:
                            img_response = requests.get(image_url, timeout=60)
                            if img_response.status_code == 200:
                                image = Image.open(io.BytesIO(img_response.content))
                                generated_images.append(image)
                                image_urls.append(image_url)
                                _log_info(f"✅ 成功下载T8编辑图像: {image_url}")
                        except Exception as e:
                            _log_warning(f"下载T8编辑图像失败: {e}")
                            continue

                if not generated_images:
                    error_message = f"T8图像编辑响应中未找到有效图像URL。响应内容: {content}"
                    _log_error(error_message)
                    blank_tensor = create_blank_tensor()
                    return (blank_tensor, error_message, content)

            elif "data" in result and result["data"]:
                # 标准图像生成响应格式
                _log_info("🖼️ 检测到标准图像生成响应格式")
                generated_images = []
                image_urls = []

                for item in result["data"]:
                    if response_format == "url":
                        image_url = item.get("url")
                        if not image_url:
                            continue

                        try:
                            img_response = requests.get(image_url, timeout=60)
                            if img_response.status_code == 200:
                                image = Image.open(io.BytesIO(img_response.content))
                                generated_images.append(image)
                                image_urls.append(image_url)
                        except Exception as e:
                            _log_warning(f"下载图像失败: {e}")
                            continue

                    elif response_format == "b64_json":
                        b64_data = item.get("b64_json")
                        if not b64_data:
                            continue

                        try:
                            image_data = base64.b64decode(b64_data)
                            image = Image.open(io.BytesIO(image_data))
                            generated_images.append(image)
                            image_urls.append("base64_data")
                        except Exception as e:
                            _log_warning(f"解码base64图像失败: {e}")
                            continue
            else:
                error_message = "响应格式不支持或无图像数据"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            if not generated_images:
                error_message = "No valid images generated"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            # 转换为tensor - 使用ComfyUI_Comfly的方式
            image_tensors = []
            for i, img in enumerate(generated_images):
                _log_info(f"🔍 处理图像 {i+1}: 原始尺寸 {img.size}, 模式 {img.mode}")
                
                # 使用pil2tensor函数，格式为[1, H, W, 3]
                tensor = pil2tensor(img)
                _log_info(f"🔍 tensor形状: {tensor.shape}, 值范围: {tensor.min().item():.3f} 到 {tensor.max().item():.3f}")
                
                # 检查tensor是否有异常
                if len(tensor.shape) != 4 or tensor.shape[-1] != 3:
                    _log_error(f"❌ 图像 {i+1} tensor形状异常: {tensor.shape}")
                    continue
                
                image_tensors.append(tensor)
            
            # 检查是否有有效的图像tensor
            if not image_tensors:
                _log_error("❌ 没有有效的图像tensor，使用空白tensor")
                final_tensor = create_blank_tensor()
            else:
                # 堆叠所有图像，格式为 [batch, H, W, 3] - 参考ComfyUI_Comfly
                if len(image_tensors) == 1:
                    final_tensor = image_tensors[0]
                else:
                    final_tensor = torch.cat(image_tensors, dim=0)
                _log_info(f"🔍 堆叠后tensor形状: {final_tensor.shape}")
            
            # 调试信息
            _log_info(f"🔍 最终tensor形状: {final_tensor.shape}")
            _log_info(f"🔍 最终tensor数据类型: {final_tensor.dtype}")
            _log_info(f"🔍 最终tensor值范围: {final_tensor.min().item():.3f} 到 {final_tensor.max().item():.3f}")
            
            # 检查tensor是否有异常值
            if torch.isnan(final_tensor).any():
                _log_error("❌ tensor包含NaN值")
            if torch.isinf(final_tensor).any():
                _log_error("❌ tensor包含无穷值")
            
            # 检查每个维度的值
            for i in range(min(final_tensor.shape[0], 2)):  # 限制输出数量
                for j in range(min(final_tensor.shape[1], 3)):  # 限制输出数量
                    _log_info(f"🔍 图像{i}通道{j}形状: {final_tensor[i,j].shape}, 值范围: {final_tensor[i,j].min().item():.3f} 到 {final_tensor[i,j].max().item():.3f}")
            
            # 特别检查是否有异常的维度
            if final_tensor.shape[1] == 1 and final_tensor.shape[2] > 1000:
                _log_error(f"❌ 检测到异常tensor形状: {final_tensor.shape} - 这可能导致PIL错误")
                _log_error(f"❌ 通道数: {final_tensor.shape[1]}, 高度: {final_tensor.shape[2]}, 宽度: {final_tensor.shape[3]}")
                # 强制修复
                _log_info("🔧 强制修复tensor格式...")
                final_tensor = create_blank_tensor()
            
            # 确保tensor格式正确
            if len(final_tensor.shape) != 4:
                _log_error(f"❌ tensor维度错误: {final_tensor.shape}, 应该是4维 (batch, channels, height, width)")
                # 尝试修复
                if len(final_tensor.shape) == 3:
                    final_tensor = final_tensor.unsqueeze(0)
                    _log_info(f"🔧 修复后tensor形状: {final_tensor.shape}")
            
            # 使用ensure_tensor_format确保tensor格式完全正确
            final_tensor = ensure_tensor_format(final_tensor)
            _log_info(f"🔧 最终tensor格式验证完成: {final_tensor.shape}")
            
            # 最终强制检查 - 确保tensor格式为[batch, H, W, 3]
            if (len(final_tensor.shape) != 4 or 
                final_tensor.shape[-1] != 3):
                _log_error(f"❌ 最终检查失败，tensor格式仍然不正确: {final_tensor.shape}")
                _log_info("🔧 使用空白tensor替代")
                final_tensor = create_blank_tensor()
            
            # 最终验证tensor是否可以被PIL处理
            try:
                # 尝试转换为numpy数组来验证 - 格式为[H, W, 3]
                test_array = final_tensor[0].cpu().numpy()
                test_array = np.clip(test_array, 0, 1)
                test_array = (test_array * 255).astype(np.uint8)
                _log_info(f"🔍 PIL兼容性测试通过: {test_array.shape}")
            except Exception as e:
                _log_error(f"❌ PIL兼容性测试失败: {e}")
                _log_info("🔧 使用空白tensor替代")
                final_tensor = create_blank_tensor()
            
            response_text = f"Successfully generated {len(generated_images)} image(s)"
            image_url_text = image_urls[0] if image_urls else ""
            
            _log_info(f"✅ 成功生成 {len(generated_images)} 张图像")
            return (final_tensor, response_text, image_url_text)
            
        except Exception as e:
            error_message = f"Generation failed: {str(e)}"
            _log_error(error_message)
            blank_tensor = ensure_tensor_format(create_blank_tensor())
            _log_info(f"🔍 错误处理tensor形状: {blank_tensor.shape}")
            
            return (blank_tensor, error_message, "")

class SeedReam4APISingleNode:
    """SeedReam4API 单图像生成及编辑节点类"""
    
    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = list(mirror_sites.keys())
        
        if not mirror_options:
            mirror_options = ["comfly", "t8_mirror"]
        
        # 保留前三个镜像站选项（包括火山引擎）
        mirror_options = [opt for opt in mirror_options if opt in ["comfly", "t8_mirror", "volcengine"]]
        
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A beautiful landscape"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "model": (["doubao-seedream-4-0-250828"], {"default": "doubao-seedream-4-0-250828"}),
                "response_format": (["url", "b64_json"], {"default": "url"}),
                "resolution": (["1K", "2K", "4K"], {"default": "1K"}),
                "aspect_ratio": (["1:1", "4:3", "3:4", "16:9", "9:16", "2:3", "3:2", "21:9", "9:21", "Custom"], {"default": "1:1"}),
                "width": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "height": ("INT", {"default": 1024, "min": 64, "max": 8192, "step": 1}),
                "api_key": ("STRING", {"default": ""}),
                "max_images": ("INT", {"default": 1, "min": 1, "max": 15, "step": 1}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
                "watermark": ("BOOLEAN", {"default": True}),
                "stream": ("BOOLEAN", {"default": False}),
                "tail_on_partial": ("BOOLEAN", {"default": True}),
            },
            "optional": {
                "image": ("IMAGE",),  # 单图像输入，用于图像编辑
                "sequential_image_generation": (["disabled", "auto"], {"default": "disabled"}),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image", "response", "image_url")
    FUNCTION = "generate_image"
    CATEGORY = "Ken-Chen/Doubao"
    
    def __init__(self):
        self.config = get_seedream4_config()
        self.timeout = self.config.get('timeout', 900)
        self.max_retries = self.config.get('max_retries', 3)
        self.size_mapping = self.config.get('size_mapping', {})
        self.resolution_factors = self.config.get('resolution_factors', {})
    
    def get_headers(self, api_key):
        """获取请求头"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def generate_image(self, prompt, mirror_site, model, response_format="url", resolution="1K",
                      aspect_ratio="1:1", width=1024, height=1024, api_key="",
                      max_images=1, seed=-1, watermark=True, stream=False, tail_on_partial=True,
                      image=None, sequential_image_generation="disabled"):
        """生成图像 - 单图像版本"""
        
        # 获取镜像站配置
        site_config = get_mirror_site_config(mirror_site)
        api_url = site_config.get("url", "").strip()
        api_format = site_config.get("api_format", "comfly")
        
        # 使用镜像站的API key（如果提供了的话）
        if site_config.get("api_key") and not api_key.strip():
            api_key = site_config["api_key"]
            _log_info(f"🔑 自动使用镜像站API Key: {api_key[:8]}...")
        
        if not api_key.strip():
            error_message = "API key not found"
            _log_error(error_message)
            blank_tensor = create_blank_tensor()
            return (blank_tensor, error_message, "")
        
        if not validate_api_url(api_url):
            error_message = "Invalid API URL"
            _log_error(error_message)
            blank_tensor = create_blank_tensor()
            return (blank_tensor, error_message, "")
        
        _log_info(f"🔗 使用镜像站: {mirror_site} ({api_url})")
        
        try:
            # 计算最终尺寸
            if aspect_ratio == "Custom":
                scale_factor = self.resolution_factors.get(resolution, 1)
                scaled_width = int(width * scale_factor)
                scaled_height = int(height * scale_factor)
                final_size = f"{scaled_width}x{scaled_height}"
                _log_info(f"使用自定义尺寸: {final_size}")
            else:
                if resolution in self.size_mapping and aspect_ratio in self.size_mapping[resolution]:
                    final_size = self.size_mapping[resolution][aspect_ratio]
                else:
                    final_size = "1024x1024"
                    _log_warning(f"未找到 {resolution} 和 {aspect_ratio} 的组合，使用 {final_size}")
            
            # 构建请求载荷
            payload = {
                "model": model,
                "prompt": prompt,
                "response_format": response_format,
                "size": final_size,
                "watermark": watermark,  # 始终添加watermark参数
                "stream": stream,  # 始终添加stream参数
                "tail_on_partial": tail_on_partial  # 始终添加tail_on_partial参数
            }
            
            if sequential_image_generation == "auto":
                payload["sequential_image_generation"] = sequential_image_generation
                payload["n"] = max_images
                
            if seed != -1:
                payload["seed"] = seed
            
            # 处理单图像输入
            if image is not None:
                _log_info(f"🔍 处理输入图像: {image.shape}")
                image_base64 = image_to_base64(image)
                if image_base64:
                    base64_size_mb = len(image_base64) / (1024 * 1024)
                    _log_info(f"🔧 添加图像到请求载荷 (base64: {len(image_base64):,} 字符, {base64_size_mb:.2f}MB)")
                    payload["image"] = [image_base64]
                    _log_info(f"🔍 单图节点图像数据: 数组长度={len(payload['image'])}, base64长度={len(image_base64)}")
                else:
                    _log_error("❌ 图像转换为base64失败")
            
            # 根据API格式调用相应的API
            _log_info(f"🔍 单图节点API调用详情:")
            _log_info(f"   - API格式: {api_format}")
            _log_info(f"   - API地址: {api_url}")
            _log_info(f"   - 模型: {payload.get('model', 'N/A')}")
            _log_info(f"   - 是否包含图像: {'image' in payload and bool(payload.get('image'))}")
            if 'image' in payload and payload.get('image'):
                _log_info(f"   - 图像数量: {len(payload['image'])}")

            response = None
            for attempt in range(self.max_retries):
                try:
                    if api_format == "comfly":
                        response = call_comfly_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "openai":
                        response = call_openai_compatible_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "api4gpt":
                        response = call_api4gpt_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "openrouter":
                        response = call_openrouter_api(api_url, api_key, payload, self.timeout)
                    elif api_format == "volcengine":
                        response = call_volcengine_api(api_url, api_key, payload, self.timeout)
                    else:
                        response = call_comfly_api(api_url, api_key, payload, self.timeout)
                    
                    if response and response.status_code == 200:
                        break
                    elif response:
                        error_text = response.text[:500] if response.text else "无错误信息"
                        _log_warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {response.status_code}")
                        _log_warning(f"错误详情: {error_text}")

                        # 检查是否是图像过大的错误
                        if "too large" in error_text.lower() or "payload too large" in error_text.lower():
                            _log_error("❌ 图像数据过大，请尝试使用较小的图像")
                        elif "invalid" in error_text.lower() and "image" in error_text.lower():
                            _log_error("❌ 图像格式无效，请检查输入图像")
                    else:
                        _log_warning(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): 无响应")
                    
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # 指数退避
                        
                except Exception as e:
                    _log_warning(f"API调用异常 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)
            
            if not response or response.status_code != 200:
                error_message = f"API Error: {response.status_code if response else 'No response'} - {response.text if response else 'Connection failed'}"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            result = response.json()
            # 只记录响应的基本结构，避免显示大量base64数据
            if "choices" in result:
                _log_info("🔍 API响应格式: T8图像编辑格式 (choices)")
            elif "data" in result:
                _log_info(f"🔍 API响应格式: 标准图像生成格式 (data, {len(result['data'])} 项)")
            else:
                _log_info(f"🔍 API响应格式: 未知格式，包含键: {list(result.keys())}")

            # 检查是否是T8图像编辑响应（chat/completions格式）
            if "choices" in result and result["choices"]:
                # T8图像编辑响应格式
                _log_info("🎨 检测到T8图像编辑响应格式")
                choice = result["choices"][0]
                content = choice.get("message", {}).get("content", "")

                # 从响应中提取图像URL（T8图像编辑会在文本中返回图像URL）
                import re

                # 尝试多种URL提取模式
                image_urls_found = []

                # 模式1：Markdown格式 ![alt](url)
                markdown_pattern = r'!\[.*?\]\((https?://[^\s\)]+)\)'
                markdown_urls = re.findall(markdown_pattern, content)
                image_urls_found.extend(markdown_urls)

                # 模式2：直接的图像URL
                direct_pattern = r'https?://[^\s<>"]+\.(?:jpg|jpeg|png|gif|webp)'
                direct_urls = re.findall(direct_pattern, content)
                image_urls_found.extend(direct_urls)

                # 模式3：任何包含图像相关域名的URL（更宽泛的匹配）
                domain_pattern = r'https?://[^\s<>"\)]+(?:tos-cn-beijing\.volces\.com|ark-content-generation)[^\s<>"\)]*'
                domain_urls = re.findall(domain_pattern, content)
                image_urls_found.extend(domain_urls)

                # 去重
                image_urls_found = list(set(image_urls_found))

                _log_info(f"🔍 提取到的图像URL: {image_urls_found}")

                generated_images = []
                image_urls = []

                if image_urls_found:
                    for image_url in image_urls_found:
                        try:
                            img_response = requests.get(image_url, timeout=60)
                            if img_response.status_code == 200:
                                image = Image.open(io.BytesIO(img_response.content))
                                generated_images.append(image)
                                image_urls.append(image_url)
                                _log_info(f"✅ 成功下载T8编辑图像: {image_url}")
                        except Exception as e:
                            _log_warning(f"下载T8编辑图像失败: {e}")
                            continue

                if not generated_images:
                    error_message = f"T8图像编辑响应中未找到有效图像URL。响应内容: {content}"
                    _log_error(error_message)
                    blank_tensor = create_blank_tensor()
                    return (blank_tensor, error_message, content)

            elif "data" in result and result["data"]:
                # 标准图像生成响应格式
                _log_info("🖼️ 检测到标准图像生成响应格式")
                generated_images = []
                image_urls = []

                for item in result["data"]:
                    if response_format == "url":
                        image_url = item.get("url")
                        if not image_url:
                            continue

                        try:
                            img_response = requests.get(image_url, timeout=60)
                            if img_response.status_code == 200:
                                image = Image.open(io.BytesIO(img_response.content))
                                generated_images.append(image)
                                image_urls.append(image_url)
                        except Exception as e:
                            _log_warning(f"下载图像失败: {e}")
                            continue

                    elif response_format == "b64_json":
                        b64_data = item.get("b64_json")
                        if not b64_data:
                            continue

                        try:
                            image_data = base64.b64decode(b64_data)
                            image = Image.open(io.BytesIO(image_data))
                            generated_images.append(image)
                            image_urls.append("base64_data")
                        except Exception as e:
                            _log_warning(f"解码base64图像失败: {e}")
                            continue
            else:
                error_message = "响应格式不支持或无图像数据"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            if not generated_images:
                error_message = "No valid images generated"
                _log_error(error_message)
                blank_tensor = create_blank_tensor()
                return (blank_tensor, error_message, "")
            
            # 转换为tensor - 使用ComfyUI_Comfly的方式
            image_tensors = []
            for i, img in enumerate(generated_images):
                _log_info(f"🔍 处理图像 {i+1}: 原始尺寸 {img.size}, 模式 {img.mode}")
                
                # 使用pil2tensor函数，格式为[1, H, W, 3]
                tensor = pil2tensor(img)
                _log_info(f"🔍 tensor形状: {tensor.shape}, 值范围: {tensor.min().item():.3f} 到 {tensor.max().item():.3f}")
                
                # 检查tensor是否有异常
                if len(tensor.shape) != 4 or tensor.shape[-1] != 3:
                    _log_error(f"❌ 图像 {i+1} tensor形状异常: {tensor.shape}")
                    continue
                
                image_tensors.append(tensor)
            
            # 检查是否有有效的图像tensor
            if not image_tensors:
                _log_error("❌ 没有有效的图像tensor，使用空白tensor")
                final_tensor = create_blank_tensor()
            else:
                # 堆叠所有图像，格式为 [batch, H, W, 3] - 参考ComfyUI_Comfly
                if len(image_tensors) == 1:
                    final_tensor = image_tensors[0]
                else:
                    final_tensor = torch.cat(image_tensors, dim=0)
                _log_info(f"🔍 堆叠后tensor形状: {final_tensor.shape}")
            
            # 调试信息
            _log_info(f"🔍 最终tensor形状: {final_tensor.shape}")
            _log_info(f"🔍 最终tensor数据类型: {final_tensor.dtype}")
            _log_info(f"🔍 最终tensor值范围: {final_tensor.min().item():.3f} 到 {final_tensor.max().item():.3f}")
            
            # 检查tensor是否有异常值
            if torch.isnan(final_tensor).any():
                _log_error("❌ tensor包含NaN值")
            if torch.isinf(final_tensor).any():
                _log_error("❌ tensor包含无穷值")
            
            # 检查每个维度的值
            for i in range(min(final_tensor.shape[0], 2)):  # 限制输出数量
                for j in range(min(final_tensor.shape[1], 3)):  # 限制输出数量
                    _log_info(f"🔍 图像{i}通道{j}形状: {final_tensor[i,j].shape}, 值范围: {final_tensor[i,j].min().item():.3f} 到 {final_tensor[i,j].max().item():.3f}")
            
            # 特别检查是否有异常的维度
            if final_tensor.shape[1] == 1 and final_tensor.shape[2] > 1000:
                _log_error(f"❌ 检测到异常tensor形状: {final_tensor.shape} - 这可能导致PIL错误")
                _log_error(f"❌ 通道数: {final_tensor.shape[1]}, 高度: {final_tensor.shape[2]}, 宽度: {final_tensor.shape[3]}")
                # 强制修复
                _log_info("🔧 强制修复tensor格式...")
                final_tensor = create_blank_tensor()
            
            # 确保tensor格式正确
            if len(final_tensor.shape) != 4:
                _log_error(f"❌ tensor维度错误: {final_tensor.shape}, 应该是4维 (batch, height, width, channels)")
                # 尝试修复
                if len(final_tensor.shape) == 3:
                    final_tensor = final_tensor.unsqueeze(0)
                    _log_info(f"🔧 修复后tensor形状: {final_tensor.shape}")
            
            # 使用ensure_tensor_format确保tensor格式完全正确
            final_tensor = ensure_tensor_format(final_tensor)
            _log_info(f"🔧 最终tensor格式验证完成: {final_tensor.shape}")
            
            # 最终强制检查 - 确保tensor格式为[batch, H, W, 3]
            if (len(final_tensor.shape) != 4 or 
                final_tensor.shape[-1] != 3):
                _log_error(f"❌ 最终检查失败，tensor格式仍然不正确: {final_tensor.shape}")
                _log_info("🔧 使用空白tensor替代")
                final_tensor = create_blank_tensor()
            
            # 最终验证tensor是否可以被PIL处理
            try:
                # 尝试转换为numpy数组来验证 - 格式为[H, W, 3]
                test_array = final_tensor[0].cpu().numpy()
                test_array = np.clip(test_array, 0, 1)
                test_array = (test_array * 255).astype(np.uint8)
                _log_info(f"🔍 PIL兼容性测试通过: {test_array.shape}")
            except Exception as e:
                _log_error(f"❌ PIL兼容性测试失败: {e}")
                _log_info("🔧 使用空白tensor替代")
                final_tensor = create_blank_tensor()
            
            response_text = f"Successfully generated {len(generated_images)} image(s)"
            image_url_text = image_urls[0] if image_urls else ""
            
            _log_info(f"✅ 成功生成 {len(generated_images)} 张图像")
            return (final_tensor, response_text, image_url_text)
            
        except Exception as e:
            error_message = f"Generation failed: {str(e)}"
            _log_error(error_message)
            blank_tensor = ensure_tensor_format(create_blank_tensor())
            _log_info(f"🔍 错误处理tensor形状: {blank_tensor.shape}")
            
            return (blank_tensor, error_message, "")

class DoubaoSeedanceVideoNode:
    """Doubao-Seedance视频生成节点"""

    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = list(mirror_sites.keys())

        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "A beautiful video scene"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "model": (["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"], {"default": "doubao-seedance-1-0-pro-250528"}),
                "video_mode": (["text_to_video", "image_to_video", "first_last_frame"], {"default": "text_to_video"}),
                "duration": (["3s", "5s", "10s", "12s"], {"default": "5s"}),
                "resolution": (["480p", "720p", "1080p"], {"default": "720p"}),
                "aspect_ratio": (["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"], {"default": "16:9"}),
                "fps": ([24, 30], {"default": 30}),
                "watermark": ("BOOLEAN", {"default": False}),
                "camera_fixed": ("BOOLEAN", {"default": False}),
                "api_key": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
            },
            "optional": {
                "input_image": ("IMAGE",),
                "first_frame": ("IMAGE",),
                "last_frame": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING", "VIDEO")
    RETURN_NAMES = ("video", "video_url", "response_text", "video_info", "AFVIDEO")
    FUNCTION = "generate_video"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 900  # 15分钟超时，视频生成需要更长时间
        self.max_retries = 3

    def generate_video(self, prompt, mirror_site, model, video_mode, duration, resolution, aspect_ratio, fps, watermark=False, camera_fixed=False, api_key="", seed=-1,
                      input_image=None, first_frame=None, last_frame=None):
        """生成视频"""

        # 获取镜像站配置
        site_config = get_mirror_site_config(mirror_site)
        api_url = site_config.get("url", "").strip()
        api_format = site_config.get("api_format", "comfly")

        # 强制修正T8镜像站的API格式（确保使用最新配置）
        if mirror_site == "t8_mirror" or "t8star.cn" in api_url:
            api_format = "volcengine"
            _log_info(f"🔧 强制修正T8镜像站API格式为: {api_format}")

        # 使用镜像站的API key（如果提供了的话）
        if site_config.get("api_key") and not api_key.strip():
            api_key = site_config["api_key"]
            _log_info(f"🔑 自动使用镜像站API Key: {api_key[:8]}...")

        if not api_key.strip():
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：未提供API Key", "", blank_video_path)

        if not api_url:
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：未配置API URL", "", blank_video_path)

        _log_info(f"🔗 使用镜像站: {mirror_site} ({api_url})")

        try:
            # 根据API格式构建不同的payload
            _log_info(f"🔍 API格式判断结果: {api_format}")
            _log_info(f"🔍 API URL: {api_url}")
            _log_info(f"🔍 是否包含t8star.cn: {'t8star.cn' in api_url}")

            if api_format == "volcengine":
                # 火山引擎使用content数组格式
                _log_info(f"🔧 构建火山引擎格式payload")

                # 根据官方文档构建文本内容，使用正确的参数格式
                if video_mode == "first_last_frame":
                    # 首尾帧模式：根据官方示例，只使用 --rs --dur --cf 参数
                    text_content = f"{prompt} --rs {resolution} --dur {duration.replace('s', '')} --cf {str(camera_fixed).lower()}"
                    if seed != -1:
                        text_content += f" --seed {seed}"
                    # 添加watermark参数
                    text_content += f" --wm {str(watermark).lower()}"
                    _log_info(f"🔧 首尾帧模式文本内容: {text_content}")
                else:
                    # 文生视频和图生视频模式：使用完整参数
                    text_content = f"{prompt} --rt {aspect_ratio} --dur {duration.replace('s', '')} --fps {fps} --rs {resolution}"
                    if seed != -1:
                        text_content += f" --seed {seed}"
                    # 添加watermark和camera_fixed参数
                    text_content += f" --wm {str(watermark).lower()} --cf {str(camera_fixed).lower()}"
                    _log_info(f"🔧 标准模式文本内容: {text_content}")

                content = [
                    {
                        "type": "text",
                        "text": text_content
                    }
                ]

                # 根据视频模式添加图像
                if video_mode == "image_to_video" and input_image is not None:
                    _log_info(f"🔍 图生视频模式: 输入图像 {input_image.shape}")

                    # 火山引擎API需要完整的Data URL格式（根据官方文档）
                    image_data_url = image_to_base64(input_image, return_data_url=True)
                    if image_data_url:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url
                            }
                        })
                        _log_info(f"🔧 添加输入图像到content (Data URL长度: {len(image_data_url)})")
                    else:
                        _log_error(f"❌ 图像Data URL编码失败")

                elif video_mode == "first_last_frame" and first_frame is not None and last_frame is not None:
                    _log_info(f"🔍 首尾帧模式: 首帧 {first_frame.shape}, 尾帧 {last_frame.shape}")
                    # 火山引擎API需要完整的Data URL格式
                    first_data_url = image_to_base64(first_frame, return_data_url=True)
                    last_data_url = image_to_base64(last_frame, return_data_url=True)
                    if first_data_url and last_data_url:
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": first_data_url
                            },
                            "role": "first_frame"  # 官方格式：首帧角色标识
                        })
                        content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": last_data_url
                            },
                            "role": "last_frame"   # 官方格式：尾帧角色标识
                        })
                        _log_info(f"🔧 添加首尾帧到content (首帧Data URL长度: {len(first_data_url)}, 尾帧Data URL长度: {len(last_data_url)})")

                # 根据官方文档，所有参数都在文本中指定，不需要顶层参数
                payload = {
                    "model": model,
                    "content": content
                }

            else:
                # Comfly/T8格式 - 根据错误信息，Comfly也使用content数组格式
                _log_info(f"🔧 构建Comfly/T8格式payload")

                if api_format == "comfly":
                    # 根据API文档，使用简单的格式
                    _log_info(f"🔧 使用Comfly格式构建payload")

                    # Comfly镜像站使用传统的分辨率标签，不支持像素格式
                    payload = {
                        "prompt": prompt,
                        "model": model,
                        "duration": int(duration.replace('s', '')),
                        "resolution": resolution,  # 使用原始分辨率标签如"720p"
                        "ratio": aspect_ratio,
                        "watermark": watermark
                    }

                    _log_info(f"🔧 Comfly使用传统分辨率格式: {resolution} + {aspect_ratio}")
                    _log_info(f"🔍 Comfly格式duration类型: {type(payload['duration'])}, 值: {payload['duration']}")

                    # T8镜像站需要特殊参数
                    if "t8star.cn" in api_url:
                        payload["01K3ZARVMSZ97JPXNWXBCJGG6K"] = ""  # T8必需参数
                        _log_info(f"🔧 为T8镜像站添加特殊参数")
                else:
                    # T8格式保持原有结构（这个分支不应该被T8镜像站使用）
                    _log_info(f"🔧 使用旧T8格式构建payload（不推荐）")
                    payload = {
                        "model": model,
                        "prompt": prompt,
                        "duration": duration,
                        "resolution": resolution,  # 使用原始分辨率标签
                        "ratio": aspect_ratio,
                        "watermark": watermark
                    }

                    _log_info(f"🔧 旧T8使用传统分辨率格式: {resolution} + {aspect_ratio}")
                    _log_info(f"🔍 旧T8格式duration类型: {type(payload['duration'])}, 值: {payload['duration']}")

                # 添加种子
                if seed != -1:
                    if api_format == "comfly":
                        # Comfly格式：种子添加到payload中
                        payload["seed"] = seed
                    else:
                        # 其他格式：种子添加到payload中
                        payload["seed"] = seed

                # 根据视频模式处理图像输入
                if video_mode == "image_to_video" and input_image is not None:
                    _log_info(f"🔍 图生视频模式: 输入图像 {input_image.shape}")

                    # 根据API格式选择合适的图像编码方式
                    if api_format == "comfly":
                        # Comfly格式：根据API文档，图生视频使用images数组（单张图片）
                        image_data = image_to_base64(input_image, return_data_url=True)
                        payload["images"] = [image_data]
                        _log_info(f"🔧 Comfly格式: 添加图生视频图像到images数组 (长度: {len(image_data) if image_data else 0})")
                    else:
                        # T8等其他格式：使用image字段
                        image_data = image_to_base64(input_image, return_data_url=True)
                        payload["image"] = [image_data]
                        _log_info(f"🔧 其他格式: 添加Data URL图像到载荷 (长度: {len(image_data) if image_data else 0})")

                    if not image_data:
                        _log_error(f"❌ 图像编码失败")

                elif video_mode == "first_last_frame" and first_frame is not None and last_frame is not None:
                    _log_info(f"🔍 首尾帧模式: 首帧 {first_frame.shape}, 尾帧 {last_frame.shape}")

                    # 根据API格式选择合适的图像编码方式
                    if api_format == "comfly":
                        # Comfly格式：使用images数组格式，第一个元素是首帧，第二个元素是尾帧
                        first_data = image_to_base64(first_frame, return_data_url=True)
                        last_data = image_to_base64(last_frame, return_data_url=True)

                        if first_data and last_data:
                            # 根据Comfly API文档，首尾帧使用images数组
                            payload["images"] = [first_data, last_data]
                            _log_info(f"🔧 Comfly格式: 使用images数组格式添加首尾帧")
                        else:
                            _log_error(f"❌ Comfly首尾帧编码失败")
                    else:
                        # T8等其他格式：使用完整的Data URL格式
                        first_data = image_to_base64(first_frame, return_data_url=True)
                        last_data = image_to_base64(last_frame, return_data_url=True)
                        payload["first_frame"] = first_data
                        payload["last_frame"] = last_data
                        _log_info(f"🔧 其他格式: 添加Data URL首尾帧到载荷")

                    if first_data and last_data:
                        _log_info(f"🔍 首帧数据长度: {len(first_data)}, 尾帧数据长度: {len(last_data)}")
                    else:
                        _log_error(f"❌ 首尾帧编码失败")

                elif video_mode == "text_to_video":
                    _log_info(f"🔍 文生视频模式")

            _log_info(f"🔍 视频生成详情:")
            _log_info(f"   - API格式: {api_format}")
            _log_info(f"   - API地址: {api_url}")
            _log_info(f"   - 模型: {model}")
            _log_info(f"   - 视频模式: {video_mode}")
            _log_info(f"   - 时长: {duration}")
            _log_info(f"   - 分辨率: {resolution}")
            _log_info(f"   - 帧率: {fps}")

            # 调用视频生成API
            _log_info(f"🔍 最终payload内容: {list(payload.keys())}")
            if "api_platform" in payload:
                _log_info(f"🔍 api_platform参数: {payload['api_platform']}")
            else:
                _log_info(f"⚠️ payload中缺少api_platform参数")

            response = None
            for attempt in range(self.max_retries):
                try:
                    response = call_video_api(api_url, api_key, payload, api_format, self.timeout)

                    if response and response.status_code in [200, 201, 202]:
                        break
                    else:
                        error_msg = response.text if response else "无响应"
                        _log_warning(f"视频API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {error_msg}")

                except Exception as e:
                    _log_warning(f"视频API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")

                if attempt < self.max_retries - 1:
                    time.sleep(2)  # 重试前等待2秒

            if not response or response.status_code not in [200, 201, 202]:
                error_msg = f"API Error: {response.text if response else 'No response'} - Connection failed"
                _log_error(error_msg)
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                return (blank_video, "", f"❌ {error_msg}", "", blank_video_path)

            # 解析响应
            try:
                result = response.json()
                _log_info(f"🔍 视频API响应格式: {type(result)}")
                _log_info(f"🔍 视频API响应内容: {str(result)[:200]}...")

                # 检查是否是异步任务响应
                task_id = None
                if "task_id" in result:
                    task_id = result["task_id"]
                elif "id" in result:
                    task_id = result["id"]
                elif "data" in result and isinstance(result["data"], dict) and "task_id" in result["data"]:
                    task_id = result["data"]["task_id"]

                if task_id:
                    _log_info(f"🔍 检测到异步任务，任务ID: {task_id}")
                    _log_info(f"⏳ 开始轮询任务状态...")

                    # 轮询任务状态 - 优化轮询策略
                    max_polls = 90  # 最多轮询90次（15分钟）
                    poll_interval = 10  # 每10秒查询一次

                    for poll_count in range(max_polls):
                        _log_info(f"🔍 轮询任务状态 ({poll_count + 1}/{max_polls})")

                        status_response = call_video_task_status(api_url, api_key, task_id, api_format)

                        if status_response and status_response.status_code == 200:
                            status_result = status_response.json()
                            _log_info(f"🔍 任务状态响应: {str(status_result)[:200]}...")

                            # 检查任务状态
                            status = status_result.get("status", "unknown")
                            _log_info(f"🔍 当前任务状态: '{status}' (类型: {type(status)})")

                            if status.lower() in ["completed", "success", "finished", "succeeded"] or status in ["SUCCESS", "COMPLETED", "FINISHED", "SUCCEEDED"]:
                                # 任务完成，提取视频URL
                                _log_info(f"🎉 任务完成！完整响应: {status_result}")
                                video_url = ""

                                # 尝试多种可能的URL字段位置
                                if "data" in status_result:
                                    data = status_result["data"]
                                    _log_info(f"🔍 data字段内容: {data}")
                                    if isinstance(data, list) and len(data) > 0:
                                        video_data = data[0]
                                    else:
                                        video_data = data

                                    if "url" in video_data:
                                        video_url = video_data["url"]
                                    elif "video_url" in video_data:
                                        video_url = video_data["video_url"]
                                    elif "output_url" in video_data:
                                        video_url = video_data["output_url"]
                                    elif "output" in video_data:
                                        video_url = video_data["output"]

                                # 检查content字段（T8镜像站格式）
                                if not video_url and "content" in status_result:
                                    content = status_result["content"]
                                    _log_info(f"🔍 content字段内容: {content}")
                                    if "video_url" in content:
                                        video_url = content["video_url"]
                                    elif "url" in content:
                                        video_url = content["url"]

                                # 直接在根级别查找URL
                                if not video_url:
                                    if "url" in status_result:
                                        video_url = status_result["url"]
                                    elif "video_url" in status_result:
                                        video_url = status_result["video_url"]
                                    elif "output_url" in status_result:
                                        video_url = status_result["output_url"]
                                    elif "result_url" in status_result:
                                        video_url = status_result["result_url"]

                                _log_info(f"🔍 提取到的视频URL: {video_url}")

                                if video_url:
                                    _log_info(f"✅ 视频生成成功: {video_url}")

                                    # 下载视频文件并转换为张量
                                    video_path = download_video_from_url(video_url)
                                    if video_path:
                                        _log_info(f"🎬 开始转换视频为ComfyUI对象...")
                                        video_obj = video_to_comfyui_video(video_path)
                                        if video_obj is not None:
                                            video_info = f"模型: {model}, 模式: {video_mode}, 时长: {duration}, 分辨率: {resolution}, 宽高比: {aspect_ratio}, 帧率: {fps}fps, 任务ID: {task_id}"
                                            return (video_obj, video_url, "✅ 视频生成成功", video_info, video_path)
                                        else:
                                            _log_error("❌ 视频转换失败")
                                            blank_video = create_blank_video_object()
                                            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                            return (blank_video, video_url, "⚠️ 视频生成成功但转换失败", f"URL: {video_url}", blank_video_path)
                                    else:
                                        _log_error("❌ 视频下载失败")
                                        blank_video = create_blank_video_object()
                                        blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                        return (blank_video, video_url, "⚠️ 视频生成成功但下载失败", f"URL: {video_url}", blank_video_path)
                                else:
                                    _log_error("❌ 任务完成但未找到视频URL")
                                    blank_video = create_blank_video_object()
                                    blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                    return (blank_video, "", "❌ 任务完成但未找到视频URL", str(status_result), blank_video_path)

                            elif status in ["failed", "error"]:
                                error_msg = status_result.get("error", "任务失败")
                                _log_error(f"❌ 视频生成任务失败: {error_msg}")
                                blank_video = create_blank_video_object()
                                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                return (blank_video, "", f"❌ 任务失败: {error_msg}", str(status_result), blank_video_path)

                            elif status.lower() in ["running", "processing", "pending", "queued", "not_start"] or status in ["RUNNING", "PROCESSING", "PENDING", "QUEUED", "NOT_START"]:
                                _log_info(f"⏳ 任务进行中，状态: {status}")
                                time.sleep(poll_interval)
                                continue

                            else:
                                _log_warning(f"⚠️ 未知任务状态: {status}")
                                time.sleep(poll_interval)
                                continue

                        else:
                            _log_warning(f"⚠️ 查询任务状态失败")
                            time.sleep(poll_interval)

                    # 轮询超时
                    _log_error("❌ 任务轮询超时")
                    blank_video = create_blank_video_object()
                    blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                    return (blank_video, "", "❌ 视频生成超时，请稍后查看", f"任务ID: {task_id}", blank_video_path)

                else:
                    # 同步响应，直接提取视频URL
                    video_url = ""
                    if "data" in result and len(result["data"]) > 0:
                        video_data = result["data"][0]
                        if "url" in video_data:
                            video_url = video_data["url"]
                        elif "video_url" in video_data:
                            video_url = video_data["video_url"]

                    if video_url:
                        _log_info(f"✅ 视频生成成功: {video_url}")

                        # 下载视频文件并转换为张量
                        video_path = download_video_from_url(video_url)
                        if video_path:
                            _log_info(f"🎬 开始转换视频为张量...")
                            video_obj = video_to_comfyui_video(video_path)
                            if video_obj is not None:
                                video_info = f"模型: {model}, 模式: {video_mode}, 时长: {duration}, 分辨率: {resolution}, 宽高比: {aspect_ratio}, 帧率: {fps}fps"
                                return (video_obj, video_url, "✅ 视频生成成功", video_info, video_path)
                            else:
                                _log_error("❌ 视频转换失败")
                                blank_video = create_blank_video_object()
                                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                return (blank_video, video_url, "⚠️ 视频生成成功但转换失败", f"URL: {video_url}", blank_video_path)
                        else:
                            _log_error("❌ 视频下载失败")
                            blank_video = create_blank_video_object()
                            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                            return (blank_video, video_url, "⚠️ 视频生成成功但下载失败", f"URL: {video_url}", blank_video_path)
                    else:
                        _log_error("❌ 响应中未找到视频URL")
                        blank_video = create_blank_video_object()
                        blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                        return (blank_video, "", "❌ 响应中未找到视频URL", str(result), blank_video_path)

            except Exception as e:
                _log_error(f"解析视频响应失败: {e}")
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                return (blank_video, "", f"❌ 解析响应失败: {str(e)}", "", blank_video_path)

        except Exception as e:
            error_message = f"Video generation failed: {str(e)}"
            _log_error(error_message)
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", f"❌ {error_message}", "", blank_video_path)

class DoubaoSeedanceContinuousVideoNode:
    """Doubao-Seedance连续视频生成节点"""

    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = list(mirror_sites.keys())

        # 确保mirror_options不为空
        if not mirror_options:
            mirror_options = ["volcengine"]

        return {
            "required": {
                "base_prompt": ("STRING", {"multiline": True, "default": "一个美丽的场景"}),
                "prompts_text": ("STRING", {"multiline": True, "default": "女孩抱着狐狸，女孩睁开眼，温柔地看向镜头\n女孩和狐狸在草地上奔跑，阳光明媚\n女孩和狐狸坐在树下休息，女孩轻轻抚摸狐狸"}),
                "video_count": ("INT", {"default": 3, "min": 1, "max": 10}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "first_video_model": (["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"], {"default": "doubao-seedance-1-0-lite-t2v-250428"}),
                "subsequent_video_model": (["doubao-seedance-1-0-pro-250528", "doubao-seedance-1-0-lite-i2v-250428", "doubao-seedance-1-0-lite-t2v-250428"], {"default": "doubao-seedance-1-0-lite-i2v-250428"}),
                "duration": (["3s", "5s", "10s", "12s"], {"default": "5s"}),
                "resolution": (["480p", "720p", "1080p"], {"default": "720p"}),
                "aspect_ratio": (["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"], {"default": "16:9"}),
                "fps": ([24, 30], {"default": 30}),
                "watermark": ("BOOLEAN", {"default": False}),
                "camera_fixed": ("BOOLEAN", {"default": False}),
                "merge_videos": ("BOOLEAN", {"default": True}),
                "api_key": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
            },
            "optional": {
                "initial_image": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING", "VIDEO", "VIDEO")
    RETURN_NAMES = ("first_video", "all_video_urls", "response_text", "video_info", "AFVIDEO", "merged_video")
    FUNCTION = "generate_continuous_videos"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 900  # 15分钟超时
        self.max_retries = 3

    def generate_continuous_videos(self, base_prompt, prompts_text, video_count, mirror_site, first_video_model, subsequent_video_model, duration,
                                 resolution, aspect_ratio, fps, watermark=False, camera_fixed=False, merge_videos=True, api_key="", seed=-1, initial_image=None):
        """生成连续视频序列"""

        # 获取镜像站配置
        site_config = get_mirror_site_config(mirror_site)
        api_url = site_config.get("url", "").strip()
        api_format = site_config.get("api_format", "comfly")

        # 强制修正T8镜像站的API格式
        if mirror_site == "t8_mirror" or "t8star.cn" in api_url:
            api_format = "volcengine"
            _log_info(f"🔧 强制修正T8镜像站API格式为: {api_format}")

        # 强制修正Comfly镜像站的API格式（支持火山引擎格式）
        if mirror_site == "comfly_mirror" or "comfly.chat" in api_url:
            api_format = "volcengine"
            _log_info(f"🔧 强制修正Comfly镜像站API格式为: {api_format}")

        # 使用镜像站的API key（如果提供了的话）
        if site_config.get("api_key") and not api_key.strip():
            api_key = site_config["api_key"]
            _log_info(f"🔑 自动使用镜像站API Key: {api_key[:8]}...")

        if not api_key.strip():
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：未提供API Key", "", blank_video_path)

        if not api_url:
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：未配置API URL", "", blank_video_path)

        # 检查API格式支持 - 移除限制，支持所有镜像站
        _log_info(f"🔍 连续视频API格式: {api_format}")

        _log_info(f"🎬 开始生成连续视频序列: {video_count}个视频")
        _log_info(f"🔗 使用镜像站: {mirror_site} ({api_url})")

        try:
            # 解析提示词列表
            if prompts_text.strip():
                prompts = [p.strip() for p in prompts_text.split('\n') if p.strip()]
            else:
                # 如果没有提供具体提示词，使用基础提示词
                prompts = [f"{base_prompt} - 第{i+1}段" for i in range(video_count)]

            # 确保提示词数量匹配
            while len(prompts) < video_count:
                prompts.append(f"{base_prompt} - 第{len(prompts)+1}段")
            prompts = prompts[:video_count]

            _log_info(f"🔍 连续视频提示词列表: {prompts}")

            # 存储生成的视频信息
            video_urls = []
            video_infos = []
            response_texts = []
            current_image = initial_image

            for i, prompt in enumerate(prompts):
                _log_info(f"🎬 生成第{i+1}/{video_count}个视频: {prompt}")

                # 根据是第一个视频还是后续视频选择模型
                current_model = first_video_model if i == 0 else subsequent_video_model
                _log_info(f"🔧 使用模型: {current_model} ({'第一个视频' if i == 0 else '后续视频'})")

                # 调用单个视频生成
                video_result = self._generate_single_video_with_last_frame(
                    prompt, api_url, api_key, api_format, current_model, duration, resolution, aspect_ratio,
                    fps, watermark, camera_fixed, seed, current_image
                )

                if video_result is None:
                    _log_error(f"❌ 第{i+1}个视频生成失败")
                    break

                video_obj, video_url, response_text, video_info, last_frame_url = video_result

                if video_url and last_frame_url:
                    video_urls.append(video_url)
                    video_infos.append(video_info)
                    response_texts.append(response_text)

                    _log_info(f"✅ 第{i+1}个视频生成成功: {video_url}")

                    # 下载尾帧作为下一个视频的首帧
                    if i < len(prompts) - 1:  # 不是最后一个视频
                        current_image = self._download_last_frame_as_image(last_frame_url)
                        if current_image is None:
                            _log_error(f"❌ 无法下载第{i+1}个视频的尾帧，停止生成")
                            break
                        _log_info(f"🔄 已获取第{i+1}个视频的尾帧作为第{i+2}个视频的首帧")
                else:
                    _log_error(f"❌ 第{i+1}个视频生成失败，停止连续生成")
                    break

            # 返回结果
            if video_urls:
                # 返回第一个视频作为主要结果，其他信息合并
                combined_urls = "\n".join(video_urls)
                combined_info = f"连续生成了{len(video_urls)}个视频:\n" + "\n".join([f"视频{i+1}: {info}" for i, info in enumerate(video_infos)])
                combined_response = "\n".join(response_texts)

                # 返回第一个视频对象
                first_video = self._download_and_convert_video(video_urls[0])
                first_video_path = getattr(first_video, 'file_path', '') if first_video else ''

                # AFVIDEO使用路径包装器，与标准视频节点保持一致
                afvideo = create_video_path_wrapper(first_video_path) if first_video_path else create_blank_video_object()

                # 视频合并功能
                merged_video = None
                if merge_videos and len(video_urls) > 1:
                    _log_info(f"🎬 开始合并{len(video_urls)}个连续视频...")

                    # 下载所有视频文件
                    all_video_paths = []
                    for i, url in enumerate(video_urls):
                        try:
                            video_path = download_video_from_url(url)
                            if video_path:
                                all_video_paths.append(video_path)
                                _log_info(f"✅ 第{i+1}个视频下载成功: {video_path}")
                            else:
                                _log_warning(f"⚠️ 第{i+1}个视频下载失败")
                        except Exception as e:
                            _log_warning(f"⚠️ 第{i+1}个视频下载异常: {str(e)}")

                    # 使用ffmpeg合并视频
                    if len(all_video_paths) > 1:
                        merged_path = merge_videos_with_ffmpeg(all_video_paths)
                        if merged_path:
                            merged_video = video_to_comfyui_video(merged_path)
                            if merged_video:
                                merged_video.file_path = merged_path
                                _log_info(f"✅ 连续视频合并成功: {merged_path}")
                            else:
                                _log_error("❌ 合并视频转换为ComfyUI对象失败")
                        else:
                            _log_error("❌ 视频合并失败")
                    else:
                        _log_warning("⚠️ 可用视频数量不足，无法合并")

                # 如果没有合并或合并失败，使用第一个视频作为merged_video
                if not merged_video:
                    merged_video = first_video

                return (first_video, combined_urls, combined_response, combined_info, afvideo, merged_video)
            else:
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                afvideo = create_video_path_wrapper(blank_video_path) if blank_video_path else create_blank_video_object()
                return (blank_video, "", "❌ 连续视频生成失败", "", afvideo, blank_video)

        except Exception as e:
            error_message = f"连续视频生成失败: {str(e)}"
            _log_error(error_message)
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            afvideo = create_video_path_wrapper(blank_video_path) if blank_video_path else create_blank_video_object()
            return (blank_video, "", f"❌ {error_message}", "", afvideo, blank_video)

    def _generate_single_video_with_last_frame(self, prompt, api_url, api_key, api_format, model, duration, resolution,
                                              aspect_ratio, fps, watermark, camera_fixed, seed, input_image=None):
        """生成单个视频并返回尾帧URL"""
        try:
            _log_info(f"🔧 构建{api_format}格式的连续视频payload")

            if api_format == "volcengine":
                # 火山引擎格式：使用content数组
                text_content = f"{prompt} --rt {aspect_ratio} --dur {duration.replace('s', '')} --fps {fps} --rs {resolution}"
                if seed != -1:
                    text_content += f" --seed {seed}"
                text_content += f" --wm {str(watermark).lower()} --cf {str(camera_fixed).lower()}"

                content = [{"type": "text", "text": text_content}]

                # 添加输入图像（如果有）
                if input_image is not None:
                    image_data_url = image_to_base64(input_image, return_data_url=True)
                    if image_data_url:
                        content.append({
                            "type": "image_url",
                            "image_url": {"url": image_data_url}
                        })

                payload = {
                    "model": model,
                    "content": content,
                    "return_last_frame": True  # 关键参数：返回尾帧
                }

            else:
                # Comfly/T8格式：使用直接参数
                payload = {
                    "prompt": prompt,
                    "model": model,
                    "duration": int(duration.replace('s', '')),
                    "resolution": resolution,
                    "ratio": aspect_ratio,
                    "watermark": watermark,
                    "return_last_frame": True  # 关键参数：返回尾帧
                }

                # 添加种子
                if seed != -1:
                    payload["seed"] = seed

                # 添加输入图像（如果有）
                if input_image is not None:
                    image_data_url = image_to_base64(input_image, return_data_url=True)
                    if image_data_url:
                        payload["images"] = [image_data_url]

                # T8镜像站特殊参数
                if "t8star.cn" in api_url:
                    payload["01K3ZARVMSZ97JPXNWXBCJGG6K"] = ""

            # 调用API
            response = call_video_api(api_url, api_key, payload, api_format, timeout=self.timeout)

            # 处理响应 - call_video_api返回的是requests.Response对象
            if response and response.status_code == 200:
                try:
                    response_data = response.json()
                    _log_info(f"🔍 连续视频API响应: {response_data}")
                except Exception as json_e:
                    _log_error(f"❌ 响应JSON解析失败: {json_e}")
                    return None
            else:
                _log_error(f"❌ API调用失败，状态码: {response.status_code if response else 'None'}")
                return None

            # 检查是否是异步任务响应
            task_id = None
            if "task_id" in response_data:
                task_id = response_data["task_id"]
            elif "id" in response_data:
                task_id = response_data["id"]
            elif "data" in response_data and isinstance(response_data["data"], dict) and "task_id" in response_data["data"]:
                task_id = response_data["data"]["task_id"]

            if task_id:
                _log_info(f"🔍 检测到异步任务，任务ID: {task_id}")
                _log_info(f"⏳ 开始轮询任务状态...")

                # 轮询任务状态
                max_polls = 90  # 最多轮询90次（15分钟）
                poll_interval = 10  # 每10秒查询一次

                for poll_count in range(max_polls):
                    _log_info(f"🔍 轮询任务状态 ({poll_count + 1}/{max_polls})")

                    status_response = call_video_task_status(api_url, api_key, task_id, api_format)

                    if status_response and status_response.status_code == 200:
                        status_result = status_response.json()
                        _log_info(f"🔍 任务状态响应: {str(status_result)[:200]}...")

                        # 检查任务状态
                        status = status_result.get("status", "unknown")
                        _log_info(f"🔍 当前任务状态: '{status}' (类型: {type(status)})")

                        if status.lower() in ["completed", "success", "finished", "succeeded"] or status in ["COMPLETED", "SUCCESS", "FINISHED", "SUCCEEDED"]:
                            _log_info(f"✅ 连续视频任务完成: {status}")
                            # 使用status_result作为最终响应数据
                            response_data = status_result
                            break

                        elif status.lower() in ["failed", "error"] or status in ["FAILED", "ERROR"]:
                            _log_error(f"❌ 连续视频任务失败: {status}")
                            return None

                        elif status.lower() in ["running", "processing", "pending", "queued", "not_start"] or status in ["RUNNING", "PROCESSING", "PENDING", "QUEUED", "NOT_START"]:
                            _log_info(f"⏳ 任务进行中，状态: {status}")
                            time.sleep(poll_interval)
                            continue

                        else:
                            _log_warning(f"⚠️ 未知任务状态: {status}")
                            time.sleep(poll_interval)
                            continue

                    else:
                        _log_warning(f"⚠️ 查询任务状态失败")
                        time.sleep(poll_interval)

                # 轮询超时
                if poll_count >= max_polls - 1:
                    _log_error("❌ 连续视频任务轮询超时")
                    return None

            # 检查最终状态
            if response_data and (response_data.get('status', '').lower() in ['completed', 'success', 'finished', 'succeeded'] or response_data.get('status') in ['COMPLETED', 'SUCCESS', 'FINISHED', 'SUCCEEDED']):
                video_url = None
                last_frame_url = None

                # 根据API格式提取视频URL和尾帧URL
                if api_format == "volcengine":
                    # 火山引擎格式
                    if 'content' in response_data:
                        content_data = response_data['content']
                        video_url = content_data.get('video_url')
                        last_frame_url = content_data.get('last_frame_url')
                elif api_format == "comfly":
                    # Comfly格式 - 支持多种响应格式
                    # 格式1: data.output (Comfly连续视频格式)
                    if 'data' in response_data and isinstance(response_data['data'], dict):
                        if 'output' in response_data['data']:
                            video_url = response_data['data']['output']
                            last_frame_url = response_data['data'].get('last_frame_url', '')
                        elif 'content' in response_data['data'] and isinstance(response_data['data']['content'], dict):
                            video_url = response_data['data']['content'].get('video_url')
                            last_frame_url = response_data['data']['content'].get('last_frame_url')

                    # 格式2: content.video_url (标准格式)
                    if not video_url and 'content' in response_data:
                        content_data = response_data['content']
                        video_url = content_data.get('video_url')
                        last_frame_url = content_data.get('last_frame_url')

                    # 格式3: 直接在response中
                    if not video_url:
                        video_url = response_data.get('video_url')
                        last_frame_url = response_data.get('last_frame_url')

                if video_url and last_frame_url:
                    # 下载并转换视频
                    video_obj = self._download_and_convert_video(video_url)

                    video_info = f"视频尺寸: {resolution}, 时长: {duration}, 宽高比: {aspect_ratio}"
                    response_text = f"✅ 视频生成成功"

                    return (video_obj, video_url, response_text, video_info, last_frame_url)
                else:
                    _log_error(f"❌ 无法从响应中提取视频URL或尾帧URL")
                    _log_info(f"🔍 响应结构: {response_data}")

            _log_error(f"❌ 单个视频生成失败或不支持return_last_frame功能")
            return None

        except Exception as e:
            _log_error(f"❌ 单个视频生成异常: {str(e)}")
            return None

    def _download_last_frame_as_image(self, last_frame_url):
        """下载尾帧URL并转换为图像tensor"""
        try:
            import requests
            import numpy as np
            from PIL import Image
            import io

            _log_info(f"🔽 下载尾帧图像: {last_frame_url}")

            # 下载图像
            response = requests.get(last_frame_url, timeout=30)
            response.raise_for_status()

            # 转换为PIL图像
            image = Image.open(io.BytesIO(response.content))
            image = image.convert('RGB')

            # 转换为numpy数组
            image_array = np.array(image).astype(np.float32) / 255.0

            # 转换为ComfyUI格式的tensor (1, H, W, 3)
            if len(image_array.shape) == 3:
                image_tensor = image_array[np.newaxis, ...]  # 添加batch维度
            else:
                image_tensor = image_array

            _log_info(f"✅ 尾帧图像下载成功，尺寸: {image_tensor.shape}")
            return image_tensor

        except Exception as e:
            _log_error(f"❌ 下载尾帧图像失败: {str(e)}")
            return None

    def _download_and_convert_video(self, video_url):
        """下载视频并转换为ComfyUI对象"""
        try:
            # 复用现有的视频下载和转换逻辑
            video_path = download_video_from_url(video_url)
            if video_path:
                video_obj = video_to_comfyui_video(video_path)
                if video_obj:
                    # 为video对象添加file_path属性
                    video_obj.file_path = video_path
                    return video_obj
            return None
        except Exception as e:
            _log_error(f"❌ 视频下载转换失败: {str(e)}")
            return None

class DoubaoSeedanceMultiRefVideoNode:
    """Doubao-Seedance多图参考视频生成节点"""

    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = list(mirror_sites.keys())

        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "一个美丽的场景，包含[图1]和[图2]的元素"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "model": (["doubao-seedance-1-0-lite-i2v-250428"], {"default": "doubao-seedance-1-0-lite-i2v-250428"}),
                "duration": (["3s", "5s", "10s", "12s"], {"default": "5s"}),
                "resolution": (["480p", "720p"], {"default": "720p"}),
                "aspect_ratio": (["16:9", "4:3", "1:1", "3:4", "9:16", "21:9", "adaptive"], {"default": "16:9"}),
                "fps": ([24, 30], {"default": 30}),
                "watermark": ("BOOLEAN", {"default": False}),
                "camera_fixed": ("BOOLEAN", {"default": False}),
                "api_key": ("STRING", {"default": ""}),
                "seed": ("INT", {"default": -1, "min": -1, "max": 2147483647}),
            },
            "optional": {
                "reference_image_1": ("IMAGE",),
                "reference_image_2": ("IMAGE",),
                "reference_image_3": ("IMAGE",),
                "reference_image_4": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING", "STRING", "STRING", "VIDEO")
    RETURN_NAMES = ("video", "video_url", "response_text", "video_info", "AFVIDEO")
    FUNCTION = "generate_multi_ref_video"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 900  # 15分钟超时，视频生成需要更长时间
        self.max_retries = 3

    def generate_multi_ref_video(self, prompt, mirror_site, model, duration, resolution, aspect_ratio, fps, watermark=False, camera_fixed=False, api_key="", seed=-1,
                                reference_image_1=None, reference_image_2=None, reference_image_3=None, reference_image_4=None):
        """生成多图参考视频"""

        # 收集参考图片
        reference_images = []
        if reference_image_1 is not None:
            reference_images.append(reference_image_1)
        if reference_image_2 is not None:
            reference_images.append(reference_image_2)
        if reference_image_3 is not None:
            reference_images.append(reference_image_3)
        if reference_image_4 is not None:
            reference_images.append(reference_image_4)

        if not reference_images:
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：至少需要提供一张参考图片", "", blank_video_path)

        if len(reference_images) > 4:
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：最多支持4张参考图片", "", blank_video_path)

        _log_info(f"🔍 多图参考视频生成: 参考图片数量={len(reference_images)}")

        # 获取镜像站配置
        site_config = get_mirror_site_config(mirror_site)
        api_url = site_config.get("url", "").strip()
        api_format = site_config.get("api_format", "comfly")

        # 强制修正T8镜像站的API格式（确保使用最新配置）
        if mirror_site == "t8_mirror" or "t8star.cn" in api_url:
            api_format = "volcengine"
            _log_info(f"🔧 强制修正T8镜像站API格式为: {api_format}")

        # 使用镜像站的API key（如果提供了的话）
        if site_config.get("api_key") and not api_key.strip():
            api_key = site_config["api_key"]
            _log_info(f"🔑 自动使用镜像站API Key: {api_key[:8]}...")

        if not api_key.strip():
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 错误：未提供API Key", "", blank_video_path)

        try:
            # 多图参考支持火山引擎格式和Comfly官方格式
            if api_format not in ["volcengine", "comfly"]:
                _log_warning(f"⚠️ 多图参考功能仅支持火山引擎和Comfly格式，当前格式: {api_format}")
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                return (blank_video, "", "❌ 错误：多图参考功能仅支持火山引擎官方、T8镜像站和Comfly镜像站", "", blank_video_path)

            # 构建统一的content数组格式（火山引擎和Comfly官方格式相同）
            _log_info(f"🔧 构建多图参考{api_format}格式payload")

            # 构建文本内容
            if api_format == "volcengine":
                # 火山引擎格式：使用命令行参数
                text_content = f"{prompt} --rt {aspect_ratio} --dur {duration.replace('s', '')} --fps {fps} --rs {resolution}"
                if seed != -1:
                    text_content += f" --seed {seed}"
                # 添加watermark和camera_fixed参数
                text_content += f" --wm {str(watermark).lower()} --cf {str(camera_fixed).lower()}"
                _log_info(f"🔧 火山引擎多图参考文本内容: {text_content}")
            else:  # api_format == "comfly"
                # Comfly官方格式：也使用命令行参数（与火山引擎相同）
                text_content = f"{prompt} --ratio {aspect_ratio} --dur {duration.replace('s', '')} --fps {fps} --rs {resolution}"
                if seed != -1:
                    text_content += f" --seed {seed}"
                # 添加watermark和camera_fixed参数
                text_content += f" --wm {str(watermark).lower()} --cf {str(camera_fixed).lower()}"
                _log_info(f"🔧 Comfly官方多图参考文本内容: {text_content}")

            content = [
                {
                    "type": "text",
                    "text": text_content
                }
            ]

            # 添加参考图片到content数组
            for i, ref_image in enumerate(reference_images, 1):
                _log_info(f"🔍 处理参考图片 {i}: {ref_image.shape}")

                # 统一使用完整的Data URL格式
                image_data_url = image_to_base64(ref_image, return_data_url=True)
                if image_data_url:
                    image_content = {
                        "type": "image_url",
                        "image_url": {
                            "url": image_data_url
                        }
                    }

                    # 多图参考统一使用火山引擎格式，都需要role字段
                    image_content["role"] = "reference_image"

                    content.append(image_content)
                    _log_info(f"🔧 添加参考图片{i}到content (Data URL长度: {len(image_data_url)})")
                else:
                    _log_error(f"❌ 参考图片{i} Data URL编码失败")

            # 构建payload
            payload = {
                "model": model,
                "content": content
            }

            _log_info(f"🔍 多图参考payload构建完成: 格式={api_format}, 模型={model}, content数量={len(content)}")

            # 调用多图参考视频生成API（使用火山引擎格式端点）
            response = call_multi_ref_video_api(api_url, api_key, payload, api_format, self.timeout)

            if not response or response.status_code != 200:
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                return (blank_video, "", "❌ 错误：视频生成任务创建失败", "", blank_video_path)

            # 从响应中提取任务ID
            try:
                result = response.json()
                task_id = None

                # 火山引擎格式的任务ID提取
                if "id" in result:
                    task_id = result["id"]
                elif "task_id" in result:
                    task_id = result["task_id"]
                elif "data" in result and isinstance(result["data"], dict):
                    if "id" in result["data"]:
                        task_id = result["data"]["id"]
                    elif "task_id" in result["data"]:
                        task_id = result["data"]["task_id"]

                if not task_id:
                    _log_error(f"❌ 无法从响应中提取任务ID: {result}")
                    blank_video = create_blank_video_object()
                    blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                    return (blank_video, "", "❌ 错误：无法获取任务ID", "", blank_video_path)

                _log_info(f"🎬 多图参考视频任务创建成功: {task_id}")

            except Exception as e:
                _log_error(f"❌ 解析任务创建响应失败: {e}")
                blank_video = create_blank_video_object()
                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                return (blank_video, "", f"❌ 错误：解析响应失败: {str(e)}", "", blank_video_path)

            # 轮询任务状态
            max_polls = 90  # 15分钟，每10秒轮询一次
            poll_interval = 10

            for poll_count in range(1, max_polls + 1):
                _log_info(f"🔍 轮询任务状态 ({poll_count}/{max_polls})")

                status_response = call_video_task_status(api_url, api_key, task_id, api_format)
                status_result = None
                if status_response and status_response.status_code == 200:
                    status_result = status_response.json()
                    _log_info(f"🔍 任务状态响应: {str(status_result)[:200]}...")

                if status_result:
                    status = status_result.get('status', 'unknown')
                    _log_info(f"🔍 当前任务状态: '{status}' (类型: {type(status)})")

                    if status.lower() in ["completed", "success", "finished", "succeeded"] or status in ["SUCCESS", "COMPLETED", "FINISHED", "SUCCEEDED"]:
                        _log_info(f"✅ 多图参考视频生成成功")

                        # 获取视频URL - 支持多种响应格式
                        video_url = None

                        # 格式1: data.content.video_url (Comfly多图参考格式)
                        if 'data' in status_result and isinstance(status_result['data'], dict):
                            if 'content' in status_result['data'] and isinstance(status_result['data']['content'], dict):
                                if 'video_url' in status_result['data']['content']:
                                    video_url = status_result['data']['content']['video_url']

                        # 格式2: content.video_url (火山引擎多图参考格式)
                        if not video_url and 'content' in status_result and isinstance(status_result['content'], dict):
                            if 'video_url' in status_result['content']:
                                video_url = status_result['content']['video_url']

                        # 格式3: video_result数组格式
                        if not video_url and 'video_result' in status_result and status_result['video_result']:
                            video_result = status_result['video_result'][0] if isinstance(status_result['video_result'], list) else status_result['video_result']
                            video_url = video_result.get('url')

                        # 格式4: 直接video_url字段
                        if not video_url and 'video_url' in status_result:
                            video_url = status_result['video_url']

                        # 格式4: result.video_url格式
                        if not video_url and 'result' in status_result and status_result['result']:
                            result = status_result['result']
                            if isinstance(result, dict) and 'video_url' in result:
                                video_url = result['video_url']
                                _log_info(f"🔍 从result.video_url提取视频URL")

                        if video_url:
                            _log_info(f"🎬 获取到视频URL: {video_url}")

                            # 下载并转换视频
                            video_path = download_video_from_url(video_url)
                            if video_path:
                                _log_info(f"🎬 开始转换视频为ComfyUI对象...")
                                video_obj = video_to_comfyui_video(video_path)
                                if video_obj is not None:
                                    video_info = f"模型: {model}, 参考图片: {len(reference_images)}张, 时长: {duration}, 分辨率: {resolution}, 宽高比: {aspect_ratio}, 帧率: {fps}fps, 任务ID: {task_id}"
                                    return (video_obj, video_url, "✅ 多图参考视频生成成功", video_info, video_path)
                                else:
                                    _log_error("❌ 视频转换失败")
                                    blank_video = create_blank_video_object()
                                    blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                    return (blank_video, video_url, "❌ 视频转换失败", "", blank_video_path)
                            else:
                                _log_error("❌ 视频下载失败")
                                blank_video = create_blank_video_object()
                                blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                                return (blank_video, video_url, "❌ 视频下载失败", "", blank_video_path)
                        else:
                            _log_error("❌ 未获取到视频URL")
                            blank_video = create_blank_video_object()
                            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                            return (blank_video, "", "❌ 未获取到视频URL", "", blank_video_path)

                    elif status.lower() in ["failed", "error"] or status in ["FAILED", "ERROR"]:
                        fail_reason = status_result.get('fail_reason', '未知错误')
                        _log_error(f"❌ 多图参考视频生成失败: {fail_reason}")
                        blank_video = create_blank_video_object()
                        blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
                        return (blank_video, "", f"❌ 视频生成失败: {fail_reason}", "", blank_video_path)

                    elif status.lower() in ["running", "processing", "in_progress", "not_start", "queued"] or status in ["RUNNING", "PROCESSING", "IN_PROGRESS", "NOT_START", "QUEUED"]:
                        _log_info(f"⏳ 任务进行中，状态: {status}")
                        if poll_count < max_polls:
                            time.sleep(poll_interval)
                        continue
                    else:
                        _log_warning(f"⚠️ 未知任务状态: {status}")
                        if poll_count < max_polls:
                            time.sleep(poll_interval)
                        continue
                else:
                    _log_warning(f"⚠️ 无法获取任务状态，响应: {status_response}")
                    if poll_count < max_polls:
                        time.sleep(poll_interval)
                    continue

            # 超时处理
            _log_error(f"❌ 多图参考视频生成超时")
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", "❌ 视频生成超时", "", blank_video_path)

        except Exception as e:
            _log_error(f"❌ 多图参考视频生成异常: {e}")
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            return (blank_video, "", f"❌ 错误：{str(e)}", "", blank_video_path)

class VideoStitchingNode:
    """视频拼接节点 - 最多可以将8个视频拼接在一起"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video1": ("VIDEO",),
            },
            "optional": {
                "video2": ("VIDEO",),
                "video3": ("VIDEO",),
                "video4": ("VIDEO",),
                "video5": ("VIDEO",),
                "video6": ("VIDEO",),
                "video7": ("VIDEO",),
                "video8": ("VIDEO",),
                "output_filename": ("STRING", {"default": ""}),
                "stitch_method": (["concat", "concat_crossfade", "concat_advanced", "concat_morph", "concat_optical_flow", "hstack", "vstack", "grid2x2", "grid2x3", "grid2x4"], {"default": "concat"}),
                "output_quality": (["high", "medium", "low"], {"default": "high"}),
                "scale_videos": ("BOOLEAN", {"default": True}),
                "smooth_transitions": ("BOOLEAN", {"default": True}),
                "transition_duration": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 2.0, "step": 0.1}),
                "force_keyframes": ("BOOLEAN", {"default": True}),
                "transition_type": (["fade", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft", "slideright", "slideup", "slidedown", "smoothleft", "smoothright", "smoothup", "smoothdown", "circleopen", "circleclose", "vertopen", "vertclose", "horzopen", "horzclose", "dissolve", "pixelize", "radial", "smoothradial"], {"default": "fade"}),
                "motion_compensation": ("BOOLEAN", {"default": False}),
                "edge_enhancement": ("BOOLEAN", {"default": False}),
            }
        }

    RETURN_TYPES = ("VIDEO", "STRING", "VIDEO")
    RETURN_NAMES = ("stitched_video", "video_path", "AFVIDEO")
    FUNCTION = "stitch_videos"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 300  # 5分钟超时，视频处理需要更长时间

    def stitch_videos(self, video1, video2=None, video3=None, video4=None, video5=None, video6=None, video7=None, video8=None,
                     output_filename="", stitch_method="concat", output_quality="high", scale_videos=True,
                     smooth_transitions=True, transition_duration=0.5, force_keyframes=True, transition_type="fade",
                     motion_compensation=False, edge_enhancement=False):
        """
        拼接多个视频

        Args:
            video1-video8: ComfyUI VIDEO对象
            output_filename: 输出文件名（可选）
            stitch_method: 拼接方法
            output_quality: 输出质量
            scale_videos: 是否缩放视频到统一尺寸

        Returns:
            tuple: (拼接后的VIDEO对象, 视频文件路径)
        """
        try:
            _log_info("🎬 开始视频拼接...")

            # 收集所有有效的视频
            videos = [video1]
            for video in [video2, video3, video4, video5, video6, video7, video8]:
                if video is not None:
                    videos.append(video)

            if len(videos) < 2:
                error_msg = "至少需要2个视频才能进行拼接"
                _log_error(error_msg)
                return self._create_error_result(error_msg)

            _log_info(f"📊 将拼接{len(videos)}个视频，使用{stitch_method}方法")

            # 获取视频文件路径
            video_paths = []
            for i, video in enumerate(videos):
                _log_info(f"🔍 处理第{i+1}个视频...")
                video_path = self._extract_video_path(video)
                if not video_path:
                    error_msg = f"无法获取第{i+1}个视频的有效路径: {video_path}"
                    _log_error(error_msg)
                    _log_error(f"视频对象详情: type={type(video)}, repr={repr(video)}")
                    return self._create_error_result(error_msg)

                if not os.path.exists(video_path):
                    error_msg = f"第{i+1}个视频文件不存在: {video_path}"
                    _log_error(error_msg)
                    return self._create_error_result(error_msg)

                video_paths.append(video_path)
                _log_info(f"✅ 第{i+1}个视频: {video_path}")

            # 生成输出文件路径
            if not output_filename:
                output_filename = f"stitched_video_{stitch_method}_{int(time.time())}.mp4"

            if not output_filename.lower().endswith('.mp4'):
                output_filename += '.mp4'

            # 使用ComfyUI的输出目录而不是系统临时目录
            try:
                import folder_paths
                output_dir = folder_paths.get_output_directory()
                _log_info(f"📁 使用ComfyUI输出目录: {output_dir}")
            except ImportError:
                # 如果在ComfyUI环境外，尝试推断ComfyUI路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                comfyui_root = None

                # 向上查找ComfyUI根目录
                path_parts = current_dir.split(os.sep)
                for i in range(len(path_parts) - 1, -1, -1):
                    potential_root = os.sep.join(path_parts[:i+1])
                    if os.path.exists(os.path.join(potential_root, "main.py")) and \
                       os.path.exists(os.path.join(potential_root, "nodes.py")):
                        comfyui_root = potential_root
                        break

                if comfyui_root:
                    output_dir = os.path.join(comfyui_root, "output")
                    os.makedirs(output_dir, exist_ok=True)
                    _log_info(f"📁 推断ComfyUI输出目录: {output_dir}")
                else:
                    import tempfile
                    output_dir = tempfile.gettempdir()
                    _log_info(f"📁 回退到系统临时目录: {output_dir}")
            except Exception as e:
                import tempfile
                output_dir = tempfile.gettempdir()
                _log_info(f"📁 异常，使用系统临时目录: {output_dir} (错误: {e})")

            output_path = os.path.join(output_dir, output_filename)

            # 根据拼接方法执行不同的处理
            success = False
            if stitch_method == "concat":
                success = self._concat_videos(video_paths, output_path, output_quality, smooth_transitions, transition_duration, force_keyframes)
            elif stitch_method == "concat_crossfade":
                if len(video_paths) <= 2:
                    success = self._concat_with_crossfade_transitions(video_paths, output_path, output_quality, transition_duration)
                else:
                    success = self._concat_with_xfade_multiple(video_paths, output_path, output_quality, transition_duration)
            elif stitch_method == "concat_advanced":
                success = self._concat_with_advanced_transitions(video_paths, output_path, output_quality, transition_duration, transition_type, motion_compensation, edge_enhancement)
            elif stitch_method == "concat_morph":
                success = self._concat_with_morphing_transitions(video_paths, output_path, output_quality, transition_duration, motion_compensation)
            elif stitch_method == "concat_optical_flow":
                success = self._concat_with_optical_flow_transitions(video_paths, output_path, output_quality, transition_duration)
            elif stitch_method == "hstack":
                success = self._hstack_videos(video_paths, output_path, output_quality, scale_videos)
            elif stitch_method == "vstack":
                success = self._vstack_videos(video_paths, output_path, output_quality, scale_videos)
            elif stitch_method == "grid2x2":
                success = self._grid_videos(video_paths, output_path, output_quality, "2x2", scale_videos)
            elif stitch_method == "grid2x3":
                success = self._grid_videos(video_paths, output_path, output_quality, "2x3", scale_videos)
            elif stitch_method == "grid2x4":
                success = self._grid_videos(video_paths, output_path, output_quality, "2x4", scale_videos)

            if not success:
                error_msg = f"视频拼接失败，方法: {stitch_method}"
                _log_error(error_msg)
                return self._create_error_result(error_msg)

            # 转换为ComfyUI VIDEO对象
            stitched_video = video_to_comfyui_video(output_path)
            if stitched_video:
                stitched_video.file_path = output_path
                _log_info(f"✅ 视频拼接成功: {output_path}")

                # AFVIDEO使用路径包装器，与标准视频节点保持一致
                afvideo = create_video_path_wrapper(output_path) if output_path else create_blank_video_object()

                return (stitched_video, output_path, afvideo)
            else:
                error_msg = "拼接视频转换为ComfyUI对象失败"
                _log_error(error_msg)
                return self._create_error_result(error_msg)

        except Exception as e:
            error_msg = f"视频拼接失败: {str(e)}"
            _log_error(error_msg)
            return self._create_error_result(error_msg)

    def _extract_video_path(self, video):
        """从VIDEO对象提取文件路径"""
        _log_info(f"🔍 尝试从VIDEO对象提取路径: {type(video)}")

        # 如果是字符串，直接返回
        if isinstance(video, str):
            _log_info(f"✅ 直接字符串路径: {video}")
            return video

        # 尝试常见的文件路径属性
        path_attributes = [
            'file_path',    # 我们自己的VideoFromFile对象
            'filename',     # 一些节点使用这个
            'file',         # 向后兼容
            'path',         # 通用路径属性
            'filepath',     # 文件路径
            'video_path',   # 视频路径
            'source',       # 源文件
            'url',          # URL路径
            'video_file',   # 视频文件
            'file_name',    # 文件名
        ]

        for attr in path_attributes:
            if hasattr(video, attr):
                value = getattr(video, attr)
                if value and isinstance(value, str):
                    _log_info(f"✅ 从属性 {attr} 获取路径: {value}")
                    return value
                elif value:
                    _log_info(f"⚠️ 属性 {attr} 存在但不是字符串: {type(value)} = {value}")

        # 如果是字典类型，尝试从字典中获取路径
        if isinstance(video, dict):
            for key in ['file_path', 'filename', 'path', 'url', 'source']:
                if key in video and isinstance(video[key], str):
                    _log_info(f"✅ 从字典键 {key} 获取路径: {video[key]}")
                    return video[key]

        # 如果有__dict__属性，打印所有属性用于调试
        if hasattr(video, '__dict__'):
            _log_info(f"🔍 VIDEO对象属性: {list(video.__dict__.keys())}")
            for key, value in video.__dict__.items():
                if isinstance(value, str) and ('path' in key.lower() or 'file' in key.lower() or 'url' in key.lower()):
                    _log_info(f"✅ 从__dict__属性 {key} 获取路径: {value}")
                    return value

        # 最后尝试：如果对象可以转换为字符串且看起来像路径
        try:
            str_repr = str(video)
            if str_repr and ('/' in str_repr or '\\' in str_repr or str_repr.endswith('.mp4')):
                _log_info(f"✅ 从字符串表示获取路径: {str_repr}")
                return str_repr
        except:
            pass

        _log_error(f"❌ 无法从VIDEO对象提取路径，对象类型: {type(video)}")
        return None

    def _get_quality_params(self, quality):
        """获取质量参数"""
        quality_settings = {
            "high": ["-crf", "18", "-preset", "medium"],
            "medium": ["-crf", "23", "-preset", "fast"],
            "low": ["-crf", "28", "-preset", "faster"]
        }
        return quality_settings.get(quality, quality_settings["high"])

    def _concat_videos(self, video_paths, output_path, quality, smooth_transitions=True, transition_duration=0.5, force_keyframes=True):
        """连续拼接视频（时间轴上连接）- 改进版本减少闪烁"""
        try:
            import subprocess
            import tempfile

            _log_info("🔗 使用改进的concat方法拼接视频...")

            # 首先检查视频属性一致性
            video_info = self._analyze_video_properties(video_paths)
            if not video_info:
                _log_error("无法分析视频属性")
                return False

            # 创建concat文件列表 - 使用合适的临时目录
            try:
                import folder_paths
                temp_dir = folder_paths.get_temp_directory()
            except:
                import tempfile
                temp_dir = tempfile.gettempdir()
            concat_file = os.path.join(temp_dir, f"concat_list_{int(time.time())}.txt")

            with open(concat_file, 'w', encoding='utf-8') as f:
                for video_path in video_paths:
                    # 使用绝对路径并转义特殊字符
                    abs_path = os.path.abspath(video_path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")

            # 根据视频属性一致性选择处理方式
            if video_info['consistent']:
                # 属性一致，尝试直接复制流（最快，无质量损失）
                success = self._concat_with_copy(concat_file, output_path)
                if success:
                    self._cleanup_temp_file(concat_file)
                    return True
                _log_info("🔄 直接复制失败，尝试重新编码...")

            # 属性不一致或直接复制失败，使用改进的重新编码方法
            success = self._concat_with_smooth_transitions(concat_file, output_path, quality, video_info, smooth_transitions, transition_duration, force_keyframes)

            self._cleanup_temp_file(concat_file)
            return success

        except Exception as e:
            _log_error(f"concat拼接失败: {str(e)}")
            return False

    def _analyze_video_properties(self, video_paths):
        """分析视频属性，检查一致性"""
        try:
            import subprocess
            import json

            _log_info("🔍 分析视频属性...")

            video_props = []
            for video_path in video_paths:
                # 使用ffprobe获取视频信息
                cmd = [
                    'ffprobe',
                    '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_streams',
                    '-select_streams', 'v:0',
                    video_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode != 0:
                    _log_error(f"无法获取视频信息: {video_path}")
                    return None

                try:
                    info = json.loads(result.stdout)
                    if 'streams' in info and len(info['streams']) > 0:
                        stream = info['streams'][0]
                        props = {
                            'width': stream.get('width', 0),
                            'height': stream.get('height', 0),
                            'fps': eval(stream.get('r_frame_rate', '0/1')),
                            'codec': stream.get('codec_name', ''),
                            'pix_fmt': stream.get('pix_fmt', '')
                        }
                        video_props.append(props)
                        _log_info(f"📊 {os.path.basename(video_path)}: {props['width']}x{props['height']} @{props['fps']:.2f}fps {props['codec']}")
                    else:
                        _log_error(f"无法解析视频流信息: {video_path}")
                        return None
                except json.JSONDecodeError:
                    _log_error(f"无法解析ffprobe输出: {video_path}")
                    return None

            # 检查属性一致性
            if not video_props:
                return None

            first_props = video_props[0]
            consistent = all(
                props['width'] == first_props['width'] and
                props['height'] == first_props['height'] and
                abs(props['fps'] - first_props['fps']) < 0.1 and
                props['codec'] == first_props['codec'] and
                props['pix_fmt'] == first_props['pix_fmt']
                for props in video_props
            )

            _log_info(f"✅ 视频属性一致性: {'是' if consistent else '否'}")

            return {
                'consistent': consistent,
                'properties': video_props,
                'target_width': first_props['width'],
                'target_height': first_props['height'],
                'target_fps': first_props['fps'],
                'target_codec': first_props['codec'],
                'target_pix_fmt': first_props['pix_fmt']
            }

        except Exception as e:
            _log_error(f"分析视频属性失败: {str(e)}")
            return None

    def _concat_with_copy(self, concat_file, output_path):
        """使用流复制方式拼接（最快，适用于属性一致的视频）"""
        try:
            import subprocess

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',  # 直接复制流
                '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行流复制命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 流复制拼接成功")
                return True
            else:
                _log_info(f"⚠️ 流复制失败: {result.stderr}")
                return False

        except Exception as e:
            _log_error(f"流复制拼接失败: {str(e)}")
            return False

    def _concat_with_smooth_transitions(self, concat_file, output_path, quality, video_info, smooth_transitions=True, transition_duration=0.5, force_keyframes=True):
        """使用平滑过渡的重新编码方式拼接"""
        try:
            import subprocess

            quality_params = self._get_quality_params(quality)

            # 构建改进的FFmpeg命令，减少闪烁
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',  # 强制使用H.264编码器
                '-pix_fmt', 'yuv420p',  # 统一像素格式
                '-r', str(int(video_info['target_fps'])),  # 统一帧率
                '-s', f"{video_info['target_width']}x{video_info['target_height']}",  # 统一分辨率
                '-vsync', 'cfr',  # 恒定帧率
                '-bf', '2',  # B帧数量
                '-sc_threshold', '0',  # 禁用场景切换检测
                '-avoid_negative_ts', 'make_zero',  # 避免负时间戳
                '-fflags', '+genpts',  # 生成PTS
            ]

            # 根据参数添加关键帧控制
            if force_keyframes:
                keyframe_interval = max(1, int(video_info['target_fps'] * 2))  # 每2秒一个关键帧
                cmd.extend([
                    '-force_key_frames', f'expr:gte(t,n_forced*2)',
                    '-g', str(keyframe_interval),
                ])

            # 添加平滑过渡滤镜（如果启用）
            if smooth_transitions and transition_duration > 0:
                # 使用minterpolate滤镜进行帧插值，减少跳跃感
                cmd.extend([
                    '-vf', f'minterpolate=fps={video_info["target_fps"]}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1'
                ])

            cmd.extend(quality_params + ['-y', output_path])

            _log_info(f"🔧 执行平滑过渡编码: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 平滑过渡拼接成功")
                return True
            else:
                _log_error(f"❌ 平滑过渡拼接失败: {result.stderr}")
                # 如果高级滤镜失败，尝试基础方法
                if smooth_transitions:
                    _log_info("🔄 尝试基础平滑方法...")
                    return self._concat_with_basic_smooth(concat_file, output_path, quality, video_info)
                return False

        except Exception as e:
            _log_error(f"平滑过渡拼接失败: {str(e)}")
            return False

    def _concat_with_basic_smooth(self, concat_file, output_path, quality, video_info):
        """基础平滑拼接方法（备用）"""
        try:
            import subprocess

            quality_params = self._get_quality_params(quality)

            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(video_info['target_fps'])),
                '-s', f"{video_info['target_width']}x{video_info['target_height']}",
                '-vsync', 'cfr',
                '-bf', '2',
                '-g', str(int(video_info['target_fps'] * 2)),
                '-sc_threshold', '0',
                '-avoid_negative_ts', 'make_zero',
                '-fflags', '+genpts',
            ] + quality_params + [
                '-y',
                output_path
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            _log_error(f"基础平滑拼接失败: {str(e)}")
            return False

    def _cleanup_temp_file(self, temp_file):
        """清理临时文件"""
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except Exception as e:
            _log_error(f"清理临时文件失败: {str(e)}")

    def _concat_with_crossfade_transitions(self, video_paths, output_path, quality, transition_duration=0.5):
        """使用交叉淡化过渡效果拼接视频"""
        try:
            import subprocess

            if len(video_paths) < 2:
                return self._concat_videos(video_paths, output_path, quality, False, 0, True)

            _log_info(f"🎬 使用交叉淡化过渡拼接 {len(video_paths)} 个视频...")

            # 对于交叉淡化，我们使用更简单但有效的方法：
            # 1. 先用concat正常拼接
            # 2. 然后在拼接点添加淡化效果

            # 首先获取视频信息以计算总时长
            video_info = self._analyze_video_properties(video_paths)
            if not video_info:
                _log_error("无法分析视频属性，回退到普通拼接")
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            # 计算每个视频的时长和累积时长
            video_durations = []
            cumulative_time = 0

            for video_path in video_paths:
                try:
                    cmd_duration = [
                        'ffprobe',
                        '-v', 'quiet',
                        '-show_entries', 'format=duration',
                        '-of', 'csv=p=0',
                        video_path
                    ]
                    result = subprocess.run(cmd_duration, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        duration = float(result.stdout.strip())
                        video_durations.append(duration)
                        cumulative_time += duration
                    else:
                        video_durations.append(2.0)  # 默认2秒
                        cumulative_time += 2.0
                except:
                    video_durations.append(2.0)
                    cumulative_time += 2.0

            _log_info(f"📊 视频时长: {[f'{d:.1f}s' for d in video_durations]}, 总时长: {cumulative_time:.1f}s")

            # 构建输入
            inputs = []
            for video_path in video_paths:
                inputs.extend(['-i', video_path])

            # 构建简化的交叉淡化滤镜
            if len(video_paths) == 2:
                # 两个视频的简单交叉淡化
                filter_complex = self._build_simple_crossfade_filter(video_durations, transition_duration)
            else:
                # 多个视频使用改进的concat方法
                _log_info("🔄 多视频交叉淡化，使用改进的concat方法...")
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            quality_params = self._get_quality_params(quality)

            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(video_info['target_fps'])),
                '-vsync', 'cfr',
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行交叉淡化命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 交叉淡化拼接成功")
                return True
            else:
                _log_error(f"❌ 交叉淡化拼接失败: {result.stderr}")
                # 回退到普通拼接
                _log_info("🔄 回退到普通拼接方法...")
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

        except Exception as e:
            _log_error(f"交叉淡化拼接失败: {str(e)}")
            # 回退到普通拼接
            return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

    def _build_simple_crossfade_filter(self, video_durations, transition_duration):
        """构建简单的两视频交叉淡化滤镜"""
        if len(video_durations) != 2:
            return "[0:v][1:v]concat=n=2:v=1[output]"

        duration1, duration2 = video_durations

        # 确保过渡时间不超过较短视频的一半
        max_transition = min(duration1, duration2) / 2
        actual_transition = min(transition_duration, max_transition)

        if actual_transition <= 0:
            return "[0:v][1:v]concat=n=2:v=1[output]"

        # 使用xfade滤镜进行交叉淡化（更专业的方法）
        # xfade滤镜会自动处理时间对齐
        offset_time = duration1 - actual_transition

        filter_complex = f"[0:v][1:v]xfade=transition=fade:duration={actual_transition}:offset={offset_time}[output]"

        return filter_complex

    def _concat_with_xfade_multiple(self, video_paths, output_path, quality, transition_duration=0.5):
        """使用xfade滤镜拼接多个视频（改进版本）"""
        try:
            import subprocess
            import tempfile

            _log_info(f"🎬 使用xfade滤镜拼接 {len(video_paths)} 个视频...")

            if len(video_paths) == 2:
                # 两个视频直接使用xfade
                return self._concat_with_crossfade_transitions(video_paths, output_path, quality, transition_duration)

            # 多个视频需要递归处理
            temp_dir = tempfile.mkdtemp()
            intermediate_files = []

            try:
                current_video = video_paths[0]

                for i in range(1, len(video_paths)):
                    next_video = video_paths[i]
                    temp_output = os.path.join(temp_dir, f"intermediate_{i}.mp4")

                    # 使用两视频交叉淡化
                    success = self._concat_with_crossfade_transitions(
                        [current_video, next_video],
                        temp_output,
                        quality,
                        transition_duration
                    )

                    if not success:
                        _log_error(f"中间步骤 {i} 失败")
                        return False

                    intermediate_files.append(temp_output)
                    current_video = temp_output

                # 复制最终结果
                if intermediate_files:
                    final_temp = intermediate_files[-1]
                    if os.path.exists(final_temp):
                        import shutil
                        shutil.copy2(final_temp, output_path)
                        return os.path.exists(output_path)

                return False

            finally:
                # 清理临时文件
                for temp_file in intermediate_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

        except Exception as e:
            _log_error(f"多视频xfade拼接失败: {str(e)}")
            return False

    def _concat_with_advanced_transitions(self, video_paths, output_path, quality, transition_duration=0.5, transition_type="fade", motion_compensation=False, edge_enhancement=False):
        """使用高级过渡效果拼接视频"""
        try:
            import subprocess

            if len(video_paths) < 2:
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            _log_info(f"🎨 使用高级过渡效果拼接 {len(video_paths)} 个视频，过渡类型: {transition_type}")

            # 获取视频信息
            video_info = self._analyze_video_properties(video_paths)
            if not video_info:
                _log_error("无法分析视频属性，回退到普通拼接")
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            # 构建输入
            inputs = []
            for video_path in video_paths:
                inputs.extend(['-i', video_path])

            # 构建高级过渡滤镜
            if len(video_paths) == 2:
                filter_complex = self._build_advanced_transition_filter(video_paths, transition_duration, transition_type, motion_compensation, edge_enhancement)
            else:
                # 多视频使用递归处理
                return self._concat_advanced_multiple(video_paths, output_path, quality, transition_duration, transition_type, motion_compensation, edge_enhancement)

            quality_params = self._get_quality_params(quality)

            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(video_info['target_fps'])),
                '-vsync', 'cfr',
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行高级过渡命令...")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout * 2  # 高级处理需要更多时间
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 高级过渡拼接成功")
                return True
            else:
                _log_error(f"❌ 高级过渡拼接失败")
                # 回退到交叉淡化
                _log_info("🔄 回退到交叉淡化方法...")
                return self._concat_with_crossfade_transitions(video_paths, output_path, quality, transition_duration)

        except Exception as e:
            _log_error(f"高级过渡拼接失败: {str(e)}")
            # 回退到交叉淡化
            return self._concat_with_crossfade_transitions(video_paths, output_path, quality, transition_duration)

    def _build_advanced_transition_filter(self, video_paths, transition_duration, transition_type, motion_compensation, edge_enhancement):
        """构建高级过渡滤镜"""
        try:
            # 获取视频时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        durations.append(float(result.stdout.strip()))
                    else:
                        durations.append(4.0)  # 默认4秒
                except:
                    durations.append(4.0)

            if len(durations) < 2:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            duration1, duration2 = durations[0], durations[1]
            max_transition = min(duration1, duration2) / 2
            actual_transition = min(transition_duration, max_transition)

            if actual_transition <= 0:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            offset_time = duration1 - actual_transition

            # 预处理滤镜
            preprocess_filters = []

            # 边缘增强
            if edge_enhancement:
                preprocess_filters.extend([
                    "[0:v]unsharp=5:5:1.0:5:5:0.0[v0enhanced]",
                    "[1:v]unsharp=5:5:1.0:5:5:0.0[v1enhanced]"
                ])
                input_labels = ["[v0enhanced]", "[v1enhanced]"]
            else:
                input_labels = ["[0:v]", "[1:v]"]

            # 运动补偿（使用minterpolate进行帧插值）
            if motion_compensation:
                preprocess_filters.extend([
                    f"{input_labels[0]}minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v0smooth]",
                    f"{input_labels[1]}minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v1smooth]"
                ])
                input_labels = ["[v0smooth]", "[v1smooth]"]

            # 构建xfade过渡
            xfade_filter = f"{input_labels[0]}{input_labels[1]}xfade=transition={transition_type}:duration={actual_transition}:offset={offset_time}[output]"

            # 组合所有滤镜
            if preprocess_filters:
                filter_complex = ";".join(preprocess_filters) + ";" + xfade_filter
            else:
                filter_complex = xfade_filter

            return filter_complex

        except Exception as e:
            _log_error(f"构建高级过渡滤镜失败: {str(e)}")
            return f"[0:v][1:v]xfade=transition=fade:duration={transition_duration}:offset={max(0, durations[0] - transition_duration)}[output]"

    def _concat_advanced_multiple(self, video_paths, output_path, quality, transition_duration, transition_type, motion_compensation, edge_enhancement):
        """多视频高级过渡拼接 - 修复时长计算问题"""
        try:
            # 对于多视频，使用一次性滤镜链而不是递归拼接
            # 这样可以避免重复减去过渡时间的问题

            if len(video_paths) == 2:
                # 两个视频直接使用原方法
                return self._concat_with_advanced_transitions(
                    video_paths, output_path, quality, transition_duration,
                    transition_type, motion_compensation, edge_enhancement
                )

            # 多于2个视频时，构建一次性滤镜链
            return self._concat_advanced_multiple_chain(
                video_paths, output_path, quality, transition_duration,
                transition_type, motion_compensation, edge_enhancement
            )

        except Exception as e:
            _log_error(f"多视频高级过渡拼接失败: {str(e)}")
            return False

    def _concat_advanced_multiple_chain(self, video_paths, output_path, quality, transition_duration, transition_type, motion_compensation, edge_enhancement):
        """使用一次性滤镜链拼接多个视频 - 正确的时长计算"""
        try:
            import subprocess

            # 获取所有视频的时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        durations.append(float(result.stdout.strip()))
                    else:
                        durations.append(4.0)  # 默认4秒
                except:
                    durations.append(4.0)

            if len(durations) < 2:
                return False

            # 计算过渡参数
            min_duration = min(durations)
            max_transition = min_duration / 2
            actual_transition = min(transition_duration, max_transition)

            if actual_transition <= 0:
                # 无过渡，使用简单concat
                return self._simple_concat_multiple(video_paths, output_path)

            # 构建多视频xfade滤镜链
            filter_complex = self._build_multiple_xfade_chain(video_paths, durations, actual_transition, transition_type)

            if not filter_complex:
                _log_error("构建多视频滤镜链失败")
                return False

            # 执行FFmpeg命令
            cmd = ['ffmpeg']

            # 添加输入文件
            for video_path in video_paths:
                cmd.extend(['-i', video_path])

            # 添加滤镜和输出参数
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                output_path
            ])

            _log_info(f"🔧 执行多视频高级过渡命令...")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 多视频高级过渡拼接成功")
                return True
            else:
                _log_error(f"多视频高级过渡拼接失败: {result.stderr}")
                return False

        except Exception as e:
            _log_error(f"多视频高级过渡拼接异常: {str(e)}")
            return False

    def _build_multiple_xfade_chain(self, video_paths, durations, transition_duration, transition_type):
        """构建多视频xfade滤镜链"""
        try:
            if len(video_paths) < 2:
                return None

            if len(video_paths) == 2:
                # 两个视频的简单情况
                offset_time = durations[0] - transition_duration
                return f"[0:v][1:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset_time}[output]"

            # 多个视频的复杂情况
            filter_parts = []
            current_offset = 0

            # 第一个过渡
            offset_time = durations[0] - transition_duration
            filter_parts.append(f"[0:v][1:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset_time}[v01]")
            current_offset = durations[0] + durations[1] - transition_duration

            # 后续过渡
            for i in range(2, len(video_paths)):
                input_label = f"v0{i-1}" if i == 2 else f"v0{i-1}"
                output_label = f"v0{i}" if i < len(video_paths) - 1 else "output"

                # 计算这个过渡的偏移时间
                offset_time = current_offset - transition_duration
                filter_parts.append(f"[{input_label}][{i}:v]xfade=transition={transition_type}:duration={transition_duration}:offset={offset_time}[{output_label}]")

                current_offset += durations[i] - transition_duration

            return ";".join(filter_parts)

        except Exception as e:
            _log_error(f"构建多视频滤镜链失败: {str(e)}")
            return None

    def _simple_concat_multiple(self, video_paths, output_path):
        """简单的多视频拼接（无过渡）"""
        try:
            import subprocess
            import tempfile

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
                concat_file = f.name

            try:
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', concat_file,
                    '-c', 'copy',
                    '-y',
                    output_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

                if result.returncode == 0 and os.path.exists(output_path):
                    return True
                else:
                    return False

            finally:
                try:
                    os.unlink(concat_file)
                except:
                    pass

        except Exception as e:
            _log_error(f"简单多视频拼接失败: {str(e)}")
            return False

    def _concat_with_morphing_transitions(self, video_paths, output_path, quality, transition_duration=0.5, motion_compensation=False):
        """使用形态学过渡拼接视频（实验性）"""
        try:
            import subprocess

            if len(video_paths) < 2:
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            _log_info(f"🧬 使用形态学过渡拼接 {len(video_paths)} 个视频...")

            # 获取视频信息
            video_info = self._analyze_video_properties(video_paths)
            if not video_info:
                _log_error("无法分析视频属性，回退到高级过渡")
                return self._concat_with_advanced_transitions(video_paths, output_path, quality, transition_duration, "fade", motion_compensation, False)

            # 对于形态学过渡，我们使用blend滤镜和morphological操作
            if len(video_paths) == 2:
                filter_complex = self._build_morphing_filter(video_paths, transition_duration, motion_compensation)
            else:
                # 多视频使用一次性滤镜链，避免时长计算错误
                return self._concat_morphing_multiple_chain(video_paths, output_path, quality, transition_duration, motion_compensation)

            inputs = []
            for video_path in video_paths:
                inputs.extend(['-i', video_path])

            quality_params = self._get_quality_params(quality)

            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(video_info['target_fps'])),
                '-vsync', 'cfr',
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行形态学过渡命令...")

            # 大幅缩短超时时间 - 形态学过渡也应该快速处理
            video_info = self._analyze_video_properties(video_paths)
            base_timeout = 20  # 基础20秒超时

            if video_info and 'target_width' in video_info and 'target_height' in video_info:
                pixels = video_info['target_width'] * video_info['target_height']
                if pixels > 1000000:  # 大于1MP (如1248x704)
                    timeout_seconds = 45  # 最多45秒
                elif pixels > 500000:  # 大于0.5MP
                    timeout_seconds = 30  # 30秒
                else:
                    timeout_seconds = 20  # 20秒
            else:
                timeout_seconds = 20

            _log_info(f"⏱️ 形态学过渡超时设置: {timeout_seconds}秒 (快速处理策略)")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 形态学过渡拼接成功")
                return True
            else:
                _log_error(f"❌ 形态学过渡拼接失败")
                if result.stderr:
                    _log_error(f"FFmpeg错误: {result.stderr[:300]}...")
                # 回退到高级过渡
                _log_info("🔄 回退到高级过渡方法...")
                return self._concat_with_advanced_transitions(video_paths, output_path, quality, transition_duration, "dissolve", motion_compensation, True)

        except subprocess.TimeoutExpired:
            _log_error(f"⏰ 形态学过渡超时 ({timeout_seconds}秒)")
            _log_info("🔄 回退到高级过渡方法...")
            return self._concat_with_advanced_transitions(video_paths, output_path, quality, transition_duration, "dissolve", motion_compensation, True)

        except Exception as e:
            _log_error(f"形态学过渡拼接失败: {str(e)}")
            # 回退到高级过渡
            return self._concat_with_advanced_transitions(video_paths, output_path, quality, transition_duration, "dissolve", motion_compensation, True)

    def _build_morphing_filter(self, video_paths, transition_duration, motion_compensation):
        """构建形态学过渡滤镜（优化版，更稳定）"""
        try:
            # 获取视频时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        durations.append(float(result.stdout.strip()))
                    else:
                        durations.append(4.0)
                except:
                    durations.append(4.0)

            if len(durations) < 2:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            duration1, duration2 = durations[0], durations[1]
            max_transition = min(duration1, duration2) / 2
            actual_transition = min(transition_duration, max_transition)

            if actual_transition <= 0:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            offset_time = duration1 - actual_transition

            # 简化的形态学过渡滤镜 - 更稳定的实现
            filter_parts = []

            # 运动补偿（如果启用）
            if motion_compensation:
                filter_parts.extend([
                    "[0:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v0smooth]",
                    "[1:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v1smooth]"
                ])
                # 使用高质量dissolve过渡
                filter_parts.append(
                    f"[v0smooth][v1smooth]xfade=transition=dissolve:duration={actual_transition}:offset={offset_time}[output]"
                )
            else:
                # 不使用运动补偿时，使用边缘增强的dissolve
                filter_parts.extend([
                    "[0:v]unsharp=5:5:1.0:5:5:0.0[v0enhanced]",
                    "[1:v]unsharp=5:5:1.0:5:5:0.0[v1enhanced]"
                ])
                filter_parts.append(
                    f"[v0enhanced][v1enhanced]xfade=transition=dissolve:duration={actual_transition}:offset={offset_time}[output]"
                )

            return ";".join(filter_parts)

        except Exception as e:
            _log_error(f"构建形态学过渡滤镜失败: {str(e)}")
            # 回退到简单的dissolve过渡
            offset_time = max(0, durations[0] - transition_duration) if durations else 0
            return f"[0:v][1:v]xfade=transition=dissolve:duration={transition_duration}:offset={offset_time}[output]"

    def _concat_with_optical_flow_transitions(self, video_paths, output_path, quality, transition_duration=0.5):
        """使用光流过渡拼接视频（最高级）"""
        try:
            import subprocess

            if len(video_paths) < 2:
                return self._concat_videos(video_paths, output_path, quality, True, transition_duration, True)

            _log_info(f"🌊 使用光流过渡拼接 {len(video_paths)} 个视频...")

            # 获取视频信息
            video_info = self._analyze_video_properties(video_paths)
            if not video_info:
                _log_error("无法分析视频属性，回退到形态学过渡")
                return self._concat_with_morphing_transitions(video_paths, output_path, quality, transition_duration, True)

            # 现在FFmpeg参数已修复，可以支持各种分辨率的光流过渡
            # 但对于超大分辨率视频，仍然建议使用快速方法以保证用户体验
            if 'target_width' in video_info and 'target_height' in video_info:
                pixels = video_info['target_width'] * video_info['target_height']
                if pixels > 2073600:  # 大于2MP (如1920x1080)，提醒用户但不强制跳过
                    _log_info(f"⚠️ 检测到超大分辨率视频 ({video_info['target_width']}x{video_info['target_height']})，光流过渡可能较慢")
                    _log_info("💡 如需快速处理，建议使用concat_advanced方法")
                    # 不再强制跳过，让用户选择

            # 尝试真正的光流过渡处理
            if len(video_paths) == 2:
                filter_complex = self._build_optical_flow_filter(video_paths, transition_duration)
            else:
                # 多视频光流过渡：使用链式光流处理
                _log_info("🌊 执行多视频光流过渡处理...")
                filter_complex = self._build_optical_flow_multiple_filter(video_paths, transition_duration)

                # 如果多视频光流滤镜构建失败，回退到高级过渡
                if filter_complex is None:
                    _log_info("🔄 多视频光流过渡构建失败，回退到高级过渡方法...")
                    return self._concat_with_advanced_transitions(video_paths, output_path, quality, transition_duration, "radial", False, False)

            inputs = []
            for video_path in video_paths:
                inputs.extend(['-i', video_path])

            quality_params = self._get_quality_params(quality)

            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-r', str(int(video_info['target_fps'])),
                '-vsync', 'cfr',
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行光流过渡命令...")

            # 为真正的光流过渡设置合理的超时时间
            video_info = self._analyze_video_properties(video_paths)

            if video_info and 'target_width' in video_info and 'target_height' in video_info:
                pixels = video_info['target_width'] * video_info['target_height']
                if pixels > 2073600:  # 大于2MP (1920x1080)
                    timeout_seconds = 600  # 10分钟，轻量级光流
                elif pixels > 800000:  # 大于0.8MP (1248x704)
                    timeout_seconds = 480  # 8分钟，标准光流
                else:
                    timeout_seconds = 300  # 5分钟，高质量光流
            else:
                timeout_seconds = 300  # 默认5分钟

            _log_info(f"⏱️ 光流过渡超时设置: {timeout_seconds}秒 (真正光流处理)")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 光流过渡拼接成功")
                return True
            else:
                _log_error(f"❌ 光流过渡拼接失败")
                if result.stderr:
                    _log_error(f"FFmpeg错误: {result.stderr[:300]}...")
                # 回退到形态学过渡
                _log_info("🔄 回退到形态学过渡方法...")
                return self._concat_with_morphing_transitions(video_paths, output_path, quality, transition_duration, True)

        except subprocess.TimeoutExpired:
            _log_error(f"⏰ 光流过渡超时 ({timeout_seconds}秒)")
            _log_info("🔄 回退到形态学过渡方法...")
            return self._concat_with_morphing_transitions(video_paths, output_path, quality, transition_duration, True)

        except Exception as e:
            _log_error(f"光流过渡拼接失败: {str(e)}")
            # 回退到形态学过渡
            return self._concat_with_morphing_transitions(video_paths, output_path, quality, transition_duration, True)

    def _build_optical_flow_filter(self, video_paths, transition_duration):
        """构建光流过渡滤镜（简化版，更稳定）"""
        try:
            # 获取视频时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        durations.append(float(result.stdout.strip()))
                    else:
                        durations.append(4.0)
                except:
                    durations.append(4.0)

            if len(durations) < 2:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            duration1, duration2 = durations[0], durations[1]
            max_transition = min(duration1, duration2) / 2
            actual_transition = min(transition_duration, max_transition)

            if actual_transition <= 0:
                return "[0:v][1:v]concat=n=2:v=1[output]"

            offset_time = duration1 - actual_transition

            # 现在提供真正的光流过渡选项
            # 用户可以选择不同级别的光流处理

            # 获取视频分辨率信息
            pixels = 1248 * 704  # 默认值
            if len(video_paths) >= 2:
                try:
                    # 尝试获取实际分辨率
                    cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_paths[0]]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and 'x' in result.stdout:
                        width, height = map(int, result.stdout.strip().split('x'))
                        pixels = width * height
                except:
                    pass

            # 根据分辨率选择光流算法复杂度
            if pixels > 2073600:  # 大于2MP (1920x1080)
                _log_info("🌊 使用轻量级光流过渡（适合大分辨率）")
                # 轻量级光流：仅使用基础运动补偿
                filter_parts = [
                    "[0:v]minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir[v0flow]",
                    "[1:v]minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir[v1flow]",
                    f"[v0flow][v1flow]xfade=transition=radial:duration={actual_transition}:offset={offset_time}[output]"
                ]
            elif pixels > 800000:  # 大于0.8MP (1248x704)
                _log_info("🌊 使用标准光流过渡（平衡质量与速度）")
                # 标准光流：中等复杂度
                filter_parts = [
                    "[0:v]minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1[v0flow]",
                    "[1:v]minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1[v1flow]",
                    f"[v0flow][v1flow]xfade=transition=radial:duration={actual_transition}:offset={offset_time}[output]"
                ]
            else:
                _log_info("🌊 使用高质量光流过渡（适合小分辨率）")
                # 高质量光流：完整算法
                filter_parts = [
                    "[0:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff[v0flow]",
                    "[1:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=fdiff[v1flow]",
                    f"[v0flow][v1flow]xfade=transition=radial:duration={actual_transition}:offset={offset_time}[output]"
                ]

            return ";".join(filter_parts)

            return ";".join(filter_parts)

        except Exception as e:
            _log_error(f"构建光流过渡滤镜失败: {str(e)}")
            # 回退到高质量的smoothleft过渡
            offset_time = max(0, durations[0] - transition_duration) if durations else 0
            return f"[0:v][1:v]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[output]"

    def _build_optical_flow_multiple_filter(self, video_paths, transition_duration):
        """构建多视频光流过渡滤镜链"""
        try:
            # 获取所有视频时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        duration = float(result.stdout.strip())
                        durations.append(duration)
                    else:
                        _log_error(f"ffprobe失败: {video_path}, 返回码: {result.returncode}")
                        _log_error(f"stderr: {result.stderr}")
                        durations.append(4.0)
                except Exception as e:
                    _log_error(f"ffprobe异常: {video_path}, 错误: {str(e)}")
                    durations.append(4.0)

            if len(durations) < 2:
                return "[0:v]concat=n=1:v=1[output]"

            # 获取视频分辨率信息用于选择光流算法复杂度
            pixels = 1248 * 704  # 默认值
            try:
                cmd = ['ffprobe', '-v', 'quiet', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'csv=s=x:p=0', video_paths[0]]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and 'x' in result.stdout:
                    width, height = map(int, result.stdout.strip().split('x'))
                    pixels = width * height
            except:
                pass

            # 根据分辨率选择光流算法复杂度
            if pixels > 2073600:  # 大于2MP (1920x1080)
                _log_info("🌊 多视频轻量级光流过渡（适合大分辨率）")
                minterpolate_params = "fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir"
            elif pixels > 800000:  # 大于0.8MP (1248x704)
                _log_info("🌊 多视频快速光流过渡（优化处理速度）")
                minterpolate_params = "fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir"  # 降低fps提高速度
            else:
                _log_info("🌊 多视频标准光流过渡（适合小分辨率）")
                minterpolate_params = "fps=48:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"

            filter_parts = []

            # 首先对所有输入视频应用光流处理
            for i in range(len(video_paths)):
                filter_parts.append(f"[{i}:v]minterpolate={minterpolate_params}[v{i}flow]")

            # 使用正确的多视频光流过渡方法：链式处理，但需要正确计算每个过渡的时长
            #
            # 关键理解：xfade的offset是相对于第一个输入的时长，而不是绝对时间
            # 每个xfade输出的长度 = offset + transition_duration

            # 第一个过渡：video1 + video2
            offset_time = durations[0] - transition_duration  # 11.5秒
            filter_parts.append(f"[v0flow][v1flow]xfade=transition=radial:duration={transition_duration}:offset={offset_time}[v01]")
            # v01的长度 = durations[0] + durations[1] - transition_duration = 23.5秒

            # 后续过渡需要重新思考：我们需要将v01和后续视频拼接
            # 但v01已经是23.5秒的完整视频，我们需要在其末尾添加新视频

            current_video_length = durations[0] + durations[1] - transition_duration  # v01的长度

            for i in range(2, len(video_paths)):
                if i == 2:
                    input_label = "v01"
                    output_label = "v02" if i < len(video_paths) - 1 else "output"
                else:
                    input_label = f"v0{i-1}"
                    output_label = f"v0{i}" if i < len(video_paths) - 1 else "output"

                # 对于后续过渡，offset应该是当前视频长度减去过渡时间
                offset_time = current_video_length - transition_duration
                filter_parts.append(f"[{input_label}][v{i}flow]xfade=transition=radial:duration={transition_duration}:offset={offset_time}[{output_label}]")

                # 更新当前视频长度：加上新视频长度，减去过渡时间
                current_video_length += durations[i] - transition_duration

            return ";".join(filter_parts)

        except Exception as e:
            _log_error(f"构建多视频光流过渡滤镜失败: {str(e)}")
            # 回退到高级过渡方法
            _log_info("🔄 光流过渡失败，回退到高级过渡方法...")
            return None  # 返回None表示需要回退

    def _concat_morphing_multiple(self, video_paths, output_path, quality, transition_duration, motion_compensation):
        """多视频形态学过渡拼接 - 保留旧方法作为备用"""
        _log_info("🔄 使用旧的递归形态学过渡方法（备用）")
        return self._concat_morphing_multiple_chain(video_paths, output_path, quality, transition_duration, motion_compensation)

    def _concat_morphing_multiple_chain(self, video_paths, output_path, quality, transition_duration, motion_compensation):
        """使用一次性滤镜链的形态学过渡拼接 - 修复时长计算"""
        try:
            import subprocess

            # 获取所有视频的时长
            durations = []
            for video_path in video_paths:
                try:
                    cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', video_path]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        durations.append(float(result.stdout.strip()))
                    else:
                        durations.append(4.0)  # 默认4秒
                except:
                    durations.append(4.0)

            if len(durations) < 2:
                return False

            # 计算过渡参数
            min_duration = min(durations)
            max_transition = min_duration / 2
            actual_transition = min(transition_duration, max_transition)

            if actual_transition <= 0:
                # 无过渡，使用简单concat
                return self._simple_concat_multiple(video_paths, output_path)

            # 构建多视频形态学滤镜链
            filter_complex = self._build_multiple_morphing_chain(video_paths, durations, actual_transition, motion_compensation)

            if not filter_complex:
                _log_error("构建多视频形态学滤镜链失败")
                return False

            # 执行FFmpeg命令
            cmd = ['ffmpeg']

            # 添加输入文件
            for video_path in video_paths:
                cmd.extend(['-i', video_path])

            # 添加滤镜和输出参数
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[output]',
                '-c:v', 'libx264',
                '-pix_fmt', 'yuv420p',
                '-preset', 'medium',
                '-crf', '23',
                '-y',
                output_path
            ])

            _log_info(f"🔧 执行多视频形态学过渡命令...")

            # 根据视频分辨率调整超时时间
            video_info = self._analyze_video_properties(video_paths)
            base_timeout = 20  # 基础20秒超时

            if video_info and 'target_width' in video_info and 'target_height' in video_info:
                pixels = video_info['target_width'] * video_info['target_height']
                if pixels > 1000000:  # 大于1MP (如1248x704)
                    timeout_seconds = 45  # 最多45秒
                elif pixels > 500000:  # 大于0.5MP
                    timeout_seconds = 30  # 30秒
                else:
                    timeout_seconds = 20  # 20秒
            else:
                timeout_seconds = 20

            _log_info(f"⏱️ 形态学过渡超时设置: {timeout_seconds}秒 (快速处理策略)")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)

            if result.returncode == 0 and os.path.exists(output_path):
                _log_info("✅ 多视频形态学过渡拼接成功")
                return True
            else:
                _log_error(f"多视频形态学过渡拼接失败: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            _log_error(f"⏰ 形态学过渡超时 ({timeout_seconds}秒)")
            return False
        except Exception as e:
            _log_error(f"多视频形态学过渡拼接异常: {str(e)}")
            return False

    def _build_multiple_morphing_chain(self, video_paths, durations, transition_duration, motion_compensation):
        """构建多视频形态学滤镜链"""
        try:
            if len(video_paths) < 2:
                return None

            if len(video_paths) == 2:
                # 两个视频的简单情况
                offset_time = durations[0] - transition_duration

                # 简化的形态学过渡滤镜
                if motion_compensation:
                    # 带运动补偿的形态学过渡
                    filter_parts = [
                        "[0:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v0smooth]",
                        "[1:v]minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc[v1smooth]",
                        f"[v0smooth][v1smooth]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[output]"
                    ]
                else:
                    # 简单的形态学过渡
                    filter_parts = [
                        "[0:v]edgedetect=low=0.1:high=0.4[v0edge]",
                        "[1:v]edgedetect=low=0.1:high=0.4[v1edge]",
                        f"[v0edge][v1edge]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[output]"
                    ]

                return ";".join(filter_parts)

            # 多个视频的复杂情况 - 使用简化的过渡效果
            filter_parts = []
            current_offset = 0

            # 第一个过渡
            offset_time = durations[0] - transition_duration
            if motion_compensation:
                filter_parts.extend([
                    "[0:v]minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc[v0smooth]",
                    "[1:v]minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc[v1smooth]",
                    f"[v0smooth][v1smooth]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[v01]"
                ])
            else:
                filter_parts.append(f"[0:v][1:v]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[v01]")

            current_offset = durations[0] + durations[1] - transition_duration

            # 后续过渡
            for i in range(2, len(video_paths)):
                input_label = f"v0{i-1}" if i == 2 else f"v0{i-1}"
                output_label = f"v0{i}" if i < len(video_paths) - 1 else "output"

                # 计算这个过渡的偏移时间
                offset_time = current_offset - transition_duration

                if motion_compensation and i == 2:  # 只对第二个过渡使用运动补偿，避免过于复杂
                    filter_parts.extend([
                        f"[{i}:v]minterpolate=fps=48:mi_mode=mci:mc_mode=aobmc[v{i}smooth]",
                        f"[{input_label}][v{i}smooth]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[{output_label}]"
                    ])
                else:
                    filter_parts.append(f"[{input_label}][{i}:v]xfade=transition=smoothleft:duration={transition_duration}:offset={offset_time}[{output_label}]")

                current_offset += durations[i] - transition_duration

            return ";".join(filter_parts)

        except Exception as e:
            _log_error(f"构建多视频形态学滤镜链失败: {str(e)}")
            return None

    def _concat_optical_flow_multiple(self, video_paths, output_path, quality, transition_duration):
        """多视频光流过渡拼接"""
        try:
            import tempfile

            temp_dir = tempfile.mkdtemp()
            intermediate_files = []

            try:
                current_video = video_paths[0]

                for i in range(1, len(video_paths)):
                    next_video = video_paths[i]
                    temp_output = os.path.join(temp_dir, f"flow_intermediate_{i}.mp4")

                    success = self._concat_with_optical_flow_transitions(
                        [current_video, next_video],
                        temp_output,
                        quality,
                        transition_duration
                    )

                    if not success:
                        _log_error(f"光流过渡中间步骤 {i} 失败")
                        return False

                    intermediate_files.append(temp_output)
                    current_video = temp_output

                # 复制最终结果
                if intermediate_files:
                    final_temp = intermediate_files[-1]
                    if os.path.exists(final_temp):
                        import shutil
                        shutil.copy2(final_temp, output_path)
                        return os.path.exists(output_path)

                return False

            finally:
                # 清理临时文件
                for temp_file in intermediate_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass
                try:
                    os.rmdir(temp_dir)
                except:
                    pass

        except Exception as e:
            _log_error(f"多视频光流过渡拼接失败: {str(e)}")
            return False

    def _hstack_videos(self, video_paths, output_path, quality, scale_videos):
        """水平拼接视频（并排显示）"""
        try:
            import subprocess

            _log_info("↔️ 使用hstack方法拼接视频...")

            if len(video_paths) > 8:
                _log_error("hstack方法最多支持8个视频")
                return False

            # 构建FFmpeg filter_complex
            inputs = []
            for i, video_path in enumerate(video_paths):
                inputs.extend(['-i', video_path])

            # 构建缩放和拼接滤镜
            if scale_videos:
                # 先缩放到统一尺寸，再水平拼接
                scale_filters = []
                for i in range(len(video_paths)):
                    scale_filters.append(f"[{i}:v]scale=640:480[v{i}]")

                hstack_filter = "[" + "][".join([f"v{i}" for i in range(len(video_paths))]) + "]hstack=inputs=" + str(len(video_paths)) + "[outv]"
                filter_complex = ";".join(scale_filters) + ";" + hstack_filter
            else:
                # 直接拼接
                input_labels = "[" + "][".join([f"{i}:v" for i in range(len(video_paths))]) + "]"
                filter_complex = input_labels + "hstack=inputs=" + str(len(video_paths)) + "[outv]"

            quality_params = self._get_quality_params(quality)
            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '0:a?',  # 使用第一个视频的音频
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行FFmpeg命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            _log_error(f"hstack拼接失败: {str(e)}")
            return False

    def _vstack_videos(self, video_paths, output_path, quality, scale_videos):
        """垂直拼接视频（上下显示）"""
        try:
            import subprocess

            _log_info("↕️ 使用vstack方法拼接视频...")

            if len(video_paths) > 8:
                _log_error("vstack方法最多支持8个视频")
                return False

            # 构建FFmpeg filter_complex
            inputs = []
            for i, video_path in enumerate(video_paths):
                inputs.extend(['-i', video_path])

            # 构建缩放和拼接滤镜
            if scale_videos:
                # 先缩放到统一尺寸，再垂直拼接
                scale_filters = []
                for i in range(len(video_paths)):
                    scale_filters.append(f"[{i}:v]scale=640:480[v{i}]")

                vstack_filter = "[" + "][".join([f"v{i}" for i in range(len(video_paths))]) + "]vstack=inputs=" + str(len(video_paths)) + "[outv]"
                filter_complex = ";".join(scale_filters) + ";" + vstack_filter
            else:
                # 直接拼接
                input_labels = "[" + "][".join([f"{i}:v" for i in range(len(video_paths))]) + "]"
                filter_complex = input_labels + "vstack=inputs=" + str(len(video_paths)) + "[outv]"

            quality_params = self._get_quality_params(quality)
            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '0:a?',  # 使用第一个视频的音频
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行FFmpeg命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            _log_error(f"vstack拼接失败: {str(e)}")
            return False

    def _grid_videos(self, video_paths, output_path, quality, grid_type, scale_videos):
        """网格拼接视频（2x2、2x3或2x4布局）"""
        try:
            import subprocess

            _log_info(f"🔲 使用{grid_type}网格方法拼接视频...")

            if grid_type == "2x2":
                max_videos = 4
            elif grid_type == "2x3":
                max_videos = 6
            elif grid_type == "2x4":
                max_videos = 8
            else:
                max_videos = 4

            if len(video_paths) > max_videos:
                _log_error(f"{grid_type}网格最多支持{max_videos}个视频")
                return False

            # 构建FFmpeg filter_complex
            inputs = []
            for i, video_path in enumerate(video_paths):
                inputs.extend(['-i', video_path])

            # 为不足的位置创建黑色视频
            while len(video_paths) < max_videos:
                video_paths.append(None)

            # 构建网格滤镜
            if scale_videos:
                # 缩放所有视频到统一尺寸
                scale_filters = []
                for i in range(len([v for v in video_paths if v is not None])):
                    scale_filters.append(f"[{i}:v]scale=320:240[v{i}]")

                # 为空位置创建黑色视频
                black_filters = []
                actual_videos = len([v for v in video_paths if v is not None])
                for i in range(actual_videos, max_videos):
                    black_filters.append(f"color=black:320x240:d=1[v{i}]")

                if grid_type == "2x2":
                    # 2x2网格布局
                    grid_filter = "[v0][v1]hstack[top];[v2][v3]hstack[bottom];[top][bottom]vstack[outv]"
                elif grid_type == "2x3":
                    # 2x3网格布局
                    grid_filter = "[v0][v1]hstack[top];[v2][v3]hstack[middle];[v4][v5]hstack[bottom];[top][middle]vstack[temp];[temp][bottom]vstack[outv]"
                else:  # 2x4
                    # 2x4网格布局
                    grid_filter = "[v0][v1]hstack[row1];[v2][v3]hstack[row2];[v4][v5]hstack[row3];[v6][v7]hstack[row4];[row1][row2]vstack[temp1];[row3][row4]vstack[temp2];[temp1][temp2]vstack[outv]"

                all_filters = scale_filters + black_filters + [grid_filter]
                filter_complex = ";".join(all_filters)
            else:
                # 不缩放，直接网格拼接（可能会有尺寸不匹配问题）
                black_filters = []
                actual_videos = len([v for v in video_paths if v is not None])
                for i in range(actual_videos, max_videos):
                    black_filters.append(f"color=black:640x480:d=1[v{i}]")

                if grid_type == "2x2":
                    grid_filter = f"[0:v][1:v]hstack[top];[2:v][3:v]hstack[bottom];[top][bottom]vstack[outv]"
                elif grid_type == "2x3":
                    grid_filter = f"[0:v][1:v]hstack[top];[2:v][3:v]hstack[middle];[4:v][5:v]hstack[bottom];[top][middle]vstack[temp];[temp][bottom]vstack[outv]"
                else:  # 2x4
                    grid_filter = f"[0:v][1:v]hstack[row1];[2:v][3:v]hstack[row2];[4:v][5:v]hstack[row3];[6:v][7:v]hstack[row4];[row1][row2]vstack[temp1];[row3][row4]vstack[temp2];[temp1][temp2]vstack[outv]"

                filter_complex = ";".join(black_filters + [grid_filter])

            quality_params = self._get_quality_params(quality)
            cmd = [
                'ffmpeg'
            ] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '[outv]',
                '-map', '0:a?',  # 使用第一个视频的音频
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行FFmpeg命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            return result.returncode == 0 and os.path.exists(output_path)

        except Exception as e:
            _log_error(f"grid拼接失败: {str(e)}")
            return False

    def _create_error_result(self, error_msg):
        """创建错误结果"""
        try:
            blank_video = create_blank_video_object()
            blank_video_path = getattr(blank_video, 'file_path', '') if blank_video else ''
            afvideo = create_video_path_wrapper(blank_video_path) if blank_video_path else create_blank_video_object()
            return (blank_video, f"❌ {error_msg}", afvideo)
        except:
            return (None, f"❌ {error_msg}", None)


class GetLastFrameNode:
    """提取任意视频尾帧的独立节点"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
            },
            "optional": {
                "output_filename": ("STRING", {"default": ""}),
                "image_quality": (["high", "medium", "low"], {"default": "high"}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("last_frame_image", "frame_path")
    FUNCTION = "extract_last_frame"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 60  # 1分钟超时

    def extract_last_frame(self, video, output_filename="", image_quality="high"):
        """
        提取视频的最后一帧

        Args:
            video: ComfyUI VIDEO对象
            output_filename: 输出文件名（可选）
            image_quality: 图像质量设置

        Returns:
            tuple: (图像张量, 图像文件路径)
        """
        try:
            _log_info("🎬 开始提取视频尾帧...")

            # 获取视频文件路径 - 使用改进的提取方法
            video_path = self._extract_video_path(video)

            if not video_path:
                error_msg = f"无法获取有效的视频文件路径: {video_path}"
                _log_error(error_msg)
                _log_error(f"视频对象详情: type={type(video)}, repr={repr(video)}")
                # 返回空白图像和错误信息
                blank_image = self._create_blank_image()
                return (blank_image, f"❌ {error_msg}")

            if not os.path.exists(video_path):
                error_msg = f"视频文件不存在: {video_path}"
                _log_error(error_msg)
                blank_image = self._create_blank_image()
                return (blank_image, f"❌ {error_msg}")

            _log_info(f"📹 视频文件路径: {video_path}")

            # 生成输出文件路径
            if not output_filename:
                video_name = os.path.splitext(os.path.basename(video_path))[0]
                output_filename = f"{video_name}_last_frame.jpg"

            # 确保输出文件名有正确的扩展名
            if not output_filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                output_filename += '.jpg'

            # 使用临时目录
            import tempfile
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"{int(time.time())}_{output_filename}")

            # 设置图像质量参数
            quality_settings = {
                "high": ["-q:v", "2"],      # 高质量
                "medium": ["-q:v", "5"],    # 中等质量
                "low": ["-q:v", "8"]        # 低质量
            }
            quality_params = quality_settings.get(image_quality, quality_settings["high"])

            # 提取尾帧
            frame_path = self._extract_frame_with_ffmpeg(video_path, output_path, quality_params)

            if not frame_path:
                error_msg = "尾帧提取失败"
                _log_error(error_msg)
                blank_image = self._create_blank_image()
                return (blank_image, f"❌ {error_msg}")

            # 将图像转换为ComfyUI张量格式
            image_tensor = self._load_image_as_tensor(frame_path)

            if image_tensor is None:
                error_msg = "图像加载失败"
                _log_error(error_msg)
                blank_image = self._create_blank_image()
                return (blank_image, f"❌ {error_msg}")

            _log_info(f"✅ 尾帧提取成功: {frame_path}")
            return (image_tensor, frame_path)

        except Exception as e:
            error_msg = f"提取视频尾帧失败: {str(e)}"
            _log_error(error_msg)
            blank_image = self._create_blank_image()
            return (blank_image, f"❌ {error_msg}")

    def _extract_frame_with_ffmpeg(self, video_path, output_path, quality_params):
        """使用FFmpeg提取尾帧"""
        try:
            import subprocess

            # 方法1：使用select=eof过滤器
            cmd1 = [
                'ffmpeg',
                '-i', video_path,
                '-vf', 'select=eof',
                '-vsync', 'vfr',
                '-frames:v', '1',
            ] + quality_params + [
                '-y',
                output_path
            ]

            _log_info(f"🔧 执行FFmpeg命令: {' '.join(cmd1)}")

            result = subprocess.run(
                cmd1,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            if result.returncode == 0 and os.path.exists(output_path):
                return output_path

            # 方法2：备用时长计算方法
            _log_info("🔄 尝试备用方法...")

            # 获取视频时长
            duration_cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                video_path
            ]

            duration_result = subprocess.run(
                duration_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if duration_result.returncode == 0:
                try:
                    duration = float(duration_result.stdout.strip())
                    seek_time = max(0, duration - 0.1)

                    cmd2 = [
                        'ffmpeg',
                        '-ss', str(seek_time),
                        '-i', video_path,
                        '-frames:v', '1',
                    ] + quality_params + [
                        '-y',
                        output_path
                    ]

                    result = subprocess.run(
                        cmd2,
                        capture_output=True,
                        text=True,
                        timeout=self.timeout
                    )

                    if result.returncode == 0 and os.path.exists(output_path):
                        return output_path
                except:
                    pass

            return None

        except Exception as e:
            _log_error(f"FFmpeg提取失败: {str(e)}")
            return None

    def _load_image_as_tensor(self, image_path):
        """将图像文件加载为ComfyUI张量格式"""
        try:
            from PIL import Image
            import numpy as np
            import torch

            # 使用PIL加载图像
            with Image.open(image_path) as img:
                # 转换为RGB格式
                if img.mode != 'RGB':
                    img = img.convert('RGB')

                # 转换为numpy数组
                img_array = np.array(img).astype(np.float32) / 255.0

                # 添加batch维度 [H, W, C] -> [1, H, W, C]
                img_array = np.expand_dims(img_array, axis=0)

                # 转换为torch张量（ComfyUI期望的格式）
                img_tensor = torch.from_numpy(img_array)

                _log_info(f"✅ 图像张量格式: {img_tensor.shape}, dtype: {img_tensor.dtype}")
                return img_tensor

        except Exception as e:
            _log_error(f"图像加载失败: {str(e)}")
            return None

    def _extract_video_path(self, video):
        """从VIDEO对象提取文件路径"""
        _log_info(f"🔍 尝试从VIDEO对象提取路径: {type(video)}")

        # 如果是字符串，直接返回
        if isinstance(video, str):
            _log_info(f"✅ 直接字符串路径: {video}")
            return video

        # 尝试常见的文件路径属性
        path_attributes = [
            'file_path',    # 我们自己的VideoFromFile对象
            'filename',     # 一些节点使用这个
            'file',         # 向后兼容
            'path',         # 通用路径属性
            'filepath',     # 文件路径
            'video_path',   # 视频路径
            'source',       # 源文件
            'url',          # URL路径
            'video_file',   # 视频文件
            'file_name',    # 文件名
        ]

        for attr in path_attributes:
            if hasattr(video, attr):
                value = getattr(video, attr)
                if value and isinstance(value, str):
                    _log_info(f"✅ 从属性 {attr} 获取路径: {value}")
                    return value
                elif value:
                    _log_info(f"⚠️ 属性 {attr} 存在但不是字符串: {type(value)} = {value}")

        # 如果是字典类型，尝试从字典中获取路径
        if isinstance(video, dict):
            for key in ['file_path', 'filename', 'path', 'url', 'source']:
                if key in video and isinstance(video[key], str):
                    _log_info(f"✅ 从字典键 {key} 获取路径: {video[key]}")
                    return video[key]

        # 如果有__dict__属性，打印所有属性用于调试
        if hasattr(video, '__dict__'):
            _log_info(f"🔍 VIDEO对象属性: {list(video.__dict__.keys())}")
            for key, value in video.__dict__.items():
                if isinstance(value, str) and ('path' in key.lower() or 'file' in key.lower() or 'url' in key.lower()):
                    _log_info(f"✅ 从__dict__属性 {key} 获取路径: {value}")
                    return value

        # 最后尝试：如果对象可以转换为字符串且看起来像路径
        try:
            str_repr = str(video)
            if str_repr and ('/' in str_repr or '\\' in str_repr or str_repr.endswith('.mp4')):
                _log_info(f"✅ 从字符串表示获取路径: {str_repr}")
                return str_repr
        except:
            pass

        _log_error(f"❌ 无法从VIDEO对象提取路径，对象类型: {type(video)}")
        return None

    def _create_blank_image(self):
        """创建空白图像张量"""
        try:
            import numpy as np
            import torch
            # 创建512x512的黑色图像
            blank_array = np.zeros((1, 512, 512, 3), dtype=np.float32)
            # 转换为torch张量（ComfyUI期望的格式）
            blank_tensor = torch.from_numpy(blank_array)
            return blank_tensor
        except:
            return None






class DoubaoSeed16Node:
    """豆包大模型文本生成节点 - 支持doubao-seed-1.6和doubao-seed-1.6-flash模型"""

    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = []
        
        # 只显示支持文本生成的镜像站
        for site_name, site_config in mirror_sites.items():
            text_models = site_config.get('text_models', [])
            if text_models:  # 如果有文本模型，则支持文本生成
                mirror_options.append(site_name)
        
        if not mirror_options:
            mirror_options = ["comfly", "volcengine"]
        
        return {
            "required": {
                "prompt": ("STRING", {"multiline": True, "default": "请介绍一下人工智能的发展历程"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "model": (["doubao-seed-1-6-250615", "doubao-seed-1-6-flash-250615", "doubao-seed-1-6-flash-250828"], {"default": "doubao-seed-1-6-250615"}),
                "api_key": ("STRING", {"default": ""}),
                "max_tokens": ("INT", {"default": 1000, "min": 1, "max": 4000, "step": 1}),
                "temperature": ("FLOAT", {"default": 0.7, "min": 0.0, "max": 2.0, "step": 0.1}),
                "top_p": ("FLOAT", {"default": 0.9, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True, "default": "你是一个有帮助的AI助手，擅长文本生成和内容创作。"}),
                "stream": ("BOOLEAN", {"default": False}),
                "presence_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1}),
                "frequency_penalty": ("FLOAT", {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("generated_text", "response_info", "usage_info")
    FUNCTION = "generate_text"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 300  # 5分钟超时（故事生成需要更长时间）

    def generate_text(self, prompt, mirror_site="comfly", model="doubao-seed-1-6-250615", api_key="", max_tokens=1000, 
                     temperature=0.7, top_p=0.9, system_prompt="你是一个有帮助的AI助手，擅长文本生成和内容创作。", 
                     stream=False, presence_penalty=0.0, frequency_penalty=0.0):
        """
        调用豆包大模型进行文本生成

        Args:
            prompt: 用户输入的提示词
            mirror_site: 镜像站选择 (comfly, t8_mirror, volcengine)
            model: 模型名称 (doubao-seed-1-6-250615, doubao-seed-1-6-flash-250615, doubao-seed-1-6-flash-250828)
            api_key: API密钥
            max_tokens: 最大生成token数
            temperature: 温度参数，控制随机性
            top_p: 核采样参数
            system_prompt: 系统提示词
            stream: 是否流式输出
            presence_penalty: 存在惩罚
            frequency_penalty: 频率惩罚

        Returns:
            tuple: (生成的文本, 响应信息, 使用情况信息)
        """
        try:
            _log_info(f"🤖 开始调用豆包大模型 {model} 进行文本生成...")
            _log_info(f"📝 提示词: {prompt[:100]}...")
            _log_info(f"🌐 使用镜像站: {mirror_site}")

            # 获取镜像站配置
            site_config = get_mirror_site_config(mirror_site)
            api_url = site_config.get("url", "").strip()
            api_format = site_config.get("api_format", "comfly")

            # 使用配置里的API格式；不再强制改写，避免端点和格式不一致
            _log_info(f"🔧 API格式: {api_format}")

            # 使用镜像站的API key（如果提供了的话）
            if site_config.get("api_key") and not api_key.strip():
                api_key = site_config.get("api_key")
                _log_info(f"🔑 使用镜像站API密钥: {api_key[:10]}...")

            # 获取API密钥
            if not api_key:
                api_key = self._get_api_key()
                if not api_key:
                    error_msg = "未提供API密钥，请在节点中设置或配置环境变量DOUBAO_API_KEY"
                    _log_error(error_msg)
                    return ("", f"❌ {error_msg}", "")

            # 构建请求数据
            request_data = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "stream": stream,
                "presence_penalty": presence_penalty,
                "frequency_penalty": frequency_penalty
            }

            # 调用API
            response = self._call_doubao_api(api_url, api_key, request_data, stream, api_format)
            
            if response is None:
                error_msg = "API调用失败"
                _log_error(error_msg)
                return ("", f"❌ {error_msg}", "")

            # 解析响应
            generated_text, response_info, usage_info = self._parse_response(response, stream)
            
            _log_info(f"✅ 文本生成成功，长度: {len(generated_text)} 字符")
            return (generated_text, response_info, usage_info)

        except Exception as e:
            error_msg = f"文本生成失败: {str(e)}"
            _log_error(error_msg)
            return ("", f"❌ {error_msg}", "")

    def _get_api_key(self):
        """获取API密钥"""
        # 优先从环境变量获取
        import os
        api_key = os.getenv('DOUBAO_API_KEY')
        if api_key:
            return api_key
        
        # 从配置文件获取
        try:
            import json
            config_path = os.path.join(os.path.dirname(__file__), 'SeedReam4_config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('doubao_api_key', '')
        except:
            pass
        
        return ""

    def _call_doubao_api(self, api_url, api_key, request_data, stream=False, api_format="volcengine"):
        """调用豆包大模型API"""
        try:
            import requests
            import json

            # 按格式构建端点
            if api_format == "volcengine":
                # 火山引擎官方: 基础是 /api/v3
                # chat 走 /chat/completions
                if api_url.endswith('/'):
                    api_url = api_url + 'chat/completions'
                elif api_url.endswith('/api/v3'):
                    api_url = api_url + '/chat/completions'
                elif api_url.endswith('/api/v3/'):
                    api_url = api_url + 'chat/completions'
                elif not api_url.endswith('/chat/completions'):
                    api_url = api_url.rstrip('/') + '/chat/completions'
            else:
                # 其它镜像按其自身（如 comfly 的 /v1/chat/completions）
                if not api_url.endswith('/chat/completions'):
                    api_url = api_url.rstrip('/') + '/chat/completions'
            
            # 设置请求头
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "ComfyUI-Doubao-Seed/2.0.0"
            }

            _log_info(f"🌐 调用API: {api_url}")
            _log_info(f"📊 请求参数: model={request_data['model']}, max_tokens={request_data['max_tokens']}")
            _log_info(f"🔧 API格式: {api_format}")

            # 发送请求
            response = requests.post(
                api_url,
                headers=headers,
                json=request_data,
                timeout=self.timeout
            )

            if response.status_code == 200:
                _log_info("✅ API调用成功")
                try:
                    return response.json()
                except json.JSONDecodeError as e:
                    _log_error(f"❌ JSON解析失败: {e}")
                    _log_error(f"响应内容: {response.text[:500]}...")
                    return None
            else:
                _log_error(f"❌ API调用失败: {response.status_code}")
                _log_error(f"响应内容: {response.text}")
                return None

        except requests.exceptions.Timeout:
            _log_error("❌ API调用超时")
            return None
        except requests.exceptions.RequestException as e:
            _log_error(f"❌ 网络请求失败: {str(e)}")
            return None
        except Exception as e:
            _log_error(f"❌ API调用异常: {str(e)}")
            return None

    def _parse_response(self, response, stream=False):
        """解析API响应"""
        try:
            if stream:
                # 流式响应处理
                generated_text = ""
                for line in response.get('data', []):
                    if 'choices' in line and len(line['choices']) > 0:
                        delta = line['choices'][0].get('delta', {})
                        if 'content' in delta:
                            generated_text += delta['content']
                
                response_info = f"流式生成完成，共 {len(generated_text)} 字符"
                usage_info = "流式模式，无使用统计"
            else:
                # 普通响应处理
                choices = response.get('choices', [])
                if not choices:
                    return ("", "❌ 响应中无生成内容", "")
                
                generated_text = choices[0].get('message', {}).get('content', "")
                
                # 构建响应信息
                response_info = f"模型: {response.get('model', 'unknown')}\n"
                response_info += f"生成完成，共 {len(generated_text)} 字符"
                
                # 构建使用情况信息
                usage = response.get('usage', {})
                usage_info = f"Token使用情况:\n"
                usage_info += f"- 提示词tokens: {usage.get('prompt_tokens', 0)}\n"
                usage_info += f"- 生成tokens: {usage.get('completion_tokens', 0)}\n"
                usage_info += f"- 总tokens: {usage.get('total_tokens', 0)}"

            return (generated_text, response_info, usage_info)

        except Exception as e:
            _log_error(f"❌ 响应解析失败: {str(e)}")
            return ("", f"❌ 响应解析失败: {str(e)}", "")


class DoubaoComicBookNode:
    """豆包连环画创作节点 - 集成文本生成和图像生成，创作完整连环画"""

    @classmethod
    def INPUT_TYPES(cls):
        config = get_seedream4_config()
        mirror_sites = config.get('mirror_sites', {})
        mirror_options = []
        
        # 只显示支持文本生成的镜像站
        for site_name, site_config in mirror_sites.items():
            text_models = site_config.get('text_models', [])
            if text_models:  # 如果有文本模型，则支持文本生成
                mirror_options.append(site_name)
        
        if not mirror_options:
            mirror_options = ["comfly", "volcengine"]
        
        return {
            "required": {
                "story_prompt": ("STRING", {"multiline": True, "default": "一个关于小兔子冒险的温馨故事"}),
                "mirror_site": (mirror_options, {"default": mirror_options[0]}),
                "text_model": (["doubao-seed-1-6-250615", "doubao-seed-1-6-flash-250615", "doubao-seed-1-6-flash-250828"], {"default": "doubao-seed-1-6-250615"}),
                "image_model": (["doubao-seedream-4-0-250828"], {"default": "doubao-seedream-4-0-250828"}),
                "story_length": (["short", "medium", "long"], {"default": "medium"}),
                "image_style": (["realistic", "cartoon", "anime", "watercolor", "sketch"], {"default": "cartoon"}),
                "resolution": (["1K", "2K", "4K"], {"default": "2K"}),
                "aspect_ratio": (["1:1", "4:3", "3:4", "16:9", "9:16"], {"default": "4:3"}),
                "watermark": ("BOOLEAN", {"default": False}),  # 水印控制，默认不显示
                "api_key": ("STRING", {"default": ""}),
                "max_tokens": ("INT", {"default": 2000, "min": 500, "max": 4000, "step": 100}),
                "temperature": ("FLOAT", {"default": 0.8, "min": 0.0, "max": 2.0, "step": 0.1}),
            },
            "optional": {
                "reference_images": ("IMAGE",),  # 最多10张参考图片
                "reference_image_2": ("IMAGE",),  # 参考图片2
                "reference_image_3": ("IMAGE",),  # 参考图片3
                "reference_image_4": ("IMAGE",),  # 参考图片4
                "reference_image_5": ("IMAGE",),  # 参考图片5
                "reference_image_6": ("IMAGE",),  # 参考图片6
                "reference_image_7": ("IMAGE",),  # 参考图片7
                "reference_image_8": ("IMAGE",),  # 参考图片8
                "reference_image_9": ("IMAGE",),  # 参考图片9
                "reference_image_10": ("IMAGE",),  # 参考图片10
                "character_description": ("STRING", {"multiline": True, "default": ""}),
                "background_style": ("STRING", {"multiline": True, "default": ""}),
                "story_theme": ("STRING", {"multiline": True, "default": ""}),
                "sequential_generation": (["disabled", "auto"], {"default": "auto"}),
            }
        }

    # 输出支持：
    # - IMAGE_BATCH: 按场景返回图像批次，便于在ComfyUI中分页浏览
    # - STRING: 返回完整故事文本、结构化JSON和生成信息
    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("comic_images", "story_text", "story_structure", "generation_info")
    FUNCTION = "create_comic_book"
    CATEGORY = "Ken-Chen/Doubao"

    def __init__(self):
        self.timeout = 600  # 10分钟超时，连环画创作需要更长时间
        self.config = get_seedream4_config()
        self.max_retries = 3  # 最大重试次数

    def create_comic_book(self, story_prompt, mirror_site="comfly", text_model="doubao-seed-1-6-250615", 
                         image_model="doubao-seedream-4-0-250828", story_length="medium", image_style="cartoon",
                         resolution="2K", aspect_ratio="4:3", api_key="", max_tokens=2000, temperature=0.8,
                         reference_images=None, reference_image_2=None, reference_image_3=None, reference_image_4=None,
                         reference_image_5=None, reference_image_6=None, reference_image_7=None, reference_image_8=None,
                         reference_image_9=None, reference_image_10=None, character_description="", background_style="",
                         story_theme="", watermark=False, sequential_generation="auto"):
        """
        创建连环画故事书

        Args:
            story_prompt: 故事提示词
            mirror_site: 镜像站选择
            text_model: 文本生成模型
            image_model: 图像生成模型
            story_length: 故事长度 (short/medium/long)
            image_style: 图像风格
            resolution: 图像分辨率
            aspect_ratio: 宽高比
            api_key: API密钥
            max_tokens: 最大token数
            temperature: 温度参数
            reference_images: 参考图片（最多10张）
            character_description: 角色描述
            background_style: 背景风格
            story_theme: 故事主题
            watermark: 是否添加水印
            sequential_generation: 顺序生成模式

        Returns:
            tuple: (连环画图像, 故事文本, 故事结构, 生成信息)
        """
        try:
            _log_info("📚 开始创作连环画故事书...")
            _log_info(f"📝 故事提示: {story_prompt[:100]}...")
            _log_info(f"🎨 图像风格: {image_style}, 分辨率: {resolution}")

            # 收集所有参考图片
            all_reference_images = self._collect_reference_images(
                reference_images, reference_image_2, reference_image_3, reference_image_4,
                reference_image_5, reference_image_6, reference_image_7, reference_image_8,
                reference_image_9, reference_image_10
            )
            _log_info(f"🖼️ 收集到 {len(all_reference_images)} 张参考图片")

            # 1. 生成故事结构
            story_structure = self._generate_story_structure(
                story_prompt, mirror_site, text_model, story_length, 
                character_description, background_style, story_theme, 
                api_key, temperature, max_tokens
            )

            if not story_structure:
                error_msg = "故事结构生成失败，使用默认故事结构"
                _log_warning(error_msg)
                # 创建默认故事结构作为降级方案
                story_structure = self._create_default_story_structure(story_prompt, story_length)

            # 2. 解析故事结构，生成场景描述
            scenes = self._parse_story_structure(story_structure)
            _log_info(f"📖 解析出 {len(scenes)} 个场景")

            # 若场景数过少，则根据故事长度进行扩展，确保能分页浏览
            desired_counts = {"short": 3, "medium": 6, "long": 9}
            desired = desired_counts.get(story_length, 6)
            if len(scenes) < desired and len(scenes) > 0:
                base_len = len(scenes)
                _log_warning(f"场景数不足 {desired}，将从 {base_len} 扩展...")
                i = 0
                while len(scenes) < desired:
                    src = scenes[i % base_len]
                    clone = {
                        "scene_number": len(scenes) + 1,
                        "title": f"{src.get('title','场景')} · 变体 {len(scenes)+1-base_len}",
                        "description": f"{src.get('description','')} (variation {len(scenes)+1-base_len})",
                        "dialogue": src.get('dialogue', ''),
                        "narration": src.get('narration', '')
                    }
                    scenes.append(clone)
                    i += 1
                _log_info(f"✅ 场景已扩展至 {len(scenes)} 个")

            # 3. 生成每个场景的图像
            comic_images = []
            generation_info = f"连环画创作完成\n故事长度: {story_length}\n图像风格: {image_style}\n分辨率: {resolution}\n场景数量: {len(scenes)}\n"

            for i, scene in enumerate(scenes):
                _log_info(f"🎬 生成第 {i+1}/{len(scenes)} 个场景: {scene['title']}")
                
                # 生成场景图像
                scene_image = self._generate_scene_image(
                    scene, mirror_site, image_model, image_style, 
                    resolution, aspect_ratio, all_reference_images, 
                    watermark, api_key, i
                )
                
                if scene_image is not None:
                    comic_images.append(scene_image)
                    generation_info += f"场景 {i+1}: ✅ 生成成功\n"
                else:
                    generation_info += f"场景 {i+1}: ❌ 生成失败\n"

            if not comic_images:
                error_msg = "所有场景图像生成失败，创建默认图像"
                _log_warning(error_msg)
                # 创建默认图像作为降级方案
                final_comic = self._create_default_comic_image(aspect_ratio)
                generation_info += "⚠️ 使用默认图像作为降级方案\n"
            else:
                # 4. 组合所有图像为连环画批次（不拼接，按批次输出以便分页浏览）
                final_comic = self._stack_images_as_batch(comic_images)
            
            _log_info(f"✅ 连环画创作完成，共生成 {len(comic_images)} 个场景")
            return (final_comic, story_structure, self._format_story_structure(scenes), generation_info)

        except Exception as e:
            error_msg = f"连环画创作失败: {str(e)}"
            _log_error(error_msg)
            return (None, "", "", f"❌ {error_msg}")

    def _collect_reference_images(self, *reference_images):
        """收集所有非空的参考图片"""
        try:
            all_images = []
            for img in reference_images:
                if img is not None:
                    all_images.append(img)
            return all_images
        except Exception as e:
            _log_error(f"收集参考图片失败: {str(e)}")
            return []

    def _create_default_story_structure(self, story_prompt, story_length):
        """创建默认故事结构作为降级方案"""
        try:
            # 根据故事长度确定场景数量
            scene_counts = {"short": 3, "medium": 5, "long": 8}
            scene_count = scene_counts.get(story_length, 5)

            # 提取故事主题关键词（简单处理）
            theme = story_prompt[:30] if len(story_prompt) > 30 else story_prompt

            # 创建简单的故事结构
            story_structure = {
                "title": f"{theme}的故事",
                "summary": f"这是一个温馨的故事。",
                "scenes": []
            }

            # 创建更合理的默认场景描述
            default_scenes = [
                {
                    "title": "开始",
                    "description": "故事的开始，介绍主要角色和场景",
                    "dialogue": "让我们开始这个故事吧！",
                    "narration": "在一个美好的日子里，故事开始了..."
                },
                {
                    "title": "发展",
                    "description": "故事情节的发展，角色开始行动",
                    "dialogue": "我们一起去冒险吧！",
                    "narration": "角色们踏上了新的旅程..."
                },
                {
                    "title": "高潮",
                    "description": "故事的高潮部分，遇到挑战",
                    "dialogue": "我们一定能克服困难！",
                    "narration": "在关键时刻，角色们展现了勇气..."
                },
                {
                    "title": "转折",
                    "description": "故事的转折点，问题得到解决",
                    "dialogue": "太好了，我们成功了！",
                    "narration": "经过努力，问题终于解决了..."
                },
                {
                    "title": "结局",
                    "description": "故事的结局，圆满收场",
                    "dialogue": "这真是一次美好的经历！",
                    "narration": "故事在温馨的氛围中结束了..."
                }
            ]

            # 根据场景数量选择合适的默认场景
            for i in range(scene_count):
                if i < len(default_scenes):
                    scene = default_scenes[i].copy()
                else:
                    # 如果需要更多场景，使用通用模板
                    scene = {
                        "title": f"场景 {i + 1}",
                        "description": f"故事继续发展，展现更多精彩内容",
                        "dialogue": f"角色们继续他们的故事...",
                        "narration": f"在这个场景中，故事继续展开..."
                    }

                scene["scene_number"] = i + 1
                story_structure["scenes"].append(scene)

            _log_warning(f"⚠️ 使用默认故事结构（文本生成可能失败），包含 {scene_count} 个场景")
            _log_warning(f"⚠️ 建议检查API配置和网络连接，以获得更好的故事内容")
            return story_structure

        except Exception as e:
            _log_error(f"创建默认故事结构失败: {str(e)}")
            return None

    def _create_default_comic_image(self, aspect_ratio):
        """创建默认连环画图像作为降级方案"""
        try:
            import torch
            import numpy as np
            
            # 根据宽高比确定图像尺寸
            aspect_ratios = {
                "1:1": (512, 512),
                "4:3": (512, 384),
                "3:4": (384, 512),
                "16:9": (512, 288),
                "9:16": (288, 512)
            }
            
            width, height = aspect_ratios.get(aspect_ratio, (512, 384))
            
            # 创建默认图像（白色背景，黑色文字提示）
            default_image = torch.ones((1, height, width, 3), dtype=torch.float32)
            
            _log_info(f"🖼️ 创建默认连环画图像，尺寸: {width}x{height}")
            return default_image
            
        except Exception as e:
            _log_error(f"创建默认图像失败: {str(e)}")
            # 返回最小的有效图像
            return torch.ones((1, 256, 256, 3), dtype=torch.float32)

    def _generate_story_structure(self, story_prompt, mirror_site, text_model, story_length, 
                                 character_description, background_style, story_theme, api_key, temperature, max_tokens):
        """生成故事结构"""
        for attempt in range(self.max_retries):
            try:
                _log_info(f"📝 尝试生成故事结构 (第 {attempt + 1}/{self.max_retries} 次)")
                
                # 构建系统提示词
                system_prompt = f"""你是一个专业的儿童故事创作专家，擅长创作连环画故事。请根据用户的要求创作一个结构化的故事。

故事要求：
- 故事长度：{story_length}（short: 3-5个场景，medium: 6-10个场景，long: 11-15个场景）
- 角色描述：{character_description if character_description else "根据故事内容自由创作"}
- 背景风格：{background_style if background_style else "根据故事内容自由创作"}
- 故事主题：{story_theme if story_theme else "温馨、积极向上"}

⚠️ 重要：请严格按照以下JSON格式输出，不要添加任何额外的文字说明或markdown标记：

{{
    "title": "故事标题",
    "summary": "故事简介",
    "scenes": [
        {{
            "scene_number": 1,
            "title": "场景标题",
            "description": "场景描述（用于图像生成）",
            "dialogue": "对话内容（如果有）",
            "narration": "旁白内容"
        }}
    ]
}}

JSON格式要求：
1. 所有字符串值必须用双引号包裹
2. 字符串中的引号必须转义为 \\"
3. 不要在字符串中使用换行符
4. 确保所有括号正确闭合
5. 数组最后一个元素后不要有逗号
6. 只输出JSON，不要有其他文字

请确保每个场景的描述都适合图像生成，包含具体的视觉元素。"""

                # 调用文本生成API
                text_node = DoubaoSeed16Node()
                generated_text, _, _ = text_node.generate_text(
                    prompt=story_prompt,
                    mirror_site=mirror_site,
                    model=text_model,
                    api_key=api_key,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system_prompt=system_prompt
                )

                if generated_text and len(generated_text.strip()) > 0:
                    _log_info("✅ 故事结构生成成功")
                    return generated_text
                else:
                    _log_warning(f"第 {attempt + 1} 次尝试返回空结果")

            except Exception as e:
                _log_error(f"第 {attempt + 1} 次故事结构生成失败: {str(e)}")
                if attempt == self.max_retries - 1:
                    _log_error("所有重试尝试都失败了")
                    return None
                else:
                    _log_info(f"等待 {2 ** attempt} 秒后重试...")
                    import time
                    time.sleep(2 ** attempt)  # 指数退避

        return None

    def _parse_story_structure(self, story_structure):
        """解析故事结构"""
        try:
            import json
            import re

            _log_info(f"🔍 开始解析故事结构，类型: {type(story_structure)}")

            # 允许直接传 dict
            if isinstance(story_structure, dict):
                data = story_structure
                _log_info("✅ 故事结构已经是字典格式")
            else:
                # 打印前100个字符用于调试
                preview = str(story_structure)[:100] if story_structure else "空"
                _log_info(f"🔍 故事结构字符串预览: {preview}")

                # 预处理：移除markdown代码块标记
                story_str = str(story_structure).strip()
                if story_str.startswith("```"):
                    lines = story_str.split('\n')
                    if len(lines) > 1:
                        story_str = '\n'.join(lines[1:])
                        if story_str.endswith("```"):
                            story_str = story_str[:-3].strip()
                    _log_info("✅ 移除了markdown代码块标记")

                # 尝试提取JSON部分
                json_match = re.search(r'\{.*\}', story_str, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group())
                        _log_info("✅ JSON解析成功")
                    except json.JSONDecodeError as je:
                        _log_warning(f"⚠️ JSON解析失败: {je}")
                        data = None
                else:
                    _log_warning("⚠️ 未找到JSON对象")
                    data = None

            if data is None:
                # 如果无法解析JSON，尝试按行解析
                _log_info("🔄 尝试按行解析故事结构")
                lines = story_structure.split('\n') if isinstance(story_structure, str) else []
                scenes = []
                current_scene = {}

                for line in lines:
                    line = line.strip()
                    if '场景' in line or 'Scene' in line.lower():
                        if current_scene:
                            scenes.append(current_scene)
                        current_scene = {
                            'title': line,
                            'description': '',
                            'dialogue': '',
                            'narration': ''
                        }
                    elif current_scene and line:
                        if not current_scene['description']:
                            current_scene['description'] = line
                        elif not current_scene['dialogue']:
                            current_scene['dialogue'] = line

                if current_scene:
                    scenes.append(current_scene)

                _log_info(f"✅ 按行解析出 {len(scenes)} 个场景")
                return scenes
            else:
                scenes = data.get('scenes', [])
                _log_info(f"✅ 从JSON解析出 {len(scenes)} 个场景")
                return scenes

        except Exception as e:
            _log_error(f"故事结构解析失败: {str(e)}")
            import traceback
            _log_error(f"详细错误: {traceback.format_exc()}")
            return []

    def _generate_scene_image(self, scene, mirror_site, image_model, image_style, 
                             resolution, aspect_ratio, reference_images, watermark, api_key, scene_index=0):
        """生成场景图像"""
        for attempt in range(self.max_retries):
            try:
                _log_info(f"🎨 尝试生成场景图像 (第 {attempt + 1}/{self.max_retries} 次)")
                
                # 构建图像生成提示词
                image_prompt = f"{scene['description']}, {image_style} style, high quality, detailed"
                
                # 选择参考图片（循环使用多张参考图片）
                selected_reference = None
                if reference_images and len(reference_images) > 0:
                    selected_reference = reference_images[scene_index % len(reference_images)]
                    _log_info(f"🎨 使用参考图片 {scene_index % len(reference_images) + 1}/{len(reference_images)}")
                
                # 调用图像生成API
                image_node = SeedReam4APISingleNode()
                generated_image, _, _ = image_node.generate_image(
                    prompt=image_prompt,
                    mirror_site=mirror_site,
                    model=image_model,
                    resolution=resolution,
                    aspect_ratio=aspect_ratio,
                    api_key=api_key,
                    watermark=watermark,
                    image=selected_reference
                )
                
                if generated_image is not None:
                    _log_info("✅ 场景图像生成成功")
                    return generated_image
                else:
                    _log_warning(f"第 {attempt + 1} 次尝试返回空图像")

            except Exception as e:
                _log_error(f"第 {attempt + 1} 次场景图像生成失败: {str(e)}")
                if attempt == self.max_retries - 1:
                    _log_error("所有重试尝试都失败了")
                    return None
                else:
                    _log_info(f"等待 {2 ** attempt} 秒后重试...")
                    import time
                    time.sleep(2 ** attempt)  # 指数退避

        return None

    def _combine_comic_images(self, comic_images, aspect_ratio):
        """组合连环画图像"""
        try:
            if not comic_images:
                return None
            
            # 简单的图像组合逻辑
            # 这里可以根据需要实现更复杂的布局
            return comic_images[0]  # 暂时返回第一张图像

        except Exception as e:
            _log_error(f"图像组合失败: {str(e)}")
            return None

    def _stack_images_as_batch(self, images):
        """将多张图像堆叠为ComfyUI可识别的图像批次 (B,H,W,C)，自动调整尺寸"""
        try:
            import torch
            import torch.nn.functional as F

            # 过滤有效图像
            valid = [img for img in images if img is not None]
            if not valid:
                _log_error("没有有效的图像可以堆叠")
                return None

            # 收集所有张量
            tensors = []
            for i, img in enumerate(valid):
                if isinstance(img, torch.Tensor) and img.ndim == 4 and img.shape[0] == 1:
                    tensors.append(img)
                    _log_info(f"📊 图像 {i+1} 尺寸: {img.shape}")
                else:
                    _log_warning(f"⚠️ 图像 {i+1} 格式不正确，跳过")

            if not tensors:
                _log_error("没有有效的张量可以堆叠")
                return None

            # 检查所有图像尺寸是否一致
            shapes = [t.shape for t in tensors]
            if len(set(shapes)) > 1:
                _log_warning(f"⚠️ 检测到不同尺寸的图像: {shapes}")

                # 找到最常见的尺寸作为目标尺寸
                from collections import Counter
                shape_counts = Counter(shapes)
                target_shape = shape_counts.most_common(1)[0][0]
                target_h, target_w = target_shape[1], target_shape[2]

                _log_info(f"🔧 将所有图像调整为目标尺寸: {target_h}x{target_w}")

                # 调整所有图像到目标尺寸
                resized_tensors = []
                for i, tensor in enumerate(tensors):
                    if tensor.shape != target_shape:
                        # 调整尺寸 (1, H, W, C) -> (1, C, H, W) -> resize -> (1, H, W, C)
                        _log_info(f"🔧 调整图像 {i+1} 从 {tensor.shape} 到 {target_shape}")

                        # 转换为 (1, C, H, W) 格式
                        tensor_chw = tensor.permute(0, 3, 1, 2)

                        # 使用双线性插值调整尺寸
                        resized = F.interpolate(
                            tensor_chw,
                            size=(target_h, target_w),
                            mode='bilinear',
                            align_corners=False
                        )

                        # 转换回 (1, H, W, C) 格式
                        resized = resized.permute(0, 2, 3, 1)
                        resized_tensors.append(resized)
                    else:
                        resized_tensors.append(tensor)

                tensors = resized_tensors

            # 堆叠所有图像
            batch = torch.cat(tensors, dim=0).contiguous()
            _log_info(f"📚 已堆叠为图像批次，数量: {batch.shape[0]}, 形状: {batch.shape}")
            return batch

        except Exception as e:
            _log_error(f"堆叠图像批次失败: {str(e)}")
            import traceback
            _log_error(traceback.format_exc())

            # 如果堆叠失败，至少返回第一张图像
            try:
                if images and len(images) > 0 and images[0] is not None:
                    _log_warning("⚠️ 堆叠失败，返回第一张图像")
                    return images[0]
            except:
                pass

            return None

    def _format_story_structure(self, scenes):
        """格式化故事结构输出"""
        try:
            formatted = "📚 连环画故事结构\n\n"
            for i, scene in enumerate(scenes):
                formatted += f"场景 {i+1}: {scene.get('title', '未命名')}\n"
                formatted += f"描述: {scene.get('description', '无描述')}\n"
                if scene.get('dialogue'):
                    formatted += f"对话: {scene['dialogue']}\n"
                if scene.get('narration'):
                    formatted += f"旁白: {scene['narration']}\n"
                formatted += "\n"
            
            return formatted

        except Exception as e:
            _log_error(f"故事结构格式化失败: {str(e)}")
            return "格式化失败"


# 分页浏览节点：从图像批次中按页选择一张，用于连环画翻页
class ComicPageSelectorNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "page_index": ("INT", {"default": 1, "min": 1, "max": 9999, "step": 1}),
                "loop": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("page_image", "page_info")
    FUNCTION = "select_page"
    CATEGORY = "Ken-Chen/Doubao"

    def select_page(self, images, page_index=1, loop=True):
        try:
            import torch
            if images is None or not isinstance(images, torch.Tensor) or images.ndim != 4:
                return (None, "无效的图像批次")
            total = int(images.shape[0])
            if total == 0:
                return (None, "空的图像批次")
            # 将1-based页码转换为索引
            idx = page_index - 1
            if loop:
                idx = idx % total
            else:
                idx = max(0, min(idx, total - 1))
            # 强制成连续内存，避免上游某些操作导致的视图切片问题
            selected = images[idx:idx+1, ...].contiguous()
            info = f"第 {idx + 1}/{total} 页"
            _log_info(f"📖 分页浏览: {info}")
            return (selected, info)
        except Exception as e:
            _log_error(f"分页选择失败: {str(e)}")
            return (None, f"错误: {str(e)}")


# 生成可交互HTML浏览文件的节点
class ComicHTMLViewerNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "story_structure": ("STRING", {"multiline": True, "default": ""}),
                "title": ("STRING", {"default": "我的连环画"}),
            },
            "optional": {
                "output_filename": ("STRING", {"default": "comic_story.html"}),
                "transition_effect": (["page-turn", "fade", "slide", "flip", "none"], {"default": "page-turn"}),
                "transition_duration": ("FLOAT", {"default": 1.5, "min": 0.1, "max": 3.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("viewer_path", "summary")
    FUNCTION = "create_viewer"
    CATEGORY = "Ken-Chen/Doubao"

    def _tensor_batch_to_base64_list(self, images, quality=85, max_size=None):
        """
        将图像张量转换为base64列表（优化版：支持压缩和缩放）

        Args:
            images: 图像张量
            quality: JPEG质量 (1-100)，默认85
            max_size: 最大尺寸（宽或高），None表示不缩放

        Returns:
            base64编码的图片列表
        """
        try:
            import torch
            import numpy as np
            from PIL import Image
            import io, base64
            if images is None or not isinstance(images, torch.Tensor) or images.ndim != 4:
                return []
            result = []
            b, h, w, c = images.shape
            data = images.clamp(0.0, 1.0).mul(255.0).byte().cpu().numpy()

            _log_info(f"🖼️ 开始编码 {b} 张图片（质量={quality}, 最大尺寸={max_size}）")

            for i in range(b):
                arr = data[i]
                img = Image.fromarray(arr, mode="RGB")

                # 🚀 优化1：缩放图片以减小文件大小
                if max_size is not None:
                    original_size = img.size
                    if img.width > max_size or img.height > max_size:
                        if img.width > img.height:
                            new_width = max_size
                            new_height = int(img.height * (max_size / img.width))
                        else:
                            new_height = max_size
                            new_width = int(img.width * (max_size / img.height))
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                        _log_info(f"  图片 {i+1}: 缩放 {original_size} -> {img.size}")

                # 🚀 优化2：使用JPEG格式压缩（比PNG小很多）
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(buf.getvalue()).decode("utf-8")
                result.append(f"data:image/jpeg;base64,{encoded}")

                # 显示文件大小
                size_kb = len(encoded) / 1024
                _log_info(f"  图片 {i+1}: {size_kb:.1f} KB")

            total_size_mb = sum(len(s) for s in result) / 1024 / 1024
            _log_info(f"✅ 图片编码完成，总大小: {total_size_mb:.2f} MB")

            return result
        except Exception as e:
            _log_error(f"图像编码失败: {str(e)}")
            return []

    def _parse_scenes_from_structure(self, story_structure):
        try:
            import json
            import re

            # 调试信息
            _log_info(f"🔍 开始解析故事结构，类型: {type(story_structure)}")

            if not story_structure:
                _log_warning("⚠️ 故事结构为空")
                return []

            if isinstance(story_structure, dict):
                data = story_structure
                _log_info("✅ 故事结构已经是字典格式")
            else:
                # 打印前100个字符用于调试
                preview = str(story_structure)[:100] if story_structure else "空"
                _log_info(f"🔍 故事结构字符串预览: {preview}")

                # 尝试提取JSON部分（去除markdown代码块）
                story_str = str(story_structure).strip()

                # 检查是否是格式化文本（以"📚 连环画故事结构"开头）
                if story_str.startswith("📚 连环画故事结构") or "场景 1:" in story_str or "场景 2:" in story_str:
                    _log_warning("⚠️ 检测到格式化文本而不是JSON")
                    _log_warning("💡 提示：请连接 DoubaoComicBookNode 的第2个输出(story_text)而不是第3个输出(story_structure)")
                    _log_info("🔄 尝试从格式化文本中提取场景信息...")
                    return self._parse_formatted_text(story_str)

                # 移除markdown代码块标记
                if story_str.startswith("```"):
                    # 找到第一个换行后的内容
                    lines = story_str.split('\n')
                    if len(lines) > 1:
                        # 移除第一行的```json或```
                        story_str = '\n'.join(lines[1:])
                        # 移除最后的```
                        if story_str.endswith("```"):
                            story_str = story_str[:-3].strip()

                # 尝试提取JSON对象
                json_match = re.search(r'\{.*\}', story_str, re.DOTALL)
                if json_match:
                    story_str = json_match.group()
                    _log_info("✅ 成功提取JSON对象")

                try:
                    data = json.loads(story_str)
                    _log_info("✅ JSON解析成功")
                except json.JSONDecodeError as je:
                    _log_warning(f"⚠️ JSON解析失败: {je}")
                    _log_info(f"🔍 错误位置: 第{je.lineno}行, 第{je.colno}列")
                    _log_info(f"🔍 错误附近内容: {story_str[max(0, je.pos-50):min(len(story_str), je.pos+50)]}")
                    _log_info("🔧 尝试修复JSON格式...")

                    # 尝试修复常见的JSON错误
                    fixed_str = story_str

                    # 1. 移除控制字符和非法字符
                    fixed_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', fixed_str)

                    # 2. 修复未转义的引号（在JSON值中）
                    # 先找到所有的键值对，然后修复值中的引号
                    def fix_quotes_in_value(match):
                        key = match.group(1)
                        value = match.group(2)
                        # 转义值中的引号（但不转义已经转义的）
                        value = re.sub(r'(?<!\\)"', r'\\"', value)
                        return f'"{key}": "{value}"'

                    # 匹配 "key": "value" 格式，value中可能有未转义的引号
                    fixed_str = re.sub(r'"([^"]+)":\s*"([^"]*(?:[^"\\]|\\.)*)(?=")', fix_quotes_in_value, fixed_str)

                    # 3. 移除最后一个对象/数组的多余逗号
                    fixed_str = re.sub(r',(\s*[}\]])', r'\1', fixed_str)

                    # 4. 修复未闭合的字符串
                    lines = fixed_str.split('\n')
                    fixed_lines = []
                    in_string = False
                    for line in lines:
                        stripped = line.strip()
                        if not stripped or stripped.startswith('//'):
                            continue

                        # 计算引号数量（忽略转义的引号）
                        quote_count = len(re.findall(r'(?<!\\)"', line))

                        # 如果引号数量是奇数，说明有未闭合的引号
                        if quote_count % 2 == 1:
                            # 检查是否是键值对的开始
                            if ':' in line and not line.rstrip().endswith('"'):
                                line = line.rstrip() + '"'

                        fixed_lines.append(line)
                    fixed_str = '\n'.join(fixed_lines)

                    # 5. 检查并补全未闭合的数组和对象
                    open_braces = fixed_str.count('{')
                    close_braces = fixed_str.count('}')
                    open_brackets = fixed_str.count('[')
                    close_brackets = fixed_str.count(']')

                    # 补全缺失的闭合括号
                    if open_brackets > close_brackets:
                        _log_info(f"🔧 补全 {open_brackets - close_brackets} 个数组闭合括号")
                        fixed_str += '\n' + '    ]' * (open_brackets - close_brackets)

                    if open_braces > close_braces:
                        _log_info(f"🔧 补全 {open_braces - close_braces} 个对象闭合括号")
                        fixed_str += '\n' + '}' * (open_braces - close_braces)

                    # 6. 尝试再次解析
                    try:
                        data = json.loads(fixed_str)
                        _log_info("✅ JSON修复成功")
                    except json.JSONDecodeError as je2:
                        _log_error(f"❌ JSON修复失败: {je2}")

                        # 7. 尝试使用更激进的修复策略
                        _log_info("🔧 尝试激进修复策略...")
                        try:
                            # 使用正则表达式提取场景数组
                            scenes_match = re.search(r'"scenes"\s*:\s*\[(.*)\]', fixed_str, re.DOTALL)
                            if scenes_match:
                                scenes_str = scenes_match.group(1)
                                # 分割场景对象
                                scene_objects = re.findall(r'\{[^{}]*\}', scenes_str)

                                scenes = []
                                for scene_obj in scene_objects:
                                    try:
                                        scene = json.loads(scene_obj)
                                        scenes.append(scene)
                                    except:
                                        # 尝试手动解析
                                        scene = {}
                                        for field in ['title', 'description', 'dialogue', 'narration']:
                                            field_match = re.search(f'"{field}"\\s*:\\s*"([^"]*)"', scene_obj)
                                            if field_match:
                                                scene[field] = field_match.group(1)
                                        if scene:
                                            scenes.append(scene)

                                if scenes:
                                    data = {"scenes": scenes}
                                    _log_info(f"✅ 激进修复成功，提取到 {len(scenes)} 个场景")
                                else:
                                    raise ValueError("无法提取场景")
                            else:
                                raise ValueError("未找到scenes数组")

                        except Exception as je3:
                            _log_error(f"❌ 激进修复也失败: {je3}")
                            _log_error(f"🔍 原始内容前500字符: {story_str[:500]}")
                            _log_error(f"🔍 原始内容后500字符: {story_str[-500:]}")
                            _log_warning("🔄 尝试按行解析故事结构")
                            return self._parse_formatted_text(story_structure)

            scenes = data.get("scenes", [])
            _log_info(f"✅ 解析出 {len(scenes)} 个场景")

            parsed = []
            for i, s in enumerate(scenes, 1):
                # 组合所有可用的文本内容
                text_parts = []

                # 获取描述（总是需要，因为这是图像生成的提示词）
                description = s.get("description", "").strip()

                # 添加旁白（过滤占位符）
                narration = s.get("narration", "").strip()
                # 过滤掉占位符文本（如"旁白描述 1"、"旁白内容"等）
                is_narration_placeholder = re.match(r'^旁白(描述|内容|文字)?\s*\d*$', narration) if narration else True

                # 添加对话（过滤占位符）
                dialogue = s.get("dialogue", "").strip()
                # 过滤掉占位符文本（如"角色对话 1"、"对话内容"等）
                is_dialogue_placeholder = re.match(r'^(角色)?对话(内容)?\s*\d*$', dialogue) if dialogue else True

                # 检查描述是否是占位符
                is_description_placeholder = False
                if description:
                    if re.match(r'^(场景)?描述\s*\d*$', description) or \
                       description.startswith("故事的第") or \
                       description.startswith("场景的"):
                        is_description_placeholder = True

                # 组合文本：优先使用旁白和对话，如果都是占位符则使用描述
                if narration and not is_narration_placeholder:
                    text_parts.append(f"旁白：{narration}")

                if dialogue and not is_dialogue_placeholder:
                    text_parts.append(f"对话：{dialogue}")

                # 如果没有有效的旁白和对话，使用描述
                if not text_parts and description and not is_description_placeholder:
                    text_parts.append(description)

                # 如果所有内容都是占位符或为空，至少显示描述（即使是占位符）
                if not text_parts:
                    if description:
                        text_parts.append(description)
                    else:
                        text_parts.append(f"场景 {i}")

                # 组合文本
                combined_text = "\n\n".join(text_parts)

                parsed.append({
                    "title": s.get("title", f"场景 {i}"),
                    "text": combined_text
                })

                _log_info(f"  场景 {i}: {s.get('title', '')} - 文本长度: {len(combined_text)}")

            return parsed
        except Exception as e:
            _log_error(f"场景解析失败: {str(e)}")
            import traceback
            _log_error(f"详细错误: {traceback.format_exc()}")
            return []

    def _parse_formatted_text(self, text):
        """从格式化文本中解析场景信息"""
        try:
            import re
            _log_info("🔄 开始解析格式化文本")
            lines = text.split('\n')
            scenes = []
            current_scene = None
            current_description = None  # 保存描述内容作为降级方案

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 匹配场景标题：场景 1: xxx 或 场景1: xxx（支持全角和半角冒号）
                scene_match = re.match(r'场景\s*(\d+)[：:]\s*(.+)', line)
                if scene_match:
                    # 保存上一个场景
                    if current_scene:
                        # 如果场景没有文本，使用描述作为降级
                        if not current_scene["text"] and current_description:
                            current_scene["text"] = current_description
                        scenes.append(current_scene)
                    # 开始新场景
                    current_scene = {
                        "title": scene_match.group(2).strip(),
                        "text": ""
                    }
                    current_description = None
                    continue

                # 收集场景内容
                if current_scene:
                    # 匹配标签行（描述:、对话:、旁白:，支持全角和半角冒号）
                    label_match = re.match(r'^(描述|对话|旁白)[：:]\s*(.+)', line)
                    if label_match:
                        label = label_match.group(1)
                        content = label_match.group(2).strip()

                        # 过滤占位符内容
                        is_placeholder = False
                        if label == "旁白" and re.match(r'^旁白(描述|内容|文字)?\s*\d*$', content):
                            is_placeholder = True
                        elif label == "对话" and re.match(r'^(角色)?对话(内容)?\s*\d*$', content):
                            is_placeholder = True
                        elif label == "描述":
                            # 保存描述内容（即使是占位符，也作为降级方案）
                            current_description = content
                            if re.match(r'^(场景)?描述\s*\d*$', content) or \
                               content.startswith("故事的第") or \
                               content.startswith("场景的"):
                                is_placeholder = True

                        if content and not is_placeholder:
                            if current_scene["text"]:
                                current_scene["text"] += f"\n\n{label}：{content}"
                            else:
                                current_scene["text"] = f"{label}：{content}"
                    else:
                        # 其他内容也添加进去（如果不是空行）
                        if line and not line.startswith("📚"):
                            if current_scene["text"]:
                                current_scene["text"] += "\n" + line
                            else:
                                current_scene["text"] = line

            # 保存最后一个场景
            if current_scene:
                # 如果场景没有文本，使用描述作为降级
                if not current_scene["text"] and current_description:
                    current_scene["text"] = current_description
                scenes.append(current_scene)

            _log_info(f"✅ 从格式化文本中解析出 {len(scenes)} 个场景")
            return scenes

        except Exception as e:
            _log_error(f"格式化文本解析失败: {str(e)}")
            import traceback
            _log_error(f"详细错误: {traceback.format_exc()}")
            return []

    def create_viewer(self, images, story_structure, title="我的连环画", output_filename="comic_story.html",
                     transition_effect="page-turn", transition_duration=1.5):
        try:
            import os, time
            # 🚀 优化：使用压缩和缩放来减小HTML文件大小
            # quality=85: JPEG质量（1-100），85是高质量和文件大小的平衡点
            # max_size=1920: 最大宽度或高度，对于网页显示已经足够
            _log_info("🖼️ 开始编码图片（使用压缩优化以减小文件大小）...")
            img_list = self._tensor_batch_to_base64_list(images, quality=85, max_size=1920)
            pages = self._parse_scenes_from_structure(story_structure)
            total = max(len(img_list), len(pages))
            # 对齐长度
            while len(img_list) < total and len(img_list) > 0:
                img_list.append(img_list[-1])
            while len(pages) < total and total > 0:
                pages.append({"title": f"第{len(pages)+1}页", "text": ""})

            html = self._build_html(title, img_list, pages, transition_effect, transition_duration)

            # 使用ComfyUI的output目录
            try:
                import folder_paths
                out_dir = folder_paths.get_output_directory()
                _log_info(f"📁 使用ComfyUI输出目录: {out_dir}")
            except ImportError:
                # 如果在ComfyUI环境外，尝试推断ComfyUI路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                comfyui_root = None

                # 向上查找ComfyUI根目录
                path_parts = current_dir.split(os.sep)
                for i in range(len(path_parts), 0, -1):
                    potential_root = os.sep.join(path_parts[:i])
                    if os.path.exists(os.path.join(potential_root, "main.py")) and \
                       os.path.exists(os.path.join(potential_root, "nodes.py")):
                        comfyui_root = potential_root
                        break

                if comfyui_root:
                    out_dir = os.path.join(comfyui_root, "output")
                    os.makedirs(out_dir, exist_ok=True)
                    _log_info(f"📁 推断ComfyUI输出目录: {out_dir}")
                else:
                    # 降级到web/exports目录
                    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "exports"))
                    _log_info(f"📁 使用web/exports目录: {out_dir}")

            os.makedirs(out_dir, exist_ok=True)
            # 加时间戳防止覆盖
            ts = int(time.time())
            if not output_filename.lower().endswith(".html"):
                output_filename += ".html"
            out_path = os.path.join(out_dir, f"{ts}_" + output_filename)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(html)
            info = f"✅ 已生成连环画HTML浏览文件: {out_path}\n页数: {total}\n特效: {transition_effect} ({transition_duration}s)"
            _log_info(info)
            return (out_path, info)
        except Exception as e:
            _log_error(f"创建HTML浏览文件失败: {str(e)}")
            return ("", f"错误: {str(e)}")

    def _build_html(self, title, img_list, pages, transition_effect="page-turn", transition_duration=1.5):
        # 打印调试信息
        _log_info(f"[DEBUG] _build_html 调用参数: transition_effect={transition_effect}, transition_duration={transition_duration}")

        # 尝试使用新的模板生成器
        try:
            import sys
            import importlib
            # 强制重新加载模块
            if 'custom_nodes.ComfyUI_doubao_seed.comic_html_template' in sys.modules:
                importlib.reload(sys.modules['custom_nodes.ComfyUI_doubao_seed.comic_html_template'])

            from .comic_html_template import build_comic_html
            _log_info(f"[DEBUG] 调用 build_comic_html，transition_effect={transition_effect}")
            html = build_comic_html(title, img_list, pages, transition_effect, transition_duration)
            _log_info(f"[DEBUG] build_comic_html 成功，HTML长度={len(html)}")
            return html
        except Exception as e:
            _log_error(f"使用新模板失败，降级到简单模板: {str(e)}")
            import traceback
            _log_error(traceback.format_exc())

        # 降级到简单模板
        import json
        total = len(img_list)
        img_list_json = json.dumps(img_list)
        pages_json = json.dumps(pages)
        # 简易样式与翻页逻辑，尽量接近官方“左图右文、上下页”体验
        return f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
<title>{title}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Noto Sans', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
.container {{ max-width: 1300px; margin: 0 auto; background: #fff; box-shadow: 0 10px 40px rgba(0,0,0,0.2); border-radius: 16px; padding: 36px; }}
.header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 14px; border-bottom: 2px solid #f0f0f0; }}
.page {{ display: grid; grid-template-columns: 1.5fr 1fr; gap: 28px; align-items: start; min-height: 550px; }}
.img-wrap {{ border-radius: 12px; overflow: hidden; box-shadow: 0 6px 24px rgba(0,0,0,0.12); }}
.img-wrap img {{ width: 100%; height: auto; display: block; }}
.text-wrap {{ background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%); border-radius: 12px; padding: 28px; min-height: 450px; box-shadow: 0 4px 16px rgba(0,0,0,0.08); line-height: 2.1; font-size: 16px; color: #333; overflow-y: auto; max-height: 650px; }}
.toolbar {{ display: flex; gap: 12px; align-items: center; }}
.btn {{ border: none; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 10px; padding: 10px 20px; cursor: pointer; font-size: 16px; font-weight: 500; transition: all 0.3s ease; box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3); }}
.btn:hover {{ transform: translateY(-2px); box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5); }}
.counter {{ color: #666; font-size: 16px; font-weight: 500; min-width: 60px; text-align: center; }}
@media (max-width: 768px) {{ .page {{ grid-template-columns: 1fr; gap: 20px; }} .container {{ padding: 20px; }} }}
</style>
</head>
<body>
  <div class=\"container\">
    <div class=\"header\">
      <div>📖 {title}</div>
      <div class=\"toolbar\">
        <button class=\"btn\" onclick=\"prev()\">◀</button>
        <span class=\"counter\" id=\"counter\">1/{total}</span>
        <button class=\"btn\" onclick=\"next()\">▶</button>
      </div>
    </div>
    <div class=\"page\">
      <div class=\"img-wrap\"><img id=\"img\" src=\"{img_list[0] if total>0 else ''}\" /></div>
      <div class=\"text-wrap\"><div id=\"text\">{pages[0]['text'] if total>0 else ''}</div></div>
    </div>
  </div>
<script>
const IMGS = {img_list_json};
const PAGES = {pages_json};
let i = 0;
function render() {{
  if (IMGS.length === 0) return;
  document.getElementById('img').src = IMGS[i];
  document.getElementById('text').innerText = (PAGES[i] && (PAGES[i].text||'')) || '';
  document.getElementById('counter').innerText = (i+1) + '/' + IMGS.length;
}}
function prev() {{ i = (i - 1 + IMGS.length) % IMGS.length; render(); }}
function next() {{ i = (i + 1) % IMGS.length; render(); }}
document.addEventListener('keydown', (e) => {{ if (e.key==='ArrowLeft') prev(); if (e.key==='ArrowRight') next(); }});
</script>
</body>
</html>"""


# 批量导出节点：将图像批次导出为图片序列，并可选合成为PDF
class ComicBatchExporterNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                "story_structure": ("STRING", {"multiline": True, "default": ""}),
                "title": ("STRING", {"default": "我的连环画"}),
                "output_subdir": ("STRING", {"default": "comic_export"}),
                "filename_prefix": ("STRING", {"default": "page_"}),
                "image_format": (["png", "jpg"], {"default": "png"}),
                "jpg_quality": ("INT", {"default": 92, "min": 10, "max": 100, "step": 1}),
                "export_pdf": ("BOOLEAN", {"default": True}),
                "pdf_with_text": ("BOOLEAN", {"default": True}),
                "pdf_filename": ("STRING", {"default": "comic_story.pdf"}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("export_dir", "summary")
    FUNCTION = "export"
    CATEGORY = "Ken-Chen/Doubao"

    def _tensor_batch_to_pil_list(self, images):
        try:
            import torch
            from PIL import Image
            if images is None or not isinstance(images, torch.Tensor) or images.ndim != 4:
                return []
            data = images.clamp(0.0, 1.0).mul(255.0).byte().cpu().numpy()
            pil_list = []
            for i in range(data.shape[0]):
                pil_list.append(Image.fromarray(data[i], mode="RGB"))
            return pil_list
        except Exception as e:
            _log_error(f"图像转换失败: {str(e)}")
            return []

    def _parse_pages(self, story_structure):
        try:
            import json
            import re

            if not story_structure:
                _log_warning("⚠️ 故事结构为空，跳过文本导出")
                return []

            if isinstance(story_structure, dict):
                data = story_structure
            else:
                # 尝试提取JSON部分（去除markdown代码块）
                story_str = str(story_structure).strip()

                # 检查是否是格式化文本
                if story_str.startswith("📚 连环画故事结构") or "场景 1:" in story_str or "场景 2:" in story_str:
                    _log_info("🔄 检测到格式化文本，尝试解析...")
                    return self._parse_formatted_text_for_export(story_str)

                # 移除markdown代码块标记
                if story_str.startswith("```"):
                    lines = story_str.split('\n')
                    if len(lines) > 1:
                        story_str = '\n'.join(lines[1:])
                        if story_str.endswith("```"):
                            story_str = story_str[:-3].strip()

                # 尝试提取JSON对象
                json_match = re.search(r'\{.*\}', story_str, re.DOTALL)
                if json_match:
                    story_str = json_match.group()

                try:
                    data = json.loads(story_str)
                except json.JSONDecodeError as je:
                    _log_warning(f"JSON解析失败，尝试格式化文本解析: {je}")
                    return self._parse_formatted_text_for_export(story_structure)

            scenes = data.get("scenes", [])
            parsed = []
            for i, s in enumerate(scenes, 1):
                # 组合所有可用的文本内容
                text_parts = []

                # 获取描述（总是需要，因为这是图像生成的提示词）
                description = s.get("description", "").strip()

                # 添加旁白（过滤占位符）
                narration = s.get("narration", "").strip()
                # 过滤掉占位符文本（如"旁白描述 1"、"旁白内容"等）
                is_narration_placeholder = re.match(r'^旁白(描述|内容|文字)?\s*\d*$', narration) if narration else True

                # 添加对话（过滤占位符）
                dialogue = s.get("dialogue", "").strip()
                # 过滤掉占位符文本（如"角色对话 1"、"对话内容"等）
                is_dialogue_placeholder = re.match(r'^(角色)?对话(内容)?\s*\d*$', dialogue) if dialogue else True

                # 检查描述是否是占位符
                is_description_placeholder = False
                if description:
                    if re.match(r'^(场景)?描述\s*\d*$', description) or \
                       description.startswith("故事的第") or \
                       description.startswith("场景的"):
                        is_description_placeholder = True

                # 组合文本：优先使用旁白和对话，如果都是占位符则使用描述
                if narration and not is_narration_placeholder:
                    text_parts.append(f"旁白：{narration}")

                if dialogue and not is_dialogue_placeholder:
                    text_parts.append(f"对话：{dialogue}")

                # 如果没有有效的旁白和对话，使用描述
                if not text_parts and description and not is_description_placeholder:
                    text_parts.append(description)

                # 如果所有内容都是占位符或为空，至少显示描述（即使是占位符）
                if not text_parts:
                    if description:
                        text_parts.append(description)
                    else:
                        text_parts.append(f"场景 {i}")

                # 组合文本
                combined_text = "\n\n".join(text_parts)

                parsed.append({
                    "title": s.get("title", f"场景 {i}"),
                    "text": combined_text
                })

            return parsed
        except Exception as e:
            _log_warning(f"解析故事结构失败，跳过文本导出: {str(e)}")
            return []

    def _parse_formatted_text_for_export(self, text):
        """从格式化文本中解析场景信息（用于导出）"""
        try:
            import re
            lines = text.split('\n')
            scenes = []
            current_scene = None
            current_description = None  # 保存描述内容作为降级方案

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # 匹配场景标题（支持全角和半角冒号）
                scene_match = re.match(r'场景\s*(\d+)[：:]\s*(.+)', line)
                if scene_match:
                    if current_scene:
                        # 如果场景没有文本，使用描述作为降级
                        if not current_scene["text"] and current_description:
                            current_scene["text"] = current_description
                        scenes.append(current_scene)
                    current_scene = {
                        "title": scene_match.group(2).strip(),
                        "text": ""
                    }
                    current_description = None
                    continue

                # 收集场景内容
                if current_scene:
                    # 匹配标签行（支持全角和半角冒号）
                    label_match = re.match(r'^(描述|对话|旁白)[：:]\s*(.+)', line)
                    if label_match:
                        label = label_match.group(1)
                        content = label_match.group(2).strip()

                        # 过滤占位符内容
                        is_placeholder = False
                        if label == "旁白" and re.match(r'^旁白(描述|内容|文字)?\s*\d*$', content):
                            is_placeholder = True
                        elif label == "对话" and re.match(r'^(角色)?对话(内容)?\s*\d*$', content):
                            is_placeholder = True
                        elif label == "描述":
                            # 保存描述内容（即使是占位符，也作为降级方案）
                            current_description = content
                            if re.match(r'^(场景)?描述\s*\d*$', content) or \
                               content.startswith("故事的第") or \
                               content.startswith("场景的"):
                                is_placeholder = True

                        if content and not is_placeholder:
                            if current_scene["text"]:
                                current_scene["text"] += f"\n\n{label}：{content}"
                            else:
                                current_scene["text"] = f"{label}：{content}"
                    else:
                        # 其他内容也添加进去（如果不是空行）
                        if line and not line.startswith("📚"):
                            if current_scene["text"]:
                                current_scene["text"] += "\n" + line
                            else:
                                current_scene["text"] = line

            if current_scene:
                # 如果场景没有文本，使用描述作为降级
                if not current_scene["text"] and current_description:
                    current_scene["text"] = current_description
                scenes.append(current_scene)

            return scenes

        except Exception as e:
            _log_error(f"格式化文本解析失败: {str(e)}")
            import traceback
            _log_error(f"详细错误: {traceback.format_exc()}")
            return []

    def _create_pdf_with_text(self, pil_list, pages, title, pdf_path):
        """创建带文字的PDF（上图下文排版）"""
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            import os

            # 注册中文字体
            try:
                # 尝试使用系统字体
                font_paths = [
                    "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                    "C:/Windows/Fonts/simhei.ttf",  # 黑体
                    "C:/Windows/Fonts/simsun.ttc",  # 宋体
                    "/System/Library/Fonts/PingFang.ttc",  # macOS
                    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Linux
                ]

                font_registered = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        try:
                            pdfmetrics.registerFont(TTFont('Chinese', font_path))
                            font_registered = True
                            _log_info(f"✅ 使用字体: {font_path}")
                            break
                        except:
                            continue

                if not font_registered:
                    _log_warning("⚠️ 未找到中文字体，使用默认字体")
                    font_name = "Helvetica"
                else:
                    font_name = "Chinese"
            except Exception as e:
                _log_warning(f"⚠️ 字体注册失败: {e}，使用默认字体")
                font_name = "Helvetica"

            # 创建PDF
            c = canvas.Canvas(pdf_path, pagesize=A4)
            page_width, page_height = A4

            # 边距
            margin = 40
            content_width = page_width - 2 * margin

            for i, img in enumerate(pil_list):
                # 获取对应的文本
                page_data = pages[i] if i < len(pages) else {"title": f"场景 {i+1}", "text": ""}
                page_title = page_data.get("title", f"场景 {i+1}")
                page_text = page_data.get("text", "")

                # 绘制页面标题和页码
                c.setFont(font_name, 18)
                c.drawString(margin, page_height - margin, title)

                c.setFont(font_name, 12)
                c.drawString(page_width - margin - 60, page_height - margin, f"第 {i+1} 页")

                # 当前Y位置
                current_y = page_height - margin - 40

                # ========== 上半部分：图片 ==========
                # 计算图片尺寸（保持宽高比，占用页面上半部分）
                img_aspect = img.width / img.height

                # 图片宽度为内容区域的90%
                img_width = content_width * 0.9
                img_height = img_width / img_aspect

                # 图片最大高度为页面的60%
                max_img_height = (page_height - 2 * margin - 80) * 0.6
                if img_height > max_img_height:
                    img_height = max_img_height
                    img_width = img_height * img_aspect

                # 图片居中显示
                img_x = margin + (content_width - img_width) / 2
                img_y = current_y - img_height

                c.drawImage(ImageReader(img), img_x, img_y, width=img_width, height=img_height)

                # 更新Y位置（图片下方留一些间距）
                current_y = img_y - 30

                # ========== 下半部分：文本 ==========
                # 绘制场景标题
                c.setFont(font_name, 14)
                c.drawString(margin, current_y, page_title)
                current_y -= 25

                # 绘制分隔线
                c.setStrokeColorRGB(0.7, 0.7, 0.7)
                c.setLineWidth(0.5)
                c.line(margin, current_y, page_width - margin, current_y)
                current_y -= 15

                # 绘制文本内容
                c.setFont(font_name, 11)
                c.setFillColorRGB(0.2, 0.2, 0.2)

                # 分行显示文本
                lines = page_text.split('\n')
                line_height = 18
                max_chars_per_line = 50  # 每行最大字符数

                for line in lines:
                    if not line.strip():
                        current_y -= line_height / 2
                        continue

                    # 文本自动换行处理
                    while len(line) > max_chars_per_line:
                        c.drawString(margin, current_y, line[:max_chars_per_line])
                        line = line[max_chars_per_line:]
                        current_y -= line_height

                        # 检查是否超出页面底部
                        if current_y < margin + 30:
                            break

                    if current_y >= margin + 30:
                        c.drawString(margin, current_y, line)
                        current_y -= line_height

                    # 检查是否超出页面底部
                    if current_y < margin + 30:
                        break

                # 绘制页面底部分隔线
                c.setStrokeColorRGB(0.8, 0.8, 0.8)
                c.setLineWidth(0.5)
                c.line(margin, margin + 15, page_width - margin, margin + 15)

                # 下一页
                c.showPage()

            c.save()
            _log_info(f"✅ 已生成带文字的PDF: {pdf_path}")
            return True

        except ImportError:
            _log_error("❌ 需要安装 reportlab 库才能生成带文字的PDF")
            _log_error("   请运行: pip install reportlab")
            return False
        except Exception as e:
            _log_error(f"❌ 生成带文字PDF失败: {str(e)}")
            import traceback
            _log_error(traceback.format_exc())
            return False

    def export(self, images, story_structure="", title="我的连环画", output_subdir="comic_export",
               filename_prefix="page_", image_format="png", jpg_quality=92,
               export_pdf=True, pdf_with_text=True, pdf_filename="comic_story.pdf"):
        try:
            import os, time
            from PIL import Image
            pil_list = self._tensor_batch_to_pil_list(images)
            if not pil_list:
                return ("", "没有可导出的图像")

            # 使用ComfyUI的output目录
            try:
                import folder_paths
                base_dir = folder_paths.get_output_directory()
                _log_info(f"📁 使用ComfyUI输出目录: {base_dir}")
            except ImportError:
                # 如果在ComfyUI环境外，尝试推断ComfyUI路径
                current_dir = os.path.dirname(os.path.abspath(__file__))
                comfyui_root = None

                # 向上查找ComfyUI根目录
                path_parts = current_dir.split(os.sep)
                for i in range(len(path_parts), 0, -1):
                    potential_root = os.sep.join(path_parts[:i])
                    if os.path.exists(os.path.join(potential_root, "main.py")) and \
                       os.path.exists(os.path.join(potential_root, "nodes.py")):
                        comfyui_root = potential_root
                        break

                if comfyui_root:
                    base_dir = os.path.join(comfyui_root, "output")
                    os.makedirs(base_dir, exist_ok=True)
                    _log_info(f"📁 推断ComfyUI输出目录: {base_dir}")
                else:
                    # 降级到web/exports目录
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "exports"))
                    _log_info(f"📁 使用web/exports目录: {base_dir}")

            # 目录: output/<timestamp_title>/<output_subdir>
            ts_dir = f"{int(time.time())}_{title}"
            export_dir = os.path.join(base_dir, ts_dir, output_subdir)
            os.makedirs(export_dir, exist_ok=True)

            # 保存图片序列
            count = 0
            for i, img in enumerate(pil_list, start=1):
                if image_format == "jpg":
                    fp = os.path.join(export_dir, f"{filename_prefix}{i:02d}.jpg")
                    img.convert("RGB").save(fp, quality=int(jpg_quality))
                else:
                    fp = os.path.join(export_dir, f"{filename_prefix}{i:02d}.png")
                    img.save(fp)
                count += 1

            # 保存文本（如有）
            pages = self._parse_pages(story_structure)
            if pages:
                txt_path = os.path.join(export_dir, "story_texts.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    for i, p in enumerate(pages, start=1):
                        f.write(f"第{i}页\n{p.get('title','')}\n{p.get('text','')}\n\n")

            # 合成PDF（可选）
            pdf_path = ""
            pdf_status = "未生成"
            if export_pdf and len(pil_list) > 0:
                pdf_path = os.path.join(base_dir, ts_dir, pdf_filename if pdf_filename.lower().endswith('.pdf') else pdf_filename + '.pdf')
                os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

                # 根据 pdf_with_text 参数选择生成方式
                if pdf_with_text and pages:
                    # 生成带文字的PDF（左图右文排版）
                    _log_info("📄 生成带文字的PDF...")
                    success = self._create_pdf_with_text(pil_list, pages, title, pdf_path)
                    if success:
                        pdf_status = f"已生成带文字PDF: {pdf_path}"
                    else:
                        # 降级到纯图片PDF
                        _log_warning("⚠️ 降级到纯图片PDF")
                        first = pil_list[0].convert("RGB")
                        rest = [p.convert("RGB") for p in pil_list[1:]]
                        first.save(pdf_path, save_all=True, append_images=rest)
                        pdf_status = f"已生成纯图片PDF: {pdf_path}"
                else:
                    # 生成纯图片PDF
                    _log_info("📄 生成纯图片PDF...")
                    first = pil_list[0].convert("RGB")
                    rest = [p.convert("RGB") for p in pil_list[1:]]
                    first.save(pdf_path, save_all=True, append_images=rest)
                    pdf_status = f"已生成纯图片PDF: {pdf_path}"

            summary = f"✅ 导出完成\n目录: {export_dir}\n图片数: {count}\nPDF: {pdf_status}"
            _log_info(summary)
            return (export_dir, summary)
        except Exception as e:
            _log_error(f"导出失败: {str(e)}")
            return ("", f"错误: {str(e)}")


# 连环画浏览器节点：在浏览器中打开HTML文件
class ComicBrowserViewerNode:
    """连环画浏览器节点 - 在浏览器中打开HTML连环画文件"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "viewer_path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "auto_open": ("BOOLEAN", {"default": False}),  # 默认不自动打开，通过按钮控制
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("file_url", "status")
    FUNCTION = "open_in_browser"
    CATEGORY = "Ken-Chen/Doubao"
    OUTPUT_NODE = True  # 标记为输出节点，这样会在执行时显示结果

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 总是标记为已更改，确保每次都能执行
        return float("nan")

    def open_in_browser(self, viewer_path, auto_open=False):
        """
        在浏览器中打开HTML文件

        Args:
            viewer_path: HTML文件路径
            auto_open: 是否自动打开浏览器

        Returns:
            tuple: (文件URL, 状态信息)
        """
        try:
            import os
            import webbrowser
            from pathlib import Path

            # 检查文件是否存在
            if not viewer_path or not os.path.exists(viewer_path):
                error_msg = f"❌ HTML文件不存在: {viewer_path}"
                _log_error(error_msg)
                return ("", error_msg)

            # 转换为绝对路径
            abs_path = os.path.abspath(viewer_path)

            # 转换为file:// URL
            file_url = Path(abs_path).as_uri()

            # 如果启用自动打开，则在浏览器中打开
            if auto_open:
                try:
                    _log_info(f"🌐 正在浏览器中打开: {abs_path}")
                    webbrowser.open(file_url)
                    status = f"✅ 已在浏览器中打开连环画\n文件: {abs_path}\nURL: {file_url}"
                    _log_info(status)
                except Exception as e:
                    error_msg = f"⚠️ 自动打开浏览器失败: {str(e)}\n文件路径: {abs_path}\n请手动打开此文件"
                    _log_warning(error_msg)
                    status = error_msg
            else:
                status = f"📄 HTML文件已准备\n文件: {abs_path}\nURL: {file_url}\n提示: 启用 auto_open 可自动打开浏览器"
                _log_info(status)

            return (file_url, status)

        except Exception as e:
            error_msg = f"❌ 打开浏览器失败: {str(e)}"
            _log_error(error_msg)
            import traceback
            _log_error(traceback.format_exc())
            return ("", error_msg)


# 连环画HTML内嵌预览节点：在ComfyUI界面内直接预览连环画
class ComicHTMLPreviewNode:
    """连环画HTML内嵌预览节点 - 在ComfyUI界面内直接预览连环画HTML"""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "viewer_path": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "width": ("INT", {"default": 800, "min": 100, "max": 2000, "step": 10}),
                "height": ("INT", {"default": 600, "min": 100, "max": 2000, "step": 10}),
                "scale": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 2.0, "step": 0.1}),
            }
        }

    INPUT_IS_LIST = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("html_content",)
    FUNCTION = "preview_html"
    CATEGORY = "Ken-Chen/Doubao"
    OUTPUT_NODE = True
    OUTPUT_IS_LIST = (True,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # 总是标记为已更改，确保每次都能刷新预览
        return float("nan")

    def preview_html(self, viewer_path, width=None, height=None, scale=None):
        """
        在ComfyUI界面内预览HTML连环画

        Args:
            viewer_path: HTML文件路径（列表）
            width: 预览窗口宽度（列表）
            height: 预览窗口高度（列表）
            scale: 缩放比例（列表）

        Returns:
            包含UI信息和HTML内容的字典
        """
        try:
            import os

            # 处理列表输入，取第一个元素
            path = viewer_path[0] if isinstance(viewer_path, list) else viewer_path
            w = width[0] if width and isinstance(width, list) else (width or 800)
            h = height[0] if height and isinstance(height, list) else (height or 600)
            s = scale[0] if scale and isinstance(scale, list) else (scale or 1.0)

            _log_info(f"📺 准备预览连环画HTML: {path}")
            _log_info(f"   预览尺寸: {w}x{h}, 缩放: {s}")

            # 检查文件是否存在
            if not path or not os.path.exists(path):
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: #f5f5f5;
                        }}
                        .error {{
                            background: white;
                            padding: 30px;
                            border-radius: 10px;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                            text-align: center;
                        }}
                        .error h2 {{
                            color: #e74c3c;
                            margin-top: 0;
                        }}
                        .error p {{
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="error">
                        <h2>❌ 文件未找到</h2>
                        <p>HTML文件不存在或路径无效</p>
                        <p style="font-size: 12px; color: #999;">路径: {path}</p>
                    </div>
                </body>
                </html>
                """
                _log_error(f"❌ HTML文件不存在: {path}")
                return {
                    "ui": {
                        "html": [error_html],
                        "width": [w],
                        "height": [h],
                        "scale": [s],
                        "is_portrait": [False]
                    },
                    "result": ([error_html],)
                }

            # 读取HTML文件内容
            with open(path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            _log_info(f"✅ 成功读取HTML文件，大小: {len(html_content)} 字节")

            # 返回UI信息和HTML内容
            return {
                "ui": {
                    "html": [html_content],
                    "width": [w],
                    "height": [h],
                    "scale": [s],
                    "is_portrait": [False]  # 连环画通常是横向布局
                },
                "result": ([html_content],)
            }

        except Exception as e:
            _log_error(f"预览HTML失败: {str(e)}")
            import traceback
            _log_error(traceback.format_exc())

            error_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100vh;
                        margin: 0;
                        background: #f5f5f5;
                    }}
                    .error {{
                        background: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                        text-align: center;
                        max-width: 600px;
                    }}
                    .error h2 {{
                        color: #e74c3c;
                        margin-top: 0;
                    }}
                    .error p {{
                        color: #666;
                    }}
                    .error pre {{
                        background: #f8f8f8;
                        padding: 10px;
                        border-radius: 5px;
                        text-align: left;
                        overflow-x: auto;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <div class="error">
                    <h2>❌ 预览失败</h2>
                    <p>无法加载HTML内容</p>
                    <pre>{str(e)}</pre>
                </div>
            </body>
            </html>
            """

            return {
                "ui": {
                    "html": [error_html],
                    "width": [800],
                    "height": [600],
                    "scale": [1.0],
                    "is_portrait": [False]
                },
                "result": ([error_html],)
            }


# 节点映射
NODE_CLASS_MAPPINGS = {
    "SeedReam4APINode": SeedReam4APINode,
    "SeedReam4APISingleNode": SeedReam4APISingleNode,
    "DoubaoSeedanceVideoNode": DoubaoSeedanceVideoNode,
    "DoubaoSeedanceContinuousVideoNode": DoubaoSeedanceContinuousVideoNode,
    "DoubaoSeedanceMultiRefVideoNode": DoubaoSeedanceMultiRefVideoNode,
    "DoubaoSeed16Node": DoubaoSeed16Node,
    "DoubaoComicBookNode": DoubaoComicBookNode,
    "ComicPageSelectorNode": ComicPageSelectorNode,
    "ComicHTMLViewerNode": ComicHTMLViewerNode,
    "ComicBatchExporterNode": ComicBatchExporterNode,
    "ComicBrowserViewerNode": ComicBrowserViewerNode,
    "ComicHTMLPreviewNode": ComicHTMLPreviewNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SeedReam4APINode": "SeedReam4API (多图)",
    "SeedReam4APISingleNode": "SeedReam4API (单图)",
    "DoubaoSeedanceVideoNode": "Doubao-Seedance视频生成",
    "DoubaoSeedanceContinuousVideoNode": "Doubao-Seedance连续视频生成",
    "DoubaoSeedanceMultiRefVideoNode": "Doubao-Seedance多图参考视频生成",
    "DoubaoSeed16Node": "doubao-seed-1-6",
    "DoubaoComicBookNode": "豆包连环画创作",
    "ComicPageSelectorNode": "连环画分页浏览",
    "ComicHTMLViewerNode": "连环画HTML浏览导出",
    "ComicBatchExporterNode": "连环画批量导出(PNG/JPG/PDF)",
    "ComicBrowserViewerNode": "连环画浏览器预览",
    "ComicHTMLPreviewNode": "连环画HTML内嵌预览",
}


# Web API 路由
WEB_DIRECTORY = "./web"

# 注册 API 路由
try:
    from aiohttp import web
    import server

    @server.PromptServer.instance.routes.post("/doubao_seed/open_browser")
    async def open_browser_api(request):
        """API 端点：在浏览器中打开 HTML 文件"""
        try:
            import os
            import webbrowser
            from pathlib import Path

            # 获取请求数据
            data = await request.json()
            viewer_path = data.get("viewer_path", "")

            _log_info(f"🌐 收到打开浏览器请求: {viewer_path}")

            # 检查文件是否存在
            if not viewer_path or not os.path.exists(viewer_path):
                error_msg = f"HTML文件不存在: {viewer_path}"
                _log_error(f"❌ {error_msg}")
                return web.json_response({
                    "success": False,
                    "error": error_msg
                })

            # 转换为绝对路径
            abs_path = os.path.abspath(viewer_path)

            # 转换为 file:// URL
            file_url = Path(abs_path).as_uri()

            # 在浏览器中打开
            try:
                _log_info(f"🌐 正在浏览器中打开: {abs_path}")
                webbrowser.open(file_url)

                success_msg = "已在浏览器中打开连环画"
                _log_info(f"✅ {success_msg}")

                return web.json_response({
                    "success": True,
                    "message": success_msg,
                    "file_path": abs_path,
                    "file_url": file_url
                })

            except Exception as e:
                error_msg = f"打开浏览器失败: {str(e)}"
                _log_error(f"❌ {error_msg}")
                return web.json_response({
                    "success": False,
                    "error": error_msg,
                    "file_path": abs_path,
                    "file_url": file_url
                })

        except Exception as e:
            error_msg = f"API 请求处理失败: {str(e)}"
            _log_error(f"❌ {error_msg}")
            import traceback
            _log_error(traceback.format_exc())
            return web.json_response({
                "success": False,
                "error": error_msg
            })

    _log_info("✅ ComicBrowserViewer API 路由已注册")

except Exception as e:
    _log_warning(f"⚠️ 无法注册 API 路由: {str(e)}")
    _log_warning("浏览器预览功能可能无法通过按钮使用，但仍可通过 auto_open 参数使用")
