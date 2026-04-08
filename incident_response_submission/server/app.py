import uvicorn
import os
import sys

# Add root folder to path so `app` can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app as fastapi_app

def main():
    uvicorn.run("app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
