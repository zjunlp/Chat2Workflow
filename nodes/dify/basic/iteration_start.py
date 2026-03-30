from ..node import Node

class IterationStart(Node):
    def __init__(self, x: int, y: int):
        super().__init__(x,y)

        self.data = {
            "desc": "",
            "isInIteration": True,
            "selected": False,
            "title": "",
            "type": "iteration-start"
        }

        self.parentId = ""
