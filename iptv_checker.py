#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import concurrent.futures
import re
from urllib.parse import urlparse
from datetime import datetime

class IPTVChecker:
    def __init__(self):
        self.source_file = "1.txt"
        self.whitelist_file = "2.txt"
        self.blacklist_file = "3.txt"
        
        # 配置参数（根据您的要求设置）
        self.request_timeout = 10  # 请求超时时间（秒）
        self.max_workers = 15     # 最大并发线程数
        self.max_response_time = 5  # 最大可接受响应时间（秒）
        
        self.valid_sources = []
        self.invalid_sources = []
        
    def read_source_urls(self):
        """从1.txt读取多个来源地址"""
        print("正在读取来源文件 1.txt...")
        source_urls = []
        
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 支持多种格式：纯URL或 名称,URL
                        if ',' in line:
                            url = line.split(',')[-1].strip()
                        else:
                            url = line
                        
                        if self.is_valid_source_url(url):
                            source_urls.append(url)
            
            print(f"从 1.txt 中读取到 {len(source_urls)} 个有效来源地址")
            return source_urls
            
        except FileNotFoundError:
            print(f"错误：文件 {self.source_file} 不存在")
            return []
        except Exception as e:
            print(f"读取文件时出错: {e}")
            return []
    
    def is_valid_source_url(self, url):
        """检查来源URL是否有效"""
        if not url or not isinstance(url, str):
            return False
        
        valid_protocols = ['http', 'https']
        parsed = urlparse(url)
        
        if parsed.scheme not in valid_protocols:
            return False
        
        if not parsed.netloc:
            return False
        
        return True
    
    def fetch_from_source(self, source_url):
        """从单个来源地址获取直播源"""
        try:
            print(f"正在抓取: {source_url}")
            response = requests.get(source_url, timeout=self.request_timeout)
            
            if response.status_code == 200:
                content = response.text
                urls = self.extract_stream_urls(content, source_url)
                print(f"从 {source_url} 提取到 {len(urls)} 个直播源")
                return urls
            else:
                print(f"抓取失败 {source_url}: HTTP {response.status_code}")
                return []
                
        except requests.exceptions.Timeout:
            print(f"抓取 {source_url} 超时（{self.request_timeout}秒）")
            return []
        except Exception as e:
            print(f"抓取 {source_url} 时出错: {e}")
            return []
    
    def extract_stream_urls(self, content, source_url):
        """从内容中提取直播源URL"""
        urls = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 处理 M3U 格式
            if line.startswith(('http://', 'https://', 'rtmp://', 'rtsp://', 'udp://')):
                # 提取频道名称（如果有）
                name = self.extract_channel_name(line, source_url)
                urls.append((name, line))
            
            # 处理 频道名,URL 格式
            elif ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2 and self.is_valid_stream_url(parts[1]):
                    urls.append((parts[0].strip(), parts[1].strip()))
            
            # 处理 EXTINF 格式（M3U文件）
            elif line.startswith('#EXTINF'):
                # 尝试解析EXTINF格式获取频道名
                name = self.parse_extinf_line(line)
                urls.append((name, ""))  # URL会在下一行
        
        # 处理M3U格式的URL行
        final_urls = []
        for i, (name, url) in enumerate(urls):
            if not url and i + 1 < len(urls):
                # 如果当前行没有URL但下一行有，则使用下一行的URL
                next_name, next_url = urls[i + 1]
                if next_url and not next_name:  # 下一行只有URL没有名称
                    final_urls.append((name, next_url))
            elif url:
                final_urls.append((name, url))
        
        return final_urls
    
    def extract_channel_name(self, url, source_url):
        """从URL中提取频道名称"""
        try:
            parsed = urlparse(url)
            # 从路径中提取可能的频道名
            path_parts = parsed.path.split('/')
            for part in path_parts:
                if part and '.' not in part and len(part) > 2:
                    return part
            return "未知频道"
        except:
            return "未知频道"
    
    def parse_extinf_line(self, line):
        """解析EXTINF行获取频道名称"""
        try:
            # 格式: #EXTINF:-1,频道名称
            match = re.search(r',([^,]+)$', line)
            if match:
                return match.group(1).strip()
            return "未知频道"
        except:
            return "未知频道"
    
    def is_valid_stream_url(self, url):
        """检查直播源URL格式是否有效"""
        if not url:
            return False
        
        valid_protocols = ['http', 'https', 'rtmp', 'rtsp', 'udp', 'rtp']
        parsed = urlparse(url)
        
        if parsed.scheme not in valid_protocols:
            return False
        
        if not parsed.netloc:
            return False
        
        return True
    
    def check_stream(self, name_url):
        """检查单个直播源的有效性"""
        name, url = name_url
        
        try:
            start_time = time.time()
            
            # 主要检查HTTP/HTTPS源
            if url.startswith(('http', 'https')):
                # 使用HEAD请求快速检查
                response = requests.head(url, timeout=self.request_timeout, 
                                       allow_redirects=True, 
                                       headers={'User-Agent': 'Mozilla/5.0'})
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    if response_time <= self.max_response_time:
                        return (name, url, True, response_time)
                    else:
                        print(f"源 {url} 响应时间 {response_time:.2f}s 超过限制 {self.max_response_time}s")
                        return (name, url, False, response_time)
            
            # 对于其他协议，暂时标记为有效（需要特殊工具验证）
            else:
                return (name, url, True, 0)
                
        except requests.exceptions.Timeout:
            print(f"检查源 {url} 超时（{self.request_timeout}秒）")
        except requests.exceptions.RequestException as e:
            print(f"检查源 {url} 网络错误: {e}")
        except Exception as e:
            print(f"检查源 {url} 时出错: {e}")
        
        return (name, url, False, 0)
    
    def check_all_streams(self, all_streams):
        """并发检查所有直播源"""
        print(f"开始检查 {len(all_streams)} 个直播源的有效性...")
        print(f"并发线程: {self.max_workers}, 超时: {self.request_timeout}s, 最大响应时间: {self.max_response_time}s")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.check_stream, all_streams))
        
        for name, url, is_valid, response_time in results:
            if is_valid and response_time <= self.max_response_time:
                self.valid_sources.append({
                    'name': name,
                    'url': url,
                    'response_time': response_time
                })
            else:
                self.invalid_sources.append({
                    'name': name,
                    'url': url,
                    'reason': '超时' if response_time > self.max_response_time else '无效'
                })
        
        print(f"检查完成: {len(self.valid_sources)} 个有效源, {len(self.invalid_sources)} 个无效源")
    
    def generate_whitelist(self):
        """生成白名单 2.txt"""
        print("生成白名单 2.txt...")
        
        try:
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                f.write("# IPTV直播源白名单\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 有效源数量: {len(self.valid_sources)}\n")
                f.write(f"# 配置: 超时{self.request_timeout}s, 最大响应{self.max_response_time}s, 线程{self.max_workers}\n")
                f.write("#" + "="*60 + "\n\n")
                
                # 按响应时间排序（快的在前）
                sorted_sources = sorted(self.valid_sources, key=lambda x: x['response_time'])
                
                for source in sorted_sources:
                    response_time_str = f"{source['response_time']:.2f}s" if source['response_time'] > 0 else "N/A"
                    f.write(f"{source['name']},{source['url']}#响应时间:{response_time_str}\n")
            
            print(f"白名单已保存到 {self.whitelist_file}")
            
        except Exception as e:
            print(f"生成白名单时出错: {e}")
    
    def generate_blacklist(self):
        """生成黑名单 3.txt"""
        print("生成黑名单 3.txt...")
        
        try:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                f.write("# IPTV直播源黑名单\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 无效源数量: {len(self.invalid_sources)}\n")
                f.write(f"# 配置: 超时{self.request_timeout}s, 最大响应{self.max_response_time}s, 线程{self.max_workers}\n")
                f.write("#" + "="*60 + "\n\n")
                
                for source in self.invalid_sources:
                    f.write(f"{source['name']},{source['url']}#原因:{source['reason']}\n")
            
            print(f"黑名单已保存到 {self.blacklist_file}")
            
        except Exception as e:
            print(f"生成黑名单时出错: {e}")
    
    def run(self):
        """主运行函数"""
        start_time = time.time()
        
        print("=" * 70)
        print("IPTV直播源自动化检测工具")
        print(f"配置: 请求超时{self.request_timeout}s, 最大响应{self.max_response_time}s, 并发线程{self.max_workers}")
        print("=" * 70)
        
        # 1. 读取来源地址
        source_urls = self.read_source_urls()
        if not source_urls:
            print("未找到有效的来源地址，请检查 1.txt 文件")
            return
        
        # 2. 从所有来源抓取直播源
        all_streams = []
        for source_url in source_urls:
            streams = self.fetch_from_source(source_url)
            all_streams.extend(streams)
        
        if not all_streams:
            print("未从任何来源获取到直播源")
            return
        
        # 3. 去重（基于URL）
        seen_urls = set()
        unique_streams = []
        for name, url in all_streams:
            if url not in seen_urls:
                seen_urls.add(url)
                unique_streams.append((name, url))
        
        print(f"去重后剩余 {len(unique_streams)} 个唯一直播源")
        
        # 4. 检查有效性
        self.check_all_streams(unique_streams)
        
        # 5. 生成结果文件
        if self.valid_sources:
            self.generate_whitelist()
        else:
            print("没有有效源，跳过生成白名单")
        
        if self.invalid_sources:
            self.generate_blacklist()
        else:
            print("没有无效源，跳过生成黑名单")
        
        # 6. 输出总结
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"\n{'='*70}")
        print("检测完成!")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"处理来源: {len(source_urls)}个")
        print(f"获取源数: {len(all_streams)}个")
        print(f"唯一源数: {len(unique_streams)}个")
        print(f"有效源数: {len(self.valid_sources)}个 → 2.txt")
        print(f"无效源数: {len(self.invalid_sources)}个 → 3.txt")
        
        if self.valid_sources:
            avg_response = sum(s['response_time'] for s in self.valid_sources) / len(self.valid_sources)
            print(f"平均响应时间: {avg_response:.2f}秒")
        
        print(f"{'='*70}")

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run()
