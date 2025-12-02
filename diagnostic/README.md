# Action Diagnostics

The diagnostic toolkit exercises individual Craft Agent actions in isolated test
sandboxes. Each action has a dedicated environment script that prepares
fixtures, assembles realistic input parameters, runs the action implementation,
and validates the produced output.

## Prerequisites

- Python 3.10+
- Project dependencies installed (recommended: `pip install -e .` or follow
the root-level setup instructions)

The diagnostic utilities only rely on the repository codebase, so no external
services are contacted while running the included scenarios.

## Usage

Run the CLI from the project root:

```bash
python diagnostic/action_diagnose.py --list
```

### Execute all available scenarios

```bash
python diagnostic/action_diagnose.py --all
```

### Execute specific actions

Supply `--action` multiple times to target one or more actions:

```bash
python diagnostic/action_diagnose.py --action "list folder" --action "read pdf file"
```

A summary of the run is printed to the console. Detailed execution artefacts are
stored in `diagnostic/logs/actions` as timestamped `.log.json` files capturing
the inputs, raw outputs, parsed payloads, and any exceptions.

## Adding new scenarios

1. Create a module inside `diagnostic/environments/` and implement a
   `get_test_case()` function that returns an `ActionTestCase` instance.
2. Use the helper utilities in `diagnostic/framework.py` to build the execution
   sandbox, craft inputs, and validate outputs.
3. The CLI automatically discovers new modules, so rerunning `--list` or
   `--all` will pick up your scenario.

## Troubleshooting

- Ensure the repository dependencies are installed and up to date.
- Delete stale artefacts from `diagnostic/logs/actions` if you want a clean run.
- Pass `--action` only for actions that have implemented environment scripts;
  otherwise the CLI reports them as `skip`.
