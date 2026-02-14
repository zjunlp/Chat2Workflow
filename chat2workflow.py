import chainlit as cl
from chainlit.input_widget import TextInput, Slider
import json
import os
import re
import asyncio
from datetime import datetime

# 导入你原有的核心逻辑
from llm_api import OpenAIAgent
from pass_stage import convert_to_yaml

# --- 全局状态缓存 ---
# 仅保留 settings，移除 chat_history，以实现每次新建对话都是全新的上下文
GLOBAL_STATE = {
    "settings": {
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 8192
    }
}

# --- 核心数据处理函数 ---

def load_system_prompt():
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

def save_workflow_yaml(workflow_json_str, task_name=None):
    if task_name is None:
        task_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    yaml_dir = "output/generated_workflows"
    os.makedirs(yaml_dir, exist_ok=True)
    
    try:
        success = convert_to_yaml(workflow_json_str, task_name, 1, yaml_dir)
        if success:
            yaml_path = os.path.join(yaml_dir, f"{task_name}_1.yaml")
            return True, yaml_path, task_name
        return False, None, "Conversion failed"
    except Exception as e:
        return False, None, f"Error during conversion: {str(e)}"


# --- Chainlit UI 交互逻辑 ---

@cl.on_chat_start
async def start():
    """初始化页面，恢复配置参数，但重置历史上下文"""
    saved_settings = GLOBAL_STATE["settings"]
    
    # 1. 设置并恢复侧边栏参数配置
    settings = cl.ChatSettings(
        [
            TextInput(id="model_name", label="Model Name", initial=saved_settings["model_name"]),
            Slider(id="temperature", label="Temperature", initial=saved_settings["temperature"], min=0.0, max=2.0, step=0.1),
            Slider(id="max_tokens", label="Max Tokens", initial=saved_settings["max_tokens"], min=512, max=16384, step=512)
        ]
    )
    await settings.send()
    
    # 2. 初始化 Agent
    try:
        system_prompt = load_system_prompt()
        agent = OpenAIAgent(
            model_name=saved_settings["model_name"],
            system_prompt=system_prompt,
            temperature=saved_settings["temperature"],
            max_tokens=saved_settings["max_tokens"]
        )
        cl.user_session.set("agent", agent)
    except Exception as e:
        await cl.Message(content=f"❌ Agent 初始化失败: {str(e)}").send()
    
    # 3. 初始化全新的历史对话记录（不再从 GLOBAL_STATE 获取）
    cl.user_session.set("chat_history", [])
    
    # 4. 发送欢迎语及状态提示
    welcome_msg = f"👋 **欢迎使用 Chat2Workflow！**\n\n\nmodel: `{saved_settings['model_name']}`, temperature: `{saved_settings['temperature']}`, max_tokens: `{saved_settings['max_tokens']}`"
        
    await cl.Message(content=welcome_msg).send()

@cl.on_settings_update
async def setup_agent(settings):
    """当用户修改设置时，更新全局状态并重新加载 Agent"""
    try:
        # 同步更新到全局状态
        GLOBAL_STATE["settings"]["model_name"] = settings["model_name"]
        GLOBAL_STATE["settings"]["temperature"] = settings["temperature"]
        GLOBAL_STATE["settings"]["max_tokens"] = settings["max_tokens"]
        
        system_prompt = load_system_prompt()
        agent = OpenAIAgent(
            model_name=settings["model_name"],
            system_prompt=system_prompt,
            temperature=settings["temperature"],
            max_tokens=settings["max_tokens"]
        )
        cl.user_session.set("agent", agent)
        
        # 明确提示当前更新的模型名称
        await cl.Message(content=f"✅ 配置已更新！\n\n\nmodel: `{settings['model_name']}`, temperature: `{settings['temperature']}`, max_tokens: `{settings['max_tokens']}`").send()
    except Exception as e:
        await cl.Message(content=f"❌ 更新失败: {str(e)}").send()

@cl.on_message
async def main(message: cl.Message):
    """处理用户消息核心逻辑"""
    agent = cl.user_session.get("agent")
    chat_history = cl.user_session.get("chat_history")
    
    if not agent:
        await cl.Message(content="⚠️ Agent 未就绪，请刷新页面。").send()
        return

    msg = cl.Message(content="")
    await msg.send()
    
    full_reasoning = ""
    full_response = ""
    
    has_reasoning = False
    reasoning_closed = False

    try:
        # 流式获取 Agent 输出
        for reasoning_chunk, content_chunk in agent.generate_stream(query=message.content, history=chat_history):
            
            # 处理思考过程：使用 Markdown 的折叠标签 (open 属性代表默认展开)
            if reasoning_chunk:
                if not has_reasoning:
                    await msg.stream_token("🧠 思考过程\n\n> ")
                    has_reasoning = True
                
                # 为了视觉美观，思考内容加上引用块的格式
                clean_chunk = reasoning_chunk.replace('\n', '\n> ')
                full_reasoning += reasoning_chunk
                await msg.stream_token(clean_chunk)
            
            # 处理最终回复内容
            if content_chunk:
                # 如果之前有思考过程，且尚未闭合标签，则在此处闭合
                if has_reasoning and not reasoning_closed:
                    await msg.stream_token("\n\n---\n\n")
                    reasoning_closed = True
                
                full_response += content_chunk
                await msg.stream_token(content_chunk)
            
            await asyncio.sleep(0.01)
            
    except Exception as e:
        await cl.Message(content=f"❌ 生成过程中出错: {str(e)}").send()
        return

    # 容错收尾：如果模型只有思考没输出正文，确保标签闭合
    if has_reasoning and not reasoning_closed:
        await msg.stream_token("\n</details>\n\n")
        
    await msg.update()

    # --- 更新对话历史（仅保存在当前 session，不再同步到全局状态） ---
    chat_history.append((message.content, full_response))
    cl.user_session.set("chat_history", chat_history)

    # --- 提取 JSON 并尝试转换为 YAML ---
    workflow_json, is_valid, error_msg = extract_workflow_json(full_response)
    
    if workflow_json and is_valid:
        success, yaml_path, task_name = save_workflow_yaml(workflow_json)
        
        if success and yaml_path and os.path.exists(yaml_path):
            with open(yaml_path, 'r', encoding='utf-8') as f:
                yaml_content = f.read()
            
            yaml_preview = cl.Text(
                name="YAML 预览", 
                content=yaml_content, 
                language="yaml", 
                display="side"
            )
            yaml_download = cl.File(
                name=f"{task_name}.yaml",
                content=yaml_content.encode('utf-8'),
                display="inline"
            )
            
            await cl.Message(
                content=f"🎉 **工作流 YAML 已生成！**",
                elements=[yaml_preview, yaml_download]
            ).send()
        else:
            await cl.Message(content=f"⚠️ YAML 转换失败。错误: {error_msg}").send()
            
    elif workflow_json and not is_valid:
        await cl.Message(content=f"❌ 发现工作流标签但 JSON 格式错误: `{error_msg}`").send()