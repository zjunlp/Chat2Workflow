from ..node import Node

class TTS(Node):
    def __init__(self, text: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Text to Speech"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "audio",
            "provider_name": "audio",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{
                "model":{
                    "type": "constant",
                    "value": "langgenius/openai/openai#gpt-4o-mini-tts"
                },
                "size":{
                    "type": "mixed",
                    "value": None
                }
            },
            "tool_label": "Text To Speech",
            "tool_name": "tts",
            "tool_node_version": "2",
            "tool_parameters":{
                "text":{
                    "type": "mixed",
                    "value": text
                }
            },
            "type": "tool"
        }
