from ..node import Node

class TemplateTransform(Node):
    def __init__(self, var_list: list, template: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.type = "text"
        self.title = "Template"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-StrConcat-v2.jpg"
        self.description = "String Formatter: Processes and formats multiple string inputs."

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {
            "concatParams": [{
                "name": "concatResult",
                "input": {
                    "type": "string",
                    "value": None
                }
            }],
            "method": "concat",
            "node_inputs": [],
            "node_outputs": {
                "output": {
                    "type": "string",
                    "required": True,
                    "value": None
                }
            }
        }

        for i in range(len(var_list)):
            var = var_list[i]
            var_template = {
                "name": f"String{i+1}",
                "input":{
                    "value":{
                        "path": var[1],
                        "ref_node": var[3],
                    }
                }
            }

            self.parameters["node_inputs"].append(var_template)

            old_name = var[0]
            old_pattern = f"{{{{{old_name}}}}}"
            new_pattern = f"{{{{String{i+1}}}}}"
            template = template.replace(old_pattern, new_pattern)
        


        self.parameters["concatParams"][0]["input"]["value"] = template
