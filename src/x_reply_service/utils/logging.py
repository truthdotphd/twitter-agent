"""Logging configuration and utilities."""

import os
import sys
import logging
import structlog
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional
from prometheus_client import Counter, Histogram, Gauge


# Prometheus metrics
tweets_processed = Counter('tweets_processed_total', 'Total tweets processed')
replies_generated = Counter('replies_generated_total', 'Total replies generated')
replies_posted = Counter('replies_posted_total', 'Total replies posted')
api_errors = Counter('api_errors_total', 'Total API errors', ['api', 'error_type'])
processing_time = Histogram('processing_time_seconds', 'Time spent processing tweets')
queue_size = Gauge('queue_size', 'Number of tweets in processing queue')
safety_filter_triggers = Counter('safety_filter_triggers_total', 'Content safety filter triggers', ['reason'])


class MetricsLogger:
    """Handles metrics collection and logging."""
    
    @staticmethod
    def increment_tweets_processed(count: int = 1):
        """Increment tweets processed counter."""
        tweets_processed.inc(count)
    
    @staticmethod
    def increment_replies_generated(count: int = 1):
        """Increment replies generated counter."""
        replies_generated.inc(count)
    
    @staticmethod
    def increment_replies_posted(count: int = 1):
        """Increment replies posted counter."""
        replies_posted.inc(count)
    
    @staticmethod
    def increment_api_errors(api: str, error_type: str, count: int = 1):
        """Increment API errors counter."""
        api_errors.labels(api=api, error_type=error_type).inc(count)
    
    @staticmethod
    def record_processing_time(duration: float):
        """Record processing time."""
        processing_time.observe(duration)
    
    @staticmethod
    def set_queue_size(size: int):
        """Set current queue size."""
        queue_size.set(size)
    
    @staticmethod
    def increment_safety_filter_triggers(reason: str, count: int = 1):
        """Increment safety filter triggers."""
        safety_filter_triggers.labels(reason=reason).inc(count)


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """Setup structured logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path / "app.log"),
        ]
    )
    
    # Setup error log
    error_handler = logging.FileHandler(log_path / "error.log")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # Setup metrics log
    metrics_handler = logging.FileHandler(log_path / "metrics.log")
    metrics_handler.setLevel(logging.INFO)
    metrics_handler.setFormatter(logging.Formatter('%(message)s'))
    
    # Add handlers to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(error_handler)
    
    # Create metrics logger
    metrics_logger = logging.getLogger('metrics')
    metrics_logger.addHandler(metrics_handler)
    metrics_logger.setLevel(logging.INFO)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


def log_api_call(logger: structlog.BoundLogger, api_name: str, endpoint: str, 
                 duration: float, success: bool, error: Optional[str] = None) -> None:
    """Log API call details.
    
    Args:
        logger: Logger instance
        api_name: Name of the API (twitter, perplexity)
        endpoint: API endpoint called
        duration: Call duration in seconds
        success: Whether the call was successful
        error: Error message if call failed
    """
    log_data = {
        'api': api_name,
        'endpoint': endpoint,
        'duration_seconds': round(duration, 3),
        'success': success
    }
    
    if error:
        log_data['error'] = error
        logger.error("API call failed", **log_data)
        MetricsLogger.increment_api_errors(api_name, "request_failed")
    else:
        logger.info("API call completed", **log_data)


def log_tweet_processing(logger: structlog.BoundLogger, tweet_id: str, 
                        action: str, success: bool, details: Optional[Dict[str, Any]] = None) -> None:
    """Log tweet processing details.
    
    Args:
        logger: Logger instance
        tweet_id: Tweet ID being processed
        action: Action being performed (selected, reply_generated, reply_posted)
        success: Whether the action was successful
        details: Additional details to log
    """
    log_data = {
        'tweet_id': tweet_id,
        'action': action,
        'success': success
    }
    
    if details:
        log_data.update(details)
    
    if success:
        logger.info("Tweet processing step completed", **log_data)
    else:
        logger.warning("Tweet processing step failed", **log_data)


def log_safety_check(logger: structlog.BoundLogger, content: str, is_safe: bool, 
                     reason: Optional[str] = None, confidence: float = 1.0) -> None:
    """Log content safety check results.
    
    Args:
        logger: Logger instance
        content: Content that was checked (truncated for logging)
        is_safe: Whether content passed safety check
        reason: Reason for safety decision
        confidence: Confidence score
    """
    # Truncate content for logging
    content_preview = content[:100] + "..." if len(content) > 100 else content
    
    log_data = {
        'content_preview': content_preview,
        'is_safe': is_safe,
        'confidence': confidence
    }
    
    if reason:
        log_data['reason'] = reason
        if not is_safe:
            MetricsLogger.increment_safety_filter_triggers(reason)
    
    if is_safe:
        logger.debug("Content safety check passed", **log_data)
    else:
        logger.warning("Content safety check failed", **log_data)


def log_rate_limit_status(logger: structlog.BoundLogger, rate_limiter_status: Dict[str, Any]) -> None:
    """Log rate limiter status.
    
    Args:
        logger: Logger instance
        rate_limiter_status: Status from rate limiter
    """
    logger.info("Rate limiter status", **rate_limiter_status)


def log_processing_summary(logger: structlog.BoundLogger, run_id: str, 
                          tweets_fetched: int, tweets_processed: int, 
                          replies_generated: int, replies_posted: int, 
                          duration: float, errors: list) -> None:
    """Log processing run summary.
    
    Args:
        logger: Logger instance
        run_id: Unique run identifier
        tweets_fetched: Number of tweets fetched
        tweets_processed: Number of tweets processed
        replies_generated: Number of replies generated
        replies_posted: Number of replies posted
        duration: Total processing duration
        errors: List of errors encountered
    """
    success_rate = (replies_posted / tweets_processed * 100) if tweets_processed > 0 else 0
    
    summary_data = {
        'run_id': run_id,
        'tweets_fetched': tweets_fetched,
        'tweets_processed': tweets_processed,
        'replies_generated': replies_generated,
        'replies_posted': replies_posted,
        'duration_seconds': round(duration, 2),
        'success_rate_percent': round(success_rate, 1),
        'error_count': len(errors)
    }
    
    if errors:
        summary_data['errors'] = errors[:5]  # Log first 5 errors
    
    logger.info("Processing run completed", **summary_data)
    
    # Update metrics
    MetricsLogger.increment_tweets_processed(tweets_processed)
    MetricsLogger.increment_replies_generated(replies_generated)
    MetricsLogger.increment_replies_posted(replies_posted)
    MetricsLogger.record_processing_time(duration)


class ContextLogger:
    """Context manager for logging with additional context."""
    
    def __init__(self, logger: structlog.BoundLogger, **context):
        """Initialize context logger.
        
        Args:
            logger: Base logger
            **context: Additional context to bind
        """
        self.logger = logger.bind(**context)
        self.start_time = None
    
    def __enter__(self) -> structlog.BoundLogger:
        """Enter context and start timing."""
        self.start_time = datetime.now()
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and log duration."""
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            if exc_type:
                self.logger.error("Context completed with error", 
                                duration_seconds=duration, 
                                error_type=exc_type.__name__)
            else:
                self.logger.info("Context completed successfully", 
                               duration_seconds=duration)
