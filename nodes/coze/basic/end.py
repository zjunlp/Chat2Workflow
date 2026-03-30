from ..node import Node

class End(Node):
    def __init__(self, out_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.id = "900001"

        self.type = "end"
        self.title = "End"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-End-v2.jpg"
        self.description = "The final node, yielding the resulting data after the workflow execution."

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {}
        node_inputs = []


        for out in out_list:

            out_template = {
                "name": out[0],
                "input":{
                    "value":{
                        "path": out[1],
                        "ref_node": out[3]
                    }
                }
            }
        
            node_inputs.append(out_template)
        
        self.parameters["node_inputs"] = node_inputs
        self.parameters["terminatePlan"] = "returnVariables"
        
