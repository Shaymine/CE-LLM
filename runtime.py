import copy
from typing import Any, Dict
import multiprocessing

class GenericRuntime:
    GLOBAL_DICT = {}
    LOCAL_DICT = None
    HEADERS = []
    def __init__(self):
        self._global_vars = copy.copy(self.GLOBAL_DICT)
        self._local_vars = copy.copy(self.LOCAL_DICT) if self.LOCAL_DICT else None
        
        for c in self.HEADERS:
            self.exec_code(c)
        
    def exec_code(self, code_piece: str, queue) -> None:
        try:
            exec(code_piece, self._global_vars)
            result = eval('solution()', self._global_vars)
            queue.put(result)
        except Exception as e:
            queue.put(e)

        
    def exec_code_timeout(self, code_piece: str) -> None:
        queue = multiprocessing.Queue()
        process = multiprocessing.Process(target=self.exec_code, args=(code_piece, queue))
        process.start()
        process.join(10)
        if process.is_alive():
            process.terminate()
            process.join()
            return "Timeout"
        else:
            if not queue.empty():
                return queue.get()

    def eval_code(self, expr: str) -> Any:
        return eval(expr, self._global_vars)
    
    def inject(self, var_dict: Dict[str, Any]) -> None:
        for k, v in var_dict.items():
            self._global_vars[k] = v
    
    @property
    def answer(self):
        return self._global_vars['answer']
