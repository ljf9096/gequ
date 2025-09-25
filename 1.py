import os
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class FOFAIPTVFetcher:
    def __init__(self):
        self.email = os.getenv('FOFA_EMAIL')
        self.api_key = os.getenv('FOFA_API_KEY')
        if not all([self.email, self.api_key]):
            raise ValueError("请正确配置.env文件中的FOFA_EMAIL和FOFA_API_KEY")
        
        self.base_url = "https://fofa.info/api/v1/search/all"
        self.session = requests.Session()
        self.timeout = 15
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def build_query(self):
        """构建精准搜索语法"""
        return 'app="iptv/live/zh_cn.js" && region="Guangdong"'

    def fetch_results(self, page=1, size=100):
        """安全获取FOFA数据"""
        query = self.build_query()
        try:
            headers = {
                'User-Agent': self.user_agent
            }
            params = {
                'email': self.email,
                'key': self.api_key,
                'qbase64': base64.b64encode(query.encode()).decode(),
                'size': size,
                'page': page,
                'fields': 'host,ip,port,title,server,protocol'
            }
            resp = self.session.get(
                self.base_url, 
                params=params, 
                headers=headers,
                timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json().get('results', [])
        except requests.exceptions.RequestException as e:
            print(f"API请求失败: {str(e)[:50]}...")
            return []

    def generate_possible_urls(self, host, port, protocol):
        """生成可能的直播源URL"""
        urls = []
        common_paths = [
            '/live.m3u8', '/iptv.m3u8', '/tv.m3u8',
            '/live.txt', '/iptv.txt', '/tv.txt',
            '/zh_cn.js', '/playlist.m3u8',
            '/iptv/index.m3u8', '/tv/index.m3u8'
        ]
        
        # 确定协议
        schemes = []
        if protocol.lower() == 'https':
            schemes = ['https']
        elif protocol.lower() == 'http':
            schemes = ['http']
        else:
            schemes = ['http', 'https']
        
        # 处理端口
        port = str(port) if port else '80'
        if port in ['80', '443']:
            port_part = ''
        else:
            port_part = f':{port}'
        
        for scheme in schemes:
            for path in common_paths:
                url = f"{scheme}://{host}{port_part}{path}"
                urls.append(url)
        
        return urls

    def verify_url(self, url):
        """验证URL有效性"""
        try:
            headers = {
                'User-Agent': self.user_agent,
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            resp = requests.head(
                url, 
                headers=headers,
                timeout=5, 
                allow_redirects=True,
                verify=False
            )
            content_type = resp.headers.get('Content-Type', '').lower()
            return (
                resp.status_code == 200 and 
                any(x in content_type for x in ['m3u', 'javascript', 'plain']) and
                int(resp.headers.get('Content-Length', 0)) > 10
            )
        except:
            return False

    def process_results(self, results):
        """处理结果并返回有效URL"""
        valid_urls = []
        
        for item in results:
            host = item.get('host', '')
            port = item.get('port', '')
            protocol = item.get('protocol', 'http')
            
            if not host:
                continue
                
            possible_urls = self.generate_possible_urls(host, port, protocol)
            
            for url in possible_urls:
                if self.verify_url(url):
                    print(f"发现有效直播源: {url}")
                    valid_urls.append(url)
                    break  # 找到一个有效URL就跳过其他可能性
        
        return list(set(valid_urls))  # 去重

    def save_to_file(self, urls, filename="1.txt"):
        """保存结果到文件"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"# 直播源生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 搜索条件: {self.build_query()}\n")
            f.write("# 格式: 直播源URL\n\n")
            f.write("\n".join(sorted(urls)))

    def run(self, max_pages=2):
        """主执行逻辑"""
        print("开始从FOFA获取直播源...")
        all_valid_urls = []
        
        for page in range(1, max_pages + 1):
            print(f"正在处理第 {page} 页...")
            results = self.fetch_results(page=page)
            if not results:
                print(f"第 {page} 页没有获取到结果")
                break
                
            valid_urls = self.process_results(results)
            all_valid_urls.extend(valid_urls)
            
            # 避免请求过于频繁
            time.sleep(1.5)
        
        if not all_valid_urls:
            print("未找到任何有效直播源")
            return
            
        # 保存结果
        self.save_to_file(all_valid_urls)
        print(f"成功保存 {len(all_valid_urls)} 个直播源到 1.txt")


if __name__ == "__main__":
    # 替换为你的FOFA账号信息
    FOFA_EMAIL = "ljf9096@163.com"
    FOFA_API_KEY = "410522Ljf"
    
    fetcher = FOFAFetcher(FOFA_EMAIL, FOFA_API_KEY)
    fetcher.run()
