import os

import google.genai as genai
from dotenv import load_dotenv

load_dotenv()

cli = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
model = cli.Models(model_name="gemini-3.1-flash-lite-preview")

print("Gemini model initialized:", model.model_name)
