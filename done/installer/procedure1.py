import os
import pandas as pd
from utils.clean_emails_from_txt import process_email
from collections import Counter

def process_csv(input_path: str, output_path: str) -> tuple[float, int]:
    """
    处理单个CSV文件中的邮箱
    
    Args:
        input_path: 输入CSV文件路径
        output_path: 输出CSV文件路径
        
    Returns:
        tuple: (空邮箱比例, 重复邮箱数量)
    """
    # 读取CSV文件
    df = pd.read_csv(input_path)
    
    # 确保Email列存在
    if 'Email' not in df.columns:
        print(f"警告: {input_path} 中未找到Email列")
        return 0.0, 0
        
    # 处理非空邮箱
    def process_single_email(email):
        if pd.isna(email) or email == '':
            return ''
        processed_email, _ = process_email(str(email))
        return processed_email
        
    # 应用邮箱处理
    df['Email'] = df['Email'].apply(process_single_email)
    
    # 处理重复邮箱
    email_counts = Counter(df['Email'].dropna())
    duplicate_emails = {email for email, count in email_counts.items() if count > 1 and email != ''}
    
    if duplicate_emails:
        print(f"\n发现重复邮箱 {len(duplicate_emails)} 个:")
        for email in duplicate_emails:
            print(f"  - {email}")
        # 重置重复邮箱为空
        df.loc[df['Email'].isin(duplicate_emails), 'Email'] = ''
        
    # 计算空邮箱比例
    total_rows = len(df)
    empty_rows = df['Email'].isna().sum() + (df['Email'] == '').sum()
    empty_ratio = empty_rows / total_rows if total_rows > 0 else 0.0
    
    # 保存处理后的文件
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n已处理：{input_path}")
    print(f"已保存：{output_path}")
    print(f"空邮箱比例: {empty_ratio:.2%}")
    
    return empty_ratio, len(duplicate_emails)

def main():
    # 获取procedure0目录中的所有CSV文件
    procedure0_dir = 'procedure0'
    procedure1_dir = 'procedure1'
    
    if not os.path.exists(procedure0_dir):
        print(f"错误: 未找到{procedure0_dir}目录")
        return
        
    # 创建输出目录
    os.makedirs(procedure1_dir, exist_ok=True)
    
    # 统计总体情况
    total_files = 0
    total_empty_ratio = 0.0
    total_duplicates = 0
    
    # 处理所有CSV文件
    for filename in os.listdir(procedure0_dir):
        if not filename.lower().endswith('.csv'):
            continue
            
        total_files += 1
        # 构建输入输出路径
        input_path = os.path.join(procedure0_dir, filename)
        output_filename = filename.replace('Procedure0', 'Procedure1')
        output_path = os.path.join(procedure1_dir, output_filename)
        
        try:
            empty_ratio, num_duplicates = process_csv(input_path, output_path)
            total_empty_ratio += empty_ratio
            total_duplicates += num_duplicates
        except Exception as e:
            print(f"处理 {filename} 时出错: {str(e)}")
            
    # 输出总体统计
    if total_files > 0:
        print("\n总体统计:")
        print(f"处理文件总数: {total_files}")
        print(f"平均空邮箱比例: {(total_empty_ratio/total_files):.2%}")
        print(f"总重复邮箱数: {total_duplicates}")

if __name__ == '__main__':
    main() 