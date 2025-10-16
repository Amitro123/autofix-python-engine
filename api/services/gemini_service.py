"""
Gemini Service - WORKING with google-generativeai
Handles the interaction with the Gemini API for the AutoFixer application.
Manages the chat session, system instructions, and tool calling lifecycle.
"""

import google.generativeai as genai
from typing import List, Dict, Any, Optional
import re
import os
import json
from autofix.helpers.logging_utils import get_logger
from .fallback_service import FallbackService


from .tools_service import ToolsService

logger = get_logger(__name__)

# Using a specific model name as requested
GEMINI_MODEL = "gemini-2.0-flash-exp"


class GeminiService:
    """Gemini service - Working version, using a manual tool calling loop."""
    
    SYSTEM_INSTRUCTION = (
        "You are AutoFixer. Fix broken Python code:\n"
        "1. Check syntax with validate_syntax\n"
        "2. Test with execute_code\n"
        "3. Search similar fixes with search_memory if needed\n"
        "4. Provide fixed code with explanation"
    )

    def __init__(self, tools_service: ToolsService, api_key: Optional[str] = None, fallback_service=None):
        """Initialize"""
        # Configure the client globally or using the provided key
        if api_key:
            genai.configure(api_key=api_key)
        else:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found or not provided.")
            genai.configure(api_key=api_key)
        
        self.tools_service = tools_service
        # Get tool declarations from the ToolsService
        tools = [tools_service.get_tool_declarations()]
        
        # Initialize GenerativeModel
        self.model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            tools=tools,
            system_instruction=self.SYSTEM_INSTRUCTION
        )
        
        # Start a new chat session
        self.chat = self.model.start_chat()
        logger.info(f"✅ Gemini ready with model: {GEMINI_MODEL}")

        self.fallback = fallback_service or FallbackService(
            memory_service=tools_service.memory_service
        )

    def process_user_code(self, user_code: str, max_iterations: int = 5) -> Dict[str, Any]:
        """Fix code using an iterative tool-calling loop."""
        logger.info("Processing user code with Gemini...")
        
        # 1. Send initial message
        response = self.chat.send_message(user_code)
        tools_used = []
        iteration = 0
        
        while iteration < max_iterations:
            # 2. Check for function calls
            function_calls = []
            if response.candidates and len(response.candidates) > 0:
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_calls.append(part.function_call)
            
            if not function_calls:
                # No more tools to call, break the loop and process final text
                break
            
            iteration += 1
            logger.info(f"Iteration {iteration}: {len(function_calls)} tool call(s) requested.")
            
            # 3. Execute tools
            results_summary = []
            for fc in function_calls:
                logger.info(f"  → Executing tool: {fc.name}")
                
                tool_result = self.tools_service.execute_tool(
                    fc.name,
                    dict(fc.args)
                )
                
                tools_used.append({
                    'tool': fc.name,
                    'args': dict(fc.args),
                    'result': tool_result
                })
                
                # Format result as text for model to interpret
                result_str = json.dumps(tool_result, indent=2)
                results_summary.append(
                    f"Tool '{fc.name}' result:\n{result_str}"
                )
            
            # 4. Send tool results back as raw text (manual approach)
            response = self.chat.send_message(
                "Tool results:\n" + "\n\n".join(results_summary) +
                "\n\nBased on these results, provide the fixed code."
            )
        
        # 5. Extract result
        if response.text:
            fixed_code = self._extract_code_from_response(response.text)
            
            logger.info(f"✅ AutoFix process completed in {iteration} iteration(s)")
            
            return {
                'success': True,
                'fixed_code': fixed_code,
                'iterations': iteration,
                'tools_used': tools_used,
                'explanation': response.text
            }
        
        # 6. Failure case
        error_msg = f"Failed to get a fixed code response after {iteration} iterations."
        logger.warning(error_msg)
        return {
            'success': False,
            'fixed_code': user_code,
            'iterations': iteration,
            'tools_used': tools_used,
            'explanation': error_msg
        }

    def _extract_code_from_response(self, text: str) -> str:
        """
        Extract Python code from a markdown response block.
        (Corrected regex pattern for robustness)
        """
        # Regex to find code block enclosed in `````` or ```
        match = re.search(r'```(?:python)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: return the entire text if no code block found
        return text.strip()

    def reset_chat(self) -> None:
        """Reset chat session"""
        self.chat = self.model.start_chat()
        logger.info("Chat session reset")

    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get chat history for debugging"""
        return [
            {'role': msg.role, 'parts': [str(p) for p in msg.parts]}
            for msg in self.chat.history
        ]
