"""Rebuild the help-docs index: python build_index.py"""
from pulse_agent.rag import build_index

if __name__ == "__main__":
    n = build_index()
    print(f"Index rebuilt with {n} chunks.")
