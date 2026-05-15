from strands.models.litellm import LiteLLMModel
try:
    m = LiteLLMModel(model_id="gemini/gemini-1.5-pro", params={"temperature": 0.5})
    print("Success")
except Exception as e:
    print(f"Error: {e}")
