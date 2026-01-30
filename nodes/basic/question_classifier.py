from ..node import Node
import random
import string

class QuestionClassifier(Node):
   def __init__(self, query: list, class_list: list, x: int, y: int, count: int = 1, instruction: str = ""):
        super().__init__(x,y)

        title = "Question Classifier"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "classes": [],
            "instructions": instruction,
            "model": {
                "completion_params": {
                    "temperature": 0.7,
                    "max_tokens": 32768
                },
                "mode": "chat",
                "name": "qwen3-vl-plus",
                "provider": "langgenius/tongyi/tongyi"
            },
            "query_variable_selector": [query[1], query[0]],
            "selected": False,
            "title": title,
            "type": "question-classifier",
            "vision": {"enabled": False}
        }
        
        self.sourceHandle_list = []

        for class_item in class_list:
            class_id = '1' + ''.join(random.choices(string.digits, k=12))
            class_template = {
                "id": class_id,
                "name": class_item
            }
            self.data["classes"].append(class_template)
            self.sourceHandle_list.append(class_id)
