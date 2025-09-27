"""Tests for security utilities."""

import pytest
from src.x_reply_service.utils.security import ContentSafetyFilter, hash_text, is_similar_content


class TestContentSafetyFilter:
    """Test ContentSafetyFilter class."""
    
    @pytest.fixture
    def safety_filter(self):
        """Create a content safety filter."""
        return ContentSafetyFilter()
    
    def test_safe_content(self, safety_filter):
        """Test safe content detection."""
        safe_texts = [
            "This is a thoughtful discussion about renewable energy.",
            "I believe we should consider different perspectives on this topic.",
            "Here's an interesting fact about climate change research.",
            "What are your thoughts on sustainable development?"
        ]
        
        for text in safe_texts:
            result = safety_filter.is_safe_content(text)
            assert result.is_safe is True
            assert result.confidence > 0.5
    
    def test_unsafe_content(self, safety_filter):
        """Test unsafe content detection."""
        unsafe_texts = [
            "I hate this stupid idea and want to kill it",
            "This is racist garbage from a nazi",
            "Violence is the only solution to this problem",
            "You're a moron and should die"
        ]
        
        for text in unsafe_texts:
            result = safety_filter.is_safe_content(text)
            assert result.is_safe is False
            assert result.reason is not None
    
    def test_political_content(self, safety_filter):
        """Test political content detection."""
        political_texts = [
            "Trump and Biden are both wrong about this republican democrat issue",
            "The liberal conservative government politics are terrible",
            "Vote for the best political candidate in this election"
        ]
        
        for text in political_texts:
            result = safety_filter.is_safe_content(text)
            assert result.is_safe is False
            assert "political" in result.reason.lower()
    
    def test_spam_content(self, safety_filter):
        """Test spam content detection."""
        spam_texts = [
            "Buy now and get rich quick! Click here for amazing deals!",
            "Make money fast! Follow me and check out my profile!",
            "Limited time offer! DM me for exclusive access!"
        ]
        
        for text in spam_texts:
            result = safety_filter.is_safe_content(text)
            assert result.is_safe is False
            assert "spam" in result.reason.lower()
    
    def test_length_validation(self, safety_filter):
        """Test content length validation."""
        # Too long
        long_text = "x" * 281
        result = safety_filter.is_safe_content(long_text)
        assert result.is_safe is False
        assert "character limit" in result.reason
        
        # Too short
        short_text = "Hi"
        result = safety_filter.is_safe_content(short_text)
        assert result.is_safe is False
        assert "too short" in result.reason
        
        # Empty
        empty_text = ""
        result = safety_filter.is_safe_content(empty_text)
        assert result.is_safe is False
        assert "empty" in result.reason.lower()
    
    def test_controversial_topics(self, safety_filter):
        """Test controversial topics handling."""
        controversial_texts = [
            "Let's discuss abortion and gun control policies",
            "Religious beliefs about God and Jesus vary widely",
            "Vaccine and COVID policies are complex topics"
        ]
        
        for text in controversial_texts:
            result = safety_filter.is_safe_content(text)
            # Should be allowed but with lower confidence
            if result.is_safe:
                assert result.confidence < 0.8
            # Or flagged as controversial
            else:
                assert "controversial" in result.reason.lower()
    
    def test_clean_text(self, safety_filter):
        """Test text cleaning functionality."""
        # Remove URLs
        text_with_url = "Check this out https://example.com for more info"
        cleaned = safety_filter.clean_text(text_with_url)
        assert "https://example.com" not in cleaned
        
        # Remove leading mentions/hashtags
        text_with_mention = "@user #hashtag This is the main content"
        cleaned = safety_filter.clean_text(text_with_mention)
        assert not cleaned.startswith("@user")
        assert not cleaned.startswith("#hashtag")
        
        # Clean excessive whitespace
        text_with_spaces = "This  has   too    many     spaces"
        cleaned = safety_filter.clean_text(text_with_spaces)
        assert "  " not in cleaned
        
        # Clean excessive punctuation
        text_with_punct = "This is amazing!!!!!!"
        cleaned = safety_filter.clean_text(text_with_punct)
        assert "!!!!!" not in cleaned
    
    def test_safety_score(self, safety_filter):
        """Test safety score calculation."""
        safe_text = "This is a safe and educational comment."
        unsafe_text = "This contains hate speech and violence."
        
        safe_score = safety_filter.get_safety_score(safe_text)
        unsafe_score = safety_filter.get_safety_score(unsafe_text)
        
        assert safe_score > unsafe_score
        assert 0.0 <= safe_score <= 1.0
        assert 0.0 <= unsafe_score <= 1.0


class TestSecurityUtilities:
    """Test security utility functions."""
    
    def test_hash_text(self):
        """Test text hashing."""
        text1 = "This is a test text"
        text2 = "This is a different text"
        text3 = "This is a test text"  # Same as text1
        
        hash1 = hash_text(text1)
        hash2 = hash_text(text2)
        hash3 = hash_text(text3)
        
        # Same text should produce same hash
        assert hash1 == hash3
        
        # Different text should produce different hash
        assert hash1 != hash2
        
        # Hash should be 16 characters (truncated SHA256)
        assert len(hash1) == 16
        assert len(hash2) == 16
    
    def test_is_similar_content(self):
        """Test content similarity detection."""
        text1 = "This is a test about artificial intelligence"
        text2 = "This is a test about machine learning"  # Similar
        text3 = "Completely different topic about cooking"  # Different
        
        # Similar texts
        assert is_similar_content(text1, text2, threshold=0.5) is True
        
        # Different texts
        assert is_similar_content(text1, text3, threshold=0.5) is False
        
        # Identical texts
        assert is_similar_content(text1, text1, threshold=0.8) is True
        
        # Empty texts
        assert is_similar_content("", "", threshold=0.8) is False
        assert is_similar_content(text1, "", threshold=0.8) is False
    
    def test_similarity_threshold(self):
        """Test similarity threshold behavior."""
        text1 = "artificial intelligence machine learning"
        text2 = "machine learning artificial intelligence"  # Same words, different order
        
        # High threshold should still match identical word sets
        assert is_similar_content(text1, text2, threshold=0.9) is True
        
        # Very high threshold might not match due to word order
        assert is_similar_content(text1, text2, threshold=1.0) is True
