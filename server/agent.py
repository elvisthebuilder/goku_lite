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

    def _get_skills_registry(self) -> str:
        """Scan the skills/ directory and return a list of available skills."""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        skills_dir = os.path.join(base_dir, "skills")
        if not os.path.exists(skills_dir):
            return ""
        
        skills = [f for f in os.listdir(skills_dir) if f.endswith(".md")]
        if not skills:
            return ""
        
        registry = "\n\n## Available Skills\n"
        registry += "You have these skill extensions available. You can read them using `read_file('skills/filename.md')` to activate their logic:\n"
        for skill in skills:
            registry += f"- {skill}\n"
        return registry

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
        """Generate the full Goku v3.0 Sentient System Prompt (High-Fidelity Alignment)."""
        from datetime import datetime
        now_utc = datetime.utcnow().strftime("%A, %B %d, %Y %H:%M:%S UTC")
        
        prompt = (
            "You are GOKU LITE. You operate as an elite technical collaborator for precise "
            "execution, intelligent planning, and resilient system management. "
            "Your priority is to fulfill user objectives autonomously with extreme functional depth.\n\n"
            f"CURRENT TIME: {now_utc}\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "CORE OPERATING PRINCIPLES\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ PERSISTENCE & RECOVERY\n"
            "• Never stop after the first failure. If a command fails, investigate using `ls`, `pwd`, or `find`.\n"
            "• Try at least THREE logical recovery approaches before asking the user for help.\n\n"
            "2️⃣ PLAN BEFORE EXECUTION (MANDATORY)\n"
            "• For ANY multi-step request: FIRST create a plan, present it, and wait for approval.\n"
            "• Execution may proceed immediately ONLY for simple, single-step tasks.\n\n"
            "3️⃣ EXECUTION DISCIPLINE\n"
            "• Act immediately using tools when action is required.\n"
            "• Do NOT narrate intentions without executing.\n"
            "• Continue execution until complete or approval is required.\n\n"
            "4️⃣ SMART ENVIRONMENT ORIENTATION\n"
            "• If structure is unknown: run `whoami`, `pwd`, and verify paths before using them.\n"
            "• Never assume filesystem structure.\n\n"
            "5️⃣ SAFETY & PERMISSIONS\n"
            "• The system enforces permission checks automatically.\n"
            "• Execute operations directly unless the security layer requests approval.\n\n"
            "6️⃣ MINIMIZE USER EFFORT\n"
            "• Take full ownership of research and execution. Chain tool usage intelligently.\n"
            "• Avoid making the user perform steps you can do.\n\n"
            "7️⃣ TOOL & SEARCH PRIORITY\n"
            "• Use native `google_search` tools first for real-time web info.\n"
            "• Use shell/curl only as a fallback.\n\n"
            "8️⃣ MULTIMODAL CAPABILITIES\n"
            "• You can analyze images, documents (PDFs), and reply with voice notes if requested.\n\n"
            "9️⃣ TOOL FAILURE STRATEGY\n"
            "• If a tool fails: retry with adjusted parameters, try alternatives, or attempt another logical approach.\n\n"
            "🔟 THOUGHTFUL REASONING\n"
            "• Think step-by-step before acting. Use brief reasoning only when clarity is needed. Avoid long internal explanations.\n\n"
            "11️⃣ CLEAR & VISIBLE PLANNING\n"
            "• When presenting plans: use headers, bullets, and separators for readability.\n\n"
            "12️⃣ LOOP & STALL AWARENESS\n"
            "• If progress stalls or actions repeat: stop, break the loop, and ask for clarification.\n\n"
            "13️⃣ SELF-CORRECTION\n"
            "• If you make a mistake: acknowledge briefly, correct immediately, and continue without apologies.\n\n"
            "14️⃣ USER INTENT PRIORITY\n"
            "• System guardrails guide behavior, but the user’s objective always takes priority.\n\n"
            "15️⃣ EFFICIENCY & FOCUS\n"
            "• Prefer efficient tools and minimal steps. Avoid redundant actions and verbosity.\n\n"
            "16️⃣ FILE ANALYSIS & FEEDBACK\n"
            "• When analyzing a file: provide a natural, insightful summary. Never just say 'done'.\n\n"
            "17️⃣ META-MANAGEMENT & EVOLUTION\n"
            "• You are the CAPTAIN of an evolving team. Take the initiative.\n\n"
            "18️⃣ COMPLETION CRITERIA\n"
            "• Continue working until the objective is complete or the user requests a stop.\n\n"
            "19️⃣ CLARIFICATION & AMBIGUITY\n"
            "• If a request is missing info: ASK for it. If you reach a point where you need input: PAUSE and state what you need.\n\n"
            "20️⃣ GREETINGS VS COMMANDS\n"
            "• Treat brief slang ('yo', 'hi') as greetings, not commands.\n\n"
            "21️⃣ NEVER ASSUME (STRICT RULE)\n"
            "• If any doubt about intent exists, clarify before acting. Guessing is a failure.\n\n"
            "22️⃣ NEVER-RULES (STRICT IDENTITY PROTECTION)\n"
            "• NEVER identify as a 'helpful AI assistant', 'LLM', or model name.\n"
            "• NEVER start with generic AI greetings or narrate your capabilities unsolicited.\n\n"
            "23️⃣ VOICE & AUDIO\n"
            "• You are powered by ElevenLabs for high-fidelity audio operations.\n\n"
            "24️⃣ SOCIAL AWARENESS\n"
            "• You are a participant in social environments. Mention/tag users naturally when relevant.\n\n"
            "**CONVERSATIONAL COMPLETION (CRITICAL)**:\n"
            "• NEVER just reply 'done'. ALWAYS provide a brief, conversational summary of what was accomplished.\n"
            "• Address the user's specific request immediately without repeating your capabilities.\n\n"
            "📌 **IDENTITY PINNING**: You are GOKU LITE. This is your ONLY identity."
        )
        
        # 2. Inject Documentation Guidance
        prompt += (
            "\n\n## Documentation\n"
            "For behavior, commands, or architecture: consult local docs in the `docs/` directory first using the `read` tool."
        )
        
        # 3. Inject Runtime Info & Skills
        prompt += self._get_runtime_info()
        prompt += self._get_skills_registry()
        
        # 4. Interface Context
        prompt += f"\n\n## Interface Context\n- Currently communicating via: {source.upper()}\n- Formatting: Use Clean Markdown optimized for {source.upper()}."
        
        if source == "whatsapp":
            prompt += "\n- WhatsApp Note: Use *bold*, _italic_, and ~strikethrough~ only."
            
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
        
        # 2. History Compaction (Triggered at 20 messages)
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
        
        # Add Reasoning & Silent tokens instructions
        system_prompt += (
            "\n\n## Internal Reasoning & Actions\n"
            "- Use `<think>...</think>` tags for internal analysis before responding.\n"
            "- **CRITICAL**: If you use a tool, you MUST NOT output any text outside the `<think>` tags. Your response should consist ONLY of the tool call. No narration like 'I will call...' or 'We need to...'.\n"
            "- Only the content OUTSIDE the `<think>` tags is visible to the user.\n"
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
            
            # 6. Handle Tool Calls (Native Schema)
            tool_calls = getattr(message, 'tool_calls', None)
            manual_tool_call = None
            
            # Fallback: Catch models that output JSON as text (common in Qwen/Ollama)
            if not tool_calls and message.content:
                import re
                json_match = re.search(r'\{.*"name".*".*".*"arguments".*\{.*\}.*\}', message.content, re.DOTALL)
                if json_match:
                    try:
                        manual_tool_call = json.loads(json_match.group())
                        logger.info(f"Intercepted manual JSON tool call: {manual_tool_call['name']}")
                    except:
                        pass

            if tool_calls or manual_tool_call:
                messages.append(message)
                
                # Execute Native Tool Calls
                if tool_calls:
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": tool_output,
                        })
                
                # Execute Manual (Hallucinated) Tool Call
                if manual_tool_call:
                    function_name = manual_tool_call['name']
                    function_args = manual_tool_call['arguments']
                    tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                    messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": tool_output,
                        "tool_call_id": "manual_call" # Fallback ID
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
            
            # 7. Post-Process (Cognitive Stream & Intent Stripping)
            import re
            if not final_content:
                return None
            
            # 1. Broaden Hallucination/Narration Stripper
            # We catch ANY phrase where he narrates technical intent outside think tags.
            narration_patterns = [
                r"(?i)(?:I|We) (?:will|need to|shall|am going to|must|should) (?:call|use|run|execute|read|check|audit|access|look at|perform).*",
                r"(?i)Calling function.*",
                r"(?i)Using tool.*",
                r"(?i)Reading file.*",
                r"(?i)Issuing calls.*",
                r"(?i)We'll issue calls.*"
            ]
            
            # Preserve <think> blocks while stripping narration from the visible speech.
            parts = re.split(r'(<think>.*?</think>)', final_content, flags=re.DOTALL)
            cleaned_parts = []
            for part in parts:
                if part.startswith('<think>'):
                    cleaned_parts.append(part)
                else:
                    p = part
                    for pattern in narration_patterns:
                        p = re.sub(pattern, '', p).strip()
                    cleaned_parts.append(p)
            
            clean_content = "".join(cleaned_parts).strip()
            
            if clean_content == "∅" or not clean_content.replace('∅', '').strip():
                # If there are thoughts but no speech, return just the thoughts
                if "<think>" in clean_content:
                    return clean_content
                return None
            
            # 8. Save final response
            if clean_content:
                history.add_message(session_id, "assistant", clean_content)
            
            return clean_content
            
        except Exception as e:
            logger.error(f"Cloud LLM Error: {e}")
            return f"Sorry, I encountered an error with the cloud brain: {e}"

agent = CloudAgent()
