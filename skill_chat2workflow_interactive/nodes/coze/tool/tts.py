from ..node import Node

class TTS(Node):
    def __init__(self, text: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "plugin"
        self.title = "Text to Speech"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Text-to-speech audio synthesis"

        if count > 1:
            self.title += ' ' + str(count)

        if records:
            text = {
                "path": records[0],
                "ref_node": records[1]
            }

        self.parameters = {
            "apiParam": [
                {"name": "apiID", "input": {"type": "string", "value": "7426655854067367946"}},
                {"name": "apiName", "input": {"type": "string", "value": "speech_synthesis"}},
                {"name": "pluginID", "input": {"type": "string","value": "7426655854067351562"}},
                {"name": "pluginName", "input": {"type": "string", "value": "语音合成"}}
            ],
            "node_inputs": [
                {"name": "text", "input": {"value": text}}
            ],
            "node_outputs": {
                "data": {
                    "type": "object",
                    "properties": {
                        "duration": {"type": "float", "value": None},
                        "link": {"type": "string", "value": None}
                    },
                    "value": None
                }
            }
        }
