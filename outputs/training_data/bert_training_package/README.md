# BERT训练数据包

## 📊 数据集信息
- 总文档数: 2
- 训练集: 1 个文档
- 验证集: 0 个文档  
- 测试集: 1 个文档
- 最大序列长度: 392

## 🏷️ 实体类型
- 病名 (DIS): 疾病名称
- 症状 (SYM): 症状表现
- 穴位 (ACU): 经络穴位
- 治法 (TRE): 治疗方法

## 📁 文件说明
- `train.txt`, `val.txt`, `test.txt`: CoNLL格式数据
- `bert_train.json`, `bert_val.json`, `bert_test.json`: BERT输入格式
- `config.json`: 模型配置文件
- `README.md`: 本说明文件

## 🚀 使用方法
1. 使用CoNLL格式文件进行传统NER模型训练
2. 使用BERT格式文件进行BERT+BiLSTM+CRF训练
3. 参考config.json配置模型参数

## 📝 标注格式
采用BIO标注格式：
- B-DIS: 病名开始
- I-DIS: 病名内部
- B-SYM: 症状开始
- I-SYM: 症状内部
- B-ACU: 穴位开始
- I-ACU: 穴位内部
- B-TRE: 治法开始
- I-TRE: 治法内部
- O: 非实体
