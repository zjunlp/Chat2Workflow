from ..node import Node
import re

def auto_transform_code(original_code: str) -> str:

    match = re.search(r'def\s+main\s*\((.*?)\)\s*:', original_code)
    if not match:
        return original_code
    
    args_str = match.group(1)
    
    variables = []
    if args_str.strip():
        for arg in args_str.split(','):
            var_name = arg.split(':')[0].strip()
            if var_name:
                variables.append(var_name)
                
    header_end_idx = match.end()
    body = original_code[header_end_idx:]
    
    indent_match = re.search(r'\n([ \t]+)', body)
    indent = indent_match.group(1) if indent_match else "    "
    
    modified_body = body
    for var in variables:
        pattern = rf'(?<![\"\'])\b{var}\b(?![\"\'])'
        modified_body = re.sub(pattern, f"params['{var}']", modified_body)
        
    new_header = "async def main(args: Args) -> Output:"
    params_line = f"\n{indent}params = args.params"
    
    new_code = new_header + params_line + modified_body
    
    return new_code


class Code(Node):
    def __init__(self, code: str, input_list: list, output_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        self.type = "code"
        self.title = "Code"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Code-v2.jpg"
        self.description = "Code execution: Processes input variables to generate specific returns."

        self.version = "v2"

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {"language": 3}

        node_inputs = []
        node_outputs = {}
        new_code = auto_transform_code(code)


        self.parameters["code"] = new_code

        for input_item in input_list:
            invar_template = {
                "name": input_item[0],
                "input":{
                    "value":{
                        "path": input_item[1],
                        "ref_node": input_item[3]
                    }
                }
            }

            node_inputs.append(invar_template)
        
        self.parameters["node_inputs"] = node_inputs

        
        for output_item in output_list:
            
            if output_item[1] == "number":
                output_item[1] = "float"
            elif output_item[1] == "array[number]":
                output_item[1] = "array[float]"

            if "array" in output_item[1]:
                var_template = {
                    "type": "list",
                    "items":{
                        "type": output_item[1].split('[')[-1].split(']')[0],
                        "value": None
                    },
                    "value": None
                }
            else:
                var_template = {
                    "type": output_item[1],
                    "value": None
                }
            
            node_outputs[output_item[0]] = var_template
        
        self.parameters["node_outputs"] = node_outputs 
