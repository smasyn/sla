class Logger:

    def __init__(self):
        # configure a logger file  
        from time import localtime, strftime

        formatted_time = strftime("%Y%m%d_%H%M%S", localtime())

        # make an output subdirectory using today's date
        self.out_path = "./log/log_" + formatted_time + ".txt"
        self.console  = False
        self.history  = ""

    def log(self,tag,msg,console=False):
            # append to a logger file  
            # t  text to append

        from time import localtime, strftime
        
        formatted_time = strftime("%Y%m%d %H%M%S", localtime())

        if msg is None:
            msg = "None"
            
        msg = formatted_time + " " + tag + "\n" + msg + "\n\n"

        # print to console
        # str(msg) to simply replace all non utf-8 characters
        if console:
            print(str(msg))

        # store the last message in the history
        self.history = msg
        
        # append to the logfile
        with open(self.out_path, 'a',encoding="UTF-8") as file:
            file.write(msg)

        return None