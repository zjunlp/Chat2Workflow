from ..node import Node
import uuid

class LLM(Node):
    def __init__(self, prompt_list: list, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "llm"
        self.title = "LLM"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-LLM-v2.jpg"
        self.description = "LLM Call: Generates responses using variables and prompts."

        if count > 1:
            self.title += ' ' + str(count)

        systemPrompt = ""
        userPrompt = ""


        for prompt in prompt_list:
            if prompt[0] == "system":
                systemPrompt = prompt[1]
            elif prompt[0] == "user":
                userPrompt = prompt[1]


        self.parameters = {
            "llmParam": [
                {"name": "temperature", "input": {"type": "float", "value": "0.7"}},
                {"name": "maxTokens", "input": {"type": "integer", "value": "32768"}},
                {"name": "thinkingType", "input": {"type": "string", "value": "enabled"}},
                {"name": "responseFormat", "input": {"type": "integer", "value": "0"}},
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
                {"name": "systemPrompt", "input": {"type": "string", "value": systemPrompt}},
                {"name": "prompt", "input": {"type": "string", "value": userPrompt}}
            ],
            "node_outputs": {
                "text": {
                    "type": "string",
                    "value": None
                }
            }
        }

        if records is not None:
            self.parameters["node_inputs"] = []

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