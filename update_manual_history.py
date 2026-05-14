import re

with open("server/agent.py", "r") as f:
    code = f.read()

old_exec = """                # Execute Manual JSON Tool Calls (Spoofing Native Schema to prevent API errors)
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

new_exec = """                # Execute Manual JSON Tool Calls (Text-Based History for Ollama Compatibility)
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
                            
                        combined_tool_output += f"\\n\\n--- Result of {function_name} ---\\n{tool_output}"
                        
                    # Feed the results back as a 'user' message so Ollama can read it natively
                    messages.append({
                        "role": "user",
                        "content": f"System Tool Execution Results:{combined_tool_output}"
                    })"""

code = code.replace(old_exec, new_exec)

with open("server/agent.py", "w") as f:
    f.write(code)
print("Updated agent.py with text-based history for Ollama")
