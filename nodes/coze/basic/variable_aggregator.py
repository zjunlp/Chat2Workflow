from ..node import Node

class VariableAggregator(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.type = "variable_merge"
        self.title = "Variable Aggregator"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/VariableMerge-icon.jpg"
        self.description = "Aggregator: Consolidates and processes outputs from multiple parallel branches."

        if count > 1:
            self.title += ' ' + str(count)
        
        self.parameters = {
            "mergeGroups": [{
                "name": "output",
                "variables": []
            }],
            "node_outputs": {
                "output": {
                    "value": None
                }
            }
        }


        for var in var_list:
            var_template = {
                "value": {
                    "content":{
                        "blockID": var[2],
                        "name": var[0],
                        "source": "block-output"
                    },
                    "type": "ref"
                }
            }
            self.parameters["mergeGroups"][0]["variables"].append(var_template)
