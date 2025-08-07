#!/usr/bin/env python3
"""
人工审核界面 - 针灸大成实体抽取
提供友好的交互式审核界面，让人工审核更加简单高效

功能：
1. 加载审核任务
2. 交互式审核界面
3. 保存审核结果
4. 生成审核报告

版本：1.0
"""

import json
import os
import time
from datetime import datetime
from typing import List, Dict, Any

class HumanReviewInterface:
    """人工审核界面"""
    
    def __init__(self, review_file: str = "outputs/review_data/human_review_tasks.json"):
        self.review_file = review_file
        self.review_data = None
        self.current_task_index = 0
        self.completed_tasks = 0
        
    def load_review_tasks(self) -> bool:
        """加载审核任务"""
        try:
            with open(self.review_file, 'r', encoding='utf-8') as f:
                self.review_data = json.load(f)
            
            print(f"✅ 成功加载审核任务")
            print(f"   📝 总任务数: {self.review_data['total_tasks']}")

            # 统计优先级
            high_priority = len([t for t in self.review_data['tasks'] if t.get('priority') == 'high'])
            medium_priority = len([t for t in self.review_data['tasks'] if t.get('priority') == 'medium'])

            print(f"   🔥 高优先级: {high_priority}")
            print(f"   ⚠️ 中优先级: {medium_priority}")

            return True
            
        except Exception as e:
            print(f"❌ 加载审核任务失败: {e}")
            return False
    
    def display_task(self, task: Dict[str, Any]):
        """显示单个审核任务"""
        
        print("\n" + "="*80)
        print(f"📝 审核任务 {task['id']} / {self.review_data['total_tasks']}")
        print(f"🔥 优先级: {task['priority'].upper()}")
        print(f"📄 文档: {task.get('doc_name', 'unknown')}")
        print(f"🎯 原因: {task.get('reason', 'unknown')}")
        print("="*80)

        print(f"\n❓ {task['question']}")

        print(f"\n📖 上下文:")
        if 'context' in task:
            if 'full_sentence' in task['context']:
                print(f"   完整句子: {task['context']['full_sentence']}")
            if 'highlighted' in task['context']:
                print(f"   高亮上下文: {task['context']['highlighted'][:200]}...")

        print(f"\n🤖 各模型判断:")
        if 'models_opinion' in task:
            for model, opinion in task['models_opinion'].items():
                print(f"   {model}: {opinion}")

        print(f"\n✅ 可选选项:")
        for i, option in enumerate(task['options'], 1):
            print(f"   {i}. {option}")
    
    def get_user_input(self, task: Dict[str, Any]) -> Dict[str, str]:
        """获取用户输入"""
        
        while True:
            try:
                # 选择选项
                choice = input(f"\n请选择选项 (1-{len(task['options'])}) 或 's'跳过, 'q'退出: ").strip().lower()
                
                if choice == 'q':
                    return {'action': 'quit'}
                elif choice == 's':
                    return {'action': 'skip'}
                
                choice_num = int(choice)
                if 1 <= choice_num <= len(task['options']):
                    selected_option = task['options'][choice_num - 1]

                    # 获取备注
                    notes = input("备注 (可选): ").strip()

                    # 获取审核人
                    reviewer = input("审核人 (可选): ").strip()
                    if not reviewer:
                        reviewer = "匿名"

                    return {
                        'action': 'review',
                        'selected_option': selected_option,
                        'notes': notes,
                        'reviewer': reviewer,
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    print(f"❌ 请输入 1-{len(task['options'])} 之间的数字")
                    
            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n👋 程序已退出")
                return {'action': 'quit'}
    
    def save_progress(self):
        """保存审核进度（只保存未完成的任务）"""
        try:
            # 分离已完成和未完成的任务
            completed_tasks = []
            pending_tasks = []

            for task in self.review_data['tasks']:
                if task['human_decision']['selected_option']:
                    completed_tasks.append(task)
                else:
                    pending_tasks.append(task)

            # 保存已完成的任务到审核数据库
            if completed_tasks:
                self.save_completed_tasks(completed_tasks)
                print(f"✅ {len(completed_tasks)} 个已完成任务已保存到审核数据库")

            # 备份原文件
            backup_file = f"{self.review_file}.backup"
            if os.path.exists(self.review_file):
                with open(self.review_file, 'r', encoding='utf-8') as f:
                    backup_data = f.read()
                with open(backup_file, 'w', encoding='utf-8') as f:
                    f.write(backup_data)

            # 只保存未完成的任务
            self.review_data['tasks'] = pending_tasks
            self.review_data['metadata']['total_tasks'] = len(pending_tasks)

            with open(self.review_file, 'w', encoding='utf-8') as f:
                json.dump(self.review_data, f, ensure_ascii=False, indent=2)

            print(f"💾 进度已保存，剩余 {len(pending_tasks)} 个待审核任务")

        except Exception as e:
            print(f"❌ 保存失败: {e}")

    def save_completed_tasks(self, completed_tasks):
        """保存已完成的任务到审核数据库"""
        if not completed_tasks:
            return

        database_file = "outputs/review_data/review_database.json"

        # 加载现有数据库
        database = {"completed_reviews": []}
        if os.path.exists(database_file):
            try:
                with open(database_file, 'r', encoding='utf-8') as f:
                    database = json.load(f)
            except:
                pass

        # 添加新完成的任务
        if "completed_reviews" not in database:
            database["completed_reviews"] = []

        for task in completed_tasks:
            # 添加完成时间戳
            import time
            task['human_decision']['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
            database["completed_reviews"].append(task)

        # 保存数据库
        with open(database_file, 'w', encoding='utf-8') as f:
            json.dump(database, f, ensure_ascii=False, indent=2)
    
    def generate_review_report(self) -> Dict[str, Any]:
        """生成审核报告"""
        
        completed_tasks = [task for task in self.review_data['tasks'] 
                          if task['human_decision']['selected_option']]
        
        if not completed_tasks:
            return {'message': '暂无已完成的审核任务'}
        
        # 统计审核结果
        option_stats = {}
        confidence_stats = {'高': 0, '中': 0, '低': 0}
        priority_stats = {'high': 0, 'medium': 0, 'low': 0}
        conflict_type_stats = {}
        
        for task in completed_tasks:
            decision = task['human_decision']
            
            # 选项统计
            option = decision['selected_option']
            option_stats[option] = option_stats.get(option, 0) + 1
            
            # 置信度统计
            confidence = decision.get('confidence', '中')
            if confidence in confidence_stats:
                confidence_stats[confidence] += 1
            
            # 优先级统计
            priority = task['priority']
            if priority in priority_stats:
                priority_stats[priority] += 1
            
            # 冲突类型统计
            conflict_type = task['conflict_type']
            conflict_type_stats[conflict_type] = conflict_type_stats.get(conflict_type, 0) + 1
        
        report = {
            'total_tasks': self.review_data['total_tasks'],
            'completed_tasks': len(completed_tasks),
            'completion_rate': len(completed_tasks) / self.review_data['total_tasks'],
            'option_stats': option_stats,
            'confidence_stats': confidence_stats,
            'priority_stats': priority_stats,
            'conflict_type_stats': conflict_type_stats,
            'recommendations': self.generate_recommendations(completed_tasks)
        }
        
        return report
    
    def generate_recommendations(self, completed_tasks: List[Dict]) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # 分析审核结果
        invalid_count = sum(1 for task in completed_tasks 
                           if task['human_decision']['selected_option'] == '无效实体')
        
        type_corrections = sum(1 for task in completed_tasks 
                              if task['conflict_type'] == 'type_disagreement' 
                              and task['human_decision']['selected_option'] not in ['无效实体', '其他'])
        
        if invalid_count > len(completed_tasks) * 0.3:
            recommendations.append("⚠️ 无效实体比例较高，建议优化模型过滤规则")
        
        if type_corrections > 0:
            recommendations.append(f"🔧 发现 {type_corrections} 个类型错误，建议更新实体类型定义")
        
        recommendations.extend([
            "💡 将审核结果用于优化模型提示词",
            "💡 将确认的实体加入知识库",
            "💡 分析错误模式，改进抽取规则"
        ])
        
        return recommendations
    
    def display_report(self, report: Dict[str, Any]):
        """显示审核报告"""
        
        print("\n" + "="*80)
        print("📊 人工审核报告")
        print("="*80)
        
        print(f"\n📈 完成情况:")
        print(f"   总任务数: {report['total_tasks']}")
        print(f"   已完成: {report['completed_tasks']}")
        print(f"   完成率: {report['completion_rate']:.1%}")
        
        print(f"\n✅ 审核结果统计:")
        for option, count in report['option_stats'].items():
            percentage = count / report['completed_tasks'] * 100
            print(f"   {option}: {count} ({percentage:.1f}%)")
        
        print(f"\n🎯 置信度分布:")
        for confidence, count in report['confidence_stats'].items():
            if count > 0:
                percentage = count / report['completed_tasks'] * 100
                print(f"   {confidence}: {count} ({percentage:.1f}%)")
        
        print(f"\n🔥 优先级分布:")
        for priority, count in report['priority_stats'].items():
            if count > 0:
                percentage = count / report['completed_tasks'] * 100
                print(f"   {priority}: {count} ({percentage:.1f}%)")
        
        print(f"\n💡 改进建议:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"   {i}. {rec}")
    
    def run_interactive_review(self):
        """运行交互式审核"""
        
        print("\n🚀 开始交互式审核")
        print("💡 提示: 输入 's' 跳过当前任务，'q' 退出程序")
        
        tasks = self.review_data['tasks']
        
        # 按优先级排序
        priority_order = {'high': 0, 'medium': 1, 'low': 2}
        tasks.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        for i, task in enumerate(tasks):
            # 跳过已完成的任务
            if task['human_decision']['selected_option']:
                continue
            
            self.display_task(task)
            
            user_input = self.get_user_input(task)
            
            if user_input['action'] == 'quit':
                print("\n👋 审核已退出")
                break
            elif user_input['action'] == 'skip':
                print("⏭️ 已跳过当前任务")
                continue
            elif user_input['action'] == 'review':
                # 保存审核结果
                task['human_decision'].update({
                    'selected_option': user_input['selected_option'],
                    'notes': user_input['notes'],
                    'reviewer': user_input['reviewer'],
                    'timestamp': user_input['timestamp']
                })
                
                self.completed_tasks += 1
                print(f"✅ 审核完成! 进度: {self.completed_tasks}/{len(tasks)}")
                
                # 每完成5个任务自动保存一次
                if self.completed_tasks % 5 == 0:
                    self.save_progress()
        
        # 最终保存
        self.save_progress()
        
        # 生成并显示报告
        report = self.generate_review_report()
        self.display_report(report)
        
        # 保存报告
        report_file = f"review_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 审核报告已保存: {report_file}")


def main():
    """主函数"""
    print("针灸大成实体抽取 - 人工审核界面")
    print("="*50)
    print("🎯 功能: 交互式审核争议实体")
    print("📝 输入: human_review_tasks.json")
    print("💾 输出: 审核结果和报告")
    print("="*50)
    
    # 检查审核任务文件
    if not os.path.exists("outputs/review_data/human_review_tasks.json"):
        print("❌ 未找到审核任务文件: outputs/review_data/human_review_tasks.json")
        print("请先运行 integrated_extractor.py 生成审核任务")
        return
    
    try:
        # 初始化审核界面
        interface = HumanReviewInterface()
        
        # 加载审核任务
        if not interface.load_review_tasks():
            return
        
        # 显示使用说明
        print(f"\n📋 使用说明:")
        print(f"   1. 仔细阅读每个实体的上下文")
        print(f"   2. 参考各模型的判断，但以您的专业知识为准")
        print(f"   3. 优先处理高优先级任务（类型冲突）")
        print(f"   4. 可以随时退出，进度会自动保存")
        
        # 询问是否开始审核
        start = input(f"\n是否开始审核? (y/n): ").strip().lower()
        if start != 'y':
            print("👋 程序已退出")
            return
        
        # 运行交互式审核
        interface.run_interactive_review()
        
        print(f"\n🎉 审核完成！感谢您的贡献！")
        
    except Exception as e:
        print(f"❌ 程序运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
