"""Security utilities for credential management and content safety."""

import os
import re
import hashlib
from pathlib import Path
from typing import Tuple, List, Optional
from cryptography.fernet import Fernet
import keyring

from ..models import SafetyCheckResult


class SecureCredentialManager:
    """Manages secure storage and retrieval of API credentials."""
    
    SERVICE_NAME = "x_reply_service"
    KEY_FILE = ".x_reply_service_key"
    
    def __init__(self):
        """Initialize credential manager."""
        self.key = self._get_or_create_key()
        self.cipher = Fernet(self.key)
    
    def _get_or_create_key(self) -> bytes:
        """Get encryption key from secure location or create new one."""
        key_path = Path.home() / self.KEY_FILE
        
        if key_path.exists():
            with open(key_path, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Save key with restricted permissions
            with open(key_path, 'wb') as f:
                f.write(key)
            os.chmod(key_path, 0o600)  # Read-only for owner
            
            return key
    
    def store_credential(self, key: str, value: str) -> None:
        """Store encrypted credential using keyring."""
        try:
            # Try to use system keyring first
            keyring.set_password(self.SERVICE_NAME, key, value)
        except Exception:
            # Fallback to file-based encryption
            encrypted_value = self.cipher.encrypt(value.encode()).decode()
            credential_file = Path.home() / f".{self.SERVICE_NAME}_{key}"
            
            with open(credential_file, 'w') as f:
                f.write(encrypted_value)
            os.chmod(credential_file, 0o600)
    
    def get_credential(self, key: str) -> Optional[str]:
        """Retrieve and decrypt credential."""
        try:
            # Try system keyring first
            value = keyring.get_password(self.SERVICE_NAME, key)
            if value:
                return value
        except Exception:
            pass
        
        # Fallback to file-based decryption
        credential_file = Path.home() / f".{self.SERVICE_NAME}_{key}"
        
        if credential_file.exists():
            try:
                with open(credential_file, 'r') as f:
                    encrypted_value = f.read().strip()
                return self.cipher.decrypt(encrypted_value.encode()).decode()
            except Exception:
                return None
        
        return None
    
    def delete_credential(self, key: str) -> None:
        """Delete stored credential."""
        try:
            keyring.delete_password(self.SERVICE_NAME, key)
        except Exception:
            pass
        
        # Also remove file-based credential
        credential_file = Path.home() / f".{self.SERVICE_NAME}_{key}"
        if credential_file.exists():
            credential_file.unlink()


class ContentSafetyFilter:
    """Filters content for safety and appropriateness."""
    
    def __init__(self):
        """Initialize content safety filter."""
        self.unsafe_patterns = [
            r'\b(hate|hatred|violence|violent|threat|threaten)\b',
            r'\b(kill|murder|die|death|suicide)\b',
            r'\b(racist|racism|sexist|sexism|homophobic|homophobia)\b',
            r'\b(nazi|hitler|genocide)\b',
            r'\b(terrorist|terrorism|bomb|bombing)\b',
            r'\b(rape|sexual assault)\b',
            r'\b(fuck|shit|damn|hell|bitch|asshole)\b',  # Profanity
        ]
        
        self.political_keywords = [
            'trump', 'biden', 'democrat', 'republican', 'liberal', 'conservative',
            'maga', 'antifa', 'blm', 'election', 'vote', 'voting', 'politics',
            'political', 'government', 'congress', 'senate', 'president'
        ]
        
        self.controversial_topics = [
            'abortion', 'gun control', 'immigration', 'climate change',
            'vaccine', 'covid', 'religion', 'religious', 'god', 'jesus',
            'muslim', 'christian', 'jewish', 'atheist'
        ]
        
        self.spam_indicators = [
            r'(buy now|click here|limited time|act fast)',
            r'(make money|get rich|earn \$\d+)',
            r'(follow me|check out my)',
            r'(dm me|send me a message)',
            r'(link in bio|see my profile)'
        ]
    
    def is_safe_content(self, text: str) -> SafetyCheckResult:
        """Check if content is safe to post."""
        text_lower = text.lower().strip()
        
        if not text_lower:
            return SafetyCheckResult(
                is_safe=False,
                reason="Empty content",
                confidence=1.0
            )
        
        # Check for unsafe patterns
        for pattern in self.unsafe_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return SafetyCheckResult(
                    is_safe=False,
                    reason=f"Contains unsafe content: {pattern}",
                    confidence=0.9
                )
        
        # Check for excessive political content
        political_count = sum(1 for keyword in self.political_keywords 
                            if keyword in text_lower)
        if political_count > 2:
            return SafetyCheckResult(
                is_safe=False,
                reason="Too much political content",
                confidence=0.8
            )
        
        # Check for controversial topics (warning, not blocking)
        controversial_count = sum(1 for topic in self.controversial_topics 
                                if topic in text_lower)
        if controversial_count > 1:
            return SafetyCheckResult(
                is_safe=True,  # Allow but with low confidence
                reason="Contains controversial topics",
                confidence=0.6
            )
        
        # Check for spam indicators
        for pattern in self.spam_indicators:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return SafetyCheckResult(
                    is_safe=False,
                    reason="Appears to be spam or promotional",
                    confidence=0.8
                )
        
        # Check length
        if len(text) > 280:
            return SafetyCheckResult(
                is_safe=False,
                reason="Exceeds character limit",
                confidence=1.0
            )
        
        if len(text) < 10:
            return SafetyCheckResult(
                is_safe=False,
                reason="Content too short to be meaningful",
                confidence=0.9
            )
        
        # All checks passed
        return SafetyCheckResult(
            is_safe=True,
            reason="Content appears safe",
            confidence=0.95
        )
    
    def clean_text(self, text: str) -> str:
        """Clean text by removing potentially problematic elements."""
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove mentions and hashtags at the beginning (but keep in context)
        text = re.sub(r'^[@#]\w+\s*', '', text)
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove trailing punctuation that might be problematic
        text = re.sub(r'[!]{2,}$', '!', text)
        text = re.sub(r'[?]{2,}$', '?', text)
        
        return text
    
    def get_safety_score(self, text: str) -> float:
        """Get safety score from 0.0 (unsafe) to 1.0 (safe)."""
        result = self.is_safe_content(text)
        return result.confidence if result.is_safe else 0.0


def hash_text(text: str) -> str:
    """Create hash of text for deduplication."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def is_similar_content(text1: str, text2: str, threshold: float = 0.8) -> bool:
    """Check if two texts are similar (simple word overlap check)."""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        return False
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    similarity = len(intersection) / len(union)
    return similarity >= threshold
