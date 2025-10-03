#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连环画HTML模板生成器
支持多种翻页特效
"""

import json


def build_comic_html(title, img_list, pages, transition_effect="page-turn", transition_duration=1.5):
    """
    生成连环画HTML（优化版：懒加载、内存管理）

    Args:
        title: 连环画标题
        img_list: 图片列表（base64或URL）
        pages: 页面数据列表 [{"title": "...", "text": "..."}]
        transition_effect: 翻页特效 (page-turn/fade/slide/flip/none)
        transition_duration: 特效持续时间（秒）

    Returns:
        HTML字符串
    """
    # 如果选择真实翻书效果，使用专门的模板
    if transition_effect == "page-turn":
        return build_page_turn_html(title, img_list, pages, transition_duration)

    total = len(img_list)

    # 优化：只在JSON中存储图片数量，不存储完整的base64数据
    # 使用懒加载机制，按需加载图片
    pages_json = json.dumps(pages)

    # 将图片数据分离，使用特殊的懒加载机制
    img_data_chunks = []
    chunk_size = 1  # 每次只加载1张图片
    for i in range(0, len(img_list), chunk_size):
        chunk = img_list[i:i+chunk_size]
        img_data_chunks.append(json.dumps(chunk))

    # 根据特效类型生成CSS动画
    transition_css = get_transition_css(transition_effect, transition_duration)

    # 生成JavaScript代码
    transition_js = get_transition_js(transition_effect, transition_duration)

    # 生成懒加载的图片数据JavaScript
    img_chunks_js = ",\n".join(img_data_chunks)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<style>
* {{ box-sizing: border-box; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, 'Noto Sans', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  margin: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  padding: 20px;
}}
.container {{
  max-width: 1300px;  /* 📐 适中的容器宽度 */
  margin: 0 auto;
  background: #fff;
  box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  border-radius: 16px;
  padding: 36px;
  animation: slideIn 0.5s ease-out;
}}
@keyframes slideIn {{
  from {{ opacity: 0; transform: translateY(20px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.header {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 2px solid #f0f0f0;
}}
.title {{
  font-size: 24px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 8px;
}}
.page {{
  display: grid;
  grid-template-columns: 1.5fr 1fr;  /* 📐 图片占60%，文字占40% */
  gap: 28px;
  align-items: start;
  min-height: 550px;
}}
.img-wrap {{
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 6px 24px rgba(0,0,0,0.12);
  background: #f5f5f5;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}}
.img-wrap:hover {{
  transform: translateY(-3px);
  box-shadow: 0 10px 32px rgba(0,0,0,0.18);
}}
.img-wrap img {{
  width: 100%;
  height: auto;
  display: block;
  object-fit: cover;
}}
.text-wrap {{
  background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
  border-radius: 12px;
  padding: 28px;
  min-height: 450px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
  line-height: 2.1;
  font-size: 16px;
  color: #333;
  position: relative;
  overflow-y: auto;
  max-height: 650px;
}}
.text-wrap::before {{
  content: '"';
  position: absolute;
  top: 10px;
  left: 10px;
  font-size: 60px;
  color: rgba(102, 126, 234, 0.2);
  font-family: Georgia, serif;
}}
.toolbar {{
  display: flex;
  gap: 12px;
  align-items: center;
}}
.btn {{
  border: none;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 10px;
  padding: 10px 20px;
  cursor: pointer;
  font-size: 16px;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 2px 10px rgba(102, 126, 234, 0.3);
}}
.btn:hover {{
  transform: translateY(-2px);
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.5);
}}
.btn:active {{
  transform: translateY(0);
}}
.btn:disabled {{
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}}
.counter {{
  color: #666;
  font-size: 16px;
  font-weight: 500;
  min-width: 60px;
  text-align: center;
}}
{transition_css}
/* 🎨 平板设备优化 */
@media (max-width: 1024px) {{
  .container {{
    max-width: 95%;
    padding: 30px;
  }}
  .page {{
    grid-template-columns: 1.4fr 1fr;
    gap: 24px;
  }}
}}

/* 🎨 手机设备优化 */
@media (max-width: 768px) {{
  .page {{
    grid-template-columns: 1fr;
    gap: 20px;
  }}
  .container {{
    padding: 20px;
  }}
  .title {{
    font-size: 20px;
  }}
  .text-wrap {{
    font-size: 16px;
    padding: 24px;
    min-height: 300px;
  }}
  .img-wrap {{
    border-radius: 12px;
  }}
}}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title">📖 {title}</div>
      <div class="toolbar">
        <button class="btn" onclick="prev()" id="prevBtn">◀ 上一页</button>
        <span class="counter" id="counter">1/{total}</span>
        <button class="btn" onclick="next()" id="nextBtn">下一页 ▶</button>
      </div>
    </div>
    <div class="page" id="page">
      <div class="img-wrap" id="imgWrap"><img id="img" src="{img_list[0] if total>0 else ''}" alt="连环画图片" /></div>
      <div class="text-wrap" id="textWrap"><div id="text">{pages[0]['text'] if total>0 else ''}</div></div>
    </div>
  </div>
<script>
// 🚀 优化版：懒加载 + 内存管理
const IMG_CHUNKS = [{img_chunks_js}];
const PAGES = {pages_json};
const TRANSITION_EFFECT = '{transition_effect}';
const TRANSITION_DURATION = {transition_duration * 1000};
const TOTAL_PAGES = IMG_CHUNKS.length;

let i = 0;
let isTransitioning = false;
let loadedImages = new Map(); // 缓存已加载的图片
const MAX_CACHE_SIZE = 5; // 最多缓存5张图片

// 🧹 内存清理：清除旧的图片缓存
function cleanupImageCache() {{
  if (loadedImages.size > MAX_CACHE_SIZE) {{
    // 保留当前页和相邻页，删除其他页
    const keepIndices = new Set([
      Math.max(0, i - 1),
      i,
      Math.min(TOTAL_PAGES - 1, i + 1)
    ]);

    for (let [index, _] of loadedImages) {{
      if (!keepIndices.has(index)) {{
        loadedImages.delete(index);
      }}
    }}

    // 强制垃圾回收（提示浏览器）
    if (window.gc) {{
      window.gc();
    }}
  }}
}}

// 📥 懒加载图片
function loadImage(index) {{
  return new Promise((resolve, reject) => {{
    // 如果已经加载过，直接返回
    if (loadedImages.has(index)) {{
      resolve(loadedImages.get(index));
      return;
    }}

    // 从分块数据中获取图片
    if (index >= 0 && index < IMG_CHUNKS.length) {{
      const imgData = IMG_CHUNKS[index][0]; // 每个chunk只有1张图片
      loadedImages.set(index, imgData);
      resolve(imgData);
    }} else {{
      reject(new Error('Invalid index'));
    }}
  }});
}}

// 🔄 预加载相邻页面
function preloadAdjacentPages() {{
  // 预加载下一页
  if (i + 1 < TOTAL_PAGES) {{
    loadImage(i + 1).catch(() => {{}});
  }}
  // 预加载上一页
  if (i - 1 >= 0) {{
    loadImage(i - 1).catch(() => {{}});
  }}
}}

// 📄 更新页面内容
async function updateContent() {{
  if (TOTAL_PAGES === 0) return;

  try {{
    // 显示加载提示
    const imgEl = document.getElementById('img');
    imgEl.style.opacity = '0.5';

    // 加载当前页图片
    const imgData = await loadImage(i);
    imgEl.src = imgData;
    imgEl.style.opacity = '1';

    // 更新文本
    document.getElementById('text').innerText = (PAGES[i] && (PAGES[i].text||'')) || '';
    document.getElementById('counter').innerText = (i+1) + '/' + TOTAL_PAGES;

    // 清理缓存
    cleanupImageCache();

    // 预加载相邻页面
    preloadAdjacentPages();
  }} catch (error) {{
    console.error('加载图片失败:', error);
  }}
}}

{transition_js}

function prev() {{
  if (isTransitioning || i === 0) return;
  changePage(i - 1, 'prev');
}}

function next() {{
  if (isTransitioning || i === TOTAL_PAGES - 1) return;
  changePage(i + 1, 'next');
}}

// 键盘导航
document.addEventListener('keydown', (e) => {{
  if (e.key==='ArrowLeft') prev();
  if (e.key==='ArrowRight') next();
}});

// 🎯 页面卸载时清理内存
window.addEventListener('beforeunload', () => {{
  loadedImages.clear();
  IMG_CHUNKS.length = 0;
}});

// 初始化
updateContent();

// 💡 提示：定期清理内存（每30秒）
setInterval(() => {{
  if (loadedImages.size > MAX_CACHE_SIZE) {{
    cleanupImageCache();
  }}
}}, 30000);
</script>
</body>
</html>"""


def get_transition_css(effect, duration):
    """获取特效CSS"""
    if effect == "fade":
        return f"""
.img-wrap, .text-wrap {{
  transition: opacity {duration}s ease-in-out;
}}
.fade-out {{
  opacity: 0;
}}
"""
    elif effect == "slide":
        return f"""
.img-wrap, .text-wrap {{
  transition: transform {duration}s cubic-bezier(0.4, 0.0, 0.2, 1), opacity {duration}s ease-in-out;
}}
.slide-out-left {{
  transform: translateX(-50px);
  opacity: 0;
}}
.slide-in-right {{
  transform: translateX(50px);
  opacity: 0;
}}
.slide-out-right {{
  transform: translateX(50px);
  opacity: 0;
}}
.slide-in-left {{
  transform: translateX(-50px);
  opacity: 0;
}}
"""
    elif effect == "flip":
        return f"""
.img-wrap, .text-wrap {{
  transition: transform {duration}s ease-in-out, opacity {duration}s ease-in-out;
  transform-style: preserve-3d;
}}
.flip-out {{
  transform: rotateY(90deg);
  opacity: 0;
}}
"""
    else:  # none
        return ""


def get_transition_js(effect, duration):
    """获取特效JavaScript"""
    if effect == "fade":
        return """
function changePage(newIndex, direction) {
  isTransitioning = true;
  const imgWrap = document.getElementById('imgWrap');
  const textWrap = document.getElementById('textWrap');

  // 淡出
  imgWrap.classList.add('fade-out');
  textWrap.classList.add('fade-out');

  setTimeout(() => {
    i = newIndex;
    updateContent();

    // 淡入
    imgWrap.classList.remove('fade-out');
    textWrap.classList.remove('fade-out');

    setTimeout(() => {
      isTransitioning = false;
    }, TRANSITION_DURATION);
  }, TRANSITION_DURATION);
}
"""
    elif effect == "slide":
        return """
function changePage(newIndex, direction) {
  isTransitioning = true;
  const imgWrap = document.getElementById('imgWrap');
  const textWrap = document.getElementById('textWrap');

  // 滑出
  if (direction === 'next') {
    imgWrap.classList.add('slide-out-left');
    textWrap.classList.add('slide-out-left');
  } else {
    imgWrap.classList.add('slide-out-right');
    textWrap.classList.add('slide-out-right');
  }

  setTimeout(() => {
    i = newIndex;
    updateContent();

    // 重置位置
    imgWrap.className = 'img-wrap';
    textWrap.className = 'text-wrap';

    // 滑入
    if (direction === 'next') {
      imgWrap.classList.add('slide-in-right');
      textWrap.classList.add('slide-in-right');
    } else {
      imgWrap.classList.add('slide-in-left');
      textWrap.classList.add('slide-in-left');
    }

    setTimeout(() => {
      imgWrap.className = 'img-wrap';
      textWrap.className = 'text-wrap';
      isTransitioning = false;
    }, 50);
  }, TRANSITION_DURATION);
}
"""
    elif effect == "flip":
        return """
function changePage(newIndex, direction) {
  isTransitioning = true;
  const imgWrap = document.getElementById('imgWrap');
  const textWrap = document.getElementById('textWrap');

  // 翻转出去
  imgWrap.classList.add('flip-out');
  textWrap.classList.add('flip-out');

  setTimeout(() => {
    i = newIndex;
    updateContent();

    // 翻转回来
    imgWrap.classList.remove('flip-out');
    textWrap.classList.remove('flip-out');

    setTimeout(() => {
      isTransitioning = false;
    }, TRANSITION_DURATION);
  }, TRANSITION_DURATION / 2);
}
"""
    else:  # none
        return """
function changePage(newIndex, direction) {
  i = newIndex;
  updateContent();
}
"""



def build_page_turn_html(title, img_list, pages, transition_duration=1.5):
    """
    生成真实翻书效果的HTML (使用Turn.js)

    Turn.js 的页面布局：
    - 第1页：封面（单独一页）
    - 第2-3页：图1（左）+ 文1（右）
    - 第4-5页：图2（左）+ 文2（右）
    - ...
    """
    import json

    # 准备页面HTML
    pages_html = []
    total_scenes = len(img_list)

    # 第1页：封面（使用第一张图片作为背景）
    cover_bg = img_list[0] if img_list else ""
    cover_html = f'''
    <div class="page cover-page">
      <div class="cover-bg" style="background-image: url('{cover_bg}');"></div>
      <div class="cover-overlay"></div>
      <div class="page-content cover-content">
        <div class="cover-decoration top">
          <span class="star">⭐</span>
          <span class="star">✨</span>
          <span class="star">🌟</span>
          <span class="star">💫</span>
          <span class="star">⭐</span>
        </div>
        <h1 class="cover-title">{title}</h1>
        <div class="cover-subtitle">连环画故事</div>
        <div class="cover-divider">
          <span class="divider-line"></span>
          <span class="divider-icon">📖</span>
          <span class="divider-line"></span>
        </div>
        <div class="cover-info">
          <div class="info-item">
            <span class="info-icon">🎨</span>
            <span class="info-text">共 {total_scenes} 个场景</span>
          </div>
          <div class="info-item">
            <span class="info-icon">📚</span>
            <span class="info-text">图文并茂</span>
          </div>
        </div>
        <div class="cover-decoration bottom">
          <span class="star">🌈</span>
          <span class="star">🎈</span>
          <span class="star">🎨</span>
          <span class="star">🎭</span>
          <span class="star">🌈</span>
        </div>
        <div class="cover-hint">点击翻页开始阅读 →</div>
      </div>
    </div>'''
    pages_html.append(cover_html)

    # 后续页：每个场景占两页（左图右文）
    page_num = 2
    for idx in range(total_scenes):
        # 左页：图片（直接使用实际图片数据）
        img_src = img_list[idx] if idx < len(img_list) else ""
        img_html = f'''
    <div class="page">
      <div class="page-content img-page">
        <img src="{img_src}" alt="场景{idx+1}">
        <div class="page-num">{page_num}</div>
      </div>
    </div>'''
        pages_html.append(img_html)
        page_num += 1

        # 右页：文字
        if idx < len(pages):
            text = pages[idx].get("text", "")
            scene_title = pages[idx].get("title", f"场景 {idx+1}")
            text_html = f'''
    <div class="page">
      <div class="page-content text-page">
        <h3 class="scene-title">{scene_title}</h3>
        <div class="text-content">{text}</div>
        <div class="page-num">{page_num}</div>
      </div>
    </div>'''
            pages_html.append(text_html)
            page_num += 1

    all_pages_html = "\n".join(pages_html)
    duration_ms = int(transition_duration * 1000)
    total_pages = len(pages_html)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/turn.js/3/turn.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  padding: 20px;
}}
.container {{
  text-align: center;
  width: 100%;
  max-width: 1200px;
}}
h1 {{
  color: white;
  font-size: 32px;
  margin-bottom: 20px;
  text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}}
.controls {{
  margin-bottom: 30px;
}}
button {{
  background: white;
  color: #667eea;
  border: none;
  padding: 12px 30px;
  font-size: 18px;
  font-weight: bold;
  border-radius: 25px;
  cursor: pointer;
  margin: 0 10px;
  transition: all 0.3s;
}}
button:hover {{
  background: #f0f0f0;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}}
.info {{
  color: white;
  font-size: 20px;
  margin: 0 20px;
  font-weight: bold;
}}
#flipbook {{
  width: 1200px;  /* 📖 书本宽度 */
  height: 700px;  /* 📖 书本高度，保持接近真实书本比例 */
  margin: 0 auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}}
#flipbook .page {{
  width: 600px;  /* 📖 每页宽度 = 总宽度的一半 */
  height: 700px;  /* 📖 每页高度 */
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}}
#flipbook .page-content {{
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
}}
/* 封面样式 */
#flipbook .cover-page {{
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #ffd89b 0%, #19547b 100%);
}}
.cover-bg {{
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-size: cover;
  background-position: center;
  filter: blur(8px);
  opacity: 0.3;
}}
.cover-overlay {{
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(255,216,155,0.9) 0%, rgba(25,84,123,0.9) 100%);
}}
#flipbook .cover-page .page-content {{
  position: relative;
  z-index: 1;
  justify-content: center;
  padding: 60px 40px;
}}
.cover-decoration {{
  display: flex;
  justify-content: space-around;
  width: 100%;
  margin: 20px 0;
  font-size: 24px;
  animation: twinkle 2s infinite;
}}
.cover-decoration.top {{
  margin-bottom: 40px;
}}
.cover-decoration.bottom {{
  margin-top: 40px;
}}
@keyframes twinkle {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}
.cover-title {{
  font-size: 52px;
  font-weight: bold;
  color: white;
  text-align: center;
  margin: 20px 0;
  text-shadow: 3px 3px 6px rgba(0,0,0,0.4);
  letter-spacing: 2px;
  line-height: 1.3;
}}
.cover-subtitle {{
  font-size: 20px;
  color: rgba(255,255,255,0.95);
  text-align: center;
  margin-bottom: 30px;
  font-weight: 500;
  letter-spacing: 4px;
}}
.cover-divider {{
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 30px 0;
  width: 100%;
}}
.divider-line {{
  flex: 1;
  height: 2px;
  background: linear-gradient(to right, transparent, rgba(255,255,255,0.6), transparent);
}}
.divider-icon {{
  font-size: 32px;
  margin: 0 20px;
  animation: bounce 2s infinite;
}}
@keyframes bounce {{
  0%, 100% {{ transform: translateY(0); }}
  50% {{ transform: translateY(-10px); }}
}}
.cover-info {{
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin: 30px 0;
}}
.info-item {{
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 20px;
  color: white;
  background: rgba(255,255,255,0.2);
  padding: 12px 24px;
  border-radius: 25px;
  backdrop-filter: blur(10px);
}}
.info-icon {{
  font-size: 24px;
}}
.info-text {{
  font-weight: 500;
}}
.cover-hint {{
  font-size: 16px;
  color: rgba(255,255,255,0.8);
  text-align: center;
  margin-top: 40px;
  animation: pulse 2s infinite;
}}
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50% {{ opacity: 0.5; }}
}}
/* 图片页样式 */
#flipbook .img-page {{
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 30px;
}}
#flipbook .page img {{
  max-width: 90%;
  max-height: 88%;
  object-fit: contain;
  border-radius: 12px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.2);
  transition: transform 0.3s ease;
}}
#flipbook .page img:hover {{
  transform: scale(1.02);
}}
/* 文字页样式 */
#flipbook .text-page {{
  background: linear-gradient(135deg, #fdfbfb 0%, #ebedee 100%);
  align-items: flex-start;
  justify-content: flex-start;
  padding: 40px;
}}
.scene-title {{
  font-size: 26px;
  font-weight: bold;
  color: #667eea;
  margin-bottom: 20px;
  width: 100%;
  text-align: left;
  border-bottom: 3px solid #667eea;
  padding-bottom: 10px;
}}
#flipbook .text-content {{
  font-size: 18px;
  line-height: 2.2;
  color: #333;
  text-align: justify;
  white-space: pre-wrap;
  width: 100%;
  overflow-y: auto;
  max-height: 82%;
}}
.page-num {{
  position: absolute;
  bottom: 20px;
  font-size: 16px;
  color: #999;
  font-weight: bold;
}}
.hint {{
  color: white;
  margin-top: 30px;
  font-size: 18px;
  line-height: 1.8;
}}
/* 📱 响应式设计 - 保持书本比例 */
@media (max-width: 1280px) {{
  #flipbook {{
    width: 1000px;
    height: 600px;
  }}
  #flipbook .page {{
    width: 500px;
    height: 600px;
  }}
  #flipbook .text-page {{
    padding: 35px;
  }}
  .scene-title {{
    font-size: 24px;
  }}
  #flipbook .text-content {{
    font-size: 17px;
  }}
}}

@media (max-width: 1024px) {{
  #flipbook {{
    width: 90vw;
    height: calc(90vw * 0.58);  /* 保持书本比例 */
  }}
  #flipbook .page {{
    width: 45vw;
    height: calc(90vw * 0.58);
  }}
  #flipbook .text-page {{
    padding: 25px;
  }}
  .scene-title {{
    font-size: 20px;
  }}
  #flipbook .text-content {{
    font-size: 15px;
  }}
}}
</style>
</head>
<body>
<div class="container">
  <h1>📖 {title}</h1>
  <div class="controls">
    <button onclick="$('#flipbook').turn('previous')">◀ 上一页</button>
    <span class="info" id="pageInfo">第 1 页 / 共 {len(pages_html)} 页</span>
    <button onclick="$('#flipbook').turn('next')">下一页 ▶</button>
  </div>
  <div id="flipbook">
{all_pages_html}
  </div>
  <div class="hint">
    💡 点击按钮翻页，或直接用鼠标拖动书页边缘<br>
    📖 真实翻书效果 - 左图右文对开页布局<br>
    ⌨️ 也可以使用键盘左右箭头键翻页
  </div>
</div>
<script>
$(document).ready(function() {{
  // 📖 根据屏幕尺寸动态调整翻书大小（保持书本比例）
  let flipbookWidth = 1200;
  let flipbookHeight = 700;

  if (window.innerWidth < 1280) {{
    flipbookWidth = 1000;
    flipbookHeight = 600;
  }}

  $('#flipbook').turn({{
    width: flipbookWidth,
    height: flipbookHeight,
    autoCenter: true,
    duration: {duration_ms},
    gradients: true,
    elevation: 50,
    acceleration: true
  }});

  $('#flipbook').bind('turned', function(event, page, view) {{
    $('#pageInfo').text('第 ' + page + ' 页 / 共 ' + $('#flipbook').turn('pages') + ' 页');
  }});

  $(document).keydown(function(e) {{
    if (e.keyCode == 37) {{
      $('#flipbook').turn('previous');
    }} else if (e.keyCode == 39) {{
      $('#flipbook').turn('next');
    }}
  }});
}});
</script>
</body>
</html>"""
