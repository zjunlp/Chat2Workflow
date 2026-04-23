from ..node import Node

class ParameterExtractor(Node):
    def __init__(self, query: list, param_list: list, x: int, y: int, count: int = 1, instruction: str = "", records: list = None):
        super().__init__(x,y)

        self.type = "llm"
        self.title = "Parameter Extractor"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-LLM-v2.jpg"
        self.description = "The Parameter Extractor node converts unstructured text into structured data using LLM intelligence."

        if count > 1:
            self.title += ' ' + str(count)

        self.parameters = {
            "llmParam": [
                {"name": "temperature", "input": {"type": "float", "value": "0.7"}},
                {"name": "maxTokens", "input": {"type": "integer", "value": "32768"}},
                {"name": "thinkingType", "input": {"type": "string", "value": "enabled"}},
                {"name": "responseFormat", "input": {"type": "integer", "value": "2"}},
                {"name": "modelName", "input": {"type": "string", "value": "豆包·2.0·pro"}},
                {"name": "modelType", "input": {"type": "integer", "value": "1772700462"}},
                {
                    "name": "parameters",
                    "input": {
                        "type": "object",
                        "properties": {
                            "max_completion_tokens": {"type": "integer", "value": "0"},
                            "reasoning_effort": {"type": "string", "value": "medium"}
                        },
                        "value": None
                    }
                },
                {"name": "systemPrompt", "input": {"type": "string", "value": instruction}},
                {"name": "prompt", "input": {"type": "string", "value": "{{query}}"}}
            ],
            "node_inputs": [
                {
                    "name": "query",
                    "input": {"value":{
                        "path": query[0],
                        "ref_node": query[1]
                    }}
                }
            ],
            "node_outputs": {}
        }

        for param in param_list:

            if param[2] == "number":
                param[2] = "float"
            elif param[2] == "array[number]":
                param[2] = "array[float]"
            
            if "array" in param[2]:
                param_template = {
                    "type": "list",
                    "items": {
                        "type": param[2].split('[')[-1].split(']')[0],
                        "value": None
                    },
                    "value": None,
                    "description": param[0]
                }
            else:
                param_template = {
                    "type": param[2],
                    "value": None,
                    "description": param[0]
                }
            self.parameters["node_outputs"][param[1]] = param_template


        if records is not None:

            for var in records:
                input_template = {
                    "name": '_' + var[1] + '_' + var[0],
                    "input":{
                        "value":{
                            "path": var[0],
                            "ref_node": var[1]
                        }
                    }
                }
                self.parameters["node_inputs"].append(input_template)
