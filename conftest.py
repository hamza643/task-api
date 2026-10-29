import os

# Tests must not need a real .env file:  
os.environ.setdefault("SECRET_KEY", "test-secret-not-for-real-use")