import requests
import base64
import json
import time
import re

class FOFALiveSourceExtractor:
    def __init__(self, email, key):
        self.email = email
        self.key = key
        self.base_url = "https://fofa.info/api/v1/search/all"
        
    def encode_query(self, query):
        """编码查询条件为base64"""
        return base64.b64encode(query.encode()).decode()
    
    def search_live_sources(self):
        """搜索直播源"""
        # 编码查询条件
        query = '"smartdesktop iptv/live/zh_cn.js" && region="Guangdong"'
        encoded_query = self.encode_query(query)
        
        params = {
            'email': self.email,
            'key': self.key,
            'qbase64': encoded_query,
            'fields': 'ip,port,host,title,protocol,lastupdatetime',
            'size': 100,  # 获取100条结果
            'full': 'false'
        }
        
        try:
            print("正在查询FOFA平台...")
            response = requests.get(self.base_url, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                print(f"查询成功，找到 {len(data['results'])} 条结果")
                return data
            else:
                print(f"API请求失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def extract_live_urls(self, host, protocol='http'):
        """从主机提取直播URL"""
        live_urls = []
        
        # 可能的直播源路径
        paths = [
            '/iptv/live/zh_cn.js',
            '/live/zh_cn.js',
            '/iptv/tv.txt',
            '/live/tv.txt',
            '/tv.txt',
            '/iptv.m3u',
            '/live.m3u'
        ]
        
        for path in paths:
            url = f"{protocol}://{host}{path}"
            if self.test_url_accessibility(url):
                live_urls.append(url)
        
        return live_urls
    
    def test_url_accessibility(self, url):
        """测试URL可访问性"""
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                # 检查内容是否包含直播相关信息
                content = response.text.lower()
                if any(keyword in content for keyword in ['cctv', '卫视', '电视台', 'm3u8', '.ts']):
                    return True
            return False
        except:
            return False
    
    def get_channel_urls(self, content, base_url):
        """从内容中提取具体的频道URL"""
        urls = []
        
        # 匹配M3U8格式
        m3u8_pattern = r'([^"\'\s]+\.m3u8[^"\'\s]*)'
        m3u8_matches = re.findall(m3u8_pattern, content)
        
        # 匹配FLV格式
        flv_pattern = r'([^"\'\s]+\.flv[^"\'\s]*)'
        flv_matches = re.findall(flv_pattern, content)
        
        # 匹配其他视频流格式
        stream_pattern = r'(http[^"\'\s]+\.(ts|m3u8|flv)[^"\'\s]*)'
        stream_matches = re.findall(stream_pattern, content)
        
        all_matches = m3u8_matches + flv_matches + [match[0] for match in stream_matches]
        
        for match in set(all_matches):  # 去重
            if match.startswith('http'):
                urls.append(match)
            else:
                # 处理相对路径
                if not match.startswith('/'):
                    match = '/' + match
                full_url = base_url.rsplit('/', 1)[0] + match
                urls.append(full_url)
        
        return urls
    
    def filter_cctv_satellite_urls(self, urls):
        """过滤出央视和卫视的URL"""
        cctv_keywords = ['cctv', '央视', '中央']
        satellite_keywords = ['卫视', '湖南', '浙江', '江苏', '北京', '上海', '东方']
        
        filtered_urls = []
        
        for url in urls:
            url_lower = url.lower()
            # 检查是否包含央视或卫视关键词
            has_cctv = any(keyword in url_lower for keyword in cctv_keywords)
            has_satellite = any(keyword in url_lower for keyword in satellite_keywords)
            
            if has_cctv or has_satellite:
                filtered_urls.append(url)
        
        return filtered_urls
    
    def process_results(self):
        """处理查询结果并提取直播源"""
        results = self.search_live_sources()
        if not results or 'results' not in results:
            print("未找到相关直播源")
            return []
        
        all_live_urls = []
        
        for item in results['results']:
            host = item.get('host') or item.get('ip')
            if not host:
                continue
                
            # 添加端口信息
            port = item.get('port', '')
            if port and port not in ['80', '443']:
                host = f"{host}:{port}"
            
            print(f"处理主机: {host}")
            
            # 尝试HTTP和HTTPS
            for protocol in ['http', 'https']:
                live_urls = self.extract_live_urls(host, protocol)
                if live_urls:
                    all_live_urls.extend(live_urls)
                    print(f"  找到 {len(live_urls)} 个直播源")
                    break
        
        # 过滤出央视和卫视URL
        cctv_satellite_urls = self.filter_cctv_satellite_urls(all_live_urls)
        
        # 去重
        unique_urls = list(set(cctv_satellite_urls))
        
        print(f"\n总共找到 {len(unique_urls)} 个央视卫视直播源")
        return unique_urls
    
    def save_to_file(self, urls, filename='1.txt'):
        """保存URL到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 央视卫视直播源列表\n")
            f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 数据来源: FOFA平台\n")
            f.write(f"# 查询条件: smartdesktop iptv/live/zh_cn.js && region=Guangdong\n\n")
            
            for i, url in enumerate(urls, 1):
                f.write(f"{url}\n")
        
        print(f"直播源已保存到 {filename}")

def main():
    # 需要替换为您的FOFA账号信息
    FOFA_EMAIL = "ljf9096@163.com"  # 替换为您的FOFA邮箱
    FOFA_KEY = "410522Ljf"         # 替换为您的FOFA API Key
    
    # 如果不想在代码中硬编码，可以从环境变量或输入获取
    # import os
    # FOFA_EMAIL = os.getenv('FOFA_EMAIL', 'your_email@example.com')
    # FOFA_KEY = os.getenv('FOFA_KEY', 'your_fofa_api_key')
    
    if FOFA_EMAIL == "your_email@example.com" or FOFA_KEY == "your_fofa_api_key":
        print("请先配置FOFA账号信息！")
        print("1. 修改代码中的FOFA_EMAIL和FOFA_KEY变量")
        print("2. 或设置环境变量FOFA_EMAIL和FOFA_KEY")
        return
    
    extractor = FOFALiveSourceExtractor(FOFA_EMAIL, FOFA_KEY)
    
    print("开始从FOFA平台提取直播源...")
    live_urls = extractor.process_results()
    
    if live_urls:
        print("\n找到的直播源:")
        for i, url in enumerate(live_urls, 1):
            print(f"{i}. {url}")
        
        extractor.save_to_file(live_urls, '1.txt')
        print(f"\n成功保存 {len(live_urls)} 个直播源到 1.txt")
    else:
        print("未找到有效的直播源")

if __name__ == "__main__":
    main()
