from ..node import Node

class TemplateTransform(Node):
    def __init__(self, var_list: list, template: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Template"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "selected": False,
            "template": template,
            "title": title,
            "type": "template-transform",
            "variables": []
        }

        for var in var_list:
            var_template = {
                "value_selector": [var[3], var[1]],
                "value_type": var[2],
                "variable": var[0]
            }

            if '.' in var[1]: 
                father_var, child_var = var[1].split('.') 
                var_template["value_selector"] = [var[3], father_var, child_var]

            self.data["variables"].append(var_template)
