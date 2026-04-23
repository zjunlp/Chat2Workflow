from ..node import Node

class MarkdownExporter(Node):
    def __init__(self, target_type: str ,md_text: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        tool_name = "md_to_" + target_type

        if target_type == "png":
            tool_label = f"Markdown 转 {target_type} 图片"
        else:
            tool_label = f"Markdown 转 {target_type} 文件"

        title = tool_name

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "bowenliang123/md_exporter/md_exporter",
            "provider_name": "bowenliang123/md_exporter/md_exporter",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{},
            "tool_label": tool_label,
            "tool_name": tool_name,
            "tool_node_version": "2",
            "tool_parameters":{
                "md_text":{
                    "type": "mixed",
                    "value": md_text
                }
            },
            "type": "tool"
        }
