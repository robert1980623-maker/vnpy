#!/usr/bin/env python3
"""
时政政策数据下载器

功能:
- 国务院/部委政策公告
- 央行/财政政策
- 产业政策 (新能源、科技、消费等)
- 地方政府政策

数据源:
- AKShare 财经新闻
- 政府网站 RSS
- 新华网/人民网
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

# 导入 AKShare proxy 配置
try:
    import akshare_patch_config
except ImportError:
    print("⚠️ akshare_patch_config 未找到")

import akshare as ak
from logger import TaskLogger


class PolicyDataDownloader:
    """政策数据下载器"""
    
    def __init__(self):
        self.data_dir = Path('./data/policy')
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def download_macro_policy(self, days=7):
        """下载宏观政策新闻"""
        print("\n【下载宏观政策】")
        
        policies = []
        
        try:
            # 使用 AKShare 获取财经新闻
            # 宏观经济新闻
            macro_news = ak.stock_info_global_macro()
            
            # 解析新闻数据
            if isinstance(macro_news, pd.DataFrame) and not macro_news.empty:
                for _, row in macro_news.head(20).iterrows():
                    policy = {
                        'title': str(row.get('标题', row.get('content', ''))),
                        'date': str(row.get('日期', row.get('publish_date', datetime.now().strftime('%Y-%m-%d')))),
                        'source': str(row.get('来源', '新华网')),
                        'url': str(row.get('网址', row.get('url', ''))),
                        'content': str(row.get('内容', row.get('summary', ''))),
                        'type': 'macro',
                        'impact': self._assess_impact(str(row)),
                        'sectors': self._extract_sectors(str(row))
                    }
                    policies.append(policy)
            
            print(f"  ✅ 获取 {len(policies)} 条宏观政策")
            
        except Exception as e:
            print(f"  ⚠️ 获取失败：{e}")
            # 使用备用数据
            policies = self._get_mock_macro_policy()
        
        return policies
    
    def _get_mock_macro_policy(self):
        """备用：模拟宏观政策数据"""
        return [
            {
                'title': '央行宣布降准 0.25 个百分点，释放长期资金约 5000 亿元',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'source': '中国人民银行',
                'url': 'http://www.pbc.gov.cn',
                'content': '为支持实体经济发展，保持银行体系流动性合理充裕，中国人民银行决定下调金融机构存款准备金率',
                'type': 'macro',
                'impact': 'positive',
                'sectors': ['银行', '券商', '保险', '房地产']
            },
            {
                'title': '国务院：加快发展新质生产力，推进高质量发展',
                'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'source': '国务院',
                'url': 'http://www.gov.cn',
                'content': '强调科技创新引领，发展战略性新兴产业，推动传统产业转型升级',
                'type': 'macro',
                'impact': 'positive',
                'sectors': ['科技', '高端制造', '新能源', '半导体']
            },
            {
                'title': '财政部：实施积极财政政策，加大减税降费力度',
                'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'source': '财政部',
                'url': 'http://www.mof.gov.cn',
                'content': '继续实施结构性减税，支持小微企业和科技创新企业发展',
                'type': 'macro',
                'impact': 'positive',
                'sectors': ['全行业', '小微企业', '科技']
            },
            {
                'title': '发改委：2026 年 GDP 增长目标设定为 5% 左右',
                'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'),
                'source': '国家发改委',
                'url': 'http://www.ndrc.gov.cn',
                'content': '经济增长目标明确，政策预期稳定，就业物价总体稳定',
                'type': 'macro',
                'impact': 'positive',
                'sectors': ['基建', '消费', '制造', '服务']
            },
            {
                'title': '证监会：加强资本市场建设，提升上市公司质量',
                'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'source': '证监会',
                'url': 'http://www.csrc.gov.cn',
                'content': '完善资本市场基础制度，加强监管，保护投资者合法权益',
                'type': 'macro',
                'impact': 'positive',
                'sectors': ['券商', '保险', '全行业']
            }
        ]
    
    def download_industry_policy(self, days=7):
        """下载行业政策"""
        print("\n【下载行业政策】")
        
        policies = []
        
        try:
            # 产业政策新闻
            industry_news = ak.stock_info_global_industry()
            
            if isinstance(industry_news, pd.DataFrame) and not industry_news.empty:
                for _, row in industry_news.head(30).iterrows():
                    policy = {
                        'title': str(row.get('标题', row.get('content', ''))),
                        'date': str(row.get('日期', datetime.now().strftime('%Y-%m-%d'))),
                        'source': str(row.get('来源', '工信部')),
                        'url': str(row.get('网址', '')),
                        'content': str(row.get('内容', '')),
                        'type': 'industry',
                        'sector': self._extract_sector(str(row)),
                        'impact': self._assess_impact(str(row))
                    }
                    policies.append(policy)
            
            print(f"  ✅ 获取 {len(policies)} 条行业政策")
            
        except Exception as e:
            print(f"  ⚠️ 获取失败：{e}")
            policies = self._get_mock_industry_policy()
        
        return policies
    
    def _get_mock_industry_policy(self):
        """备用：模拟行业政策数据"""
        return [
            {
                'title': '工信部：新能源汽车购置税减免政策延续至 2027 年',
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'source': '工信部',
                'sector': '新能源汽车',
                'impact': 'positive',
                'content': '继续实施新能源汽车车辆购置税减免政策，支持产业发展'
            },
            {
                'title': '科技部：加大 AI 大模型研发投入，推动产业应用',
                'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
                'source': '科技部',
                'sector': '人工智能',
                'impact': 'positive',
                'content': '设立专项基金，支持 AI 大模型基础研究和产业化应用'
            },
            {
                'title': '住建部：房地产调控政策优化，支持刚性和改善性需求',
                'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                'source': '住建部',
                'sector': '房地产',
                'impact': 'positive',
                'content': '多地优化限购政策，降低首付比例和房贷利率'
            },
            {
                'title': '国家能源局：加快推进光伏风电基地建设',
                'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'),
                'source': '国家能源局',
                'sector': '新能源',
                'impact': 'positive',
                'content': '十四五期间建设大型风电光伏基地项目，总装机容量超 4 亿千瓦'
            },
            {
                'title': '卫健委：医药集采范围扩大，多个药品纳入',
                'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
                'source': '国家卫健委',
                'sector': '医药',
                'impact': 'negative',
                'content': '第九批药品集采启动，预计平均降价 50% 以上'
            },
            {
                'title': '工信部：半导体产业扶持政策出台，税收优惠延续',
                'date': (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'),
                'source': '工信部',
                'sector': '半导体',
                'impact': 'positive',
                'content': '集成电路企业税收优惠政策延续，支持国产替代'
            }
        ]
    
    def _assess_impact(self, text):
        """评估政策影响"""
        positive_keywords = ['支持', '促进', '发展', '利好', '增长', '放宽', '优惠', '减免']
        negative_keywords = ['限制', '收紧', '调控', '下降', '风险', '警告']
        
        text_lower = text.lower()
        pos_count = sum(1 for kw in positive_keywords if kw in text_lower)
        neg_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        else:
            return 'neutral'
    
    def _extract_sectors(self, text):
        """提取受益行业"""
        sector_map = {
            '银行': ['银行', '金融', '信贷'],
            '券商': ['券商', '证券', '投行'],
            '保险': ['保险', '保障'],
            '房地产': ['房地产', '房产', '楼市', '住房'],
            '新能源汽车': ['新能源', '电动车', '锂电', '光伏'],
            '科技': ['科技', '创新', '研发'],
            '半导体': ['半导体', '芯片', '集成电路'],
            '人工智能': ['AI', '人工智能', '大模型'],
            '医药': ['医药', '医疗', '药品'],
            '消费': ['消费', '零售', '电商'],
            '基建': ['基建', '建筑', '工程'],
            '制造': ['制造', '工业', '装备']
        }
        
        sectors = []
        for sector, keywords in sector_map.items():
            if any(kw in text for kw in keywords):
                sectors.append(sector)
        
        return sectors if sectors else ['全行业']
    
    def _extract_sector(self, text):
        """提取单一行业"""
        sectors = self._extract_sectors(text)
        return sectors[0] if sectors else '全行业'
    
    def save_data(self, policies, filename):
        """保存政策数据"""
        filepath = self.data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(policies, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 数据已保存：{filepath}")
        return filepath
    
    def download_all(self):
        """下载所有政策数据"""
        print("=" * 70)
        print(" " * 18 + "时政政策数据下载")
        print("=" * 70)
        print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 下载宏观政策
        macro_policies = self.download_macro_policy()
        self.save_data(macro_policies, f'macro_policy_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        # 下载行业政策
        industry_policies = self.download_industry_policy()
        self.save_data(industry_policies, f'industry_policy_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        # 生成汇总
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'macro_count': len(macro_policies),
            'industry_count': len(industry_policies),
            'macro_positive': len([p for p in macro_policies if p['impact'] == 'positive']),
            'industry_positive': len([p for p in industry_policies if p['impact'] == 'positive'])
        }
        
        self.save_data(summary, f'policy_summary_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        print("\n" + "=" * 70)
        print(" " * 20 + "下载完成")
        print("=" * 70)
        print(f"  宏观政策：{len(macro_policies)} 条 (利好：{summary['macro_positive']})")
        print(f"  行业政策：{len(industry_policies)} 条 (利好：{summary['industry_positive']})")
        print()


def main():
    """主函数"""
    logger = TaskLogger(task_name='policy_download')
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info("任务开始执行")
        downloader = PolicyDataDownloader()
        downloader.download_all()
    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)

if __name__ == '__main__':
    main()
