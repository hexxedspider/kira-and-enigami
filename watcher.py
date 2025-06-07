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
            print(f"Restarting {script}...")
            self.processes[script].terminate()
            self.processes[script].wait()
        print(f"Starting {script}...")
        self.processes[script] = subprocess.Popen([sys.executable, script])

    def on_modified(self, event):
        for script in self.scripts:
            if event.src_path.endswith(script):
                print(f"{event.src_path} changed, restarting...")
                self.start_bot(script)

if __name__ == "__main__":
    path = "."  # folder to watch
    bot_scripts = ["bot1.py", "bot2.py", "bot3.py"]  # your two bot scripts

    event_handler = RestartHandler(bot_scripts)
    observer = Observer()
    observer.schedule(event_handler, path=path, recursive=False)
    observer.start()
    print("Watching for file changes to bot1.py, bot2.py, and bot3.py...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        for proc in event_handler.processes.values():
            proc.terminate()
    observer.join()
