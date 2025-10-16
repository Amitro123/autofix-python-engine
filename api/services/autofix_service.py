"""
Gemini Service
Handles the interaction with the Gemini API for the AutoFixer application.
Manages the chat session, system instructions, and tool calling lifecycle.
"""

from typing import List, Dict, Any, Optional
import re
from google import genai
from google.generativeai import types
from autofix.helpers.logging_utils import get_logger

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
        try:
            # Pass the API key explicitly if provided, otherwise uses GEMINI_API_KEY env var
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client. Ensure API key is set: {e}")
            raise

        self.tools_service = tools_service
        self.history: List[types.Content] = []
        
        # Start a new chat session when the service is initialized
        self.chat = self._start_new_chat()

    def _start_new_chat(self):
        """Starts a new chat session with defined system instructions and tools."""
        tools = self.tools_service.get_tool_declarations()
        
        # Configure model generation settings
        config = types.GenerationConfig(
        temperature=0.1
        )

        # Start a new chat session
        chat = self.client.chats.create(
            model=GEMINI_MODEL,
            history=self.history,
            config=config,
            system_instruction=self.SYSTEM_INSTRUCTION, 
            tools=[tools] 
        )
        
        logger.info(f"Started new chat session with {GEMINI_MODEL}")
        return chat

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
        code_block_pattern = r'``````'
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
AutoFixService = GeminiService
