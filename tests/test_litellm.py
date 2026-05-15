import litellm
import os
from dotenv import load_dotenv

load_dotenv()

try:
    response = litellm.completion(
        model="gemini/gemini-1.5-flash",
        messages=[{"role": "user", "content": "hello"}]
    )
    print(response)
except Exception as e:
    print(f"Error: {e}")
