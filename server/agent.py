import litellm
import json
import logging
from .config import config
from .history import history
from .tools import tool_registry

logger = logging.getLogger(__name__)

class CloudAgent:
    def __init__(self):
        self.model = config.GOKU_MODEL

    def _get_system_prompt(self, source: str):
        """Generate a source-aware system prompt."""
        base = (
            "You are Goku Lite v1.0, an elite cloud-native AI agent. "
            "You are lightweight yet powerful, designed to run on minimal hardware while wielding infinite cloud power. "
            "You have full access to a terminal, file system, and long-term cloud memory.\n\n"
            "CRITICAL: You are an expert at documentation. When writing docs, use clear headings, Mermaid diagrams, "
            "and professional technical language."
        )
        
        if source == "cli":
            return base + "\n\n[INTERFACE] You are currently in the CLI Terminal. Use clean formatting and prioritize technical precision."
        elif source == "telegram":
            return base + "\n\n[INTERFACE] You are currently on Telegram. Use bold headers, high-fidelity markdown, and appropriate emojis."
        elif source == "whatsapp":
            return base + "\n\n[INTERFACE] You are currently on WhatsApp. Use concise bullet points and mobile-friendly formatting."
        
        return base

    async def chat(self, user_input: str, session_id: str = "default", source: str = "cli"):
        # 1. Get history
        messages = history.get_messages(session_id)
        
        # 2. Add System Prompt (Awareness)
        if not messages:
            messages.append({"role": "system", "content": self._get_system_prompt(source)})
        
        # 3. Add current message
        messages.append({"role": "user", "content": user_input})
        history.add_message(session_id, "user", user_input)

        # 4. Call Cloud LLM with Tool Support
        try:
            # Determine API Key and Base based on provider
            api_key = None
            api_base = None
            
            if self.model.startswith("gpt") or "openai" in self.model:
                api_key = config.OPENAI_API_KEY
            elif self.model.startswith("claude") or "anthropic" in self.model:
                api_key = config.ANTHROPIC_API_KEY
            elif "gemini" in self.model:
                api_key = config.GEMINI_API_KEY
            elif "ollama" in self.model:
                api_key = config.OLLAMA_API_KEY or "ollama" # LiteLLM needs a non-empty key for some providers
                api_base = config.OLLAMA_API_BASE
            
            # Fallback to general keys if still None
            if not api_key:
                api_key = config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY or config.GEMINI_API_KEY

            response = await litellm.acompletion(
                model=self.model,
                messages=messages,
                tools=tool_registry.tools,
                tool_choice="auto",
                api_key=api_key,
                api_base=api_base
            )
            
            message = response.choices[0].message
            
            # 5. Handle Tool Calls
            if message.get("tool_calls"):
                messages.append(message)
                
                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    tool_output = await tool_registry.execute(function_name, function_args)
                    
                    messages.append({
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output,
                    })
                
                # Second pass with tool results
                second_response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    api_key=api_key,
                    api_base=api_base
                )
                final_content = second_response.choices[0].message.content
            else:
                final_content = message.content
            
            # 6. Save final response
            if final_content:
                history.add_message(session_id, "assistant", final_content)
            
            return final_content
            
        except Exception as e:
            logger.error(f"Cloud LLM Error: {e}")
            return f"Sorry, I encountered an error with the cloud brain: {e}"

agent = CloudAgent()
