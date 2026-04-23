from ..node import Node
import random
import string

class Iteration(Node):
    def __init__(self, input_var: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Iteration"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "error_handle_mode": "terminated",
            "flatten_output": True,
            "is_parallel": False,
            "iterator_input_type": input_var[1],
            "iterator_selector": [input_var[2],input_var[0]],
            "output_selector": None,
            "output_type": None,
            "parallel_nums": 10,
            "selected": False,
            "start_node_id": self.id + 'start',
            "title": title,
            "type": "iteration"
        }
