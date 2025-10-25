"""
Test database connection for ERPNext Mock API
Run this to verify your Aiven MySQL database connection works
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
# Configuration

BASE_URL = os.getenv("BASE_URL", '') 
API_KEY = "test_api_key"
API_SECRET = "test_api_secret"
# Your Aiven database URL
DATABASE_URL = BASE_URL 

def test_connection():
    """Test the database connection"""
    print("=" * 60)
    print("Testing Aiven MySQL Connection")
    print("=" * 60)
    
    # Fix URL format for SQLAlchemy
    if DATABASE_URL.startswith('mysql://'):
        fixed_url = DATABASE_URL.replace('mysql://', 'mysql+pymysql://', 1)
    else:
        fixed_url = DATABASE_URL
    
    # Fix SSL mode parameter
    if 'ssl-mode=' in fixed_url:
        fixed_url = fixed_url.replace('ssl-mode=', 'ssl_mode=')
    
    print(f"\n📡 Connecting to: {fixed_url.split('@')[1].split('?')[0]}")
    print(f"🔐 SSL Mode: REQUIRED")
    print(f"👤 User: avnadmin")
    
    try:
        # Try to create engine
        print("\n⏳ Creating database engine...")
        engine = create_engine(
            fixed_url,
            poolclass=NullPool,
            echo=False
        )
        
        # Try to connect
        print("⏳ Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
        print("✅ Connection successful!")
        
        # Try to get database info
        print("\n📊 Database Info:")
        with engine.connect() as conn:
            # Get version
            result = conn.execute(text("SELECT VERSION()"))
            version = result.fetchone()[0]
            print(f"   MySQL Version: {version}")
            
            # Get current database
            result = conn.execute(text("SELECT DATABASE()"))
            db_name = result.fetchone()[0]
            print(f"   Current Database: {db_name}")
            
            # List tables
            result = conn.execute(text("SHOW TABLES"))
            tables = [row[0] for row in result]
            print(f"   Tables: {len(tables)} found")
            if tables:
                for table in tables:
                    print(f"      - {table}")
            else:
                print("      (No tables yet - they'll be created on first run)")
        
        print("\n✅ All tests passed!")
        print("\n📝 Next steps:")
        print("   1. Add DATABASE_URL to Render environment variables")
        print("   2. Deploy your service")
        print("   3. Check /health endpoint")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Connection failed!")
        print(f"\n🔍 Error details:")
        print(f"   {type(e).__name__}: {str(e)}")
        
        print(f"\n💡 Troubleshooting tips:")
        print("   1. Verify your password is correct")
        print("   2. Check if Aiven service is running")
        print("   3. Ensure IP whitelisting allows your connection")
        print("   4. Install required packages: pip install pymysql cryptography sqlalchemy")
        
        if "Access denied" in str(e):
            print("\n   ⚠️  Authentication error - check username/password")
        elif "Can't connect" in str(e) or "Connection refused" in str(e):
            print("\n   ⚠️  Network error - check host and port")
        elif "SSL" in str(e):
            print("\n   ⚠️  SSL error - make sure cryptography package is installed")
        
        return False


if __name__ == '__main__':
    import sys
    
    print("\n🔧 ERPNext Mock API - Database Connection Test\n")
    
    # Check if required packages are installed
    try:
        import pymysql
        import cryptography
        import sqlalchemy
        print("✅ Required packages installed")
    except ImportError as e:
        print(f"❌ Missing required package: {e.name}")
        print("\nInstall with: pip install pymysql cryptography sqlalchemy")
        sys.exit(1)
    
    success = test_connection()
    sys.exit(0 if success else 1)
