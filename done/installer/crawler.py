import requests
from bs4 import BeautifulSoup
import csv
import datetime
import re
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import concurrent.futures
import random
import time
import proxy_pool

# 日志重定向到文件和终端
class Logger(object):
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w", encoding="utf-8")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
        self.log.flush()  # 实时写入
    def flush(self):
        self.terminal.flush()
        self.log.flush()

sys.stdout = Logger("crawler.py.log")

def fetch_company_list(base_url, start_page, end_page, limit, headers, data_event):
    company_data = []
    seq = 1
    proxy_index = 0  # 代理索引，0为本机
    page_since_last_proxy = 0
    proxies = None  # 本机
    for page in range(start_page, end_page + 1):
        # 每20页切换代理
        if page_since_last_proxy >= 20:
            proxy_index += 1
            page_since_last_proxy = 0
        # 设置代理
        if proxy_index == 0:
            proxies = None  # 本机
        else:
            proxies = proxy_pool.get_proxy_by_index(proxy_index - 1)
        URL = f"{base_url}?page={page}"
        print(f"[代理{proxy_index}] 正在抓取页面：{URL}")
        try:
            response = requests.get(URL, headers=headers, proxies=proxies, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all("tr", attrs={"class": "mkjs-el"})
            page_count = 0
            for row in rows:
                # 提取地址
                address_td = row.find("td", class_="no-left-right-padding")
                address = address_td.get_text(strip=True) if address_td else ""
                name_link = row.find("a", attrs={"data-event": data_event})
                name = name_link.get_text(strip=True) if name_link else ""
                link1 = name_link['href'] if name_link and name_link.has_attr('href') else ""
                # 过滤无效公司（如广告或特殊页）
                if not name or not link1:
                    continue
                company_data.append((seq, name, address, link1))
                seq += 1
                page_count += 1
                # 判断是否达到limit
                if limit != 'all':
                    try:
                        lim = int(limit)
                        if len(company_data) > lim:
                            break
                    except Exception:
                        pass
            print(f"[代理{proxy_index}] 本页抓取到公司数量：{page_count}")
            # 如果本页抓取到0个，说明被限制，立即切换代理
            if page_count == 0:
                proxy_index += 1
                page_since_last_proxy = 0
        except Exception as e:
            print(f"抓取失败：{e}")
        # 页内break后，整体break
        if limit != 'all':
            try:
                lim = int(limit)
                if len(company_data) > lim:
                    break
            except Exception:
                pass
        page_since_last_proxy += 1
        time.sleep(0.1)  # 增加每页抓取间隔0.1秒，防止被限制
    # limit截断
    if limit != 'all':
        try:
            lim = int(limit)
            company_data = company_data[:lim]
        except Exception:
            pass
    print(f"所有页面共抓取到公司数量：{len(company_data)}")
    return company_data

def fetch_link2(item, headers, proxies=None, max_retry=3, proxy_switch_callback=None, proxy_index=0):
    number, name, address, link1 = item
    link2 = ""
    if link1:
        detail_url = link1 if link1.startswith('http') else f"https://www.enf.com.cn{link1}"
        for attempt in range(max_retry):
            try:
                resp = requests.get(detail_url, headers=headers, proxies=proxies, timeout=10)
                if resp.status_code == 429:
                    print(f"[{number}] 错误：Too Many Requests")
                    time.sleep(random.uniform(0.5, 1))
                    if proxy_switch_callback:
                        proxies = proxy_switch_callback()
                    continue
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')
                ext_link_tag = soup.find("a", attrs={"itemprop": "url"})
                link2 = ext_link_tag['href'] if ext_link_tag and ext_link_tag.has_attr('href') else ""
                break
            except Exception as e:
                if attempt == max_retry - 1:
                    print(f"获取第{number}条 {name} 官网链接失败：{e}")
                time.sleep(random.uniform(1, 3))  # 随机延迟，防止被封
    print(f"[代理{proxy_index}] 正在处理第{number}条：{name} {link2}")
    return (number, name, address, link1, link2)

def fetch_all_link2(company_data, headers):
    company_data_with_link2 = []
    proxy_index = 0
    proxies = None
    def switch_proxy():
        nonlocal proxy_index, proxies
        proxy_index += 1
        if proxy_index == 0:
            proxies = None
        else:
            proxies = proxy_pool.get_proxy_by_index(proxy_index - 1)
        return proxies
    for idx, item in enumerate(company_data):
        # 每20个切换一次代理
        if idx % 20 == 0:
            proxy_index += 1
        if proxy_index == 0:
            proxies = None
        else:
            proxies = proxy_pool.get_proxy_by_index(proxy_index - 1)
        company_data_with_link2.append(fetch_link2(item, headers, proxies=proxies, proxy_switch_callback=switch_proxy, proxy_index=proxy_index))
        time.sleep(0.1)  # 每个都延时0.1秒
    return company_data_with_link2

def extract_url_prefix(url):
    # 提取url路径末尾两个词，去除结尾斜杠
    parts = url.rstrip('/').split('/')
    if len(parts) >= 2:
        return f"{parts[-2]}_{parts[-1]}"
    elif len(parts) == 1:
        return parts[-1]
    else:
        return "output"

def save_to_csv(company_data_with_link2, script_name, url_prefix):
    current_date = datetime.datetime.now().strftime("%Y%m%d")
    csv_filename = f"{url_prefix}_Company{current_date}.csv"
    with open(csv_filename, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Number", "Company Name", "Address", "Link1", "Link2"])
        writer.writerows(company_data_with_link2)
    print(f"{csv_filename} 完成：共保存 {len(company_data_with_link2)} 条公司信息")

if __name__ == "__main__":
    # 元组列表，每个元组包含：url, 起始页码, 结束页码, data-event
    url_page_list = [
        # # 西班牙（Spain）
        # ("https://www.enf.com.cn/directory/installer/Spain", 1, 19, "cl_installer_spain_clk"),

        # # 德国（Germany）
        # ("https://www.enf.com.cn/directory/installer/Germany", 1, 70, "cl_installer_germany_clk"),

        # # 法国（France）
        # ("https://www.enf.com.cn/directory/installer/France", 1, 9, "cl_installer_france_clk"),

        # # 澳大利亚（Australia）
        # ("https://www.enf.com.cn/directory/installer/Australia", 1, 36, "cl_installer_australia_clk"),

        # # 波兰（Poland）
        # ("https://www.enf.com.cn/directory/installer/Poland", 1, 11, "cl_installer_poland_clk"),

        # 捷克共和国（Czech Republic）
        ("https://www.enf.com.cn/directory/installer/Czech%20Republic", 1, 5, "cl_installer_czech_republic_clk"),

        # 比利时（Belgium）
        ("https://www.enf.com.cn/directory/installer/Belgium", 1, 7, "cl_installer_belgium_clk"),

        # 美国（United States）
        ("https://www.enf.com.cn/directory/installer/United%20States", 1, 85, "cl_installer_united_states_clk"),

        # 印度（India）
        ("https://www.enf.com.cn/directory/installer/India", 1, 37, "cl_installer_india_clk"),

        # 巴西（Brazil）
        ("https://www.enf.com.cn/directory/installer/Brazil", 1, 25, "cl_installer_brazil_clk"),

        # 瑞士（Switzerland）
        ("https://www.enf.com.cn/directory/installer/Switzerland", 1, 7, "cl_installer_switzerland_clk"),

        # 奥地利（Austria）
        ("https://www.enf.com.cn/directory/installer/Austria", 1, 10, "cl_installer_austria_clk"),

        # 加拿大（Canada）
        ("https://www.enf.com.cn/directory/installer/Canada", 1, 9, "cl_installer_canada_clk"),
    ]

    LIMIT = 'all'
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    SCRIPT_NAME = "crawler.py"

    for url, start_page, end_page, data_event in url_page_list:
        url_prefix = extract_url_prefix(url)
        print(f"\n==== 开始抓取 {url_prefix} ====")
        company_data = fetch_company_list(url, start_page, end_page, LIMIT, HEADERS, data_event)
        company_data_with_link2 = fetch_all_link2(company_data, HEADERS)
        save_to_csv(company_data_with_link2, SCRIPT_NAME, url_prefix)