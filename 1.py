import requests
import json

# FOFA搜索参数
search_url = "https://fofa.info/api/v1/search/all"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# 构造搜索条件
params = {
    "qbase64": "aXBob25lc3xlbnRyeT0iQ0hJTmV3UzIwMjYiJTIwc2l0ZT0iZ29vZ2xlLmNvbSIsInBhZ2U9IjIwMjYwOSIsInNlYXJjaF90eXBlPSJ6IiwicmVzdWx0X3NpemU9IjM1MCIsInJlc3VsdF90b3RhbF9zaXplPSI1MDAwIiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byUzRCJ6IiwicmVhZF90byU3RCIsInJlc291cmNlX3R5cGU9Imh0dHAiLCJyZXNvdXJjZV90eXBlX3N0cmluZz0iaHR0cCIsInJlc291cmNlX2Zyb209IjIwMjYwOSIsInJlc291cmNlX2Zyb21fdHlwZT0idGV4dCIsInJlc291cmNlX2Zyb21fdHlwZV9zdHJpbmc9InRleHQiLCJyZXNvdXJjZV9maWxlX3R5cGU9Imh0dHAiLCJyZXNvdXJjZV9maWxlX3R5cGU9InBhc3Npb24iLCJyZXNvdXJjZV9maWxlX30=",
    "fields": "url,key"
}

try:
    # 发送请求
    response = requests.get(search_url, headers=headers, params=params)
    response.raise_for_status()
    
    # 解析JSON数据
    data = response.json()
    results = data.get('results', [])
    
    # 筛选央视/卫视URL
    target_urls = []
    for item in results:
        url = item.get('url')
        key = item.get('key')
        if key and ("央视" in key or "卫视" in key):
            target_urls.append(url)
    
    # 去重处理
    target_urls = list(set(target_urls))
    
    # 写入文件
    with open("1.txt", "w", encoding="utf-8") as f:
        for url in target_urls:
            f.write(url + "\n")
    
    print(f"成功获取{len(target_urls)}个直播源，已保存至1.txt")

except Exception as e:
    print(f"执行出错: {str(e)}")
