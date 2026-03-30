from ..node import Node

class DocumentExtractor(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.type = "plugin"
        self.title = "Document Extractor"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Document Reader: Extracts content from documents; supports HTML, XML, DOC/X, PPT/X, TXT, PDF, CSV, and XLSX."

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {
            "apiParam": [
                {"name": "apiID", "input": {"type": "string", "value": "7405805158996934683"}},
                {"name": "apiName", "input": {"type": "string", "value": "read"}},
                {"name": "pluginID", "input": {"type": "string", "value": "7405805158996918299"}},
                {"name": "pluginName", "input": {"type": "string", "value": "文件读取"}}
            ],
            "node_inputs": [
                {"name": "url", "input": {"value": {"path": var_list[0], "ref_node": var_list[2]}}}
            ],
            "node_outputs": {"data": {"type": "string", "value": None}}
        }