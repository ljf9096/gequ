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
        self.timeout = 10  # 请求超时时间（秒）
        self.max_workers = 15  # 最大并发线程数
        self.max_response_time = 5  # 最大可接受响应时间（秒）
        
        self.valid_sources = []
        self.invalid_sources = []

    def read_source_urls(self):
        """从1.txt读取来源地址"""
        print("正在读取来源文件 1.txt...")
        try:
            if not os.path.exists(self.source_file):
                print(f"错误：文件 {self.source_file} 不存在")
                return []
                
            with open(self.source_file, 'r', encoding='utf-8') as f:
                urls = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # 提取URL（支持 名称,URL 格式）
                        if ',' in line:
                            url = line.split(',')[-1].strip()
                        else:
                            url = line
                        
                        if self.is_valid_url(url):
                            urls.append(url)
                
                print(f"找到 {len(urls)} 个有效来源地址")
                return urls
                
        except Exception as e:
            print(f"读取文件时出错: {e}")
            return []

    def is_valid_url(self, url):
        """检查URL是否有效"""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except:
            return False

    def fetch_streams_from_url(self, url):
        """从单个URL获取直播源"""
        try:
            print(f"抓取: {url}")
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                return self.parse_content(response.text, url)
        except Exception as e:
            print(f"抓取失败 {url}: {e}")
        return []

    def parse_content(self, content, source_url):
        """解析内容中的直播源"""
        streams = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 处理 频道名称,URL 格式
            if ',' in line:
                parts = line.split(',', 1)
                if len(parts) == 2 and self.is_valid_url(parts[1]):
                    streams.append((parts[0].strip(), parts[1].strip()))
            
            # 处理纯URL格式
            elif self.is_valid_url(line):
                # 尝试从URL中提取频道名称
                name = self.extract_channel_name(line, source_url)
                streams.append((name, line))
        
        return streams

    def extract_channel_name(self, url, source_url):
        """从URL中提取频道名称"""
        try:
            # 从URL路径中提取可能的频道名
            parsed = urlparse(url)
            path_parts = [p for p in parsed.path.split('/') if p and '.' not in p]
            if path_parts:
                return path_parts[-1]
            return "未知频道"
        except:
            return "未知频道"

    def check_stream(self, stream):
        """检查单个直播源的有效性"""
        name, url = stream
        start_time = time.time()
        
        try:
            # 只检查HTTP/HTTPS源
            if url.startswith(('http://', 'https://')):
                response = requests.head(url, timeout=self.timeout, 
                                      allow_redirects=True,
                                      headers={'User-Agent': 'Mozilla/5.0'})
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    if response_time <= self.max_response_time:
                        return (name, url, True, response_time)
                    else:
                        return (name, url, False, response_time)
            
            return (name, url, False, 0)
            
        except requests.exceptions.Timeout:
            return (name, url, False, 0)
        except Exception as e:
            return (name, url, False, 0)

    def save_to_file(self, filename, data, title):
        """保存数据到文件"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n")
                f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 总数: {len(data)}\n")
                f.write("#" * 50 + "\n\n")
                f.write("\n".join(data))
            print(f"已生成文件: {filename}")
            return True
        except Exception as e:
            print(f"保存文件 {filename} 失败: {e}")
            return False

    def run(self):
        """主运行函数"""
        print("=" * 60)
        print("IPTV直播源检测工具")
        print(f"超时: {self.timeout}s, 线程: {self.max_workers}, 最大响应: {self.max_response_time}s")
        print("=" * 60)
        
        start_time = time.time()
        
        # 1. 读取来源地址
        source_urls = self.read_source_urls()
        if not source_urls:
            return
        
        # 2. 获取所有直播源
        print("\n开始抓取直播源...")
        all_streams = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.fetch_streams_from_url, source_urls))
        
        for result in results:
            all_streams.extend(result)
        
        if not all_streams:
            print("未获取到任何直播源")
            return
        
        print(f"共获取 {len(all_streams)} 个直播源")
        
        # 3. 去重处理
        unique_streams = []
        seen_urls = set()
        for stream in all_streams:
            if stream[1] not in seen_urls:
                seen_urls.add(stream[1])
                unique_streams.append(stream)
        
        print(f"去重后剩余 {len(unique_streams)} 个唯一直播源")
        
        # 4. 检测有效性
        print("\n开始检测直播源有效性...")
        valid_list = []
        invalid_list = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.check_stream, unique_streams))
        
        for name, url, is_valid, response_time in results:
            if is_valid:
                valid_list.append(f"{name},{url}")
            else:
                invalid_list.append(f"{name},{url}")
        
        # 5. 生成结果文件
        print("\n生成结果文件...")
        if valid_list:
            self.save_to_file(self.whitelist_file, valid_list, "白名单 - 有效直播源")
        else:
            print("没有有效直播源，跳过生成白名单")
        
        if invalid_list:
            self.save_to_file(self.blacklist_file, invalid_list, "黑名单 - 无效直播源")
        else:
            print("没有无效直播源，跳过生成黑名单")
        
        # 6. 输出统计信息
        end_time = time.time()
        total_time = end_time - start_time
        
        print("\n" + "=" * 60)
        print("检测完成!")
        print(f"总耗时: {total_time:.2f}秒")
        print(f"来源地址: {len(source_urls)}个")
        print(f"获取源数: {len(all_streams)}个")
        print(f"唯一源数: {len(unique_streams)}个")
        print(f"有效源数: {len(valid_list)}个 → 2.txt")
        print(f"无效源数: {len(invalid_list)}个 → 3.txt")
        print("=" * 60)

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run()
