import chainlit as cl
from chainlit.input_widget import TextInput, Slider, Select
import json
import os
import re
import asyncio
from datetime import datetime

from llm_api import OpenAIAgent
from converter import convert_to_dify, convert_to_coze

GLOBAL_STATE = {
    "settings": {
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 8192,
        "workflow_type": "dify"
    }
}

def load_system_prompt(workflow_type="dify"):
    if workflow_type == "coze":
        prompt_path = "prompts/builder_prompt_coze.txt"
    else:
        prompt_path = "prompts/builder_prompt.txt"
    
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return "You are a helpful AI assistant for workflow generation."

def extract_workflow_json(text):
    pattern = r'<workflow>(.*?)</workflow>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        workflow_str = match.group(1).strip()
        try:
            json.loads(workflow_str)
            return workflow_str, True, None
        except json.JSONDecodeError as e:
            return workflow_str, False, f"Invalid JSON: {str(e)}"
    return None, False, "No <workflow> tags found"

def save_workflow_yaml(workflow_json_str, workflow_type="dify", task_name=None):
    
    yaml_dir = "output/generated_workflows"
    os.makedirs(yaml_dir, exist_ok=True)
    
    try:
        data = json.loads(workflow_json_str)
        
        if workflow_type == "coze":
            task_name = "test"
            manifest_path = "nodes/coze/MANIFEST.yml"
            success = convert_to_coze(data, task_name, yaml_dir, manifest_path)
            if success:
                zip_path = os.path.join(yaml_dir, f"Workflow-{task_name}-draft.zip")
                return True, zip_path, task_name
        else:
            if task_name is None:
                task_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            success = convert_to_dify(data, task_name, yaml_dir)
            if success:
                yaml_path = os.path.join(yaml_dir, f"{task_name}.yaml")
                return True, yaml_path, task_name
        
        return False, None, "Conversion failed"
    except Exception as e:
        return False, None, f"Error during conversion: {str(e)}"



@cl.on_chat_start
async def start():
    """Initialize page, restore configuration parameters, but reset history context"""
    saved_settings = GLOBAL_STATE["settings"]
    
    # 1. Set and restore sidebar parameter configuration
    settings = cl.ChatSettings(
        [
            Select(id="workflow_type", label="Workflow Type", 
                   values=["dify", "coze"], initial_value=saved_settings["workflow_type"]),
            TextInput(id="model_name", label="Model Name", initial=saved_settings["model_name"]),
            Slider(id="temperature", label="Temperature", initial=saved_settings["temperature"], min=0.0, max=2.0, step=0.1),
            Slider(id="max_tokens", label="Max Tokens", initial=saved_settings["max_tokens"], min=512, max=16384, step=512)
        ]
    )
    await settings.send()
    
    # 2. Initialize Agent
    try:
        system_prompt = load_system_prompt(saved_settings["workflow_type"])
        agent = OpenAIAgent(
            model_name=saved_settings["model_name"],
            system_prompt=system_prompt,
            temperature=saved_settings["temperature"],
            max_tokens=saved_settings["max_tokens"]
        )
        cl.user_session.set("agent", agent)
    except Exception as e:
        await cl.Message(content=f"❌ Agent initialization failed: {str(e)}").send()
    
    # 3. Initialize fresh chat history
    cl.user_session.set("chat_history", [])
    
    # 4. Send welcome message and status prompt
    welcome_msg = f"👋 **Welcome to Chat2Workflow!**\n\nworkflow type: `{saved_settings['workflow_type']}`\nmodel: `{saved_settings['model_name']}`, temperature: `{saved_settings['temperature']}`, max_tokens: `{saved_settings['max_tokens']}`\n**You can reset them in Settings!**"
        
    await cl.Message(content=welcome_msg).send()

@cl.on_settings_update
async def setup_agent(settings):
    """Update global state and reload Agent when user modifies settings"""
    try:
        GLOBAL_STATE["settings"]["workflow_type"] = settings["workflow_type"]
        GLOBAL_STATE["settings"]["model_name"] = settings["model_name"]
        GLOBAL_STATE["settings"]["temperature"] = settings["temperature"]
        GLOBAL_STATE["settings"]["max_tokens"] = settings["max_tokens"]
        
        system_prompt = load_system_prompt(settings["workflow_type"])
        agent = OpenAIAgent(
            model_name=settings["model_name"],
            system_prompt=system_prompt,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"]
        )
        cl.user_session.set("agent", agent)
        
        await cl.Message(content=f"✅ Configuration updated!\n\nworkflow type: `{settings['workflow_type']}`\nmodel: `{settings['model_name']}`, temperature: `{settings['temperature']}`, max_tokens: `{settings['max_tokens']}`").send()
    except Exception as e:
        await cl.Message(content=f"❌ Update failed: {str(e)}").send()

@cl.on_message
async def main(message: cl.Message):
    """Core logic for processing user messages"""
    agent = cl.user_session.get("agent")
    chat_history = cl.user_session.get("chat_history")
    
    if not agent:
        await cl.Message(content="⚠️ Agent not ready, please refresh the page.").send()
        return

    msg = cl.Message(content="")
    await msg.send()
    
    full_reasoning = ""
    full_response = ""
    
    has_reasoning = False
    reasoning_closed = False

    try:
        for reasoning_chunk, content_chunk in agent.generate_stream(query=message.content, history=chat_history):
            
            if reasoning_chunk:
                if not has_reasoning:
                    await msg.stream_token("🧠 Reasoning Process\n\n> ")
                    has_reasoning = True
                
                clean_chunk = reasoning_chunk.replace('\n', '\n> ')
                full_reasoning += reasoning_chunk
                await msg.stream_token(clean_chunk)
            
            if content_chunk:
                if has_reasoning and not reasoning_closed:
                    await msg.stream_token("\n\n---\n\n")
                    reasoning_closed = True
                
                full_response += content_chunk
                await msg.stream_token(content_chunk)
            
            await asyncio.sleep(0.01)
            
    except Exception as e:
        await cl.Message(content=f"❌ Error during generation: {str(e)}").send()
        return

    if has_reasoning and not reasoning_closed:
        await msg.stream_token("\n</details>\n\n")
        
    await msg.update()

    chat_history.append((message.content, full_response))
    cl.user_session.set("chat_history", chat_history)

    workflow_json, is_valid, error_msg = extract_workflow_json(full_response)
    
    if workflow_json and is_valid:
        workflow_type = GLOBAL_STATE["settings"]["workflow_type"]
        success, output_path, task_name = save_workflow_yaml(workflow_json, workflow_type)
        
        if success and output_path and os.path.exists(output_path):
            with open(output_path, 'rb') as f:
                file_content = f.read()
            
            if workflow_type == "coze":
                file_download = cl.File(
                    name=f"Workflow-{task_name}-draft.zip",
                    content=file_content,
                    display="inline"
                )
                await cl.Message(
                    content=f"🎉 **Coze Workflow ZIP generated successfully!**",
                    elements=[file_download]
                ).send()
            else:
                yaml_content = file_content.decode('utf-8')
                yaml_preview = cl.Text(
                    name="YAML Preview", 
                    content=yaml_content, 
                    language="yaml", 
                    display="side"
                )
                yaml_download = cl.File(
                    name=f"{task_name}.yaml",
                    content=file_content,
                    display="inline"
                )
                await cl.Message(
                    content=f"🎉 **Dify Workflow YAML generated successfully!**",
                    elements=[yaml_preview, yaml_download]
                ).send()
        else:
            await cl.Message(content=f"⚠️ Conversion failed. Error: {error_msg}").send()
            
    elif workflow_json and not is_valid:
        await cl.Message(content=f"❌ Workflow tags found but JSON format is invalid: `{error_msg}`").send()