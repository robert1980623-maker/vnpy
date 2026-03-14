#!/usr/bin/env python3
"""
GLM 错误分析器测试
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from glm_error_analyzer import GLMErrorAnalyzer


class TestGLMErrorAnalyzer:
    """GLM 错误分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器"""
        return GLMErrorAnalyzer()
    
    def test_analyze_type_error(self, analyzer):
        """测试 TypeError 分析"""
        result = analyzer.analyze(
            error_type='TypeError',
            error_message="'NoneType' object is not subscriptable",
            context="data = None; print(data['key'])"
        )
        
        assert 'task_type' in result
        assert 'confidence' in result
        assert 'reasoning' in result
        assert 'suggested_agent' in result
    
    def test_analyze_assertion_error(self, analyzer):
        """测试 AssertionError 分析"""
        result = analyzer.analyze(
            error_type='AssertionError',
            error_message='assert result == expected',
            context='def test_add(): assert add(1,2) == 3'
        )
        
        assert 'task_type' in result
        assert result['task_type'] in ['qa', 'engineering']
    
    def test_analyze_timeout_error(self, analyzer):
        """测试 TimeoutError 分析"""
        result = analyzer.analyze(
            error_type='TimeoutError',
            error_message='Download timeout after 30s',
            context='fetch_stock_data'
        )
        
        assert 'task_type' in result
        assert result['task_type'] in ['data', 'engineering']
    
    def test_fallback_on_timeout(self):
        """测试超时 fallback"""
        analyzer = GLMErrorAnalyzer(
            model_url="http://localhost:9999/v1/chat/completions"
        )
        analyzer.timeout = 1  # 1 秒超时
        
        result = analyzer.analyze(
            error_type='Error',
            error_message='Test error'
        )
        
        assert result['task_type'] == 'engineering'
        assert result['confidence'] == 0.0
    
    def test_parse_malformed_json(self, analyzer):
        """测试解析异常 JSON"""
        result = analyzer._parse_response("这不是 JSON")
        
        assert result['task_type'] == 'engineering'
        assert result['confidence'] <= 0.5
    
    def test_parse_valid_json(self, analyzer):
        """测试解析有效 JSON"""
        json_str = '''
        {
            "task_type": "qa",
            "confidence": 0.95,
            "reasoning": "测试失败",
            "suggested_agent": "qa"
        }
        '''
        result = analyzer._parse_response(json_str)
        
        assert result['task_type'] == 'qa'
        assert result['confidence'] == 0.95
        assert result['suggested_agent'] == 'qa'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
