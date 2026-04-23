from ..node import Node

class End(Node):
    def __init__(self, out_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "End"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "outputs": [],
            "selected": False,
            "title": title,
            "type": "end"
        }

        for out in out_list:
            out_template = {
                "value_selector": [out[3], out[1]],
                "value_type": out[2],
                "variable": out[0]
            }

            if '.' in out[1]: 
                father_var, child_var = out[1].split('.') 
                out_template["value_selector"] = [out[3], father_var, child_var]

            self.data["outputs"].append(out_template)
