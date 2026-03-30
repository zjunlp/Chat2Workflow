from ..node import Node

class QuestionClassifier(Node):
   def __init__(self, query: list, class_list: list, x: int, y: int, count: int = 1, instruction: str = ""):
        super().__init__(x,y)
        
        self.type = "intent"
        self.title = "Question Classifier"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Intent-v2.jpg"
        self.description = "Intent Classifier: Recognizes user intent and matches it to a predefined option."

        if count > 1:
            self.title += ' ' + str(count)


        self.parameters = {
            "intents": [],
            "llmParam": {
                "modelName": "豆包·2.0·pro",
                "modelType": "1772700462",
                "prompt": {
                    "type": "string",
                    "value": {
                        "content": "{{query}}",
                        "type": "literal"
                    }
                },
                "systemPrompt": {
                    "type": "string",
                    "value": {
                        "content": instruction,
                        "type": "literal"
                    }
                }
            },
            "node_inputs": [
                {
                    "name": "query",
                    "input": {"value":{
                        "path": query[0],
                        "ref_node": query[1]
                    }}
                }
            ],
            "node_outputs": {
                "classificationId": {
                    "type": "integer",
                    "value": None
                }
            }
        }

        for class_item in class_list:
            self.parameters["intents"].append({"name": class_item})
        
        if len(self.parameters["intents"]) > 1:
            self.parameters["intents"].pop(-1)
