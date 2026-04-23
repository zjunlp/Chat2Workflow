from ..node import Node

class Text2Image(Node):
    def __init__(self, image_prompt: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "image_generate"
        self.title = "Image Generator"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-ImageGeneration-v2.jpg"
        self.description = "Generate images through textual descriptions"

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {
            "modelSetting": {
                "custom_ratio": {
                    "height": 1024,
                    "ratio_type": "fixed",
                    "width": 1024
                },
                "ddim_steps": 25,
                "guidance_scale": 2.5,
                "max_images": 1,
                "model": 8,
                "ratio": 0,
                "watermark": False
            },
            "node_outputs":{
                "data": {"type": "image", "value": None}
            },
            "prompt": {
                "negative_prompt": "",
                "prompt": image_prompt
            }
        }

        if records is not None:
            self.parameters["node_inputs"] = []

            for var in records:
                input_template = {
                    "name": '_' + var[1] + '_' + var[0],
                    "input":{
                        "value":{
                            "path": var[0],
                            "ref_node": var[1]
                        }
                    }
                }
                self.parameters["node_inputs"].append(input_template)