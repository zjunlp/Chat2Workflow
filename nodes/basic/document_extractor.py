from ..node import Node

class DocumentExtractor(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Document Extractor"

        if count > 1:
            title += ' ' + str(count)

        if var_list[1] == 'file':
            var_type = False
        elif var_list[1] == 'array[file]':
            var_type = True

        self.data = {
            "is_array_file": var_type,
            "selected": False,
            "title": title,
            "type": "document-extractor",
            "variable_selector": [var_list[2], var_list[0]]
        }
