#!/usr/bin/env python3
"""Health check script for the X.com Auto-Reply Service."""

import sys
import json
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.x_reply_service.core.service import XReplyService
from src.x_reply_service.config import load_config, validate_config
from src.x_reply_service.utils.logging import setup_logging


def main():
    """Perform comprehensive health check."""
    print("🏥 X.com Auto-Reply Service - Health Check")
    print("=" * 50)
    
    try:
        # Load configuration
        config = load_config()
        setup_logging(config.app.log_level, config.app.log_dir)
        
        # Validate configuration
        print("\n🔧 Configuration Check")
        config_errors = validate_config()
        if config_errors:
            print("❌ Configuration validation failed:")
            for error in config_errors:
                print(f"  • {error}")
            return False
        else:
            print("✅ Configuration is valid")
        
        # Initialize service
        print("\n🚀 Service Initialization")
        try:
            service = XReplyService(config, dry_run=True)
            print("✅ Service initialized successfully")
        except Exception as e:
            print(f"❌ Service initialization failed: {e}")
            return False
        
        # Perform health check
        print("\n🔍 Component Health Check")
        health = service.health_check()
        
        overall_healthy = True
        
        for component, info in health.get('components', {}).items():
            status = info['status']
            status_icon = "✅" if status == 'healthy' else "❌"
            print(f"  {status_icon} {component.title()}: {status}")
            
            if status != 'healthy':
                overall_healthy = False
                
                # Show additional details for unhealthy components
                if component == 'twitter':
                    rate_limits = info.get('rate_limits', {})
                    print(f"    Available tokens: {rate_limits.get('available_tokens', 'unknown')}")
                    print(f"    Circuit state: {rate_limits.get('circuit_state', 'unknown')}")
                elif component == 'perplexity':
                    rate_limits = info.get('rate_limits', {})
                    print(f"    Available tokens: {rate_limits.get('available_tokens', 'unknown')}")
                    print(f"    Circuit state: {rate_limits.get('circuit_state', 'unknown')}")
                elif component == 'filesystem':
                    print(f"    Data directory: {info.get('data_dir', 'unknown')}")
        
        # Service status
        print("\n📊 Service Status")
        status = service.get_status()
        
        print(f"  Dry run mode: {status['service']['dry_run']}")
        print(f"  Config valid: {status['service']['config_valid']}")
        
        # Last run information
        if 'last_run' in status and status['last_run']:
            last_run = status['last_run']
            print(f"  Last run: {last_run.get('last_run_time', 'Never')}")
            
            if 'last_run_stats' in last_run:
                stats = last_run['last_run_stats']
                print(f"    Tweets processed: {stats.get('tweets_processed', 0)}")
                print(f"    Replies posted: {stats.get('replies_posted', 0)}")
                print(f"    Errors: {stats.get('error_count', 0)}")
        else:
            print("  Last run: Never")
        
        # Rate limits
        print("\n⏱️  Rate Limit Status")
        rate_limits = status.get('rate_limits', {})
        
        for api, limits in rate_limits.items():
            print(f"  {api.replace('_', ' ').title()}:")
            print(f"    Available tokens: {limits.get('available_tokens', 0)}")
            print(f"    Circuit state: {limits.get('circuit_state', 'unknown')}")
            
            time_until_tokens = limits.get('time_until_tokens', 0)
            if time_until_tokens > 0:
                print(f"    Time until tokens: {time_until_tokens:.0f}s")
        
        # Configuration summary
        print("\n⚙️  Configuration Summary")
        print(f"  Max tweets per run: {config.selection.max_tweets_per_run}")
        print(f"  Min engagement threshold: {config.selection.min_engagement_threshold}")
        print(f"  Max tweet age: {config.selection.max_tweet_age_hours} hours")
        print(f"  Exclude retweets: {config.selection.exclude_retweets}")
        print(f"  Exclude replies: {config.selection.exclude_replies}")
        print(f"  Blacklisted users: {len(config.selection.blacklisted_users)}")
        print(f"  Blacklisted keywords: {len(config.selection.blacklisted_keywords)}")
        
        # Test generation (optional)
        print("\n🧪 Test Reply Generation")
        try:
            test_reply = service.reply_generator.test_generation(
                "This is a test tweet about artificial intelligence and its impact on society."
            )
            if test_reply:
                print("✅ Reply generation test successful")
                print(f"  Sample reply: {test_reply}")
            else:
                print("⚠️  Reply generation test failed")
                overall_healthy = False
        except Exception as e:
            print(f"⚠️  Reply generation test error: {e}")
            overall_healthy = False
        
        # Overall result
        print("\n" + "=" * 50)
        if overall_healthy:
            print("✅ Overall Health: HEALTHY")
            print("The service is ready to run!")
        else:
            print("❌ Overall Health: UNHEALTHY")
            print("Please address the issues above before running the service.")
        
        return overall_healthy
        
    except Exception as e:
        print(f"\n❌ Health check failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
