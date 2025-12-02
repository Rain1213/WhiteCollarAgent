# -*- coding: utf-8 -*-
"""
core.main

Main driver code that starts the **vanilla BaseAgent**.
Environment variables let you tweak connection details without code
changes, making this usable inside Docker containers.

Run this before the core directory, using 'python -m core.main'
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from core.agent_base import AgentBase


def main() -> None:
    agent = AgentBase(
        data_dir=os.getenv("DATA_DIR", "core/data"),
        chroma_path=os.getenv("CHROMA_PATH", "./chroma_db"),
    )
    asyncio.run(agent.run())


if __name__ == "__main__":
    main()
