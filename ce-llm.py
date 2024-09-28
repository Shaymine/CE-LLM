from flask import Flask, request, jsonify
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
import torch
from runtime import GenericRuntime
import os

os.environ['CUDA_VISIBLE_DEVICES'] = ','.join(["0","1","2","3"])

class ProgramInterface:
    def __init__(
        self, 
        model_name:str = "../pretrained_model/Meta-Llama-3-8B-Instruct", 
        runtime = None,
        stop:str = '\n\n'
    ) -> None:
        self.model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16, device_map="auto")
        # self.model = self.model.to('cuda')
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.runtime = runtime
        self.stop = stop
        self.history = []
        self.runtime = runtime if runtime else GenericRuntime()
    
    def whether_execute_input(self, user_input):
        whether_execute = bool(re.search(r'\b(execute|run|calculate)\b', user_input, re.IGNORECASE))
        whether_code = bool(re.search(r'\b(code|script|command)\b', user_input, re.IGNORECASE))
        return whether_execute and whether_code
    
    def extract_code(self, text):
        match = re.search(r'```(.*?)```', text, re.DOTALL)
        snippet = match.group(1).strip() if match else ""
        return snippet.split('\n')
    
    def execute(self, code):
        all_code = '\n'.join(code)
        # if self.dangerous_check(all_code):
        #     return "Reject"
        method = 'solution()'
        if method not in all_code:
            return None
        self.runtime.exec_code('\n'.join(code))
        return self.runtime.eval_code(method)

    def dangerous_check(self, code):
        dangerous_imports = r'^(import\s+(os|subprocess)|from\s+(os|subprocess)\s+import)'
        return bool(re.search(dangerous_imports, code, re.MULTILINE))


    def query_model(self, prompt):
        input = self.tokenizer(prompt, return_tensors='pt')
        outputs = self.model.generate(**input, max_new_tokens=256)
        # prompt_length = len(self.tokenizer.encode(input))
        text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        text = text[len(prompt):].strip()
        end_index = text.find('\n\n\n')
        if end_index != -1:
            text = text[:end_index]
        result = None
        if self.whether_execute_input(prompt):
            code = self.extract_code(text)
            try:
                result = self.execute(code)
                if result == None:
                    text = text + '\nNo results was produced. A common reason is that the generated code snippet did not return any results.'
                elif result == "Reject":
                    text = text + "\nSorry, a dangerous command has been detected in your code and is refused to execute."
                else:
                    text = text + f"\nThe execution result of this code snippet is {result}."
            except:
                # print(e)
                text = text + "\nSorry, it seems that the generated code snippet is not valid."
        return text

app = Flask(__name__)
interface = ProgramInterface()

@app.route('/query', methods=['POST'])
def query_model():
    user_input = request.json.get('input')
    response = interface.query_model(user_input)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)