from ..node import Node

class Code(Node):
    def __init__(self, code: str, input_list: list, output_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Code"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "code": code,
            "code_language": "python3",
            "outputs": {}, ## 
            "selected": False,
            "title": title,
            "type": "code",
            "variables": []
        }

        for input_item in input_list:
            var_template = {
                "value_selector": [input_item[3], input_item[1]],
                "value_type": input_item[2],
                "variable": input_item[0]
            }

            if '.' in input_item[1]: 
                father_var, child_var = input_item[1].split('.') 
                var_template["value_selector"] = [input_item[3], father_var, child_var]

            self.data["variables"].append(var_template)
        
        for output_item in output_list:
            self.data["outputs"][output_item[0]] = {
                "children": None,
                "type": output_item[1]
            }
