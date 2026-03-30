from ..node import Node

class Start(Node):
    def __init__(self, var_list: list, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        title = "Start"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "selected": False,
            "title": title,
            "type": "start",
            "variables": []
        }

        for var in var_list:
            if var[1] == "array[file]" or var[1] == "file":

                if var[1] == "array[file]":
                    var[1] = "file-list"

                var_file_template = {
                    "allowed_file_extensions": [],
                    "allowed_file_types": ["image","document","audio","video"],
                    "allowed_file_upload_methods": ["local_file","remote_url"],
                    "default": "",
                    "hint": "",
                    "label": var[0],
                    "max_length": 10,
                    "options": [],
                    "placeholder": "",
                    "required": False,
                    "type": var[1],
                    "variable": var[0]
                }
                if var[1] == "file":
                    var_file_template["max_length"] = 32768
                self.data["variables"].append(var_file_template)
            else:

                if var[1] == "string":
                    var[1] = "paragraph"
                elif var[1] == "boolean":
                    var[1] = "checkbox"

                var_template = {
                    "default": "",
                    "hint": "",
                    "label": var[0],
                    "max_length": 32768,
                    "options": [],
                    "placeholder": "",
                    "required": False,
                    "type": var[1],
                    "variable": var[0]
                }
                self.data["variables"].append(var_template)
