import os
import csv
import glob

# 确保procedure1目录存在
os.makedirs('procedure1', exist_ok=True)

# 查找所有目标csv文件
for file in glob.glob("Company/*Company20250508.csv"):
    out_name = file.replace("Company", "Procedure1")
    out_path = os.path.join("procedure1", out_name)
    with open(file, newline='', encoding='utf-8') as fin, \
         open(out_path, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        writer = csv.writer(fout)
        # 写表头
        writer.writerow(['Number', 'Company Name', 'Email', 'Website'])
        for row in reader:
            number = row.get('Number', '')
            company = row.get('Company Name', '')
            link1 = row.get('Link1', '')
            # Email留空
            writer.writerow([number, company, '', link1])
    print(f"{file} 已处理，结果保存为 {out_path}")

print("全部处理完成。")