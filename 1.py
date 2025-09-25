import requests
import json
import time
import re
from concurrent.futures import ThreadPoolExecutor

class FOFALiveSourceFetcher:
    def __init__(self, email, key):
        self.email = email
        self.key = key
        self.base_url = "https://fofa.info/api/v1/search/all"
        
    def search_live_sources(self):
        """搜索直播源"""
        params = {
            'email': self.email,
            'key': self.key,
            'qbase64': 'InNtYXJ0ZGVza3RvcCBpcHR2L2xpdmUvemhfY24uanMiICYmIHJlZ2lvbj0iR3Vhbmdkb25nIg==',  # 编码后的查询条件
            'fields': 'ip,port,protocol,host,title,lastupdatetime',
            'size': 1000  # 获取较多结果用于筛选
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API请求失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def test_live_source_speed(self, host, protocol='http'):
        """测试直播源响应时间"""
        test_urls = [
            f"{protocol}://{host}/live/zh_cn.js",
            f"{protocol}://{host}/iptv/live/zh_cn.js",
            f"{protocol}://{host}/live/tv.txt",
            f"{protocol}://{host}/iptv/tv.txt"
        ]
        
        for url in test_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5, stream=True)
                response_time = (time.time() - start_time) * 1000  # 转换为毫秒
                
                if response.status_code == 200:
                    # 检查内容是否包含央视卫视频道
                    content = response.text
                    if self.is_valid_live_source(content):
                        return url, response_time
            except:
                continue
        
        return None, float('inf')
    
    def is_valid_live_source(self, content):
        """验证是否为有效的直播源内容"""
        # 检查是否包含央视卫视关键字
        cctv_keywords = ['CCTV', '央视', '中央']
        satellite_keywords = ['卫视', '湖南卫视', '浙江卫视', '江苏卫视', '北京卫视']
        
        has_cctv = any(keyword in content for keyword in cctv_keywords)
        has_satellite = any(keyword in content for keyword in satellite_keywords)
        
        return has_cctv or has_satellite
    
    def extract_channel_urls(self, content, base_url):
        """从内容中提取频道URL"""
        urls = []
        
        # 匹配常见的直播源格式
        patterns = [
            r'([^,\n]+\.m3u8[^,\n]*)',
            r'([^,\n]+\.flv[^,\n]*)',
            r'([^,\n]+\?auth[^,\n]*)',
            r'(http[^,\n]+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                if match.startswith('http'):
                    urls.append(match)
                else:
                    # 相对路径转绝对路径
                    if not match.startswith('/'):
                        match = '/' + match
                    urls.append(base_url + match)
        
        return list(set(urls))  # 去重
    
    def get_top_live_sources(self):
        """获取响应时间最短的前5个直播源"""
        print("正在搜索FOFA直播源...")
        result = self.search_live_sources()
        
        if not result or 'results' not in result:
            print("未找到直播源或API请求失败")
            return []
        
        print(f"找到 {len(result['results'])} 个潜在直播源")
        
        # 测试响应时间
        live_sources = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for item in result['results']:
                host = item.get('host') or item.get('ip')
                if host:
                    futures.append(executor.submit(self.test_live_source_speed, host))
            
            for i, future in enumerate(futures):
                url, response_time = future.result()
                if url and response_time < float('inf'):
                    live_sources.append((url, response_time))
                print(f"测试进度: {i+1}/{len(futures)}")
        
        # 按响应时间排序，取前5个
        live_sources.sort(key=lambda x: x[1])
        return live_sources[:5]
    
    def save_to_file(self, live_sources, filename='1.txt'):
        """保存到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 央视卫视直播源 - 响应时间最短前5个\n")
            f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 格式: 频道名称,直播地址,响应时间(ms)\n\n")
            
            for i, (url, response_time) in enumerate(live_sources, 1):
                # 尝试获取频道名称
                channel_name = self.guess_channel_name(url)
                f.write(f"{channel_name},{url},{response_time:.2f}ms\n")
        
        print(f"直播源已保存到 {filename}")

    def guess_channel_name(self, url):
        """根据URL猜测频道名称"""
        if 'cctv' in url.lower():
            return '央视综合'
        elif 'weishi' in url.lower() or 'satellite' in url.lower():
            return '卫视综合'
        else:
            return '直播频道'

# 使用示例
if __name__ == "__main__":
    # 需要替换为你的FOFA账号信息
    FOFA_EMAIL = "ljf9096@example.com"  # 替换为你的FOFA邮箱
    FOFA_KEY = "410522Ljf"         # 替换为你的FOFA API Key
    
    fetcher = FOFALiveSourceFetcher(FOFA_EMAIL, FOFA_KEY)
    
    print("开始获取直播源...")
    top_sources = fetcher.get_top_live_sources()
    
    if top_sources:
        print("\n找到的前5个直播源:")
        for i, (url, response_time) in enumerate(top_sources, 1):
            print(f"{i}. {url} - {response_time:.2f}ms")
        
        fetcher.save_to_file(top_sources, '1.txt')
        print("\n任务完成！")
    else:
        print("未找到有效的直播源")
