"""AI-powered reply generation using Perplexity API."""

import re
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models import Tweet, ProcessedTweet, ReplyConfig, SafetyCheckResult
from ..api.perplexity_client import PerplexityClient
from ..utils.security import ContentSafetyFilter
from ..utils.logging import get_logger, log_safety_check


class ReplyGenerator:
    """Generates AI-powered replies to tweets using Perplexity API."""
    
    def __init__(self, perplexity_client: PerplexityClient, config: ReplyConfig):
        """Initialize reply generator.
        
        Args:
            perplexity_client: Perplexity API client
            config: Reply generation configuration
        """
        self.client = perplexity_client
        self.config = config
        self.safety_filter = ContentSafetyFilter()
        self.logger = get_logger("reply_generator")
        
        self.logger.info("Reply generator initialized",
                        model=config.model,
                        temperature=config.temperature,
                        max_length=config.max_reply_length)
    
    def generate_reply(self, tweet: ProcessedTweet) -> Optional[str]:
        """Generate a reply for a tweet.
        
        Args:
            tweet: Tweet to generate reply for
            
        Returns:
            Generated reply text, or None if generation failed
        """
        try:
            self.logger.info("Generating reply", 
                           tweet_id=tweet.id,
                           author=tweet.author_username)
            
            # Extract context and enhance prompt
            enhanced_prompt = self._create_enhanced_prompt(tweet)
            
            # Generate reply using Perplexity
            reply = self.client.generate_reply(
                prompt=enhanced_prompt,
                tweet_content=tweet.text,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_reply_length
            )
            
            if not reply:
                self.logger.warning("No reply generated", tweet_id=tweet.id)
                return None
            
            # Clean and validate reply
            cleaned_reply = self._clean_reply(reply)
            
            # Safety check
            safety_result = self.safety_filter.is_safe_content(cleaned_reply)
            log_safety_check(self.logger, cleaned_reply, 
                           safety_result.is_safe, safety_result.reason, 
                           safety_result.confidence)
            
            if not safety_result.is_safe:
                self.logger.warning("Generated reply failed safety check",
                                  tweet_id=tweet.id,
                                  reason=safety_result.reason)
                return None
            
            # Final length check
            if len(cleaned_reply) > self.config.max_reply_length:
                cleaned_reply = cleaned_reply[:self.config.max_reply_length-3] + "..."
            
            self.logger.info("Reply generated successfully",
                           tweet_id=tweet.id,
                           reply_length=len(cleaned_reply),
                           safety_confidence=safety_result.confidence)
            
            return cleaned_reply
            
        except Exception as e:
            self.logger.error("Failed to generate reply",
                            tweet_id=tweet.id,
                            error=str(e))
            return None
    
    def generate_multiple_replies(self, tweet: ProcessedTweet, 
                                count: int = 3) -> List[str]:
        """Generate multiple reply options for a tweet.
        
        Args:
            tweet: Tweet to generate replies for
            count: Number of replies to generate
            
        Returns:
            List of generated replies
        """
        try:
            self.logger.info("Generating multiple replies",
                           tweet_id=tweet.id,
                           count=count)
            
            enhanced_prompt = self._create_enhanced_prompt(tweet)
            
            # Generate multiple replies with slight temperature variations
            replies = self.client.generate_multiple_replies(
                prompt=enhanced_prompt,
                tweet_content=tweet.text,
                count=count,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_reply_length
            )
            
            # Clean and filter replies
            safe_replies = []
            for reply in replies:
                cleaned_reply = self._clean_reply(reply)
                safety_result = self.safety_filter.is_safe_content(cleaned_reply)
                
                if safety_result.is_safe and len(cleaned_reply) <= self.config.max_reply_length:
                    safe_replies.append(cleaned_reply)
            
            self.logger.info("Multiple replies generated",
                           tweet_id=tweet.id,
                           requested=count,
                           generated=len(replies),
                           safe_replies=len(safe_replies))
            
            return safe_replies
            
        except Exception as e:
            self.logger.error("Failed to generate multiple replies",
                            tweet_id=tweet.id,
                            error=str(e))
            return []
    
    def _create_enhanced_prompt(self, tweet: ProcessedTweet) -> str:
        """Create enhanced prompt with context from tweet.
        
        Args:
            tweet: Tweet to create prompt for
            
        Returns:
            Enhanced prompt string
        """
        # Extract context from tweet
        context_parts = []
        
        # Topic detection from context annotations
        if tweet.context_annotations:
            topics = []
            for annotation in tweet.context_annotations:
                if annotation.entity and 'name' in annotation.entity:
                    topics.append(annotation.entity['name'])
            if topics:
                context_parts.append(f"Topics: {', '.join(topics[:3])}")
        
        # Engagement level context
        total_engagement = sum(tweet.public_metrics.dict().values())
        if total_engagement > 100:
            context_parts.append("High engagement tweet")
        elif total_engagement > 50:
            context_parts.append("Moderate engagement tweet")
        
        # Time context
        hours_old = (datetime.now() - tweet.created_at).total_seconds() / 3600
        if hours_old < 1:
            context_parts.append("Recent tweet")
        elif hours_old < 6:
            context_parts.append("Posted today")
        
        # Author context (if we had more data)
        context_parts.append(f"Author: @{tweet.author_username}")
        
        context = "; ".join(context_parts) if context_parts else "General discussion"
        
        # Create enhanced prompt
        enhanced_prompt = f"""
{self.config.base_prompt}

Context: {context}
Tweet: "{tweet.text}"

Guidelines:
- Keep response under {self.config.max_reply_length} characters
- Provide educational value with facts or insights
- Challenge conventional thinking respectfully
- Use current information when relevant
- Be engaging and thought-provoking
- Avoid political extremes or controversial topics
- Don't repeat the original tweet's content
- Make it conversational and authentic
"""
        
        return enhanced_prompt.strip()
    
    def _clean_reply(self, reply: str) -> str:
        """Clean and format reply text.
        
        Args:
            reply: Raw reply text
            
        Returns:
            Cleaned reply text
        """
        if not reply:
            return ""
        
        # Remove leading/trailing whitespace
        reply = reply.strip()
        
        # Remove quotes if the entire reply is quoted
        if reply.startswith('"') and reply.endswith('"'):
            reply = reply[1:-1].strip()
        
        # Remove common AI-generated prefixes
        prefixes_to_remove = [
            "Here's a reply:",
            "Reply:",
            "Response:",
            "Here's an impactful reply:",
            "An impactful reply would be:",
        ]
        
        for prefix in prefixes_to_remove:
            if reply.lower().startswith(prefix.lower()):
                reply = reply[len(prefix):].strip()
        
        # Clean up excessive punctuation
        reply = re.sub(r'[!]{3,}', '!!', reply)
        reply = re.sub(r'[?]{3,}', '??', reply)
        reply = re.sub(r'\.{4,}', '...', reply)
        
        # Remove excessive whitespace
        reply = re.sub(r'\s+', ' ', reply)
        
        # Ensure proper sentence structure
        if reply and not reply[0].isupper():
            reply = reply[0].upper() + reply[1:]
        
        # Add period if missing and doesn't end with punctuation
        if reply and reply[-1] not in '.!?':
            reply += '.'
        
        return reply
    
    def _extract_tweet_topics(self, tweet: ProcessedTweet) -> List[str]:
        """Extract topics from tweet content.
        
        Args:
            tweet: Tweet to extract topics from
            
        Returns:
            List of identified topics
        """
        topics = []
        
        # Extract from context annotations
        if tweet.context_annotations:
            for annotation in tweet.context_annotations:
                if annotation.entity and 'name' in annotation.entity:
                    topics.append(annotation.entity['name'])
        
        # Extract hashtags
        hashtag_pattern = re.compile(r'#(\w+)')
        hashtags = hashtag_pattern.findall(tweet.text)
        topics.extend(hashtags)
        
        # Simple keyword extraction for common topics
        topic_keywords = {
            'technology': ['tech', 'ai', 'software', 'computer', 'digital'],
            'business': ['business', 'startup', 'company', 'market', 'economy'],
            'science': ['science', 'research', 'study', 'data', 'experiment'],
            'health': ['health', 'medical', 'doctor', 'medicine', 'wellness'],
            'education': ['education', 'learning', 'school', 'university', 'knowledge'],
            'environment': ['climate', 'environment', 'green', 'sustainability', 'energy']
        }
        
        text_lower = tweet.text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        return list(set(topics))  # Remove duplicates
    
    def get_generation_stats(self) -> Dict[str, Any]:
        """Get statistics about reply generation.
        
        Returns:
            Dictionary with generation statistics
        """
        # This would be enhanced with actual tracking in a full implementation
        return {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "max_length": self.config.max_reply_length,
            "safety_filter_enabled": True
        }
    
    def test_generation(self, test_tweet_text: str = "This is a test tweet about technology.") -> Optional[str]:
        """Test reply generation with a sample tweet.
        
        Args:
            test_tweet_text: Test tweet content
            
        Returns:
            Generated test reply, or None if failed
        """
        try:
            # Create a mock tweet for testing
            from ..models import PublicMetrics
            
            test_tweet = ProcessedTweet(
                id="test_123",
                text=test_tweet_text,
                author_id="test_author",
                author_username="test_user",
                author_name="Test User",
                created_at=datetime.now(),
                public_metrics=PublicMetrics(),
                selection_score=50.0
            )
            
            reply = self.generate_reply(test_tweet)
            
            self.logger.info("Test generation completed",
                           success=reply is not None,
                           reply_length=len(reply) if reply else 0)
            
            return reply
            
        except Exception as e:
            self.logger.error("Test generation failed", error=str(e))
            return None
