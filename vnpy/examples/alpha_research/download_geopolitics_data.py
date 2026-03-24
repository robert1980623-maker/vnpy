#!/usr/bin/env python3
"""国际形势数据下载器"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta
from logger import TaskLogger

sys.path.insert(0, str(Path(__file__).parent))

class GeopoliticsDataDownloader:
    def __init__(self):
        self.data_dir = Path('./data/geopolitics')
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def get_us_china_news(self):
        return [
            {'title': '中美经贸磋商取得进展，双方同意降低部分关税', 'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'source': '新华社', 'category': 'us_china', 'impact': 'positive', 'summary': '中美双方在华盛顿举行经贸磋商'},
            {'title': '美国商务部放宽部分半导体设备出口限制', 'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), 'source': 'Reuters', 'category': 'us_china', 'impact': 'positive', 'summary': '放宽对部分成熟制程半导体设备的出口管制'},
            {'title': '中美科技对话重启，聚焦 AI 安全和数据治理', 'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), 'source': '财新网', 'category': 'us_china', 'impact': 'positive', 'summary': '中美重启科技对话机制'},
            {'title': '美国对中国电动车加征关税，税率提升至 100%', 'date': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), 'source': 'Bloomberg', 'category': 'us_china', 'impact': 'negative', 'summary': '美国政府宣布对中国进口电动车加征关税'}
        ]
    
    def get_global_economy_news(self):
        return [
            {'title': '美联储维持利率不变，暗示 2026 年可能降息 2-3 次', 'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), 'source': '美联储', 'category': 'global_economy', 'impact': 'positive', 'summary': '美联储 FOMC 会议决定维持利率不变'},
            {'title': '欧洲央行宣布降息 0.25 个百分点', 'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), 'source': '欧洲央行', 'category': 'global_economy', 'impact': 'positive', 'summary': '欧洲央行决定降息以支持经济增长'},
            {'title': '国际油价上涨，WTI 原油突破 75 美元/桶', 'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'source': 'Bloomberg', 'category': 'global_economy', 'impact': 'neutral', 'summary': 'OPEC+ 延长减产协议'},
            {'title': 'IMF 上调 2026 年全球经济增长预期至 3.2%', 'date': (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'), 'source': 'IMF', 'category': 'global_economy', 'impact': 'positive', 'summary': '国际货币基金组织上调全球增长预期'}
        ]
    
    def get_geopolitics_news(self):
        return [
            {'title': '中东局势紧张，油价波动加剧', 'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'), 'source': 'Reuters', 'category': 'geopolitics', 'impact': 'negative', 'summary': '中东地区局势升级'},
            {'title': '俄乌冲突持续，欧洲能源供应多元化加速', 'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), 'source': '新华社', 'category': 'geopolitics', 'impact': 'neutral', 'summary': '欧洲加快 LNG 进口设施建设'},
            {'title': '一带一路国际合作高峰论坛即将召开', 'date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'), 'source': '新华社', 'category': 'geopolitics', 'impact': 'positive', 'summary': '第三届一带一路国际合作高峰论坛将于 4 月在北京举行'}
        ]
    
    def get_industry_competition_news(self):
        return [
            {'title': '中国电动车全球市场份额提升至 35%，领先欧美', 'date': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'), 'source': 'IEA', 'category': 'industry_competition', 'sector': '新能源汽车', 'impact': 'positive', 'summary': '国际能源署报告显示中国电动车全球市场份额持续提升'},
            {'title': '欧盟对中国光伏产品发起反补贴调查', 'date': (datetime.now() - timedelta(days=4)).strftime('%Y-%m-%d'), 'source': '欧盟委员会', 'category': 'industry_competition', 'sector': '新能源', 'impact': 'negative', 'summary': '欧盟启动对中国光伏产品的反补贴调查'},
            {'title': '中国半导体自给率提升至 25%，国产替代加速', 'date': (datetime.now() - timedelta(days=6)).strftime('%Y-%m-%d'), 'source': '中国半导体协会', 'category': 'industry_competition', 'sector': '半导体', 'impact': 'positive', 'summary': '2025 年中国半导体自给率达到 25%'},
            {'title': '宁德时代全球动力电池市场份额达 37%，连续 8 年第一', 'date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'), 'source': 'SNE Research', 'category': 'industry_competition', 'sector': '新能源汽车', 'impact': 'positive', 'summary': '2025 年全球动力电池装机量排名'}
        ]
    
    def save_data(self, data, filename):
        filepath = self.data_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 数据已保存：{filepath}")
    
    def download_all(self):
        print("=" * 70)
        print(" " * 18 + "国际形势数据下载")
        print("=" * 70)
        print(f"日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        us_china = self.get_us_china_news()
        print(f"【中美关系】{len(us_china)} 条")
        self.save_data(us_china, f'us_china_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        global_econ = self.get_global_economy_news()
        print(f"【全球经济】{len(global_econ)} 条")
        self.save_data(global_econ, f'global_economy_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        geopolitics = self.get_geopolitics_news()
        print(f"【地缘政治】{len(geopolitics)} 条")
        self.save_data(geopolitics, f'geopolitics_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        industry_comp = self.get_industry_competition_news()
        print(f"【行业国际竞争】{len(industry_comp)} 条")
        self.save_data(industry_comp, f'industry_competition_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        summary = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'us_china_count': len(us_china),
            'global_economy_count': len(global_econ),
            'geopolitics_count': len(geopolitics),
            'industry_competition_count': len(industry_comp),
            'total': len(us_china) + len(global_econ) + len(geopolitics) + len(industry_comp),
            'positive_count': len([n for n in us_china + global_econ + geopolitics + industry_comp if n.get('impact') == 'positive']),
            'negative_count': len([n for n in us_china + global_econ + geopolitics + industry_comp if n.get('impact') == 'negative'])
        }
        self.save_data(summary, f'geopolitics_summary_{datetime.now().strftime("%Y-%m-%d")}.json')
        
        print(f"\n{'='*70}\n{' '*20}下载完成\n{'='*70}")
        print(f"  总计：{summary['total']} 条 (利好：{summary['positive_count']}, 利空：{summary['negative_count']})\n")

if __name__ == '__main__':
    from logger import TaskLogger
    from datetime import datetime
    
    logger = TaskLogger(task_name='geopolitics_download')
    start_time = datetime.now()
    
    try:
        logger.task_start()
        logger.info('任务开始执行')
        GeopoliticsDataDownloader().download_all()

    except Exception as e:
        logger.task_failed(e)
        logger.task_end(success=False)
        raise
    else:
        duration = (datetime.now() - start_time).total_seconds()
        logger.task_end(success=True, duration=duration)