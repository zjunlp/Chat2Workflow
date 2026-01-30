from kalm.agent import KalmAgent
from openai import OpenAI

def kalm_agent_init(service_url, system_prompt, temerature, max_new_tokens):
    agent = KalmAgent(
        adams_business_name="xxxxxx",
        adams_platform_user="xxxxxx",
        adams_user_token="xxxxxx",
        service_url = service_url, 
        temperature = temerature, 
        top_p=0.8,
        top_k=20,
        num_beams=1,
        max_new_tokens=max_new_tokens,
        repetition_penalty=1,
        no_repeat_ngrams=0,
        retries=3,
        single_retry_timeout=300,
        system_prompt= system_prompt
    )
    return agent


class OpenAIAgent:
    def __init__(self, model_name, system_prompt, temperature, max_tokens):
        self.api_key = "sk-xxxxxx"
        self.base_url = "xxxxx"
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate(self, query, history=None):
        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if history:
            for user_msg, assistant_msg in history:
                messages.append({"role": "user", "content": user_msg})
                messages.append({"role": "assistant", "content": assistant_msg})
        
        messages.append({"role": "user", "content": query})

        
        response = client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        return response.choices[0].message.content
