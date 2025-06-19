import inspect
import os

def log(*args, sep=' ', end='\n'):
    """
    替代 print() 的除錯工具，會自動顯示目前的檔案、行號與函式名稱。

    使用範例：
        log("資料接收中", data)
    """
    frame = inspect.currentframe().f_back
    filename = os.path.basename(inspect.getfile(frame))
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name
    prefix = f"[{filename}:{lineno} {funcname}]"

    print(prefix, *args, sep=sep, end=end)