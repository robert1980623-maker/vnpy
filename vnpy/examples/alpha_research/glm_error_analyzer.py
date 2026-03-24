#!/usr/bin/env python3
"""
GLM 错误分析器

使用本地 GLM 模型分析错误类型，提供智能判断
"""

import json
import requests
from typing import Dict, Optional


class GLMErrorAnalyzer:
    """GLM 错误分析器"""
    
    def __init__(self, model_url: str = "http://localhost:1234/v1/chat/completions", 
                 model_name: str = "glm-4.7-flash"):
        self.model_url = model_url
        self.model_name = model_name
        self.timeout = 30  # 30 秒超时
    
    def analyze(self, error_type: str, error_message: str, 
                context: Optional[str] = None) -> Dict:
        """
        分析错误类型
        
        Args:
            error_type: 错误类型 (如 TypeError, KeyError)
            error_message: 错误消息
            context: 可选的上下文信息 (如代码片段、日志)
        
        Returns:
            {
                'task_type': str,  # engineering/qa/trading/risk/data
                'confidence': float,  # 0-1 置信度
                'reasoning': str,  # 分析理由
                'suggested_agent': str  # 建议的 Agent
            }
        """
        prompt = self._build_prompt(error_type, error_message, context)
        
        try:
            response = requests.post(
                self.model_url,
                json={
                    "model": self.model_name,
                    "messages": [
                        {
                            "role": "system",
                            "content": self._get_system_prompt()
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.1,  # 低温度，确保输出稳定
                    "max_tokens": 500
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return self._parse_response(content)
            else:
                return self._fallback_result(error_type, error_message, f"API 错误：{response.status_code}")
        
        except requests.exceptions.Timeout:
            return self._fallback_result(error_type, error_message, "GLM 超时")
        except Exception as e:
            return self._fallback_result(error_type, error_message, f"异常：{str(e)}")
    
    def _get_system_prompt(self) -> str:
        """系统提示词"""
        return """你是一个专业的错误分析专家。请分析错误并判断类型。

可用的任务类型：
- engineering: 代码 bug (TypeError, KeyError, AttributeError 等)
- qa: 测试失败 (assertion error, test failed 等)
- trading: 交易相关 (order, position, trade 等)
- risk: 风控相关 (risk limit, stop loss 等)
- data: 数据相关 (download, timeout, data fetch 等)

请只返回 JSON 格式：
{
    "task_type": "类型",
    "confidence": 0.0-1.0,
    "reasoning": "分析理由",
    "suggested_agent": "建议的 Agent 名称"
}"""
    
    def _build_prompt(self, error_type: str, error_message: str, 
                     context: Optional[str]) -> str:
        """构建提示词"""
        prompt = f"""请分析以下错误：

错误类型：{error_type}
错误消息：{error_message}
"""
        if context:
            prompt += f"\n上下文信息：\n{context}"
        
        prompt += "\n\n请判断这是什么类型的任务，需要哪个 Agent 处理？"
        return prompt
    
    def _parse_response(self, content: str) -> Dict:
        """解析 GLM 响应"""
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return {
                    'task_type': result.get('task_type', 'engineering'),
                    'confidence': float(result.get('confidence', 0.8)),
                    'reasoning': result.get('reasoning', 'GLM 分析'),
                    'suggested_agent': result.get('suggested_agent', 'delta')
                }
            else:
                return {
                    'task_type': 'engineering',
                    'confidence': 0.5,
                    'reasoning': f'GLM 返回格式异常：{content[:100]}',
                    'suggested_agent': 'delta'
                }
        except Exception as e:
            return {
                'task_type': 'engineering',
                'confidence': 0.3,
                'reasoning': f'解析失败：{str(e)}',
                'suggested_agent': 'delta'
            }
    
    def _fallback_result(self, error_type: str, error_message: str, 
                        reason: str) -> Dict:
        """Fallback 结果"""
        return {
            'task_type': 'engineering',
            'confidence': 0.0,
            'reasoning': f'GLM 分析失败，使用默认规则。原因：{reason}',
            'suggested_agent': 'delta'
        }


def main():
    """测试 GLM 分析器"""
    analyzer = GLMErrorAnalyzer()
    
    # 测试用例
    test_cases = [
        {
            'error_type': 'TypeError',
            'error_message': "'NoneType' object is not subscriptable",
            'context': "data = None; print(data['key'])"
        },
        {
            'error_type': 'AssertionError',
            'error_message': "assert result == expected",
            'context': "def test_add(): assert add(1,2) == 3"
        },
        {
            'error_type': 'TimeoutError',
            'error_message': "Download timeout after 30s",
            'context': "fetch_stock_data('000001.SZ')"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"测试用例 {i}:")
        print(f"  错误类型：{case['error_type']}")
        print(f"  错误消息：{case['error_message']}")
        print(f"{'='*70}")
        
        result = analyzer.analyze(
            case['error_type'],
            case['error_message'],
            case.get('context')
        )
        
        print(f"分析结果:")
        print(f"  任务类型：{result['task_type']}")
        print(f"  置信度：{result['confidence']:.2f}")
        print(f"  建议 Agent: {result['suggested_agent']}")
        print(f"  分析理由：{result['reasoning'][:200]}")


if __name__ == '__main__':
    main()
