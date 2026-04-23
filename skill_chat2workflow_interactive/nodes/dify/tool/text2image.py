from ..node import Node

class Text2Image(Node):
    def __init__(self, image_prompt: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)
        
        title = "Z-Image Text to Image"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "sawyer-shi/tongyi_aigc/tongyi_aigc",
            "provider_name": "sawyer-shi/tongyi_aigc/tongyi_aigc",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{
                "model":{
                    "type": "constant",
                    "value": "z-image-turbo"
                },
                "prompt_extend":{
                    "type": "constant",
                    "value": False
                },
                "seed":{
                    "type": "constant",
                    "value": None
                },
                "size":{
                    "type": "constant",
                    "value": "1024*1024"
                }
            },
            "tool_label": "Z-Image Text to Image",
            "tool_name": "z_image_text_2_image",
            "tool_node_version": "2",
            "tool_parameters":{
                "prompt":{
                    "type": "mixed",
                    "value": image_prompt
                }
            },
            "type": "tool"
        }
