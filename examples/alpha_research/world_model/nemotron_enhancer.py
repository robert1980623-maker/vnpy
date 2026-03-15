#!/usr/bin/env python3
"""
使用 glm-4.7-flash 增强预测分析结果

功能:
- 解释统计结果
- 生成自然语言报告
- 优化告警文案
- 提供深度洞察

模型：lmstudio/zai-org/glm-4.7-flash (本地)
成本：¥0
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

class NemotronEnhancer:
    """glm-4.7-flash 增强器"""
    
    def __init__(self):
        self.model = "lmstudio/zai-org/glm-4.7-flash"
        self.api_url = "http://localhost:1234/v1/chat/completions"
        self.project_dir = Path(__file__).parent.parent
    
    def enhance_prediction(self, prediction_result: dict) -> str:
        """增强预测结果"""
        
        prompt = f"""你是一个专业的系统分析助手。请解释以下预测结果：

预测数据:
{json.dumps(prediction_result, ensure_ascii=False, indent=2)}

请用中文生成一份易懂的分析报告，包括:
1. 当前状态解读
2. 趋势分析
3. 未来预测
4. 建议操作

要求：
- 简洁明了 (200 字以内)
- 使用 emoji 增强可读性
- 避免技术术语"""

        return self._call_nemotron(prompt)
    
    def enhance_pattern(self, pattern_result: dict) -> str:
        """增强模式识别结果"""
        
        prompt = f"""你是一个专业的行为分析助手。请分析以下模式：

模式数据:
{json.dumps(pattern_result, ensure_ascii=False, indent=2)}

请用中文生成一份洞察报告，包括:
1. 模式描述
2. 可能的原因
3. 优化建议

要求：
- 简洁明了 (150 字以内)
- 实用建议
- 使用 emoji"""

        return self._call_nemotron(prompt)
    
    def enhance_alert(self, alert: dict) -> str:
        """增强告警文案"""
        
        prompt = f"""你是一个专业的运维助手。请优化以下告警：

告警数据:
{json.dumps(alert, ensure_ascii=False, indent=2)}

请用中文生成一份友好的告警通知，包括:
1. 当前状态
2. 可能原因
3. 影响评估
4. 建议操作
5. 紧急程度

要求：
- 语气友好但专业
- 避免引起恐慌
- 提供可操作建议
- 使用 emoji"""

        return self._call_nemotron(prompt)
    
    def generate_hourly_report(self, system_state: dict) -> str:
        """生成小时报告"""
        
        prompt = f"""你是一个专业的系统监控助手。请根据以下数据生成小时报告：

系统状态:
{json.dumps(system_state, ensure_ascii=False, indent=2)}
时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}

请用中文生成一份简洁的小时报告，包括:
1. 📊 系统整体状态
2. ✅ 正常运行的组件
3. ⚠️ 需要关注的项
4. 📈 趋势分析
5. 💡 建议

要求：
- 简洁明了 (300 字以内)
- 使用 emoji
- 适合 Slack 发送
- 语气友好专业"""

        return self._call_nemotron(prompt)
    
    def _call_nemotron(self, prompt: str) -> str:
        """调用 glm-4.7-flash"""
        
        try:
            cmd = f'''
            curl -s {self.api_url} \\
              -H "Content-Type: application/json" \\
              -d '{{
                "model": "{self.model}",
                "messages": [{{"role": "user", "content": {json.dumps(prompt)}}}],
                "temperature": 0.3,
                "max_tokens": 600
              }}' | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
            '''
            
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return f"⚠️ nemotron 调用失败：{result.stderr}"
        
        except Exception as e:
            return f"⚠️ 错误：{e}"


if __name__ == '__main__':
    # 测试
    enhancer = NemotronEnhancer()
    
    # 测试预测增强
    prediction = {
        'trend': 'increasing',
        'growth_rate': 0.067,
        'forecast': [0.97, 0.97, 0.98]
    }
    
    print("=== 预测增强测试 ===\n")
    enhanced = enhancer.enhance_prediction(prediction)
    print(enhanced)
