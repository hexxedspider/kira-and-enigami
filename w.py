import subprocess
import sys
import time
import multiprocessing
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class RestartHandler(FileSystemEventHandler):
    def __init__(self, scripts):
        self.scripts = scripts  # list of bot scripts
        self.processes = {}
        self.start_bots()

    def start_bots(self):
        for script in self.scripts:
            self.start_bot(script)

    def start_bot(self, script):
        if script in self.processes:
            self.processes[script].terminate()
            self.processes[script].wait()
        self.processes[script] = subprocess.Popen([sys.executable, script])

    def on_modified(self, event):
        for script in self.scripts:
            if event.src_path.endswith(script):
                self.start_bot(script)

if __name__ == "__main__":
    path = "."  # folder to watch
    bot_scripts = ["bot1.py", "bot2.py", "bot3.py"]
    event_handler = RestartHandler(bot_scripts)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()
    print("Thank you for choosing kira and enigami's experience.")

    try:
        while True:
            time.sleep(5) # set to 5 seconds to avoid small breaks from restarting, forcing rate limits
    except KeyboardInterrupt:
        observer.stop()
        for proc in event_handler.processes.values():
            proc.terminate()
    observer.join()
