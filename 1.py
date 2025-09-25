import requests
import json
import base64
import time
import re

class FOFAScraper:
    def __init__(self, email, key):
        self.email = email
        self.key = key
        self.base_url = "https://fofa.info/api/v1/search/all"
        
    def build_query(self):
        """构建FOFA查询语句"""
        query = 'body="iptv/live/zh_cn.js" && region="Guangdong"'
        return base64.b64encode(query.encode()).decode()
    
    def search_fofa(self, page=1, size=100):
        """搜索FOFA数据"""
        params = {
            'email': self.email,
            'key': self.key,
            'qbase64': self.build_query(),
            'page': page,
            'size': size,
            'fields': 'ip,port,host,title'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"请求失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"请求异常: {e}")
            return None
    
    def extract_live_sources(self, results):
        """从结果中提取直播源"""
        live_sources = []
        
        if not results or 'results' not in results:
            return live_sources
        
        for item in results['results']:
            ip = item[0] if len(item) > 0 else ''
            port = item[1] if len(item) > 1 else ''
            host = item[2] if len(item) > 2 else ''
            
            # 尝试多种可能的直播源URL模式
            base_urls = self.generate_base_urls(ip, port, host)
            
            for base_url in base_urls:
                sources = self.get_live_sources_from_url(base_url)
                if sources:
                    live_sources.extend(sources)
                    break  # 如果从一个URL获取成功，就不尝试其他URL
        
        return live_sources
    
    def generate_base_urls(self, ip, port, host):
        """生成可能的直播源基础URL"""
        urls = []
        
        # 基于host生成URL
        if host and host not in ['', 'null']:
            if not host.startswith('http'):
                host = f"http://{host}"
            urls.append(f"{host}/iptv/live/zh_cn.js")
            urls.append(f"{host}/live/zh_cn.js")
            urls.append(f"{host}/zh_cn.js")
        
        # 基于IP和端口生成URL
        if ip and ip not in ['', 'null']:
            if port and port not in ['', 'null', '0']:
                base = f"http://{ip}:{port}"
            else:
                base = f"http://{ip}"
            
            urls.extend([
                f"{base}/iptv/live/zh_cn.js",
                f"{base}/live/zh_cn.js",
                f"{base}/zh_cn.js",
                f"{base}/iptv/live/1000.json?key=tott",
                f"{base}/live/1000.json?key=tott"
            ])
        
        return urls
    
    def get_live_sources_from_url(self, url):
        """从具体URL获取直播源"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return self.parse_live_sources(response.text, url)
                
        except Exception as e:
            print(f"获取 {url} 失败: {e}")
        
        return []
    
    def parse_live_sources(self, content, base_url):
        """解析直播源内容"""
        sources = []
        base_domain = '/'.join(base_url.split('/')[:3])
        
        # 匹配JavaScript中的频道数据
        patterns = [
            r'channelName["\']?\s*:\s*["\']([^"\']+)["\'][^}]*?url["\']?\s*:\s*["\']([^"\']+)["\']',
            r'{"channelName":"([^"]+)","url":"([^"]+)"}',
            r'name["\']?\s*:\s*["\']([^"\']+)["\'][^}]*?url["\']?\s*:\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                channel_name, url = match
                if self.is_cctv_or_satellite(channel_name):
                    # 处理相对URL
                    if url.startswith('/'):
                        full_url = base_domain + url
                    elif not url.startswith('http'):
                        full_url = base_domain + '/' + url
                    else:
                        full_url = url
                    
                    sources.append(f"{channel_name},{full_url}")
        
        return sources
    
    def is_cctv_or_satellite(self, channel_name):
        """判断是否为央视或卫视频道"""
        cctv_keywords = ['CCTV', '央视', '中央']
        satellite_keywords = ['卫视', 'TV', '电视台']
        
        channel_lower = channel_name.upper()
        
        # 央视频道
        if any(keyword in channel_name for keyword in cctv_keywords):
            return True
        
        # 卫视频道
        if any(keyword in channel_name for keyword in satellite_keywords):
            # 排除一些非电视节目
            exclude_words = ['信息', '数据', '监控']
            if not any(word in channel_name for word in exclude_words):
                return True
        
        return False
    
    def save_to_file(self, sources, filename='1.txt'):
        """保存直播源到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("# 央视卫视直播源\n")
            f.write("# 更新时间: " + time.strftime("%Y-%m-%d %H:%M:%S") + "\n\n")
            
            # 分类保存
            cctv_sources = [s for s in sources if any(kw in s for kw in ['CCTV', '央视', '中央'])]
            satellite_sources = [s for s in sources if s not in cctv_sources]
            
            if cctv_sources:
                f.write("# 央视频道\n")
                for source in cctv_sources:
                    f.write(source + "\n")
                f.write("\n")
            
            if satellite_sources:
                f.write("# 卫视频道\n")
                for source in satellite_sources:
                    f.write(source + "\n")
        
        print(f"成功保存 {len(sources)} 个直播源到 {filename}")

def main():
    # 需要配置您的FOFA账号信息
    FOFA_EMAIL = "your_fofa_email@example.com"  # 替换为您的FOFA邮箱
    FOFA_KEY = "your_fofa_api_key"  # 替换为您的FOFA API Key
    
    if FOFA_EMAIL == "your_fofa_email@example.com":
        print("请先配置FOFA账号信息！")
        return
    
    scraper = FOFAScraper(FOFA_EMAIL, FOFA_KEY)
    
    print("开始搜索FOFA数据...")
    results = scraper.search_fofa(page=1, size=100)
    
    if not results:
        print("未获取到数据，请检查网络连接和API配置")
        return
    
    print(f"获取到 {len(results.get('results', []))} 条记录")
    
    print("提取直播源...")
    live_sources = scraper.extract_live_sources(results)
    
    if live_sources:
        print(f"成功提取 {len(live_sources)} 个直播源")
        scraper.save_to_file(live_sources, '1.txt')
        
        # 打印部分结果预览
        print("\n前10个直播源预览:")
        for i, source in enumerate(live_sources[:10]):
            print(f"{i+1}. {source}")
    else:
        print("未提取到有效的直播源")

if __name__ == "__main__":
    main()
