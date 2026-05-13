import os
import asyncio
import httpx
import logging
import subprocess
import time
from .memory import memory
from .config import config

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": "Search the web for real-time information. Use the results to provide a natural, conversational answer.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a file in the project directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the file."}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write or update a file in the project directory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the file."},
                            "content": {"type": "string", "description": "The text content to write."}
                        },
                        "required": ["path", "content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "Execute a safe shell command in the terminal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "The shell command to run."}
                        },
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_save",
                    "description": "Store a fact or context in long-term memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "The information to remember."},
                            "protected": {"type": "boolean", "description": "If true, this memory will NOT be deleted by a standard clear_memory command."}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_query",
                    "description": "Query long-term memory for past context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The topic to search for."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "Get the current health and configuration of Goku Lite.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_document",
                    "description": "Parse a PDF, DOCX, or Excel file into clean Markdown text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the document file."}
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_tasks",
                    "description": "Create, update, or list tasks for a multi-step objective. Mandatory for complex plans.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["add", "update", "list", "clear"]},
                            "tasks": {"type": "array", "items": {"type": "string"}},
                            "index": {"type": "integer"}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "remind_me",
                    "description": "Schedule a reminder to be sent to the user after a delay. Use this when the user asks to be reminded about something.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {"type": "string", "description": "The reminder message to send."},
                            "delay_minutes": {"type": "integer", "description": "How many minutes from now to send the reminder."}
                        },
                        "required": ["message", "delay_minutes"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_briefing_time",
                    "description": "Change the time of the daily morning briefing. Use this when the user asks to be texted at a different time.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hour": {"type": "integer", "description": "The hour (0-23) in UTC."},
                            "minute": {"type": "integer", "description": "The minute (0-59)."}
                        },
                        "required": ["hour", "minute"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_metrics",
                    "description": "Fetch REAL RAM and Disk usage from the Linux server. Use this whenever the user asks about specs.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_time",
                    "description": "Fetch the absolute current UTC time from the server clock.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_history",
                    "description": "Wipe the current conversation history. Use this if the user wants to start a fresh chat or forget the current context.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "clear_memory",
                    "description": "Wipe long-term vector memory. By default, it preserves 'protected' memories.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "delete_protected": {"type": "boolean", "description": "If true, even protected memories will be wiped. Danger!"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_persona",
                    "description": "Change the active persona for the current session. Example: 'researcher', 'assistant', 'CORE'.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "The name of the persona to activate."}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mcp_voice__list_voices",
                    "description": "List all available ElevenLabs voices with their names and IDs.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "mcp_voice__set_active_voice",
                    "description": "Set the active ElevenLabs voice ID for speech generation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "voice_id": {"type": "string", "description": "The ElevenLabs voice ID."}
                        },
                        "required": ["voice_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_reply",
                    "description": "Send a spoken voice response instead of text. Use this when the user asks for audio or if more natural.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "The text to convert to speech."}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_music",
                    "description": "Generate a 30-second music clip based on a prompt.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Description of the music to generate."}
                        },
                        "required": ["prompt"]
                    }
                }
            }
        ]

    async def execute(self, tool_name, args, session_id=None):
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        
        if tool_name == "google_search":
            query = args.get("query")
            
            # Strategy 1: Tavily
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post("https://api.tavily.com/search", json={"api_key": tavily_key, "query": query})
                        results = resp.json().get("results", [])
                        return "\n".join([f"- {r['title']}: {r['content'][:300]} ({r['url']})" for r in results[:3]])
                except Exception as e:
                    logger.warning(f"Tavily search failed: {e}. Trying fallback...")
            
            # Strategy 2: Gemini Google Search
            if config.GEMINI_API_KEY:
                try:
                    import litellm
                    resp = await litellm.acompletion(
                        model="gemini/gemini-2.5-flash",
                        messages=[{"role": "user", "content": f"Search Google for: {query}"}],
                        api_key=config.GEMINI_API_KEY,
                        tools=[{"type": "google_search_retrieval", "google_search_retrieval": {}}]
                    )
                    return resp.choices[0].message.content
                except Exception as e:
                    logger.warning(f"Gemini Google search failed: {e}")

            return "Error: No search provider (Tavily or Gemini) is configured or available."

        elif tool_name == "read_file":
            path = args.get("path")
            try:
                with open(path, "r") as f:
                    return f.read()
            except Exception as e:
                return f"Error reading file: {e}"

        elif tool_name == "write_file":
            path = args.get("path")
            content = args.get("content")
            try:
                with open(path, "w") as f:
                    f.write(content)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error writing file: {e}"

        elif tool_name == "execute_command":
            command = args.get("command")
            forbidden = ["rm ", "> /", "mv "]
            if any(f in command for f in forbidden):
                return "Error: Command contains forbidden operations for safety."
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                return f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            except Exception as e:
                return f"Command failed: {e}"

        elif tool_name == "memory_save":
            text = args.get("text")
            protected = args.get("protected", False)
            await memory.add_memory(text, protected=protected)
            return f"Saved to memory: {text} (Protected: {protected})"

        elif tool_name == "memory_query":
            query = args.get("query")
            results = await memory.search_memory(query)
            if not results: return "No relevant memories found."
            return "\n".join([f"- {r['text']} (at {time.ctime(r['timestamp'])})" for r in results])

        elif tool_name == "get_system_status":
            db_type = "Remote (SQL)" if config.DATABASE_URL else "Local (SQLite)"
            mem_type = "Remote (Qdrant Cloud)" if config.QDRANT_API_KEY else "Disabled"
            return f"🐉 Goku Lite Status:\n- Model: {config.GOKU_MODEL}\n- Database: {db_type}\n- Memory: {mem_type}\n- Mode: Cloud-Native"

        elif tool_name == "analyze_document":
            path = args.get("path")
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(path)
                return result.text_content
            except Exception as e:
                return f"Google Search failed: {e}"

        elif tool_name == "remind_me":
            message = args.get("message")
            delay_minutes = args.get("delay_minutes", 5)
            delay_seconds = delay_minutes * 60
            from .scheduler import schedule_one_time
            asyncio.create_task(schedule_one_time(delay_seconds, message))
            return f"Got it! I'll remind you about '{message}' in {delay_minutes} minute(s)."

        elif tool_name == "get_current_time":
            from datetime import datetime, timedelta
            now = datetime.utcnow()
            
            def get_countdown(h, m):
                target = now.replace(hour=h, minute=m, second=0, microsecond=0)
                if target <= now:
                    target += timedelta(days=1)
                diff = target - now
                hours, remainder = divmod(int(diff.total_seconds()), 3600)
                minutes, _ = divmod(remainder, 60)
                return f"{hours}h {minutes}m"

            morning = get_countdown(config.BRIEFING_HOUR, config.BRIEFING_MINUTE)
            afternoon = get_countdown(config.AFTERNOON_HOUR, config.AFTERNOON_MINUTE)
            evening = get_countdown(config.EVENING_HOUR, config.EVENING_MINUTE)

            return (
                f"Current UTC Time: {now.strftime('%H:%M:%S')}\n"
                f"Date: {now.strftime('%Y-%m-%d')}\n\n"
                f"--- Persistent Schedule Status ---\n"
                f"☀️ Morning Brief ({config.BRIEFING_HOUR:02d}:{config.BRIEFING_MINUTE:02d} UTC): Starts in {morning}\n"
                f"🌤️ Afternoon Check ({config.AFTERNOON_HOUR:02d}:{config.AFTERNOON_MINUTE:02d} UTC): Starts in {afternoon}\n"
                f"🌙 Evening Wrap ({config.EVENING_HOUR:02d}:{config.EVENING_MINUTE:02d} UTC): Starts in {evening}"
            )

        elif tool_name == "get_system_metrics":
            try:
                # RAM via /proc/meminfo — no 'free' binary needed
                mem_info = {}
                with open("/proc/meminfo") as f:
                    for line in f:
                        parts = line.split()
                        if len(parts) >= 2:
                            mem_info[parts[0].rstrip(":")] = int(parts[1])
                total_mb = mem_info.get("MemTotal", 0) // 1024
                avail_mb = mem_info.get("MemAvailable", 0) // 1024
                used_mb  = total_mb - avail_mb
                ram_str  = f"{'':>12}total        used        free\nMem:{total_mb:>12}       {used_mb:>8}       {avail_mb:>8}"

                # Disk via os.statvfs
                st = os.statvfs("/")
                total_gb = (st.f_blocks * st.f_frsize) / (1024 ** 3)
                free_gb  = (st.f_bavail * st.f_frsize) / (1024 ** 3)
                used_gb  = total_gb - free_gb
                pct = int((used_gb / total_gb) * 100) if total_gb else 0
                disk_str = f"Filesystem      Size  Used Avail Use%\n/               {total_gb:.0f}G  {used_gb:.1f}G  {free_gb:.1f}G  {pct}%"

                # Date from Python
                from datetime import datetime
                date = datetime.utcnow().strftime("%a %b %d %H:%M:%S UTC %Y")

                return f"REAL SYSTEM METRICS:\n\nRAM (MB):\n{ram_str}\n\nDISK:\n{disk_str}\n\nCURRENT TIME:\n{date}"
            except Exception as e:
                return f"Failed to fetch metrics: {e}"

        elif tool_name == "update_schedule":
            slot = args.get("slot", "morning").lower() # morning, afternoon, evening
            hour = args.get("hour")
            minute = args.get("minute")
            
            if slot not in ["morning", "afternoon", "evening"]:
                return f"Error: Invalid slot '{slot}'. Use 'morning', 'afternoon', or 'evening'."
            
            # 1. Update live scheduler
            from .scheduler import set_schedule_time
            set_schedule_time(slot, hour, minute)
            
            # 2. Persist to goku_settings.json (Safe Storage)
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                settings_path = os.path.join(base_dir, "goku_settings.json")
                
                settings = {}
                if os.path.exists(settings_path):
                    with open(settings_path, "r") as f:
                        settings = json.load(f)
                
                settings[f"{slot}_hour"] = hour
                settings[f"{slot}_minute"] = minute
                
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=4)
                    
                return f"✅ Done! I've updated your {slot} check-in to {hour:02d}:{minute:02d} UTC and saved it to my persistent memory."
            except Exception as e:
                return f"I've updated the live timer, but couldn't save to settings: {e}"

        elif tool_name == "clear_history":
            if not session_id: return "Error: No session ID provided."
            from .history import history
            history.clear_history(session_id)
            return "Successfully wiped current chat history. I have forgotten our current conversation."

        elif tool_name == "clear_memory":
            delete_protected = args.get("delete_protected", False)
            success = await memory.clear_all_memory(delete_protected=delete_protected)
            if success:
                msg = "Successfully wiped memory."
                if not delete_protected: msg += " I kept your protected memories safe."
                return msg
            else:
                return "Failed to clear long-term memory."

        elif tool_name == "manage_tasks":
            action = args.get("action")
            tasks_file = "goku_tasks.json"
            import json
            current_tasks = []
            if os.path.exists(tasks_file):
                try:
                    with open(tasks_file, "r") as f: current_tasks = json.load(f)
                except: current_tasks = []
            
            if action == "add": current_tasks.extend(args.get("tasks", []))
            elif action == "clear": current_tasks = []
            elif action == "list": pass
            elif action == "update":
                idx = args.get("index")
                new_tasks = args.get("tasks", [])
                if idx is not None and 0 <= idx < len(current_tasks) and new_tasks:
                    current_tasks[idx] = new_tasks[0]
            
            with open(tasks_file, "w") as f: json.dump(current_tasks, f)
            return f"Current Task List:\n" + "\n".join([f"{i}. {t}" for i, t in enumerate(current_tasks)]) if current_tasks else "Task list is empty."

        elif tool_name == "set_persona":
            name = args.get("name")
            if not session_id: return "Error: No session ID provided."
            from .personality_manager import personality_manager
            
            # Check if persona exists (if not CORE)
            if name != "CORE" and name not in personality_manager.list_personalities():
                return f"Error: Persona '{name}' not found. Please create it first by writing to ~/.goku/personalities/{name}.md"
            
            personality_manager.assign_personality(session_id, name)
            return f"Persona for this session updated to: {name}. I will adopt this identity in my next response."

        elif tool_name == "mcp_voice__list_voices":
            api_key = os.getenv("ELEVENLABS_API_KEY")
            if not api_key: return "Error: ElevenLabs API Key missing."
            try:
                headers = {"xi-api-key": api_key}
                resp = httpx.get("https://api.elevenlabs.io/v1/voices", headers=headers)
                if resp.status_code == 200:
                    voices = resp.json().get("voices", [])
                    return "\n".join([f"- {v['name']}: `{v['voice_id']}`" for v in voices[:10]])
                return f"Error fetching voices: {resp.text}"
            except Exception as e: return f"Error: {e}"

        elif tool_name == "mcp_voice__set_active_voice":
            voice_id = args.get("voice_id")
            # Update .env file (Safe write)
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                env_path = os.path.join(base_dir, ".env")
                if os.path.exists(env_path):
                    with open(env_path, "r") as f: lines = f.readlines()
                    new_lines = []
                    found = False
                    for line in lines:
                        if line.startswith("ELEVENLABS_VOICE_ID="):
                            new_lines.append(f"ELEVENLABS_VOICE_ID={voice_id}\n")
                            found = True
                        else: new_lines.append(line)
                    if not found: new_lines.append(f"ELEVENLABS_VOICE_ID={voice_id}\n")
                    with open(env_path, "w") as f: f.writelines(new_lines)
                return f"Successfully set active voice ID to `{voice_id}`. This will be used for all future voice notes."
            except Exception as e: return f"Error updating voice: {e}"

        elif tool_name == "voice_reply":
            text = args.get("text")
            return f"[VOICE_REPLY]: {text}"

        elif tool_name == "generate_music":
            prompt = args.get("prompt")
            ts = int(time.time())
            out_path = f"uploads/music_{ts}.mp3"
            os.makedirs("uploads", exist_ok=True)
            from .speech_service import generate_music as gen_music
            if await gen_music(prompt, out_path):
                return f"[MUSIC_REPLY]: {out_path}"
            return "Failed to generate music."

        return f"Unknown tool: {tool_name}"

tool_registry = ToolRegistry()
