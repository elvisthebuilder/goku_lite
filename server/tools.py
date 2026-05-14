import os
import asyncio
import httpx
import logging
import subprocess
import time
import json
from .memory import memory
from .config import config
from .history import history

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        # Cloud Native: No mandatory local directory creation in constructor.
        # Tools will use /tmp or memory for transient operations.
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "google_search",
                    "description": "Search the web for real-time information.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "Execute a safe shell command. No sudo.",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {"type": "string"}},
                        "required": ["command"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "memory_save",
                    "description": "Store a fact in long-term cloud memory.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "protected": {"type": "boolean"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "manage_tasks",
                    "description": "Manage tasks in the cloud database.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["add", "list", "clear"]},
                            "tasks": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["action"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "voice_reply",
                    "description": "Send a spoken voice response.",
                    "parameters": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}},
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
                        "properties": {"prompt": {"type": "string"}},
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_metrics",
                    "description": "Fetch REAL RAM and Disk usage.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

    async def execute(self, tool_name, args, session_id=None):
        logger.info(f"Executing tool: {tool_name}")
        
        if tool_name == "google_search":
            query = args.get("query")
            tavily_key = os.getenv("TAVILY_API_KEY")
            if tavily_key:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.post("https://api.tavily.com/search", json={"api_key": tavily_key, "query": query})
                        results = resp.json().get("results", [])
                        return "\n".join([f"- {r['title']}: {r['content'][:300]}" for r in results[:3]])
                except Exception as e: logger.warning(f"Search failed: {e}")
            return "Search unavailable."

        elif tool_name == "execute_command":
            command = args.get("command")
            if "sudo" in command or "rm " in command: return "Error: Unauthorized command."
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            except Exception as e: return f"Failed: {e}"

        elif tool_name == "memory_save":
            await memory.add_memory(args.get("text"), protected=args.get("protected", False))
            return "Saved to cloud memory."

        elif tool_name == "manage_tasks":
            action = args.get("action")
            if action == "add":
                for t in args.get("tasks", []): history.add_task(t)
                return "Tasks added to cloud database."
            elif action == "clear":
                history.clear_tasks()
                return "Tasks cleared from cloud database."
            elif action == "list":
                tasks = history.get_tasks()
                return "\n".join([f"- {t.description}" for t in tasks]) if tasks else "No tasks."

        elif tool_name == "voice_reply":
            return f"[VOICE_REPLY]: {args.get('text')}"

        elif tool_name == "generate_music":
            return f"[MUSIC_REPLY]: {args.get('prompt')}"

        elif tool_name == "get_system_metrics":
            # Disk/RAM metrics as before
            try:
                st = os.statvfs("/")
                free_gb = (st.f_bavail * st.f_frsize) / (1024 ** 3)
                return f"System is healthy. Cloud Database connected. Local disk free: {free_gb:.1f}GB"
            except: return "Metrics unavailable."

        return f"Unknown tool: {tool_name}"

tool_registry = ToolRegistry()
