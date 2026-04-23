from ..node import Node

class Echarts(Node):
    def __init__(self, chart_type: str, chart_title: str, data: str, x_axisORcategories: str, x: int, y: int, count: int = 1):
        super().__init__(x,y)

        tool_name = chart_type + "_chart"

        if chart_type == "line":
            tool_label = "线性图表"
        elif chart_type == "pie":
            tool_label = "饼图"
        elif chart_type == "bar":
            tool_label = "柱状图"
        else:
            tool_label = ""

        title = tool_name

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "provider_id": "langgenius/echarts/echarts",
            "provider_name": "langgenius/echarts/echarts",
            "provider_type": "builtin",
            "selected": False,
            "title": title,
            "tool_configurations":{},
            "tool_label": tool_label,
            "tool_name": tool_name,
            "tool_node_version": "2",
            "tool_parameters":{
                "data":{
                    "type": "mixed",
                    "value": data
                },
                "title":{
                    "type": "mixed",
                    "value": chart_title
                }
            },
            "type": "tool"
        }
        
        if chart_type == "pie":
            self.data["tool_parameters"]["categories"] = {
                "type": "mixed",
                "value": x_axisORcategories
            }
        else:
            self.data["tool_parameters"]["x_axis"] = {
                "type": "mixed",
                "value": x_axisORcategories
            }
