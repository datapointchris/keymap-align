# keymap-align

ZMK keymap alignment tool for custom mechanical keyboards. Parses `.keymap` files and aligns bindings according to physical keyboard layout definitions, producing consistently formatted keymaps.

## Overview

keymap-align reads ZMK keymap files and a JSON layout definition, then reformats the `bindings = <...>` blocks so that each key binding aligns to its physical column position on the keyboard. This makes keymaps easier to read and maintain across different layer definitions.

**Supports:**

- Simple bindings: `&kp A`, `&trans`, `&none`
- Multi-parameter behaviors: `&hml LCTRL A`, `&lt 1 SPACE`
- Nested behaviors: `&hmr &caps_word RALT`
- Display-name preservation: `display-name = "BASE";`
- Split keyboard layouts with empty positions
- In-place file modification or separate output

## Installation

```bash
# Install with uv (recommended)
uv tool install keymap-align

# Or install from source
cd ~/code/keymap-align
uv sync --all-groups
uv run pre-commit install
```

## Quick Start

```bash
# Align a keymap in-place
keymap-align -k config/corne.keymap -l corne_layout.json

# Align to a separate output file
keymap-align -k config/glove80.keymap -l glove80_layout.json -o aligned.keymap

# Debug mode: visualize layout and bindings without writing
keymap-align -k config/piantor.keymap -l piantor_layout.json --debug
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

## How It Works

1. **Parse**: Extract all layers and their bindings from the `.keymap` file
2. **Structure**: Map bindings to physical positions using the layout matrix
3. **Calculate**: Determine optimal column widths across all layers
4. **Format**: Rewrite the keymap section with aligned columns (2-space padding)
5. **Preserve**: Everything outside `bindings = <...>` blocks is kept unchanged

## Project Structure

```text
keymap-align/
├── src/keymap_align/
│   ├── __init__.py
│   ├── align.py          # Core alignment library
│   └── cli.py            # CLI entry point
└── tests/
    ├── test_align_keymap.py              # Main test suite (28 tests)
    ├── test_display_name_preservation.py # Display-name tests (7 tests)
    ├── test_data.py                      # Test fixtures
    ├── layouts/                          # Test layout files
    ├── simple_tests/                     # Simple test keymaps
    └── test_keymaps/
        ├── correct/                      # Reference output files
        └── misaligned/                   # Test input files
```

## Development

```bash
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
