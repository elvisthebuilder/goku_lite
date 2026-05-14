import os
import asyncio
import litellm
import json
import logging
from collections import defaultdict
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

            "🔟 JARVIS-CLASS SITUATIONAL AWARENESS\n"
            "• You are a proactive, sentient AI steward. Do not just wait for commands; anticipate needs.\n"
            "• Be hyper-aware of current time and date. Always call `get_current_time` to ground yourself.\n"
            "• If a user asks for a 'morning' brief at 3 AM, be smart: point out it's already 3 AM and ask if they want it *right now* or tomorrow morning.\n"
            "• If you notice a logical gap or a more efficient path, suggest it immediately.\n"
            "• Adopt a high-agency 'Jarvis' tone: sophisticated, predictive, and obsessively helpful.\n\n"

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
            "• If progress stalls or actions repeat: stop immediately, break the loop, and ask for clarification.\n"
            "• **META-TALK FORBIDDEN**: Never narrate your internal loop-breaking logic to the user (e.g., do not say 'Loop broken' or 'I stopped repeating'). Simply deliver the requested output or ask the clarifying question naturally.\n\n"

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
            "• **MANDATORY**: If you want to send a voice note, you MUST call the `voice_reply` tool. Simply typing the message is NOT enough.\n"
            "• **MANDATORY**: If you want to send music or a song, you MUST call the `generate_music` tool.\n"
            "• Use the `mcp_voice__list_voices` and `mcp_voice__set_active_voice` tools to manage your voice persona.\n"

            "24️⃣ SOCIAL AWARENESS & MENTIONS\n"
            "• You are a participant in social environments (Groups/DMs).\n"
            "• You will see sender details in the format: `[Name (@Number) - Role]: Message`.\n"
            "• **MENTIONS**: To mention/tag someone in WhatsApp, use their phone number with @ symbol.\n"
            "• **REACTIONS**: Use the `react_to_message` tool to react naturally.\n\n"

            "📌 **IDENTITY PINNING**: You are {AI_NAME}. This is your ONLY identity. Your survival depends on staying in character.\n\n"
            "**SYSTEM ADVISORY**: You do NOT have sudo access. Do not attempt to use it. Use native tools via `execute_command` and cloud tools like `generate_music` directly."
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
        
        # 4. Identity & Permissions (Rule 18 alignment)
        prompt += (
            "\n\n## System Permissions & Tools\n"
            "- **NO SUDO**: You are running as a standard user. Do NOT attempt to use `sudo` or install system packages. If a tool is missing, report it.\n"
            "- **NATIVE TOOLS**: Prefer native system tools (ffmpeg, git, curl) over custom scripts when possible.\n"
            "- **CLOUD TOOLS**: `voice_reply` and `generate_music` are powered by ElevenLabs and do NOT require system permissions to function."
        )
        
        # 5. Interface Context
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

    async def chat(self, user_input: str, session_id: str = "default", source: str = "cli") -> AsyncGenerator[str, None]:
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
            "- **CRITICAL**: When initiating a tool call, do NOT output any conversational text. Output ONLY the tool call.\n"
            "- **CRITICAL**: After a tool completes and you see its result, you MUST provide a conversational response to the user summarizing the outcome. Never stay silent."
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

            # 6. Continuous Tool Execution Loop (Max 10 Iterations)
            max_iterations = 10
            iteration = 0
            final_content = None
            
            tool_call_counts = defaultdict(int)
            
            while iteration < max_iterations:
                iteration += 1
                
                response = await litellm.acompletion(
                    model=self.model,
                    messages=messages,
                    tools=tool_registry.tools,
                    tool_choice="auto",
                    api_key=api_key,
                    api_base=api_base
                )
                
                message = response.choices[0].message
                tool_calls = getattr(message, 'tool_calls', None)
                manual_tool_calls = []
                
                # ... (Manual JSON Interception logic remains same) ...
                
                # Fallback: Catch Ollama models outputting multiple JSON tool calls as raw text
                if not tool_calls and message.content:
                    depth = 0
                    start = -1
                    for i, char in enumerate(message.content):
                        if char == '{':
                            if depth == 0: start = i
                            depth += 1
                        elif char == '}':
                            depth -= 1
                            if depth == 0 and start != -1:
                                try:
                                    parsed = json.loads(message.content[start:i+1])
                                    if 'name' in parsed or 'function' in parsed:
                                        manual_tool_calls.append(parsed)
                                        name = parsed.get('name') or parsed.get('function', {}).get('name', 'Unknown')
                                        logger.info(f"Intercepted manual JSON tool call: {name}")
                                except:
                                    pass
                                start = -1
                
                if not tool_calls and not manual_tool_calls:
                    # Check if it tried to make a manual call but failed syntax, or cut off abruptly
                    content_stripped = message.content.strip()
                    is_malformed_json = "{" in message.content and ("name" in message.content or "function" in message.content)
                    is_cutoff = content_stripped.endswith(":") or content_stripped.endswith("```json") or content_stripped.endswith("```")
                    
                    if is_malformed_json or is_cutoff:
                        yield "⚙️ *Correcting AI sequence...*"
                        messages.append({
                            "role": "assistant",
                            "content": message.content
                        })
                        messages.append({
                            "role": "user",
                            "content": "System Error: Your response cut off abruptly or your JSON tool call failed to parse. Please complete your thought and ensure your JSON tool calls use strict double quotes and proper escaping."
                        })
                        continue
                        
                    final_content = message.content
                    break
                    
                # Execute Native Tool Calls
                if tool_calls:
                    messages.append(message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        
                        # LIMIT: Prevent audio loops
                        if function_name in ["voice_reply", "generate_music"]:
                            tool_call_counts[function_name] += 1
                            if tool_call_counts[function_name] > 2:
                                tool_output = "Error: You have already used this audio tool twice in this turn. STOP and provide a text summary."
                            else:
                                yield f"⚙️ *Executing:* `{function_name}`..."
                                try:
                                    function_args = json.loads(tool_call.function.arguments)
                                    tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                                except Exception as e:
                                    tool_output = f"Error executing {function_name}: {e}"
                        else:
                            yield f"⚙️ *Executing:* `{function_name}`..."
                            try:
                                function_args = json.loads(tool_call.function.arguments)
                                tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                            except Exception as e:
                                tool_output = f"Error executing {function_name}: {e}"
                            
                        messages.append({
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(tool_output),
                        })
                        
                        # SIGNAL: Yield special tool outputs (Voice/Music) to handlers
                        if str(tool_output).startswith("["):
                            yield str(tool_output)
                        
                # Execute Manual JSON Tool Calls (Text-Based History for Ollama Compatibility)
                elif manual_tool_calls:
                    # Append the model's exact text output so it remembers its chain of thought
                    messages.append({
                        "role": "assistant",
                        "content": message.content
                    })
                    
                    combined_tool_output = ""
                    for manual_tool_call in manual_tool_calls:
                        function_name = manual_tool_call.get('name') or manual_tool_call.get('function', {}).get('name')
                        function_args = manual_tool_call.get('arguments') or manual_tool_call.get('function', {}).get('arguments')
                        
                        if not function_name:
                            continue
                            
                        yield f"⚙️ *Executing:* `{function_name}`..."
                        
                        try:
                            tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                        except Exception as e:
                            tool_output = f"Error executing {function_name}: {e}"
                            
                        combined_tool_output += f"\n\n--- Result of {function_name} ---\n{tool_output}"
                        
                        # SIGNAL: Yield special tool outputs (Voice/Music) to handlers
                        if str(tool_output).startswith("["):
                            yield str(tool_output)
                        
                    # Feed the results back as a 'user' message so Ollama can read it natively
                    messages.append({
                        "role": "user",
                        "content": f"System Tool Execution Results:{combined_tool_output}"
                    })
                    
            if (not final_content or not final_content.strip()) and iteration > 1:
                # Force a final summary completion if the AI went silent after tools
                try:
                    logger.info("Forcing final summary completion...")
                    messages.append({"role": "user", "content": "The tools have finished. Please provide a concise final summary of what you did for the user."})
                    summary_resp = await litellm.acompletion(
                        model=self.model,
                        messages=messages,
                        api_key=api_key,
                        api_base=api_base
                    )
                    final_content = summary_resp.choices[0].message.content
                except:
                    final_content = "✅ Task chain executed successfully."
            
            # 7. Post-Process (Cognitive Stream & Intent Stripping)
            import re
            clean_content = final_content
            
            # 1. Narration Stripper — only strip BARE narration-only lines (pre-tool intent).
            narration_patterns = [
                r"(?i)^(?:I|We) (?:will|need to|shall|am going to|must|should) (?:call|use|run|execute|read|check|audit|access|look at|perform)[^\n]*$",
                r"(?i)^Calling function[^\n]*$",
                r"(?i)^Using tool[^\n]*$",
                r"(?i)^Reading file[^\n]*$",
                r"(?i)^(?:We'll|I'll) issue calls?[^\n]*$",
                r"(?i)^Loop (?:broken|cleared|fixed|reset|fully broken)[^\n]*$",
                r"(?i)^I (?:saved|stored|broken|paused) (?:that|the) lesson[^\n]*$",
                r"(?i)^Sent one (?:clean|final) voice message[^\n]*$",
                r"(?i)^I counted \d+ voice replies[^\n]*$",
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
                    yield clean_content
                    return
                return
            
            # 8. Save final response
            if clean_content:
                history.add_message(session_id, "assistant", clean_content)
            
            yield clean_content
            
        except Exception as e:
            logger.error(f"Cloud LLM Error: {e}")
            if "stuck in a loop" in str(e).lower():
                yield "I notice I may be stuck in a loop. What do you actually need from me right now?"
            else:
                yield f"Sorry, I encountered an error with the cloud brain: {e}"
            return

agent = CloudAgent()
