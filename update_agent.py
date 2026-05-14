import re

with open("server/agent.py", "r") as f:
    code = f.read()

# 1. Update Imports
code = code.replace("from typing import List, Dict, Optional", "from typing import List, Dict, Optional, AsyncGenerator")

# 2. Update Signature
code = code.replace("async def chat(self, user_input: str, session_id: str = \"default\", source: str = \"cli\"):", "async def chat(self, user_input: str, session_id: str = \"default\", source: str = \"cli\") -> AsyncGenerator[str, None]:")

# 3. Update return None to return
code = re.sub(r'return None', r'return', code)

# 4. Fix KeyError and yield intermediate steps
old_manual_exec = """                # Execute Manual JSON Tool Calls (Spoofing Native Schema to prevent API errors)
                elif manual_tool_call:
                    function_name = manual_tool_call['name']
                    function_args = manual_tool_call['arguments']"""

new_manual_exec = """                # Execute Manual JSON Tool Calls (Spoofing Native Schema to prevent API errors)
                elif manual_tool_call:
                    function_name = manual_tool_call.get('name') or manual_tool_call.get('function', {}).get('name')
                    function_args = manual_tool_call.get('arguments') or manual_tool_call.get('function', {}).get('arguments')
                    
                    if not function_name:
                        yield f"⚠️ Failed to parse tool call format."
                        break
                        
                    yield f"⚙️ *Executing:* `{function_name}`..."
"""
code = code.replace(old_manual_exec, new_manual_exec)

old_native_exec = """                # Execute Native Tool Calls
                if tool_calls:
                    messages.append(message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        try:"""

new_native_exec = """                # Execute Native Tool Calls
                if tool_calls:
                    messages.append(message)
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        yield f"⚙️ *Executing:* `{function_name}`..."
                        try:"""
code = code.replace(old_native_exec, new_native_exec)

# 5. Fix Final Return
old_final_return = """            # 8. Save final response
            if clean_content:
                history.add_message(session_id, "assistant", clean_content)
            
            return clean_content"""

new_final_return = """            # 8. Save final response
            if clean_content:
                history.add_message(session_id, "assistant", clean_content)
            
            yield clean_content"""
code = code.replace(old_final_return, new_final_return)

# 6. Fix Exception return
old_exception_return = """            return f"Sorry, I encountered an error with the cloud brain: {e}\""""
new_exception_return = """            yield f"Sorry, I encountered an error with the cloud brain: {e}\""""
code = code.replace(old_exception_return, new_exception_return)

with open("server/agent.py", "w") as f:
    f.write(code)

print("agent.py updated")
