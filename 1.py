import requests
from bs4 import BeautifulSoup
import re

# 1. 模拟FOFA资产页面请求（需替换实际Cookie与资产IP）
fofa_cookie = "your_fofa_cookie"  # 从浏览器F12开发者工具获取
target_ip = "192.168.1.100"  # FOFA筛选出的广东地区IPTV资产IP
js_url = f"http://{target_ip}/iptv/live/zh_cn.js"  # 目标JS文件路径

headers = {
    "Cookie": fofa_cookie,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
}

# 2. 下载并解析JS文件提取URL
response = requests.get(js_url, headers=headers, timeout=10)
response.encoding = "utf-8"
js_content = response.text

# 匹配央视、卫视URL（适配http/rtmp协议，含频道关键词）
url_pattern = r'(http|rtmp)://[^\s,"]+(CCTV\d+|GuangdongTV|HunanTV|ZhejiangTV|JiangsuTV|卫视|央视)[^\s,"]*'
matched_urls = re.findall(url_pattern, js_content, re.IGNORECASE)

# 提取纯URL（过滤正则匹配的分组元素）
valid_urls = [url[0] + "://" + url[1] for url in matched_urls]

# 3. 去重并写入1.txt文件
unique_urls = list(set(valid_urls))  # 去除重复URL
with open("1.txt", "w", encoding="utf-8") as f:
    for url in unique_urls:
        f.write(url + "\n")

print(f"成功提取{len(unique_urls)}条有效URL，已保存至1.txt")
