#!/usr/bin/env python3
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from bot.main import main

if __name__ == "__main__":
    main()
