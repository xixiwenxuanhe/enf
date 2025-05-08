#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import sys

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

def main():
    # 直接在代码中指定CSV文件路径
    csv_file_path = "../procedure1/installer_Spain_Procedure120250507.csv"
    output_file = "extracted_emails.txt"
    
    if not os.path.exists(csv_file_path):
        print(f"错误: 文件 '{csv_file_path}' 不存在")
        sys.exit(1)
    
    emails = extract_emails(csv_file_path)
    save_emails(emails, output_file)

if __name__ == "__main__":
    main() 