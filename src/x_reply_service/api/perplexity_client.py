"""Perplexity API client for generating AI-powered replies."""

import time
import json
from typing import Optional, Dict, Any
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..models import APIError
from ..utils.logging import get_logger, log_api_call
from ..utils.rate_limiter import RateLimiter


class PerplexityClient:
    """Perplexity API client for AI-powered content generation."""
    
    BASE_URL = "https://api.perplexity.ai"
    
    def __init__(self, api_key: str, rate_limiter: RateLimiter):
        """Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key
            rate_limiter: Rate limiter instance
        """
        self.api_key = api_key
        self.rate_limiter = rate_limiter
        self.logger = get_logger("perplexity_client")
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "X-Reply-Service/1.0"
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        self.logger.info("Perplexity client initialized successfully")
    
    def verify_credentials(self) -> bool:
        """Verify Perplexity API credentials.
        
        Returns:
            True if credentials are valid, False otherwise
        """
        try:
            # Test with a simple query
            response = self.generate_reply(
                "Test query", 
                "This is a test to verify API credentials."
            )
            return response is not None
            
        except Exception as e:
            self.logger.error("Credential verification failed", error=str(e))
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((requests.exceptions.RequestException,))
    )
    def generate_reply(self, prompt: str, tweet_content: str, 
                      model: str = "llama-3.1-sonar-small-128k-online",
                      temperature: float = 0.7, 
                      max_tokens: int = 280) -> Optional[str]:
        """Generate a reply using Perplexity AI.
        
        Args:
            prompt: Base prompt template
            tweet_content: Tweet content to reply to
            model: Perplexity model to use
            temperature: Generation temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated reply text, or None if failed
        """
        try:
            start_time = time.time()
            
            # Format the prompt with tweet content
            formatted_prompt = prompt.format(tweet_content=tweet_content)
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful assistant that provides educational and "
                            "contrarian perspectives. Your responses should be thoughtful, "
                            "informative, and challenge conventional thinking while remaining "
                            "respectful and constructive. Keep responses under 280 characters "
                            "for social media. Use current information from web search when relevant."
                        )
                    },
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
                "search": True,  # Enable web search
                "return_citations": False,  # Don't include citations in response
                "return_images": False
            }
            
            def _make_request():
                response = self.session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    timeout=60
                )
                response.raise_for_status()
                return response
            
            response = self.rate_limiter.perplexity_with_circuit_breaker(_make_request)
            duration = time.time() - start_time
            
            # Parse response
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                reply_text = response_data['choices'][0]['message']['content'].strip()
                
                # Ensure reply fits in character limit
                if len(reply_text) > 280:
                    reply_text = reply_text[:277] + "..."
                
                log_api_call(self.logger, "perplexity", "generate_reply", 
                           duration, True)
                
                self.logger.info("Reply generated successfully",
                               model=model,
                               temperature=temperature,
                               input_length=len(tweet_content),
                               output_length=len(reply_text),
                               tokens_used=response_data.get('usage', {}).get('total_tokens', 0))
                
                return reply_text
            else:
                log_api_call(self.logger, "perplexity", "generate_reply", 
                           duration, False, "No choices in response")
                return None
                
        except requests.exceptions.HTTPError as e:
            duration = time.time() - start_time
            error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
            log_api_call(self.logger, "perplexity", "generate_reply", 
                       duration, False, error_msg)
            
            # Handle specific error codes
            if e.response.status_code == 401:
                self.logger.error("Perplexity API authentication failed")
            elif e.response.status_code == 429:
                self.logger.warning("Perplexity API rate limit exceeded")
                raise  # Let retry decorator handle this
            elif e.response.status_code >= 500:
                self.logger.error("Perplexity API server error")
                raise  # Let retry decorator handle this
            
            return None
            
        except requests.exceptions.Timeout as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "perplexity", "generate_reply", 
                       duration, False, "Request timeout")
            return None
            
        except requests.exceptions.RequestException as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "perplexity", "generate_reply", 
                       duration, False, str(e))
            raise  # Let retry decorator handle this
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "perplexity", "generate_reply", 
                       duration, False, str(e))
            self.logger.error("Unexpected error generating reply", error=str(e))
            return None
    
    def generate_multiple_replies(self, prompt: str, tweet_content: str, 
                                count: int = 3, **kwargs) -> list[str]:
        """Generate multiple reply options.
        
        Args:
            prompt: Base prompt template
            tweet_content: Tweet content to reply to
            count: Number of replies to generate
            **kwargs: Additional arguments for generate_reply
            
        Returns:
            List of generated replies
        """
        replies = []
        
        for i in range(count):
            try:
                # Vary temperature slightly for each generation
                temp = kwargs.get('temperature', 0.7) + (i * 0.1)
                temp = min(temp, 1.0)  # Cap at 1.0
                
                reply = self.generate_reply(
                    prompt, tweet_content, 
                    temperature=temp, 
                    **{k: v for k, v in kwargs.items() if k != 'temperature'}
                )
                
                if reply and reply not in replies:
                    replies.append(reply)
                    
            except Exception as e:
                self.logger.warning(f"Failed to generate reply {i+1}", error=str(e))
                continue
        
        self.logger.info("Generated multiple replies", 
                        requested=count, 
                        generated=len(replies))
        
        return replies
    
    def get_usage_stats(self) -> Optional[Dict[str, Any]]:
        """Get API usage statistics (if available).
        
        Returns:
            Usage statistics dictionary, or None if not available
        """
        try:
            # Note: Perplexity API may not have a dedicated usage endpoint
            # This is a placeholder for future implementation
            self.logger.info("Usage stats not available for Perplexity API")
            return None
            
        except Exception as e:
            self.logger.error("Failed to get usage stats", error=str(e))
            return None
    
    def test_connection(self) -> bool:
        """Test connection to Perplexity API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            start_time = time.time()
            
            def _test_request():
                # Simple test request
                payload = {
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello, this is a test."
                        }
                    ],
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "search": False
                }
                
                response = self.session.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    timeout=30
                )
                response.raise_for_status()
                return response
            
            response = self.rate_limiter.perplexity_with_circuit_breaker(_test_request)
            duration = time.time() - start_time
            
            log_api_call(self.logger, "perplexity", "test_connection", 
                       duration, True)
            return True
            
        except Exception as e:
            duration = time.time() - start_time
            log_api_call(self.logger, "perplexity", "test_connection", 
                       duration, False, str(e))
            return False
