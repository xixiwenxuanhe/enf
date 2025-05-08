import pandas as pd

# 读取 CSV 文件
df = pd.read_csv("seller_United%20Kingdom_Mail20250507_Fixed.csv")

# 生成 Email 列，规则为：info@companyname.com（company name 全部小写、去掉空格和特殊字符）
def generate_email(name):
    name_clean = ''.join(e for e in name.lower() if e.isalnum())  # 只保留字母和数字
    return f"info@{name_clean}.com"

df['Email'] = df['Company Name'].apply(generate_email)

# 只保留需要的列
output_df = df[['Number', 'Company Name', 'Email']]

# 保存为新的 CSV 文件
output_df.to_csv(f"generated_emails.csv", index=False)

print("Emails generated and saved to 'generated_emails.csv'")
