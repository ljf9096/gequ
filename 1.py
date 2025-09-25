import requests
import base64
import time
from datetime import datetime

class FOFAFetcher:
    def __init__(self, email, api_key):
        self.email = email
        self.api_key = api_key
        self.base_url = "https://fofa.info/api/v1/search/all"
        self.session = requests.Session()
        self.live_sources = []

    def build_query(self):
        """构建FOFA搜索语法"""
        queries = [
            'title="直播"',
            'title="IPTV"',
            'title="电视"',
            'body="直播"',
            'body="m3u8"',
            'body=".m3u"',
            'header="m3u"',
            'protocol="m3u"',
            'port="80" && body="电视"',
            'port="8080" && body="直播"'
        ]
        return ' || '.join(queries)

    def fetch_from_fofa(self, page=1, size=100):
        """从FOFA获取直播源数据"""
        query = self.build_query()
        query_base64 = base64.b64encode(query.encode()).decode()

        params = {
            'email': self.email,
            'key': self.api_key,
            'qbase64': query_base64,
            'size': size,
            'page': page,
            'fields': 'host,ip,port,title,server,country,city'
        }

        try:
            response = self.session.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error'):
                print(f"FOFA API错误: {data['errmsg']}")
                return []
            
            return data.get('results', [])
            
        except Exception as e:
            print(f"从FOFA获取数据失败: {e}")
            return []

    def extract_live_urls(self, results):
        """从FOFA结果中提取直播源URL"""
        live_urls = []
        common_paths = [
            '/live.m3u', '/tv.m3u', '/iptv.m3u',
            '/live.txt', '/tv.txt', '/iptv.txt',
            '/live', '/tv', '/iptv',
            '/m3u', '/txt', '/playlist.m3u'
        ]

        for result in results:
            host = result.get('host', '')
            port = str(result.get('port', ''))
            title = result.get('title', '').lower()

            if not host:
                continue

            # 尝试常见协议和路径组合
            schemes = ['http', 'https']
            for scheme in schemes:
                for path in common_paths:
                    # 如果端口是80或443，可以省略
                    if port in ['80', '443']:
                        url = f"{scheme}://{host}{path}"
                    else:
                        url = f"{scheme}://{host}:{port}{path}"
                    
                    if self.check_url(url):
                        live_urls.append(url)
                        print(f"发现可用直播源: {url}")
        
        return list(set(live_urls))  # 去重

    def check_url(self, url):
        """检查URL是否可访问"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            return response.status_code == 200 and ('m3u' in content_type or 'text/plain' in content_type)
        except:
            return False

    def get_live_content(self, url):
        """获取直播源内容"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"获取直播内容失败 {url}: {e}")
            return ""

    def save_to_file(self, filename="1.txt"):
        """将直播源保存到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 直播源收集时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# 数据来源: FOFA\n")
            f.write("# 格式: 频道名称,URL\n\n")
            
            for source in self.live_sources:
                f.write(f"{source}\n")
        
        print(f"直播源已保存到 {filename}")

    def run(self, max_pages=3):
        """主运行方法"""
        print("开始从FOFA搜索直播源...")
        
        for page in range(1, max_pages + 1):
            print(f"正在处理第 {page} 页...")
            results = self.fetch_from_fofa(page=page)
            live_urls = self.extract_live_urls(results)
            
            for url in live_urls:
                content = self.get_live_content(url)
                if content:
                    # 简单处理M3U格式
                    if content.startswith('#EXTM3U'):
                        lines = content.split('\n')
                        for line in lines:
                            if line.startswith('#EXTINF'):
                                channel_name = line.split(',')[-1].strip()
                            elif line.startswith(('http', 'rtmp')):
                                self.live_sources.append(f"{channel_name},{line.strip()}")
                    else:
                        # 处理普通文本格式
                        for line in content.split('\n'):
                            if ',' in line and '://' in line:
                                self.live_sources.append(line.strip())
            
            # 避免请求过于频繁
            time.sleep(2)
        
        # 去重
        self.live_sources = list(set(self.live_sources))
        print(f"共找到 {len(self.live_sources)} 个直播源")
        
        # 保存到文件
        self.save_to_file()

if __name__ == "__main__":
    # 替换为你的FOFA账号信息
    FOFA_EMAIL = "ljf9096@163.com"
    FOFA_API_KEY = "410522Ljf"
    
    fetcher = FOFAFetcher(FOFA_EMAIL, FOFA_API_KEY)
    fetcher.run()
