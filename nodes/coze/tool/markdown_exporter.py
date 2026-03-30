from ..node import Node

class MarkdownExporter(Node):
    def __init__(self, target_type: str ,md_text: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "plugin"
        self.title = "Doc Maker"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Generate documents in specified formats based on the provided text."

        self.target_type = target_type

        if count > 1:
            self.title += ' ' + str(count)
        
        if records:
            md_text = {
                "path": records[0],
                "ref_node": records[1]
            }


        if target_type != "png":

            if target_type == "md":
                target_type = "markdown"
            
            if target_type == "pptx":
                apiName = "create_pptx"
                apiID = "7365715035999682597"
            else:
                apiName = "create_document"
                apiID = "7365715035999666213" 
            
            self.parameters = {
                "apiParam": [
                    {"name": "apiID", "input": {"type": "string", "value": apiID}},
                    {"name": "apiName", "input": {"type": "string", "value": apiName}},
                    {"name": "pluginID", "input": {"type": "string","value": "7365715035999649829"}},
                    {"name": "pluginName", "input": {"type": "string", "value": "Doc Maker"}}
                ],
                "node_inputs": [
                    {"name": "formatted_markdown", "input": {"value": md_text}},
                    {"name": "title", "input": {"type": "string", "value": "Final Document"}}
                ],
                "node_outputs": {
                    "data": {"type": "string", "value": None}
                }
            }

            if target_type != "pptx":
                self.parameters["node_inputs"].append({"name": "to_format", "input": {"type": "string", "value": target_type}})
        
        else:
            self.parameters = {
                "apiParam": [
                    {"name": "apiID", "input": {"type": "string", "value": "7589192736172146734"}},
                    {"name": "apiName", "input": {"type": "string", "value": "generatePosterImage"}},
                    {"name": "pluginID", "input": {"type": "string","value": "7589192736172130350"}},
                    {"name": "pluginName", "input": {"type": "string", "value": "MD2Image"}}
                ],
                "node_inputs": [
                    {"name": "markdown", "input": {"value": md_text}}
                ],
                "node_outputs": {
                    "url": {"type": "string", "value": None}
                }
            }