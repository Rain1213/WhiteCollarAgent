# core/action/action_framework/registry.py
import functools
import platform as platform_lib
from typing import List, Dict, Any, Optional, Callable, Union
from dataclasses import dataclass, field
import logging
import inspect
import textwrap

# Setup basic logging
logger = logging.getLogger("ActionRegistry")
# logger.setLevel(logging.INFO)

# Standard platform identifiers
PLATFORM_ALL = "all"
PLATFORM_LINUX = "linux"
PLATFORM_WINDOWS = "windows"
PLATFORM_DARWIN = "darwin" # macOS

@dataclass
class ActionMetadata:
    """Holds configuration data defining the action contract."""
    name: str
    description: str = ""
    # Platforms this specific implementation supports.
    # Defaults to [PLATFORM_ALL] if not specified.
    platforms: List[str] = field(default_factory=lambda: [PLATFORM_ALL])
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    requirements: List[str] = field(default_factory=list)
    test_payload: Optional[Dict[str, Any]] = None

@dataclass
class RegisteredAction:
    """Combines the actual Python callable with its metadata."""
    handler: Callable[..., Dict[str, Any]]
    metadata: ActionMetadata

class ActionRegistry:
    """Singleton registry to hold all discovered actions."""
    _instance = None
    
    # Storage Structure: 
    # { 
    #   "logical_action_name": { 
    #       "linux": RegisteredAction(...),
    #       "windows": RegisteredAction(...),
    #       "all": RegisteredAction(...)
    #   } 
    # }
    _registry: Dict[str, Dict[str, RegisteredAction]] = {}

    def __new__(cls):
        # Ensure singleton pattern
        if cls._instance is None:
            cls._instance = super(ActionRegistry, cls).__new__(cls)
        return cls._instance

    def register(self, action_def: RegisteredAction):
        """Registers an action implementation for its specified platforms."""
        name = action_def.metadata.name
        
        if name not in self._registry:
            self._registry[name] = {}
            
        for platform in action_def.metadata.platforms:
            platform_key = platform.lower()
            
            if platform_key in self._registry[name]:
                 logger.warning(f"Overwriting existing action implementation for '{name}' on platform '{platform_key}'")
            
            self._registry[name][platform_key] = action_def
            logger.debug(f"Registered '{name}' for platform: '{platform_key}'")

    def get_action_implementation(self, name: str, target_platform: Optional[str] = None) -> Optional[RegisteredAction]:
        """
        Retrieves the best fit action implementation.
        1. Looks for exact platform match (e.g., 'linux').
        2. Falls back to generic 'all' match.
        """
        if name not in self._registry:
            return None
        
        platform_impls = self._registry[name]
        
        # Detect OS if not provided
        if target_platform is None:
            target_platform = platform_lib.system().lower()
        else:
            target_platform = target_platform.lower()
        
        # 1. Try specific platform match first
        if target_platform in platform_impls:
            return platform_impls[target_platform]
        
        # 2. Fallback to generic implementation
        if PLATFORM_ALL in platform_impls:
            return platform_impls[PLATFORM_ALL]
            
        # 3. No suitable implementation found
        return None

    def get_testable_actions(self, target_platform: Optional[str] = None) -> List[RegisteredAction]:
        """
        Returns a list of unique action implementations that run on the current OS
        AND have valid test_payload data configured for simulation.
        """
        if target_platform is None:
            target_platform = platform_lib.system().lower()

        testable_actions = []
        
        for logical_name in self._registry.keys():
            # Find the best implementation for this OS
            impl = self.get_action_implementation(logical_name, target_platform)
            
            # 1. Check if implementation exists and has test payload configured
            if impl and impl.metadata.test_payload is not None:
                payload = impl.metadata.test_payload
                
                # 2. Inspect the payload. If 'simulated_mode' is explicitly False, skip this test.
                # We use .get() and default to True to ensure tests run unless explicitly disabled.
                is_simulated = payload.get("simulated_mode", True)
                
                if is_simulated is False:
                     logger.debug(f"Skipping test for action '{impl.metadata.name}' because simulated_mode is False.")
                     continue
                
                testable_actions.append(impl)
                
        return testable_actions

    def list_all_actions(self) -> Dict[str, Any]:
        """Returns the entire registry structure for inspection."""
        return self._registry

    def list_all_actions_as_json(self) -> List[Dict[str, Any]]:
        """
        Returns the registry flattened into JSON-compatible dictionaries matching legacy requirements.
        It extracts the actual source code of the functions using the 'inspect' module.
        """
        current_os = platform_lib.system().lower()
        json_actions_list = []
        
        for logical_name, platform_impls in self._registry.items():
            action_json = self._get_action_as_json(platform_impls=platform_impls)
            json_actions_list.append(action_json)
            
        return json_actions_list

    def find_action_by_name(self, action_name: str) -> Dict[str, Any]:
        if action_name not in self._registry:
            return None
        
        current_os = platform_lib.system().lower()
        platform_impls = self._registry[action_name]

        return self._get_action_as_json(platform_impls=platform_impls)

    def _get_action_as_json(self, platform_impls) -> Dict[str, Any]:
        main_impl = platform_impls.get(current_os)
        if not main_impl:
            main_impl = platform_impls.get(PLATFORM_ALL)
        if not main_impl:
            main_impl = next(iter(platform_impls.values()))

        meta = main_impl.metadata

        # 1. Extract source code for the main implementation
        try:
            # getsource returns the raw code, including indentation
            raw_code = inspect.getsource(main_impl.handler)
            # dedent removes leading common whitespace to make it clean
            main_code_str = textwrap.dedent(raw_code)
        except Exception as e:
            logger.error(f"Could not extract source for action '{logical_name}': {e}")
            main_code_str = f"# Error extracting source code: {e}"


        # 2. Build the base JSON structure with required hardcoded fields
        action_json = {
            # Note: "_id" omitted so DB generates it.
            "name": meta.name,
            "description": meta.description,
            # --- HARDCODED REQUIREMENTS ---
            "type": "atomic",
            "execution_mode": "internal",
            "scope": ["global"],
            "default": False,
            # -----------------------------
            "platforms": list(platform_impls.keys()),
            "input_schema": meta.input_schema,
            "output_schema": meta.output_schema,
            "requirements": meta.requirements,
            # The extracted source code string
            "code": main_code_str,
            "platform_overrides": {}
        }

        # 3. Handle Platform Overrides
        for platform_key, impl in platform_impls.items():
            # Skip the implementation we used for the main code block so it's not redundant
            if impl == main_impl:
                continue
            
            try:
                override_raw = inspect.getsource(impl.handler)
                override_code_str = textwrap.dedent(override_raw)
                
                action_json["platform_overrides"][platform_key] = {
                    "code": override_code_str
                }
            except Exception as e:
                    logger.warning(f"Could not extract override source for {logical_name} on {platform_key}: {e}")

        # Clean up empty overrides dict if unused
        if not action_json["platform_overrides"]:
            del action_json["platform_overrides"]

        return action_json

# Global singleton instance used by the decorator and the main app
registry_instance = ActionRegistry()

# ==========================================
# The Decorator Implementation
# ==========================================
def action(
    name: str,
    description: str = "",
    platforms: Union[str, List[str], None] = None,
    input_schema: Optional[Dict[str, Any]] = None,
    output_schema: Optional[Dict[str, Any]] = None,
    requirement: Optional[List[str]] = None,
    test_payload: Optional[Dict[str, Any]] = None
):
    """
    Decorator used by developers to register functions as actions.
    This runs at import time, populating the registry.
    """
    # Normalize platforms input to a list of lowercase strings
    if platforms is None:
        # If not specified, assume it works everywhere
        platform_list = [PLATFORM_ALL]
    elif isinstance(platforms, str):
        platform_list = [platforms.lower()]
    else:
        platform_list = [p.lower() for p in platforms]

    def decorator_factory(func: Callable):
        # 1. Create the metadata object from decorator arguments
        metadata = ActionMetadata(
            name=name,
            description=description,
            platforms=platform_list,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            requirements=requirement or [],
            test_payload=test_payload
        )
        
        # 2. Create the full registration object
        action_definition = RegisteredAction(
            handler=func,
            metadata=metadata
        )

        # 3. Register immediately with the singleton instance upon import
        registry_instance.register(action_definition)

        # 4. Return the original function unmodified.
        # (We use wraps to keep the original function's name/docstring available)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator_factory