from ..node import Node

class GoogleSearch(Node):
    def __init__(self, query: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "plugin"
        self.title = "Web Search"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Enable multi-source web searching to aggregate information from various websites and platforms."

        if count > 1:
            self.title += ' ' + str(count)
        
        if records:
            value = {
                "path": records[0],
                "ref_node": records[1]
            }
        else:
            value = query


        self.parameters = {
            "apiParam": [
                {"name": "apiID", "input": {"type": "string", "value": "7387323807385829402"}},
                {"name": "apiName", "input": {"type": "string", "value": "search_url"}},
                {"name": "pluginID", "input": {"type": "string", "value": "7380279400157265954"}},
                {"name": "pluginName", "input": {"type": "string", "value": "联网问答（免费版）"}}
            ],
            "node_inputs": [
                {"name": "query", "input": {"value": value}}
            ],
            "node_outputs": {"data": {"type": "list", "items": {
                "type": "object",
                "properties": {
                    "has_image": {"type": "boolean", "value": None},
                    "image_url": {"type": "string", "value": None},
                    "logo_url": {"type": "string", "value": None},
                    "sitename": {"type": "string", "value": None},
                    "summary": {"type": "string", "value": None},
                    "title": {"type": "string", "value": None},
                    "url": {"type": "string", "value": None}
                },
                "value": None
            },
            "value": None}}
        }
