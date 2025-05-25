# Nodetool Apple Nodes

Nodetool-Apple provides a collection of nodes that let you automate macOS
applications from [Nodetool](https://github.com/nodetool-ai/nodetool).  The
project exposes Python classes and a DSL so that workflows can interact with
built‑in Apple apps like Calendar, Notes, Messages or the Dictionary.

## Features

The package currently implements the following nodes:

- **Calendar** – create events or list events from Apple Calendar
- **Dictionary** – look up definitions in the macOS Dictionary app
- **Messages** – send iMessage messages via AppleScript
- **Notes** – create notes or read notes from the Notes app
- **Reminders** – create reminders using Reminders.app
- **Screen** – capture screenshots of the current display
- **Speech** – speak text using the system text‑to‑speech voices

Each node follows the `BaseNode` API from `nodetool-core` and can therefore be
used like any other workflow node.

## Installation

```bash
pip install nodetool-apple
```

The package requires Python 3.11 or later.  On macOS the optional PyObjC
dependencies are installed automatically and are needed for the nodes that use
Apple frameworks.

## Basic Example

```python
from nodetool.workflows.processing_context import ProcessingContext
from nodetool.nodes.apple.notes import CreateNote

context = ProcessingContext()
node = CreateNote(title="Demo Note", body="Created from Nodetool")
await node.process(context)
```

For more involved scenarios take a look at the example workflow in
`src/nodetool/examples/nodetool-apple/`.

## Development

After adding or modifying nodes run the following commands to update metadata and DSL files:

```bash
nodetool package scan
nodetool codegen
```

Before submitting patches make sure the linters and tests succeed:

```bash
ruff check .
black --check .
pytest -q
```

## License

This project is distributed under the terms of the GNU Affero General Public
License v3.0. See the [LICENSE](LICENSE) file for details.
