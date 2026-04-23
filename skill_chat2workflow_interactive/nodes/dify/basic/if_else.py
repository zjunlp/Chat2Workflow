from ..node import Node
import uuid

class IfElse(Node):
    def __init__(self, case_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "If-Else"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "cases": [],
            "selected": False,
            "title": title,
            "type": "if-else",
        }

        self.sourceHandle_list = []

        for case in case_list:
            case_id = str(uuid.uuid4())
            case_template = {
                "case_id": case_id,
                "conditions": [],
                "id": case_id,
                "logical_operator": case[0],
            }

            for condition in case[1]:
                value = ""
                if len(condition) == 5:
                    value = condition[4]
                    if value == 'true':
                        value = True
                    elif value == 'false':
                        value = False

                condition_template = {
                    "comparison_operator": condition[3],
                    "id": str(uuid.uuid4()),
                    "value": value,
                    "varType": condition[1],
                    "variable_selector": [condition[2], condition[0]]
                }

                if '.' in condition[0]: 
                    father_var, child_var = condition[0].split('.') 
                    condition_template["variable_selector"] = [condition[2], father_var, child_var]
                    condition_template["value"] = [value]

                if condition[1] == "number" and '{{#' in value:
                    condition_template["numberVarType"] = "variable"
                
                if condition[1] == "array[file]":
                    sub_variable_condition = {
                        "case_id": str(uuid.uuid4()),
                        "conditions": [{
                            "comparison_operator": "in",
                            "id": str(uuid.uuid4()),
                            "key": "type",
                            "value": [],
                            "varType": "string",
                        }],
                        "logical_operator": "and"
                    }
                    sub_variable_condition["conditions"][0]["value"].append(value)
                    condition_template["sub_variable_condition"] = sub_variable_condition

                case_template["conditions"].append(condition_template)

            self.data["cases"].append(case_template)
            self.sourceHandle_list.append(case_id)
        
        self.sourceHandle_list.append("false")
