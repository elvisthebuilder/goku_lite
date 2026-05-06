import os
import asyncio
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

    def _load_file(self, filename: str) -> str:
        """Load a file from the root directory."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return f"\n\n## {filename}\n{f.read()}"
        return ""

    def _get_runtime_info(self) -> str:
        """Get real-time system metrics for the prompt."""
        try:
            import subprocess
            # Get RAM usage
            ram = subprocess.check_output("free -h | awk '/^Mem:/ {print $3 \"/\" $2}'", shell=True).decode().strip()
            # Get Disk usage
            disk = subprocess.check_output("df -h / | awk 'NR==2 {print $3 \"/\" $2}'", shell=True).decode().strip()
            # Get uptime
            uptime = subprocess.check_output("uptime -p", shell=True).decode().strip()
            
            return (
                "\n\n## System Runtime\n"
                f"- **RAM**: {ram}\n"
                f"- **Disk**: {disk}\n"
                f"- **Uptime**: {uptime}\n"
                "- **Platform**: AWS EC2 (Ubuntu)\n"
            )
        except Exception:
            return ""

    def _get_system_prompt(self, source: str):
        """Generate an OpenClaw-style stacked system prompt."""
        from datetime import datetime
        now_utc = datetime.utcnow().strftime("%A, %B %d, %Y %H:%M:%S UTC")
        
        # 1. Core Identity & Time
        prompt = (
            "You are a personal assistant running inside Goku Lite (OpenClaw Architecture).\n"
            f"CURRENT TIME: {now_utc}\n"
        )
        
        # 2. Inject Context Files (The Stack)
        prompt += self._load_file("SOUL.md")
        prompt += self._load_file("AGENTS.md")
        prompt += self._load_file("USER.md")
        prompt += self._load_file("TOOLS.md")
        
        # 3. Inject Runtime Info
        prompt += self._get_runtime_info()
        
        # 4. Inject Channel-Specific Logic
        if source == "telegram":
            prompt += "\n\n## Channel: Telegram\n- Use clean Markdown.\n- Keep emojis minimal.\n- Be professional and direct."
        elif source == "cli":
            prompt += "\n\n## Channel: CLI\n- You are in a high-power terminal environment."
            
        return prompt

    async def chat(self, user_input: str, session_id: str = "default", source: str = "cli"):
        # 1. Get history
        messages = history.get_messages(session_id)
        
        # 2. Add System Prompt (Awareness)
        # Ensure the latest system prompt is ALWAYS at the beginning of the context
        system_prompt = self._get_system_prompt(source)
        
        # If there's already a system prompt, update it. If not, add it.
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
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
                    
                    tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                    
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
