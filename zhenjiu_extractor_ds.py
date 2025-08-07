#!/usr/bin/env python3
"""
针灸大成实体抽取器 - 简化版本
专注于探索大模型实体抽取效果，无备用方法

使用方法：
1. 安装依赖：pip install requests
2. 访问deepseek官网，注册账号，获取api key
3. 运行程序：python zhenjiu_extractor.py

版本：4.0 (简化版) - DeepSeek版本
"""

import os
import json
import re
import time
import sys
import requests
from pathlib import Path
from typing import List, Dict, Any

# 内置API密钥配置
DEEPSEEK_API_KEY = "sk-4b6506b9178d43fbb1319ab602d2c2da"  # 请替换为您的DeepSeek API密钥

# 检查Python版本
if sys.version_info < (3, 6):
    print("错误：需要Python 3.6或更高版本")
    sys.exit(1)

# 检查并安装依赖
try:
    import requests
except ImportError:
    print("错误：缺少依赖包，请运行以下命令安装：")
    print("   pip install requests")
    print("   或者：pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple/")
    sys.exit(1)


class ZhenjiuDocumentSelector:
    """《针灸大成》文档选择器"""
    
    def __init__(self, texts_dir="test_texts"):
        self.texts_dir = Path(texts_dir)
        self.documents = self.load_documents()
    
    def load_documents(self):
        """加载所有文档"""
        if not self.texts_dir.exists():
            print(f"错误：文档目录不存在: {self.texts_dir}")
            return []

        documents = []
        for file_path in sorted(self.texts_dir.glob("*.txt")):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                if content and len(content) > 10:  # 过滤太短的文件
                    documents.append({
                        'id': len(documents) + 1,
                        'filename': file_path.name,
                        'title': self.clean_title(file_path.stem),
                        'content': content,
                        'length': len(content),
                        'preview': content[:100] + "..." if len(content) > 100 else content
                    })
            except Exception as e:
                print(f"警告：读取文件失败 {file_path}: {e}")

        return documents
    
    def clean_title(self, filename):
        """清理标题"""
        # 移除编号前缀
        title = re.sub(r'^\d+_', '', filename)
        title = title.replace('_', ' ')
        return title
    
    def display_documents(self):
        """显示文档列表"""
        if not self.documents:
            print("错误：没有找到可用的文档")
            return

        print(f"\n针灸大成精选文档列表 (共{len(self.documents)}个)")
        print("=" * 60)
        
        # 按类型分组显示
        categories = {
            "刺法专论": [],
            "歌诀赋文": [],
            "穴位主治": [],
            "理论基础": []
        }
        
        for doc in self.documents:
            category = self.get_category(doc['title'])
            categories[category].append(doc)
        
        for category, docs in categories.items():
            if docs:
                print(f"\n{category} ({len(docs)}个文档)")
                print("-" * 40)
                for doc in docs:
                    print(f"  {doc['id']:2d}. {doc['title']:<25} ({doc['length']:4d}字符)")
                    print(f"       预览: {doc['preview'][:60]}...")
    
    def get_category(self, title):
        """获取文档类别"""
        if any(x in title for x in ['刺热论', '刺疟论', '刺咳论', '刺腰痛论', '缪刺论', '奇病论', '调经论', '骨空论']):
            return "刺法专论"
        elif any(x in title for x in ['百症赋', '玉龙赋', '标幽赋', '席弘赋', '金针赋', '通玄指要赋', '灵光赋', '兰江赋', '流注指微赋']):
            return "歌诀赋文"
        elif any(x in title for x in ['经穴主治', '手太阴', '手少阴', '足阳明']):
            return "穴位主治"
        else:
            return "理论基础"
    
    def select_document(self):
        """选择文档"""
        while True:
            try:
                choice = input(f"\n请选择文档编号 (1-{len(self.documents)}) 或输入 'q' 退出: ").strip()
                
                if choice.lower() == 'q':
                    return None
                
                doc_id = int(choice)
                if 1 <= doc_id <= len(self.documents):
                    selected_doc = self.documents[doc_id - 1]
                    print(f"\n已选择: {selected_doc['title']}")
                    print(f"   文件: {selected_doc['filename']}")
                    print(f"   长度: {selected_doc['length']} 字符")
                    return selected_doc
                else:
                    print(f"错误：请输入 1-{len(self.documents)} 之间的数字")

            except ValueError:
                print("错误：请输入有效的数字")
            except KeyboardInterrupt:
                print("\n程序已退出")
                return None


class ZhenjiuEntityExtractor:
    """《针灸大成》实体抽取器 - 简化版"""

    def __init__(self, api_key: str = None):
        """初始化抽取器"""
        # 优先使用传入的API密钥，然后使用内置密钥，最后尝试环境变量
        self.api_key = api_key or DEEPSEEK_API_KEY or os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError(
                "API密钥未配置！请检查程序内置密钥或设置环境变量 DEEPSEEK_API_KEY"
            )

        # 设置请求头
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        print("DeepSeek模型初始化成功")

        # 关系抽取配置
        self.enable_relation_extraction = True
        self.relation_types = {
            'TREAT': '治疗关系：治法治疗病名/症状',
            'MANIFEST': '表现关系：病名表现为症状',
            'MAIN_TREAT': '主治关系：穴位主治病名/症状'
        }
    
    def build_optimized_prompt(self, text: str) -> str:
        """构建优化的提示词"""
        
        prompt = f"""你是《针灸大成》专家。请从古文中抽取四类实体，要求全面且准确。请以JSON格式输出结果。

【实体类型详细定义】
1. 病名：疾病名称
   - 格式：X热病、X病、X症、X证等
   - 示例：肝热病、心热病、脾热病、肺热病、肾热病、疟疾、痹症

2. 症状：症状表现（包括复合症状）
   - 单一症状：腹痛、头痛、身热、腰痛、喘咳、汗出
   - 复合症状：小便先黄、胁满痛、手足躁、卒心痛、恶风寒、舌上黄
   - 状态描述：烦闷、善呕、面赤、无汗、头重、颊痛、烦心、颜青、欲呕

3. 穴位：经络穴位
   - 格式：足/手+经络名、具体穴位名
   - 示例：足厥阴、手少阴、足太阴、手太阴、少阳、太阳、阳明、风府、百会

4. 治法：治疗方法
   - 示例：刺、出血、补、泻、灸、针刺、平刺、艾灸

【古文原文】
{text}

【抽取要求】
- 仔细阅读每个句子，不要遗漏任何症状
- 复合词汇要完整抽取（如"小便先黄"不要拆分）
- 每种病名对应的所有症状都要抽取
- 所有穴位和治法都要识别

【输出要求】
必须输出标准JSON格式，结构如下：
{{
    "entities": [
        {{"text": "肝热病", "type": "病名", "start_pos": 0, "end_pos": 3}},
        {{"text": "腹痛", "type": "症状", "start_pos": 10, "end_pos": 12}}
    ]
}}"""

        return prompt
    
    def call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        try:
            # DeepSeek API端点 - 使用完整的chat/completions路径
            url = "https://api.deepseek.com/v1/chat/completions"
            data = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4000,
                "temperature": 0.1,
                "top_p": 0.8,
                "response_format": {
                    "type": "json_object"
                }
            }

            response = requests.post(url, headers=self.headers, json=data)
            response.raise_for_status() # 检查HTTP状态码

            return response.json()['choices'][0]['message']['content']

        except requests.exceptions.RequestException as e:
            print(f"API请求错误详情: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"响应状态码: {e.response.status_code}")
                print(f"响应内容: {e.response.text}")
            raise Exception(f"DeepSeek API调用失败: {str(e)}")
        except Exception as e:
            raise Exception(f"DeepSeek API调用失败: {str(e)}")
    
    def parse_response(self, response: str, original_text: str) -> List[Dict[str, Any]]:
        """解析模型响应 - 纯大模型方法，API失败直接报错"""
        entities = []
        
        try:
            # 清理响应
            cleaned = response.strip()
            
            # 移除markdown标记
            if '```json' in cleaned:
                cleaned = cleaned.split('```json')[1].split('```')[0]
            elif '```' in cleaned:
                parts = cleaned.split('```')
                for part in parts:
                    if '{' in part and '}' in part:
                        cleaned = part
                        break
            
            cleaned = cleaned.strip()
            
            # 修复常见JSON问题
            cleaned = re.sub(r',\s*}', '}', cleaned)
            cleaned = re.sub(r',\s*]', ']', cleaned)
            
            # 如果JSON太长，截取完整部分
            if len(cleaned) > 8000:
                # 寻找最后一个完整的实体
                last_complete = cleaned.rfind('}, {')
                if last_complete > 0:
                    # 找到最后一个完整实体的结束位置
                    next_brace = cleaned.find('}', last_complete + 4)
                    if next_brace > 0:
                        cleaned = cleaned[:next_brace+1] + ']}'
                    else:
                        cleaned = cleaned[:last_complete] + '}]}'
                else:
                    # 如果找不到完整实体，尝试找到最后的}}
                    last_complete = cleaned.rfind('}}')
                    if last_complete > 0:
                        cleaned = cleaned[:last_complete+2] + ']}'
            
            # 解析JSON
            try:
                data = json.loads(cleaned)
                raw_entities = data.get('entities', [])
            except json.JSONDecodeError as e:
                print(f"JSON解析失败，尝试修复: {str(e)}")
                # 尝试修复截断的JSON
                if 'Unterminated string' in str(e):
                    # 找到最后一个完整的实体
                    pattern = r'\{"text":\s*"[^"]*",\s*"type":\s*"[^"]*"[^}]*\}'
                    matches = list(re.finditer(pattern, cleaned))
                    if matches:
                        last_match = matches[-1]
                        # 构建修复的JSON
                        fixed_json = '{"entities": [' + cleaned[cleaned.find('{"text"'):last_match.end()] + ']}'
                        try:
                            data = json.loads(fixed_json)
                            raw_entities = data.get('entities', [])
                            print(f"JSON修复成功，提取到 {len(raw_entities)} 个实体")
                        except:
                            print("JSON修复失败，返回空列表")
                            raw_entities = []
                    else:
                        raw_entities = []
                else:
                    raise
            
            # 验证和清理实体
            for entity in raw_entities:
                if self.validate_entity(entity, original_text):
                    # 移除置信度字段
                    clean_entity = {
                        'text': entity['text'],
                        'type': entity['type'],
                        'start_pos': entity.get('start_pos', -1),
                        'end_pos': entity.get('end_pos', -1)
                    }
                    entities.append(clean_entity)
            
            return entities
            
        except json.JSONDecodeError as e:
            print(f"错误：JSON解析失败: {e}")
            print(f"原始响应: {response[:200]}...")
            return []
        except Exception as e:
            print(f"错误：响应解析失败: {e}")
            return []
    
    def validate_entity(self, entity: Dict[str, Any], original_text: str) -> bool:
        """验证实体"""
        required_fields = ['text', 'type']
        
        for field in required_fields:
            if field not in entity:
                return False
        
        text = entity['text']
        if not text or len(text) < 1:
            return False
        
        # 检查文本是否在原文中
        if text not in original_text:
            return False
        
        return True
    
    def extract_entities(self, text: str, doc_title: str = "") -> Dict[str, Any]:
        """抽取实体主函数"""
        print(f"开始分析文档: {doc_title}")
        print(f"   长度: {len(text)} 字符")
        
        # 构建提示词
        prompt = self.build_optimized_prompt(text)

        # 输出prompt到终端（如果启用）
        try:
            from config import get_show_prompts
            if get_show_prompts():
                print(f"\n{'='*60}")
                print(f"🤖 DeepSeek模型 - 实体抽取Prompt")
                print(f"{'='*60}")
                print(prompt)
                print(f"{'='*60}\n")
        except ImportError:
            pass  # 如果没有config文件，默认不显示

        # 调用API
        start_time = time.time()
        try:
            response = self.call_deepseek_api(prompt)
            processing_time = time.time() - start_time
            
            print(f"模型响应时间: {processing_time:.2f}秒")

            # 解析实体
            entities = self.parse_response(response, text)

            return {
                'success': True,
                'entities': entities,
                'processing_time': processing_time,
                'text_length': len(text),
                'entity_count': len(entities),
                'doc_title': doc_title,
                'raw_response': response
            }

        except Exception as e:
            print(f"错误：抽取失败: {e}")
            return {
                'success': False,
                'entities': [],
                'processing_time': time.time() - start_time,
                'error': str(e),
                'doc_title': doc_title
            }

    def extract_relations(self, text: str, entities: List[Dict[str, Any]], doc_title: str = "") -> Dict[str, Any]:
        """基于已抽取的实体，抽取关系"""
        if not entities or not self.enable_relation_extraction:
            return {
                'success': True,
                'relations': [],
                'processing_time': 0,
                'doc_title': doc_title
            }

        print(f"开始抽取关系: {doc_title}")
        print(f"   基于 {len(entities)} 个实体")

        # 构建关系抽取提示词
        prompt = self.build_relation_prompt(text, entities)

        # 输出关系抽取prompt到终端（如果启用）
        try:
            from config import get_show_prompts
            if get_show_prompts():
                print(f"\n{'='*60}")
                print(f"🔗 DeepSeek模型 - 关系抽取Prompt")
                print(f"{'='*60}")
                print(prompt)
                print(f"{'='*60}\n")
        except ImportError:
            pass  # 如果没有config文件，默认不显示

        # 调用API
        start_time = time.time()
        try:
            response = self.call_deepseek_api(prompt)
            processing_time = time.time() - start_time

            print(f"关系抽取响应时间: {processing_time:.2f}秒")

            # 解析关系
            relations = self.parse_relation_response(response, entities)

            return {
                'success': True,
                'relations': relations,
                'processing_time': processing_time,
                'relation_count': len(relations),
                'doc_title': doc_title,
                'raw_response': response
            }

        except Exception as e:
            print(f"错误：关系抽取失败: {e}")
            return {
                'success': False,
                'relations': [],
                'processing_time': time.time() - start_time,
                'error': str(e),
                'doc_title': doc_title
            }

    def build_relation_prompt(self, text: str, entities: List[Dict[str, Any]]) -> str:
        """构建关系抽取提示词"""

        # 格式化实体信息
        entity_info = []
        for i, entity in enumerate(entities):
            entity_info.append(f"{i+1}. {entity['text']} ({entity['type']})")

        entities_str = "\n".join(entity_info)

        prompt = f"""你是中医文献分析专家。请基于已识别的实体，抽取它们之间的关系。

文本：{text}

已识别实体：
{entities_str}

请识别以下类型的关系：
1. TREAT（治疗）：治法治疗病名/症状
2. MANIFEST（表现）：病名表现为症状
3. MAIN_TREAT（主治）：穴位主治病名/症状

要求：
- 只抽取明确的关系，不要推测
- 关系必须在文本中有明确体现
- 实体必须来自上述已识别实体列表

输出JSON格式：
{{
  "relations": [
    {{
      "head": "实体1文本",
      "head_type": "实体1类型",
      "relation": "关系类型",
      "tail": "实体2文本",
      "tail_type": "实体2类型",
      "confidence": 0.9
    }}
  ]
}}"""

        return prompt

    def parse_relation_response(self, response: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """解析关系抽取响应"""
        relations = []

        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return relations

            json_str = json_match.group()
            data = json.loads(json_str)

            # 创建实体文本到实体的映射
            entity_map = {entity['text']: entity for entity in entities}

            # 解析关系
            for rel_data in data.get('relations', []):
                head_text = rel_data.get('head', '').strip()
                tail_text = rel_data.get('tail', '').strip()
                relation_type = rel_data.get('relation', '').strip()

                # 验证实体存在和关系类型
                if (head_text in entity_map and tail_text in entity_map and
                    relation_type in self.relation_types):

                    relation = {
                        'head': head_text,
                        'head_type': rel_data.get('head_type', entity_map[head_text]['type']),
                        'relation': relation_type,
                        'tail': tail_text,
                        'tail_type': rel_data.get('tail_type', entity_map[tail_text]['type']),
                        'confidence': rel_data.get('confidence', 0.8)
                    }

                    relations.append(relation)

        except Exception as e:
            print(f"关系解析错误: {e}")

        return relations

    def extract_entities_and_relations(self, text: str, doc_title: str = "") -> Dict[str, Any]:
        """综合抽取实体和关系"""
        print(f"🚀 开始综合抽取: {doc_title}")

        # 第一步：抽取实体
        entity_result = self.extract_entities(text, doc_title)

        if not entity_result['success']:
            return {
                'success': False,
                'entities': [],
                'relations': [],
                'error': entity_result.get('error', '实体抽取失败'),
                'doc_title': doc_title
            }

        entities = entity_result['entities']

        # 第二步：基于实体抽取关系
        relation_result = self.extract_relations(text, entities, doc_title)

        # 合并结果
        return {
            'success': True,
            'entities': entities,
            'relations': relation_result['relations'],
            'entity_count': len(entities),
            'relation_count': len(relation_result['relations']),
            'processing_time': entity_result['processing_time'] + relation_result['processing_time'],
            'doc_title': doc_title,
            'entity_result': entity_result,
            'relation_result': relation_result
        }

    def display_results(self, text: str, result: Dict[str, Any]):
        """显示抽取结果"""
        print(f"\n" + "="*60)
        print(f"针灸大成实体抽取结果")
        print(f"="*60)

        print(f"\n文档: {result.get('doc_title', '未知')}")
        print(f"文本信息:")
        print(f"   长度: {len(text)} 字符")
        print(f"   处理时间: {result.get('processing_time', 0):.2f}秒")

        if not result['success']:
            print(f"\n错误：抽取失败: {result.get('error', '未知错误')}")
            return
        
        entities = result['entities']
        print(f"   抽取实体数: {len(entities)} 个")
        
        # 按类型统计
        type_stats = {}
        for entity in entities:
            entity_type = entity['type']
            if entity_type not in type_stats:
                type_stats[entity_type] = []
            type_stats[entity_type].append(entity)
        
        print(f"\n抽取结果:")

        for entity_type in ['病名', '症状', '穴位', '治法']:
            entities_of_type = type_stats.get(entity_type, [])
            unique_texts = sorted(set([e['text'] for e in entities_of_type]))

            print(f"\n   {entity_type} ({len(unique_texts)}个):")
            if unique_texts:
                for i, entity_text in enumerate(unique_texts, 1):
                    print(f"      {i:2d}. {entity_text}")
            else:
                print(f"      (无)")


def check_environment():
    """检查运行环境"""
    print("检查运行环境...")

    # 检查Python版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"   Python版本: {python_version}")

    # 检查依赖包
    try:
        import requests
        print(f"   requests包: 已安装")
    except ImportError:
        print(f"   requests包: 未安装")
        return False
    
    # 检查API密钥
    if DEEPSEEK_API_KEY:
        print(f"   API密钥: 已内置")
    else:
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if api_key:
            print(f"   API密钥: 环境变量已设置")
        else:
            print(f"   API密钥: 未配置")
            return False

    # 检查文档目录
    texts_dir = Path("test_texts")
    if texts_dir.exists():
        file_count = len(list(texts_dir.glob("*.txt")))
        print(f"   文档目录: 已存在 ({file_count}个文件)")
    else:
        print(f"   文档目录: 不存在")
        return False

    print("环境检查通过")
    return True


def main():
    """主函数"""
    print("针灸大成实体抽取器 - 简化版本")
    print("="*50)
    print("功能：探索大模型实体抽取效果，纯大模型方法，无备用机制")
    print("模型：DeepSeek (deepseek-chat)")
    print("版本：4.0 (简化版)")
    print("="*50)

    # 检查运行环境
    if not check_environment():
        print("\n错误：环境检查失败，请按以下步骤配置：")
        print("1. 安装依赖包：")
        print("   pip install requests")
        print("   或使用国内镜像：pip install requests -i https://pypi.tuna.tsinghua.edu.cn/simple/")
        print("2. 确保test_texts文件夹存在且包含文档")
        print("注意：API密钥已内置，无需额外配置")
        return
    
    try:
        # 初始化文档选择器
        selector = ZhenjiuDocumentSelector()
        
        # 显示文档列表
        selector.display_documents()
        
        # 选择文档
        selected_doc = selector.select_document()
        if not selected_doc:
            print("程序已退出")
            return
        
        # 初始化抽取器
        extractor = ZhenjiuEntityExtractor()
        
        # 进行实体抽取
        result = extractor.extract_entities(selected_doc['content'], selected_doc['title'])
        
        # 显示结果
        extractor.display_results(selected_doc['content'], result)
        
        # 保存结果到文件
        output_file = f"extraction_result_{selected_doc['filename'][:-4]}.json"
        output_data = {
            "source_document": selected_doc,
            "extraction_result": result,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n结果已保存到: {output_file}")

        # 性能总结
        if result['success']:
            entity_count = result['entity_count']
            processing_time = result['processing_time']
            print(f"\n性能总结:")
            print(f"   成功抽取 {entity_count} 个实体")
            print(f"   处理时间: {processing_time:.2f}秒")

        print(f"\n程序运行完成")
        
    except Exception as e:
        print(f"错误：程序运行失败: {e}")
        print(f"请检查:")
        print(f"   1. 网络连接是否正常")
        print(f"   2. 是否有足够的API余额")
        print(f"   3. API密钥是否有效（已内置）")


if __name__ == "__main__":
    main()
