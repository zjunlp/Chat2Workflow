from ..node import Node

class IfElse(Node):
    def __init__(self, case_list: list, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "condition"
        self.title = "IF-Else"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Condition-v2.jpg"
        self.description = "Conditional Branch: Executes the specific branch whose condition is met, or the 'Else' branch if none match."

        if count > 1:
            self.title += ' ' + str(count)
    

        self.parameters = {
            "branches": []
        }

        for case in case_list:
            
            if case[0] == "or":
                logic = 1
            else:
                logic = 2

            case_template = {
                "condition": {
                    "conditions": [],
                    "logic": logic
                }
            }

            OPERATOR_MAP = {"=": 1, "is": 1, "≠": 2, "is not": 2, "contains": 7, "not contains": 8,"empty": 9, "not exists": 9, "not empty": 10, "exists": 10, ">": 13, "≥": 14, "<": 15, "≤": 16}

            for condition in case[1]:
                operator = OPERATOR_MAP.get(condition[3])

                if len(condition) == 5:

                    if records:
                        value = {
                            "path": records[0],
                            "ref_node": records[1]
                        }
                    else:
                        value = condition[4]


                    if value == 'true':
                        value = True
                    elif value == 'false':
                        value = False

                    item = {
                        "left": {"input":{"value":{
                            "path": condition[0],
                            "ref_node": condition[2]
                        }}},
                        "operator": operator,
                        "right": {"input":{"value": value}}
                    }
                else:
                    item = {
                        "left": {"input":{"value":{
                            "path": condition[0],
                            "ref_node": condition[2]
                        }}},
                        "operator": operator
                    }

                case_template["condition"]["conditions"].append(item)
            
            self.parameters["branches"].append(case_template)
