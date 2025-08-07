#!/usr/bin/env python3
"""
全局配置文件

用于控制系统的各种行为，包括prompt显示等

版本：1.0
"""

# 调试配置
SHOW_PROMPTS = True  # 是否在终端显示模型prompt

# 关系抽取配置
ENABLE_RELATION_EXTRACTION = True  # 是否启用关系抽取
RELATION_EXTRACTION_MODE = 'after_all_entities'  # 'progressive' 或 'after_all_entities'

# 模型可靠性配置
MODEL_RELIABILITY = {
    'doubao': 3,    # 最可靠
    'deepseek': 2,  # 次之
    'tongyi': 1     # 最后
}

# 支持的关系类型
RELATION_TYPES = ['TREAT', 'MANIFEST', 'MAIN_TREAT']

# 实体类型
ENTITY_TYPES = ['病名', '症状', '穴位', '治法']

def set_show_prompts(show: bool):
    """设置是否显示prompt"""
    global SHOW_PROMPTS
    SHOW_PROMPTS = show

def get_show_prompts() -> bool:
    """获取是否显示prompt的设置"""
    return SHOW_PROMPTS
