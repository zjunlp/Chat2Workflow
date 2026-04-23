from ..node import Node

class Start(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.id = "100001"

        self.type = "start"
        self.title = "Start"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Start-v2.jpg"
        self.description = "The initial node, setting the required parameters to start the workflow."

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {}
        node_outputs = {}

        for var in var_list:

            if var[1] == "number":
                var[1] = "float"
            elif var[1] == "array[number]":
                var[1] = "array[float]"
            
            if "array" in var[1]:
                var_template = {
                    "type": "list",
                    "items":{
                        "type": var[1].split('[')[-1].split(']')[0],
                        "value": None
                    },
                    "value": None
                }
            else:
                var_template = {
                    "type": var[1],
                    "value": None
                }
            
            node_outputs[var[0]] = var_template
        

        self.parameters["node_outputs"] = node_outputs
