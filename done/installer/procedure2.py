import os
import pandas as pd

def generate_email(name):
    name_clean = ''.join(e for e in name.lower() if e.isalnum())
    return f"info@{name_clean}.com"

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