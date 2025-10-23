'''
Loading Spinner Helper
Provides a reusable, thread-based loading spinner for console applications.
'''

import sys
import time
import threading
from contextlib import contextmanager


class LoadingSpinner:
    '''Thread-based loading spinner for console feedback'''
    
    def __init__(self, message: str = 'Running'):
        self.message = message
        self.spinner_chars = ['|', '/', '-', '\\\\']
        self.stop_event = threading.Event()
        self.thread = None
    
    def _spin(self):
        '''Spinner animation loop'''
        i = 0
        while not self.stop_event.is_set():
            char = self.spinner_chars[i % len(self.spinner_chars)]
            sys.stdout.write(f'\r  {self.message}... {char}')
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
    
    def start(self):
        '''Start the spinner in a background thread'''
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        '''Stop the spinner and clear the line'''
        if self.thread and self.thread.is_alive():
            self.stop_event.set()
            self.thread.join(timeout=0.5)
            sys.stdout.write('\r' + ' ' * 60 + '\r')
            sys.stdout.flush()


@contextmanager
def spinner(message: str = 'Running'):
    '''
    Context manager for loading spinner
    
    Usage:
        with spinner('Processing'):
            # Long running operation
            time.sleep(5)
    '''
    sp = LoadingSpinner(message)
    sp.start()
    try:
        yield sp
    finally:
        sp.stop()
