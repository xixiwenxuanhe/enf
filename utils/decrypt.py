import requests
import re
import os
import datetime
import time
import sys
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_pool import get_random_proxy, get_proxy_by_index, proxy_accounts

def extract_email_from_script(html_content):
    """从页面脚本中提取加密的邮箱并解密"""
    # 使用正则表达式查找let eee = 'xxx' 形式的加密邮箱
    email_pattern = re.compile(r"let\s+eee\s*=\s*['\"]([^'\"]+)['\"]")
    match = email_pattern.search(html_content)
    
    if match:
        encoded_email = match.group(1)
        # 应用解密规则：只将#109#103#.cn替换为@
        email = encoded_email.replace('#109#103#.cn', '@')
        print(f"找到加密邮箱: {encoded_email}")
        print(f"解密后的邮箱: {email}")
        return email
    return None

# 获取当前时间，格式化为字符串
def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# 获取脚本所在目录
def get_script_dir():
    return os.path.dirname(os.path.abspath(__file__))

def fetch_page(url, use_local_only=False):
    """
    获取页面内容
    
    参数:
        url (str): 要获取的URL
        use_local_only (bool): 是否只使用本机连接，默认为False
        
    返回:
        list: 成功结果列表，每个元素为(状态码, 页面内容, 使用的连接类型)
    """
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    
    results = []
    
    # 首先尝试本机连接
    print("使用本机")
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            print("  成功")
            results.append((response.status_code, response.text, "本机"))
            if use_local_only:
                return results
    except Exception as e:
        print(f"  失败: {e}")
    
    # 如果只使用本机，则返回本机结果（无论成功与否）
    if use_local_only:
        return results
    
    # 依次使用每个代理
    for i in range(len(proxy_accounts)):
        proxies = get_proxy_by_index(i)
        print(f"使用代理{i+1}")
        
        try:
            response = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            if response.status_code == 200:
                print("  成功")
                results.append((response.status_code, response.text, f"代理{i+1}"))
            else:
                print(f"  失败: 状态码 {response.status_code}")
        except Exception as e:
            print(f"  失败: {e}")
    
    return results

if __name__ == "__main__":
    url = "https://www.enf.com.cn/4blue?directory=seller&utm_source=ENF&utm_medium=Netherlands&utm_content=84677&utm_campaign=profiles_seller"
    
    # True: 只用本机 False: 本机+代理
    use_local_only =True
    if len(sys.argv) > 1:
        if sys.argv[1].lower() == "true":
            use_local_only = True
        elif sys.argv[1].lower() == "false":
            use_local_only = False
    
    print(f"脚本所在目录: {get_script_dir()}")
    print(f"是否只使用本机连接: {use_local_only}")

    try:
        print(f"正在获取页面: {url}")
        results = fetch_page(url, use_local_only)
        
        # 从URL中提取公司名
        company_name = url.split("/")[-1].split("?")[0]
        
        if results:
            print(f"\n成功获取页面的连接数量: {len(results)}")
            
            # 处理每个成功的结果
            for i, (status_code, page_content, connection_type) in enumerate(results):
                print(f"\n===== 结果 {i+1}/{len(results)} (使用{connection_type}) =====")
                
                # 检查页面是否包含加密邮箱
                if "let eee =" in page_content:
                    print("在页面中找到了加密邮箱标记")
                    # 从页面中提取并解密邮箱
                    email = extract_email_from_script(page_content)
                    if email:
                        print(f"成功提取并解密邮箱: {email}")
                    else:
                        print("无法提取邮箱，正则表达式可能需要调整")
                else:
                    print("页面中没有找到加密邮箱标记")
                    # 提取页面中的一部分内容以便调试
                    email_section = re.search(r'<td itemprop="email"[^>]*>.*?</td>', page_content, re.DOTALL)
                    if email_section:
                        print("\n邮箱相关的HTML片段:")
                        print(email_section.group(0))
                    else:
                        print("未找到邮箱相关的HTML片段")
        else:
            print(f"所有请求均失败，无法获取页面内容")
    except Exception as e:
        print(f"发生错误: {e}")
