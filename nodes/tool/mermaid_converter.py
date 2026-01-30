from ..node import Node

class MermaidConverter(Node):
    def __init__(self, mermaid_code: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Mermaid Converter"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "hjlarry/mermaid_converter/mermaid_converter",
            "provider_name": "hjlarry/mermaid_converter/mermaid_converter",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{
                "output_format":{
                    "type": "constant",
                    "value": "png"
                },
                "theme":{
                    "type": "constant",
                    "value": "default"
                }
            },
            "tool_label": "Mermaid转换器",
            "tool_name": "mermaid_converter",
            "tool_node_version": "2",
            "tool_parameters":{
                "mermaid_code":{
                    "type": "mixed",
                    "value": mermaid_code
                }
            },
            "type": "tool"
        }
