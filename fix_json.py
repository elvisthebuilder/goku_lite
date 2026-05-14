import re

with open("server/agent.py", "r") as f:
    code = f.read()

old_fallback = """                manual_tool_call = None
                
                # Fallback: Catch Ollama models outputting JSON as raw text
                if not tool_calls and message.content:
                    import re
                    json_match = re.search(r'\{.*"name".*".*".*"arguments".*\{.*\}.*\}', message.content, re.DOTALL)
                    if json_match:
                        try:
                            import json
                            manual_tool_call = json.loads(json_match.group())
                            name = manual_tool_call.get('name') or manual_tool_call.get('function', {}).get('name', 'Unknown')
                            logger.info(f"Intercepted manual JSON tool call: {name}")
                        except:
                            pass
                
                if not tool_calls and not manual_tool_call:"""

new_fallback = """                manual_tool_calls = []
                
                # Fallback: Catch Ollama models outputting multiple JSON tool calls as raw text
                if not tool_calls and message.content:
                    import json
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
                
                if not tool_calls and not manual_tool_calls:"""

code = code.replace(old_fallback, new_fallback)

old_exec = """                # Execute Manual JSON Tool Calls (Spoofing Native Schema to prevent API errors)
                elif manual_tool_call:
                    function_name = manual_tool_call.get('name') or manual_tool_call.get('function', {}).get('name')
                    function_args = manual_tool_call.get('arguments') or manual_tool_call.get('function', {}).get('arguments')
                    
                    if not function_name:
                        yield f"⚠️ Failed to parse tool call format."
                        break
                        
                    yield f"⚙️ *Executing:* `{function_name}`..."

                    yield f"⚙️ *Executing:* `{function_name}`..."
                    try:
                        tool_output = await tool_registry.execute(function_name, function_args, session_id=session_id)
                    except Exception as e:
                        tool_output = f"Error executing {function_name}: {e}"
                        
                    spoofed_id = "call_manual123"
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": spoofed_id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": json.dumps(function_args)
                                }
                            }
                        ]
                    })
                    messages.append({
                        "tool_call_id": spoofed_id,
                        "role": "tool",
                        "name": function_name,
                        "content": str(tool_output),
                    })"""

new_exec = """                # Execute Manual JSON Tool Calls (Spoofing Native Schema to prevent API errors)
                elif manual_tool_calls:
                    import uuid
                    spoofed_tool_calls = []
                    
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
                            
                        spoofed_id = f"call_{uuid.uuid4().hex[:8]}"
                        spoofed_tool_calls.append({
                            "id": spoofed_id,
                            "type": "function",
                            "function": {
                                "name": function_name,
                                "arguments": json.dumps(function_args)
                            }
                        })
                        
                        messages.append({
                            "tool_call_id": spoofed_id,
                            "role": "tool",
                            "name": function_name,
                            "content": str(tool_output),
                        })
                        
                    # Prepend the spoofed assistant message right before the tool results
                    messages.insert(-len(manual_tool_calls), {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": spoofed_tool_calls
                    })"""

code = code.replace(old_exec, new_exec)

with open("server/agent.py", "w") as f:
    f.write(code)
print("Updated agent.py")
