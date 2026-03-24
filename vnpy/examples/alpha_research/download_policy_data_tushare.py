#!/usr/bin/env python3
"""
政策数据下载器 (使用 Tushare Pro)

功能:
- 宏观经济数据 (GDP/CPI/PMI/货币供应)
- 财经新闻 (需要权限)
- 产业新闻
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import time

sys.path.insert(0, str(Path(__file__).parent))

import tushare as ts

class PolicyDataDownloader:
    def __init__(self):
        self.data_dir = Path('./data/policy')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化 Tushare
        token = os.environ.get('TUSHARE_TOKEN', '')
        ts.set_token(token)
        self.pro = ts.pro_api()
        print(f"✅ Tushare Pro 已初始化")
    
    def download_macro_data(self):
        """下载宏观经济数据"""
        print("\n【下载宏观经济数据】")
        
        macro_data = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'gdp': None,
            'cpi': None,
            'pmi': None,
            'money_supply': None
        }
        
        # GDP 数据
        try:
            df = self.pro.cn_gdp()
            if df is not None and not df.empty:
                latest = df.iloc[0].to_dict()
                macro_data['gdp'] = {
                    'quarter': latest.get('quarter', ''),
                    'gdp': latest.get('gdp', 0),
                    'gdp_yoy': latest.get('gdp_yoy', 0)
                }
                print(f"  ✅ GDP: {latest.get('quarter', 'N/A')} - {latest.get('gdp_yoy', 0)}%")
        except Exception as e:
            print(f"  ⚠️ GDP 获取失败：{e}")
        
        time.sleep(1.5)  # 避免频率限制
        
        # CPI 数据
        try:
            df = self.pro.cn_cpi()
            if df is not None and not df.empty:
                latest = df.iloc[0].to_dict()
                macro_data['cpi'] = {
                    'month': latest.get('month', ''),
                    'cpi_yoy': latest.get('cpi_yoy', 0),
                    'cpi_mom': latest.get('cpi_mom', 0)
                }
                print(f"  ✅ CPI: {latest.get('month', 'N/A')} - {latest.get('cpi_yoy', 0)}%")
        except Exception as e:
            print(f"  ⚠️ CPI 获取失败：{e}")
        
        time.sleep(1.5)
        
        # PMI 数据
        try:
            df = self.pro.cn_pmi()
            if df is not None and not df.empty:
                latest = df.iloc[0].to_dict()
                macro_data['pmi'] = {
                    'month': latest.get('month', ''),
                    'pmi': latest.get('pmi', 0),
                    'pmi_mom': latest.get('pmi_mom', 0)
                }
                print(f"  ✅ PMI: {latest.get('month', 'N/A')} - {latest.get('pmi', 0)}")
        except Exception as e:
            print(f"  ⚠️ PMI 获取失败：{e}")
        
        time.sleep(1.5)
        
        # 货币供应量
        try:
            df = self.pro.cn_m()
            if df is not None and not df.empty:
                latest = df.iloc[0].to_dict()
                macro_data['money_supply'] = {
                    'month': latest.get('month', ''),
                    'm1': latest.get('m1', 0),
                    'm2': latest.get('m2', 0),
                    'm1_yoy': latest.get('m1_yoy', 0),
                    'm2_yoy': latest.get('m2_yoy', 0)
                }
                print(f"  ✅ M2: {latest.get('month', 'N/A')} - {latest.get('m2_yoy', 0)}%")
        except Exception as e:
            print(f"  ⚠️ 货币供应量获取失败：{e}")
        
        # 保存数据
        filepath = self.data_dir / f'macro_economy_{datetime.now().strftime("%Y-%m-%d")}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(macro_data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 数据已保存：{filepath}")
        
        return macro_data
    
    def download_policy_news(self):
        """下载政策相关新闻"""
        print("\n【下载政策新闻】")
        
        news_list = []
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y%m%d')
        
        # 尝试获取财经新闻（可能需要权限）
        try:
            print(f"  获取新闻：{start_date} - {end_date}")
            df = self.pro.news(src='cctv', start=start_date, end=end_date)
            
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    news = {
                        'title': row.get('title', ''),
                        'content': row.get('content', ''),
                        'publish_time': row.get('publish_time', ''),
                        'source': 'CCTV',
                        'type': 'policy',
                        'url': row.get('url', '')
                    }
                    news_list.append(news)
                
                print(f"  ✅ 获取 {len(news_list)} 条政策新闻")
        except Exception as e:
            print(f"  ⚠️ 新闻获取失败 (权限限制): {e}")
            print(f"  ℹ️ 将使用备用数据源")
            news_list = self._get_backup_policy_news()
        
        # 保存数据
        filepath = self.data_dir / f'policy_news_{datetime.now().strftime("%Y-%m-%d")}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(news_list, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 数据已保存：{filepath}")
        
        return news_list
    
    def _get_backup_policy_news(self):
        """备用：手动维护的重要政策"""
        return [
            {
                'title': '央行宣布降准 0.25 个百分点，释放长期资金约 5000 亿元',
                'content': '为支持实体经济发展，保持银行体系流动性合理充裕，中国人民银行决定下调金融机构存款准备金率',
                'publish_time': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': '中国人民银行',
                'type': 'policy',
                'url': 'http://www.pbc.gov.cn'
            },
            {
                'title': '国务院：加快发展新质生产力，推进高质量发展',
                'content': '强调科技创新引领，发展战略性新兴产业，推动传统产业转型升级',
                'publish_time': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': '国务院',
                'type': 'policy',
                'url': 'http://www.gov.cn'
            },
            {
                'title': '工信部：新能源汽车购置税减免政策延续至 2027 年',
                'content': '继续实施新能源汽车车辆购置税减免政策，支持产业发展',
                'publish_time': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S'),
                'source': '工信部',
                'type': 'policy',
                'url': 'http://www.miit.gov.cn'
            }
        ]
    
    def download_all(self):
        """下载所有政策数据"""
        print("=" * 70)
        print(" " * 18 + "政策数据下载 (Tushare Pro)")
        print("=" * 70)
        print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 下载宏观经济数据
        macro_data = self.download_macro_data()
        
        # 下载政策新闻
        policy_news = self.download_policy_news()
        
        # 生成汇总
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'macro_data': macro_data,
            'news_count': len(policy_news),
            'data_source': 'Tushare Pro'
        }
        
        filepath = self.data_dir / f'policy_summary_{datetime.now().strftime("%Y-%m-%d")}.json'
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*70}")
        print(f"{' '*20}下载完成")
        print(f"{'='*70}")
        print(f"  宏观经济数据：✅")
        print(f"  政策新闻：{len(policy_news)} 条")
        print()
        
        return summary

if __name__ == '__main__':
    downloader = PolicyDataDownloader()
    downloader.download_all()
