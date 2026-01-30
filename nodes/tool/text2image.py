from ..node import Node

class Text2Image(Node):
    def __init__(self, image_prompt: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)
        
        title = "Text to Image"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "wwwzhouhui/qwen_text2image/modelscope",
            "provider_name": "wwwzhouhui/qwen_text2image/modelscope",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{
                "model":{
                    "type": "constant",
                    "value": "Qwen/Qwen-Image"
                },
                "size":{
                    "type": "mixed",
                    "value": None
                }
            },
            "tool_label": "文生图",
            "tool_name": "text2image",
            "tool_node_version": "2",
            "tool_parameters":{
                "prompt":{
                    "type": "mixed",
                    "value": image_prompt
                }
            },
            "type": "tool"
        }
