import requests
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import threading

class LiveSourceValidator:
    def __init__(self):
        self.white_list = []
        self.black_list = []
        self.lock = threading.Lock()
        self.timeout = 10  # 请求超时时间（秒）
        
    def read_source_urls(self, filename):
        """从文件读取源地址"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            return urls
        except FileNotFoundError:
            print(f"错误：文件 {filename} 不存在")
            return []
        except Exception as e:
            print(f"读取文件时出错：{e}")
            return []
    
    def fetch_live_sources(self, url):
        """从源地址抓取直播源"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(url, timeout=self.timeout, headers=headers)
            response.encoding = 'utf-8'
            
            if response.status_code == 200:
                # 提取直播源链接（支持多种格式）
                sources = self.extract_sources(response.text)
                return sources
            else:
                print(f"请求失败：{url}，状态码：{response.status_code}")
                return []
                
        except Exception as e:
            print(f"抓取直播源时出错：{url}，错误：{e}")
            return []
    
    def extract_sources(self, text):
        """从文本中提取直播源链接"""
        # 支持多种格式：直接链接、m3u8、flv等
        patterns = [
            r'https?://[^\s<>"{}|\\^`\[\]']+\.(m3u8|flv|ts|mp4)[^\s<>"{}|\\^`\[\]']*',
            r'https?://[^\s<>"{}|\\^`\[\]']+\.m3u8',
            r'https?://[^\s<>"{}|\\^`\[\]']+\.flv',
            r'^[^#].*\.(m3u8|flv|ts|mp4)',
        ]
        
        sources = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            # 如果是正则分组，取整个匹配
            if matches and isinstance(matches[0], tuple):
                full_matches = re.findall(pattern.replace(r'(m3u8|flv|ts|mp4)', r'.*'), text, re.IGNORECASE | re.MULTILINE)
                sources.extend(full_matches)
            else:
                matches = re.findall(pattern.replace(r'(m3u8|flv|ts|mp4)', r'.*'), text, re.IGNORECASE | re.MULTILINE)
                sources.extend(matches)
        
        # 去重
        return list(set(sources))
    
    def validate_source(self, source_url):
        """验证单个直播源的有效性"""
        try:
            # 简单的HEAD请求验证
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Range': 'bytes=0-1'  # 只请求少量数据
            }
            
            start_time = time.time()
            response = requests.head(source_url, timeout=self.timeout, headers=headers)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # 检查状态码和响应时间
            if response.status_code in [200, 206]:  # 206是部分内容
                print(f"✓ 有效源：{source_url} (响应时间：{response_time:.2f}s)")
                return source_url, True, response_time
            else:
                print(f"✗ 无效源：{source_url} (状态码：{response.status_code})")
                return source_url, False, response_time
                
        except requests.exceptions.Timeout:
            print(f"✗ 超时源：{source_url}")
            return source_url, False, self.timeout
        except Exception as e:
            print(f"✗ 错误源：{source_url}，错误：{e}")
            return source_url, False, None
    
    def validate_sources_parallel(self, sources, max_workers=10):
        """并行验证多个直播源"""
        valid_sources = []
        invalid_sources = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_source = {executor.submit(self.validate_source, source): source for source in sources}
            
            for future in as_completed(future_to_source):
                source_url, is_valid, response_time = future.result()
                
                with self.lock:
                    if is_valid:
                        # 添加响应时间信息
                        if response_time:
                            valid_sources.append(f"{source_url} # 响应时间：{response_time:.2f}s")
                        else:
                            valid_sources.append(source_url)
                    else:
                        invalid_sources.append(source_url)
        
        return valid_sources, invalid_sources
    
    def process_sources(self, input_file, white_file, black_file):
        """主处理函数"""
        print("开始读取源地址...")
        source_urls = self.read_source_urls(input_file)
        
        if not source_urls:
            print("没有找到有效的源地址")
            return
        
        print(f"找到 {len(source_urls)} 个源地址")
        
        all_sources = []
        
        # 抓取所有直播源
        print("\n开始抓取直播源...")
        for i, url in enumerate(source_urls, 1):
            print(f"抓取进度：{i}/{len(source_urls)} - {url}")
            sources = self.fetch_live_sources(url)
            if sources:
                print(f"  找到 {len(sources)} 个直播源")
                all_sources.extend(sources)
            else:
                print(f"  未找到直播源")
        
        # 去重
        all_sources = list(set(all_sources))
        print(f"\n总共找到 {len(all_sources)} 个唯一的直播源")
        
        if not all_sources:
            print("没有找到直播源，程序结束")
            return
        
        # 验证直播源
        print("\n开始验证直播源有效性...")
        valid_sources, invalid_sources = self.validate_sources_parallel(all_sources)
        
        print(f"\n验证完成！")
        print(f"有效源：{len(valid_sources)} 个")
        print(f"无效源：{len(invalid_sources)} 个")
        
        # 保存结果
        self.save_results(white_file, valid_sources)
        self.save_results(black_file, invalid_sources)
        
        print(f"\n结果已保存：")
        print(f"白名单：{white_file} ({len(valid_sources)} 个)")
        print(f"黑名单：{black_file} ({len(invalid_sources)} 个)")
    
    def save_results(self, filename, sources):
        """保存结果到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                for source in sources:
                    f.write(source + '\n')
        except Exception as e:
            print(f"保存文件 {filename} 时出错：{e}")

def main():
    validator = LiveSourceValidator()
    
    # 文件配置
    input_file = "1.txt"      # 输入文件
    white_file = "2.txt"      # 白名单文件
    black_file = "3.txt"      # 黑名单文件
    
    print("直播源验证工具")
    print("=" * 50)
    
    validator.process_sources(input_file, white_file, black_file)

if __name__ == "__main__":
    main()
