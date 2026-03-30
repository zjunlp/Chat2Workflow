from ..node import Node

class HttpRequest(Node):
    def __init__(self, url: str, x: int, y: int, count: int = 1, github_rest_token: str = "", params: str = ""):
        super().__init__(x,y)

        self.type = "http"
        self.title = "HTTP Request"
        self.icon = "https://lf3-static.bytednsdoc.com/obj/eden-cn/dvsmryvd_avi_dvsm/ljhwZthlaukjlkulzlp/icon/icon-HTTP.png"
        self.description = "Sends HTTP/API requests to external services and returns the data from the interface."

        if count > 1:
            self.title += ' ' + str(count)


        if github_rest_token:
            authdata = github_rest_token
        else:
            authdata = "EMPTY"

        self.parameters = {
            "apiInfo":{
                "method": "GET",
                "url": url
            },
            "auth":{
                "authData":{
                    "bearerTokenData": [{"name": "token", "input": {"type": "string", "value": authdata}}],
                    "customData": {"addTo": "header"}
                },
                "authOpen": True,
                "authType": "BEARER_AUTH"
            },
            "body":{
                "bodyData":{"binary":{"fileURL":{
                    "type": "string",
                    "value": {
                        "content":{
                            "blockID": "",
                            "name": "",
                            "source": "block-output"
                        },
                        "type": "ref"
                    }
                }}},
                "bodyType": "EMPTY"
            }
        }
