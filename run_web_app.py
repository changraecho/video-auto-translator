#!/usr/bin/env python3
"""
Video Auto Translator Web Application Launcher

This script starts the Flask web application for the Video Auto Translator.
Make sure all dependencies are installed before running.

Usage:
    python3 run_web_app.py

Environment Variables:
    ANTHROPIC_API_KEY - Required for translation functionality
    FLASK_ENV - Set to 'development' for debug mode (optional)
    FLASK_PORT - Port to run on (default: 5000)
"""

import os
import sys

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = [
        'flask',
        'cv2',
        'PIL',
        'anthropic',
        'srt'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PIL':
                from PIL import Image
            else:
                __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def check_environment():
    """Check environment setup"""
    issues = []
    
    # Check API key - config_local.py가 있으면 환경변수 체크 생략
    if not os.path.exists('config_local.py') and not os.getenv('ANTHROPIC_API_KEY'):
        issues.append("ANTHROPIC_API_KEY environment variable not set (config_local.py도 없음)")
    
    # Check required directories
    required_dirs = ['Fonts', 'SubtitleFonts', 'templates']
    for directory in required_dirs:
        if not os.path.exists(directory):
            issues.append(f"Required directory '{directory}' not found")
    
    return issues

def main():
    print("🎬 Video Auto Translator Web Application")
    print("=" * 50)
    
    # Check dependencies
    print("📋 Checking dependencies...")
    missing = check_dependencies()
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print("💡 Install them with: pip3 install " + ' '.join(missing))
        print("📄 Or use: pip3 install -r web_requirements.txt")
        return 1
    
    print("✅ All required packages found")
    
    # Check environment
    print("🔧 Checking environment...")
    issues = check_environment()
    if issues:
        print("❌ Environment issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return 1
    
    print("✅ Environment setup complete")
    
    # Start Flask app
    print("\n🚀 Starting Flask application...")
    print("📡 Server will be available at: http://localhost:3000")
    print("🛑 Press Ctrl+C to stop the server")
    print("-" * 50)
    
    try:
        from app import app
        
        # Configuration
        debug_mode = os.getenv('FLASK_ENV') == 'development'
        port = int(os.getenv('FLASK_PORT', 3000))
        
        app.run(
            debug=debug_mode,
            host='0.0.0.0',
            port=port,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return 0
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())