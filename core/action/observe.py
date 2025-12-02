# -*- coding: utf-8 -*-
"""
Although implemented, this observe is not USED at all yet.
This observe will be fired after action completion, if implemented.
This cause the action to have an immediate validation step followed up.

For example, action that create a folder path will followed by an observation step
to make sure the folder path is created successfully. This create another
layers of validation. 

"""

from typing import Optional, Dict, Any

class Observe:
    """
    Defines how to confirm that an action completed successfully in the real world.
    Observation logic is defined as Python code that executes repeatedly until
    success or timeout is reached.
    """

    def __init__(
        self,
        name: str,                                # e.g. "check_file_created"
        description: Optional[str] = None,
        code: Optional[str] = None,               # Python code to confirm action success
        retry_interval_sec: int = 3,              # Default interval between retries
        max_retries: int = 20,                    # Max number of retries
        max_total_time_sec: int = 60,             # Max total time allowed regardless of retries
        wait_to_observe_sec: Optional[int] = None,  # Optional how long to wait before observing again or after action is completed
        input_schema: Optional[dict] = None,      # e.g. {"file": {"type": "string"}}
        success: Optional[bool] = None,           # Final result of observation
        message: Optional[str] = None             # Optional output message
    ):
        self.name = name
        self.description = description
        self.code = code

        self.retry_interval_sec = retry_interval_sec
        self.max_retries = max_retries
        self.max_total_time_sec = max_total_time_sec
        self.wait_to_observe_sec = wait_to_observe_sec

        self.input_schema = input_schema or {}
        self.success = success
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "code": self.code,
            "retry_interval_sec": self.retry_interval_sec,
            "max_retries": self.max_retries,
            "max_total_time_sec": self.max_total_time_sec,
            "wait_to_observe_sec": self.wait_to_observe_sec,
            "input_schema": self.input_schema,
            "success": self.success,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Observe":
        return cls(
            name=data["name"],
            description=data.get("description"),
            code=data.get("code"),
            retry_interval_sec=data.get("retry_interval_sec", 3),
            max_retries=data.get("max_retries", 20),
            max_total_time_sec=data.get("max_total_time_sec", 600),
            wait_to_observe_sec=data.get("wait_to_observe_sec"),
            input_schema=data.get("input_schema") or {},
            success=data.get("success"),
            message=data.get("message"),
        )
