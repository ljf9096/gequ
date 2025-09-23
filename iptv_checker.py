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
        
        self.timeout = 5
        self.max_workers = 30
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
            response = requests.get(source_url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                urls = self.extract_stream_urls(content, source_url)
                print(f"从 {source_url} 提取到 {len(urls)} 个直播源")
                return urls
            else:
                print(f"抓取失败 {source_url}: HTTP {response.status_code}")
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
            if line.startswith('http'):
                urls.append(("未知频道", line))
            
            # 处理 频道名,URL 格式
            elif ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2 and self.is_valid_stream_url(parts[1]):
                    urls.append((parts[0].strip(), parts[1].strip()))
            
            # 处理 EXTINF 格式
            elif line.startswith('#EXTINF'):
                # 在M3U格式中，下一行通常是URL
                pass
        
        return urls
    
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
            # 主要检查HTTP/HTTPS源
            if url.startswith(('http', 'https')):
                # 使用HEAD请求快速检查
                response = requests.head(url, timeout=self.timeout, 
                                       allow_redirects=True, 
                                       headers={'User-Agent': 'Mozilla/5.0'})
                
                if response.status_code == 200:
                    return (name, url, True, response.elapsed.total_seconds())
            
            # 对于其他协议，暂时标记为有效（需要特殊工具验证）
            else:
                return (name, url, True, 0)
                
        except requests.exceptions.RequestException:
            pass
        except Exception as e:
            print(f"检查源 {url} 时出错: {e}")
        
        return (name, url, False, 0)
    
    def check_all_streams(self, all_streams):
        """并发检查所有直播源"""
        print(f"开始检查 {len(all_streams)} 个直播源的有效性...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.check_stream, all_streams))
        
        for name, url, is_valid, response_time in results:
            if is_valid:
                self.valid_sources.append({
                    'name': name,
                    'url': url,
                    'response_time': response_time
                })
            else:
                self.invalid_sources.append({
                    'name': name,
                    'url': url
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
                f.write("#" + "="*50 + "\n\n")
                
                # 按响应时间排序（快的在前）
                sorted_sources = sorted(self.valid_sources, key=lambda x: x['response_time'])
                
                for source in sorted_sources:
                    f.write(f"{source['name']},{source['url']}\n")
            
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
                f.write("#" + "="*50 + "\n\n")
                
                for source in self.invalid_sources:
                    f.write(f"{source['name']},{source['url']}\n")
            
            print(f"黑名单已保存到 {self.blacklist_file}")
            
        except Exception as e:
            print(f"生成黑名单时出错: {e}")
    
    def run(self):
        """主运行函数"""
        start_time = time.time()
        
        print("=" * 60)
        print("IPTV直播源自动化检测工具")
        print("=" * 60)
        
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
        
        # 3. 去重
        unique_streams = list(set(all_streams))
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
        print(f"\n{'='*60}")
        print("检测完成!")
        print(f"总耗时: {end_time - start_time:.2f}秒")
        print(f"处理来源: {len(source_urls)}个")
        print(f"获取源数: {len(all_streams)}个")
        print(f"唯一源数: {len(unique_streams)}个")
        print(f"有效源数: {len(self.valid_sources)}个 → 2.txt")
        print(f"无效源数: {len(self.invalid_sources)}个 → 3.txt")
        print(f"{'='*60}")

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run()
