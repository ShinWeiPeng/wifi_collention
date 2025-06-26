import inspect
import os
from datetime import datetime

def log(*args, sep=' ', end='\n'):
    """
    替代 print() 的除錯工具，會自動顯示目前的檔案、行號、函式名稱、時間戳（到毫秒）。

    使用範例：
        log("資料接收中", data)
    """
    frame = inspect.currentframe().f_back
    filename = os.path.basename(inspect.getfile(frame))
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name

    timestr = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # 切掉最後3位，變成毫秒

    prefix = f"[{timestr}] [{filename}:{lineno}] {funcname}()"

    print(prefix, *args, sep=sep, end=end)
