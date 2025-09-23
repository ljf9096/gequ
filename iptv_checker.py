#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import concurrent.futures
from urllib.parse import urlparse
from datetime import datetime
import os

class IPTVChecker:
    def __init__(self):
        self.source_file = "1.txt"
        self.whitelist_file = "2.txt"
        self.blacklist_file = "3.txt"
        
        # 配置参数
        self.timeout = 10
        self.max_workers = 15
        self.max_response_time = 5
        
        self.valid_sources = []
        self.invalid_sources = []

    def read_source_urls(self):
        """从1.txt读取来源地址"""
        print("读取来源文件 1.txt...")
        urls = []
        try:
            if os.path.exists(self.source_file):
                with open(self.source_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if ',' in line:
                                url = line.split(',')[-1].strip()
                            else:
                                url = line
                            if url.startswith(('http://', 'https://')):
                                urls.append(url)
            print(f"找到 {len(urls)} 个来源地址")
        except Exception as e:
            print(f"读取文件错误: {e}")
        return urls

    def fetch_streams(self, url):
        """从URL获取直播源"""
        try:
            print(f"抓取: {url}")
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return self.parse_streams(response.text)
        except:
            pass
        return []

    def parse_streams(self, content):
        """解析直播源"""
        streams = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2 and self.is_valid_url(parts[1]):
                        streams.append((parts[0], parts[1]))
                elif self.is_valid_url(line):
                    streams.append(("未知频道", line))
        return streams

    def is_valid_url(self, url):
        """检查URL格式"""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except:
            return False

    def check_stream(self, stream):
        """检查直播源有效性"""
        name, url = stream
        try:
            if url.startswith(('http://', 'https://')):
                start_time = time.time()
                response = requests.head(url, timeout=self.timeout, 
                                       allow_redirects=True,
                                       headers={'User-Agent': 'Mozilla/5.0'})
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time <= self.max_response_time:
                    return (name, url, True)
        except:
            pass
        return (name, url, False)

    def force_create_files(self):
        """强制生成2.txt和3.txt文件"""
        print("强制生成结果文件...")
        
        # 强制生成白名单文件 2.txt
        with open(self.whitelist_file, 'w', encoding='utf-8') as f:
            f.write("# IPTV直播源白名单\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 有效源数量: {len(self.valid_sources)}\n")
            f.write("#" * 50 + "\n\n")
            if self.valid_sources:
                for name, url in self.valid_sources:
                    f.write(f"{name},{url}\n")
            else:
                f.write("# 暂无有效直播源\n")
        print(f"已生成: {self.whitelist_file}")

        # 强制生成黑名单文件 3.txt
        with open(self.blacklist_file, 'w', encoding='utf-8') as f:
            f.write("# IPTV直播源黑名单\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 无效源数量: {len(self.invalid_sources)}\n")
            f.write("#" * 50 + "\n\n")
            if self.invalid_sources:
                for name, url in self.invalid_sources:
                    f.write(f"{name},{url}\n")
            else:
                f.write("# 暂无无效直播源\n")
        print(f"已生成: {self.blacklist_file}")

    def run(self):
        """主函数"""
        print("=" * 60)
        print("IPTV直播源检测工具 - 强制生成版本")
        print("=" * 60)
        
        # 读取来源
        sources = self.read_source_urls()
        
        all_streams = []
        if sources:
            # 获取直播源
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(self.fetch_streams, sources))
                for result in results:
                    all_streams.extend(result)
        
        # 去重
        unique_streams = []
        seen_urls = set()
        for stream in all_streams:
            if stream[1] not in seen_urls:
                seen_urls.add(stream[1])
                unique_streams.append(stream)
        
        # 检测有效性
        if unique_streams:
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(self.check_stream, unique_streams))
            
            for name, url, is_valid in results:
                if is_valid:
                    self.valid_sources.append((name, url))
                else:
                    self.invalid_sources.append((name, url))
        
        # 强制生成文件
        self.force_create_files()
        
        # 输出统计
        print(f"\n统计结果:")
        print(f"来源地址: {len(sources)}个")
        print(f"直播源数: {len(all_streams)}个")
        print(f"唯一源数: {len(unique_streams)}个")
        print(f"有效源数: {len(self.valid_sources)}个")
        print(f"无效源数: {len(self.invalid_sources)}个")
        print("=" * 60)

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run()
