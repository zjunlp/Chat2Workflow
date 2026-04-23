from ..node import Node

class VariableAggregator(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Variable Aggregator"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "output_type": var_list[0][1],
            "selected": False,
            "title": title,
            "type": "variable-aggregator",
            "variables": []
        }

        for var in var_list:
            if '.' in var[0]: 
                father_var, child_var = var[0].split('.') 
                self.data["variables"].append([var[2], father_var, child_var])
            else:
                self.data["variables"].append([var[2], var[0]])
