#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查视频质量和拼接效果
"""

import os
import subprocess
import tempfile
import json

def check_video_info(video_path):
    """检查视频基本信息"""
    if not os.path.exists(video_path):
        return None
    
    try:
        cmd = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None
        
        info = json.loads(result.stdout)
        
        # 提取视频流信息
        video_stream = None
        audio_stream = None
        
        for stream in info.get('streams', []):
            if stream.get('codec_type') == 'video' and video_stream is None:
                video_stream = stream
            elif stream.get('codec_type') == 'audio' and audio_stream is None:
                audio_stream = stream
        
        if not video_stream:
            return None
        
        # 计算帧率
        fps_str = video_stream.get('r_frame_rate', '30/1')
        try:
            fps = eval(fps_str) if '/' in fps_str else float(fps_str)
        except:
            fps = 30.0
        
        return {
            'file_path': video_path,
            'file_size': os.path.getsize(video_path),
            'duration': float(video_stream.get('duration', 0)),
            'width': video_stream.get('width', 0),
            'height': video_stream.get('height', 0),
            'fps': fps,
            'codec': video_stream.get('codec_name', ''),
            'bitrate': video_stream.get('bit_rate', ''),
            'pix_fmt': video_stream.get('pix_fmt', ''),
            'has_audio': audio_stream is not None,
            'audio_codec': audio_stream.get('codec_name', '') if audio_stream else None
        }
        
    except Exception as e:
        print(f"❌ 分析视频失败: {str(e)}")
        return None

def extract_sample_frames(video_path, output_dir, num_frames=6):
    """提取样本帧"""
    info = check_video_info(video_path)
    if not info:
        return []
    
    duration = info['duration']
    if duration <= 0:
        return []
    
    # 计算提取时间点
    time_points = []
    if num_frames == 1:
        time_points = [duration / 2]
    else:
        for i in range(num_frames):
            time_point = (duration * i) / (num_frames - 1)
            time_points.append(min(time_point, duration - 0.1))
    
    extracted_frames = []
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    
    for i, time_point in enumerate(time_points):
        frame_path = os.path.join(output_dir, f"{video_name}_frame_{i:02d}_{time_point:.1f}s.png")
        
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-ss', str(time_point),
            '-vframes', '1',
            '-y',
            frame_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and os.path.exists(frame_path):
                extracted_frames.append({
                    'time': time_point,
                    'path': frame_path,
                    'size': os.path.getsize(frame_path)
                })
        except:
            continue
    
    return extracted_frames

def main():
    """主函数"""
    print("🎬 视频质量检查工具")
    print("="*50)
    
    # 检查测试生成的视频
    temp_base = tempfile.gettempdir()
    test_videos = [
        os.path.join(temp_base, 'stitched_1_基础concat拼接.mp4'),
        os.path.join(temp_base, 'stitched_2_平滑过渡concat拼接.mp4'),
        os.path.join(temp_base, 'stitched_3_交叉淡化拼接.mp4')
    ]
    
    # 创建输出目录
    output_dir = os.path.join(os.getcwd(), f"video_analysis_{int(__import__('time').time())}")
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📁 分析结果将保存到: {output_dir}")
    
    results = []
    
    for video_path in test_videos:
        if not os.path.exists(video_path):
            print(f"⚠️ 跳过不存在的文件: {os.path.basename(video_path)}")
            continue
        
        print(f"\n🔍 分析: {os.path.basename(video_path)}")
        
        # 获取视频信息
        info = check_video_info(video_path)
        if not info:
            print(f"❌ 无法获取视频信息")
            continue
        
        # 提取样本帧
        frames = extract_sample_frames(video_path, output_dir, 6)
        
        info['frames'] = frames
        results.append(info)
        
        # 显示基本信息
        print(f"   📊 分辨率: {info['width']}x{info['height']}")
        print(f"   🎞️ 帧率: {info['fps']:.2f} fps")
        print(f"   ⏱️ 时长: {info['duration']:.2f} 秒")
        print(f"   📦 文件大小: {info['file_size']/1024:.1f} KB")
        print(f"   🎨 编码: {info['codec']} ({info['pix_fmt']})")
        print(f"   🔊 音频: {'有' if info['has_audio'] else '无'}")
        print(f"   🖼️ 提取帧数: {len(frames)}")
    
    # 生成对比报告
    if results:
        print("\n" + "="*60)
        print("📊 视频对比总结")
        print("="*60)
        
        # 按方法分类
        methods = {
            '基础concat拼接': None,
            '平滑过渡concat拼接': None,
            '交叉淡化拼接': None
        }
        
        for result in results:
            filename = os.path.basename(result['file_path'])
            for method in methods.keys():
                if method in filename:
                    methods[method] = result
                    break
        
        print("\n🎯 不同方法对比:")
        for method, result in methods.items():
            if result:
                efficiency = result['file_size'] / result['duration'] if result['duration'] > 0 else 0
                print(f"  📹 {method}:")
                print(f"     文件大小: {result['file_size']/1024:.1f} KB")
                print(f"     压缩效率: {efficiency/1024:.1f} KB/秒")
                print(f"     帧数: {len(result['frames'])}")
            else:
                print(f"  ❌ {method}: 未找到")
        
        # 生成简单的HTML报告
        html_path = os.path.join(output_dir, "quality_report.html")
        generate_html_report(results, html_path)
        
        print(f"\n🌐 详细报告: {html_path}")
        print("💡 用浏览器打开查看详细对比")
        
        # 结论和建议
        print("\n🎯 分析结论:")
        if len(results) >= 2:
            sizes = [r['file_size'] for r in results]
            min_size = min(sizes)
            max_size = max(sizes)
            
            if max_size > min_size * 1.5:
                print("  • 不同方法的文件大小差异较大，建议根据需求选择")
            else:
                print("  • 不同方法的文件大小相近，可以优先考虑质量")
            
            print("  • 基础concat适合快速拼接")
            print("  • 平滑过渡适合减少闪烁")
            print("  • 交叉淡化适合艺术效果")
        
        print(f"\n📁 所有分析文件保存在: {output_dir}")
    
    else:
        print("❌ 没有找到可分析的视频文件")

def generate_html_report(results, html_path):
    """生成HTML报告"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>视频质量分析报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; }}
        .video-section {{ margin: 20px 0; border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
        .frame-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 15px; }}
        .frame-item {{ text-align: center; }}
        .frame-item img {{ max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 3px; }}
        .frame-time {{ font-size: 11px; color: #666; margin-top: 5px; }}
        .info-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        .info-table th, .info-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        .info-table th {{ background-color: #f2f2f2; }}
        h1 {{ color: #333; text-align: center; }}
        h2 {{ color: #666; border-bottom: 2px solid #eee; padding-bottom: 5px; }}
        .summary {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 视频拼接质量分析报告</h1>
        <p style="text-align: center; color: #666;">生成时间: {__import__('time').strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <div class="summary">
            <h3>📊 总体概况</h3>
            <p>本次分析了 {len(results)} 个视频文件，对比了不同拼接方法的效果。</p>
        </div>
"""
    
    for i, result in enumerate(results):
        video_name = os.path.basename(result['file_path'])
        method_name = video_name.replace('stitched_', '').replace('.mp4', '')
        
        html_content += f"""
        <div class="video-section">
            <h2>📹 {method_name}</h2>
            
            <table class="info-table">
                <tr><th>属性</th><th>值</th></tr>
                <tr><td>文件大小</td><td>{result['file_size']/1024:.1f} KB</td></tr>
                <tr><td>分辨率</td><td>{result['width']} × {result['height']}</td></tr>
                <tr><td>帧率</td><td>{result['fps']:.2f} fps</td></tr>
                <tr><td>时长</td><td>{result['duration']:.2f} 秒</td></tr>
                <tr><td>编码格式</td><td>{result['codec']}</td></tr>
                <tr><td>像素格式</td><td>{result['pix_fmt']}</td></tr>
                <tr><td>音频</td><td>{'有 (' + result['audio_codec'] + ')' if result['has_audio'] else '无'}</td></tr>
            </table>
            
            <h3>🖼️ 样本帧 ({len(result['frames'])} 帧)</h3>
            <div class="frame-grid">
"""
        
        for frame in result['frames']:
            frame_name = os.path.basename(frame['path'])
            html_content += f"""
                <div class="frame-item">
                    <img src="{frame_name}" alt="Frame at {frame['time']:.1f}s">
                    <div class="frame-time">{frame['time']:.1f}s<br>({frame['size']/1024:.1f}KB)</div>
                </div>
"""
        
        html_content += """
            </div>
        </div>
"""
    
    html_content += """
        <div class="summary">
            <h3>💡 使用建议</h3>
            <ul>
                <li><strong>基础concat拼接</strong>: 速度最快，适合属性一致的视频</li>
                <li><strong>平滑过渡concat拼接</strong>: 减少闪烁，适合一般用途</li>
                <li><strong>交叉淡化拼接</strong>: 艺术效果，适合需要过渡效果的场景</li>
            </ul>
        </div>
    </div>
</body>
</html>
"""
    
    try:
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return True
    except Exception as e:
        print(f"❌ 生成HTML报告失败: {str(e)}")
        return False

if __name__ == "__main__":
    main()
