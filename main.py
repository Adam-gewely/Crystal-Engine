#!/usr/bin/env python3
"""Crystal Engine - Entry Point"""
import sys
import os

# Ensure the engine directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.app import CrystalApp

if __name__ == '__main__':
    app = CrystalApp()
    app.run()
