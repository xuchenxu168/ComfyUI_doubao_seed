# Doubao-Seed Plugin for ComfyUI
# 专注于Doubao图像和视频生成功能
# 作者: Ken-Chen
# 版本: 2.0.0

import importlib

# 合并所有节点的映射
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"

# Delay module import to avoid startup import errors
def load_modules():
    global NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

    # Import Doubao-Seed module
    try:
        # Try relative import
        try:
            from . import doubao_seed
        except (ImportError, ValueError):
            # If relative import fails, try absolute import
            doubao_seed = importlib.import_module('doubao_seed')

        if hasattr(doubao_seed, 'NODE_CLASS_MAPPINGS'):
            NODE_CLASS_MAPPINGS.update(doubao_seed.NODE_CLASS_MAPPINGS)
        if hasattr(doubao_seed, 'NODE_DISPLAY_NAME_MAPPINGS'):
            NODE_DISPLAY_NAME_MAPPINGS.update(doubao_seed.NODE_DISPLAY_NAME_MAPPINGS)
        print("[Doubao-Seed] Module loaded successfully")
    except Exception as e:
        print(f"[Doubao-Seed] Module loading failed: {e}")

# Load modules immediately
load_modules()

print("[Doubao-Seed] Plugin loading completed!")
print(f"[Doubao-Seed] Registered {len(NODE_CLASS_MAPPINGS)} nodes")
print(f"[Doubao-Seed] Node list: {list(NODE_CLASS_MAPPINGS.keys())}")
