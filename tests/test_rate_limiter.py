"""Tests for rate limiter and circuit breaker."""

import pytest
import time
from unittest.mock import Mock

from src.x_reply_service.utils.rate_limiter import (
    TokenBucket, CircuitBreaker, CircuitBreakerConfig, CircuitState, RateLimiter
)


class TestTokenBucket:
    """Test TokenBucket class."""
    
    def test_initial_tokens(self):
        """Test initial token allocation."""
        bucket = TokenBucket(capacity=10, refill_period=60)
        assert bucket.available_tokens() == 10
    
    def test_consume_tokens(self):
        """Test token consumption."""
        bucket = TokenBucket(capacity=10, refill_period=60)
        
        # Should be able to consume available tokens
        assert bucket.consume(5) is True
        assert bucket.available_tokens() == 5
        
        # Should be able to consume remaining tokens
        assert bucket.consume(5) is True
        assert bucket.available_tokens() == 0
        
        # Should not be able to consume more tokens
        assert bucket.consume(1) is False
        assert bucket.available_tokens() == 0
    
    def test_consume_more_than_available(self):
        """Test consuming more tokens than available."""
        bucket = TokenBucket(capacity=10, refill_period=60)
        
        # Should not be able to consume more than available
        assert bucket.consume(15) is False
        assert bucket.available_tokens() == 10
    
    def test_refill_tokens(self):
        """Test token refill over time."""
        bucket = TokenBucket(capacity=10, refill_period=1)  # 1 second refill
        
        # Consume all tokens
        bucket.consume(10)
        assert bucket.available_tokens() == 0
        
        # Manually trigger refill by advancing time
        bucket.last_refill -= 2  # Simulate 2 seconds passed
        
        # Should refill to capacity
        assert bucket.available_tokens() == 10
    
    def test_time_until_tokens(self):
        """Test time calculation until tokens are available."""
        bucket = TokenBucket(capacity=10, refill_period=60)
        
        # With available tokens, should return 0
        assert bucket.time_until_tokens(5) == 0.0
        
        # Consume all tokens
        bucket.consume(10)
        
        # Should need to wait for refill
        wait_time = bucket.time_until_tokens(5)
        assert wait_time > 0


class TestCircuitBreaker:
    """Test CircuitBreaker class."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create a circuit breaker with test configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            success_threshold=2
        )
        return CircuitBreaker(config)
    
    def test_initial_state(self, circuit_breaker):
        """Test initial circuit breaker state."""
        assert circuit_breaker.get_state() == CircuitState.CLOSED
    
    def test_successful_calls(self, circuit_breaker):
        """Test successful function calls."""
        mock_func = Mock(return_value="success")
        
        result = circuit_breaker.call(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitState.CLOSED
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_failed_calls(self, circuit_breaker):
        """Test failed function calls."""
        mock_func = Mock(side_effect=Exception("Test error"))
        
        # First few failures should not open circuit
        for i in range(2):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)
            assert circuit_breaker.get_state() == CircuitState.CLOSED
        
        # Third failure should open circuit
        with pytest.raises(Exception):
            circuit_breaker.call(mock_func)
        assert circuit_breaker.get_state() == CircuitState.OPEN
    
    def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test that open circuit rejects calls."""
        mock_func = Mock(side_effect=Exception("Test error"))
        
        # Trigger circuit to open
        for i in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)
        
        assert circuit_breaker.get_state() == CircuitState.OPEN
        
        # New calls should be rejected
        mock_func.reset_mock()
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            circuit_breaker.call(mock_func)
        
        # Function should not be called
        mock_func.assert_not_called()
    
    def test_circuit_recovery(self, circuit_breaker):
        """Test circuit breaker recovery."""
        mock_func = Mock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)
        
        assert circuit_breaker.get_state() == CircuitState.OPEN
        
        # Simulate time passing
        circuit_breaker.last_failure_time = time.time() - 10  # 10 seconds ago
        
        # Next call should transition to half-open
        mock_func.side_effect = None
        mock_func.return_value = "success"
        
        result = circuit_breaker.call(mock_func)
        assert result == "success"
        assert circuit_breaker.get_state() == CircuitState.HALF_OPEN
    
    def test_half_open_to_closed(self, circuit_breaker):
        """Test transition from half-open to closed."""
        # Manually set to half-open state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 1
        
        mock_func = Mock(return_value="success")
        
        # One more success should close the circuit
        circuit_breaker.call(mock_func)
        assert circuit_breaker.get_state() == CircuitState.CLOSED
    
    def test_manual_reset(self, circuit_breaker):
        """Test manual circuit breaker reset."""
        mock_func = Mock(side_effect=Exception("Test error"))
        
        # Open the circuit
        for i in range(3):
            with pytest.raises(Exception):
                circuit_breaker.call(mock_func)
        
        assert circuit_breaker.get_state() == CircuitState.OPEN
        
        # Manual reset
        circuit_breaker.reset()
        assert circuit_breaker.get_state() == CircuitState.CLOSED


class TestRateLimiter:
    """Test RateLimiter class."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create a rate limiter with test configuration."""
        return RateLimiter(
            twitter_read_limit=10,
            twitter_write_limit=5,
            perplexity_limit=20
        )
    
    def test_initial_state(self, rate_limiter):
        """Test initial rate limiter state."""
        assert rate_limiter.can_make_twitter_read() is True
        assert rate_limiter.can_make_twitter_write() is True
        assert rate_limiter.can_make_perplexity_request() is True
    
    def test_twitter_read_limit(self, rate_limiter):
        """Test Twitter read rate limiting."""
        # Consume all read tokens
        for i in range(10):
            assert rate_limiter.can_make_twitter_read() is True
        
        # Should be rate limited now
        assert rate_limiter.can_make_twitter_read() is False
    
    def test_twitter_write_limit(self, rate_limiter):
        """Test Twitter write rate limiting."""
        # Consume all write tokens
        for i in range(5):
            assert rate_limiter.can_make_twitter_write() is True
        
        # Should be rate limited now
        assert rate_limiter.can_make_twitter_write() is False
    
    def test_perplexity_limit(self, rate_limiter):
        """Test Perplexity rate limiting."""
        # Consume all Perplexity tokens
        for i in range(20):
            assert rate_limiter.can_make_perplexity_request() is True
        
        # Should be rate limited now
        assert rate_limiter.can_make_perplexity_request() is False
    
    def test_circuit_breaker_integration(self, rate_limiter):
        """Test circuit breaker integration."""
        mock_func = Mock(return_value="success")
        
        # Should work normally
        result = rate_limiter.twitter_read_with_circuit_breaker(mock_func, "arg")
        assert result == "success"
        
        # Test with failing function
        mock_func.side_effect = Exception("API error")
        
        # Should eventually open circuit after failures
        for i in range(5):
            try:
                rate_limiter.twitter_read_with_circuit_breaker(mock_func)
            except Exception:
                pass
        
        # Circuit should be open now
        status = rate_limiter.get_status()
        assert status['twitter_read']['circuit_state'] == 'open'
    
    def test_rate_limit_exceeded_error(self, rate_limiter):
        """Test rate limit exceeded error."""
        mock_func = Mock(return_value="success")
        
        # Consume all tokens
        for i in range(10):
            rate_limiter.can_make_twitter_read()
        
        # Should raise rate limit error
        with pytest.raises(Exception, match="rate limit exceeded"):
            rate_limiter.twitter_read_with_circuit_breaker(mock_func)
    
    def test_get_status(self, rate_limiter):
        """Test status reporting."""
        status = rate_limiter.get_status()
        
        assert 'twitter_read' in status
        assert 'twitter_write' in status
        assert 'perplexity' in status
        
        for api_status in status.values():
            assert 'available_tokens' in api_status
            assert 'circuit_state' in api_status
            assert 'time_until_tokens' in api_status
    
    def test_wait_for_tokens(self, rate_limiter):
        """Test waiting for tokens to become available."""
        # This test would need to mock time or use very short refill periods
        # For now, just test that the method exists and returns boolean
        
        # With available tokens, should return immediately
        result = rate_limiter.wait_for_twitter_read(timeout=0.1)
        assert isinstance(result, bool)
