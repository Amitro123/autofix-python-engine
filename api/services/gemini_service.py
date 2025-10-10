"""Google Gemini AI Service for AutoFix"""
import os
from typing import Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


class GeminiService:
    """Service to integrate Gemini AI for code fixing"""
    
    def __init__(self):
        """Initialize Gemini with API key"""
        if not GENAI_AVAILABLE:
            self.enabled = False
            return
            
        api_key = os.getenv("GEMINI_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.5-pro')
            self.enabled = True
        else:
            self.enabled = False

    def fix_with_ai(self, code: str, error: str) -> Optional[str]:
        """Use Gemini to fix Python code"""
        if not self.enabled:
            return None
        
        try:
            prompt = "You are an expert Python debugger.\n\n"
            prompt += "Error:\n" + error + "\n\n"
            prompt += "Code:\n" + code + "\n\n"
            prompt += "Provide ONLY the fixed code."
            
            response = self.model.generate_content(prompt)
            return self._clean_response(response.text)
            
        except Exception as e:
            print("Gemini error:", e)
            return None
    
    def _clean_response(self, text: str) -> str:
        """Extract Python code from Gemini response - remove markdown"""
        if not text:
            return ""
        
        text = text.strip()
        text = text.replace('```python', '')
        text = text.replace('```', '')
        
        if text.startswith('python\n'):
            text = text[7:]
        elif text.startswith('python'):
            text = text[6:]
        
        return text.strip()

    def is_enabled(self) -> bool:
        """Check if Gemini is configured"""
        return self.enabled