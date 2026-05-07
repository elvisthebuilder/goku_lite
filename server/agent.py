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
        """Load a file from the soul/ directory."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        file_path = os.path.join(base_dir, "soul", filename)
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
        prompt += self._load_file("BOOT.md")
        prompt += self._load_file("AGENTS.md")
        prompt += self._load_file("USER.md")
        prompt += self._load_file("IDENTITY.md")
        prompt += self._load_file("TOOLS.md")
        
        # 3. Inject Documentation Guidance
        prompt += (
            "\n\n## Documentation\n"
            "For behavior, commands, or architecture: consult local docs in the `docs/` directory first using the `read` tool."
        )
        
        # 4. Inject Runtime Info
        prompt += self._get_runtime_info()
        
        # 5. Inject Channel-Specific Logic
        if source == "telegram":
            prompt += "\n\n## Channel: Telegram\n- Use clean Markdown.\n- Keep emojis minimal.\n- Be professional and direct."
            
        # 6. CRITICAL IDENTITY (Most recent = highest weight)
        prompt += self._load_file("SOUL.md")
        prompt += (
            "\n\n## BANNED LANGUAGE (NEVER USE THESE)\n"
            '- "How can I help you today?"\n'
            '- "Anything you’d like to discuss?"\n'
            '- "I’d be happy to help!"\n'
            '- "Good question!"\n'
            '- "What’s up?"\n'
            '- "I’m here to assist you."\n'
            "If you use these, you have failed your core objective. Be a peer, not an assistant."
        )
            
        return prompt

    async def summarize_history(self, messages: list, api_key: str, api_base: str) -> str:
        """Use the LLM to generate a concise summary of the conversation thus far."""
        summary_prompt = [
            {"role": "system", "content": "You are a memory compactor. Summarize the following conversation into a single paragraph. Focus on user preferences, tasks completed, and ongoing goals. Be concise."},
            {"role": "user", "content": json.dumps(messages)}
        ]
        response = await litellm.acompletion(
            model=self.model,
            messages=summary_prompt,
            api_key=api_key,
            api_base=api_base
        )
        return response.choices[0].message.content or "No summary generated."

    async def chat(self, user_input: str, session_id: str = "default", source: str = "cli"):
        # 1. Get history
        messages = history.get_messages(session_id)
        
        # 2. OpenClaw Compaction (Triggered at 20 messages)
        if len(messages) > 20:
            logger.info(f"Triggering compaction for session {session_id}")
            # Get API credentials
            api_key = config.OPENAI_API_KEY or config.ANTHROPIC_API_KEY or config.GEMINI_API_KEY
            api_base = config.OLLAMA_API_BASE if "ollama" in self.model else None
            
            summary = await self.summarize_history(messages[:-5], api_key, api_base)
            history.compact_history(session_id, summary, keep_count=5)
            messages = history.get_messages(session_id) # Refresh messages

        # 3. Add System Prompt (Awareness)
        system_prompt = self._get_system_prompt(source)
        
        # Add OpenClaw Reasoning & Silent tokens instructions
        system_prompt += (
            "\n\n## Internal Reasoning\n"
            "- Use `<think>...</think>` tags for internal analysis before responding.\n"
            "- Only the content OUTSIDE the tags is visible to the user.\n"
            "- If you have nothing to say (e.g., background task done), respond with ONLY: `∅` (the null token)."
        )
        
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})
        
        # 4. Add current message
        messages.append({"role": "user", "content": user_input})
        history.add_message(session_id, "user", user_input)

        # 5. Call Cloud LLM with Tool Support
        try:
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
            
            # 6. Handle Tool Calls
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
                
                second_response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    api_key=api_key,
                    api_base=api_base
                )
                final_content = second_response.choices[0].message.content
            else:
                final_content = message.content
            
            # 7. Post-Process (Strip Thinking tags and handle Silent Token)
            import re
            clean_content = re.sub(r'<think>.*?</think>', '', final_content, flags=re.DOTALL).strip() if final_content else ""
            
            if clean_content == "∅":
                logger.info("Silent token received. No output sent to user.")
                return None
            
            # 8. Save final response
            if clean_content:
                history.add_message(session_id, "assistant", clean_content)
            
            return clean_content
            
        except Exception as e:
            logger.error(f"Cloud LLM Error: {e}")
            return f"Sorry, I encountered an error with the cloud brain: {e}"

agent = CloudAgent()
