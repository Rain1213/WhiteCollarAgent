# -*- coding: utf-8 -*-
"""
core.event_stream.event_stream_manager.

Event stream manager that manages, stores, return concurrent event streams 
running under several active tasks.

"""


from __future__ import annotations
from pathlib import Path
from typing import Dict, Optional
from core.event_stream.event_stream import EventStream
from core.llm_interface import LLMInterface
from core.logger import logger

class EventStreamManager:
    def __init__(self, llm: LLMInterface) -> None:
        # active event streams, keyed by session_id (string)
        self.active: Dict[str, EventStream] = {}
        self.llm = llm

    # ───────────────────────────── lifecycle ─────────────────────────────

    def create_stream(self, session_id: str, *, temp_dir: Path | None = None) -> EventStream:
        """
        Create a new event stream for a given session_id.
        If it already exists, overwrite with a fresh one.
        """
        stream = EventStream(session_id=session_id, llm=self.llm, temp_dir=temp_dir)
        self.active[session_id] = stream
        return stream

    def get_stream(self, session_id: str) -> Optional[EventStream]:
        """Return the event stream for this session, or None if missing."""
        return self.active.get(session_id)

    def remove_stream(self, session_id: str) -> None:
        """Remove and discard a stream."""
        self.active.pop(session_id, None)

    def clear_all(self) -> None:
        """Remove all event streams."""
        self.active.clear()

    # ───────────────────────────── utilities ─────────────────────────────

    def log(
        self,
        session_id: str,
        kind: str,
        message: str,
        severity: str = "INFO",
        *,
        display_message: str | None = None,
        action_name: str | None = None,
    ) -> int:
        """
        Convenience: log directly to a session's event stream.
        Creates the stream if it does not exist.
        Returns the index of the logged event.
        """
        logger.debug(f"Process Started - Logging event to stream {session_id}: [{severity}] {kind} - {message}")
        stream = self.get_stream(session_id)
        if not stream:
            logger.debug(f"No existing stream for {session_id}. Creating new stream.")
            stream = self.create_stream(session_id)
            logger.debug(f"Created new stream: {stream}")
        return stream.log(
            kind,
            message,
            severity,
            display_message=display_message,
            action_name=action_name,
        )

    def snapshot(self, session_id: str, max_events: int = 60, include_summary: bool = True) -> str:
        """Return a prompt snapshot of a specific session, or '(no events)' if not found."""
        stream = self.get_stream(session_id)
        if not stream:
            return "(no events)"
        return stream.to_prompt_snapshot(max_events=max_events, include_summary=include_summary)

    def snapshot_all(self, max_events: int = 30) -> Dict[str, str]:
        """
        Return prompt snapshots for all active streams.
        Useful for debugging or dashboarding.
        """
        return {sid: s.to_prompt_snapshot(max_events=max_events) for sid, s in self.active.items()}
