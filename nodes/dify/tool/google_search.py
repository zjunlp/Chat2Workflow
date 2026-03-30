from ..node import Node

class GoogleSearch(Node):
    def __init__(self, query: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Google Search"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "langgenius/google/google",
            "provider_name": "langgenius/google/google",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{
                "as_agent_tool":{
                    "type": "constant",
                    "value": False
                }
            },
            "tool_label": "谷歌搜索",
            "tool_name": "google_search",
            "tool_node_version": "2",
            "tool_parameters":{
                "query":{
                    "type": "mixed",
                    "value": query
                }
            },
            "type": "tool"
        }
