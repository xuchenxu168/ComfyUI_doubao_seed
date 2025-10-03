#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试文本生成API是否正常工作
"""

import json
import requests
import os

def test_text_generation():
    """测试文本生成API"""
    
    print("=" * 60)
    print("🧪 测试文本生成API")
    print("=" * 60)
    
    # 1. 读取配置文件
    config_path = os.path.join(os.path.dirname(__file__), 'SeedReam4_config.json')
    
    if not os.path.exists(config_path):
        print("❌ 配置文件不存在:", config_path)
        return False
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print("✅ 配置文件读取成功")
    
    # 2. 获取comfly配置
    mirror_sites = config.get('mirror_sites', {})
    comfly_config = mirror_sites.get('comfly', {})
    
    if not comfly_config:
        print("❌ 未找到comfly配置")
        return False
    
    api_url = comfly_config.get('url', '')
    api_key = comfly_config.get('api_key', '')
    text_models = comfly_config.get('text_models', [])
    
    print(f"📍 API端点: {api_url}")
    print(f"🔑 API密钥: {api_key[:20]}..." if api_key else "❌ 未配置API密钥")
    print(f"📝 支持的文本模型: {text_models}")
    
    if not api_key:
        print("❌ API密钥未配置")
        return False
    
    # 3. 构建请求
    chat_url = api_url.rstrip('/') + '/chat/completions'
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ComfyUI-Doubao-Seed/Test"
    }
    
    request_data = {
        "model": "doubao-seed-1-6-250615",
        "messages": [
            {"role": "system", "content": "你是一个有帮助的AI助手。"},
            {"role": "user", "content": "请用一句话介绍一下你自己。"}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 0.9
    }
    
    print("\n" + "=" * 60)
    print("📤 发送测试请求...")
    print("=" * 60)
    print(f"URL: {chat_url}")
    print(f"Model: {request_data['model']}")
    print(f"Prompt: {request_data['messages'][1]['content']}")
    
    # 4. 发送请求
    try:
        response = requests.post(
            chat_url,
            headers=headers,
            json=request_data,
            timeout=60
        )
        
        print(f"\n📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API调用成功！")
            
            try:
                result = response.json()
                print("\n" + "=" * 60)
                print("📄 响应内容:")
                print("=" * 60)
                print(json.dumps(result, indent=2, ensure_ascii=False))
                
                # 提取生成的文本
                if 'choices' in result and len(result['choices']) > 0:
                    generated_text = result['choices'][0].get('message', {}).get('content', '')
                    print("\n" + "=" * 60)
                    print("✨ 生成的文本:")
                    print("=" * 60)
                    print(generated_text)
                    print("\n✅ 文本生成测试成功！")
                    return True
                else:
                    print("❌ 响应中没有找到生成的文本")
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON解析失败: {e}")
                print(f"响应内容: {response.text[:500]}")
                return False
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ 请求超时")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ 网络请求失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_story_generation():
    """测试故事生成（模拟连环画创作的文本生成）"""
    
    print("\n\n" + "=" * 60)
    print("📚 测试故事生成（连环画创作场景）")
    print("=" * 60)
    
    # 1. 读取配置文件
    config_path = os.path.join(os.path.dirname(__file__), 'SeedReam4_config.json')
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    comfly_config = config['mirror_sites']['comfly']
    api_url = comfly_config['url'].rstrip('/') + '/chat/completions'
    api_key = comfly_config['api_key']
    
    # 2. 构建故事生成请求
    system_prompt = """你是一个专业的儿童故事创作专家，擅长创作连环画故事。请根据用户的要求创作一个结构化的故事。

故事要求：
- 故事长度：medium（6-10个场景）
- 角色描述：根据故事内容自由创作
- 背景风格：根据故事内容自由创作
- 故事主题：温馨、积极向上

请按照以下JSON格式输出故事结构：
{
    "title": "故事标题",
    "summary": "故事简介",
    "scenes": [
        {
            "scene_number": 1,
            "title": "场景标题",
            "description": "场景描述（用于图像生成）",
            "dialogue": "对话内容（如果有）",
            "narration": "旁白内容"
        }
    ]
}

请确保每个场景的描述都适合图像生成，包含具体的视觉元素。"""
    
    user_prompt = "图1是T8,图2是贞贞，创作一个关于T8和贞贞的温馨爱情故事"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "ComfyUI-Doubao-Seed/Test"
    }
    
    request_data = {
        "model": "doubao-seed-1-6-250615",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.8,
        "top_p": 0.9
    }
    
    print(f"📤 发送故事生成请求...")
    print(f"Prompt: {user_prompt}")
    
    # 3. 发送请求
    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=request_data,
            timeout=120  # 增加到120秒
        )
        
        print(f"📥 响应状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                generated_text = result['choices'][0].get('message', {}).get('content', '')
                
                print("\n" + "=" * 60)
                print("✨ 生成的故事结构:")
                print("=" * 60)
                print(generated_text)
                
                # 尝试解析JSON
                try:
                    # 移除markdown代码块标记
                    story_str = generated_text.strip()
                    if story_str.startswith("```"):
                        lines = story_str.split('\n')
                        if len(lines) > 1:
                            story_str = '\n'.join(lines[1:])
                            if story_str.endswith("```"):
                                story_str = story_str[:-3].strip()
                    
                    # 尝试提取JSON部分
                    import re
                    json_match = re.search(r'\{.*\}', story_str, re.DOTALL)
                    if json_match:
                        story_data = json.loads(json_match.group())
                        
                        print("\n" + "=" * 60)
                        print("✅ 故事结构解析成功:")
                        print("=" * 60)
                        print(f"标题: {story_data.get('title', '')}")
                        print(f"简介: {story_data.get('summary', '')}")
                        print(f"场景数量: {len(story_data.get('scenes', []))}")
                        
                        for i, scene in enumerate(story_data.get('scenes', []), 1):
                            print(f"\n场景 {i}:")
                            print(f"  标题: {scene.get('title', '')}")
                            print(f"  描述: {scene.get('description', '')[:100]}...")
                            print(f"  对话: {scene.get('dialogue', '')[:50]}...")
                            print(f"  旁白: {scene.get('narration', '')[:50]}...")
                        
                        print("\n✅ 故事生成测试成功！")
                        return True
                    else:
                        print("❌ 未找到JSON对象")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"❌ JSON解析失败: {e}")
                    return False
            else:
                print("❌ 响应中没有找到生成的文本")
                return False
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"响应内容: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 发生异常: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 测试基础文本生成
    success1 = test_text_generation()
    
    # 测试故事生成
    success2 = test_story_generation()
    
    print("\n\n" + "=" * 60)
    print("📊 测试总结")
    print("=" * 60)
    print(f"基础文本生成: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"故事生成: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 and success2:
        print("\n🎉 所有测试通过！文本生成API工作正常。")
        print("\n💡 如果连环画创作仍然使用默认故事结构，请检查：")
        print("   1. ComfyUI控制台日志中的错误信息")
        print("   2. 节点参数中的API密钥设置")
        print("   3. 网络连接是否稳定")
    else:
        print("\n❌ 测试失败！请检查：")
        print("   1. API密钥是否正确")
        print("   2. 网络连接是否正常")
        print("   3. API端点是否可访问")

