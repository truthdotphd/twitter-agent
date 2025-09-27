#!/usr/bin/env python3
"""Cleanup script for old data and logs."""

import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.x_reply_service.config import load_config


def cleanup_processed_tweets(data_dir: Path, days: int) -> int:
    """Clean up old processed tweets.
    
    Args:
        data_dir: Data directory path
        days: Number of days to keep
        
    Returns:
        Number of entries removed
    """
    processed_tweets_file = data_dir / "processed_tweets.jsonl"
    
    if not processed_tweets_file.exists():
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    kept_entries = []
    removed_count = 0
    
    with open(processed_tweets_file, 'r') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                processed_time = datetime.fromisoformat(data.get('processing_timestamp', ''))
                
                if processed_time >= cutoff_date:
                    kept_entries.append(line)
                else:
                    removed_count += 1
                    
            except (json.JSONDecodeError, ValueError, KeyError):
                # Keep malformed entries
                kept_entries.append(line)
    
    # Write back the kept entries
    with open(processed_tweets_file, 'w') as f:
        f.writelines(kept_entries)
    
    return removed_count


def cleanup_logs(log_dir: Path, days: int) -> int:
    """Clean up old log files.
    
    Args:
        log_dir: Log directory path
        days: Number of days to keep
        
    Returns:
        Number of files removed
    """
    if not log_dir.exists():
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=days)
    removed_count = 0
    
    for log_file in log_dir.glob("*.log*"):
        try:
            # Check file modification time
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_time < cutoff_date:
                log_file.unlink()
                removed_count += 1
                
        except Exception as e:
            print(f"Warning: Could not process {log_file}: {e}")
    
    return removed_count


def cleanup_temp_files(base_dir: Path) -> int:
    """Clean up temporary files.
    
    Args:
        base_dir: Base directory to search
        
    Returns:
        Number of files removed
    """
    removed_count = 0
    
    # Common temporary file patterns
    temp_patterns = [
        "*.tmp",
        "*.temp",
        "*~",
        ".DS_Store",
        "Thumbs.db",
        "*.pyc",
        "__pycache__"
    ]
    
    for pattern in temp_patterns:
        for temp_file in base_dir.rglob(pattern):
            try:
                if temp_file.is_file():
                    temp_file.unlink()
                    removed_count += 1
                elif temp_file.is_dir():
                    # Remove empty __pycache__ directories
                    if pattern == "__pycache__" and not any(temp_file.iterdir()):
                        temp_file.rmdir()
                        removed_count += 1
            except Exception as e:
                print(f"Warning: Could not remove {temp_file}: {e}")
    
    return removed_count


def get_directory_size(path: Path) -> int:
    """Get total size of directory in bytes.
    
    Args:
        path: Directory path
        
    Returns:
        Total size in bytes
    """
    if not path.exists():
        return 0
    
    total_size = 0
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total_size += file_path.stat().st_size
            except Exception:
                pass
    
    return total_size


def format_size(size_bytes: int) -> str:
    """Format size in human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description="Clean up old data and logs")
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to keep (default: 30)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be cleaned without actually doing it')
    parser.add_argument('--logs-only', action='store_true',
                       help='Only clean log files')
    parser.add_argument('--data-only', action='store_true',
                       help='Only clean data files')
    
    args = parser.parse_args()
    
    print("🧹 X.com Auto-Reply Service - Cleanup")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        data_dir = Path(config.app.data_dir)
        log_dir = Path(config.app.log_dir)
        base_dir = Path(".")
        
        print(f"Data directory: {data_dir}")
        print(f"Log directory: {log_dir}")
        print(f"Keeping files newer than {args.days} days")
        
        if args.dry_run:
            print("🧪 DRY RUN MODE - No files will be actually removed")
        
        print()
        
        # Show current sizes
        data_size_before = get_directory_size(data_dir)
        log_size_before = get_directory_size(log_dir)
        
        print(f"Current data directory size: {format_size(data_size_before)}")
        print(f"Current log directory size: {format_size(log_size_before)}")
        print()
        
        total_removed = 0
        
        # Clean processed tweets
        if not args.logs_only:
            print("🗂️  Cleaning processed tweets...")
            if not args.dry_run:
                tweets_removed = cleanup_processed_tweets(data_dir, args.days)
                print(f"  Removed {tweets_removed} old tweet entries")
                total_removed += tweets_removed
            else:
                print("  Would clean old processed tweets")
        
        # Clean log files
        if not args.data_only:
            print("📝 Cleaning log files...")
            if not args.dry_run:
                logs_removed = cleanup_logs(log_dir, args.days)
                print(f"  Removed {logs_removed} old log files")
                total_removed += logs_removed
            else:
                print("  Would clean old log files")
        
        # Clean temporary files
        if not args.logs_only and not args.data_only:
            print("🗑️  Cleaning temporary files...")
            if not args.dry_run:
                temp_removed = cleanup_temp_files(base_dir)
                print(f"  Removed {temp_removed} temporary files")
                total_removed += temp_removed
            else:
                print("  Would clean temporary files")
        
        if not args.dry_run:
            # Show final sizes
            data_size_after = get_directory_size(data_dir)
            log_size_after = get_directory_size(log_dir)
            
            data_saved = data_size_before - data_size_after
            log_saved = log_size_before - log_size_after
            total_saved = data_saved + log_saved
            
            print()
            print("📊 Cleanup Results:")
            print(f"  Total items removed: {total_removed}")
            print(f"  Data space saved: {format_size(data_saved)}")
            print(f"  Log space saved: {format_size(log_saved)}")
            print(f"  Total space saved: {format_size(total_saved)}")
            print()
            print(f"Final data directory size: {format_size(data_size_after)}")
            print(f"Final log directory size: {format_size(log_size_after)}")
        
        print("\n✅ Cleanup completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
