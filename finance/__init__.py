"""
Quinn Finance Framework
专业金融分析框架

使用方法:
    from report_generator import ReportGenerator
    gen = ReportGenerator()
    print(gen.generate_daily_report())
"""

from .report_generator import ReportGenerator, DataFetcher, TechnicalAnalyzer

__all__ = ['ReportGenerator', 'DataFetcher', 'TechnicalAnalyzer']
