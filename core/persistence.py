import json
import os
import datetime
from typing import Dict, Any

PAPER_DATA_FILE = "paper_data.json"

class PersistenceManager:
    @staticmethod
    def save_paper_state(state: Dict[str, Any]):
        try:
            with open(PAPER_DATA_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"[PERSISTENCE] Save Error: {e}")

    @staticmethod
    def load_paper_state() -> Dict[str, Any]:
        if not os.path.exists(PAPER_DATA_FILE):
            return {}
        try:
            with open(PAPER_DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[PERSISTENCE] Load Error: {e}")
            return {}

    @staticmethod
    def reset_paper_state():
        if os.path.exists(PAPER_DATA_FILE):
            try:
                os.remove(PAPER_DATA_FILE)
            except Exception as e:
                print(f"[PERSISTENCE] Reset Error: {e}")
