#!/usr/bin/env python3
"""Setup script for securely storing API credentials."""

import sys
import os
import getpass
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.x_reply_service.utils.security import SecureCredentialManager


def main():
    """Setup API credentials securely."""
    print("🔐 X.com Auto-Reply Service - Credential Setup")
    print("=" * 50)
    
    credential_manager = SecureCredentialManager()
    
    print("\nThis script will help you securely store your API credentials.")
    print("Credentials will be encrypted and stored using your system's keyring.")
    print("\nYou'll need:")
    print("• Twitter/X.com API credentials (Bearer Token, API Key, API Secret, Access Token, Access Token Secret)")
    print("• Perplexity API key")
    
    if not input("\nContinue? (y/N): ").lower().startswith('y'):
        print("Setup cancelled.")
        return
    
    # Twitter/X.com credentials
    print("\n📱 Twitter/X.com API Credentials")
    print("-" * 30)
    
    twitter_bearer_token = getpass.getpass("Twitter Bearer Token: ").strip()
    if not twitter_bearer_token:
        print("❌ Bearer Token is required")
        return
    
    twitter_api_key = getpass.getpass("Twitter API Key: ").strip()
    if not twitter_api_key:
        print("❌ API Key is required")
        return
    
    twitter_api_secret = getpass.getpass("Twitter API Secret: ").strip()
    if not twitter_api_secret:
        print("❌ API Secret is required")
        return
    
    twitter_access_token = getpass.getpass("Twitter Access Token: ").strip()
    if not twitter_access_token:
        print("❌ Access Token is required")
        return
    
    twitter_access_token_secret = getpass.getpass("Twitter Access Token Secret: ").strip()
    if not twitter_access_token_secret:
        print("❌ Access Token Secret is required")
        return
    
    # Perplexity credentials
    print("\n🤖 Perplexity API Credentials")
    print("-" * 30)
    
    perplexity_api_key = getpass.getpass("Perplexity API Key: ").strip()
    if not perplexity_api_key:
        print("❌ Perplexity API Key is required")
        return
    
    # Store credentials
    print("\n💾 Storing credentials securely...")
    
    try:
        credential_manager.store_credential("TWITTER_BEARER_TOKEN", twitter_bearer_token)
        credential_manager.store_credential("TWITTER_API_KEY", twitter_api_key)
        credential_manager.store_credential("TWITTER_API_SECRET", twitter_api_secret)
        credential_manager.store_credential("TWITTER_ACCESS_TOKEN", twitter_access_token)
        credential_manager.store_credential("TWITTER_ACCESS_TOKEN_SECRET", twitter_access_token_secret)
        credential_manager.store_credential("PERPLEXITY_API_KEY", perplexity_api_key)
        
        print("✅ Credentials stored successfully!")
        
    except Exception as e:
        print(f"❌ Failed to store credentials: {e}")
        return
    
    # Create .env file for environment variables
    env_file = Path(".env")
    print(f"\n📝 Creating {env_file} file...")
    
    env_content = f"""# X.com Auto-Reply Service Environment Variables
# These reference the securely stored credentials

TWITTER_BEARER_TOKEN={twitter_bearer_token}
TWITTER_API_KEY={twitter_api_key}
TWITTER_API_SECRET={twitter_api_secret}
TWITTER_ACCESS_TOKEN={twitter_access_token}
TWITTER_ACCESS_TOKEN_SECRET={twitter_access_token_secret}
PERPLEXITY_API_KEY={perplexity_api_key}
"""
    
    try:
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        # Set restrictive permissions
        os.chmod(env_file, 0o600)
        
        print(f"✅ {env_file} created with secure permissions")
        
    except Exception as e:
        print(f"❌ Failed to create {env_file}: {e}")
    
    # Test credentials
    print("\n🧪 Testing credentials...")
    
    try:
        # Set environment variables for testing
        os.environ['TWITTER_BEARER_TOKEN'] = twitter_bearer_token
        os.environ['TWITTER_API_KEY'] = twitter_api_key
        os.environ['TWITTER_API_SECRET'] = twitter_api_secret
        os.environ['TWITTER_ACCESS_TOKEN'] = twitter_access_token
        os.environ['TWITTER_ACCESS_TOKEN_SECRET'] = twitter_access_token_secret
        os.environ['PERPLEXITY_API_KEY'] = perplexity_api_key
        
        from src.x_reply_service.core.service import XReplyService
        
        service = XReplyService(dry_run=True)
        health = service.health_check()
        
        if health['overall'] == 'healthy':
            print("✅ Credential test successful!")
            print("\n🎉 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Review and customize config/config.yaml")
            print("2. Test the service: python main.py --dry-run --test-mode")
            print("3. Set up cron job for hourly execution")
        else:
            print("⚠️  Credential test failed. Please check your API keys.")
            print("Health check results:")
            for component, info in health.get('components', {}).items():
                status_icon = "✅" if info['status'] == 'healthy' else "❌"
                print(f"  {status_icon} {component.title()}: {info['status']}")
        
    except Exception as e:
        print(f"⚠️  Could not test credentials: {e}")
        print("You can test them later with: python main.py --health-check")
    
    print("\n" + "=" * 50)
    print("Setup complete! Your credentials are stored securely.")


if __name__ == "__main__":
    main()
