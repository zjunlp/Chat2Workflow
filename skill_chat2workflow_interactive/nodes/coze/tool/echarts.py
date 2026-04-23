from ..node import Node

class Echarts(Node):
    def __init__(self, chart_type: str, chart_title: str, data: str, x_axisORcategories: str, x: int, y: int, count: int = 1, records: list = None):
        super().__init__(x,y)

        self.type = "plugin"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-Plugin-v2.jpg"
        self.description = "Visualization Node: Generates charts based on user-specified requirements."

        tool_name = chart_type + "_charts"
        self.title = tool_name

        if count > 1:
            self.title += ' ' + str(count)

        apiID = ""

        if chart_type == "bar":
            apiID = "7404745324968869922"
        elif chart_type == "line":
            apiID = "7404745324968886306"
        elif chart_type == "pie":
            apiID = "7362433438483300364"

        
        if records:
            chart_title = {
                "path": records[0],
                "ref_node": records[1]
            }

        self.parameters = {
            "apiParam": [
                {"name": "apiID", "input": {"type": "string", "value": apiID}},
                {"name": "apiName", "input": {"type": "string", "value": tool_name}},
                {"name": "pluginID", "input": {"type": "string","value": "7362433438483267596"}},
                {"name": "pluginName", "input": {"type": "string", "value": "图表大师"}}
            ],
            "node_inputs": [{"name": "title", "input": {"type": "string", "value": chart_title}}],
            "node_outputs": {
                "data": {"type": "string", "value": None}
            }
        }


        if chart_type != "pie":
            data = data.strip('`').strip('"').strip("'")
            data = data.replace(';', ',')
            data = "[" + data + "]"

            x_axisORcategories = x_axisORcategories.strip('`').strip('"').strip("'")
            temp_list = x_axisORcategories.split(';')
            temp_str = ""
            for item in temp_list:
                temp_str += "\\\"" + item + "\\\""
                if item != temp_list[-1]:
                    temp_str += ","
            x_axisORcategories = "[" + temp_str + "]"

            self.parameters["node_inputs"].append({"name": "data", "input": {"type": "string", "value": data}})
            self.parameters["node_inputs"].append({"name": "xAxis", "input": {"type": "object", "value": "{\"data\": \"" + x_axisORcategories + "\"}"}})
            self.parameters["node_inputs"].append({"name": "yAxis", "input": {"type": "object", "value": "{\"type\":\"value\"}"}})

            print(self.parameters["node_inputs"])
        else:
            data = data.strip('`').strip('"').strip("'")
            data_list = [int(item) for item in data.split(';')]

            categories = x_axisORcategories.strip('`').strip('"').strip("'")
            categories_list = [item.strip() for item in categories.split(';')]

            string = "[\n  "
            for i in range(len(data_list)):
                string += "{\n    \"name\": \"" + categories_list[i] + "\",\n    \"value\": " + str(data_list[i]) + "\n  }"
                if i != len(data_list) - 1:
                    string += ",\n  "
            string += "\n]"

            template = {
                "name": "data",
                "input": {
                    "type": "list",
                    "items":{
                        "type": "object",
                        "value": None
                    },
                    "value": string
                }
            }

            self.parameters["node_inputs"].append(template)
