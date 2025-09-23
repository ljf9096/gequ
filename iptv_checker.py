#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import concurrent.futures
import re
import os
from urllib.parse import urlparse
import json
from datetime import datetime

class IPTVChecker:
    def __init__(self):
        self.sources = [
            # 公开的IPTV源地址
            "https://raw.githubusercontent.com/iptv-org/iptv/master/streams.m3u",
            "https://raw.githubusercontent.com/free-iptv/iptv/master/streams.m3u",
            "https://raw.githubusercontent.com/EvilCult/iptv-m3u-maker/master/m3u/iptv.m3u",
            "http://tonkiang.us/9dlist.txt",
            "https://raw.githubusercontent.com/YanG-1989/m3u/main/Adult.m3u",
            "https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u"
        ]
        
        self.timeout = 5
        self.max_workers = 50
        self.valid_sources = []
        self.invalid_sources = []
        self.whitelist = []
        self.blacklist = []
        
        # 分类定义
        self.categories = {
            "CCTV": ["CCTV", "央视"],
            "卫视": ["卫视", "TV", "电视台"],
            "电影": ["电影", "MOVIE", "影院"],
            "体育": ["体育", "SPORT", "足球", "篮球"],
            "新闻": ["新闻", "NEWS"],
            "少儿": ["少儿", "卡通", "动画", "儿童"],
            "国际": ["BBC", "CNN", "NHK", "HBO", "DISNEY"],
            "成人": ["成人", "ADULT", "18+", "XXX"]
        }
        
    def fetch_sources(self):
        """从多个来源获取直播源"""
        print("开始从多个来源抓取直播源...")
        all_urls = set()
        
        for source in self.sources:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    # 解析M3U格式
                    if source.endswith('.m3u') or source.endswith('.m3u8'):
                        urls = self.parse_m3u(response.text)
                    # 解析TXT格式
                    else:
                        urls = self.parse_txt(response.text)
                    
                    print(f"从 {source} 获取到 {len(urls)} 个直播源")
                    all_urls.update(urls)
                    
            except Exception as e:
                print(f"获取源 {source} 失败: {e}")
                continue
        
        return list(all_urls)
    
    def parse_m3u(self, content):
        """解析M3U格式文件"""
        urls = []
        lines = content.split('\n')
        
        for i in range(len(lines)):
            if lines[i].startswith('#EXTINF'):
                if i + 1 < len(lines) and not lines[i + 1].startswith('#'):
                    url = lines[i + 1].strip()
                    if self.is_valid_url(url):
                        # 提取频道名称
                        name_match = re.search(r'[,]([^,]+)$', lines[i])
                        name = name_match.group(1).strip() if name_match else "未知频道"
                        urls.append((name, url))
        
        return urls
    
    def parse_txt(self, content):
        """解析TXT格式文件"""
        urls = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # 处理 频道名,URL 格式
                if ',' in line:
                    parts = line.split(',', 1)
                    if len(parts) == 2 and self.is_valid_url(parts[1]):
                        urls.append((parts[0].strip(), parts[1].strip()))
                # 处理纯URL格式
                elif self.is_valid_url(line):
                    urls.append(("未知频道", line))
        
        return urls
    
    def is_valid_url(self, url):
        """检查URL是否有效"""
        if not url or not isinstance(url, str):
            return False
        
        # 检查常见协议
        valid_protocols = ['http', 'https', 'rtmp', 'rtsp', 'udp']
        parsed = urlparse(url)
        if parsed.scheme not in valid_protocols:
            return False
        
        # 检查域名和路径
        if not parsed.netloc or not parsed.path:
            return False
        
        return True
    
    def check_single_source(self, name_url):
        """检查单个直播源的有效性"""
        name, url = name_url
        
        try:
            # 对于HTTP/HTTPS源
            if url.startswith(('http', 'https')):
                response = requests.head(url, timeout=self.timeout, allow_redirects=True)
                if response.status_code == 200:
                    return (name, url, True, response.elapsed.total_seconds())
            
            # 对于其他协议，尝试建立连接
            else:
                # 这里可以添加其他协议的检查逻辑
                # 暂时标记为有效，但需要进一步验证
                return (name, url, True, 0)
                
        except requests.exceptions.RequestException:
            pass
        except Exception as e:
            print(f"检查源 {url} 时出错: {e}")
        
        return (name, url, False, 0)
    
    def check_sources(self, sources):
        """并发检查所有直播源"""
        print(f"开始检查 {len(sources)} 个直播源的有效性...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(self.check_single_source, sources))
        
        for name, url, is_valid, response_time in results:
            if is_valid:
                self.valid_sources.append({
                    'name': name,
                    'url': url,
                    'response_time': response_time,
                    'category': self.categorize_channel(name)
                })
            else:
                self.invalid_sources.append({
                    'name': name,
                    'url': url
                })
        
        print(f"检查完成: {len(self.valid_sources)} 个有效源, {len(self.invalid_sources)} 个无效源")
    
    def categorize_channel(self, channel_name):
        """对频道进行分类"""
        channel_name = channel_name.upper()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword.upper() in channel_name:
                    return category
        
        return "其他"
    
    def generate_whitelist(self):
        """生成白名单"""
        print("生成白名单...")
        
        # 按分类组织白名单
        categorized = {}
        for source in self.valid_sources:
            category = source['category']
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(source)
        
        # 生成白名单文件
        with open('whitelist.txt', 'w', encoding='utf-8') as f:
            f.write("# IPTV直播源白名单\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 有效源数量: {len(self.valid_sources)}\n")
            f.write("#" + "="*50 + "\n\n")
            
            for category, sources in categorized.items():
                f.write(f"# {category}频道\n")
                for source in sorted(sources, key=lambda x: x['name']):
                    f.write(f"{source['name']},{source['url']}\n")
                f.write("\n")
        
        # 生成M3U格式白名单
        with open('whitelist.m3u', 'w', encoding='utf-8') as f:
            f.write('#EXTM3U\n')
            for source in self.valid_sources:
                f.write(f'#EXTINF:-1 tvg-name="{source["name"]}" group-title="{source["category"]}",{source["name"]}\n')
                f.write(f'{source["url"]}\n')
    
    def generate_blacklist(self):
        """生成黑名单"""
        print("生成黑名单...")
        
        with open('blacklist.txt', 'w', encoding='utf-8') as f:
            f.write("# IPTV直播源黑名单\n")
            f.write(f"# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 无效源数量: {len(self.invalid_sources)}\n")
            f.write("#" + "="*50 + "\n\n")
            
            for source in self.invalid_sources:
                f.write(f"{source['name']},{source['url']}\n")
    
    def generate_statistics(self):
        """生成统计报告"""
        print("生成统计报告...")
        
        stats = {
            'total_sources': len(self.valid_sources) + len(self.invalid_sources),
            'valid_sources': len(self.valid_sources),
            'invalid_sources': len(self.invalid_sources),
            'success_rate': len(self.valid_sources) / (len(self.valid_sources) + len(self.invalid_sources)) * 100,
            'categories': {},
            'generation_time': datetime.now().isoformat()
        }
        
        # 分类统计
        for source in self.valid_sources:
            category = source['category']
            if category not in stats['categories']:
                stats['categories'][category] = 0
            stats['categories'][category] += 1
        
        with open('statistics.json', 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        # 文本格式统计
        with open('statistics.txt', 'w', encoding='utf-8') as f:
            f.write("IPTV直播源统计报告\n")
            f.write("="*50 + "\n")
            f.write(f"生成时间: {stats['generation_time']}\n")
            f.write(f"总源数量: {stats['total_sources']}\n")
            f.write(f"有效源数量: {stats['valid_sources']}\n")
            f.write(f"无效源数量: {stats['invalid_sources']}\n")
            f.write(f"成功率: {stats['success_rate']:.2f}%\n\n")
            
            f.write("分类统计:\n")
            for category, count in stats['categories'].items():
                f.write(f"  {category}: {count}个\n")
    
    def run(self):
        """主运行函数"""
        start_time = time.time()
        
        try:
            # 1. 获取直播源
            sources = self.fetch_sources()
            if not sources:
                print("未获取到任何直播源")
                return
            
            # 2. 检查有效性
            self.check_sources(sources)
            
            # 3. 生成结果文件
            self.generate_whitelist()
            self.generate_blacklist()
            self.generate_statistics()
            
            # 4. 输出总结
            end_time = time.time()
            print(f"\n{'='*60}")
            print("IPTV直播源检测完成!")
            print(f"总耗时: {end_time - start_time:.2f}秒")
            print(f"有效源: {len(self.valid_sources)}个")
            print(f"无效源: {len(self.invalid_sources)}个")
            print(f"成功率: {len(self.valid_sources)/len(sources)*100:.2f}%")
            print(f"生成文件: whitelist.txt, whitelist.m3u, blacklist.txt, statistics.json, statistics.txt")
            print(f"{'='*60}")
            
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    checker = IPTVChecker()
    checker.run()
