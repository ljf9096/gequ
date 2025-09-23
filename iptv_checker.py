#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import concurrent.futures
from urllib.parse import urlparse
from datetime import datetime

class IPTVChecker:
    def __init__(self):
        self.source_file = "1.txt"
        self.whitelist_file = "2.txt"
        self.blacklist_file = "3.txt"
        
        # 配置参数
        self.timeout = 10  # 请求超时时间（秒）
        self.max_workers = 15  # 最大并发线程数
        self.max_response_time = 5  # 最大可接受响应时间（秒）
        
        self.valid_sources = []
        self.invalid_sources = []

    def read_source_urls(self):
        """从1.txt读取来源地址"""
        print("读取来源文件...")
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except:
            return []

    def fetch_streams_from_url(self, url):
        """从单个URL获取直播源"""
        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return self.parse_content(response.text)
        except:
            pass
        return []

    def parse_content(self, content):
        """解析内容中的直播源"""
        streams = []
        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2 and self.is_valid_url(parts[1]):
                    streams.append((parts[0], parts[1]))
            elif self.is_valid_url(line):
                streams.append(("未知频道", line))
        
        return streams

    def is_valid_url(self, url):
        """检查URL是否有效"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False

    def check_stream(self, stream):
        """检查单个直播源"""
        name, url = stream
        start_time = time.time()
        
        try:
            if url.startswith(('http', 'https')):
                response = requests.head(url, timeout=self.timeout, allow_redirects=True)
                response_time = time.time() - start_time
                
                if response.status_code == 200 and response_time <= self.max_response_time:
                    return (name, url, True, response_time)
            
            return (name, url, False, 0)
            
        except:
            return (name, url, False, 0)

    def run_check(self):
        """主检测流程"""
        print("开始IPTV直播源检测...")
        
        # 读取来源
        sources = self.read_source_urls()
        if not sources:
            print("未找到有效的来源地址")
            return

        # 获取所有直播源
        all_streams = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = executor.map(self.fetch_streams_from_url, sources)
            for result in results:
                all_streams.extend(result)

        if not all_streams:
            print("未获取到任何直播源")
            return

        # 去重
        unique_streams = []
        seen_urls = set()
        for stream in all_streams:
            if stream[1] not in seen_urls:
                seen_urls.add(stream[1])
                unique_streams.append(stream)

        print(f"获取到 {len(unique_streams)} 个唯一直播源")

        # 检测有效性
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = executor.map(self.check_stream, unique_streams)
            
            for name, url, is_valid, response_time in results:
                if is_valid:
                    self.valid_sources.append(f"{name},{url}")
                else:
                    self.invalid_sources.append(f"{name},{url}")

        # 保存结果
        self.save_results()

    def save_results(self):
        """保存结果到文件"""
        # 保存白名单
        if self.valid_sources:
            with open(self.whitelist_file, 'w', encoding='utf-8') as f:
                f.write(f"# 白名单 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 有效源数量: {len(self.valid_sources)}\n")
                f.write("\n".join(self.valid_sources))
            print(f"白名单已保存至: {self.whitelist_file}")

        # 保存黑名单
        if self.invalid_sources:
            with open(self.blacklist_file, 'w', encoding='utf-8') as f:
                f.write(f"# 黑名单 - 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 无效源数量: {len(self.invalid_sources)}\n")
                f.write("\n".join(self.invalid_sources))
            print(f"黑名单已保存至: {self.blacklist_file}")

        print(f"\n检测完成！有效源: {len(self.valid_sources)}, 无效源: {len(self.invalid_sources)}")

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run_check()
