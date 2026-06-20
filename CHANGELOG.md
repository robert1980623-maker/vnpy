# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- 补齐核心模块测试覆盖（cross_sectional_engine, data_source_router, circuit_breaker）
- CI 配置（GitHub Actions）
- 配置管理统一化
- 统一错误处理 + 自定义异常体系
- Observability（metrics + logging）

## [1.0.0] - 2026-06-21

### Added
- **AI Readiness 文档体系**
  - `AGENTS.md` - 通用 AI agent 指南（324 行）
  - `CLAUDE.md` - Claude Code 操作指南（409 行）
  - `README.md` - 项目入口文档（249 行）
  - `docs/ARCHITECTURE.md` - 系统架构详解（555 行）

### Fixed
- **industry_rotation.py 4 个 P0 边界条件问题** (ad36ee58)
  - `safe_float()` 添加 `math.isinf()` 防护
  - `_normalize_symbol()` 北交所代码标准化（83/87/88/43 → .BSE）
  - `_calculate_industry_turnover()` 除零保护
  - 估值缓存穿透时添加 warning 日志

## [0.9.0] - 2026-04-15

### Added
- 深度代码审查报告 (2026-04-14)
- 项目优化全面升级 (v2.0)

### Fixed
- CSV→Parquet column name inconsistency bug (d3c6fd3c)
- 测试收集和 41 个测试失败问题 (c3933994)
  - file_lock 模块导入问题
  - test_quick.py 模块级 sys.exit(1) 问题
  - SQLite 并发锁定问题
  - IssueDB base_dir 隔离问题
- alpha/lab.py 假交易日期问题 (5939ec72)
- Manager 内存泄漏 (d4388e0e)
- 虚拟账户数据分裂问题 (988f6a68)
- SQLite+JSON 双写原子操作保证一致性 (80fcecc6)
- 数据库初始化文件锁保护 (50e272fe)
- delta_consumer 文件锁保护 (4dad025e)

## [0.8.0] - 2026-03-21

### Added
- 首席架构师自动工作流
- 架构师行动研究报告

### Changed
- 项目结构优化

## [0.7.0] - 2026-03-01

### Added
- 选股策略系统 API 文档
- 实盘应用计划
- 实盘快速启动指南
- 系统测试报告

### Changed
- 性能优化：并行下载 + 智能缓存 + 多数据源支持

## [0.6.0] - 2026-02-28

### Added
- 统一配置文件 config.yaml
- 快速开始指南 QUICKSTART.md
- 主入口脚本 main.py
- 项目审计报告

### Fixed
- 测试中发现的问题

## [0.5.0] - 2026-02-27

### Added
- 完整的选股策略系统实现
- 数据下载和回测脚本
- 增强数据下载功能
- 定时下载任务
- AKShare 依赖管理和诊断指南
- Baostock 作为备选数据源
- akshare-proxy-patch 解决限流问题
- 消息面数据获取功能
- 股票模拟交易功能

### Fixed
- download_all_data 函数缺少 night_mode 参数的问题

## [0.1.0] - 2026-02-26

### Added
- 初始项目结构
- 基础数据下载功能
- 示例代码和开发进度文档

---

## 版本说明

- **Major (x.0.0)**: 架构性变更，不向后兼容
- **Minor (0.x.0)**: 新增功能，向后兼容
- **Patch (0.0.x)**: Bug 修复，向后兼容

## 发布流程

1. 更新 CHANGELOG.md
2. 更新版本号（如有需要）
3. 创建 git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
4. 推送 tag: `git push origin v1.0.0`
5. 创建 GitHub Release

---

[Unreleased]: https://github.com/robert1980623-maker/vnpy/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/robert1980623-maker/vnpy/compare/v0.1.0...v0.5.0
[0.1.0]: https://github.com/robert1980623-maker/vnpy/releases/tag/v0.1.0
