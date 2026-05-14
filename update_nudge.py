with open("server/agent.py", "r") as f:
    code = f.read()

old_check = """                    # Check if it tried to make a manual call but failed syntax
                    if "{" in message.content and ('"name"' in message.content or '"function"' in message.content):
                        yield "⚙️ *Correcting JSON syntax...*"
                        messages.append({
                            "role": "assistant",
                            "content": message.content
                        })
                        messages.append({
                            "role": "user",
                            "content": "System Error: Your JSON tool call failed to parse. Please ensure all strings have closing quotes and proper escaping."
                        })
                        continue"""

new_check = """                    # Check if it tried to make a manual call but failed syntax, or cut off abruptly
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
                        continue"""

code = code.replace(old_check, new_check)

with open("server/agent.py", "w") as f:
    f.write(code)
print("Updated agent.py with nudge logic")
