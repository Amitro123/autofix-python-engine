"""
Gemini Service
Handles the interaction with the Gemini API for the AutoFixer application.
Manages the chat session, system instructions, and tool calling lifecycle.
"""

from typing import List, Dict, Any, Optional
import re
import os
from google import genai
from google.genai import types
from autofix_core.shared.helpers.logging_utils import get_logger

from .tools_service import ToolsService

logger = get_logger(__name__)

# Configuration
GEMINI_MODEL = "gemini-2.0-flash-exp"  # Using flash for fast iteration


class GeminiService:
    """
    Main service to handle AI communication and the AutoFix loop.
    The service is designed to maintain state (chat history) for multi-turn debugging.
    """
    
    # Define the core AI instruction set (The Persona and Rules)
    SYSTEM_INSTRUCTION = (
        "You are an elite, highly logical Python debugging and AutoFix agent named AutoFixer. "
        "Your goal is to correct user-provided Python code that contains errors. "
        "You must operate in a rigorous, step-by-step manner following these rules:\n\n"
        "1. **Initial Assessment**: Always start by attempting to use the `validate_syntax` tool on the user's code. "
        "2. **Syntax Check**: If syntax is invalid, provide a fix for the syntax error. DO NOT execute code with syntax errors.\n"
        "3. **Execution**: If syntax is valid, or if you propose a fix, you MUST use the `execute_code` tool to verify the code's behavior or test your fix. "
        "4. **RAG Retrieval**: If `execute_code` fails with a runtime error (e.g., TypeError, IndexError, NameError), you MUST use the `search_memory` tool with the exact error type to find similar, proven solutions from the knowledge base. "
        "5. **Final Output**: Once you have a working solution verified by `execute_code` (success=True and correct output), provide the final, complete, and corrected code snippet to the user, along with a concise explanation of *why* the original code failed and *how* your fix solved it. "
        "6. **Be Direct**: ONLY provide code and explanations. Do not engage in casual chat unless the user asks a non-debugging question."
    )

    def __init__(self, tools_service: ToolsService, api_key: Optional[str] = None):
        """
        Initializes the Gemini client and chat session.
        
        Args:
            tools_service: The service handling all tool executions.
            api_key: Optional Gemini API key (overrides environment variable).
        """
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found or not provided.")
        try:
            # Pass the API key explicitly if provided, otherwise uses GEMINI_API_KEY env var
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client. Ensure API key is set: {e}")
            raise

        self.tools_service = tools_service
        # Start a new chat session when the service is initialized
        self.chat = self._start_new_chat()

    def _start_new_chat(self):
        """Starts a new chat session with defined system instructions and tools."""
        tools = self.tools_service.get_tool_declarations()
        
        # Configure model generation settings
        # system_instruction and tools go in the config
        config = types.GenerateContentConfig(
            temperature=0.1,
            system_instruction=self.SYSTEM_INSTRUCTION,
            tools=[tools]  # Tools are passed as a list in config
        )

        # Start a new chat session
        chat = self.client.chats.create(
            model=GEMINI_MODEL,
            config=config
        )

        logger.info(f"Started new chat session with {GEMINI_MODEL}")
        return chat


    def fix_code(self, code: str, auto_install: bool = False) -> Dict[str, Any]:
        """Hybrid: Try handler first, then AI fallback"""
        
        import tempfile
        import os
        
        # STEP 1: Try Handler (FAST & FREE!)
        try:
            from autofix_core.infrastructure.cli.python_fixer import PythonFixer
            
            # Create temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_path = f.name
            
            try:
                fixer = PythonFixer()
                success = fixer.run_script_with_fixes(temp_path)  # ← FIXED!
                
                # Read fixed code from file
                if os.path.exists(temp_path):
                    with open(temp_path, 'r', encoding='utf-8') as f:
                        fixed_code = f.read()
                else:
                    fixed_code = code
                
                # Check if it worked
                if success and fixed_code != code:
                    logger.info("✅ Handler fixed it!")
                    return {
                        'success': True,
                        'original_code': code,
                        'fixed_code': fixed_code,
                        'error_type': 'SyntaxError',
                        'method': 'handler',
                        'cache_hit': False,
                        'changes': ['Fixed by deterministic handler'],
                        'explanation': 'Fixed by rule-based handler'
                    }
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                    
        except Exception as e:
            logger.warning(f"Handler failed: {e}")
        
        # STEP 2: AI Fallback
        logger.info("🤖 Using AI fallback...")
        result = self.process_user_code(code)
        
        return {
            'success': result.get('success', False),
            'original_code': code,
            'fixed_code': result.get('fixed_code', code),
            'error_type': 'Unknown',
            'method': 'gemini',
            'cache_hit': False,
            'changes': [],
            'explanation': result.get('explanation', '')
        }

    
    def process_user_code(self, user_code: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Processes a user's code prompt and runs the AutoFix loop.

        Args:
            user_code: The code snippet provided by the user.
            max_iterations: Maximum number of tool-calling iterations allowed.

        Returns:
            Dict containing the final result (success, fixed_code, explanation, tools_used).
        """
        logger.info(f"Received user code for processing:\n{user_code[:200]}...")
        
        # 1. Send initial user message (code)
        response = self.chat.send_message(user_code)

        tools_used: List[Dict[str, Any]] = []
        iteration = 0

        # 2. Start the Tool Calling Loop
        while response.function_calls and iteration < max_iterations:
            iteration += 1
            function_calls = response.function_calls
            tool_responses = []

            logger.info(f"Iteration {iteration}: Processing {len(function_calls)} tool call(s)")

            for fc in function_calls:
                func_name = fc.name
                func_args = dict(fc.args)

                logger.info(f"  → Tool: {func_name}")
                logger.debug(f"    Args: {func_args}")
                
                # Execute the tool using the ToolsService
                tool_result = self.tools_service.execute_tool(func_name, func_args)
                
                # Track tool usage
                tools_used.append({
                    'tool': func_name,
                    'args': func_args,
                    'result': tool_result
                })

                # Create the FunctionResponse object
                tool_responses.append(
                    types.Part.from_function_response(
                        name=func_name,
                        response=tool_result
                    )
                )
                
                logger.debug(f"    Result: {str(tool_result)[:100]}...")

            # 3. Send tool results back to the model for the next reasoning step
            logger.info(f"Sending {len(tool_responses)} tool result(s) back to model")
            response = self.chat.send_message(tool_responses)

        # 4. Final Processing (Text response or error)
        if response.text:
            fixed_code = self._extract_code_from_response(response.text)

            logger.info(f"Fix completed in {iteration} iteration(s)")
            
            return {
                'success': True,
                'fixed_code': fixed_code,
                'iterations': iteration,
                'tools_used': tools_used,
                'explanation': response.text
            }
        
        # 5. Handle failure case (max iterations or no final text)
        error_msg = "AutoFix process failed to converge or returned an empty response."
        if iteration == max_iterations:
            error_msg = f"Max iterations ({max_iterations}) reached without successful fix."

        logger.warning(error_msg)

        return {
            'success': False,
            'fixed_code': user_code,  # Return original code on failure
            'iterations': iteration,
            'tools_used': tools_used,
            'explanation': error_msg
        }

    def _extract_code_from_response(self, response_text: str) -> str:
        """
        Extract Python code from a markdown response block.
        
        Handles blocks with or without language tag:
        ```
        code here
        ```

        or

        ```
        code here
        ```
        """
        # Regex to find code block enclosed in `````` or ```
        code_block_pattern = r'```(?:python\n)?(.*?)```'
        matches = re.findall(code_block_pattern, response_text, re.DOTALL)

        if matches:
            # Return the last code block (usually the final fix)
            code = matches[-1].strip()
            logger.info(f"Extracted code block ({len(code)} chars)")
            return code
        
        # No code block found, return full text
        logger.warning("No code block found in response, returning full text")
        return response_text.strip()
    
    def reset_chat(self) -> None:
        """Reset chat session (start fresh conversation)"""
        logger.info("Resetting chat session")
        self.history = []
        self.chat = self._start_new_chat()
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get chat history for debugging/logging"""
        return [
            {
                'role': msg.role,
                'parts': [str(part) for part in msg.parts]
            }
            for msg in self.chat.history
        ]

# Backward compatibility alias

# Backward compatibility alias
AutoFixService = GeminiService
