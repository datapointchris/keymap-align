import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from keymap_align.config import DEFAULT_INDENT_SIZE
from keymap_align.config import DEFAULT_PADDING


class Colors:
    """ANSI Color codes for terminal output."""

    RESET = '\033[0m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    ORANGE = '\033[38;5;208m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    PURPLE = '\033[95m'
    MAGENTA = '\033[38;5;198m'
    GRAY = '\033[90m'
    BRIGHT_GREEN = '\033[38;5;46m'


DIMMED_BEHAVIORS = {'&none', '&trans'}
KEYPRESS_BEHAVIORS = {'&kp'}
STOCK_ZMK_BEHAVIORS = {
    '&lt',
    '&mt',
    '&mo',
    '&to',
    '&tog',
    '&sl',
    '&sk',
    '&caps_word',
    '&bt',
    '&rgb_ug',
    '&sys_reset',
    '&bootloader',
    '&out',
    '&mkp',
    '&mmv',
    '&msc',
    '&mwh',  # Mouse behaviors
    '&td',
    '&key_repeat',
    '&gresc',
    '&sticky_key',  # Other stock behaviors
}

# Behaviors that take multiple parameters (including behavior parameters)
MULTI_PARAM_BEHAVIORS = {'&hmr', '&hml', '&hmrt', '&hmlt', '&ltl', '&ltr', '&td'}


def get_behavior_color(behavior):
    if not behavior.startswith('&'):
        return Colors.RESET

    behavior_name = behavior.split()[0].lower()

    if behavior_name in DIMMED_BEHAVIORS:
        return Colors.GRAY
    if behavior_name in KEYPRESS_BEHAVIORS:
        return Colors.ORANGE
    if behavior_name in STOCK_ZMK_BEHAVIORS:
        return Colors.PURPLE
    # Custom/user-defined behaviors (home row mods, custom macros, etc.)
    return Colors.MAGENTA


def extract_bindings_from_content(bindings_content, binding_macros=frozenset()):
    """Split a bindings array's text into bindings, each starting at an `&behavior` or a name in `binding_macros`."""
    if not bindings_content:
        return []

    content = re.sub(r'//.*$', '', bindings_content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    tokens = [token.rstrip('>;') for token in content.split() if token.rstrip('>;')]
    return _parse_tokens_into_bindings(tokens, binding_macros)


def _parse_tokens_into_bindings(tokens, binding_macros):
    bindings = []
    i = 0

    while i < len(tokens):
        if tokens[i].startswith('&') or tokens[i] in binding_macros:
            binding_parts = [tokens[i]]
            behavior = binding_parts[0].lower()
            i += 1

            if behavior in MULTI_PARAM_BEHAVIORS:
                i = _handle_multi_param_behavior(tokens, i, binding_parts, binding_macros)
            else:
                i = _handle_standard_behavior(tokens, i, binding_parts, binding_macros)

            bindings.append(' '.join(binding_parts))
        else:
            i += 1

    return bindings


def _handle_multi_param_behavior(tokens, i, binding_parts, binding_macros):
    """Handle behaviors that can take multiple parameters including behavior parameters."""
    behavior = binding_parts[0].lower()
    param_count = 0

    # Define parameter patterns for different behaviors
    # Each behavior can have different valid parameter patterns
    behavior_param_rules = {
        '&hmr': [1, 2],  # Can take 1 or 2 parameters
        '&hml': [1, 2],  # Can take 1 or 2 parameters
        '&hmrt': [1, 2],  # Can take 1 or 2 parameters
        '&hmlt': [1, 2],  # Can take 1 or 2 parameters
        '&ltl': [2],  # Always takes 2 parameters
        '&ltr': [2],  # Always takes 2 parameters
        '&td': [1, 2],  # Can take 1 or 2 parameters
    }

    max_params = max(behavior_param_rules.get(behavior, [2]))  # Default to 2 if not specified

    while i < len(tokens) and param_count < max_params:
        if tokens[i] in binding_macros:
            break
        if tokens[i].startswith('&'):
            # For behaviors like &hmr, &hml, &hmrt, &hmlt, a behavior can be the second parameter
            if param_count == 0 or (param_count == 1 and behavior in ('&hmr', '&hml', '&hmrt', '&hmlt')):
                binding_parts.append(tokens[i])
                i += 1
                param_count += 1

                # If this behavior parameter has its own parameter, include it
                # but only if we're still under the max params and the next token isn't a behavior
                if param_count < max_params and i < len(tokens) and not tokens[i].startswith('&'):
                    binding_parts.append(tokens[i])
                    i += 1
                    param_count += 1
            else:
                break  # This is the next binding
        else:
            binding_parts.append(tokens[i])
            i += 1
            param_count += 1

    return i


def _handle_standard_behavior(tokens, i, binding_parts, binding_macros):
    """Handle standard behaviors with simple parameters."""
    # Collect parameters until the next binding starts or the tokens run out
    while i < len(tokens) and not tokens[i].startswith('&') and tokens[i] not in binding_macros:
        binding_parts.append(tokens[i])
        i += 1

    return i


class KeymapError(ValueError):
    """A keymap the aligner cannot rewrite without losing or misplacing text."""


@dataclass
class Layer:
    """A child node of the `keymap` node that holds a `bindings = < … >` array.

    `start` and `end` bound the text between the array's `<` and `>`, which is the only
    text a rewrite replaces. `indent` is the leading whitespace of the line holding
    `bindings`, where the rewritten `>` goes.
    """

    name: str
    display_name: str | None
    bindings: list[str]
    start: int
    end: int
    indent: str


_COMMENT_OR_STRING = re.compile(r'//[^\n]*|/\*.*?\*/|"(?:[^"\\\n]|\\.)*"', re.DOTALL)
_KEYMAP_NODE = re.compile(r'(?<![\w,.+@&#-])keymap\s*\{')
_BINDINGS_PROPERTY = re.compile(r'\s*bindings\s*=\s*<')
_DISPLAY_NAME_PROPERTY = re.compile(r'\s*display-name\s*=\s*"')
_BINDING_MACRO = re.compile(r'^[ \t]*#[ \t]*define[ \t]+(\w+)[ \t]+&', re.MULTILINE)


def _blank_comments_and_strings(text):
    """Return `text` with every comment, and every string between its quotes, turned to spaces.

    Newlines stay, so an offset into the result is the same offset into `text`. A brace,
    `<` or `;` inside a comment or a display-name then reads as nothing.
    """

    def blank(match):
        found = match.group(0)
        if found.startswith('"'):
            return '"' + re.sub(r'[^\n]', ' ', found[1:-1]) + '"'
        return re.sub(r'[^\n]', ' ', found)

    return _COMMENT_OR_STRING.sub(blank, text)


def _line_number(text, offset):
    return text.count('\n', 0, offset) + 1


def _closing_brace(masked, open_brace):
    depth = 0
    for i in range(open_brace, len(masked)):
        if masked[i] == '{':
            depth += 1
        elif masked[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    raise KeymapError(f'the brace on line {_line_number(masked, open_brace)} is never closed')


def _statements(masked, start, end):
    """Yield `(start, end, body)` for each property and child node directly inside `masked[start:end]`.

    A property runs to its `;`, and its body is None. A child node's statement runs to its
    opening brace, and its body is the `(start, end)` span between its braces.
    """
    statement_start = start
    i = start
    while i < end:
        char = masked[i]
        if char == '{':
            close = _closing_brace(masked, i)
            yield statement_start, i, (i + 1, close)
            i = statement_start = close + 1
            continue
        if char == ';':
            yield statement_start, i, None
            statement_start = i + 1
        i += 1


def _closing_angle(masked, open_angle, end):
    """Find the `>` closing the cell array opened at `open_angle`, skipping any inside parentheses."""
    depth = 0
    for i in range(open_angle + 1, end):
        if masked[i] == '(':
            depth += 1
        elif masked[i] == ')':
            depth -= 1
        elif masked[i] == '>' and depth == 0:
            return i
    raise KeymapError(f'the bindings array opened on line {_line_number(masked, open_angle)} is never closed')


def _read_layer(keymap_content, masked, name, body_start, body_end, binding_macros):
    """Read one child node of `keymap`, or return None when it holds no `bindings` array."""
    display_name = None
    array = None
    for start, end, body in _statements(masked, body_start, body_end):
        if body is not None:
            continue
        statement = masked[start:end]
        if match := _DISPLAY_NAME_PROPERTY.match(statement):
            open_quote = start + match.end() - 1
            close_quote = masked.find('"', open_quote + 1, end)
            if close_quote != -1:
                display_name = keymap_content[open_quote + 1 : close_quote]
        elif match := _BINDINGS_PROPERTY.match(statement):
            open_angle = start + match.end() - 1
            close_angle = _closing_angle(masked, open_angle, end)
            if masked[close_angle + 1 : end].strip():
                raise KeymapError(
                    f"layer '{name}' continues its bindings past the '>' on line {_line_number(masked, close_angle)}, "
                    'and the aligner reads a single < > array'
                )
            keyword = start + len(statement) - len(statement.lstrip())
            array = (open_angle + 1, close_angle, keyword)

    if array is None:
        return None
    array_start, array_end, keyword = array
    line = keymap_content[keymap_content.rfind('\n', 0, keyword) + 1 : keyword]
    return Layer(
        name=name,
        display_name=display_name,
        bindings=extract_bindings_from_content(keymap_content[array_start:array_end], binding_macros),
        start=array_start,
        end=array_end,
        indent=line[: len(line) - len(line.lstrip(' \t'))],
    )


def find_layers(keymap_content):
    """Return each child node of the `keymap` node that holds a `bindings` array, in file order.

    A node name is whatever precedes its opening brace, minus any label, so a name may hold
    any character devicetree allows. A name the file `#define`s to a binding, such as
    `XXX` for `&none`, is a binding of its own. Raises KeymapError when there is no `keymap`
    node, a brace or a `bindings` array is never closed, or a `bindings` property holds more
    than one array.
    """
    masked = _blank_comments_and_strings(keymap_content)
    binding_macros = frozenset(_BINDING_MACRO.findall(masked))
    keymap_match = _KEYMAP_NODE.search(masked)
    if keymap_match is None:
        raise KeymapError("no 'keymap {' node found")
    open_brace = keymap_match.end() - 1
    close_brace = _closing_brace(masked, open_brace)

    layers = []
    for start, end, body in _statements(masked, open_brace + 1, close_brace):
        if body is None:
            continue
        header = masked[start:end].split()
        name = header[-1].rsplit(':', 1)[-1] if header else ''
        layer = _read_layer(keymap_content, masked, name, *body, binding_macros)
        if layer is not None:
            layers.append(layer)
    return layers


def _layer_data(layers):
    return {layer.name: {'bindings': layer.bindings, 'display_name': layer.display_name} for layer in layers}


def extract_all_layers(keymap_content):
    """Map each layer's node name to its bindings and display-name."""
    return _layer_data(find_layers(keymap_content))


def load_layout(layout_file):
    try:
        with open(layout_file) as f:
            layout = json.load(f)

        if 'layout' not in layout:
            print("Error: Layout file must contain a 'layout' field", file=sys.stderr)
            return None

        return layout

    except FileNotFoundError:
        print(f"Error: Layout file '{layout_file}' not found.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in layout file '{layout_file}': {e}", file=sys.stderr)
        return None


def build_layer_structure(layers, layout):
    """
    Organize layer bindings according to the keyboard layout matrix.
    """
    layout_matrix = layout['layout']
    structured_layers = {}

    for layer_name, layer_data in layers.items():
        bindings = layer_data['bindings']
        layer_rows = []
        binding_index = 0

        for row in layout_matrix:
            row_bindings = []
            for cell in row:
                if cell == 'X':
                    if binding_index < len(bindings):
                        row_bindings.append(bindings[binding_index])
                        binding_index += 1
                    else:
                        row_bindings.append(None)  # Missing binding
                else:
                    row_bindings.append(None)  # Empty position
            layer_rows.append(row_bindings)

        structured_layers[layer_name] = {'rows': layer_rows, 'display_name': layer_data['display_name']}

    return structured_layers


def calculate_column_widths(structured_layers, layout, padding=DEFAULT_PADDING):
    layout_matrix = layout['layout']
    num_columns = len(layout_matrix[0]) if layout_matrix else 0
    column_widths = [0] * num_columns

    # Find the maximum width needed for each column across all layers
    for layer_data in structured_layers.values():
        layer_rows = layer_data['rows']
        for row in layer_rows:
            for col_idx, binding in enumerate(row):
                if binding is not None:
                    column_widths[col_idx] = max(column_widths[col_idx], len(binding))

    return [width + padding for width in column_widths]


def format_binding_rows(layer_rows, column_widths, indent_size=DEFAULT_INDENT_SIZE):
    """Render one layer's grid as lines of text, each cell padded to its column's width.

    Each line starts with `indent_size` spaces. A gap or a missing binding is a blank cell.
    """
    lines = []
    for row in layer_rows:
        row_content = ' ' * indent_size
        for col_idx, binding in enumerate(row):
            row_content += (binding or '').ljust(column_widths[col_idx])
        lines.append(row_content.rstrip())
    return lines


def _first_lost_token(original, realigned):
    """Return the first token of `original`, as a match, that `realigned` does not hold at the same position."""
    realigned_tokens = realigned.split()
    for index, token in enumerate(re.finditer(r'\S+', original)):
        if index >= len(realigned_tokens) or token.group(0) != realigned_tokens[index]:
            return token
    return None


def realign_bindings(keymap_content, layers, structured_layers, column_widths, layout, indent_size=DEFAULT_INDENT_SIZE):
    """Return `keymap_content` with the inside of each layer's `bindings` array realigned.

    Only the text between each array's `<` and `>` changes, and the `>` goes on its own line
    at the indentation of the line holding `bindings`. Raises KeymapError, naming every layer
    at fault, when a layer holds more bindings than the layout has keys, or when its array
    holds text the realigned rows would not reproduce, such as a comment.
    """
    key_count = sum(1 for row in layout['layout'] for cell in row if cell == 'X')
    problems = []
    pieces = []
    cursor = 0
    for layer in layers:
        if len(layer.bindings) > key_count:
            problems.append(f"layer '{layer.name}' holds {len(layer.bindings)} bindings, but the layout has {key_count} keys")
            continue
        rows = format_binding_rows(structured_layers[layer.name]['rows'], column_widths, indent_size)
        realigned = '\n' + '\n'.join(rows) + '\n' + layer.indent
        lost = _first_lost_token(keymap_content[layer.start : layer.end], realigned)
        if lost is not None:
            problems.append(
                f"layer '{layer.name}' holds '{lost.group(0)}' on line {_line_number(keymap_content, layer.start + lost.start())} "
                'inside its bindings, which realigning would drop'
            )
            continue
        pieces.append(keymap_content[cursor : layer.start])
        pieces.append(realigned)
        cursor = layer.end

    if problems:
        raise KeymapError('\n'.join(problems))
    pieces.append(keymap_content[cursor:])
    return ''.join(pieces)


def visual_debug_print_layout(layout):
    """Print keyboard layout structure for human inspection."""
    print(f'\n{Colors.GREEN}{Colors.BOLD}{"=" * 70}')
    print('ZMK KEYMAP ALIGNMENT DEBUG')
    print(f'{"=" * 70}{Colors.RESET}')

    print(f'\n{Colors.CYAN}KEYBOARD LAYOUT INFORMATION{Colors.RESET}')
    print('─' * 50)

    layout_matrix = layout['layout']
    rows = len(layout_matrix)
    columns = len(layout_matrix[0]) if layout_matrix else 0
    total_keys = sum(sum(1 for cell in row if cell == 'X') for row in layout_matrix)

    print(f'  Layout name: {Colors.YELLOW}{layout.get("name", "Unknown")}{Colors.RESET}')
    print(f'  Dimensions:  {Colors.YELLOW}{rows} rows x {columns} columns{Colors.RESET}')
    print(f'  Total keys:  {Colors.YELLOW}{total_keys}{Colors.RESET}')

    print(f'\n{Colors.CYAN}LAYOUT MATRIX{Colors.RESET} (X = key position, - = empty)')
    print('─' * 50)

    for row_idx, row in enumerate(layout_matrix):
        row_display = []
        for col_idx, cell in enumerate(row):
            if cell == 'X':
                row_display.append(f'{Colors.GREEN}[{col_idx:2d}]{Colors.RESET}')
            else:
                row_display.append('    ')
        print(f'  Row {row_idx:2d}: ' + ' '.join(row_display))


def visual_debug_print_layer_bindings(layers, layout, column_widths):
    """Print layer bindings in keyboard layout matrix format."""
    print(f'\n{Colors.CYAN}COLUMN WIDTHS{Colors.RESET}')
    print('─' * 50)
    print('  Col: ' + ' '.join(f'{i:2d}' for i in range(len(column_widths))))
    print('  Width: ' + ' '.join(f'{width:2d}' for width in column_widths))

    print(f'\n{Colors.CYAN}LAYER BINDINGS LAYOUT{Colors.RESET}')
    print('─' * 50)

    layout_matrix = layout['layout']

    for layer_name, layer_data in layers.items():
        bindings = layer_data['bindings']
        display_name = layer_data['display_name']
        layer_title = f'Layer: {layer_name}'
        if display_name:
            layer_title += f' ("{display_name}")'

        print(f'\n  {Colors.BLUE}{Colors.BOLD}{layer_title}{Colors.RESET}')
        print(f'     Total bindings: {Colors.YELLOW}{len(bindings)}{Colors.RESET}')

        # Calculate layer-specific column widths for compact display
        layer_column_widths = _calculate_layer_column_widths(layout_matrix, bindings)

        # Display the layer with proper visual alignment
        _print_layer_with_alignment(layout_matrix, bindings, layer_column_widths)


def _calculate_layer_column_widths(layout_matrix, bindings):
    """Calculate column widths optimized for a single layer."""
    layer_column_widths = [0] * len(layout_matrix[0])
    binding_index = 0

    for row in layout_matrix:
        for col_idx, cell in enumerate(row):
            if cell == 'X' and binding_index < len(bindings):
                binding = bindings[binding_index]
                layer_column_widths[col_idx] = max(layer_column_widths[col_idx], len(binding) + 2)
                binding_index += 1

    return layer_column_widths


def _print_layer_with_alignment(layout_matrix, bindings, layer_column_widths):
    """Print a single layer with proper visual keyboard alignment."""
    binding_index = 0

    for row_idx, row in enumerate(layout_matrix):
        if not any(cell == 'X' for cell in row):
            continue  # Skip rows with no bindings

        row_display = []
        for col_idx, cell in enumerate(row):
            if cell == 'X':
                if binding_index < len(bindings):
                    binding = bindings[binding_index]
                    colored_binding = _colorize_binding(binding)
                    display_text = f'[{colored_binding}]'
                    # Account for color codes in padding calculation
                    color_len = len(colored_binding) - len(binding)
                    padded_text = display_text.ljust(layer_column_widths[col_idx] + color_len)
                    row_display.append(padded_text)
                    binding_index += 1
                else:
                    empty_text = f'[{Colors.RED}---{Colors.RESET}]'
                    color_len = len(empty_text) - 3
                    padded_text = empty_text.ljust(layer_column_widths[col_idx] + color_len)
                    row_display.append(padded_text)
            else:
                row_display.append(' ' * layer_column_widths[col_idx])

        print(f'     Row {row_idx:2d}: ' + ''.join(row_display).rstrip())


def _colorize_binding(binding):
    """Apply appropriate color to a binding for display."""
    if not binding.startswith('&'):
        return binding

    parts = binding.split()
    behavior_color = get_behavior_color(binding)

    if len(parts) > 1:
        return f'{behavior_color}{parts[0]}{Colors.RESET} {" ".join(parts[1:])}'
    return f'{behavior_color}{binding}{Colors.RESET}'


def visual_debug_print_formatted_layers(structured_layers, column_widths, indent_size=DEFAULT_INDENT_SIZE):
    """Print formatted layers with colored output for debugging."""
    print(f'\n{Colors.CYAN}FORMATTED LAYERS OUTPUT{Colors.RESET}')
    print('─' * 50)

    for layer_name, layer_data in structured_layers.items():
        rows = format_binding_rows(layer_data['rows'], column_widths, indent_size)

        print(f'\n{Colors.BLUE}{layer_name}{Colors.RESET}')
        _print_colored_bindings('\n'.join(row.strip() for row in rows))


def _print_colored_bindings(clean_bindings):
    """Print bindings with appropriate coloring applied."""

    def replace_behavior(match):
        behavior = match.group(0)
        behavior_parts = behavior.split()
        behavior_color = get_behavior_color(behavior)

        if len(behavior_parts) > 1:
            return f'{behavior_color}{behavior_parts[0]}{Colors.RESET} {" ".join(behavior_parts[1:])}'
        return f'{behavior_color}{behavior}{Colors.RESET}'

    behavior_pattern = r'&\w+(?:\s+[^&\s]+(?:\s+[^&\s]+)*)?'

    for line in clean_bindings.split('\n'):
        if line.strip():
            colored_line = re.sub(behavior_pattern, replace_behavior, line)
            print(f'  {colored_line}')


def align_keymap_with_layout(
    keymap_file,
    layout_file,
    output_file=None,
    debug=False,
    indent_size=DEFAULT_INDENT_SIZE,
    padding=DEFAULT_PADDING,
):
    """Align keymap bindings according to keyboard layout.

    Only the inside of each layer's `bindings` array is rewritten. A keymap that cannot be
    rewritten without losing text is reported, and nothing is written.

    Args:
        keymap_file: Path to the keymap file
        layout_file: Path to the layout JSON file
        output_file: Optional output file path (default: modify in place)
        debug: Print the layout and each layer's grid; write nothing
        indent_size: Number of spaces before each binding row (default 4)
        padding: Number of spaces between columns (default 2)
    """
    layout = load_layout(layout_file)
    if layout is None:
        return False

    try:
        keymap_content = Path(keymap_file).read_text()
    except FileNotFoundError:
        print(f"Error: Keymap file '{keymap_file}' not found.", file=sys.stderr)
        return False

    try:
        layers = find_layers(keymap_content)
    except KeymapError as e:
        print(f'Error: {e}', file=sys.stderr)
        return False
    if not layers:
        print('Error: No layers found in keymap file.', file=sys.stderr)
        return False

    names = [layer.name for layer in layers]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        print(f'Error: more than one layer node is named {", ".join(duplicates)}', file=sys.stderr)
        return False

    print(f'Found layers: {names}')
    layer_data = _layer_data(layers)
    structured_layers = build_layer_structure(layer_data, layout)
    column_widths = calculate_column_widths(structured_layers, layout, padding)

    if debug:
        visual_debug_print_layout(layout)
        visual_debug_print_layer_bindings(layer_data, layout, column_widths)
        visual_debug_print_formatted_layers(structured_layers, column_widths, indent_size)

    try:
        output_content = realign_bindings(keymap_content, layers, structured_layers, column_widths, layout, indent_size)
    except KeymapError as e:
        for problem in str(e).splitlines():
            print(f'Error: {problem}', file=sys.stderr)
        print('Nothing was written.', file=sys.stderr)
        return False

    if debug:
        return True

    for layer in layers:
        print(f'Formatted {layer.name}: {len(layer.bindings)} bindings')

    # Determine output destination
    target_file = output_file or keymap_file

    try:
        Path(target_file).write_text(output_content)

        if output_file:
            print(f'Output written to: {output_file}')
        else:
            print(f'Keymap formatted in place: {keymap_file}')

    except OSError as e:
        print(f"Error writing to file '{target_file}': {e}", file=sys.stderr)
        return False

    print(f'Keymap aligned using layout: {layout_file}')
    print('Alignment completed successfully!')
    return True
