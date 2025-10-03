# ComfyUI Doubao-Seed - 专业的Doubao AI创作解决方案

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![ComfyUI](https://img.shields.io/badge/ComfyUI-Compatible-green.svg)](https://github.com/comfyanonymous/ComfyUI)
[![Doubao](https://img.shields.io/badge/Doubao-Seedream4-orange.svg)](https://www.volcengine.com/product/doubao)

一个专注于火山引擎豆包（Doubao）生态的ComfyUI自定义节点集合，提供**图像生成**、**视频生成**、**文本生成**和**连环画创作**等全方位AI内容创作功能。基于火山引擎豆包大模型，为用户提供高质量的AI内容创作体验。

---

## 📑 目录

- [核心特性](#-核心特性)
- [节点概览](#-节点概览)
- [连环画创作完整指南](#-连环画创作完整指南)
- [功能展示](#-功能展示)
- [安装指南](#-安装指南)
- [配置设置](#-配置设置)
- [快速开始](#-快速开始)
- [使用示例](#-使用示例)
- [性能优化](#-性能优化)
- [故障排除](#-故障排除)
- [更新日志](#-更新日志)
- [相关文档](#-相关文档)
- [许可证](#-许可证)
- [贡献](#-贡献)
- [支持](#-支持)

---

## 🌟 核心特性

- **🎨 专业图像生成**: 基于Doubao Seedream4的高质量图像生成，支持多图参考和单图模式
- **🎬 强大视频生成**: 支持基础视频生成、连续视频生成和多图参考视频生成
- **📝 智能文本生成**: 基于豆包大模型的高质量文本创作，支持多种模型选择
- **📚 连环画创作**: 一键生成完整连环画故事书，支持多种预览和导出方式
- **🚀 多镜像支持**: 支持官方API、T8和ComFly镜像站等多种服务端点
- **⚡ 高性能处理**: 优化的API调用和任务轮询机制
- **🎯 专业品质**: 统一的"Ken-Chen/Doubao"品牌，专注于Doubao生态
- **🛠️ 灵活配置**: 支持多种分辨率、质量设置和自定义参数

---

## ✨ 项目亮点

### 🎯 为什么选择 ComfyUI Doubao-Seed？

1. **📚 独家连环画创作系统**
   - 业界首个集成文本生成和图像生成的连环画创作解决方案
   - 一键生成完整故事书，包含文字和图像
   - 支持HTML内嵌预览、浏览器预览、PDF导出等多种方式
   - 智能参考图像循环使用，保持风格一致性

2. **🎨 强大的图像生成能力**
   - 支持1K/2K/4K多种分辨率
   - 一次生成1-15张图像
   - 支持最多10张参考图像（连环画模式）
   - 多种图像风格：卡通、写实、动漫、水彩等

3. **🎬 专业的视频生成功能**
   - 文本到视频生成
   - 连续场景视频生成
   - 多图参考视频生成
   - 智能任务轮询，自动处理长时间任务

4. **📝 灵活的文本生成**
   - 支持豆包大模型系列（doubao-seed-1-6）
   - 多种模型选择：标准版、快速版
   - 可调节温度、top_p等参数
   - 适合故事创作、文案生成等场景

5. **🔧 完善的工具链**
   - 12个专业节点，覆盖全流程
   - 统一的"Ken-Chen/Doubao"分类
   - 详尽的文档和示例
   - 活跃的社区支持

6. **⚡ 优秀的性能**
   - 优化的API调用机制
   - 智能缓存和批处理
   - 多镜像自动故障转移
   - 内存优化，支持大规模生成

---

## 🎯 节点概览

本项目提供 **12个专业节点**，全部归类在 **"Ken-Chen/Doubao"** 类别下：

### 📸 图像生成节点（2个）
- **SeedReam4API (多图)** - 支持最多5张参考图像的高质量图像生成
- **SeedReam4API (单图)** - 单张图像生成和编辑，适合快速创作

### 🎬 视频生成节点（3个）
- **Doubao-Seedance视频生成** - 基础的文本到视频生成
- **Doubao-Seedance连续视频生成** - 支持连续场景的视频生成
- **Doubao-Seedance多图参考视频生成** - 基于多张参考图的视频生成

### 📝 文本生成节点（1个）
- **doubao-seed-1-6** - 豆包大模型文本生成，支持3种模型选择

### 📚 连环画创作节点（6个）
- **豆包连环画创作** - 一键生成完整连环画故事书（文本+图像）
- **连环画分页浏览** - 分页预览连环画，支持翻页和循环
- **连环画HTML浏览导出** - 生成可交互的HTML连环画文件
- **连环画HTML内嵌预览** - 在ComfyUI界面内直接预览连环画
- **连环画浏览器预览** - 在系统浏览器中打开连环画
- **连环画批量导出(PNG/JPG/PDF)** - 批量导出图片和PDF文件

## 📚 连环画创作完整指南

### 🎨 连环画创作节点详解

#### 1. 豆包连环画创作（DoubaoComicBookNode）

**核心功能**：一键生成完整的连环画故事书，集成文本生成和图像生成

**主要参数**：

**故事设置**：
- `story_prompt` (STRING): 故事主题提示词
  - 示例：`"一个关于小兔子冒险的温馨故事"`
- `story_length` (选择): 故事长度
  - `short`: 3-5个场景
  - `medium`: 6-8个场景（推荐）
  - `long`: 9-12个场景
- `story_theme` (STRING): 故事主题（可选）
  - 示例：`"友谊、勇气、成长"`

**图像设置**：
- `image_style` (选择): 图像风格
  - `cartoon`: 卡通风格（推荐）
  - `realistic`: 写实风格
  - `anime`: 动漫风格
  - `watercolor`: 水彩风格
- `resolution` (选择): 图像分辨率
  - `1K`: 1024x1024（快速）
  - `2K`: 2048x2048（推荐）
  - `4K`: 4096x4096（高质量）
- `aspect_ratio` (选择): 宽高比
  - `4:3`: 适合连环画（推荐）
  - `16:9`: 宽屏
  - `1:1`: 正方形

**参考图像**（可选）：
- `reference_images`: 主参考图像
- `reference_image_2` 到 `reference_image_10`: 额外参考图像
- **智能循环使用**: 系统会自动循环使用所有参考图片，为不同场景提供不同的视觉参考
- **最多支持10张**: 可以同时使用最多10张参考图片来指导连环画创作

**角色和场景**（可选）：
- `character_description` (STRING): 角色描述
  - 示例：`"一只白色的小兔子，穿着蓝色背心"`
- `background_style` (STRING): 背景风格
  - 示例：`"梦幻森林，充满魔法元素"`

**API设置**：
- `mirror_site` (选择): 镜像站选择
  - `comfly`: ComFly镜像站（推荐）
  - `volcengine`: 火山引擎官方API
- `text_model` (选择): 文本生成模型
  - `doubao-seed-1-6-250615`: 标准版（推荐）
  - `doubao-seed-1-6-flash-250615`: 快速版
  - `doubao-seed-1-6-flash-250828`: 最新快速版
- `image_model` (选择): 图像生成模型
  - `doubao-seedream-4-0-250828`: 最新版（推荐）
- `watermark` (BOOLEAN): 是否添加水印（默认：True）

**输出内容**：
1. `comic_images` (IMAGE): 生成的连环画图像批次
2. `story_text` (STRING): 格式化的故事文本
3. `story_structure` (STRING): JSON格式的故事结构
4. `generation_info` (STRING): 生成信息统计

---

### 🔍 连环画预览和导出节点

#### 2. 连环画分页浏览（ComicPageSelectorNode）

**功能**：从图像批次中按页选择一张，用于连环画翻页预览

**参数**：
- `images` (IMAGE): 连环画图像批次
- `page_index` (INT): 页码（从1开始）
- `loop` (BOOLEAN): 是否循环（超出范围时回到第一页）

**使用方法**：
```
豆包连环画创作.comic_images → 连环画分页浏览.images
连环画分页浏览.page_image → Preview Image.images
```

**输出**：
- `page_image` (IMAGE): 当前页的图像
- `page_info` (STRING): 页码信息

---

#### 3. 连环画HTML浏览导出（ComicHTMLViewerNode）

**功能**：生成可交互的HTML连环画文件，支持翻页动画

**参数**：
- `images` (IMAGE): 连环画图像批次
- `story_structure` (STRING): 故事结构（推荐连接 `story_text` 输出）
- `title` (STRING): 连环画标题（默认："我的连环画"）
- `output_filename` (STRING): HTML文件名（默认："comic_story.html"）
- `transition_effect` (选择): 翻页特效
  - `page-turn`: 翻书效果（推荐）
  - `fade`: 淡入淡出
  - `slide`: 滑动
  - `flip`: 翻转
  - `none`: 无特效
- `transition_duration` (FLOAT): 特效持续时间（0.1-3.0秒，默认1.5秒）

**输出**：
- `viewer_path` (STRING): HTML文件路径
- `info` (STRING): 生成信息

**输出位置**：`web/exports/时间戳_comic_story.html`

**HTML特性**：
- ✅ 左右翻页按钮
- ✅ 页码显示（第X页/共Y页）
- ✅ 键盘导航（←/→ 键翻页）
- ✅ 图片和文字同步显示
- ✅ 响应式设计
- ✅ 所有资源内嵌（单文件分享）

---

#### 4. 连环画HTML内嵌预览（ComicHTMLPreviewNode）⭐ 推荐

**功能**：在ComfyUI界面内直接预览连环画，无需打开外部浏览器

**参数**：
- `viewer_path` (STRING): HTML文件路径（从 `ComicHTMLViewerNode` 输出）
- `width` (INT): 预览窗口宽度（100-2000，默认800）
- `height` (INT): 预览窗口高度（100-2000，默认600）
- `scale` (FLOAT): 缩放比例（0.1-2.0，默认1.0）

**使用方法**：
```
连环画HTML浏览导出.viewer_path → 连环画HTML内嵌预览.viewer_path
```

**特点**：
- ✅ 直接在 ComfyUI 界面内预览
- ✅ 无需打开外部浏览器
- ✅ 内置刷新按钮，可实时更新
- ✅ 可调整预览窗口尺寸
- ✅ 支持所有HTML交互功能

**适用场景**：快速预览、调试、小屏幕设备

---

#### 5. 连环画浏览器预览（ComicBrowserViewerNode）

**功能**：在系统默认浏览器中打开HTML连环画文件

**参数**：
- `viewer_path` (STRING): HTML文件路径
- `auto_open` (BOOLEAN): 是否自动打开（默认：False）

**使用方法**：
```
连环画HTML浏览导出.viewer_path → 连环画浏览器预览.viewer_path
```

**特点**：
- ✅ 在系统默认浏览器中打开
- ✅ 节点上有"🌐 打开浏览器"按钮
- ✅ 完整的浏览体验
- ✅ 支持打印、分享等功能
- ✅ 可选自动打开或手动点击按钮

**输出**：
- `file_url` (STRING): 文件URL（file://路径）
- `status` (STRING): 状态信息

**适用场景**：最终查看、分享、打印

---

#### 6. 连环画批量导出(PNG/JPG/PDF)（ComicBatchExporterNode）

**功能**：批量导出连环画为图片序列和PDF文件

**参数**：
- `images` (IMAGE): 连环画图像批次
- `story_structure` (STRING): 故事结构（可选，用于导出文字）
- `title` (STRING): 连环画标题（默认："我的连环画"）
- `output_subdir` (STRING): 输出子目录（默认："comic_export"）
- `filename_prefix` (STRING): 文件名前缀（默认："page_"）
- `image_format` (选择): 图像格式
  - `png`: PNG格式（无损）
  - `jpg`: JPG格式（较小）
- `jpg_quality` (INT): JPG质量（10-100，默认92）
- `export_pdf` (BOOLEAN): 是否导出PDF（默认：True）
- `pdf_with_text` (BOOLEAN): PDF是否包含文字（默认：True）
- `pdf_filename` (STRING): PDF文件名（默认："comic_story.pdf"）

**输出内容**：
- 图片序列：`page_01.png`、`page_02.png`...
- 文本文件：`story_texts.txt`（包含每页的文字）
- PDF文件：`comic_story.pdf`（可选）

**输出目录**：`web/exports/<时间戳_标题>/<output_subdir>/`

**输出**：
- `export_path` (STRING): 导出目录路径
- `info` (STRING): 导出信息统计

**适用场景**：
- 需要单独编辑图片
- 需要打印或印刷
- 需要分享PDF文件
- 需要备份原始图片

---

### 🎯 推荐工作流

#### 工作流 1：快速预览（推荐新手）

```
豆包连环画创作
    ↓ comic_images, story_text
连环画HTML浏览导出
    ↓ viewer_path
连环画HTML内嵌预览
    (在ComfyUI界面内直接查看)
```

#### 工作流 2：完整浏览体验

```
豆包连环画创作
    ↓ comic_images, story_text
连环画HTML浏览导出
    ↓ viewer_path
    ├─→ 连环画HTML内嵌预览（快速预览）
    └─→ 连环画浏览器预览（完整浏览）
```

#### 工作流 3：完整导出（推荐专业用户）

```
豆包连环画创作
    ↓ comic_images, story_text
    ├─→ 连环画HTML浏览导出 ─→ 连环画浏览器预览
    └─→ 连环画批量导出(PNG/JPG/PDF)
```

#### 工作流 4：分页预览

```
豆包连环画创作
    ↓ comic_images
连环画分页浏览
    ↓ page_image
Preview Image
    (调整 page_index 翻页)
```

---

### 💡 使用技巧

1. **故事文本连接**：
   - ✅ 推荐：`DoubaoComicBookNode.story_text` → `ComicHTMLViewerNode.story_structure`
   - ⚠️ 也支持：`DoubaoComicBookNode.story_structure` → `ComicHTMLViewerNode.story_structure`

2. **参考图像使用**：
   - 单张参考图：连接到 `reference_images`
   - 多张参考图：连接到 `reference_image_2` 到 `reference_image_10`
   - 系统会自动循环使用所有参考图片

3. **预览方式选择**：
   - 快速调试：使用 `连环画HTML内嵌预览`
   - 最终查看：使用 `连环画浏览器预览`
   - 分页查看：使用 `连环画分页浏览`

4. **导出格式选择**：
   - 需要编辑：导出PNG格式
   - 需要分享：导出PDF格式
   - 需要网页：使用HTML浏览导出

---

## 📸 功能展示

### 连环画创作示例
![连环画创作示例](https://via.placeholder.com/800x600/5B8FF9/FFFFFF?text=Comic+Book+Creation)

*一键生成完整的连环画故事书，包含文本和图像*

### Doubao-Seed图像生成
![Doubao-Seed图像生成示例](https://via.placeholder.com/800x600/61DDAA/FFFFFF?text=Image+Generation)

*高质量图像生成，支持多种风格和分辨率*

### Doubao-Seed视频生成
![Doubao-Seed视频生成示例](https://via.placeholder.com/800x600/F6BD16/FFFFFF?text=Video+Generation)

*文本到视频生成，支持多种分辨率和时长*

### HTML内嵌预览
![HTML内嵌预览](https://via.placeholder.com/800x600/7262FD/FFFFFF?text=HTML+Preview)

*在ComfyUI界面内直接预览连环画*

## 📦 安装指南

### 前置要求

- **ComfyUI**: 已安装并可正常运行
- **Python**: 3.8 或更高版本
- **操作系统**: Windows / Linux / macOS

### 方法一：Git克隆（推荐）

```bash
# 进入ComfyUI的custom_nodes目录
cd ComfyUI/custom_nodes

# 克隆项目
git clone https://github.com/Ken-Chen/ComfyUI_Doubao_Seed.git

# 进入项目目录
cd ComfyUI_Doubao_Seed

# 安装依赖
pip install -r requirements.txt

# 如果需要PDF导出功能（可选）
pip install -r requirements_face_restore.txt
# 或者运行批处理文件（Windows）
install_pdf_support.bat
```

### 方法二：ComfyUI Manager（最简单）

1. 在ComfyUI中打开 **Manager** 面板
2. 搜索 **"Doubao"** 或 **"ComfyUI_Doubao_Seed"**
3. 点击 **Install** 安装
4. 重启ComfyUI

### 方法三：手动下载

1. 下载项目压缩包：[GitHub Releases](https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/releases)
2. 解压到 `ComfyUI/custom_nodes/ComfyUI_Doubao_Seed`
3. 安装依赖：
```bash
cd ComfyUI/custom_nodes/ComfyUI_Doubao_Seed
pip install -r requirements.txt
```

### 依赖说明

**核心依赖**（必需）：
- `requests` - API调用
- `Pillow` - 图像处理
- `numpy` - 数值计算
- `torch` - PyTorch（ComfyUI已包含）

**可选依赖**（增强功能）：
- `reportlab` - PDF生成（连环画导出功能）
- `opencv-python` - 视频处理
- `imageio` - 图像序列处理

### 验证安装

1. 重启ComfyUI
2. 在节点列表中搜索 **"Ken-Chen/Doubao"**
3. 应该能看到12个节点：
   - SeedReam4API (多图)
   - SeedReam4API (单图)
   - Doubao-Seedance视频生成
   - Doubao-Seedance连续视频生成
   - Doubao-Seedance多图参考视频生成
   - doubao-seed-1-6
   - 豆包连环画创作
   - 连环画分页浏览
   - 连环画HTML浏览导出
   - 连环画HTML内嵌预览
   - 连环画浏览器预览
   - 连环画批量导出(PNG/JPG/PDF)

## 🔧 配置设置

### API密钥配置

在使用前，您需要配置相应的API密钥。项目支持多种服务端点。

#### 方法一：配置文件（推荐）

在项目根目录创建 `SeedReam4_config.json` 文件：

```json
{
  "doubao_api_key": "your_doubao_api_key",
  "doubao_endpoint": "https://ark.cn-beijing.volces.com/api/v3",
  "t8_api_key": "your_t8_api_key",
  "t8_endpoint": "https://api.t8.run/v1",
  "comfly_api_key": "your_comfly_api_key",
  "comfly_endpoint": "https://api.comfly.ai/v1"
}
```

**配置说明**：
- `doubao_api_key`: 火山引擎豆包API密钥
- `doubao_endpoint`: 火山引擎API端点
- `t8_api_key`: T8镜像站API密钥
- `t8_endpoint`: T8镜像站端点
- `comfly_api_key`: ComFly镜像站API密钥
- `comfly_endpoint`: ComFly镜像站端点

#### 方法二：环境变量

您可以通过环境变量设置API密钥：

**Windows (PowerShell)**:
```powershell
$env:DOUBAO_API_KEY="your_doubao_api_key"
$env:T8_API_KEY="your_t8_api_key"
$env:COMFLY_API_KEY="your_comfly_api_key"
```

**Linux / macOS**:
```bash
export DOUBAO_API_KEY="your_doubao_api_key"
export T8_API_KEY="your_t8_api_key"
export COMFLY_API_KEY="your_comfly_api_key"
```

#### 方法三：节点参数

在节点中直接输入API密钥（不推荐，安全性较低）

### 获取API密钥

#### 1. 火山引擎豆包API（官方）

1. 访问 [火山引擎控制台](https://console.volcengine.com/ark)
2. 注册并登录账号
3. 创建API密钥
4. 复制密钥到配置文件

**优点**：
- ✅ 官方服务，稳定可靠
- ✅ 完整功能支持
- ✅ 技术支持

**缺点**：
- ⚠️ 需要实名认证
- ⚠️ 可能需要付费

#### 2. T8镜像站

1. 访问 [T8镜像站](https://api.t8.run)
2. 注册账号
3. 获取API密钥

**优点**：
- ✅ 注册简单
- ✅ 价格优惠
- ✅ 支持多种模型

#### 3. ComFly镜像站（推荐）

1. 访问 ComFly官网
2. 注册账号
3. 获取API密钥

**优点**：
- ✅ 注册简单
- ✅ 稳定性好
- ✅ 响应速度快
- ✅ 支持连环画创作

### 代理设置

如果需要使用代理，可以在配置文件中添加：

```json
{
  "proxy": {
    "http": "http://proxy:port",
    "https": "https://proxy:port"
  }
}
```

或在节点参数中配置：
- HTTP代理：`http://proxy:port`
- SOCKS代理：`socks5://proxy:port`

### 高级配置

在 `SeedReam4_config.json` 中可以配置更多选项：

```json
{
  "doubao_api_key": "your_api_key",
  "doubao_endpoint": "https://ark.cn-beijing.volces.com/api/v3",

  "default_model": "doubao-seedream-4-0-250828",
  "timeout": 60,
  "max_retries": 3,
  "retry_delay": 2,

  "performance": {
    "max_concurrent_requests": 3,
    "request_timeout": 60,
    "max_image_size": "4K",
    "video_quality": "high"
  },

  "proxy": {
    "http": "http://proxy:port",
    "https": "https://proxy:port"
  }
}
```

**参数说明**：
- `default_model`: 默认使用的模型
- `timeout`: API请求超时时间（秒）
- `max_retries`: 最大重试次数
- `retry_delay`: 重试延迟（秒）
- `max_concurrent_requests`: 最大并发请求数
- `request_timeout`: 请求超时时间
- `max_image_size`: 最大图像尺寸
- `video_quality`: 视频质量设置

## 📋 节点详细说明

### 🎯 Doubao-Seed节点系列

ComfyUI Doubao-Seed提供了7个专业节点，全部归类在"Ken-Chen/Doubao"类别下，为用户提供统一的Doubao生态体验。

#### 📊 节点分类概览

**图像生成节点（2个）**
- **SeedReam4APINode** - 多图像输入的图像生成
- **SeedReam4APISingleNode** - 单图像生成和编辑

**视频生成节点（3个）**
- **DoubaoSeedanceVideoNode** - 基础视频生成功能
- **DoubaoSeedanceContinuousVideoNode** - 连续视频生成
- **DoubaoSeedanceMultiRefVideoNode** - 多图参考视频生成

**视频处理节点（2个）**
- **VideoStitchingNode** - 视频拼接处理
- **GetLastFrameNode** - 视频尾帧提取

---

### 🌐 Doubao-Seed节点详解

#### 1. SeedReam4API (多图) - SeedReam4APINode
**专业的多图像输入图像生成节点**

- **功能描述**: 基于Doubao Seedream4模型的高质量图像生成，支持多张参考图像输入
- **核心特性**:
  - ✅ **多图像输入**: 支持最多5张参考图像同时输入
  - ✅ **多镜像支持**: T8镜像站、ComFly、火山引擎等多种服务端点
  - ✅ **自动故障转移**: 主API失败时自动切换到备用服务
  - ✅ **高分辨率支持**: 1K/2K/4K多种分辨率选择
  - ✅ **灵活比例**: 支持9种预设比例和自定义尺寸
  - ✅ **批量生成**: 一次生成1-15张图像
  - ✅ **种子控制**: 支持固定种子获得可重现结果

- **主要参数**:
  - `prompt`: 图像描述提示词
  - `mirror_site`: 服务端点选择
  - `resolution`: 分辨率设置 (1K/2K/4K)
  - `aspect_ratio`: 宽高比选择
  - `max_images`: 生成图像数量 (1-15)
  - `image1-5`: 参考图像输入
  - `seed`: 随机种子控制
  - `watermark`: 水印开关

- **输出内容**: 生成的图像、响应信息、图像URL

#### 2. SeedReam4API (单图) - SeedReam4APISingleNode
**专业的单图像生成和编辑节点**

- **功能描述**: 专门用于单图像生成和基于参考图像的编辑变换
- **核心特性**:
  - ✅ **单图像专精**: 专注于单张图像的生成和编辑
  - ✅ **图像编辑**: 基于输入图像进行智能编辑和风格变换
  - ✅ **快速生成**: 优化的单图生成流程，响应更快
  - ✅ **多镜像支持**: T8镜像站、火山引擎官方API
  - ✅ **高质量输出**: 支持1K-4K高分辨率输出

- **主要参数**:
  - `prompt`: 图像描述或编辑指令
  - `mirror_site`: 服务端点 (t8_mirror, volcengine)
  - `image`: 参考图像输入
  - `resolution`: 分辨率设置
  - `aspect_ratio`: 宽高比选择
  - `max_images`: 生成数量
  - `seed`: 种子控制

- **适用场景**: 单图编辑、风格转换、图像优化、快速原型制作
#### 3. Doubao-Seedance视频生成 - DoubaoSeedanceVideoNode
**基础的文本到视频生成节点**

- **功能描述**: 基于Doubao Seedance模型的高质量视频生成功能
- **核心特性**:
  - ✅ **文本到视频**: 根据文本描述生成高质量视频
  - ✅ **多分辨率支持**: 支持720p、1080p等多种分辨率
  - ✅ **时长控制**: 支持3-12秒的视频时长设置
  - ✅ **多镜像支持**: T8镜像站、火山引擎官方API
  - ✅ **智能轮询**: 自动任务状态检查和结果获取

- **主要参数**:
  - `prompt`: 视频描述提示词
  - `mirror_site`: 服务端点选择
  - `resolution`: 视频分辨率
  - `duration`: 视频时长 (3-12秒)
  - `api_key`: API密钥
  - `seed`: 随机种子

- **输出内容**: 生成的视频文件、任务信息

#### 4. Doubao-Seedance连续视频生成 - DoubaoSeedanceContinuousVideoNode
**连续场景视频生成节点**

- **功能描述**: 支持连续场景和长视频生成的高级视频节点
- **核心特性**:
  - ✅ **连续生成**: 支持连续场景的视频生成
  - ✅ **长视频支持**: 支持更长时长的视频创作
  - ✅ **场景连贯**: 保持视频场景的连贯性和一致性
  - ✅ **高级控制**: 更多的视频生成参数控制

- **适用场景**: 故事叙述、连续动画、长视频创作

#### 5. Doubao-Seedance多图参考视频生成 - DoubaoSeedanceMultiRefVideoNode
**多图像参考视频生成节点**

- **功能描述**: 基于多张参考图像生成视频，支持图像序列到视频的转换
- **核心特性**:
  - ✅ **多图输入**: 支持多张参考图像输入
  - ✅ **图像序列**: 将图像序列转换为流畅视频
  - ✅ **风格一致**: 保持参考图像的风格和特征
  - ✅ **智能插帧**: 自动生成图像间的过渡帧

- **适用场景**: 图像动画化、产品展示视频、艺术创作

#### 6. doubao-seed-1-6 - DoubaoSeed16Node
**豆包大模型文本生成节点**

- **功能描述**: 基于火山引擎豆包大模型的高质量文本生成和内容创作
- **核心特性**:
  - ✅ **三模型支持**: 支持doubao-seed-1-6-250615、doubao-seed-1-6-flash-250615和doubao-seed-1-6-flash-250828模型
  - ✅ **多镜像站支持**: 支持Comfly、T8镜像站、火山引擎官方API
  - ✅ **智能文本生成**: 高质量的文章、对话、创意内容生成
  - ✅ **灵活参数控制**: 支持温度、top_p、token限制等参数调节
  - ✅ **系统提示词**: 可自定义系统角色和行为模式
  - ✅ **流式输出**: 支持实时流式文本生成
  - ✅ **使用统计**: 详细的token使用情况统计
  - ✅ **自动故障转移**: 主API失败时自动切换到备用服务

- **主要参数**:
  - `prompt`: 用户输入的提示词
  - `mirror_site`: 镜像站选择 (comfly / t8_mirror / volcengine)
  - `model`: 模型选择 (doubao-seed-1-6-250615 / doubao-seed-1-6-flash-250615 / doubao-seed-1-6-flash-250828)
  - `api_key`: API密钥
  - `max_tokens`: 最大生成token数 (1-4000)
  - `temperature`: 温度参数，控制随机性 (0.0-2.0)
  - `top_p`: 核采样参数 (0.0-1.0)
  - `system_prompt`: 系统提示词
  - `stream`: 是否流式输出
  - `presence_penalty`: 存在惩罚 (-2.0到2.0)
  - `frequency_penalty`: 频率惩罚 (-2.0到2.0)

- **输出内容**: 生成的文本、响应信息、使用情况统计

- **适用场景**: 内容创作、文章写作、对话生成、创意写作、代码生成

 
- **核心特性**:
  - ✅ **精确提取**: 准确获取视频的最后一帧
  - ✅ **高质量输出**: 保持原视频的图像质量
  - ✅ **格式兼容**: 支持多种视频格式输入
  - ✅ **ComfyUI集成**: 输出标准的ComfyUI图像格式

- **主要参数**:
  - `video`: 输入视频文件

- **输出内容**: 视频最后一帧的图像

- **适用场景**: 视频缩略图生成、关键帧提取、视频预览图制作

---
## 🚀 快速开始

### 5分钟快速上手

#### 步骤 1：安装插件

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/Ken-Chen/ComfyUI_Doubao_Seed.git
cd ComfyUI_Doubao_Seed
pip install -r requirements.txt
```

#### 步骤 2：配置API密钥

在项目根目录创建 `SeedReam4_config.json`:
```json
{
  "comfly_api_key": "your_comfly_api_key",
  "comfly_endpoint": "https://api.comfly.ai/v1"
}
```

**获取API密钥**：
- ComFly镜像站（推荐）: 访问ComFly官网注册
- T8镜像站: [https://api.t8.run](https://api.t8.run)
- 火山引擎官方: [https://console.volcengine.com/ark](https://console.volcengine.com/ark)

#### 步骤 3：重启ComfyUI

配置完成后重启ComfyUI，在节点列表中搜索 **"Ken-Chen/Doubao"**

#### 步骤 4：创建第一个连环画

1. **添加节点**：
   - 右键 → Add Node → Ken-Chen/Doubao → 豆包连环画创作

2. **配置参数**：
   ```
   story_prompt: "一个关于小猫咪学习飞翔的奇幻故事"
   mirror_site: comfly
   story_length: medium
   image_style: cartoon
   resolution: 2K
   aspect_ratio: 4:3
   ```

3. **添加预览节点**：
   - 添加 "连环画HTML浏览导出" 节点
   - 添加 "连环画HTML内嵌预览" 节点
   - 连接：
     ```
     豆包连环画创作.comic_images → 连环画HTML浏览导出.images
     豆包连环画创作.story_text → 连环画HTML浏览导出.story_structure
     连环画HTML浏览导出.viewer_path → 连环画HTML内嵌预览.viewer_path
     ```

4. **执行工作流**：
   - 点击 "Queue Prompt" 执行
   - 等待生成完成（约2-5分钟）
   - 在 "连环画HTML内嵌预览" 节点中查看结果

🎉 **恭喜！** 您已经成功创建了第一个连环画！

## 🚀 使用示例

### 📚 连环画创作示例（推荐）

#### 示例 1：基础连环画创作

**目标**：创作一个关于小兔子冒险的温馨故事

**步骤**：

1. **添加连环画创作节点**
   ```
   豆包连环画创作:
     story_prompt = "一个关于小兔子在森林里寻找魔法胡萝卜的冒险故事"
     mirror_site = "comfly"
     text_model = "doubao-seed-1-6-250615"
     image_model = "doubao-seedream-4-0-250828"
     story_length = "medium"
     image_style = "cartoon"
     resolution = "2K"
     aspect_ratio = "4:3"
     watermark = False
   ```

2. **添加HTML导出节点**
   ```
   连环画HTML浏览导出:
     images = 豆包连环画创作.comic_images
     story_structure = 豆包连环画创作.story_text
     title = "小兔子的魔法冒险"
     transition_effect = "page-turn"
     transition_duration = 1.5
   ```

3. **添加预览节点**
   ```
   连环画HTML内嵌预览:
     viewer_path = 连环画HTML浏览导出.viewer_path
     width = 800
     height = 600
     scale = 1.0
   ```

4. **执行工作流**
   - 点击 "Queue Prompt"
   - 等待生成完成（约3-5分钟）
   - 在预览节点中查看连环画

---

#### 示例 2：带参考图片的连环画

**目标**：使用参考图片创作风格一致的连环画

**步骤**：

1. **加载参考图片**
   ```
   Load Image:
     image = "character_reference.png"

   Load Image (2):
     image = "background_reference.png"
   ```

2. **创建连环画**
   ```
   豆包连环画创作:
     story_prompt = "小女孩和她的宠物狗在公园里的快乐时光"
     reference_images = Load Image.IMAGE
     reference_image_2 = Load Image (2).IMAGE
     character_description = "一个穿着黄色连衣裙的小女孩，扎着马尾辫"
     background_style = "阳光明媚的公园，有绿树和花朵"
     story_theme = "友谊、快乐、成长"
     story_length = "long"
     image_style = "cartoon"
     resolution = "2K"
   ```

3. **导出和预览**
   - 连接HTML导出节点
   - 连接预览节点
   - 执行工作流

---

#### 示例 3：完整导出工作流

**目标**：生成连环画并导出为多种格式

**步骤**：

1. **创建连环画**
   ```
   豆包连环画创作:
     story_prompt = "勇敢的小猫咪学习飞翔的故事"
     story_length = "medium"
     image_style = "anime"
     resolution = "2K"
   ```

2. **HTML导出**
   ```
   连环画HTML浏览导出:
     images = 豆包连环画创作.comic_images
     story_structure = 豆包连环画创作.story_text
     title = "飞翔的小猫咪"
   ```

3. **批量导出**
   ```
   连环画批量导出(PNG/JPG/PDF):
     images = 豆包连环画创作.comic_images
     story_structure = 豆包连环画创作.story_text
     title = "飞翔的小猫咪"
     image_format = "png"
     export_pdf = True
     pdf_with_text = True
   ```

4. **预览**
   ```
   连环画HTML内嵌预览:
     viewer_path = 连环画HTML浏览导出.viewer_path

   连环画浏览器预览:
     viewer_path = 连环画HTML浏览导出.viewer_path
     auto_open = False
   ```

**输出结果**：
- HTML文件：`web/exports/时间戳_飞翔的小猫咪.html`
- PNG图片：`web/exports/时间戳_飞翔的小猫咪/comic_export/page_01.png` ...
- PDF文件：`web/exports/时间戳_飞翔的小猫咪/comic_export/comic_story.pdf`
- 文本文件：`web/exports/时间戳_飞翔的小猫咪/comic_export/story_texts.txt`

---

### 📸 图像生成示例

#### 示例 4：基础图像生成

**目标**：生成一张高质量的图像

```
SeedReam4API (单图):
  prompt = "一只可爱的橘猫坐在阳光明媚的窗台上，温暖的光线，高质量摄影，4K，细节丰富"
  mirror_site = "t8_mirror"
  resolution = "2K"
  aspect_ratio = "16:9"
  max_images = 1
  watermark = False

Preview Image:
  images = SeedReam4API (单图).images
```

---

#### 示例 5：多图参考生成

**目标**：基于多张参考图生成新图像

```
Load Image (1-5):
  image = "reference_1.png" ... "reference_5.png"

SeedReam4API (多图):
  prompt = "结合参考图的风格，创作一幅梦幻的风景画"
  image1 = Load Image (1).IMAGE
  image2 = Load Image (2).IMAGE
  image3 = Load Image (3).IMAGE
  image4 = Load Image (4).IMAGE
  image5 = Load Image (5).IMAGE
  resolution = "2K"
  aspect_ratio = "4:3"
  max_images = 4

Preview Image:
  images = SeedReam4API (多图).images
```

---

### 🎬 视频生成示例

#### 示例 6：基础视频生成

**目标**：生成一段短视频

```
Doubao-Seedance视频生成:
  prompt = "一只小鸟在樱花树上歌唱，春天的微风轻抚花瓣，唯美画面"
  mirror_site = "t8_mirror"
  resolution = "1080p"
  duration = 6
  seed = 42

VHS_VideoCombine:
  images = Doubao-Seedance视频生成.video
  frame_rate = 24
  format = "video/h264-mp4"
```

---

#### 示例 7：多图参考视频生成

**目标**：基于图像序列生成视频

```
Load Image (序列):
  image = "frame_01.png" ... "frame_10.png"

Doubao-Seedance多图参考视频生成:
  prompt = "将这些图像转换为流畅的动画视频"
  reference_images = Load Image.IMAGE
  resolution = "1080p"
  duration = 8

VHS_VideoCombine:
  images = Doubao-Seedance多图参考视频生成.video
```

---

### 📝 文本生成示例

#### 示例 8：基础文本生成

**目标**：生成一篇文章

```
doubao-seed-1-6:
  prompt = "请写一篇关于人工智能在医疗领域应用的短文，包括现状、挑战和未来展望"
  mirror_site = "comfly"
  model = "doubao-seed-1-6-250615"
  max_tokens = 1000
  temperature = 0.7
  top_p = 0.9

Show Text:
  text = doubao-seed-1-6.generated_text
```

---

#### 示例 9：创意写作

**目标**：创作一个科幻故事

```
doubao-seed-1-6:
  prompt = "创作一个关于未来人类移民火星的科幻短故事"
  system_prompt = "你是一个创意写作专家，擅长创作引人入胜的科幻故事"
  mirror_site = "comfly"
  model = "doubao-seed-1-6-250615"
  max_tokens = 2000
  temperature = 0.9
  presence_penalty = 0.6
  frequency_penalty = 0.3

Show Text:
  text = doubao-seed-1-6.generated_text
```

 
## ⚙️ 性能优化

### 图像生成优化

**批量处理**：
- 支持1-15张图像同时生成
- 自动批处理优化内存使用
- 并行处理提高生成速度

**分辨率优化**：
- `1K (1024x1024)`: 快速生成，适合预览
- `2K (2048x2048)`: 平衡质量和速度（推荐）
- `4K (4096x4096)`: 最高质量，适合打印

**内存管理**：
- 自动释放未使用的图像缓存
- 大图像分块处理
- 优化的张量操作

### 视频生成优化

**任务轮询**：
- 智能任务状态检查
- 自动重试失败的任务
- 实时进度反馈

**质量控制**：
- 多级质量设置
- 自适应码率
- 平衡速度与效果

**格式兼容**：
- 支持MP4、AVI等多种格式
- 自动格式转换
- 兼容ComfyUI视频节点

### API调用优化

**多镜像支持**：
- 自动故障转移
- 负载均衡
- 智能路由选择

**重试机制**：
- 指数退避重试
- 最大重试次数限制
- 错误分类处理

**连接优化**：
- HTTP连接池
- Keep-Alive支持
- SSL优化

### 连环画创作优化

**并行生成**：
- 文本和图像并行生成
- 多场景并发处理
- 智能任务调度

**缓存策略**：
- 参考图像缓存
- 模型响应缓存
- 减少重复API调用

**内存优化**：
- 流式处理大型连环画
- 自动清理临时文件
- 优化的图像编码

### 性能建议

**推荐配置**（中等性能）：
```json
{
  "performance": {
    "max_concurrent_requests": 3,
    "request_timeout": 60,
    "retry_delay": 2,
    "max_image_size": "2K",
    "video_quality": "medium"
  }
}
```

**高性能配置**（高端设备）：
```json
{
  "performance": {
    "max_concurrent_requests": 5,
    "request_timeout": 120,
    "retry_delay": 1,
    "max_image_size": "4K",
    "video_quality": "high"
  }
}
```

**低配置优化**（低端设备）：
```json
{
  "performance": {
    "max_concurrent_requests": 1,
    "request_timeout": 30,
    "retry_delay": 3,
    "max_image_size": "1K",
    "video_quality": "low"
  }
}
```

## 🐛 故障排除

### 常见问题解决

#### 1. 连环画预览窗口空白 ⭐ 重要

**问题**：连环画HTML内嵌预览节点显示空白

**原因**：
- `WEB_DIRECTORY` 配置未正确加载
- 浏览器缓存问题
- HTML文件路径错误

**解决方案**：
1. 确认 `__init__.py` 中有 `WEB_DIRECTORY = "./web"` 定义
2. 重启 ComfyUI 服务器
3. 强制刷新浏览器（Ctrl+F5 或 Cmd+Shift+R）
4. 清除浏览器缓存
5. 检查 `web/comic_html_preview.js` 是否存在

**验证**：
- 在浏览器控制台（F12）查看是否有JavaScript错误
- 检查 `viewer_path` 输出是否正确
- 确认HTML文件确实生成在 `web/exports/` 目录

---

#### 2. API密钥配置问题

**问题**: "Invalid API key" 或认证失败

**解决方案**：
```json
// 检查 SeedReam4_config.json
{
  "comfly_api_key": "sk-xxxxxxxxxxxxxxxx",  // 确保格式正确
  "comfly_endpoint": "https://api.comfly.ai/v1"  // 确保URL正确
}
```

**验证步骤**：
1. 确认API密钥没有多余的空格或换行
2. 检查API密钥是否过期
3. 验证镜像站选择与API密钥匹配
4. 尝试在节点参数中直接输入API密钥测试

---

#### 3. 网络连接问题

**问题**: "Connection timeout" 或网络错误

**解决方案**：
```json
// 增加超时时间
{
  "timeout": 120,  // 从60秒增加到120秒
  "max_retries": 5,  // 增加重试次数
  "retry_delay": 3  // 增加重试延迟
}
```

**其他方法**：
- 切换到其他镜像站（comfly → t8_mirror → volcengine）
- 检查网络连接和防火墙设置
- 配置代理（如果需要）
- 检查API服务状态

---

#### 4. 图像生成失败

**问题**：图像生成返回错误或空结果

**常见原因**：
- ❌ 提示词违反内容政策
- ❌ API配额不足
- ❌ 分辨率设置不支持
- ❌ 参考图像格式错误

**解决方案**：
- 检查提示词是否符合内容政策
- 验证分辨率设置（推荐使用2K）
- 确认API余额和配额
- 查看ComfyUI控制台的详细错误信息

---

#### 5. 视频生成超时

**问题**: 视频生成任务长时间无响应

**正常情况**：
- 视频生成通常需要 **5-15分钟**
- 高分辨率视频可能需要 **20-30分钟**

**解决方案**：
- 减小分辨率（使用720p而不是1080p）
- 减少时长（使用4秒而不是8秒）
- 检查任务状态轮询日志
- 等待至少15分钟后再判断是否卡住

---

#### 6. 内存不足

**问题**: 生成大图像或长视频时内存溢出

**解决方案**：
- 减小图像分辨率（使用1K而不是4K）
- 减少批量生成数量（max_images = 1）
- 减少连环画场景数量（story_length = "short"）
- 关闭其他占用内存的程序
- 定期清理 `web/exports/` 目录

---

#### 7. 节点不显示

**问题**: 安装后在ComfyUI中找不到节点

**解决方案**：
1. 确认安装位置：`ComfyUI/custom_nodes/ComfyUI_Doubao_Seed`
2. 安装依赖：`pip install -r requirements.txt`
3. 检查 `__init__.py` 是否包含 `NODE_CLASS_MAPPINGS`
4. 重启 ComfyUI
5. 查看启动日志是否有 "[Doubao-Seed] Plugin loading completed!"

---

#### 8. PDF导出失败

**问题**: 连环画批量导出时PDF生成失败

**解决方案**：
```bash
# 安装PDF支持
pip install reportlab

# Windows用户：系统会自动使用 C:/Windows/Fonts/msyh.ttc
# Linux用户：
sudo apt-get install fonts-noto-cjk

# Mac用户：
brew install font-noto-sans-cjk
```

---

### 调试技巧

#### 1. 启用详细日志

在ComfyUI启动时添加 `--verbose` 参数：
```bash
python main.py --verbose
```

#### 2. 浏览器控制台调试

1. 按 `F12` 打开开发者工具
2. 切换到 `Console` 标签查看JavaScript错误
3. 切换到 `Network` 标签查看网络请求

#### 3. 验证配置文件

使用Python验证JSON格式：
```python
import json
with open('SeedReam4_config.json', 'r') as f:
    config = json.load(f)
    print("配置文件格式正确！")
```

---

### 获取帮助

如果问题仍未解决：

1. **📖 查看文档**：
   - `README.md` - 完整使用文档
   - `节点使用说明.md` - 节点详细说明
   - `COMIC_BOOK_USAGE_GUIDE.md` - 连环画使用指南

2. **🔍 搜索Issues**：
   - [GitHub Issues](https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/issues)

3. **📝 提交Issue**：
   - 提供详细的错误信息
   - 包含复现步骤
   - 附上ComfyUI控制台日志
   - 说明系统环境（OS、Python版本等）

4. **💬 社区支持**：
   - ComfyUI Discord服务器
   - 相关QQ群或微信群

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎提交问题报告和功能请求！如果您想贡献代码，请：

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📞 支持

如果您遇到问题或需要帮助：

- 提交 [GitHub Issue](https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/issues)
- 查看项目文档和示例
- 参考故障排除指南

## 🔄 更新日志

### v3.0.0 (最新) - 连环画创作完整解决方案 🎉

**📚 连环画创作系统（新增）:**
- ✅ **一键创作**: 豆包连环画创作节点，集成文本生成和图像生成
- ✅ **多种预览**: HTML内嵌预览、浏览器预览、分页浏览
- ✅ **批量导出**: 支持PNG/JPG/PDF多种格式导出
- ✅ **参考图像**: 支持最多10张参考图像，智能循环使用
- ✅ **交互HTML**: 生成可翻页的HTML连环画文件
- ✅ **翻页特效**: 支持5种翻页动画效果

**🎨 连环画节点（6个新节点）:**
- ✅ **豆包连环画创作**: 一键生成完整连环画
- ✅ **连环画分页浏览**: 分页预览连环画
- ✅ **连环画HTML浏览导出**: 生成交互式HTML文件
- ✅ **连环画HTML内嵌预览**: 在ComfyUI界面内预览
- ✅ **连环画浏览器预览**: 在系统浏览器中打开
- ✅ **连环画批量导出**: 批量导出图片和PDF

**🔧 技术改进:**
- ✅ **WEB_DIRECTORY配置**: 正确配置前端资源加载
- ✅ **iframe预览**: 完善的HTML内嵌预览功能
- ✅ **故事结构解析**: 支持JSON和格式化文本双格式
- ✅ **旁白显示修复**: 修复HTML中旁白显示问题
- ✅ **翻页特效优化**: 修复参数传递错误

**📝 文档完善:**
- ✅ **完整README**: 详尽的使用文档和示例
- ✅ **连环画指南**: 专门的连环画创作指南
- ✅ **故障排除**: 详细的问题解决方案
- ✅ **快速开始**: 5分钟快速上手指南

---

### v2.0.0 - Doubao-Seed专注化重构

**🎯 项目重构:**
- ✅ **专注化定位**: 100%专注于Doubao-Seed功能
- ✅ **品牌统一**: 所有节点统一归类到"Ken-Chen/Doubao"
- ✅ **代码简化**: 移除非核心模块，提升维护性
- ✅ **性能优化**: 更快的启动速度和更少的资源占用

**🎨 图像生成功能:**
- ✅ **多图输入**: 支持最多5张参考图像
- ✅ **高分辨率**: 支持1K/2K/4K多种分辨率
- ✅ **批量生成**: 一次生成1-15张图像
- ✅ **多镜像支持**: T8镜像站、火山引擎官方API

**🎬 视频生成功能:**
- ✅ **基础视频生成**: 文本到视频生成
- ✅ **连续视频生成**: 支持连续场景视频
- ✅ **多图参考视频**: 基于参考图像的视频生成
- ✅ **智能轮询**: 自动任务状态检查

**📝 文本生成功能:**
- ✅ **豆包大模型**: 支持doubao-seed-1-6系列模型
- ✅ **多模型选择**: 标准版和快速版
- ✅ **灵活配置**: 支持温度、top_p等参数调整

---

### 历史更新

**v1.5.0** - 视频处理增强
- 新增视频拼接功能，支持8个视频输入
- 新增视频尾帧提取功能
- 支持多种拼接布局

**v1.4.0** - 稳定性提升
- 优化视频生成节点
- 改进任务轮询机制
- 提升API调用稳定性

**v1.3.0** - 多图参考视频
- 新增多图参考视频生成功能
- 支持图像序列到视频转换
- 优化参考图像处理

**v1.2.0** - API优化
- 完善API故障转移机制
- 新增多镜像支持
- 改进错误处理

**v1.1.0** - 连续视频生成
- 新增连续视频生成功能
- 支持场景连续性
- 优化视频质量

**v1.0.0** - 初始版本
- 基础图像生成功能
- 基础视频生成功能
- T8镜像站支持

## 📚 相关文档

### 连环画创作文档
- [COMIC_BOOK_USAGE_GUIDE.md](COMIC_BOOK_USAGE_GUIDE.md) - 完整使用指南
- [QUICK_START_COMIC.md](QUICK_START_COMIC.md) - 快速入门
- [COMIC_TRANSITIONS_GUIDE.md](COMIC_TRANSITIONS_GUIDE.md) - 翻页特效指南
- [连环画浏览器预览节点说明.md](连环画浏览器预览节点说明.md) - 浏览器预览说明
- [连环画HTML内嵌预览节点说明.md](连环画HTML内嵌预览节点说明.md) - 内嵌预览说明

### 技术文档
- [STORY_STRUCTURE_PARSING_FIX.md](STORY_STRUCTURE_PARSING_FIX.md) - 故事结构解析修复
- [FORMATTED_TEXT_SUPPORT.md](FORMATTED_TEXT_SUPPORT.md) - 格式化文本支持
- [NARRATION_DISPLAY_FIX.md](NARRATION_DISPLAY_FIX.md) - 旁白显示修复
- [TRANSITION_FIX_SUMMARY.md](TRANSITION_FIX_SUMMARY.md) - 翻页特效修复
- [新功能完成报告.md](新功能完成报告.md) - 新功能完成报告

### 测试工具

```bash
# 测试JSON解析
python test_story_structure_parsing.py

# 测试格式化文本解析
python test_formatted_text_parsing.py

# 测试旁白显示
python test_narration_fix.py

# 测试HTML生成
python test_html_generation.py

# 诊断连环画解析
python diagnose_comic_parsing.py
```

## 🙏 致谢

感谢以下项目和开发者的贡献：

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) - 强大的AI工作流平台
- [火山引擎豆包](https://www.volcengine.com/product/doubao) - 提供强大的Doubao Seedream4模型
- [FFmpeg](https://ffmpeg.org/) - 视频处理核心库

## 🌟 特别说明

本项目专注于Doubao生态系统，致力于为用户提供：

- **🎯 专业品质**: 基于火山引擎豆包大模型的高质量生成
- **🚀 高效稳定**: 优化的API调用和任务处理机制
- **🔧 易于使用**: 简洁的节点设计和清晰的参数配置
- **📈 持续优化**: 专注于Doubao功能的持续改进和优化

---

**⚠️ 重要提示**:
- 使用本项目需要有效的Doubao API密钥
- 请遵守火山引擎豆包的使用条款和限制
- 建议在生产环境使用前进行充分测试
- 视频生成功能需要较长处理时间，请耐心等待

**💡 提示**: 如果您觉得这个项目有用，请给我们一个⭐星标支持！

**🔗 相关链接**:
- [火山引擎豆包官网](https://www.volcengine.com/product/doubao)
- [ComfyUI官方文档](https://github.com/comfyanonymous/ComfyUI)
- [项目GitHub仓库](https://github.com/Ken-Chen/ComfyUI_Doubao_Seed)

---

## 📱 联系方式

### 💬 微信交流

如果您在使用过程中遇到问题，或者有任何建议和想法，欢迎添加微信交流：

<div align="center">
  <img src="https://github.com/xuchenxu168/images/blob/main/%E5%BE%AE%E4%BF%A1%E5%8F%B7.jpg" alt="微信二维码" width="200"/>
  <p><strong>扫码添加微信</strong></p>
  <p>备注：ComfyUI Doubao</p>
</div>

**交流内容**：
- 🔧 技术支持和问题解答
- 💡 功能建议和需求讨论
- 📚 使用经验分享
- 🤝 合作交流

---

## 💖 支持项目

如果这个项目对您有帮助，欢迎通过以下方式支持项目的持续开发：

### ⭐ Star支持

给项目一个⭐星标是对我们最大的鼓励！

### 💰 赞赏支持

您的赞赏将用于：
- 🔧 项目持续维护和更新
- 📚 文档完善和教程制作
- 🚀 新功能开发
- 🌐 服务器和API测试费用

<div align="center">
  <img src="[wechat_pay_qrcode.png](https://github.com/xuchenxu168/images/blob/main/%E6%94%B6%E6%AC%BE%E7%A0%81.jpg)" alt="微信收款二维码" width="200"/>
  <p><strong>微信赞赏</strong></p>
  <p>感谢您的支持！</p>
</div>

### 🎁 赞赏福利

赞赏用户可获得：
- ✅ **优先技术支持** - 问题优先解答
- ✅ **专属交流群** - 加入核心用户群
- ✅ **新功能抢先体验** - 提前试用新功能
- ✅ **定制化建议** - 功能定制建议优先考虑

---

## 🌟 贡献者

感谢所有为这个项目做出贡献的开发者！

<div align="center">
  <a href="https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=Ken-Chen/ComfyUI_Doubao_Seed" />
  </a>
</div>

---

<div align="center">
  <p><strong>Made with ❤️ by Ken-Chen</strong></p>
  <p>© 2024 ComfyUI Doubao-Seed. All rights reserved.</p>
  <p>
    <a href="https://github.com/Ken-Chen/ComfyUI_Doubao_Seed">GitHub</a> •
    <a href="https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/issues">Issues</a> •
    <a href="https://github.com/Ken-Chen/ComfyUI_Doubao_Seed/discussions">Discussions</a>
  </p>
</div>

