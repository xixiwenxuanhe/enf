import os
import pandas as pd
from urllib.parse import unquote

input_dir = 'procedure2'
company_dir = 'Company'
output_dir = 'procedure3'
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(input_dir):
    if filename.endswith('.csv'):
        # 解析国家名
        parts = filename.split('_')
        if len(parts) < 2:
            continue
        country_raw = parts[1]
        country = unquote(country_raw).replace('%20', ' ')
        # 判断Customer Type
        if filename.startswith('seller'):
            customer_type = 'Sellers'
        elif filename.startswith('installer'):
            customer_type = 'Installers'
        else:
            customer_type = 'Unknown'

        # 读取procedure2下的csv
        df = pd.read_csv(os.path.join(input_dir, filename))

        # 读取Company下的csv，获取Link2列
        company_filename = filename.replace('Procedure2', 'Company')
        company_path = os.path.join(company_dir, company_filename)
        if os.path.exists(company_path):
            df_company = pd.read_csv(company_path)
            if 'Link2' in df_company.columns:
                company_website = df_company['Link2']
            else:
                company_website = [''] * len(df)
        else:
            company_website = [''] * len(df)

        # 新建DataFrame
        df_new = pd.DataFrame()
        df_new['Number'] = df['Number']
        df_new['Country'] = country
        df_new['Company Name'] = df['Company Name']
        df_new['Email'] = df['Email']
        df_new['Customer Type'] = customer_type
        df_new['Company Website'] = company_website

        # 保存为xlsx
        out_filename = f"{customer_type}_{country}.xlsx"
        out_path = os.path.join(output_dir, out_filename)
        with pd.ExcelWriter(out_path, engine='xlsxwriter') as writer:
            df_new.to_excel(writer, index=False, sheet_name=customer_type)
        print(f"已保存：{out_path}")
