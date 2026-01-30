from ..node import Node

class ParameterExtractor(Node):
    def __init__(self, query: list, param_list: list, x: int, y: int, count: int = 1, instruction: str = ""):
        super().__init__(x,y)

        title = "Parameter Extractor"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "instruction": instruction,
            "model": {
                "completion_params": {
                    "temperature": 0.7,
                    "max_tokens": 32768
                },
                "mode": "chat",
                "name": "qwen3-vl-plus",
                "provider": "langgenius/tongyi/tongyi"
            },
            "parameters": [],
            "query": [query[1],query[0]],
            "reasoning_mode": "prompt",
            "selected": False,
            "title": title,
            "type": "parameter-extractor",
            "vision": {"enabled": False}
        }

        for param in param_list:
            param_template = {
                "description": param[0],
                "name": param[1],
                "required": True,
                "type": param[2]
            }
            self.data["parameters"].append(param_template)
