#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import sys
import glob

def extract_emails(csv_file_path):
    """
    从CSV文件中提取所有邮箱地址
    CSV文件格式应为：Number,Company Name,Company Website,Email
    """
    emails = []
    
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            # 跳过标题行
            next(csv_reader)
            
            for row in csv_reader:
                # 检查行是否有足够的列，并且Email列不为空
                if len(row) >= 4 and row[3].strip():
                    emails.append(row[3].strip())
    except Exception as e:
        print(f"处理CSV文件时出错: {e}")
        return []
    
    return emails

def save_emails(emails, output_file="extracted_emails.txt"):
    """
    将提取的邮箱保存到文件中
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            for email in emails:
                file.write(f"{email}\n")
        print(f"已成功提取 {len(emails)} 个邮箱地址并保存到 {output_file}")
    except Exception as e:
        print(f"保存邮箱地址时出错: {e}")

def extract_emails_from_directory(directory_path):
    """
    遍历指定目录下所有csv文件，提取所有非空邮箱
    """
    all_emails = []  # 改用列表而不是集合，保留重复项
    csv_files = glob.glob(os.path.join(directory_path, '*.csv'))
    if not csv_files:
        print(f"警告: 目录 '{directory_path}' 下未找到任何CSV文件")
        return all_emails
        
    for csv_file in csv_files:
        try:
            emails = extract_emails(csv_file)
            all_emails.extend(emails)  # 使用extend而不是update，保留所有邮箱
            print(f"已处理文件: {csv_file}，提取邮箱数: {len(emails)}")
        except Exception as e:
            print(f"警告: 处理文件 '{csv_file}' 时出错: {e}")
            
    return all_emails

def main():
    # 设置要处理的CSV文件目录
    csv_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'procedure0')
    output_file = "extracted_emails.txt"

    if not os.path.exists(csv_dir):
        print(f"错误: 目录 '{csv_dir}' 不存在")
        sys.exit(1)

    emails = extract_emails_from_directory(csv_dir)
    if not emails:
        print("未提取到任何邮箱地址。")
        sys.exit(0)
    save_emails(emails, output_file)

if __name__ == "__main__":
    main() 