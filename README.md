# keymap-align

ZMK keymap alignment tool for custom mechanical keyboards. Parses `.keymap` files and aligns bindings according to physical keyboard layout definitions, producing consistently formatted keymaps.

## Overview

keymap-align reads ZMK keymap files and a JSON layout definition, then reformats the `bindings = <...>` blocks so that each key binding aligns to its physical column position on the keyboard. This makes keymaps easier to read and maintain across different layer definitions.

**Supports:**

- Simple bindings: `&kp A`, `&trans`, `&none`
- Multi-parameter behaviors: `&hml LCTRL A`, `&lt 1 SPACE`
- Nested behaviors such as `&hmr &caps_word RALT`, for the behaviors named in `MULTI_PARAM_BEHAVIORS` in `src/keymap_align/align.py`
- Names the keymap file `#define`s to a binding, such as `XXX` for `&none`
- Split keyboard layouts with empty positions
- In-place file modification or separate output

## Installation

Every release is published to a package index of its own:

```bash
uv tool install --index https://pypi.ichrisbirch.com/simple/ keymap-align
```

uv records the index beside the tool, so `uv tool upgrade keymap-align` reads it back.

## Quick Start

```bash
# Align a keymap in place, using a board that ships with the tool
keymap-align -k config/corne.keymap --layout corne42

# Use a layout file of your own, and write to a separate file
keymap-align -k config/glove80.keymap -l my_layout.json -o aligned.keymap

# Debug mode: show the layout and each layer's grid without writing
keymap-align -k config/piantor.keymap --layout piantor --debug
```

`keymap-align --list-layouts` prints the boards that ship with the tool.

## Config File

A `keymap_align.toml` saves passing the layout on every run:

```toml
layout = "corne42"   # a bundled board name, or a path to a layout JSON file
indent_size = 4      # spaces before each binding row
padding = 2          # spaces between columns
```

- The search starts in the keymap file's directory and walks up to the git root, or to the filesystem root outside a repository. The working directory plays no part.
- A `layout` value containing `/` or `\`, or ending in `.json`, is a path. A relative path resolves against the config file's directory. Any other value is a bundled board name.
- `--layout-file` beats `--layout`, and either flag beats the config file.
- `indent_size` and `padding` are set only here. No flag sets them.
- A config file that fails to parse prints a warning, and the run continues without it.

The search lets an editor formatter pass nothing but the keymap. For conform.nvim:

```lua
keymap_align = {
  command = 'keymap-align',
  args = { '-k', '$FILENAME' },
  stdin = false,
},
```

## Layout JSON Format

Layout files define the physical key matrix using `"X"` for key positions and `"-"` for empty spaces:

```json
{
  "name": "Corne 42 Layout",
  "layout": [
    ["X", "X", "X", "X", "X", "X", "-", "-", "X", "X", "X", "X", "X", "X"],
    ["X", "X", "X", "X", "X", "X", "-", "-", "X", "X", "X", "X", "X", "X"],
    ["X", "X", "X", "X", "X", "X", "-", "-", "X", "X", "X", "X", "X", "X"],
    ["-", "-", "-", "-", "X", "X", "X", "X", "X", "X", "-", "-", "-", "-"]
  ]
}
```

The bundled boards are files in this format in `src/keymap_align/layouts/`. Adding a file there adds a board, named by the file stem.

## How It Works

1. **Parse**: Find each layer node inside the keymap's `keymap { … }` node, and read its `bindings` array
2. **Structure**: Place each layer's bindings, in order, into the layout's `"X"` cells
3. **Calculate**: Give each column the width of its widest binding across all layers, plus `padding`
4. **Rewrite**: Replace the text between each array's `<` and `>` with the aligned rows. Each row is indented `indent_size` spaces, and the closing `>` goes on its own line at the indentation of the line holding `bindings`

Everything outside those arrays is kept byte for byte: comments, blank lines, node names, `display-name`, and every other property, such as `sensor-bindings`. A layer with fewer bindings than the layout has keys gets a blank cell for each one missing.

A run exits 1 and writes nothing when the keymap cannot be rewritten without losing text:

- a layer holds more bindings than the layout has keys;
- a `bindings` array holds a comment, or a token that does not belong to any binding, such as an undefined macro name before the first `&`;
- two layer nodes share a name;
- a `bindings` property holds more than one `< >` array.

## Project Structure

```text
keymap-align/
├── src/keymap_align/
│   ├── align.py            # Parsing, column widths and the in-place rewrite
│   ├── cli.py              # CLI entry point
│   ├── config.py           # keymap_align.toml discovery and loading
│   ├── layout_resolver.py  # Flag and config precedence, bundled board lookup
│   └── layouts/            # Bundled board layouts, one JSON file each
└── tests/
    ├── layouts/            # Test layout files
    ├── simple_tests/       # Simple test keymaps
    └── test_keymaps/
        ├── correct/        # Reference output files, compared byte for byte
        └── misaligned/     # Test input files
```

## Development

```bash
git clone https://github.com/datapointchris/keymap-align
cd keymap-align
uv sync --all-groups
uv run pre-commit install

# Run tests
uv run pytest

# Code quality
uv run ruff check src/
uv run ruff format src/
uv run mypy src/

# Pre-commit (runs all checks)
uv run pre-commit run --all-files
```

## License

MIT License
