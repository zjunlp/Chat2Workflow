from ..node import Node

class ListOperator(Node):
    def __init__(self, var: list, operator: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "List Operator"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "extract_by": {
                "enabled": False,
                "serial": "" #
            },
            "filter_by":{
                "conditions":[{
                    "comparison_operator": "contains", # 
                    "key": "",
                    "value": "" #
                }],
                "enabled": False
            },
            "item_var_type": var[1].split('[')[-1].split(']')[0],
            "limit":{
                "enabled": False,
                "size": 10 #
            },
            "order_by":{
                "enabled": False,
                "key": "",
                "value": "asc" #
            },
            "selected": False,
            "title": title,
            "type": "list-operator",
            "var_type": var[1], 
            "variable": [var[2],var[0]] 
        }

        if operator[0] == "filter_by":
            self.data["filter_by"]["enabled"] = True
            self.data["filter_by"]["conditions"][0]["comparison_operator"] = operator[1]
            
            value = str(operator[2])
            if value == 'true':
                value = True
            elif value == 'false':
                value = False

            if var[1] == 'array[file]':
                self.data["filter_by"]["conditions"][0]["key"] = "type"
                self.data["filter_by"]["conditions"][0]["value"] = [value]

            else:
                if operator[1] != "empty" and operator[1] != "not empty":
                    self.data["filter_by"]["conditions"][0]["value"] = value

        elif operator[0] == "extract_by":
            self.data["extract_by"]["enabled"] = True
            self.data["extract_by"]["serial"] = str(operator[1])
        elif operator[0] == "limit":
            self.data["limit"]["enabled"] = True
            self.data["limit"]["size"] = operator[1]
        elif operator[0] == "order_by":

            if var[1] == 'array[file]':
                self.data["order_by"]["key"] = "name"

            self.data["order_by"]["enabled"] = True
            self.data["order_by"]["value"] = operator[1]
