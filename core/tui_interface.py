"""Textual-based terminal user interface for interacting with the agent."""
from __future__ import annotations

import asyncio
from asyncio import Queue, QueueEmpty
from dataclasses import dataclass
from typing import Tuple

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import var
from inspect import signature

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Input, Static
from textual.widgets import RichLog as _BaseLog

from core.logger import logger
if False:  # pragma: no cover
    from core.agent_base import AgentBase  # type: ignore

class _ConversationLog(_BaseLog):
    """RichLog wrapper with robust wrapping + reflow on resize."""

    def __init__(self, *args, **kwargs) -> None:
        # RichLog params: wrap off by default, min_width=78; override both
        kwargs.setdefault("markup", True)
        kwargs.setdefault("highlight", False)
        kwargs.setdefault("wrap", True)        # enable word-wrapping (RichLog)
        kwargs.setdefault("min_width", 1)      # let width track the pane size
        super().__init__(*args, **kwargs)

    def append_text(self, content) -> None:
        # Normalize to Rich Text, enable folding of long tokens
        text: Text = content if isinstance(content, Text) else Text(str(content))
        text.no_wrap = False
        text.overflow = "fold"                 # split unbreakable runs (URLs / IDs)
        self.append_renderable(text)

    def append_markup(self, markup: str) -> None:
        self.append_text(Text.from_markup(markup))

    def append_renderable(self, renderable: RenderableType) -> None:
        # Write using expand/shrink so width follows the widget on resize
        self.write(renderable, expand=True, shrink=True)


TimelineEntry = Tuple[str, str, str]


@dataclass
class _ActionEntry:
    """Container for agent action updates."""

    kind: str
    message: str
    style: str = "action"


class _CraftApp(App):
    """Textual application rendering the Craft Agent TUI."""

    CSS = """
    Screen {
        layout: vertical;
        background: #111111;
        color: #f5f5f5;
    }

    #top-region {
        height: 1fr;
    }

    #chat-panel, #action-panel {
        height: 100%;
        border: solid #444444;
        border-title-align: left;
        margin: 0 1;
    }
    
    #chat-log, #action-log {
        text-wrap: wrap;        /* word wrap (default, but make it explicit) */
        text-overflow: fold;    /* fold long unbreakable tokens onto next line */
        overflow-x: hidden;     /* no horizontal scrollbar */
    }

    #chat-panel {
        width: 2fr;
    }

    #action-panel {
        width: 1fr;
    }

    /* Ensure logs size to the container without horizontal overflow */
    TextLog {
        height: 1fr;
        padding: 0 1;
        overflow-x: hidden;   /* hide horizontal scrollbar if any */
    }

    /* Explicitly enable wrapping inside both logs */
    #chat-log, #action-log {
        text-wrap: wrap;      /* force wrapping at widget width */
        overflow-x: hidden;   /* no horizontal scrolling */
    }

    #bottom-region {
        height: auto;
        border-top: solid #333333;
        padding: 1;
    }

    #status-bar {
        height: 1;
        min-height: 1;
        text-wrap: nowrap;
        overflow: hidden;
        text-style: bold;
        color: #dddddd;
    }

    #chat-input {
        border: solid #444444;
        background: #1a1a1a;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
    ]

    status_text = var("Status: Idle")

    _STATUS_PREFIX = "Status: "
    _STATUS_GAP = 4
    _STATUS_INITIAL_PAUSE = 6

    def __init__(self, interface: "TUIInterface") -> None:
        super().__init__()
        self._interface = interface
        self._status_message: str = "Idle"
        self._status_offset: int = 0
        self._status_pause: int = self._STATUS_INITIAL_PAUSE
        self._last_rendered_status: str = ""


    def compose(self) -> ComposeResult:  # pragma: no cover - declarative layout
        yield Container(
            Horizontal(
                Container(
                    _ConversationLog(id="chat-log"),
                    id="chat-panel",
                ),
                Container(
                    _ConversationLog(id="action-log"),
                    id="action-panel",
                ),
                id="top-region",
            ),
            Vertical(
                Static(
                    Text(self.status_text, no_wrap=True, overflow="crop"),
                    id="status-bar",
                ),
                Input(placeholder="Type a message and press Enter…", id="chat-input"),
                id="bottom-region",
            ),
        )

    async def on_mount(self) -> None:  # pragma: no cover - UI lifecycle
        chat_input = self.query_one("#chat-input", Input)
        chat_input.focus()
        
        self.query_one("#chat-panel").border_title = "Chat"
        self.query_one("#action-panel").border_title = "Action"
        
        # Runtime safeguard: enforce wrapping on the logs even if CSS/props vary by version
        chat_log = self.query_one("#chat-log", _ConversationLog)
        action_log = self.query_one("#action-log", _ConversationLog)

        chat_log.styles.text_wrap = "wrap"
        action_log.styles.text_wrap = "wrap"
        chat_log.styles.text_overflow = "fold"
        action_log.styles.text_overflow = "fold"

        self.set_interval(0.1, self._flush_pending_updates)
        self.set_interval(0.2, self._tick_status_marquee)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        message = event.value.strip()
        event.input.value = ""
        await self._interface.submit_user_message(message)

    async def action_quit(self) -> None:  # pragma: no cover - user-triggered
        await self._interface.request_shutdown()
        await super().action_quit()

    def _flush_pending_updates(self) -> None:
        chat_log = self.query_one("#chat-log", _ConversationLog)
        action_log = self.query_one("#action-log", _ConversationLog)
        while True:
            try:
                label, message, style = self._interface.chat_updates.get_nowait()
            except QueueEmpty:
                break
            entry = self._interface.format_chat_entry(label, message, style)
            chat_log.append_renderable(entry)

        while True:
            try:
                action = self._interface.action_updates.get_nowait()
            except QueueEmpty:
                break
            entry = self._interface.format_action_entry(action)
            action_log.append_renderable(entry)

        while True:
            try:
                status = self._interface.status_updates.get_nowait()
            except QueueEmpty:
                break
            self._set_status(status)

    async def on_shutdown_request(self, event: events.ShutdownRequest) -> None:
        await self._interface.request_shutdown()

    def _set_status(self, status: str) -> None:
        self._status_message = status
        self._status_offset = 0
        self._status_pause = self._STATUS_INITIAL_PAUSE
        self._render_status()

    def _tick_status_marquee(self) -> None:
        status_bar = self.query_one("#status-bar", Static)
        width = status_bar.size.width or self.size.width or (
            len(self._STATUS_PREFIX) + len(self._status_message)
        )
        available = max(0, width - len(self._STATUS_PREFIX))

        if available <= 0 or len(self._status_message) <= available:
            self._status_offset = 0
            self._status_pause = self._STATUS_INITIAL_PAUSE
        else:
            if self._status_pause > 0:
                self._status_pause -= 1
            else:
                scroll_span = len(self._status_message) + self._STATUS_GAP
                self._status_offset = (self._status_offset + 1) % scroll_span
                if self._status_offset == 0:
                    self._status_pause = self._STATUS_INITIAL_PAUSE

        self._render_status()

    def _render_status(self) -> None:
        status_bar = self.query_one("#status-bar", Static)
        width = status_bar.size.width or self.size.width or (
            len(self._STATUS_PREFIX) + len(self._status_message)
        )
        available = max(0, width - len(self._STATUS_PREFIX))
        visible = self._visible_status_content(available)
        full_text = f"{self._STATUS_PREFIX}{visible}"

        if full_text == self._last_rendered_status:
            return

        self.status_text = full_text
        status_bar.update(Text(full_text, no_wrap=True, overflow="crop"))
        self._last_rendered_status = full_text

    def _visible_status_content(self, available: int) -> str:
        if available <= 0:
            return ""
        message = self._status_message
        if len(message) <= available:
            return message

        scroll_span = len(message) + self._STATUS_GAP
        start = self._status_offset % scroll_span
        extended = message + " " * self._STATUS_GAP

        segment_chars = []
        for idx in range(available):
            segment_chars.append(extended[(start + idx) % scroll_span])
        return "".join(segment_chars)


class TUIInterface:
    """Asynchronous Textual TUI driver that feeds user prompts to the agent."""

    _STYLE_COLORS = {
        "user": "bold plum1",
        "agent": "bold gold1",
        "action": "bold deep_sky_blue1",
        "task": "bold dark_orange",
        "error": "bold red",
        "info": "bold grey70",
        "system": "bold medium_orchid",
    }

    _CHAT_LABEL_WIDTH = 7
    _ACTION_LABEL_WIDTH = 7

    def __init__(self, agent: "AgentBase") -> None:
        self._agent = agent
        self._running: bool = False
        self._tracked_sessions: set[str] = set()
        self._seen_events: set[Tuple[str, str, str, str]] = set()
        self._status_message: str = "Idle"
        self._app: _CraftApp | None = None
        self._event_task: asyncio.Task[None] | None = None

        self.chat_updates: Queue[TimelineEntry] = Queue()
        self.action_updates: Queue[_ActionEntry] = Queue()
        self.status_updates: Queue[str] = Queue()

    async def start(self) -> None:
        """Start the Textual TUI session and background consumers."""
        if self._running:
            return

        self._running = True
        logger.debug("Starting Textual TUI interface. Press Ctrl+C to exit.")

        await self.chat_updates.put(
            ("System", "White Collar Agent TUI ready. Type '/exit' to finish.", "system")
        )
        await self.status_updates.put(self._status_message)

        trigger_consumer = asyncio.create_task(self._consume_triggers())
        self._event_task = asyncio.create_task(self._watch_events())

        self._app = _CraftApp(self)

        try:
            await self._app.run_async()
        finally:
            self._running = False
            self._agent.is_running = False

            trigger_consumer.cancel()
            try:
                await trigger_consumer
            except asyncio.CancelledError:  # pragma: no cover - event loop teardown
                pass

            if self._event_task:
                self._event_task.cancel()
                try:
                    await self._event_task
                except asyncio.CancelledError:  # pragma: no cover - event loop teardown
                    pass

    async def submit_user_message(self, message: str) -> None:
        """Handle chat input captured by the Textual app."""
        if not message:
            return

        lowered = message.lower()
        if lowered in {"/exit"}:
            await self.chat_updates.put(("System", "Session terminated by user.", "system"))
            await self.status_updates.put("Idle")
            await self.request_shutdown()
            return

        await self.chat_updates.put(("You", message, "user"))
        await self.status_updates.put("Awaiting agent response…")

        payload = {
            "text": message,
            "sender": {"id": "cli_user", "type": "user"},
            "gui_mode": False,
        }
        await self._agent._handle_chat_message(payload)

    async def request_shutdown(self) -> None:
        """Stop the interface and close the Textual application."""
        if not self._running:
            return

        self._running = False
        self._agent.is_running = False

        if self._app and self._app.is_running:
            self._app.exit()

    async def _consume_triggers(self) -> None:
        """Continuously consume triggers and hand them to the agent."""
        try:
            while self._agent.is_running:
                trigger = await self._agent.triggers.get()
                if trigger.session_id:
                    self._tracked_sessions.add(trigger.session_id)
                await self._agent.react(trigger)
        except asyncio.CancelledError:  # pragma: no cover - event loop teardown
            raise

    async def _watch_events(self) -> None:
        """Refresh the conversation timeline with agent actions."""
        try:
            while self._running and self._agent.is_running:
                for session_id in list(self._tracked_sessions):
                    stream = self._agent.event_stream_manager.get_stream(session_id)
                    if not stream:
                        continue
                    for event in stream.as_list():
                        key = (session_id, event.iso_ts, event.kind, event.message)
                        if key in self._seen_events:
                            continue
                        self._seen_events.add(key)

                        # Screen events are consumed by GUI clients; skip showing
                        # them in the TUI to avoid the "Screen summary updated"
                        # marker while still keeping the markdown in the event
                        # stream for other consumers.
                        if event.kind == "screen":
                            continue

                        style = self._style_for_event(event.kind, event.severity)
                        label = self._label_for_style(style, event.kind)
                        display_text = event.display_text()

                        if style in {"action", "task"}:
                            await self._handle_action_event(
                                event.kind, display_text, style=style
                            )
                            continue

                        if style not in {"agent", "system", "user", "error", "info"}: 
                            continue

                        if display_text is not None:
                            await self.chat_updates.put((label, display_text, style))

                await asyncio.sleep(0.05)
        except asyncio.CancelledError:  # pragma: no cover - event loop teardown
            raise

    async def _handle_action_event(
        self, kind: str, message: str, *, style: str = "action"
    ) -> None:
        """Record an action update and refresh the status bar."""
        await self.action_updates.put(
            _ActionEntry(kind=kind, message=message, style=style)
        )
        if style == "action":
            status = self._derive_status(kind, message)
            if status != self._status_message:
                self._status_message = status
                await self.status_updates.put(status)

    def _derive_status(self, kind: str, message: str) -> str:
        normalized = message.strip() or ""
        if kind == "action_start":
            return f"Running: {normalized or 'action in progress'}"
        if kind == "action_end":
            return f"Completed: {normalized or 'last action'}"
        if kind == "action":
            return normalized or "Action in progress"
        return normalized or self._status_message or "Idle"

    def _format_labelled_entry(
        self,
        label_text: str,
        message: Text | str,
        *,
        colour: str,
        label_width: int,
    ) -> Table:
        table = Table.grid(padding=(0, 1))
        table.expand = True
        table.add_column(
            "label",
            width=label_width,
            min_width=label_width,
            max_width=label_width,
            style=colour,
            no_wrap=True,
            justify="left",
        )
        table.add_column("message", ratio=1)

        label_cell = Text(label_text, style=colour, no_wrap=True)
        message_text = message if isinstance(message, Text) else Text(str(message))
        message_text.no_wrap = False
        message_text.overflow = "fold"

        table.add_row(label_cell, message_text)

        return table

    def format_chat_entry(self, label: str, message: str, style: str) -> RenderableType:
        colour = self._STYLE_COLORS.get(style, self._STYLE_COLORS["info"])
        label_text = f"{label}:"
        return self._format_labelled_entry(
            label_text,
            message,
            colour=colour,
            label_width=self._CHAT_LABEL_WIDTH,
        )

    def format_action_entry(self, entry: _ActionEntry) -> RenderableType:
        kind = entry.kind.replace("_", " ").title()
        colour = "bold deep_sky_blue1" if entry.style == "action" else "bold dark_orange"
        label_text = f"{kind}:"
        return self._format_labelled_entry(
            label_text,
            entry.message,
            colour=colour,
            label_width=self._ACTION_LABEL_WIDTH,
        )

    def _style_for_event(self, kind: str, severity: str) -> str:
        if severity.upper() == "ERROR":
            return "error"
        if kind == "system":
            return "system"
        if kind.startswith("task"):
            return "task"
        if kind in {"action", "action_start", "action_end"}:
            return "action"
        if kind in {"screen", "info", "note"}:
            return "info"
        if kind == "user":
            return "user"
        return "agent"

    @staticmethod
    def _label_for_style(style: str, kind: str) -> str:
        if style == "agent":
            return "Agent"
        if style == "system":
            return "System"
        if style == "user":
            return "You"
        if style == "error":
            return "Error"
        if style == "task":
            return kind.replace("_", " ").title()
        if style == "info":
            return kind.replace("_", " ").title()
        return kind.title()
