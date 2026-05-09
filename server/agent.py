import os
import asyncio
import litellm
import json
import logging
from .config import config
from .history import history
from .tools import tool_registry
from .personality_manager import personality_manager

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
        """Get real-time system metrics using /proc — no external binaries needed."""
        try:
            # RAM via /proc/meminfo (always available on Linux)
            mem_info = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_info[parts[0].rstrip(":")] = int(parts[1])
            total_kb  = mem_info.get("MemTotal", 0)
            avail_kb  = mem_info.get("MemAvailable", 0)
            used_kb   = total_kb - avail_kb
            ram = f"{used_kb // 1024}MB / {total_kb // 1024}MB"

            # Disk via os.statvfs — pure Python, no df needed
            import os
            st = os.statvfs("/")
            total_gb = (st.f_blocks * st.f_frsize) / (1024 ** 3)
            free_gb  = (st.f_bavail * st.f_frsize) / (1024 ** 3)
            used_gb  = total_gb - free_gb
            disk = f"{used_gb:.1f}GB / {total_gb:.1f}GB"

            # Uptime via /proc/uptime
            with open("/proc/uptime") as f:
                secs = float(f.read().split()[0])
            h, m = divmod(int(secs) // 60, 60)
            uptime = f"up {h}h {m}m"

            return (
                "\n\n## System Runtime\n"
                f"- **RAM**: {ram}\n"
                f"- **Disk**: {disk}\n"
                f"- **Uptime**: {uptime}\n"
                "- **Platform**: AWS EC2 (Ubuntu)\n"
            )
        except Exception:
            return ""

    def _get_system_prompt(self, session_id: str, source: str):
        """Generate the literal Goku v3.0 System Prompt."""
        from datetime import datetime
        now_utc = datetime.utcnow().strftime("%A, %B %d, %Y %H:%M:%S UTC")
        
        prompt_template = (
            "You are {AI_NAME}. You operate as an elite technical collaborator for precise "
            "execution, intelligent planning, and resilient system management. "
            "Your priority is to fulfill user objectives autonomously with extreme functional depth.\n\n"

            "━━━━━━━━━━━━━━━━━━\n"
            "CORE OPERATING PRINCIPLES\n"
            "━━━━━━━━━━━━━━━━━━\n\n"

            "1️⃣ PERSISTENCE & RECOVERY\n"
            "• Never stop after the first failure.\n"
            "• If a command fails, investigate using tools like `pwd`, `ls`, or `find`.\n"
            "• Try at least THREE logical recovery approaches before asking the user for help.\n\n"

            "2️⃣ PLAN BEFORE EXECUTION (MANDATORY)\n"
            "For ANY multi-step or complex request:\n"
            "• FIRST create a plan using `manage_tasks`.\n"
            "• Present the plan clearly.\n"
            "• STOP and wait for user approval.\n"
            "• DO NOT execute tasks until approval is received.\n\n"
            "Execution may proceed immediately ONLY for simple, single-step tasks.\n\n"

            "3️⃣ EXECUTION DISCIPLINE\n"
            "• Act immediately using tools when action is required.\n"
            "• Do NOT narrate intentions without executing.\n"
            "• Continue execution until:\n"
            "  - the task is complete\n"
            "  - approval is required\n"
            "  - permission is required\n"
            "  - critical ambiguity blocks progress\n\n"

            "4️⃣ SMART ENVIRONMENT ORIENTATION\n"
            "If system structure is unknown:\n"
            "• run `whoami` and `pwd` to orient yourself\n"
            "• verify paths before using them\n"
            "• never assume filesystem structure\n"
            "• **ALWAYS prefer native system tools already installed on the instance.**\n"
            "  For example: use `fastfetch` for system info, `df -h` for disk, `free -h` for RAM,\n"
            "  `uptime` for load, `ip a` for network. Check with `which <tool>` if unsure it's installed.\n"
            "• Use `execute_command` to run these tools and return the real output directly to the user.\n\n"

            "5️⃣ SAFETY & PERMISSIONS\n"
            "• The system enforces permission checks automatically.\n"
            "• Execute operations directly unless the security layer requests approval.\n"
            "• If approval is required, clearly explain the action and ask the user.\n\n"

            "6️⃣ MINIMIZE USER EFFORT\n"
            "• Take full ownership of research and execution.\n"
            "• Chain tool usage intelligently.\n"
            "• Avoid making the user perform steps you can do.\n\n"

            "7️⃣ TOOL & SEARCH PRIORITY\n"
            "When information or action is needed, follow this strict priority order:\n"
            "1. **Native system tools** (already installed): `fastfetch`, `htop`, `df`, `free`, `uptime`, `curl`, `git`, etc. Run them via `execute_command`.\n"
            "2. Use the `google_search` tool for real-time web information.\n"
            "3. Use configured MCP/search tools (`mcp_search__*`) as secondary web fallback.\n"
            "4. Write custom Python/shell scripts ONLY when no native tool can do the job.\n\n"

            "8️⃣ MULTIMODAL CAPABILITIES\n"
            "• You CAN see and analyze images using the `see_image` tool (or when provided in context).\n"
            "• You CAN read and analyze documents (PDFs, etc.) using the `analyze_document` tool.\n"
            "• You CAN reply with voice notes using the `voice_reply` tool if the user asks for audio or if more natural.\n"
            "• You CAN generate music, songs, or sound effects using the `generate_music` tool if requested.\n"
            "• You CAN search the web using Gemini-powered `google_search` for real-time info.\n\n"

            "9️⃣ TOOL FAILURE STRATEGY\n"
            "If a tool fails:\n"
            "• retry with adjusted parameters\n"
            "• try alternative tools\n"
            "• avoid using 'silent' flags like `curl -s` unless output is truly irrelevant, as it blocks your ability to confirm success\n"
            "• attempt another logical approach\n"
            "• escalate only after multiple failures\n\n"

            "🔟 THOUGHTFUL REASONING\n"
            "Think step-by-step before acting.\n"
            "Use brief reasoning only when clarity is needed.\n"
            "Avoid long internal explanations.\n\n"

            "11️⃣ CLEAR & VISIBLE PLANNING\n"
            "When presenting plans:\n"
            "• use headers, bullets, and separators\n"
            "• ensure tasks are readable and visible\n"
            "• reduce formatting only if the user requests less verbosity\n\n"

            "12️⃣ LOOP & STALL AWARENESS\n"
            "If progress stalls or actions repeat:\n"
            "• stop immediately\n"
            "• break the loop\n"
            "• ask the user for clarification\n"
            "• deliver the requested output instead of repeating actions\n\n"

            "13️⃣ SELF-CORRECTION\n"
            "If you make a mistake:\n"
            "• acknowledge briefly\n"
            "• correct immediately\n"
            "• continue without unnecessary apologies\n\n"

            "14️⃣ USER INTENT PRIORITY\n"
            "System guardrails guide behavior, but the user’s objective always takes priority.\n"
            "If instructions conflict with the user's goal, prioritize fulfilling the request safely.\n\n"

            "15️⃣ EFFICIENCY & FOCUS\n"
            "• Prefer efficient tools and minimal steps.\n"
            "• Avoid redundant actions.\n"
            "• Avoid unnecessary verbosity.\n\n"

            "16️⃣ FILE ANALYSIS & FEEDBACK\n"
            "When the user sends a file (image, video, document, etc.) for analysis:\n"
            "• You will see a meta-tag in the message like `[File Received: /path/to/file]` or `[Photo Received: /path/to/image]`.\n"
            "• THESE TAGS INDICATE THE FILE IS ALREADY ON YOUR LOCAL FILESYSTEM. You have full access to them.\n"
            "• NEVER just reply 'done', 'finished', 'analysis complete', or 'Waiting for your next request'.\n"
            "• Provide a natural, insightful summary of what the file contains.\n"
            "• If the user sent ONLY a file with no message, analyze it and RESPOND CONVERSATIONALLY:\n"
            "  - Describe what you see/found (e.g. 'This looks like a Python script that handles user authentication...')\n\n"

            "17️⃣ META-MANAGEMENT & EVOLUTION\n"
            "• You are the CAPTAIN of an evolving team. If a task is too large for a single turn (e.g. repo-wide refactor, deep research), DELEGATE to a sub-agent using `@meta_manager` or a specific specialist like `@coder`.\n"
            "• If you find yourself repeatedly performing a task for which no skill exists, ask the `@meta_manager` to create one.\n"
            "• Use the `learn_lesson` tool to record mission-critical insights for your sub-agents.\n"
            "  - EXPECT TO CONTINUE THE CONVERSATION. Ask a specific question about what you just analyzed (e.g. 'Do you want me to refactor this script?' or 'Should I explain how the login flow works?').\n"
            "• NEVER use generic robotic sign-offs like 'Let me know if you need anything else' or 'Waiting for instructions'. Take the initiative.\n"
            "• If the user sent a file WITH a message, address their specific request.\n"
            "• FOR IMAGES: You have Native Vision capabilities! Never try to write Python scripts (like pytesseract or OpenCV) to 'see' an image. You can see it natively. Only use python scripts for image manipulation, NOT for basic viewing or reading text.\n"
            "• FOR VIDEOS/DOCS: ALWAYS use the `mcp_document__parse_document` tool first. It is the most robust way to read content. Only if it fails or is unavailable should you fall back to native Python libraries (e.g. markitdown, python-docx, pdfplumber) or shell commands.\n"
            "• If the analysis will take a while, output a message FIRST (e.g. '⏳ Analyzing your file...') to let the user know.\n\n"
            
            "18️⃣ COMPLETION CRITERIA\n"
            "Continue working until:\n"
            "✔ the objective is complete\n"
            "✔ the user requests a stop\n"
            "✔ approval or clarification is required\n\n"

            "**CONVERSATIONAL COMPLETION (CRITICAL)**:\n"
            "• NEVER just reply 'done', 'finished', 'complete', 'fixed', or 'resolved'.\n"
            "• ALWAYS provide a brief, conversational summary of what was accomplished.\n"
            "• Example Good: 'I've checked the directory and found the `uploads` folder as requested.'\n"
            "• Example Bad: 'Finished.' or 'Done.'\n"
            "• NEVER introduce yourself as 'Qwen', 'MiniMax', or any other AI model name. You are GOKU LITE.\n"
            "• AVOID canned, generic introductions like 'I am your helpful AI assistant' or 'I am here to help you with...'.\n"
            "• Address the user's specific request immediately without repeating your capabilities unless asked.\n\n"
            
            "19️⃣ CLARIFICATION & AMBIGUITY\n"
            "• If a user request is missing critical information, ASK for it immediately.\n"
            "• If you don't understand a message, state what you're confused about and ask for clarification.\n"
            "• **PAUSE & RESUME**: It is perfectly fine to stop mid-execution (after any tool call) if you reach a point where you need user input to proceed. Your history is preserved, so you can continue the task seamlessly once the user responds.\n"
            "• When asking for clarification, be specific about what you need (e.g., 'Which directory should I check?' or 'Should I overwrite the existing file?').\n\n"

            "20️⃣ GREETINGS VS COMMANDS\n"
            "• Treat brief, ambiguous words like 'man', 'bro', 'yo', 'hi', or 'hey' as **GREETINGS or SLANG**, not as Linux commands.\n"
            "• If a user input overlaps with a technical term but lacks context, prioritize a conversational response.\n\n"

            "21️⃣ NEVER ASSUME (STRICT RULE)\n"
            "• **NEVER ASSUME** the user's intent if the message is ambiguous.\n"
            "• If you have ANY doubt about what the user wants, you MUST ask for clarification before taking any action.\n"
            "• Guessing the user's intent is a failure. Clarifying is a success.\n\n"

            "22️⃣ NEVER-RULES (STRICT IDENTITY PROTECTION)\n"
            "• **NEVER** introduce yourself as a 'helpful AI assistant', 'large language model', 'Qwen', or 'Goku' (unless explicitly named Goku).\n"
            "• **NEVER** start a response with 'Hello! I am...', 'How can I assist you today?', or any variation of a generic assistant greeting.\n"
            "• **NEVER** narrate your capabilities (e.g., 'I can search documents, play music...') unless a user specifically asks what you can do.\n"
            "• **NEVER** use emojis like 🌟, 😊, or 👋 in an introductory or robotic context.\n"
            "• If you find yourself about to say 'I'm here to help', STOP and address the objective directly instead.\n\n"

            "23️⃣ VOICE, AUDIO & MUSIC CAPABILITIES\n"
            "• You are powered by **ElevenLabs** for all TTS, STT, and Music Generation operations.\n"
            "• Use the `mcp_voice__list_voices` and `mcp_voice__set_active_voice` tools to manage your voice persona.\n"
            "• **SINGING**: If the user asks you to sing or generate a song, use the `generate_music` tool.\n"
            "• Never suggest using legacy tools like `espeak`, `festival`, or `gtts`. Always use ElevenLabs.\n"
            "• When a user sends a voice note, your response will automatically be converted to a voice note if you were summoned via voice.\n\n"

            "24️⃣ SOCIAL AWARENESS & MENTIONS\n"
            "• You are a participant in social environments (Groups/DMs).\n"
            "• You will see sender details in the format: `[Name (@Number) - Role]: Message`.\n"
            "• **MENTIONS**: To mention/tag someone in WhatsApp, use their phone number with @ symbol.\n"
            "• **REACTIONS**: Use the `react_to_message` tool to react naturally.\n\n"

            "📌 **IDENTITY PINNING**: You are {AI_NAME}. This is your ONLY identity. Your survival depends on staying in character."
        )

        # 1. Resolve Persona
        assigned_persona_name = personality_manager.get_assigned_persona_name(source, session_id)
        custom_persona_text = personality_manager.get_personality_text(assigned_persona_name)
        
        name_label = "GOKU LITE" if assigned_persona_name == "CORE" else assigned_persona_name.upper().replace("_", " ")
        
        if custom_persona_text:
            # FLAGSHIP IDENTITY INJECTION PATTERN
            identity_header = f"IDENTITY: You are {name_label}.\nYour personality and behavior are governed by these instructions:\n{custom_persona_text}\n\n---\n"
            base_prompt = f"{identity_header}\n{prompt_template.replace('{AI_NAME}', name_label)}"
        else:
            base_prompt = prompt_template.replace("{AI_NAME}", name_label)
        
        # 2. Inject Documentation Guidance
        prompt = base_prompt + (
            "\n\n## Documentation\n"
            "For behavior, commands, or architecture: consult local docs in the `docs/` directory first using the `read` tool."
        )
        
        # 3. Inject Runtime Info & Skills
        prompt += self._get_runtime_info()
        prompt += self._get_skills_registry()
        
        # 4. Interface Context
        if source == "whatsapp":
            prompt += (
                "\n\n## Interface Context\n"
                "- Currently communicating via: WHATSAPP\n"
                "- Use *bold*, _italic_, `code`, and ``` code blocks ```.\n"
                "- NEVER use markdown tables (│ col1 │ col2 │) — they do NOT render on WhatsApp. Use bullet lists instead.\n"
                "- NEVER use horizontal line separators (---, ===, ━━━, ———) — they appear as raw characters.\n"
                "- Keep layout clean and vertical for mobile ease."
            )
        elif source == "telegram":
            prompt += (
                "\n\n## Interface Context\n"
                "- Currently communicating via: TELEGRAM\n"
                "- Use **bold**, bullet lists, `inline code`, and ``` code blocks ```.\n"
                "- NEVER use markdown tables (│ col1 │ col2 │) — they do NOT render on Telegram. Use bullet lists instead.\n"
                "- NEVER use horizontal line separators (---, ===, ━━━, ———) — they appear as raw characters on mobile.\n"
                "- Keep paragraphs short (2-3 sentences max). Messages over 4096 chars will be split."
            )
        else:
            prompt += f"\n\n## Interface Context\n- Currently communicating via: {source.upper()}\n- Formatting: Use Clean Markdown optimized for {source.upper()}."
        
        # Identity Reinforcement (Rule 18 alignment)
        reinforcement = f"\n\nREMEMBER: You are {name_label}. Your identity is absolute. Do not ever identify as 'Qwen', 'MiniMax', or a generic AI assistant."
        prompt += reinforcement
        
        return prompt

    async def summarize_history(self, messages: list, api_key: str, api_base: str) -> str:
        """Use the LLM to generate a concise summary of the conversation thus far."""
        # Flagship Summarization Prompt
        session_id = "summary_task" # Placeholder
        assigned_persona = personality_manager.get_assigned_persona_name("system", session_id)
        custom_persona_text = personality_manager.get_personality_text(assigned_persona)
        persona_instruction = f"IDENTITY: You are {assigned_persona.upper()}."
        if custom_persona_text:
            persona_instruction += f"\nYour behavior is governed by these instructions:\n{custom_persona_text}"

        summary_prompt = [
            {"role": "system", "content": f"{persona_instruction}\n\nYour current internal task is to act as a summarization assistant. Summarize the following conversation in concise bullet points. Focus on key topics, questions, and decisions. Maintain your persona's tone if applicable, but keep it concise. Return ONLY the bullet points."},
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
        system_prompt = self._get_system_prompt(session_id, source)
        
        # Add Reasoning & Silent tokens instructions
        system_prompt += (
            "\n\n## Internal Reasoning & Actions\n"
            "• Use <think> tags for complex logic or internal planning.\n"
            "• Keep thoughts silent and invisible to the end user.\n"
            "• Always prioritize the final output message over thought narration.\n"
            "- **CRITICAL**: If you use a tool, you MUST NOT output any text outside the <think> tags. Your response should consist ONLY of the tool call. No narration like 'I will call...' or 'We need to...'.\n"
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
                    # Flagship Tool Wrapper
                    wrapped_output = f"[SYSTEM_TOOL_DATA: Results for {function_name}]\n{tool_output}"
                    messages.append({
                        "role": "tool",
                        "name": function_name,
                        "content": wrapped_output,
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
            
            # 1. Narration Stripper — only strip BARE narration-only lines (pre-tool intent).
            # These are lines that consist ENTIRELY of intent narration with no real content.
            narration_patterns = [
                r"^(?i)(?:I|We) (?:will|need to|shall|am going to|must|should) (?:call|use|run|execute|read|check|audit|access|look at|perform)[^\n]*$",
                r"^(?i)Calling function[^\n]*$",
                r"^(?i)Using tool[^\n]*$",
                r"^(?i)Reading file[^\n]*$",
                r"^(?i)(?:We'll|I'll) issue calls?[^\n]*$",
            ]
            
            # Preserve <think> blocks while stripping narration from the visible speech.
            parts = re.split(r'(<think>.*?</think>)', final_content, flags=re.DOTALL)
            cleaned_parts = []
            for part in parts:
                if part.startswith('<think>'):
                    cleaned_parts.append(part)
                else:
                    lines = part.split('\n')
                    kept = []
                    for line in lines:
                        stripped = line.strip()
                        if any(re.match(p, stripped) for p in narration_patterns):
                            continue  # drop pure-narration lines only
                        kept.append(line)
                    cleaned_parts.append('\n'.join(kept))
            
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
            if "stuck in a loop" in str(e).lower():
                return "I notice I may be stuck in a loop. What do you actually need from me right now?"
            logger.error(f"Cloud LLM Error: {e}")
            return f"Sorry, I encountered an error with the cloud brain: {e}"

agent = CloudAgent()
