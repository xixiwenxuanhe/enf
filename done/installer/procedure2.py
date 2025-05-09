import os
import pandas as pd
import random

# 邮箱前缀及其概率
EMAIL_PREFIXES = {
    'info': 0.6,
    'service': 0.2,
    'contact': 0.2
}

def random_case_word(word: str) -> str:
    """随机处理单词的大小写"""
    r = random.random()
    if r < 0.9:      # 90%概率全小写
        return word.lower()
    elif r < 0.95:   # 5%概率首字母大写
        return word.capitalize()
    else:            # 5%概率全大写
        return word.upper()

def generate_email(name):
    # 清理公司名称
    name_clean = ''.join(e for e in name.lower() if e.isalnum())
    
    # 根据概率随机选择前缀
    prefix = random.choices(
        list(EMAIL_PREFIXES.keys()),
        weights=list(EMAIL_PREFIXES.values())
    )[0]
    
    # 随机处理前缀大小写
    prefix = random_case_word(prefix)
    
    return f"{prefix}@{name_clean}.com"

input_dir = 'procedure1'
output_dir = 'procedure2'
os.makedirs(output_dir, exist_ok=True)

results = []

for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        input_path = os.path.join(input_dir, filename)
        output_filename = filename.replace('Procedure1', 'Procedure2')
        output_path = os.path.join(output_dir, output_filename)

        df = pd.read_csv(input_path)
        mask = df['Email'].isnull() | (df['Email'].astype(str).str.strip() == '')
        df.loc[mask, 'Email'] = df.loc[mask, 'Company Name'].apply(generate_email)
        
        # 重新排列列的顺序
        df = df[['Number', 'Company Name', 'Email', 'Company Website']]
        
        df.to_csv(output_path, index=False)

        # 统计空邮箱数量
        empty_count = df['Email'].isnull().sum() + (df['Email'].astype(str).str.strip() == '').sum()
        results.append((output_filename, empty_count))

# 输出每个文件空邮箱数量
for fname, count in results:
    print(f"{fname} 空邮箱数量: {count}")