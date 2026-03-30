from ..node import Node

class Iteration(Node):
    def __init__(self, input_var: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.type = "batch"
        self.title = "Iteration"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Batch-v2.jpg"
        self.description = "Process arrays by applying workflows to each element"

        if count > 1:
            self.title += ' ' + str(count)

        self.canvas_position = {
            "x": x - 100,
            "y": -400 * count
        }
        
        self.parameters = {
            "batchSize": {"type": "integer", "value": {"content": "100", "type": "literal"}},
            "concurrentSize": {"type": "integer", "value": {"content": "10", "type": "literal"}},
            "node_inputs": [
                {"name": "iterator_selector", 
                 "input": {
                    "value": {
                        "path": input_var[0],
                        "ref_node": input_var[2]
                    }
                }}
            ],
            "node_outputs": {
                "output":{
                    "value":{
                        "type": "list",
                        "items":{
                            "value": None
                        },
                        "value": {
                            "path": None,
                            "ref_node": None
                        }
                    }
                }
            }
        }
        self.internal_ori_id = []
        self.internal_edges = []

        self.nodes = []
        self.edges = []
