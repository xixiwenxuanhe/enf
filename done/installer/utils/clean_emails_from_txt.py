#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
from collections import Counter

EXCLUDE_EXTENSIONS = [
    "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "tiff", "ico", "pdf", "doc",
    "docx", "xls", "xlsx", "ppt", "pptx", "zip", "rar", "tar", "gz", "mp3", "mp4",
    "avi", "mov", "wmv", "flv", "wav", "ogg", "webm",
]

VALID_TLDS = [
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz", "name",
    "pro", "museum", "coop", "aero", "xxx", "idv", "me", "mobi", "asia", "tel",
    "eu", "de", "uk", "fr", "it", "es", "nl", "ru", "cn", "jp", "kr", "au", "nz",
    "ca", "us", "mx", "br", "ch", "at", "be", "dk", "fi", "gr", "ie", "no", "pt",
    "se", "cat", "pl", "cz", "hu", "ro", "si", "tr", "co", "io", "ai", "app", "dev",
    "xyz", "online", "tech", "shop", "store", "site", "website", "blog", "cloud",
]

BLACKLIST_KEYWORDS = [
    "2x", "3x", "scaled", "copy", "copia", "mesa-de-trabajo", "icon", "logo", "banner", "header", "footer", "background", "image", "img", "photo", "picture", "avatar", "profile", "thumb", "thumbnail", "slide", "slide-", "@2x", "@3x", "-copy", "-scaled", "-copia", "-icon", "-logo", "-banner", "-header", "-footer", "-background", "-image", "-img", "-photo", "-picture", "-avatar", "-profile", "-thumb", "-thumbnail", "-slide",
]

PREFIX_KEYWORDS = [
    "info", "hola", "admin", "contact", "mail", "office", "web", "hello", "servicio", "ventas", "support", "service"
]

def filter_email(email: str) -> str:
    if not isinstance(email, str) or not email:
        return ""
    email = email.strip()
    # 增强前缀去除，支持所有常见email拼写
    email = re.sub(r'^(e[-_ ]?mail)[_\-\. ]*', '', email, flags=re.I)
    email_lower = email.lower()
    # 优化关键词截断逻辑
    at_pos = email.find('@')
    if at_pos > 0:
        username = email[:at_pos]
        domain = email[at_pos+1:]
        
        # 修改后的PREFIX_KEYWORDS处理逻辑，只有关键词出现在用户名开头时才处理
        username_lower = username.lower()
        for kw in PREFIX_KEYWORDS:
            kw_lower = kw.lower()
            # 只检查关键词是否在用户名开头
            if username_lower.startswith(kw_lower):
                # 如果关键词就是整个用户名，则不处理
                if len(username) > len(kw):
                    username = username[len(kw):]
                    email = username + '@' + domain
                    email_lower = email.lower()
                break
            
    tld_pattern = r"|".join([fr"\\.{tld}" for tld in VALID_TLDS])
    tld_regex = re.compile(fr"(@[^@]+?({tld_pattern}))", re.I)
    match = tld_regex.search(email)
    if match:
        tld_end = match.end(2)
        at_pos = email.find('@')
        email = email[:at_pos + tld_end - match.start(1)]
    m = re.search(r'([\w\.-]+)@([\w\.-]+\.[a-zA-Z]{2,})', email)
    if not m:
        return ""
    username, domain = m.group(1), m.group(2)

    # 修正：从左到右找到所有数字且其左侧没有任何字母，最终只截断到最右侧（最后一个）满足条件的数字
    cut_idx = None
    for i, c in enumerate(username):
        if c.isdigit() and not any(ch.isalpha() for ch in username[:i]):
            cut_idx = i
    if cut_idx is not None:
        username = username[cut_idx:]

    # # @前面没有点：根据测试，不合理
    # if '.' in username:
    #     username = username.split('.')[-1]

    # @后面只一个点，根据测试，不合理
    # if domain.count('.') > 1:
    #     first_dot = domain.find('.')
    #     domain = domain[first_dot:]
    #     # 去掉开头的点
    #     if domain.startswith('.'):
    #         domain = domain[1:]

    # 数字开头，修改为匹配任意数量的数字（1个或多个）
    m2 = re.match(r'^(\d+)([a-zA-Z].*)$', username)
    if m2:
        username = m2.group(2)
    for ext in EXCLUDE_EXTENSIONS:
        if domain.lower().endswith('.' + ext) or email.lower().endswith('.' + ext):
            return ""
    uname_lower = username.lower()
    domain_lower = domain.lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in uname_lower or kw in domain_lower:
            return ""
    if not any(domain.lower().endswith('.' + tld) for tld in VALID_TLDS):
        return ""
    if not (2 <= len(username) <= 64):
        return ""
    return f"{username}@{domain}"

def is_static_resource(email: str) -> bool:
    if not isinstance(email, str) or not email:
        return False
    email = email.strip().lower()
    for ext in EXCLUDE_EXTENSIONS:
        if email.endswith('.' + ext):
            return True
    return False

def process_email(email: str) -> tuple[str, str]:
    """
    处理邮箱地址，返回处理后的邮箱和原始邮箱
    
    Args:
        email: 原始邮箱字符串
        
    Returns:
        tuple: (处理后的邮箱, 原始邮箱). 如果处理后的邮箱无效，则第一个元素为空字符串
    """
    if not isinstance(email, str) or not email:
        return "", email
        
    email = email.strip()
    
    # 检查是否为静态资源
    if is_static_resource(email):
        return "", email
        
    # 过滤和清理邮箱
    filtered_email = filter_email(email)
    return filtered_email, email

def main():
    input_file = os.path.join(os.path.dirname(__file__), 'extracted_emails.txt')
    output_file = os.path.join(os.path.dirname(__file__), 'cleaned_emails.txt')
    if not os.path.exists(input_file):
        print(f"错误: 未找到输入文件 {input_file}")
        return
        
    cleaned_emails = []
    with open(input_file, 'r', encoding='utf-8') as fin, \
         open(output_file, 'w', encoding='utf-8') as fout:
        total = 0
        for line in fin:
            total += 1
            filtered_email, original_email = process_email(line.strip())
            fout.write(f"{filtered_email}{'        '}{original_email}\n" if filtered_email else f"{'        '}{original_email}\n")
            cleaned_emails.append(filtered_email)
            
    print(f"处理完成，共处理 {total} 行，结果已保存到 {output_file}")
    
    # 统计并输出重复邮箱
    email_counter = Counter([e for e in cleaned_emails if e])
    duplicates = [email for email, count in email_counter.items() if count > 1]
    if duplicates:
        print("以下邮箱在结果中有重复：")
        for email in duplicates:
            print(email)
    else:
        print("结果中没有重复邮箱。")

if __name__ == "__main__":
    main() 