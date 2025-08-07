#!/usr/bin/env python3
"""
针灸大成集成实体抽取系统
同时调用三个模型进行抽取，对比一致性，支持人工审核和批量处理

模型可靠性排序：豆包 > DeepSeek > 通义千问

功能：
1. 批量调用三个模型抽取器
2. 智能对比和一致性分析
3. 人工审核界面（可累积审核）
4. 批量处理文本文件
5. 结果统计和报告

版本：1.0
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from collections import defaultdict, Counter

class IntegratedExtractor:
    """集成实体抽取器"""
    
    def __init__(self):
        self.model_reliability = {
            'doubao': 3,    # 最可靠
            'deepseek': 2,  # 次之
            'tongyi': 1     # 最后
        }

        self.extractors = {
            'deepseek': 'zhenjiu_extractor_ds.py',
            'doubao': 'zhenjiu_extractor_doubao.py',  # 使用简化版
            'tongyi': 'zhenjiu_extractor_tongyi.py'
        }

        # 关系抽取配置
        self.enable_relation_extraction = True  # 是否启用关系抽取
        self.relation_types = ['TREAT', 'MANIFEST', 'MAIN_TREAT']
        self.relation_extraction_mode = 'after_all_entities'  # 'progressive' 或 'after_all_entities'
        self.processed_docs_count = 0  # 已处理文档计数

        # 调试配置
        self.show_prompts = True  # 是否显示prompt到终端

        self.review_database = self.load_review_database()
        
    def load_review_database(self) -> Dict[str, Any]:
        """加载人工审核数据库"""
        db_file = "review_database.json"
        if os.path.exists(db_file):
            try:
                with open(db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            'reviews': {},  # entity_text -> review_result
            'statistics': {
                'total_reviewed': 0,
                'confirmed_entities': 0,
                'rejected_entities': 0,
                'type_corrections': 0
            },
            'reviewers': {},
            'last_updated': None
        }
    
    def save_review_database(self):
        """保存人工审核数据库"""
        self.review_database['last_updated'] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open("review_database.json", 'w', encoding='utf-8') as f:
            json.dump(self.review_database, f, ensure_ascii=False, indent=2)
    
    def get_text_files(self, directory: str = "test_texts") -> List[Path]:
        """获取所有文本文件"""
        text_dir = Path(directory)
        if not text_dir.exists():
            print(f"❌ 文本目录不存在: {directory}")
            return []
        
        files = list(text_dir.glob("*.txt"))
        print(f"📁 找到 {len(files)} 个文本文件")
        return files
    
    def call_extractor_directly(self, model_name: str, text_content: str, doc_title: str) -> Dict[str, Any]:
        """直接调用抽取器模块"""
        try:
            if model_name == 'deepseek':
                # 导入DeepSeek抽取器
                sys.path.append('.')
                from zhenjiu_extractor_ds import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_entities(text_content, doc_title)
                
            elif model_name == 'tongyi':
                # 导入通义千问抽取器
                from zhenjiu_extractor_tongyi import ZhenjiuEntityExtractor as TongyiExtractor
                extractor = TongyiExtractor()
                return extractor.extract_entities(text_content, doc_title)
                
            elif model_name == 'doubao':
                # 导入豆包抽取器
                from zhenjiu_extractor_doubao import ZhenjiuEntityExtractor as DoubaoExtractor
                extractor = DoubaoExtractor()
                return extractor.extract_entities(text_content, doc_title)
                
            else:
                return {'success': False, 'error': f'未知模型: {model_name}'}
                
        except Exception as e:
            return {'success': False, 'error': f'{model_name} 调用失败: {str(e)}'}
    
    def extract_from_file(self, text_file: Path) -> Dict[str, Any]:
        """从单个文件抽取实体和关系（分阶段）"""
        print(f"\n📄 处理文件: {text_file.name}")

        # 增加处理计数
        self.processed_docs_count += 1

        # 判断是否启用关系抽取（根据模式决定）
        if self.relation_extraction_mode == 'after_all_entities':
            enable_relations = False  # 在这个阶段不抽取关系
            print(f"  📝 第 {self.processed_docs_count} 篇文档，仅抽取实体（关系将在所有实体完成后统一抽取）")
        else:
            # 原来的渐进式模式
            enable_relations = (self.enable_relation_extraction and
                              self.processed_docs_count > 50)
            if enable_relations:
                print(f"  🔗 第 {self.processed_docs_count} 篇文档，启用关系抽取")
            else:
                print(f"  📝 第 {self.processed_docs_count} 篇文档，仅抽取实体")

        # 读取文件内容
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                text_content = f.read().strip()
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return {}

        doc_title = text_file.stem.replace('_', ' ')
        results = {}

        # 依次调用三个模型
        for model_name in ['doubao', 'deepseek', 'tongyi']:  # 按可靠性排序
            print(f"  🔄 运行 {model_name} 模型...")

            if enable_relations:
                # 调用综合抽取方法（实体+关系）
                result = self.call_extractor_with_relations(model_name, text_content, doc_title)
            else:
                # 只调用实体抽取
                result = self.call_extractor_directly(model_name, text_content, doc_title)

            results[model_name] = result

            if result['success']:
                entity_count = len(result.get('entities', []))
                relation_count = len(result.get('relations', []))
                if enable_relations:
                    print(f"    ✅ {model_name}: {entity_count} 个实体, {relation_count} 个关系")
                else:
                    print(f"    ✅ {model_name}: {entity_count} 个实体")
            else:
                print(f"    ❌ {model_name}: {result.get('error', '未知错误')}")

            # 添加延迟避免API限制
            time.sleep(2)

        return results

    def call_extractor_with_relations(self, model_name: str, text_content: str, doc_title: str) -> Dict[str, Any]:
        """调用抽取器进行实体和关系抽取"""
        try:
            if model_name == 'deepseek':
                # 导入DeepSeek抽取器
                sys.path.append('.')
                from zhenjiu_extractor_ds import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_entities_and_relations(text_content, doc_title)

            elif model_name == 'doubao':
                # 导入豆包抽取器
                sys.path.append('.')
                from zhenjiu_extractor_doubao import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_entities_and_relations(text_content, doc_title)

            elif model_name == 'tongyi':
                # 导入通义千问抽取器
                sys.path.append('.')
                from zhenjiu_extractor_tongyi import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_entities_and_relations(text_content, doc_title)

            else:
                return {'success': False, 'error': f'未知模型: {model_name}'}

        except Exception as e:
            return {'success': False, 'error': f'{model_name} 关系抽取失败: {str(e)}'}
    
    def analyze_consistency(self, model_results: Dict[str, Any]) -> Dict[str, Any]:
        """分析实体和关系的一致性"""

        # 收集所有实体
        all_entities = defaultdict(list)  # (text, type) -> [model_names]
        entity_details = {}

        # 收集所有关系
        all_relations = defaultdict(list)  # (head, relation, tail) -> [model_names]
        relation_details = {}

        for model_name, result in model_results.items():
            if result['success']:
                # 处理实体
                for entity in result.get('entities', []):
                    key = (entity['text'], entity['type'])
                    all_entities[key].append(model_name)
                    entity_details[key] = entity

                # 处理关系
                for relation in result.get('relations', []):
                    key = (relation['head'], relation['relation'], relation['tail'])
                    all_relations[key].append(model_name)
                    relation_details[key] = relation
        
        # 按一致性分类
        consensus_data = {
            'unanimous': [],      # 三模型一致
            'majority': [],       # 两模型一致
            'disputed': [],       # 仅一个模型
            'conflicts': []       # 同文本不同类型
        }

        # 关系一致性分析
        relation_consensus = {
            'unanimous': [],      # 三模型一致
            'majority': [],       # 两模型一致
            'disputed': [],       # 仅一个模型
            'conflicts': []       # 关系冲突
        }
        
        # 检查类型冲突
        text_to_types = defaultdict(dict)
        for (text, entity_type), models in all_entities.items():
            text_to_types[text][entity_type] = models
        
        # 识别冲突
        for text, type_models in text_to_types.items():
            if len(type_models) > 1:  # 同一文本有多种类型
                consensus_data['conflicts'].append({
                    'text': text,
                    'type_assignments': {
                        entity_type: models for entity_type, models in type_models.items()
                    }
                })
        
        # 分类实体
        for (text, entity_type), models in all_entities.items():
            support_count = len(models)
            
            entity_info = {
                'text': text,
                'type': entity_type,
                'supporting_models': models,
                'support_count': support_count,
                'reliability_score': self.calculate_reliability_score(models),
                'details': entity_details[(text, entity_type)]
            }
            
            if support_count == 3:
                consensus_data['unanimous'].append(entity_info)
            elif support_count == 2:
                consensus_data['majority'].append(entity_info)
            else:
                consensus_data['disputed'].append(entity_info)

        # 分析关系一致性
        for (head, relation, tail), models in all_relations.items():
            support_count = len(models)

            relation_info = {
                'head': head,
                'relation': relation,
                'tail': tail,
                'supporting_models': models,
                'support_count': support_count,
                'reliability_score': self.calculate_reliability_score(models),
                'details': relation_details[(head, relation, tail)]
            }

            if support_count == 3:
                relation_consensus['unanimous'].append(relation_info)
            elif support_count == 2:
                relation_consensus['majority'].append(relation_info)
            else:
                relation_consensus['disputed'].append(relation_info)

        return {
            'entities': consensus_data,
            'relations': relation_consensus,
            'has_relations': len(all_relations) > 0
        }
    
    def calculate_reliability_score(self, models: List[str]) -> float:
        """计算可靠性分数"""
        total_score = sum(self.model_reliability.get(model, 0) for model in models)
        max_possible = len(models) * 3  # 最高可靠性是3
        return total_score / max_possible if max_possible > 0 else 0
    
    def identify_review_candidates(self, consensus_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别需要人工审核的候选实体"""
        
        candidates = []
        
        # 1. 类型冲突（最高优先级）
        for conflict in consensus_data['conflicts']:
            text = conflict['text']
            
            # 检查是否已经审核过
            if text in self.review_database['reviews']:
                continue
            
            candidates.append({
                'text': text,
                'priority': 'high',
                'reason': 'type_conflict',
                'conflict_info': conflict,
                'question': f'实体"{text}"的正确类型是什么？'
            })
        
        # 2. 仅被一个模型识别的实体（按可靠性排序）
        disputed_by_reliability = sorted(
            consensus_data['disputed'],
            key=lambda x: self.model_reliability.get(x['supporting_models'][0], 0),
            reverse=True
        )
        
        for entity in disputed_by_reliability[:10]:  # 限制数量
            text = entity['text']
            
            if text in self.review_database['reviews']:
                continue
            
            model = entity['supporting_models'][0]
            candidates.append({
                'text': text,
                'priority': 'medium',
                'reason': 'single_model',
                'entity_info': entity,
                'question': f'实体"{text}"（仅被{model}识别）是否有效？'
            })
        
        return candidates
    
    def save_review_tasks(self, candidates: List[Dict[str, Any]],
                         doc_name: str, doc_content: str) -> str:
        """保存审核任务到outputs/review_data/human_review_tasks.json"""

        if not candidates:
            print("✅ 无需人工审核")
            return "outputs/review_data/human_review_tasks.json"

        # 加载现有的审核任务
        review_tasks_file = "outputs/review_data/human_review_tasks.json"
        existing_tasks = []

        if os.path.exists(review_tasks_file):
            try:
                with open(review_tasks_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    existing_tasks = existing_data.get('tasks', [])
            except:
                existing_tasks = []

        # 生成新的审核任务
        new_tasks = []
        task_id_start = len(existing_tasks) + 1

        for i, candidate in enumerate(candidates):
            text = candidate['text']
            context = self.extract_context(doc_content, text)

            # 构建模型意见 - 显示所有三个模型的判断
            models_opinion = {}

            # 先初始化所有模型为"未识别"
            for model_name in ['doubao', 'deepseek', 'tongyi']:
                models_opinion[model_name] = '未识别'

            if candidate['reason'] == 'type_conflict':
                conflict_info = candidate['conflict_info']
                for entity_type, models in conflict_info['type_assignments'].items():
                    for model in models:
                        models_opinion[model] = entity_type
            elif candidate['reason'] == 'single_model':
                entity_info = candidate['entity_info']
                model = entity_info['supporting_models'][0]
                entity_type = entity_info['type']
                models_opinion[model] = entity_type

            task = {
                'id': task_id_start + i,
                'doc_name': doc_name,
                'entity_text': text,
                'priority': candidate['priority'],
                'reason': candidate['reason'],
                'question': candidate['question'],
                'context': {
                    'highlighted': context,
                    'full_sentence': self.extract_sentence(doc_content, text)
                },
                'models_opinion': models_opinion,
                'options': ['病名', '症状', '穴位', '治法', '无效'],
                'human_decision': {
                    'selected_option': '',  # 待填写
                    'notes': '',           # 备注
                    'reviewer': '',        # 审核人
                    'timestamp': ''        # 审核时间
                }
            }
            new_tasks.append(task)

        # 合并任务
        all_tasks = existing_tasks + new_tasks

        # 保存审核任务
        review_data = {
            'instructions': """
🔍 针灸大成实体抽取 - 人工审核任务

请对以下争议实体进行审核：

📋 审核说明：
1. 仔细阅读上下文，理解实体在原文中的含义
2. 参考各模型的判断，但以您的专业知识为准
3. 优先处理"高优先级"任务（类型冲突）

✅ 审核选项：
- 病名：疾病名称（如：肝热病、心热病）
- 症状：症状表现（如：腹痛、头痛、小便先黄）
- 穴位：经络穴位（如：足厥阴、手少阴、百会）
- 治法：治疗方法（如：刺、灸、补、泻）
- 无效：不是有效实体
            """,
            'total_tasks': len(all_tasks),
            'new_tasks_count': len(new_tasks),
            'tasks': all_tasks
        }

        with open(review_tasks_file, 'w', encoding='utf-8') as f:
            json.dump(review_data, f, ensure_ascii=False, indent=2)

        print(f"📝 已添加 {len(new_tasks)} 个审核任务到 {review_tasks_file}")
        print(f"📊 总审核任务数: {len(all_tasks)}")

        return review_tasks_file

    def extract_sentence(self, text: str, entity_text: str) -> str:
        """提取包含实体的完整句子"""
        pos = text.find(entity_text)
        if pos == -1:
            return entity_text

        # 中文句子分隔符
        sentence_endings = ['。', '！', '？', '；', '\n']

        # 向前找句子开始
        start = pos
        while start > 0 and text[start-1] not in sentence_endings:
            start -= 1

        # 向后找句子结束
        end = pos + len(entity_text)
        while end < len(text) and text[end] not in sentence_endings:
            end += 1

        if end < len(text):
            end += 1  # 包含句号

        sentence = text[start:end].strip()
        return sentence
    
    def extract_context(self, text: str, entity_text: str, context_length: int = 80) -> str:
        """提取实体上下文（包括上一句和下一句）"""
        pos = text.find(entity_text)
        if pos == -1:
            return "未找到上下文"

        # 找到实体所在句子的边界
        entity_start = pos
        entity_end = pos + len(entity_text)

        # 向前找句子边界（找到句号、感叹号、问号或文档开头）
        sentence_start = entity_start
        while sentence_start > 0:
            if text[sentence_start - 1] in '。！？\n':
                break
            sentence_start -= 1

        # 向后找句子边界
        sentence_end = entity_end
        while sentence_end < len(text):
            if text[sentence_end] in '。！？\n':
                sentence_end += 1  # 包含标点
                break
            sentence_end += 1

        # 扩展到上一句
        prev_sentence_start = sentence_start
        if sentence_start > 0:
            # 向前找上一句的开始
            temp_pos = sentence_start - 1
            while temp_pos > 0 and text[temp_pos] in '。！？\n ':
                temp_pos -= 1  # 跳过标点和空格

            # 找到上一句的开始
            while temp_pos > 0:
                if text[temp_pos - 1] in '。！？\n':
                    break
                temp_pos -= 1
            prev_sentence_start = temp_pos

        # 扩展到下一句
        next_sentence_end = sentence_end
        if sentence_end < len(text):
            # 向后找下一句的结束
            temp_pos = sentence_end
            while temp_pos < len(text) and text[temp_pos] in ' \n':
                temp_pos += 1  # 跳过空格和换行

            # 找到下一句的结束
            while temp_pos < len(text):
                if text[temp_pos] in '。！？\n':
                    temp_pos += 1  # 包含标点
                    break
                temp_pos += 1
            next_sentence_end = temp_pos

        # 提取扩展的上下文
        extended_context = text[prev_sentence_start:next_sentence_end].strip()

        # 高亮实体
        highlighted = extended_context.replace(entity_text, f"【{entity_text}】")

        return highlighted

    def generate_final_entities(self, consensus_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成最终实体列表（按可靠性排序）"""

        final_entities = []

        # 1. 三模型一致的实体（直接采用，最高置信度）
        for entity in consensus_data['unanimous']:
            final_entities.append({
                'text': entity['text'],
                'type': entity['type'],
                'confidence': 'high',
                'source': 'unanimous',
                'supporting_models': entity['supporting_models'],
                'reliability_score': entity['reliability_score']
            })

        # 2. 两模型一致的实体（按可靠性采用）
        for entity in consensus_data['majority']:
            # 检查是否包含豆包（最可靠）
            models = entity['supporting_models']
            if 'doubao' in models:
                confidence = 'high'
            elif 'deepseek' in models:
                confidence = 'medium'
            else:
                confidence = 'low'

            final_entities.append({
                'text': entity['text'],
                'type': entity['type'],
                'confidence': confidence,
                'source': 'majority',
                'supporting_models': entity['supporting_models'],
                'reliability_score': entity['reliability_score']
            })

        # 3. 单模型实体（仅采用豆包的，或已审核的）
        for entity in consensus_data['disputed']:
            model = entity['supporting_models'][0]
            text = entity['text']

            # 检查人工审核结果
            if text in self.review_database['reviews']:
                review = self.review_database['reviews'][text]
                if review['selected_type'] != '无效':
                    final_entities.append({
                        'text': text,
                        'type': review['selected_type'],
                        'confidence': review['confidence'].lower(),
                        'source': 'human_reviewed',
                        'supporting_models': ['human_review'],
                        'reliability_score': 1.0
                    })
            elif model == 'doubao':  # 仅采用豆包的单模型实体
                final_entities.append({
                    'text': entity['text'],
                    'type': entity['type'],
                    'confidence': 'medium',
                    'source': 'doubao_only',
                    'supporting_models': entity['supporting_models'],
                    'reliability_score': entity['reliability_score']
                })

        # 4. 处理类型冲突（使用人工审核结果或豆包判断）
        for conflict in consensus_data['conflicts']:
            text = conflict['text']

            if text in self.review_database['reviews']:
                review = self.review_database['reviews'][text]
                if review['selected_type'] != '无效':
                    final_entities.append({
                        'text': text,
                        'type': review['selected_type'],
                        'confidence': review['confidence'].lower(),
                        'source': 'conflict_resolved',
                        'supporting_models': ['human_review'],
                        'reliability_score': 1.0
                    })
            else:
                # 使用豆包的判断，如果豆包没有则用DeepSeek
                best_type = None
                best_models = []

                for entity_type, models in conflict['type_assignments'].items():
                    if 'doubao' in models:
                        best_type = entity_type
                        best_models = models
                        break
                    elif 'deepseek' in models and not best_type:
                        best_type = entity_type
                        best_models = models

                if best_type:
                    final_entities.append({
                        'text': text,
                        'type': best_type,
                        'confidence': 'low',
                        'source': 'conflict_auto_resolved',
                        'supporting_models': best_models,
                        'reliability_score': self.calculate_reliability_score(best_models)
                    })

        return final_entities

    def generate_final_relations(self, relation_consensus: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成最终关系列表（按可靠性排序）"""

        final_relations = []

        # 1. 三模型一致的关系（直接采用，最高置信度）
        for relation in relation_consensus.get('unanimous', []):
            final_relations.append({
                'head': relation['head'],
                'relation': relation['relation'],
                'tail': relation['tail'],
                'confidence': 'high',
                'source': 'unanimous_consensus',
                'supporting_models': relation['supporting_models'],
                'reliability_score': relation['reliability_score']
            })

        # 2. 两模型一致的关系（采用，中等置信度）
        for relation in relation_consensus.get('majority', []):
            final_relations.append({
                'head': relation['head'],
                'relation': relation['relation'],
                'tail': relation['tail'],
                'confidence': 'medium',
                'source': 'majority_consensus',
                'supporting_models': relation['supporting_models'],
                'reliability_score': relation['reliability_score']
            })

        # 3. 单模型关系（仅采用豆包的）
        for relation in relation_consensus.get('disputed', []):
            model = relation['supporting_models'][0]

            # 只采用豆包的单模型关系
            if model == 'doubao':
                final_relations.append({
                    'head': relation['head'],
                    'relation': relation['relation'],
                    'tail': relation['tail'],
                    'confidence': 'low',
                    'source': 'doubao_only',
                    'supporting_models': relation['supporting_models'],
                    'reliability_score': relation['reliability_score']
                })

        return final_relations

    def extract_relations_for_all_documents(self, entity_results_dir: str = "outputs/integrated_results") -> Dict[str, Any]:
        """为所有已完成的实体抽取文档统一抽取关系"""

        print("\n" + "="*80)
        print("🔗 开始为所有文档统一抽取关系")
        print("="*80)

        # 查找所有实体结果文件
        import glob
        entity_files = glob.glob(f"{entity_results_dir}/final_entities_*.json")

        if not entity_files:
            print("❌ 未找到实体结果文件")
            return {'success': False, 'error': '未找到实体结果文件'}

        print(f"📁 找到 {len(entity_files)} 个实体结果文件")

        relation_results = {}
        total_relations = 0

        for entity_file in entity_files:
            try:
                # 读取实体结果
                with open(entity_file, 'r', encoding='utf-8') as f:
                    entity_data = json.load(f)

                doc_name = entity_data.get('doc_name', 'unknown')
                entities = entity_data.get('entities', [])

                if not entities:
                    print(f"⚠️ {doc_name}: 无实体数据，跳过")
                    continue

                print(f"\n🔄 处理文档: {doc_name}")
                print(f"   实体数量: {len(entities)}")

                # 读取原文档内容
                doc_content = self.load_document_content(doc_name)
                if not doc_content:
                    print(f"⚠️ {doc_name}: 无法读取原文档，跳过")
                    continue

                # 为这个文档抽取关系
                doc_relations = self.extract_relations_for_document(doc_name, doc_content, entities)

                if doc_relations['success']:
                    relation_count = len(doc_relations['relations'])
                    total_relations += relation_count
                    print(f"   ✅ 抽取到 {relation_count} 个关系")

                    # 保存关系结果
                    self.save_relation_results(doc_name, doc_relations['relations'], entities)

                    relation_results[doc_name] = doc_relations
                else:
                    print(f"   ❌ 关系抽取失败: {doc_relations.get('error', '未知错误')}")

            except Exception as e:
                print(f"❌ 处理文件 {entity_file} 失败: {e}")

        print(f"\n🎉 关系抽取完成！")
        print(f"📊 总计抽取 {total_relations} 个关系")

        return {
            'success': True,
            'total_documents': len(entity_files),
            'total_relations': total_relations,
            'results': relation_results
        }

    def load_document_content(self, doc_name: str) -> str:
        """加载文档原始内容"""
        # 尝试不同的文件名格式
        possible_files = [
            f"test_texts/{doc_name}.txt",
            f"test_texts/{doc_name.replace(' ', '_')}.txt",
            f"test_texts/{doc_name.replace(' ', '')}.txt"
        ]

        for file_path in possible_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except FileNotFoundError:
                continue

        return ""

    def extract_relations_for_document(self, doc_name: str, doc_content: str, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """为单个文档抽取关系"""

        # 转换实体格式
        formatted_entities = []
        for entity in entities:
            formatted_entities.append({
                'text': entity['text'],
                'type': entity['type']
            })

        # 调用三个模型抽取关系
        model_results = {}

        for model_name in ['doubao', 'deepseek', 'tongyi']:
            try:
                print(f"     🔄 {model_name} 模型抽取关系...")

                result = self.call_model_for_relations(model_name, doc_content, formatted_entities, doc_name)
                model_results[model_name] = result

                if result['success']:
                    relation_count = len(result.get('relations', []))
                    print(f"       ✅ {relation_count} 个关系")
                else:
                    print(f"       ❌ 失败: {result.get('error', '未知错误')}")

                # 添加延迟
                time.sleep(1)

            except Exception as e:
                print(f"       ❌ {model_name} 抽取失败: {e}")
                model_results[model_name] = {'success': False, 'error': str(e)}

        # 分析关系一致性
        final_relations = self.analyze_relation_consensus(model_results)

        return {
            'success': True,
            'relations': final_relations,
            'model_results': model_results
        }

    def call_model_for_relations(self, model_name: str, text_content: str, entities: List[Dict[str, Any]], doc_title: str) -> Dict[str, Any]:
        """调用指定模型进行关系抽取"""
        try:
            if model_name == 'deepseek':
                from zhenjiu_extractor_ds import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_relations(text_content, entities, doc_title)

            elif model_name == 'doubao':
                from zhenjiu_extractor_doubao import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_relations(text_content, entities, doc_title)

            elif model_name == 'tongyi':
                from zhenjiu_extractor_tongyi import ZhenjiuEntityExtractor
                extractor = ZhenjiuEntityExtractor()
                return extractor.extract_relations(text_content, entities, doc_title)

            else:
                return {'success': False, 'error': f'未知模型: {model_name}'}

        except Exception as e:
            return {'success': False, 'error': f'{model_name} 关系抽取失败: {str(e)}'}

    def analyze_relation_consensus(self, model_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """分析关系一致性并生成最终关系列表"""

        all_relations = defaultdict(list)  # (head, relation, tail) -> [model_names]
        relation_details = {}

        # 收集所有关系
        for model_name, result in model_results.items():
            if result.get('success'):
                for relation in result.get('relations', []):
                    key = (relation['head'], relation['relation'], relation['tail'])
                    all_relations[key].append(model_name)
                    relation_details[key] = relation

        final_relations = []

        # 按一致性生成最终关系
        for (head, relation, tail), models in all_relations.items():
            support_count = len(models)

            if support_count >= 2:  # 至少两个模型支持
                confidence = 'high' if support_count == 3 else 'medium'
                final_relations.append({
                    'head': head,
                    'relation': relation,
                    'tail': tail,
                    'confidence': confidence,
                    'supporting_models': models,
                    'support_count': support_count
                })
            elif 'doubao' in models:  # 只有豆包支持的关系也采用
                final_relations.append({
                    'head': head,
                    'relation': relation,
                    'tail': tail,
                    'confidence': 'low',
                    'supporting_models': models,
                    'support_count': support_count
                })

        return final_relations

    def save_relation_results(self, doc_name: str, relations: List[Dict[str, Any]], entities: List[Dict[str, Any]]):
        """保存关系抽取结果"""

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 保存关系结果
        relation_result = {
            'doc_name': doc_name,
            'timestamp': timestamp,
            'entities': entities,
            'relations': relations,
            'statistics': {
                'entity_count': len(entities),
                'relation_count': len(relations),
                'relation_types': {
                    rel_type: len([r for r in relations if r['relation'] == rel_type])
                    for rel_type in self.relation_types
                }
            }
        }

        # 保存到文件
        relation_file = f"outputs/integrated_results/relations_{doc_name}_{timestamp}.json"
        with open(relation_file, 'w', encoding='utf-8') as f:
            json.dump(relation_result, f, ensure_ascii=False, indent=2)

        print(f"       💾 关系结果已保存: {relation_file}")

        # 更新原有的实体文件，添加关系信息
        import glob
        entity_files = glob.glob(f"outputs/integrated_results/final_entities_{doc_name}_*.json")
        if entity_files:
            latest_entity_file = max(entity_files)
            try:
                with open(latest_entity_file, 'r', encoding='utf-8') as f:
                    entity_data = json.load(f)

                entity_data['relations'] = relations
                entity_data['relation_statistics'] = relation_result['statistics']

                with open(latest_entity_file, 'w', encoding='utf-8') as f:
                    json.dump(entity_data, f, ensure_ascii=False, indent=2)

                print(f"       🔄 已更新实体文件: {latest_entity_file}")

            except Exception as e:
                print(f"       ⚠️ 更新实体文件失败: {e}")

    def generate_bert_training_data(self, text_file: Path, final_entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成BERT+BiLSTM+CRF训练数据格式"""

        # 读取原文
        with open(text_file, 'r', encoding='utf-8') as f:
            text = f.read().strip()

        # 创建字符级别的标注
        char_labels = ['O'] * len(text)

        # 实体类型映射
        type_mapping = {
            '病名': 'DIS',    # Disease
            '症状': 'SYM',    # Symptom
            '穴位': 'ACU',    # Acupoint
            '治法': 'TRE'     # Treatment
        }

        # 标注实体
        for entity in final_entities:
            entity_text = entity['text']
            entity_type = entity['type']

            if entity_type not in type_mapping:
                continue

            bio_tag = type_mapping[entity_type]

            # 查找实体在文本中的所有位置
            start_pos = 0
            while True:
                pos = text.find(entity_text, start_pos)
                if pos == -1:
                    break

                # 检查是否已经被标注
                if char_labels[pos] == 'O':
                    # BIO标注
                    for i, char in enumerate(entity_text):
                        if i == 0:
                            char_labels[pos + i] = f'B-{bio_tag}'
                        else:
                            char_labels[pos + i] = f'I-{bio_tag}'

                start_pos = pos + 1

        # 生成训练数据格式
        training_data = {
            'doc_name': text_file.stem,
            'text': text,
            'entities': final_entities,
            'char_labels': char_labels,
            'bio_format': self.convert_to_bio_format(text, char_labels),
            'statistics': {
                'total_chars': len(text),
                'total_entities': len(final_entities),
                'entity_types': {
                    '病名': len([e for e in final_entities if e['type'] == '病名']),
                    '症状': len([e for e in final_entities if e['type'] == '症状']),
                    '穴位': len([e for e in final_entities if e['type'] == '穴位']),
                    '治法': len([e for e in final_entities if e['type'] == '治法'])
                }
            }
        }

        return training_data

    def convert_to_bio_format(self, text: str, char_labels: List[str]) -> List[Dict[str, str]]:
        """转换为BIO格式的训练数据"""

        bio_data = []
        for i, char in enumerate(text):
            if char.strip():  # 跳过空白字符
                bio_data.append({
                    'char': char,
                    'label': char_labels[i],
                    'position': i
                })

        return bio_data

    def display_results(self, doc_name: str, consensus_data: Dict[str, Any],
                       final_entities: List[Dict[str, Any]], review_stats: Dict[str, Any],
                       final_relations: List[Dict[str, Any]] = None):
        """显示结果统计"""

        print(f"\n{'='*80}")
        print(f"📊 {doc_name} - 抽取结果统计")
        print(f"{'='*80}")

        # 一致性统计
        print(f"\n🤝 一致性分析:")
        print(f"   ✅ 三模型一致: {len(consensus_data['unanimous'])} 个")
        print(f"   🤝 两模型一致: {len(consensus_data['majority'])} 个")
        print(f"   ❓ 仅一个模型: {len(consensus_data['disputed'])} 个")
        print(f"   ⚠️ 类型冲突: {len(consensus_data['conflicts'])} 个")

        # 人工审核统计
        if review_stats['reviewed'] > 0 or review_stats['skipped'] > 0:
            print(f"\n📝 人工审核:")
            print(f"   ✅ 已审核: {review_stats['reviewed']} 个")
            print(f"   ⏭️ 已跳过: {review_stats['skipped']} 个")

        # 最终实体统计
        print(f"\n🎯 最终实体: {len(final_entities)} 个")

        # 按类型统计
        type_stats = defaultdict(int)
        confidence_stats = defaultdict(int)
        source_stats = defaultdict(int)

        for entity in final_entities:
            type_stats[entity['type']] += 1
            confidence_stats[entity['confidence']] += 1
            source_stats[entity['source']] += 1

        print(f"\n📋 类型分布:")
        for entity_type in ['病名', '症状', '穴位', '治法']:
            count = type_stats.get(entity_type, 0)
            print(f"   {entity_type}: {count} 个")

        print(f"\n🎯 置信度分布:")
        for confidence in ['high', 'medium', 'low']:
            count = confidence_stats.get(confidence, 0)
            percentage = count / len(final_entities) * 100 if final_entities else 0
            print(f"   {confidence}: {count} 个 ({percentage:.1f}%)")

        print(f"\n📊 来源分布:")
        for source, count in source_stats.items():
            percentage = count / len(final_entities) * 100 if final_entities else 0
            print(f"   {source}: {count} 个 ({percentage:.1f}%)")

        # 显示关系统计
        if final_relations:
            print(f"\n🔗 关系抽取结果:")
            print(f"   总关系数: {len(final_relations)}")

            # 关系类型分布
            relation_type_stats = defaultdict(int)
            relation_confidence_stats = defaultdict(int)

            for relation in final_relations:
                relation_type_stats[relation['relation']] += 1
                relation_confidence_stats[relation['confidence']] += 1

            print(f"\n🔗 关系类型分布:")
            for rel_type, count in relation_type_stats.items():
                percentage = count / len(final_relations) * 100
                print(f"   {rel_type}: {count} 个 ({percentage:.1f}%)")

            print(f"\n🎯 关系置信度分布:")
            for confidence in ['high', 'medium', 'low']:
                count = relation_confidence_stats.get(confidence, 0)
                percentage = count / len(final_relations) * 100 if final_relations else 0
                print(f"   {confidence}: {count} 个 ({percentage:.1f}%)")
        else:
            print(f"\n🔗 关系抽取: 未启用（当前为实体抽取阶段）")

    def save_results(self, doc_name: str, model_results: Dict[str, Any],
                    consensus_data: Dict[str, Any], final_entities: List[Dict[str, Any]],
                    review_stats: Dict[str, Any], bert_training_data: Dict[str, Any],
                    final_relations: List[Dict[str, Any]] = None):
        """保存结果"""

        timestamp = time.strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        detailed_result = {
            'doc_name': doc_name,
            'timestamp': timestamp,
            'model_results': model_results,
            'consensus_analysis': consensus_data,
            'final_entities': final_entities,
            'final_relations': final_relations or [],
            'review_statistics': review_stats,
            'model_reliability': self.model_reliability,
            'summary': {
                'total_final_entities': len(final_entities),
                'total_final_relations': len(final_relations) if final_relations else 0,
                'unanimous_entities': len(consensus_data['unanimous']),
                'majority_entities': len(consensus_data['majority']),
                'disputed_entities': len(consensus_data['disputed']),
                'conflicts': len(consensus_data['conflicts']),
                'human_reviewed': review_stats['reviewed'],
                'has_relations': bool(final_relations)
            }
        }

        result_file = f"outputs/integrated_results/integrated_result_{doc_name}_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_result, f, ensure_ascii=False, indent=2)

        print(f"💾 详细结果已保存: {result_file}")

        # 保存简化的最终实体和关系列表
        simple_result = {
            'doc_name': doc_name,
            'timestamp': timestamp,
            'entities': [
                {
                    'text': entity['text'],
                    'type': entity['type'],
                    'confidence': entity['confidence']
                }
                for entity in final_entities
            ],
            'relations': [
                {
                    'head': relation['head'],
                    'relation': relation['relation'],
                    'tail': relation['tail'],
                    'confidence': relation['confidence']
                }
                for relation in (final_relations or [])
            ],
            'statistics': detailed_result['summary']
        }

        simple_file = f"outputs/integrated_results/final_entities_{doc_name}_{timestamp}.json"
        with open(simple_file, 'w', encoding='utf-8') as f:
            json.dump(simple_result, f, ensure_ascii=False, indent=2)

        print(f"💾 最终实体已保存: {simple_file}")

        # 保存BERT训练数据
        bert_file = f"outputs/training_data/bert_training_{doc_name}_{timestamp}.json"
        with open(bert_file, 'w', encoding='utf-8') as f:
            json.dump(bert_training_data, f, ensure_ascii=False, indent=2)

        print(f"🤖 BERT训练数据已保存: {bert_file}")

        return result_file, simple_file, bert_file

    def process_single_file(self, text_file: Path) -> Dict[str, Any]:
        """处理单个文件的完整流程"""

        doc_name = text_file.stem.replace('_', ' ')

        # 1. 三模型抽取
        model_results = self.extract_from_file(text_file)

        if not any(result.get('success', False) for result in model_results.values()):
            print(f"❌ 所有模型抽取失败")
            return {'success': False, 'error': '所有模型抽取失败'}

        # 2. 一致性分析
        analysis_result = self.analyze_consistency(model_results)
        entity_consensus = analysis_result['entities']
        relation_consensus = analysis_result.get('relations', {})
        has_relations = analysis_result.get('has_relations', False)

        # 3. 识别审核候选并保存到outputs/review_data/human_review_tasks.json
        review_candidates = self.identify_review_candidates(entity_consensus)
        review_tasks_file = None
        if review_candidates:
            with open(text_file, 'r', encoding='utf-8') as f:
                doc_content = f.read()
            review_tasks_file = self.save_review_tasks(review_candidates, doc_name, doc_content)

        # 4. 生成最终实体和关系
        final_entities = self.generate_final_entities(entity_consensus)
        final_relations = self.generate_final_relations(relation_consensus) if has_relations else []

        # 5. 生成BERT训练格式数据
        bert_training_data = self.generate_bert_training_data(text_file, final_entities)

        # 6. 显示结果
        self.display_results(doc_name, entity_consensus, final_entities, {'reviewed': 0, 'skipped': 0}, final_relations)

        # 7. 保存结果
        result_files = self.save_results(doc_name, model_results, entity_consensus,
                                       final_entities, {'reviewed': 0, 'skipped': 0}, bert_training_data,
                                       final_relations)

        return {
            'success': True,
            'doc_name': doc_name,
            'final_entities': final_entities,
            'final_relations': final_relations,
            'entity_consensus': entity_consensus,
            'relation_consensus': relation_consensus,
            'bert_training_data': bert_training_data,
            'review_tasks_file': review_tasks_file,
            'result_files': result_files,
            'has_relations': has_relations
        }

    def batch_process(self, max_files: int = None) -> Dict[str, Any]:
        """批量处理文本文件"""

        print("🚀 针灸大成集成实体抽取系统")
        print("="*60)
        print("🎯 功能: 三模型协同抽取 + 智能对比 + 生成审核任务")
        print("🤖 模型: 豆包(最可靠) > DeepSeek > 通义千问")
        print("🔧 输出: BERT训练数据 + 人工审核任务")
        print("="*60)

        # 获取文本文件
        text_files = self.get_text_files()
        if not text_files:
            return {'success': False, 'error': '未找到文本文件'}

        if max_files:
            text_files = text_files[:max_files]

        print(f"\n📋 将处理 {len(text_files)} 个文件")
        print("📝 争议实体将保存到 outputs/review_data/human_review_tasks.json")
        print("🤖 BERT训练数据将自动生成")

        # 处理每个文件
        all_results = []
        total_entities = 0
        total_review_tasks = 0

        for i, text_file in enumerate(text_files, 1):
            print(f"\n{'='*80}")
            print(f"📄 处理文件 {i}/{len(text_files)}: {text_file.name}")
            print(f"{'='*80}")

            try:
                result = self.process_single_file(text_file)

                if result['success']:
                    all_results.append(result)
                    total_entities += len(result['final_entities'])

                    # 统计审核任务
                    if result['review_tasks_file'] and os.path.exists(result['review_tasks_file']):
                        with open(result['review_tasks_file'], 'r', encoding='utf-8') as f:
                            review_data = json.load(f)
                            total_review_tasks = review_data.get('total_tasks', 0)

                    print(f"✅ 处理完成: {len(result['final_entities'])} 个最终实体")
                else:
                    print(f"❌ 处理失败: {result.get('error', '未知错误')}")

            except KeyboardInterrupt:
                print(f"\n⏹️ 用户中断，已处理 {i-1} 个文件")
                break
            except Exception as e:
                print(f"❌ 处理异常: {e}")
                continue

        # 生成总体报告
        print(f"\n🎊 批量处理完成!")
        print(f"📊 总体统计:")
        print(f"   📄 处理文件: {len(all_results)} 个")
        print(f"   📝 最终实体: {total_entities} 个")
        print(f"   📋 审核任务: {total_review_tasks} 个")
        print(f"   🤖 BERT训练数据: {len(all_results)} 个文件")

        print(f"\n🔄 下一步操作:")
        print(f"   1. 运行 python human_review_interface.py 进行人工审核")
        print(f"   2. 使用生成的 outputs/training_data/bert_training_*.json 文件训练BERT模型")

        return {
            'success': True,
            'processed_files': len(all_results),
            'total_entities': total_entities,
            'total_review_tasks': total_review_tasks,
            'results': all_results
        }


def main():
    """主函数"""

    print("针灸大成集成实体抽取系统")
    print("="*50)

    try:
        extractor = IntegratedExtractor()

        # 询问是否显示prompt
        print("\n调试选项:")
        show_prompt = input("是否显示模型Prompt到终端？(y/N): ").strip().lower()

        # 设置全局配置
        try:
            from config import set_show_prompts
            set_show_prompts(show_prompt == 'y')

            if show_prompt == 'y':
                print("✅ 已启用Prompt显示")
            else:
                print("❌ 已禁用Prompt显示")
        except ImportError:
            print("⚠️ 配置文件不存在，使用默认设置")

        # 询问处理模式
        print("\n选择处理模式:")
        print("1. 单文件处理")
        print("2. 批量处理")
        print("3. 🔗 为已完成的实体抽取关系")

        choice = input("请选择 (1-3): ").strip()

        if choice == '1':
            # 单文件处理
            text_files = extractor.get_text_files()
            if not text_files:
                return

            print(f"\n可用文件:")
            for i, file in enumerate(text_files[:10], 1):
                print(f"  {i}. {file.name}")

            file_choice = input(f"选择文件 (1-{min(10, len(text_files))}): ").strip()
            try:
                file_index = int(file_choice) - 1
                if 0 <= file_index < len(text_files):
                    selected_file = text_files[file_index]
                    extractor.process_single_file(selected_file)
                else:
                    print("无效选择")
            except ValueError:
                print("请输入有效数字")

        elif choice == '2':
            # 批量处理
            max_files = input("最大处理文件数 (回车=全部): ").strip()
            max_files = int(max_files) if max_files.isdigit() else None

            extractor.batch_process(max_files=max_files)

        elif choice == '3':
            # 关系抽取
            print("\n🔗 开始为所有已完成的实体抽取关系...")
            print("💡 这将基于已保存的实体结果文件进行关系抽取")

            confirm = input("确认开始？(y/N): ").strip().lower()
            if confirm == 'y':
                result = extractor.extract_relations_for_all_documents()

                if result['success']:
                    print(f"\n🎉 关系抽取完成！")
                    print(f"📊 处理文档数: {result['total_documents']}")
                    print(f"🔗 总关系数: {result['total_relations']}")
                else:
                    print(f"\n❌ 关系抽取失败: {result.get('error', '未知错误')}")
            else:
                print("已取消")

        else:
            print("无效选择")

    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
