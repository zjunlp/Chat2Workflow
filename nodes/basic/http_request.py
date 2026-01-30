from ..node import Node

class HttpRequest(Node):
    def __init__(self, url: str, x: int, y: int, count: int = 1, params: str = ""):
        super().__init__(x,y)

        title = "HTTP Request"

        if count > 1:
            title += ' ' + str(count)

        self.data = {
            "authorization":{
                "config": None,
                "type": "no-auth"
            },
            "body": {
                "data":[],
                "type": 'none'
            },
            "headers": "",
            "method": "get",
            "params": params,
            "retry_config":{
                "max_retries": 3,
                "retry_enabled": True,
                "retry_interval": 100
            },
            "selected": False,
            "ssl_verify": True,
            "timeout":{
                "max_connect_timeout": 0,
                "max_read_timeout": 0,
                "max_write_timeout": 0
            },
            "title": title,
            "type": "http-request",
            "url": url,
            "variables": []
        }
