#!/usr/bin/env python3
"""
Test script to verify the setup works correctly
"""

import asyncio
import sys
import os

async def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")

    try:
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.chrome.options import Options
        print("✅ selenium imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import selenium: {e}")
        return False

    try:
        from dotenv import load_dotenv
        print("✅ python-dotenv imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import python-dotenv: {e}")
        return False

    try:
        from bs4 import BeautifulSoup
        print("✅ beautifulsoup4 imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import beautifulsoup4: {e}")
        return False

    return True

def test_browser_initialization():
    """Test basic browser initialization"""
    print("\nTesting browser initialization...")

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Use headless for testing
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Chrome WebDriver started successfully")

        # Test basic navigation
        driver.get("https://google.com")
        print("✅ Basic navigation test successful")

        driver.quit()
        print("✅ Browser closed successfully")

        return True

    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        print("   Make sure ChromeDriver is installed and in your PATH")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")

    try:
        from dotenv import load_dotenv
        load_dotenv()

        # Test environment variables
        delay = int(os.getenv('DELAY_BETWEEN_TWEETS', 30))
        max_tweets = int(os.getenv('MAX_TWEETS_PER_SESSION', 5))
        wait_time = int(os.getenv('PERPLEXITY_WAIT_TIME', 15))
        headless = os.getenv('HEADLESS', 'false').lower() == 'true'

        print(f"✅ Configuration loaded:")
        print(f"   - Delay between tweets: {delay}s")
        print(f"   - Max tweets per session: {max_tweets}")
        print(f"   - Perplexity wait time: {wait_time}s")
        print(f"   - Headless mode: {headless}")

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("="*50)
    print("🧪 TESTING TWITTER AGENT SETUP")
    print("="*50)

    tests = [
        ("Import Test", test_imports()),
        ("Configuration Test", test_configuration()),
        ("Browser Test", test_browser_initialization()),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")

        if asyncio.iscoroutine(test_func):
            result = await test_func
        else:
            result = test_func

        if result:
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")

    print("\n" + "="*50)
    print(f"📊 TEST RESULTS: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\nYou can now run the main application with:")
        print("   python run_agent.py")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())