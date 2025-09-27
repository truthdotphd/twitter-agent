#!/usr/bin/env python3
"""Main entry point for the X.com Auto-Reply Service."""

import sys
import click
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.x_reply_service.core.service import XReplyService
from src.x_reply_service.config import load_config, validate_config
from src.x_reply_service.utils.logging import setup_logging, get_logger


@click.command()
@click.option('--dry-run', is_flag=True, default=False,
              help='Run without actually posting replies')
@click.option('--verbose', '-v', is_flag=True, default=False,
              help='Enable verbose logging')
@click.option('--debug', is_flag=True, default=False,
              help='Enable debug logging')
@click.option('--test-mode', is_flag=True, default=False,
              help='Run in test mode with reduced tweet processing')
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration file')
@click.option('--status', is_flag=True, default=False,
              help='Show service status and exit')
@click.option('--health-check', is_flag=True, default=False,
              help='Perform health check and exit')
def main(dry_run, verbose, debug, test_mode, config, status, health_check):
    """X.com Auto-Reply Service - Automated intelligent tweet replies."""
    
    try:
        # Load configuration
        if config:
            # TODO: Support custom config path
            pass
        
        config_obj = load_config()
        
        # Adjust log level based on options
        if debug:
            config_obj.app.log_level = "DEBUG"
        elif verbose:
            config_obj.app.log_level = "INFO"
        
        # Setup logging
        setup_logging(config_obj.app.log_level, config_obj.app.log_dir)
        logger = get_logger("main")
        
        # Validate configuration
        config_errors = validate_config()
        if config_errors:
            logger.error("Configuration validation failed")
            for error in config_errors:
                click.echo(f"❌ {error}", err=True)
            sys.exit(1)
        
        # Adjust config for test mode
        if test_mode:
            config_obj.selection.max_tweets_per_run = min(2, config_obj.selection.max_tweets_per_run)
            config_obj.selection.min_engagement_threshold = 0
            logger.info("Running in test mode with reduced tweet processing")
        
        # Initialize service
        service = XReplyService(config_obj, dry_run=dry_run)
        
        # Handle status request
        if status:
            status_info = service.get_status()
            click.echo("📊 Service Status:")
            click.echo(f"  Dry Run: {status_info['service']['dry_run']}")
            click.echo(f"  Config Valid: {status_info['service']['config_valid']}")
            
            if 'last_run' in status_info and status_info['last_run']:
                last_run = status_info['last_run']
                click.echo(f"  Last Run: {last_run.get('last_run_time', 'Never')}")
                if 'last_run_stats' in last_run:
                    stats = last_run['last_run_stats']
                    click.echo(f"    Tweets Processed: {stats.get('tweets_processed', 0)}")
                    click.echo(f"    Replies Posted: {stats.get('replies_posted', 0)}")
            
            # Rate limit status
            rate_limits = status_info.get('rate_limits', {})
            for api, limits in rate_limits.items():
                click.echo(f"  {api.title()} API:")
                click.echo(f"    Available Tokens: {limits.get('available_tokens', 0)}")
                click.echo(f"    Circuit State: {limits.get('circuit_state', 'unknown')}")
            
            sys.exit(0)
        
        # Handle health check request
        if health_check:
            health = service.health_check()
            overall_status = health['overall']
            
            if overall_status == 'healthy':
                click.echo("✅ Service is healthy")
            else:
                click.echo("❌ Service is unhealthy")
            
            for component, info in health.get('components', {}).items():
                status_icon = "✅" if info['status'] == 'healthy' else "❌"
                click.echo(f"  {status_icon} {component.title()}: {info['status']}")
            
            sys.exit(0 if overall_status == 'healthy' else 1)
        
        # Run main service
        logger.info("Starting X Reply Service",
                   dry_run=dry_run,
                   test_mode=test_mode,
                   max_tweets=config_obj.selection.max_tweets_per_run)
        
        if dry_run:
            click.echo("🧪 Running in DRY RUN mode - no replies will be posted")
        
        if test_mode:
            click.echo("🔬 Running in TEST mode - processing fewer tweets")
        
        # Execute processing run
        result = service.run()
        
        # Display results
        click.echo("\n📈 Processing Results:")
        click.echo(f"  Run ID: {result.run_id}")
        click.echo(f"  Duration: {result.duration_seconds:.1f}s" if result.duration_seconds else "  Duration: N/A")
        click.echo(f"  Tweets Fetched: {result.tweets_fetched}")
        click.echo(f"  Tweets Processed: {result.tweets_processed}")
        click.echo(f"  Replies Generated: {result.replies_generated}")
        click.echo(f"  Replies Posted: {result.replies_posted}")
        click.echo(f"  Success Rate: {result.success_rate:.1f}%")
        
        if result.errors:
            click.echo(f"\n⚠️  Errors ({len(result.errors)}):")
            for error in result.errors[:5]:  # Show first 5 errors
                click.echo(f"  • {error}")
            if len(result.errors) > 5:
                click.echo(f"  ... and {len(result.errors) - 5} more errors")
        
        # Show sample replies in dry run mode
        if dry_run and result.processed_tweets:
            click.echo("\n💬 Sample Generated Replies:")
            for i, tweet in enumerate(result.processed_tweets[:3], 1):
                if tweet.generated_reply:
                    click.echo(f"\n  {i}. Original Tweet (@{tweet.author_username}):")
                    click.echo(f"     {tweet.text[:100]}{'...' if len(tweet.text) > 100 else ''}")
                    click.echo(f"     Generated Reply:")
                    click.echo(f"     {tweet.generated_reply}")
        
        # Exit with appropriate code
        if result.errors:
            logger.warning("Processing completed with errors", error_count=len(result.errors))
            sys.exit(1)
        else:
            logger.info("Processing completed successfully")
            click.echo("\n✅ Processing completed successfully!")
            sys.exit(0)
            
    except KeyboardInterrupt:
        click.echo("\n⏹️  Interrupted by user")
        sys.exit(130)
        
    except Exception as e:
        logger = get_logger("main")
        logger.error("Unexpected error", error=str(e))
        click.echo(f"\n❌ Unexpected error: {str(e)}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
