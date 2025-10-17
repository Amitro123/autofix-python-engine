"""
Gemini Service - Complete implementation with google-genai SDK
Handles the interaction with the Gemini API for the AutoFixer application.
Manages the chat session, system instructions, and tool calling lifecycle.
"""

from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import re
import os
import json
import time
from autofix.helpers.logging_utils import get_logger
from autofix.core.base import CodeFixer, FixResult
from .fallback_service import FallbackService
from .tools_service import ToolsService

logger = get_logger(__name__)

# Using a specific model name as requested
GEMINI_MODEL = "gemini-2.0-flash-exp"


class GeminiService(CodeFixer):
    """
    Gemini service - AI-powered code fixing using Gemini 2.0 Flash.
    Implements CodeFixer abstract base class.
    """
    
    SYSTEM_INSTRUCTION = (
        "You are AutoFixer. Fix broken Python code:\n"
        "1. Check syntax with validate_syntax\n"
        "2. Test with execute_code\n"
        "3. Search similar fixes with search_memory if needed\n"
        "4. Provide fixed code with explanation"
    )

    def __init__(self, tools_service: ToolsService, api_key: Optional[str] = None, fallback_service=None):
        """
        Initialize the Gemini Service with NEW SDK (google-genai).
        
        Args:
            tools_service: Service for tool declarations
            api_key: Optional API key (uses env var if not provided)
            fallback_service: Optional fallback service
        """
        # Get API key
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found or not provided.")
        
        # Initialize NEW SDK Client
        try:
            self.client = genai.Client(api_key=api_key)
            logger.info("✅ Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Gemini Client: {e}")
            raise
        
        # Store tools service
        self.tools_service = tools_service
        
        # Initialize fallback service
        self.fallback = fallback_service or FallbackService(
            memory_service=tools_service.memory_service
        )
        
        # Start a new chat session
        self.chat = self._start_new_chat()
        
        logger.info(f"✅ Gemini ready with model: {GEMINI_MODEL}")
    
    def _start_new_chat(self):
        """
        Start a new chat session with system instructions and tools.
        
        Returns:
            Chat object configured with model, system instructions, and tools
        """
        # Get tool declarations
        tools = self.tools_service.get_tool_declarations()
        
        # Create configuration with system instruction
        config = types.GenerateContentConfig(
            temperature=0.1,
            system_instruction=self.SYSTEM_INSTRUCTION,
            tools=[tools] if tools else None
        )
        
        # Create new chat session
        chat = self.client.chats.create(
            model=GEMINI_MODEL,
            config=config
        )
        
        logger.info(f"Started new chat session with {GEMINI_MODEL}")
        return chat
    
    def is_enabled(self) -> bool:
        """
        Check if Gemini service is available and enabled.
        
        Returns:
            True if client is initialized, False otherwise
        """
        try:
            return self.client is not None
        except AttributeError:
            return False
    
    def fix_code(self, code: str, auto_install: bool = False) -> FixResult:
        """
        Fix code using Gemini AI (implements CodeFixer interface).
        
        Args:
            code: Python code to fix
            auto_install: Whether to auto-install missing packages (not used yet)
            
        Returns:
            FixResult with standardized output
        """
        start_time = time.time()
        
        # Process code through Gemini
        result = self.process_user_code(code)
        
        # Convert to FixResult
        return FixResult(
            success=result.get('success', False),
            original_code=code,
            fixed_code=result.get('fixed_code', code),
            error_type='Unknown',
            method='gemini' if result.get('success') else 'error',
            cache_hit=False,
            changes=[],
            explanation=result.get('explanation', ''),
            execution_time=time.time() - start_time,
            iterations=result.get('iterations', 0)
        )
    
    def process_user_code(self, user_code: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Fix code using an iterative tool-calling loop.
        
        Args:
            user_code: Python code to fix
            max_iterations: Maximum number of tool-calling iterations
            
        Returns:
            Dict with success status, fixed code, and explanation
        """
        logger.info(f"Received user code for processing:\n{user_code[:100]}...")
        
        try:
            # 1. Send initial message
            response = self.chat.send_message(user_code)
            tools_used = []
            iteration = 0
            
            # 2. Tool-calling loop
            while iteration < max_iterations:
                # Check for function calls
                function_calls = []
                if response.candidates and len(response.candidates) > 0:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            function_calls.append(part.function_call)
                
                if not function_calls:
                    # No more tools to call, break the loop
                    break
                
                iteration += 1
                logger.info(f"Iteration {iteration}: Processing {len(function_calls)} tool call(s)")
                
                # 3. Execute tools
                results_summary = []
                for fc in function_calls:
                    logger.info(f"  → Tool: {fc.name}")
                    
                    try:
                        tool_result = self.tools_service.execute_tool(
                            fc.name,
                            dict(fc.args)
                        )
                        
                        tools_used.append({
                            'tool': fc.name,
                            'args': dict(fc.args),
                            'result': tool_result
                        })
                        
                        # Format result as text
                        result_str = json.dumps(tool_result, indent=2)
                        results_summary.append(
                            f"Tool '{fc.name}' result:\n{result_str}"
                        )
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        results_summary.append(
                            f"Tool '{fc.name}' failed: {str(e)}"
                        )
                
                # 4. Send tool results back
                logger.info(f"Sending {len(results_summary)} tool result(s) back to model")
                response = self.chat.send_message(
                    "Tool results:\n" + "\n\n".join(results_summary) +
                    "\n\nBased on these results, provide the fixed code."
                )
            
            # 5. Extract final result
            if response.text:
                fixed_code = self._extract_code_from_response(response.text)
                
                logger.info(f"✅ AutoFix completed in {iteration} iteration(s)")
                
                return {
                    'success': True,
                    'fixed_code': fixed_code,
                    'iterations': iteration,
                    'tools_used': tools_used,
                    'explanation': response.text
                }
            
            # 6. Failure case
            error_msg = f"No valid response after {iteration} iterations"
            logger.warning(error_msg)
            return {
                'success': False,
                'fixed_code': user_code,
                'iterations': iteration,
                'tools_used': tools_used,
                'explanation': error_msg
            }
        
        except Exception as e:
            logger.error(f"💥 Error in process_user_code: {e}", exc_info=True)
            return {
                'success': False,
                'fixed_code': user_code,
                'iterations': 0,
                'tools_used': [],
                'explanation': f"Error: {str(e)}"
            }
    
    def _extract_code_from_response(self, text: str) -> str:
        """
        Extract Python code from a markdown response block.
        
        Args:
            text: Response text that may contain markdown code blocks
            
        Returns:
            Extracted Python code or original text
        """
        # Regex to find code block enclosed in ``````
        match = re.search(r'``````', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # Fallback: return the entire text if no code block found
        return text.strip()
    
    def reset_chat(self) -> None:
        """Reset chat session to start fresh."""
        self.chat = self._start_new_chat()
        logger.info("Chat session reset")
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """
        Get chat history for debugging.
        
        Returns:
            List of chat messages with roles and content
        """
        try:
            history = self.chat.get_history()
            return [
                {
                    'role': msg.role if hasattr(msg, 'role') else 'unknown',
                    'parts': [str(p) for p in (msg.parts if hasattr(msg, 'parts') else [])]
                }
                for msg in history
            ]
        except Exception as e:
            logger.warning(f"Could not retrieve chat history: {e}")
            return []
