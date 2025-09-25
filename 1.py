import requests
import json
import base64
import time
from typing import List, Dict

class FofaLiveSourceExtractor:
    def __init__(self, email: str, key: str):
        """
        初始化FOFA API客户端
        
        Args:
            email: FOFA账号邮箱
            key: FOFA API Key
        """
        self.email = email
        self.key = key
        self.base_url = "https://fofa.info/api/v1/search/all"
        
    def build_query(self) -> str:
        """构建FOFA查询语句"""
        query = '\"iptv/live/zh_cn.js\" && region=\"Guangdong\"'
        return base64.b64encode(query.encode()).decode()
    
    def search_live_sources(self, page: int = 1, size: int = 100) -> Dict:
        """
        搜索直播源
        
        Args:
            page: 页码
            size: 每页数量
            
        Returns:
            API响应数据
        """
        params = {
            'email': self.email,
            'key': self.key,
            'qbase64': self.build_query(),
            'page': page,
            'size': size,
            'fields': 'ip,port,host,title,country,city,domain,server,os'
        }
        
        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None
    
    def extract_live_urls(self, results: List) -> List[str]:
        """
        从搜索结果中提取直播源URL
        
        Args:
            results: FOFA搜索结果
            
        Returns:
            直播源URL列表
        """
        live_urls = []
        
        for result in results:
            # 根据不同的结果格式提取URL
            if 'host' in result and result['host']:
                base_url = f"http://{result['host']}"
            elif 'ip' in result and result['ip']:
                port = result.get('port', '80')
                base_url = f"http://{result['ip']}:{port}"
            else:
                continue
            
            # 构建可能的直播源路径
            possible_paths = [
                "/iptv/live/zh_cn.js",
                "/live/zh_cn.js",
                "/zh_cn.js",
                "/iptv/live.js",
                "/live.js"
            ]
            
            for path in possible_paths:
                live_url = base_url + path
                live_urls.append(live_url)
        
        return live_urls
    
    def get_js_content(self, url: str) -> str:
        """
        获取JavaScript文件内容
        
        Args:
            url: JS文件URL
            
        Returns:
            JS文件内容
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            return response.text
        except:
            return None
    
    def parse_js_for_sources(self, js_content: str) -> List[str]:
        """
        从JavaScript内容中解析直播源
        
        Args:
            js_content: JavaScript内容
            
        Returns:
            直播源列表
        """
        sources = []
        
        # 常见的直播源格式匹配模式
        patterns = [
            r'http[s]?://[^\s\"\']+\.m3u8?[^\s\"\']*',
            r'http[s]?://[^\s\"\']+\.flv?[^\s\"\']*',
            r'http[s]?://[^\s\"\']+\.ts?[^\s\"\']*',
            r'rtmp://[^\s\"\']+',
            r'http[s]?://[^\s\"\']+/live?[^\s\"\']*'
        ]
        
        import re
        for pattern in patterns:
            matches = re.findall(pattern, js_content)
            sources.extend(matches)
        
        return list(set(sources))  # 去重
    
    def save_to_file(self, sources: List[str], filename: str = "1.txt"):
        """
        保存直播源到文件
        
        Args:
            sources: 直播源列表
            filename: 文件名
        """
        with open(filename, 'w', encoding='utf-8') as f:
            for source in sources:
                f.write(source + '\n')
        print(f"成功保存 {len(sources)} 个直播源到 {filename}")
    
    def run(self, max_pages: int = 5):
        """
        主执行函数
        
        Args:
            max_pages: 最大搜索页数
        """
        all_live_sources = []
        
        print("开始搜索FOFA平台...")
        
        for page in range(1, max_pages + 1):
            print(f"正在搜索第 {page} 页...")
            
            data = self.search_live_sources(page=page)
            if not data or not data.get('error'):
                print("API请求失败或返回错误")
                break
                
            if not data.get('results'):
                print("没有更多结果")
                break
            
            # 提取直播源URL
            live_urls = self.extract_live_urls(data['results'])
            print(f"第 {page} 页找到 {len(live_urls)} 个潜在直播源")
            
            # 逐个获取并解析JS文件
            for i, url in enumerate(live_urls):
                print(f"正在处理 {i+1}/{len(live_urls)}: {url}")
                
                js_content = self.get_js_content(url)
                if js_content:
                    sources = self.parse_js_for_sources(js_content)
                    all_live_sources.extend(sources)
                    print(f"从 {url} 提取到 {len(sources)} 个直播源")
                
                # 避免请求过快
                time.sleep(0.5)
            
            # 检查是否还有更多页面
            if len(data['results']) < 100:
                break
        
        # 去重并保存
        unique_sources = list(set(all_live_sources))
        self.save_to_file(unique_sources, "1.txt")
        
        print(f"任务完成！共找到 {len(unique_sources)} 个唯一直播源")

# 使用示例
if __name__ == "__main__":
    # 需要替换为您的FOFA账号信息
    FOFA_EMAIL = "ljf9096@163.com"  # 替换为您的FOFA邮箱
    FOFA_KEY = "410522Ljf"  # 替换为您的FOFA API Key
    
    # 创建提取器实例
    extractor = FofaLiveSourceExtractor(FOFA_EMAIL, FOFA_KEY)
    
    # 执行提取
    extractor.run(max_pages=3)
