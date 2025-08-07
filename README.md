# 🎯 针灸大成智能实体关系抽取系统

## 🚀 快速开始

### 环境要求
```bash
pip install requests tkinter dashscope openai
```

### 完整使用流程
```bash
# 1. 实体抽取阶段
python integrated_extractor.py
# 选择: 是否显示模型Prompt到终端？(y/N): y
# 选择: 请选择 (1-3): 2
# 等待所有文档处理完成...

# 2. 关系抽取阶段  
python integrated_extractor.py
# 选择: 是否显示模型Prompt到终端？(y/N): n
# 选择: 请选择 (1-3): 3
# 确认开始？(y/N): y

# 3. 可选：人工审核
python human_review_interface.py

# 4. 可选：生成训练数据
python outputs/bert_data_converter.py
```

### 输出文件说明
- `integrated_result_*.json`：完整的抽取结果
- `final_entities_*.json`：最终实体列表
- `relations_*.json`：关系抽取结果
- `human_review_tasks.json`：人工审核任务
- `training_data/`：BERT训练数据

## 🔧 配置说明

### API配置
确保在对应的抽取器文件中配置了正确的API密钥：
- `zhenjiu_extractor_doubao.py`：豆包API密钥
- `zhenjiu_extractor_ds.py`：DeepSeek API密钥  
- `zhenjiu_extractor_tongyi.py`：通义千问API密钥


### 🔄 两阶段工作流程

#### 阶段一：实体抽取
```bash
python integrated_extractor.py
```
1. 选择 `2. 批量处理`
2. 完成所有文档的实体抽取
3. 生成完整的实体库

#### 阶段二：关系抽取（未完善）
```bash
python integrated_extractor.py
```
1. 选择 `3. 🔗 为已完成的实体抽取关系`
2. 基于完整实体库进行关系抽取
3. 生成实体-关系知识图谱

#### 可选：人工审核
```bash
python human_review_interface.py
```
- 命令行界面，快速审核
- 支持实体类型修正
- 提高最终数据质量

#### 未完善：生成训练数据
```bash
python outputs/bert_data_converter.py
```
- 自动生成BIO格式标注文件
- 划分训练/验证/测试集
- 输出标准训练数据包

## 📁 项目结构

```
📦 针灸大成实体关系抽取系统
├── 🚀 核心程序
│   ├── integrated_extractor.py          # 主程序：多模型协同抽取
│   ├── human_review_interface.py        # 命令行审核界面
│   ├── zhenjiu_extractor_doubao.py      # 豆包模型抽取器
│   ├── zhenjiu_extractor_ds.py          # DeepSeek模型抽取器
│   ├── zhenjiu_extractor_tongyi.py      # 通义千问模型抽取器
│   └── config.py                        # 全局配置文件
│
├── 📚 数据文件
│   ├── test_texts/                       # 针灸经典文档（20个）
│   └── outputs/                          # 输出结果目录
│       ├── integrated_results/           # 集成分析结果
│       │   ├── integrated_result_*.json  # 完整抽取结果
│       │   ├── final_entities_*.json     # 最终实体结果
│       │   └── relations_*.json          # 关系抽取结果
│       ├── review_data/                  # 人工审核数据
│       ├── training_data/                # BERT训练数据
│       └── bert_data_converter.py        # 训练数据转换器
│
├── 📖 文档
│   ├── README.md                         # 项目说明
│   └── RELATION_EXTRACTION_GUIDE.md     # 关系抽取指南
│
└── 🧪 测试文件
    └── test_*.py                         # 各种测试脚本
```


## 🎮 操作指南

### 主程序选项
```bash
python integrated_extractor.py
```
- **调试选项**：是否显示模型Prompt到终端？(y/N)
- **处理模式**：
  - `1. 单文件处理`：测试单个文档
  - `2. 批量处理`：处理所有文档（实体抽取阶段）
  - `3. 🔗 为已完成的实体抽取关系`：关系抽取阶段

### 命令行审核界面
```bash
python human_review_interface.py
```
- **1-4**：选择实体类型（病名/症状/穴位/治法）
- **5**：标记为无效
- **s**：跳过当前任务
- **q**：保存并退出

### 配置文件 (config.py)
```python
SHOW_PROMPTS = True  # 是否显示prompt
ENABLE_RELATION_EXTRACTION = True  # 是否启用关系抽取
RELATION_EXTRACTION_MODE = 'after_all_entities'  # 两阶段模式
```

### 模型可靠性
系统默认的模型可靠性排序：
1. **豆包**：最高可靠性，作为主要参考
2. **DeepSeek**：中等可靠性，提供验证
3. **通义千问**：基础可靠性，扩大覆盖面
