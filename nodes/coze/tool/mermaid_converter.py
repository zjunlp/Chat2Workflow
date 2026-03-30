from ..node import Node

class MermaidConverter(Node):
    def __init__(self, mermaid_code: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "plugin"
        self.title = "Mermaid Converter"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Convert a piece of Mermaid code into a chart image and provide a corresponding online editing link."

        if count > 1:
            self.title += ' ' + str(count)
        
        if records:
            mermaid_code = {
                "path": records[0],
                "ref_node": records[1]
            }

        self.parameters = {
            "apiParam": [
                {"name": "apiID", "input": {"type": "string", "value": "7479445382888620066"}},
                {"name": "apiName", "input": {"type": "string", "value": "Mermaid"}},
                {"name": "pluginID", "input": {"type": "string","value": "7479445382888603682"}},
                {"name": "pluginName", "input": {"type": "string", "value": "Mermaid图表生成器"}}
            ],
            "node_inputs": [
                {"name": "mermaidCode", "input": {"value": mermaid_code}}
            ],
            "node_outputs": {
                "editUrl": {"type": "string", "value": None}
            }
        }
