import datetime
from typing import Optional, List, Dict, Any
from core.action.observe import Observe

# ------------------------------
# Action Class
# ------------------------------
class Action:
    """
    Defines an action that the agent can execute.
    Actions can be atomic (directly executable) or hierarchical (contain sub-actions).
    """

    def __init__(
        self,
        name: str,
        description: str,
        action_type: str,
        code: Optional[str] = None,
        mode: Optional[str] = None,
        input_schema: Optional[dict] = None,   # e.g. {"a": {"type": "integer", "example": 2, "description": "First number"}}
        output_schema: Optional[dict] = None,  # e.g. {"result": {"type": "integer", "example": 5, "description": "Sum of a and b"}}
        sub_actions: Optional[List["Action"]] = None,
        observer: Optional[Observe] = None,
        last_use: bool = None,
        default: bool = False,
        platforms: List[str] = ["windows", "linux", "darwin"],
        platform_overrides: dict[str, dict] = {}
    ):
        self.name = name
        self.description = description
        self.action_type = action_type
        self.code = code  # For atomic actions; if 'divisible', use sub_actions instead

        self.platforms: List[str] = platforms  # Platforms where this action is applicable
        self.platform_overrides: dict[str, dict] = platform_overrides  # Platform-specific overrides for code or schemas

        # Keep input/output_schema as plain dictionaries without "properties" or "required"
        self.input_schema = input_schema or {}
        self.output_schema = output_schema or {}

        self.sub_actions = sub_actions or []
        self.observer = observer 
        self.created_at = datetime.datetime.utcnow().isoformat()
        self.updated_at = self.created_at
        self.last_use = last_use
        self.default = default  
        self.mode = mode

    def to_dict(self):
        """Convert Action to a dictionary format (for database storage)."""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.action_type,
            "code": self.code,
            "mode": self.mode,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "subActions": [sub_action.to_dict() for sub_action in self.sub_actions],
            "observer": self.observer.to_dict() if self.observer else None,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
            "lastUse": self.last_use,
            "default": self.default,
            "platforms": self.platforms,
            "platform_overrides": self.platform_overrides
        }

    @classmethod
    def from_dict(cls, data):
        """Create an Action object from a dictionary (used when loading from DB)."""
        sub_actions = [cls.from_dict(sub) for sub in data.get("subActions", [])]
        observer_data = data.get("observer")
        observer = Observe.from_dict(observer_data) if observer_data else None

        # Fallback logic for older fields if input_schema/output_schema not present
        input_schema = data.get("input_schema") or data.get("input") or {}
        output_schema = data.get("output_schema") or data.get("expected_output") or data.get("expected_output_schema") or {}

        data_to_return = cls(
            name=data["name"],
            description=data["description"],
            action_type=data["type"],
            code=data.get("code"),
            mode=data.get("mode", ""),
            input_schema=input_schema,
            output_schema=output_schema,
            sub_actions=sub_actions,
            observer=observer,
            default=data.get("default", False) ,
            platforms=data.get("platforms", ["windows", "linux", "darwin"]),
            platform_overrides=data.get("platform_overrides", {})
        )

        return data_to_return

