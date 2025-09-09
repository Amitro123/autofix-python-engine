#!/usr/bin/env python3
"""
Import Suggestions - Configuration for Python import fixing

Contains all the mappings and data structures used by PythonFixer
to suggest and add appropriate imports for missing functions and modules.
"""

# Simple import suggestions (one option per function)
IMPORT_SUGGESTIONS = {
    "sleep": "from time import sleep",
    "time": "import time",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "date": "from datetime import date",
    "json": "import json",
    "os": "import os",
    "sys": "import sys",
    "random": "import random",
    "math": "import math",
    "DataFrame": "import pandas as pd",
    "array": "import numpy as np",
    "plt": "import matplotlib.pyplot as plt",
    
    # Collections
    "defaultdict": "from collections import defaultdict",
    "Counter": "from collections import Counter",
    "OrderedDict": "from collections import OrderedDict",
    "namedtuple": "from collections import namedtuple",
    "deque": "from collections import deque",
    
    # File system and paths
    "Path": "from pathlib import Path",
    "glob": "import glob",
    "shutil": "import shutil",
    "tempfile": "import tempfile",
    
    # System and process
    "subprocess": "import subprocess",
    "platform": "import platform",
    
    # Concurrency
    "threading": "import threading",
    "multiprocessing": "import multiprocessing",
    "asyncio": "import asyncio",
    
    # Data serialization
    "pickle": "import pickle",
    "csv": "import csv",
    "xml": "import xml",
    
    # Database
    "sqlite3": "import sqlite3",
    
    # Network and web
    "urllib": "import urllib",
    "http": "import http",
    "socket": "import socket",
    
    # Cryptography and encoding
    "hashlib": "import hashlib",
    "base64": "import base64",
    "uuid": "import uuid",
    "secrets": "import secrets",
    
    # Utilities
    "logging": "import logging",
    "argparse": "import argparse",
    "configparser": "import configparser",
    "itertools": "import itertools",
    "functools": "import functools",
    "operator": "import operator",
    "warnings": "import warnings",
    "traceback": "import traceback",
    "copy": "import copy",
    "re": "import re",
    "string": "import string",
    
    # Math and statistics
    "statistics": "import statistics",
    "decimal": "import decimal",
    "fractions": "import fractions",
}

# Python standard library modules for checking if a module is built-in
STDLIB_MODULES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio', 'asyncore',
    'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins',
    'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
    'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
    'contextlib', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv', 'ctypes', 'curses',
    'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils', 'doctest', 'email',
    'encodings', 'ensurepip', 'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp',
    'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib', 'functools', 'gc',
    'getopt', 'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq',
    'hmac', 'html', 'http', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect',
    'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3', 'linecache',
    'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes',
    'mmap', 'modulefinder', 'multiprocessing', 'netrc', 'nntplib', 'numbers', 'operator',
    'optparse', 'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools',
    'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'pprint', 'profile',
    'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri',
    'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
    'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil', 'signal',
    'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver', 'sqlite3',
    'ssl', 'stat', 'statistics', 'string', 'stringprep', 'struct', 'subprocess',
    'sunau', 'symbol', 'symtable', 'sys', 'sysconfig', 'tabnanny', 'tarfile',
    'telnetlib', 'tempfile', 'termios', 'test', 'textwrap', 'threading', 'time',
    'timeit', 'tkinter', 'token', 'tokenize', 'trace', 'traceback', 'tracemalloc',
    'tty', 'turtle', 'types', 'typing', 'unicodedata', 'unittest', 'urllib',
    'uu', 'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg',
    'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib'
}

# Multiple import suggestions for ambiguous functions
MULTI_IMPORT_SUGGESTIONS = {
    "dump": [
        "import json  # for json.dump",
        "import pickle  # for pickle.dump",
    ],
    "load": [
        "import json  # for json.load",
        "import pickle  # for pickle.load",
    ],
    "dumps": [
        "import json  # for json.dumps",
        "import pickle  # for pickle.dumps",
    ],
    "loads": [
        "import json  # for json.loads",
        "import pickle  # for pickle.loads",
    ],
}

# Known pip packages for common modules
KNOWN_PIP_PACKAGES = {
    "requests", "numpy", "pandas", "matplotlib", "scipy", "sklearn",
    "tensorflow", "torch", "flask", "django", "fastapi", "sqlalchemy",
    "psycopg2", "pymongo", "redis", "celery", "pytest", "black",
    "flake8", "mypy", "pydantic", "click", "typer", "rich", "tqdm",
    "pillow", "opencv-python", "beautifulsoup4", "lxml", "selenium",
    "openpyxl", "xlsxwriter", "python-dateutil", "pytz", "arrow",
    "cryptography", "bcrypt", "jwt", "passlib", "httpx", "aiohttp",
    "uvicorn", "gunicorn", "streamlit", "dash", "plotly", "seaborn",
    "statsmodels", "networkx", "sympy", "nltk", "spacy", "transformers"
}

# Math functions that need special import
MATH_FUNCTIONS = {
    "sqrt", "sin", "cos", "tan", "log", "exp", "pow", "ceil", "floor", "abs"
}

# Module name to package name mappings for pip installation
MODULE_TO_PACKAGE = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "dateutil": "python-dateutil",
    "jwt": "PyJWT",
    "bs4": "beautifulsoup4",
    "psycopg2": "psycopg2-binary",
    "MySQLdb": "mysqlclient",
    "Image": "Pillow",
    "requests_oauthlib": "requests-oauthlib",
    "google.cloud": "google-cloud",
    "tensorflow": "tensorflow",
    "torch": "torch",
    "torchvision": "torchvision",
    "transformers": "transformers",
    "huggingface_hub": "huggingface-hub",
}
