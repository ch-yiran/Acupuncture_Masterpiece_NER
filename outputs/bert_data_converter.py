#!/usr/bin/env python3
"""
BERT训练数据转换工具

功能：
1. 合并多个文档的训练数据
2. 生成标准的BIO标注格式
3. 创建训练/验证/测试数据集
4. 输出适合BERT模型的格式

版本：1.0
"""

import json
import os
import random
from pathlib import Path
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter

class BERTDataConverter:
    def __init__(self):
        self.entity_types = ['病名', '症状', '穴位', '治法']
        self.bio_tags = ['O'] + [f'B-{t}' for t in self.entity_types] + [f'I-{t}' for t in self.entity_types]
        
    def load_training_data(self, data_dir: str = "outputs/training_data") -> List[Dict[str, Any]]:
        """加载所有训练数据文件"""
        training_files = []
        data_path = Path(data_dir)
        
        if not data_path.exists():
            print(f"❌ 训练数据目录不存在: {data_dir}")
            return []
        
        # 查找所有bert_training_*.json文件
        for file_path in data_path.glob("bert_training_*.json"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    training_files.append(data)
                    print(f"✅ 加载训练数据: {file_path.name}")
            except Exception as e:
                print(f"❌ 加载失败 {file_path.name}: {e}")
        
        return training_files
    
    def convert_to_bio_format(self, training_data: List[Dict[str, Any]]) -> List[Tuple[List[str], List[str]]]:
        """转换为BIO格式"""
        bio_data = []
        
        for doc_data in training_data:
            doc_name = doc_data.get('doc_name', 'unknown')
            print(f"🔄 处理文档: {doc_name}")
            
            sentences = doc_data.get('sentences', [])
            for sentence_data in sentences:
                text = sentence_data.get('text', '')
                entities = sentence_data.get('entities', [])
                
                if not text.strip():
                    continue
                
                # 初始化标签
                chars = list(text)
                labels = ['O'] * len(chars)
                
                # 标注实体
                for entity in entities:
                    entity_text = entity.get('text', '')
                    entity_type = entity.get('type', '')
                    
                    if entity_type not in self.entity_types:
                        continue
                    
                    # 查找实体在文本中的位置
                    start_pos = text.find(entity_text)
                    if start_pos != -1:
                        end_pos = start_pos + len(entity_text)
                        
                        # BIO标注
                        for i in range(start_pos, end_pos):
                            if i == start_pos:
                                labels[i] = f'B-{entity_type}'
                            else:
                                labels[i] = f'I-{entity_type}'
                
                bio_data.append((chars, labels))
        
        return bio_data
    
    def split_dataset(self, bio_data: List[Tuple[List[str], List[str]]], 
                     train_ratio: float = 0.7, val_ratio: float = 0.15) -> Tuple[List, List, List]:
        """划分数据集"""
        random.shuffle(bio_data)
        
        total_size = len(bio_data)
        train_size = int(total_size * train_ratio)
        val_size = int(total_size * val_ratio)
        
        train_data = bio_data[:train_size]
        val_data = bio_data[train_size:train_size + val_size]
        test_data = bio_data[train_size + val_size:]
        
        print(f"📊 数据集划分:")
        print(f"   训练集: {len(train_data)} 个句子")
        print(f"   验证集: {len(val_data)} 个句子")
        print(f"   测试集: {len(test_data)} 个句子")
        
        return train_data, val_data, test_data
    
    def save_bio_file(self, data: List[Tuple[List[str], List[str]]], file_path: str):
        """保存BIO格式文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for chars, labels in data:
                for char, label in zip(chars, labels):
                    f.write(f"{char}\t{label}\n")
                f.write("\n")  # 句子间空行
    
    def generate_config(self, output_dir: str, stats: Dict[str, Any]):
        """生成配置文件"""
        config = {
            "model_type": "bert-bilstm-crf",
            "entity_types": self.entity_types,
            "bio_tags": self.bio_tags,
            "max_seq_length": stats.get('max_length', 512),
            "train_file": "train.txt",
            "val_file": "val.txt", 
            "test_file": "test.txt",
            "dataset_stats": stats
        }
        
        config_path = os.path.join(output_dir, "config.json")
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 配置文件已保存: {config_path}")
    
    def generate_readme(self, output_dir: str, stats: Dict[str, Any]):
        """生成README文档"""
        readme_content = f"""# BERT训练数据包

## 📊 数据集信息
- 总文档数: {stats.get('total_docs', 0)}
- 训练集: {stats.get('train_sentences', 0)} 个句子
- 验证集: {stats.get('val_sentences', 0)} 个句子  
- 测试集: {stats.get('test_sentences', 0)} 个句子
- 最大序列长度: {stats.get('max_length', 0)}

## 🏷️ 实体类型
{chr(10).join([f"- {entity_type}: {stats.get('entity_counts', {}).get(entity_type, 0)} 个实体" for entity_type in self.entity_types])}

## 📁 文件说明
- `train.txt`: 训练集（BIO格式）
- `val.txt`: 验证集（BIO格式）
- `test.txt`: 测试集（BIO格式）
- `config.json`: 模型配置文件
- `README.md`: 本说明文档

## 🔧 使用方法
1. 使用BERT作为编码器
2. 添加BiLSTM层进行序列建模
3. 使用CRF层进行序列标注
4. 支持的实体类型: {', '.join(self.entity_types)}

## 📈 数据质量
- 数据来源: 多模型协同抽取 + 人工审核
- 标注格式: BIO标准格式
- 质量保证: 专家审核确认
"""
        
        readme_path = os.path.join(output_dir, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        print(f"✅ 说明文档已保存: {readme_path}")
    
    def calculate_stats(self, train_data: List, val_data: List, test_data: List, 
                       training_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算数据统计信息"""
        entity_counts = defaultdict(int)
        max_length = 0
        
        # 统计实体数量和最大长度
        for doc_data in training_data:
            for sentence_data in doc_data.get('sentences', []):
                text = sentence_data.get('text', '')
                max_length = max(max_length, len(text))
                
                for entity in sentence_data.get('entities', []):
                    entity_type = entity.get('type', '')
                    if entity_type in self.entity_types:
                        entity_counts[entity_type] += 1
        
        return {
            'total_docs': len(training_data),
            'train_sentences': len(train_data),
            'val_sentences': len(val_data),
            'test_sentences': len(test_data),
            'max_length': max_length,
            'entity_counts': dict(entity_counts)
        }
    
    def convert(self, output_dir: str = "outputs/training_data/bert_training_package"):
        """主转换函数"""
        print("🚀 开始BERT训练数据转换...")
        
        # 加载训练数据
        training_data = self.load_training_data()
        if not training_data:
            print("❌ 没有找到训练数据文件")
            return
        
        # 转换为BIO格式
        bio_data = self.convert_to_bio_format(training_data)
        if not bio_data:
            print("❌ 转换BIO格式失败")
            return
        
        # 划分数据集
        train_data, val_data, test_data = self.split_dataset(bio_data)
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存数据文件
        self.save_bio_file(train_data, os.path.join(output_dir, "train.txt"))
        self.save_bio_file(val_data, os.path.join(output_dir, "val.txt"))
        self.save_bio_file(test_data, os.path.join(output_dir, "test.txt"))
        
        # 计算统计信息
        stats = self.calculate_stats(train_data, val_data, test_data, training_data)
        
        # 生成配置和文档
        self.generate_config(output_dir, stats)
        self.generate_readme(output_dir, stats)
        
        print(f"\n✅ BERT训练数据转换完成！")
        print(f"📁 输出目录: {output_dir}")
        print(f"📊 总计: {len(bio_data)} 个训练样本")

def main():
    """主函数"""
    converter = BERTDataConverter()
    converter.convert()

if __name__ == "__main__":
    main()
