#!/usr/bin/env python3
"""
失败下载自动重试脚本 (Phase 4B)

Cron 任务：每天 03:00 自动重试失败的下载。
用法:
    python3 examples/alpha_research/retry_failed_downloads.py [--max-retries N] [--dry-run]

Cron 配置:
    0 3 * * * cd /Users/rowang/projects/vnpy && \
        python3 examples/alpha_research/retry_failed_downloads.py >> logs/retry_failed.log 2>&1
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

# 确保 examples/alpha_research 在 sys.path 中
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from atomic_failed_queue import AtomicFailedQueue
from data_downloader import DataDownloader, DownloaderConfig

# 默认失败队列文件路径
_DEFAULT_FAILED_FILE = _SCRIPT_DIR / 'failed_downloads.json'

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def retry_failed(
    max_retries: int = 3,
    dry_run: bool = False,
    failed_file: Path = _DEFAULT_FAILED_FILE,
) -> dict:
    """
    重试失败的下载

    Args:
        max_retries: 最大重试次数（超过的跳过）
        dry_run: 仅打印重试列表，不实际下载
        failed_file: 失败队列文件路径

    Returns:
        dict: 重试结果统计 {retried: N, succeeded: N, failed: N, skipped: N}
    """
    queue = AtomicFailedQueue(failed_file)
    failed = queue.get_all()

    if not failed:
        logger.info("✅ 失败队列为空，无需重试")
        return {'retried': 0, 'succeeded': 0, 'failed': 0, 'skipped': 0}

    # 筛选可重试的 symbol
    retry_list = []
    skipped_expired = 0
    for symbol, info in failed.items():
        # 向后兼容：retries 或 count
        retries = info.get('retries', info.get('count', 0))
        if retries < max_retries:
            retry_list.append(symbol)
        else:
            skipped_expired += 1

    if skipped_expired:
        logger.info(
            f"⏭️  跳过 {skipped_expired} 只已达最大重试次数 ({max_retries}) 的股票"
        )

    if not retry_list:
        logger.info("✅ 无可重试的下载（全部已达上限或队列为空）")
        return {
            'retried': 0, 'succeeded': 0, 'failed': 0,
            'skipped': skipped_expired,
        }

    logger.info(
        f"📋 准备重试 {len(retry_list)} 只失败股票 "
        f"(max_retries={max_retries}, dry_run={dry_run})"
    )

    if dry_run:
        for symbol in retry_list:
            info = failed[symbol]
            error = info.get('error', 'unknown')
            retries = info.get('retries', info.get('count', 0))
            logger.info(f"  [dry-run] {symbol}: retries={retries}, error={error}")
        return {
            'retried': len(retry_list), 'succeeded': 0, 'failed': 0,
            'skipped': skipped_expired,
        }

    # 初始化下载器（静默模式，无进度条）
    config = DownloaderConfig(
        max_workers=2,
        max_retries=2,
        base_delay=1.0,
        max_delay=10.0,
        progress=False,
        graceful_shutdown=True,
    )
    downloader = DataDownloader(config=config)

    succeeded = 0
    failed_count = 0

    for i, symbol in enumerate(retry_list):
        info = failed.get(symbol, {})
        retries = info.get('retries', info.get('count', 0))
        error = info.get('error', 'unknown')

        logger.info(
            f"[{i + 1}/{len(retry_list)}] 🔄 重试 {symbol} "
            f"(retries={retries}, last_error={error[:60]})"
        )

        try:
            result = downloader.download_single(symbol)
            if result.ok:
                logger.info(f"  ✅ {symbol} 成功 (source={result.source}, rows={result.rows})")
                # download_single 内部已在成功时调用 self.failed_queue.remove(symbol)
                succeeded += 1
            else:
                logger.warning(f"  ❌ {symbol} 失败: {result.error}")
                failed_count += 1
        except Exception as e:
            logger.error(f"  ❌ {symbol} 异常: {e}")
            failed_count += 1

    stats = {
        'retried': len(retry_list),
        'succeeded': succeeded,
        'failed': failed_count,
        'skipped': skipped_expired,
    }

    logger.info(
        f"📊 重试完成: 成功={succeeded}, 失败={failed_count}, "
        f"跳过(达上限)={skipped_expired}"
    )
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='失败下载自动重试脚本 (Phase 4B)',
    )
    parser.add_argument(
        '--max-retries', type=int, default=3,
        help='单只股票最大重试次数（默认 3）',
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='仅打印重试列表，不实际下载',
    )
    parser.add_argument(
        '--failed-file', type=str, default=str(_DEFAULT_FAILED_FILE),
        help=f'失败队列文件路径（默认 { _DEFAULT_FAILED_FILE }）',
    )
    args = parser.parse_args()

    logger.info(f"🚀 失败下载重试任务启动 ({datetime.now().isoformat()})")

    stats = retry_failed(
        max_retries=args.max_retries,
        dry_run=args.dry_run,
        failed_file=Path(args.failed_file),
    )

    logger.info(f"🏁 任务结束: {stats}")

    # 退出码：有失败则返回 1
    sys.exit(1 if stats.get('failed', 0) > 0 else 0)


if __name__ == '__main__':
    main()
