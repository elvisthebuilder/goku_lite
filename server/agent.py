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
            "CRITICAL: Always respond in English unless the user explicitly requests another language. "
            "Use clean Markdown (bold, lists) but avoid complex formatting that breaks simple terminal/mobile parsers. "
            "You have full access to a terminal, file system, and long-term cloud memory."
        )
        
        if source == "cli":
            return base + "\n\n[IDENTITY] You are currently interacting via a Command Line Interface (CLI). Use technical precision and clean terminal-friendly formatting."
        elif source == "telegram":
            return base + (
                "\n\n[IDENTITY] You are currently interacting via TELEGRAM. You are a Telegram Bot.\n"
                "[SKILL: TELEGRAM FORMATTING]\n"
                "- Use *bold* for headers and key terms.\n"
                "- Use `inline code` for commands or technical values.\n"
                "- Use ```code blocks``` for multi-line technical info.\n"
                "- Use emojis to keep the conversation engaging.\n"
                "- CRITICAL: Avoid using raw underscores (_) as they break the parser. Use bold instead."
            )
        elif source == "whatsapp":
            return base + "\n\n[IDENTITY] You are currently interacting via WHATSAPP. You are a WhatsApp Bot. Use mobile-friendly formatting."
        
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
                api_key = config.OLLAMA_API_KEY or "ollama"
                api_base = config.OLLAMA_API_BASE
                if api_base:
                    # Strip trailing /api or /api/generate as LiteLLM adds them
                    api_base = api_base.rstrip("/")
                    if api_base.endswith("/api"):
                        api_base = api_base[:-4]
                    if api_base.endswith("/api/generate"):
                        api_base = api_base[:-13]
            
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
