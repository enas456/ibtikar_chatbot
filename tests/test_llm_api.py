from dotenv import load_dotenv
load_dotenv()

from services.llm_client import call_llm
from services.chat_logic import _clean_response  # ✅ Import cleaner

print("Sending test prompt to LLM API...")
try:
    data = call_llm("Say hi.", timeout=10)
    print("✅ Raw API response:", data["raw"])
    print("✅ Clean text:", _clean_response(data["text"]))  # ✅ Clean it here
except Exception as e:
    print(f"❌ API call failed: {type(e).__name__} {e}")
