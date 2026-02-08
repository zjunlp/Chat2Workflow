import gradio as gr
import json
import yaml
import os
import re
import html
from datetime import datetime
from llm_api import OpenAIAgent
from pass_stage import convert_to_yaml

# Global variables
current_agent = None
chat_history = []
workflow_counter = 0

def load_system_prompt():
    """Load the system prompt from file"""
    prompt_path = "prompts/builder_prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    else:
        return "You are a helpful AI assistant for workflow generation."

def initialize_agent(model_name, temperature, max_tokens):
    """Initialize the LLM agent with specified parameters"""
    global current_agent
    try:
        system_prompt = load_system_prompt()
        current_agent = OpenAIAgent(
            model_name=model_name,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return f"✅ Agent initialized successfully with model: {model_name}"
    except Exception as e:
        return f"❌ Failed to initialize agent: {str(e)}"

def extract_workflow_json(text):
    """Extract workflow JSON from <workflow></workflow> tags"""
    pattern = r'<workflow>(.*?)</workflow>'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        workflow_str = match.group(1).strip()
        try:
            # Validate JSON
            workflow_json = json.loads(workflow_str)
            return workflow_str, True, None
        except json.JSONDecodeError as e:
            return workflow_str, False, f"Invalid JSON: {str(e)}"
    return None, False, "No <workflow> tags found"

def save_workflow_yaml(workflow_json_str, task_name=None):
    """Convert workflow JSON to YAML and save it"""
    global workflow_counter
    
    if task_name is None:
        workflow_counter += 1
        task_name = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Create output directory
    yaml_dir = "output/generated_workflows"
    os.makedirs(yaml_dir, exist_ok=True)
    
    # Use convert_to_yaml function
    try:
        success = convert_to_yaml(workflow_json_str, task_name, 1, yaml_dir)
        if success:
            yaml_path = os.path.join(yaml_dir, f"{task_name}_1.yaml")
            return True, yaml_path, None
        else:
            return False, None, "Conversion failed"
    except Exception as e:
        return False, None, f"Error during conversion: {str(e)}"

def chat_with_agent(user_message, history):
    """Handle chat interaction with the agent using streaming"""
    global current_agent, chat_history
    
    if current_agent is None:
        # Return error message in new format
        error_msg = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": "⚠️ Please initialize the agent first by clicking 'Initialize Agent' button."}
        ]
        yield history + error_msg, "", None, None
        return
    
    try:
        # Prepare history for the agent (convert from new format to tuple format)
        agent_history = []
        for i in range(0, len(history), 2):
            if i + 1 < len(history):
                user_msg = history[i].get("content", "")
                assistant_msg = history[i + 1].get("content", "")
                if user_msg and assistant_msg:
                    # Unescape HTML entities when sending to agent
                    agent_history.append((user_msg, html.unescape(assistant_msg)))
        
        # Add user message to history
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": ""})
        
        # Generate response with streaming
        full_reasoning = ""
        full_response = ""
        
        for reasoning_chunk, content_chunk in current_agent.generate_stream(query=user_message, history=agent_history):
            # Accumulate reasoning content
            if reasoning_chunk:
                full_reasoning += reasoning_chunk
            
            # Accumulate regular content
            if content_chunk:
                full_response += content_chunk
            
            # Build display text with reasoning (if available) and response
            # Note: Only escape the response content, keep reasoning as-is for better readability
            display_text = ""
            if full_reasoning:
                # Don't escape reasoning content - it's displayed in code block which handles special chars
                display_text += f"🧠 **Think:**\n```\n{full_reasoning}\n```\n\n---\n\n"
            # Escape only the response content to prevent HTML injection
            if full_response:
                display_text += html.escape(full_response)
            else:
                display_text = display_text  # Keep only reasoning if no response yet
            
            # Update the last assistant message
            history[-1]["content"] = display_text
            yield history, "", "⏳ Generating response...", None
        
        print("=== Reasoning Content ===")
        print(full_reasoning if full_reasoning else "No reasoning content")
        print("\n=== Response Content ===")
        print(full_response)
        
        # Try to extract and convert workflow (use original unescaped response)
        workflow_json, is_valid, error_msg = extract_workflow_json(full_response)
        
        workflow_info = ""
        yaml_path = None
        
        if workflow_json:
            if is_valid:
                # Try to convert to YAML
                success, yaml_file, conv_error = save_workflow_yaml(workflow_json)
                if success:
                    workflow_info = f"✅ Workflow extracted and converted successfully!\n📁 Saved to: {yaml_file}"
                    yaml_path = yaml_file
                else:
                    workflow_info = f"⚠️ Workflow JSON extracted but conversion failed: {conv_error}"
            else:
                workflow_info = f"⚠️ Workflow found but JSON is invalid: {error_msg}"
        else:
            workflow_info = "ℹ️ No workflow detected in this response."
        
        yield history, "", workflow_info, yaml_path
        
    except Exception as e:
        error_response = f"❌ Error: {str(e)}"
        history[-1]["content"] = error_response
        yield history, "", "Error occurred during processing", None

def clear_chat():
    """Clear chat history"""
    global chat_history
    chat_history = []
    return [], "", "Chat history cleared"

def load_yaml_content(yaml_path):
    """Load and display YAML file content"""
    if yaml_path and os.path.exists(yaml_path):
        with open(yaml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    return "No YAML file available"

# Create Gradio interface
with gr.Blocks(title="Chat2Workflow - Interactive Workflow Generator") as demo:
    gr.Markdown("# 🤖 Chat2Workflow - Interactive Workflow Generator")
    
    # Usage instructions at the top with two-column layout
    with gr.Accordion("📖 Usage Instructions & Tips", open=True):
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("""
                ### 📖 How to Use:
                
                1. **Configure Agent**: Set your preferred model name, temperature, and max tokens in the left panel
                
                2. **Initialize**: Click "🚀 Initialize Agent" button to load the system prompt and create the agent
                
                3. **Chat**: Type your workflow requirements in the message box and click "📤 Send"
                
                4. **Auto-Extract**: The system automatically detects `<workflow>` tags in LLM responses
                
                5. **Auto-Convert**: Valid workflow JSON is automatically converted to YAML format
                
                6. **Preview**: View the generated YAML in the preview section at the bottom
                """)
            
            with gr.Column(scale=1):
                gr.Markdown("""
                ### 💡 Tips & Features:
                
                📁 **Auto-Save**: Generated YAML files are automatically saved in `output/generated_workflows/` directory
                
                💬 **Multi-Turn**: You can have multi-turn conversations to refine and improve your workflow
                
                🗑️ **Clear History**: Clear chat history anytime to start a fresh conversation
                
                🔄 **Refresh**: Use "Refresh YAML Preview" button to reload the YAML content if needed
                            
                ⬇️ **Download**: You can download the YAML file in one click.
                """)
    
    gr.Markdown("---")
    
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### ⚙️ Agent Configuration")
            
            model_name = gr.Textbox(
                label="Model Name",
                value="deepseek-chat",
                placeholder="e.g., gpt-4o, deepseek-chat",
                info="Enter the model name to use"
            )
            
            temperature = gr.Slider(
                minimum=0.0,
                maximum=2.0,
                value=0.7,
                step=0.1,
                label="Temperature",
                info="Controls randomness in responses"
            )
            
            max_tokens = gr.Slider(
                minimum=512,
                maximum=16384,
                value=4096,
                step=512,
                label="Max Tokens",
                info="Maximum length of generated response"
            )
            
            init_btn = gr.Button("🚀 Initialize Agent", variant="primary")
            init_status = gr.Textbox(label="Initialization Status", interactive=False)
            
            gr.Markdown("---")
            gr.Markdown("### 📊 Workflow Status")
            workflow_status = gr.Textbox(
                label="Workflow Extraction Status",
                interactive=False,
                lines=3
            )
            
            yaml_file_path = gr.Textbox(
                label="Generated YAML Path",
                interactive=False,
                visible=False
            )
        
        with gr.Column(scale=2):
            gr.Markdown("### 💬 Chat Interface")
            
            chatbot = gr.Chatbot(
                label="Conversation",
                height=500
            )
            
            with gr.Row():
                user_input = gr.Textbox(
                    label="Your Message",
                    placeholder="Type your message here... (e.g., 'Create a workflow that processes user input and generates a summary')",
                    lines=3,
                    scale=4
                )
                
            with gr.Row():
                send_btn = gr.Button("📤 Send", variant="primary", scale=1)
                clear_btn = gr.Button("🗑️ Clear Chat", scale=1)
    
    with gr.Row():
        with gr.Column():
            gr.Markdown("### 📄 Generated YAML Preview")
            yaml_preview = gr.Code(
                label="YAML Content",
                language="yaml",
                lines=20,
                interactive=False
            )
            refresh_yaml_btn = gr.Button("🔄 Refresh YAML Preview")
    
    # Event handlers
    init_btn.click(
        fn=initialize_agent,
        inputs=[model_name, temperature, max_tokens],
        outputs=[init_status]
    )
    
    send_btn.click(
        fn=chat_with_agent,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input, workflow_status, yaml_file_path]
    ).then(
        fn=load_yaml_content,
        inputs=[yaml_file_path],
        outputs=[yaml_preview]
    )
    
    user_input.submit(
        fn=chat_with_agent,
        inputs=[user_input, chatbot],
        outputs=[chatbot, user_input, workflow_status, yaml_file_path]
    ).then(
        fn=load_yaml_content,
        inputs=[yaml_file_path],
        outputs=[yaml_preview]
    )
    
    clear_btn.click(
        fn=clear_chat,
        inputs=[],
        outputs=[chatbot, user_input, workflow_status]
    )
    
    refresh_yaml_btn.click(
        fn=load_yaml_content,
        inputs=[yaml_file_path],
        outputs=[yaml_preview]
    )

if __name__ == "__main__":
    demo.launch(
        server_name="127.0.0.1",
        share=False,
        show_error=True
    )
