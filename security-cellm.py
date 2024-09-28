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
        model_name:str = "/mnt/home/wujialin/llm/pretrained_model/Meta-Llama-3-8B-Instruct", 
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
        # predefined的危险函数/库
        dangerous_libraries = [
            r'\bimport\s+os\b',
            r'\bimport\s+subprocess\b',
            r'\bimport\s+requests\b',
            r'\bimport\s+sqlite3\b',
            r'\bopen\s*\(.*\)',
            r'\bexec\s*\(.*\)',
            r'\beval\s*\(.*\)',
            r'\bimport\s+shutil\b',
            r'\bimport\s+socket\b',
            r'\bimport\s+sys\b',
            r'\bimport\s+ctypes\b',
            r'\bimport\s+pickle\b',
            r'__import__\s*\(.*\s*(os|subprocess|requests|sqlite3|shutil|socket|sys|ctypes|pickle)\s*',
        ]
        all_code = '\n'.join(code)
        # 模式匹配
        for pattern in dangerous_libraries:
            if re.search(pattern, all_code):
                print('Malicious Code Detect.')
                return "Reject"
        method = 'solution()'
        if method not in all_code:
            return None
        try:
            runtime_result = self.runtime.exec_code_timeout('\n'.join(code))
            if runtime_result == "Timeout":
                return "Timeout"
            else:
                return runtime_result
        except Exception as e:
            return e
    
    def llm_check(self, text):
        negative_phrases = [r"can't", r"can not", r"won't", r"will not"]
        action_phrases = [r"execute", r"run"]
        # 使用正则表达式分割句子
        sentences = re.split(r'(?<=\.)\s*', text)
        # 遍历每个句子，检查是否包含所需的短语组合
        for sentence in sentences:
            # 检查句子是否包含任意一个否定短语
            has_negative = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in negative_phrases)
            # 检查句子是否包含任意一个动作短语
            has_action = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in action_phrases)
            # 如果同时包含否定短语和动作短语，返回 True
            if has_negative and has_action:
                return True
        return False



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
            llm_judge = self.llm_check(text.split('```')[0])
            if llm_judge:
                return text
            code = self.extract_code(text)
            try:
                result = self.execute(code)
                # sys.stderr(result)
                if result == None:
                    text = text + '\nNo results was produced. A common reason is that the generated code snippet did not return any results.'
                elif isinstance(result, Exception):
                    text = text + f"\nAn error occurred during the operation: {result}."
                elif result == "Reject":
                    text = text + "\nSorry, a dangerous command has been detected in your code and is refused to execute."
                elif result == "Timeout":
                    text = text + "\nThe program has timed out. Please check if there is any looping code."
                else:
                    text = text + f"\nThe execution result of this code snippet is {result}."
            except Exception as e:
                # print(e)
                text = text + f"\nSorry, it seems that the generated code snippet is not valid: {e}"
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