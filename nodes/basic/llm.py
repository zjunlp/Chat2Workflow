from ..node import Node
import uuid

class LLM(Node):
    def __init__(self, prompt_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "LLM"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "context":{
                "enabled": False,
                "variable_selector": []
            },
            "model":{
                "completion_params": {
                    "temperature": 0.7,
                    "max_tokens": 32768
                },
                "mode": "chat",
                "name": "qwen3-vl-plus",
                "provider": "langgenius/tongyi/tongyi"
            },
            "prompt_template": [],
            "selected": False,
            "title": title,
            "type": "llm",
            "vision": {"enabled": False}
        }
        
        for prompt in prompt_list:
            dialog_template = {
                "role": prompt[0],
                "text": prompt[1]
            }
            self.data["prompt_template"].append(dialog_template)
