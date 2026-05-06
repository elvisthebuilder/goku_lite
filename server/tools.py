import os
import httpx
import logging
import subprocess
from .memory import memory

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the web for real-time information.",
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
                            "text": {"type": "string", "description": "The information to remember."}
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
                    "name": "google_search",
                    "description": "Use Google Search (via Gemini) to find real-time facts and verify information.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The specific fact or query to verify."}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "parse_document",
                    "description": "Parse a PDF, DOCX, or Excel file into clean Markdown text.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Relative path to the document file."}
                        },
                        "required": ["path"]
                    }
                }
            }
        ]

    async def execute(self, tool_name, args):
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        
        if tool_name == "web_search":
            query = args.get("query")
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key: return "Error: TAVILY_API_KEY missing."
            async with httpx.AsyncClient() as client:
                resp = await client.post("https://api.tavily.com/search", json={"api_key": api_key, "query": query})
                results = resp.json().get("results", [])
                return "\n".join([f"- {r['title']}: {r['content'][:300]} ({r['url']})" for r in results[:3]])

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
            await memory.add_memory(text)
            return f"Saved to memory: {text}"

        elif tool_name == "memory_query":
            query = args.get("query")
            results = await memory.search_memory(query)
            if not results: return "No relevant memories found."
            return "\n".join([f"- {r['text']} (at {time.ctime(r['timestamp'])})" for r in results])

        elif tool_name == "get_system_status":
            from .config import config
            db_type = "Remote (SQL)" if config.DATABASE_URL else "Local (SQLite)"
            mem_type = "Remote (Qdrant Cloud)" if config.QDRANT_API_KEY else "Disabled"
            return f"🐉 Goku Lite Status:\n- Model: {config.GOKU_MODEL}\n- Database: {db_type}\n- Memory: {mem_type}\n- Mode: Cloud-Native"

        elif tool_name == "parse_document":
            path = args.get("path")
            try:
                from markitdown import MarkItDown
                md = MarkItDown()
                result = md.convert(path)
                return result.text_content
            except Exception as e:
                return f"Failed to parse document: {e}"

        elif tool_name == "google_search":
            query = args.get("query")
            from .config import config
            if not config.GEMINI_API_KEY:
                return "Error: GEMINI_API_KEY missing. Google Search requires a Gemini key."
            try:
                import litellm
                # Call Gemini with grounding/search enabled
                resp = await litellm.acompletion(
                    model="gemini/gemini-2.5-flash",
                    messages=[{"role": "user", "content": f"Search Google for: {query}"}],
                    api_key=config.GEMINI_API_KEY,
                    tools=[{"type": "google_search_retrieval", "google_search_retrieval": {}}]
                )
                return resp.choices[0].message.content
            except Exception as e:
                return f"Google Search failed: {e}"

        return f"Unknown tool: {tool_name}"

import time # For ctime
tool_registry = ToolRegistry()
