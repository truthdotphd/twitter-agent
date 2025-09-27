"""Rate limiting and circuit breaker utilities."""

import time
import threading
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 300  # 5 minutes
    success_threshold: int = 3   # For half-open state


class TokenBucket:
    """Token bucket rate limiter implementation."""
    
    def __init__(self, capacity: int, refill_period: int, initial_tokens: Optional[int] = None):
        """Initialize token bucket.
        
        Args:
            capacity: Maximum number of tokens
            refill_period: Time in seconds to refill the bucket
            initial_tokens: Initial number of tokens (defaults to capacity)
        """
        self.capacity = capacity
        self.tokens = initial_tokens if initial_tokens is not None else capacity
        self.refill_period = refill_period
        self.last_refill = time.time()
        self._lock = threading.Lock()
    
    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        with self._lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        time_passed = now - self.last_refill
        
        if time_passed >= self.refill_period:
            # Calculate how many full periods have passed
            periods = int(time_passed / self.refill_period)
            tokens_to_add = periods * self.capacity
            
            self.tokens = min(self.capacity, self.tokens + tokens_to_add)
            self.last_refill = now
    
    def available_tokens(self) -> int:
        """Get number of available tokens."""
        with self._lock:
            self._refill()
            return self.tokens
    
    def time_until_tokens(self, required_tokens: int) -> float:
        """Get time in seconds until required tokens are available."""
        with self._lock:
            self._refill()
            
            if self.tokens >= required_tokens:
                return 0.0
            
            tokens_needed = required_tokens - self.tokens
            periods_needed = (tokens_needed + self.capacity - 1) // self.capacity  # Ceiling division
            
            return periods_needed * self.refill_period


class CircuitBreaker:
    """Circuit breaker implementation for API protection."""
    
    def __init__(self, config: CircuitBreakerConfig):
        """Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise Exception(f"Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt to reset."""
        if self.last_failure_time is None:
            return False
        
        return (time.time() - self.last_failure_time) >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful operation."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
    
    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state
    
    def reset(self):
        """Manually reset circuit breaker."""
        with self._lock:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


class RateLimiter:
    """Comprehensive rate limiter for multiple APIs."""
    
    def __init__(self, twitter_read_limit: int = 240, twitter_write_limit: int = 240, 
                 perplexity_limit: int = 480):
        """Initialize rate limiter.
        
        Args:
            twitter_read_limit: Twitter read requests per 15 minutes
            twitter_write_limit: Twitter write requests per 15 minutes
            perplexity_limit: Perplexity requests per hour
        """
        # Twitter rate limits (15-minute windows)
        self.twitter_read = TokenBucket(twitter_read_limit, 900)  # 15 minutes
        self.twitter_write = TokenBucket(twitter_write_limit, 900)  # 15 minutes
        
        # Perplexity rate limits (1-hour window)
        self.perplexity = TokenBucket(perplexity_limit, 3600)  # 1 hour
        
        # Circuit breakers for each API
        self.twitter_circuit = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            success_threshold=3
        ))
        
        self.perplexity_circuit = CircuitBreaker(CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=600,  # 10 minutes
            success_threshold=2
        ))
    
    def can_make_twitter_read(self) -> bool:
        """Check if Twitter read request can be made."""
        return (self.twitter_circuit.get_state() != CircuitState.OPEN and 
                self.twitter_read.consume(1))
    
    def can_make_twitter_write(self) -> bool:
        """Check if Twitter write request can be made."""
        return (self.twitter_circuit.get_state() != CircuitState.OPEN and 
                self.twitter_write.consume(1))
    
    def can_make_perplexity_request(self) -> bool:
        """Check if Perplexity request can be made."""
        return (self.perplexity_circuit.get_state() != CircuitState.OPEN and 
                self.perplexity.consume(1))
    
    def twitter_read_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute Twitter read request with circuit breaker."""
        if not self.can_make_twitter_read():
            raise Exception("Twitter read rate limit exceeded or circuit breaker open")
        
        return self.twitter_circuit.call(func, *args, **kwargs)
    
    def twitter_write_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute Twitter write request with circuit breaker."""
        if not self.can_make_twitter_write():
            raise Exception("Twitter write rate limit exceeded or circuit breaker open")
        
        return self.twitter_circuit.call(func, *args, **kwargs)
    
    def perplexity_with_circuit_breaker(self, func, *args, **kwargs):
        """Execute Perplexity request with circuit breaker."""
        if not self.can_make_perplexity_request():
            raise Exception("Perplexity rate limit exceeded or circuit breaker open")
        
        return self.perplexity_circuit.call(func, *args, **kwargs)
    
    def get_status(self) -> Dict[str, any]:
        """Get current rate limiter status."""
        return {
            'twitter_read': {
                'available_tokens': self.twitter_read.available_tokens(),
                'circuit_state': self.twitter_circuit.get_state().value,
                'time_until_tokens': self.twitter_read.time_until_tokens(1)
            },
            'twitter_write': {
                'available_tokens': self.twitter_write.available_tokens(),
                'circuit_state': self.twitter_circuit.get_state().value,
                'time_until_tokens': self.twitter_write.time_until_tokens(1)
            },
            'perplexity': {
                'available_tokens': self.perplexity.available_tokens(),
                'circuit_state': self.perplexity_circuit.get_state().value,
                'time_until_tokens': self.perplexity.time_until_tokens(1)
            }
        }
    
    def wait_for_twitter_read(self, timeout: float = 300) -> bool:
        """Wait for Twitter read tokens to become available.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if tokens became available, False if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.can_make_twitter_read():
                return True
            
            wait_time = min(60, self.twitter_read.time_until_tokens(1))
            time.sleep(wait_time)
        
        return False
    
    def wait_for_twitter_write(self, timeout: float = 300) -> bool:
        """Wait for Twitter write tokens to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.can_make_twitter_write():
                return True
            
            wait_time = min(60, self.twitter_write.time_until_tokens(1))
            time.sleep(wait_time)
        
        return False
    
    def wait_for_perplexity(self, timeout: float = 600) -> bool:
        """Wait for Perplexity tokens to become available."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.can_make_perplexity_request():
                return True
            
            wait_time = min(300, self.perplexity.time_until_tokens(1))
            time.sleep(wait_time)
        
        return False
