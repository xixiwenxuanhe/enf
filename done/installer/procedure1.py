import re
import pandas as pd
import argparse

# 合法TLD列表
VALID_TLDS = [
    "com", "net", "org", "edu", "gov", "mil", "int", "info", "biz", "name",
    "pro", "museum", "coop", "aero", "xxx", "idv", "me", "mobi", "asia", "tel",
    "eu", "de", "uk", "fr", "it", "es", "nl", "ru", "cn", "jp", "kr", "au", "nz",
    "ca", "us", "mx", "br", "ch", "at", "be", "dk", "fi", "gr", "ie", "no", "pt",
    "se", "cat", "pl", "cz", "hu", "ro", "si", "tr", "co", "io", "ai", "app", "dev",
    "xyz", "online", "tech", "shop", "store", "site", "website", "blog", "cloud",
]

# 静态资源后缀
EXCLUDE_EXTENSIONS = [
    "png", "jpg", "jpeg", "gif", "webp", "svg", "bmp", "tiff", "ico", "pdf", "doc",
    "docx", "xls", "xlsx", "ppt", "pptx", "zip", "rar", "tar", "gz", "mp3", "mp4",
    "avi", "mov", "wmv", "flv", "wav", "ogg", "webm",
]

# 黑名单关键词
BLACKLIST_KEYWORDS = [
    "2x", "3x", "scaled", "copy", "copia", "mesa-de-trabajo", "icon", "logo", "banner", "header", "footer", "background", "image", "img", "photo", "picture", "avatar", "profile", "thumb", "thumbnail", "slide", "slide-", "@2x", "@3x", "-copy", "-scaled", "-copia", "-icon", "-logo", "-banner", "-header", "-footer", "-background", "-image", "-img", "-photo", "-picture", "-avatar", "-profile", "-thumb", "-thumbnail", "-slide",
]

# 前缀截断关键词
PREFIX_KEYWORDS = [
    "info", "hola", "admin", "contact", "mail", "office", "web", "hello", "servicio", "ventas", "support", "service"
]

def filter_email(email: str) -> str:
    if not isinstance(email, str) or not email:
        return ""
    email = email.strip()
    # 1. 去除 email/e-mail 前缀
    email = re.sub(r'^(email|e-mail)[_\-\.]?', '', email, flags=re.I)
    email_lower = email.lower()
    # 2. 多关键词前缀截断
    for kw in PREFIX_KEYWORDS:
        idx = email_lower.find(kw + "@")
        if idx > 0:
            email = email[idx:]
            email_lower = email_lower[idx:]
            break
    # 3. 合法TLD后截断
    tld_pattern = r"|".join([fr"\.{tld}" for tld in VALID_TLDS])
    tld_regex = re.compile(fr"(@[^@]+?({tld_pattern}))", re.I)
    match = tld_regex.search(email)
    if match:
        tld_end = match.end(2)
        at_pos = email.find('@')
        email = email[:at_pos + tld_end - match.start(1)]
    # 4. 标准邮箱格式提取
    m = re.match(r'([\w\.-]+)@([\w\.-]+\.[a-zA-Z]{2,})', email)
    if not m:
        return ""
    username, domain = m.group(1), m.group(2)
    # 5. 用户名点分割前缀去除
    if '.' in username:
        username = username.split('.')[-1]
    # 6. 数字前缀去除
    m2 = re.match(r'^(\d{2,})([a-zA-Z].*)$', username)
    if m2:
        username = m2.group(2)
    # 7. 静态资源后缀过滤
    for ext in EXCLUDE_EXTENSIONS:
        if domain.lower().endswith('.' + ext) or email.lower().endswith('.' + ext):
            return ""
    # 8. 黑名单关键词过滤
    uname_lower = username.lower()
    domain_lower = domain.lower()
    for kw in BLACKLIST_KEYWORDS:
        if kw in uname_lower or kw in domain_lower:
            return ""
    # 9. 合法TLD校验
    if not any(domain.lower().endswith('.' + tld) for tld in VALID_TLDS):
        return ""
    # 10. 长度与格式校验
    if not (2 <= len(username) <= 64):
        return ""
    return f"{username}@{domain}"

def process_csv(input_path, output_path, email_col=None):
    df = pd.read_csv(input_path)
    # 自动检测邮箱列
    if email_col is None:
        for col in df.columns:
            if 'email' in col.lower():
                email_col = col
                break
    if email_col is None:
        raise ValueError('未检测到邮箱列，请指定 --email_col')
    df['filtered_email'] = df[email_col].apply(filter_email)
    df.to_csv(output_path, index=False)
    print(f"已处理：{input_path}，输出：{output_path}")

def main():
    parser = argparse.ArgumentParser(description='批量邮箱过滤分析工具')
    parser.add_argument('--input', required=True, help='输入CSV文件路径')
    parser.add_argument('--output', required=True, help='输出CSV文件路径')
    parser.add_argument('--email_col', default=None, help='邮箱列名（可选，自动检测）')
    args = parser.parse_args()
    process_csv(args.input, args.output, args.email_col)

if __name__ == '__main__':
    main() 