import json
import re
from pathlib import Path


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

# Default padding for column alignment
DEFAULT_COLUMN_PADDING = 2


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


def parse_layer_for_debug(formatted_layer):
    lines = formatted_layer.split('\n')
    clean_lines = []
    in_bindings = False
    layer_name = None
    for line in lines:
        if '{' in line and not line.strip().startswith('bindings'):
            layer_name = line.split('{')[0].strip()
            break

    for line in lines:
        if 'bindings = <' in line:
            in_bindings = True
            continue
        elif '>; ' in line or line.strip().endswith('>;'):
            in_bindings = False
            break
        elif in_bindings and line.strip():
            clean_lines.append(line.strip())

    return layer_name, '\n'.join(clean_lines)


def extract_bindings_from_content(bindings_content):
    if not bindings_content:
        return []

    content = re.sub(r'//.*$', '', bindings_content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    tokens = [token.rstrip('>;') for token in content.split() if token.rstrip('>;')]
    return _parse_tokens_into_bindings(tokens)


def _parse_tokens_into_bindings(tokens):
    bindings = []
    i = 0

    while i < len(tokens):
        if tokens[i].startswith('&'):
            binding_parts = [tokens[i]]
            behavior = binding_parts[0].lower()
            i += 1

            if behavior in MULTI_PARAM_BEHAVIORS:
                i = _handle_multi_param_behavior(tokens, i, binding_parts)
            else:
                i = _handle_standard_behavior(tokens, i, binding_parts)

            bindings.append(' '.join(binding_parts))
        else:
            i += 1

    return bindings


def _handle_multi_param_behavior(tokens, i, binding_parts):
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


def _handle_standard_behavior(tokens, i, binding_parts):
    """Handle standard behaviors with simple parameters."""
    # Collect parameters until we hit another behavior or run out
    while i < len(tokens) and not tokens[i].startswith('&'):
        binding_parts.append(tokens[i])
        i += 1

    return i


def extract_all_layers(keymap_content):
    layers = {}
    # Match layer_name { [optional display-name = "...";] bindings = < content >; }
    layer_pattern = r'(\w+)\s*\{\s*(?:display-name\s*=\s*\"([^\"]*)\";?\s*)?bindings\s*=\s*<([^>]+)>\s*;'

    for match in re.finditer(layer_pattern, keymap_content, re.DOTALL):
        layer_name = match.group(1)
        display_name = match.group(2)  # Will be None if no display-name found
        bindings_content = match.group(3)
        bindings = extract_bindings_from_content(bindings_content)
        layers[layer_name] = {'bindings': bindings, 'display_name': display_name}

    return layers


def load_layout(layout_file):
    try:
        with open(layout_file) as f:
            layout = json.load(f)

        if 'layout' not in layout:
            print("Error: Layout file must contain a 'layout' field")
            return None

        return layout

    except FileNotFoundError:
        print(f"Error: Layout file '{layout_file}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in layout file '{layout_file}': {e}")
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


def calculate_column_widths(structured_layers, layout, padding=DEFAULT_COLUMN_PADDING):
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


def format_layer(layer_name, layer_data, column_widths):
    layer_rows = layer_data['rows']
    display_name = layer_data['display_name']

    lines = [f'        {layer_name} {{']

    # Add display-name if it exists
    if display_name:
        lines.append(f'            display-name = "{display_name}";')

    lines.append('            bindings = <')

    for row in layer_rows:
        row_content = '   '  # Base indentation

        for col_idx, binding in enumerate(row):
            if binding is not None:
                row_content += binding.ljust(column_widths[col_idx])
            else:
                row_content += ' ' * column_widths[col_idx]

        lines.append(row_content.rstrip())

    lines.extend(['            >;', '        };'])
    return '\n'.join(lines)


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


def visual_debug_print_formatted_layers(structured_layers, column_widths):
    """Print formatted layers with colored output for debugging."""
    print(f'\n{Colors.CYAN}FORMATTED LAYERS OUTPUT{Colors.RESET}')
    print('─' * 50)

    for layer_name, layer_data in structured_layers.items():
        formatted_layer = format_layer(layer_name, layer_data, column_widths)
        parsed_name, clean_bindings = parse_layer_for_debug(formatted_layer)

        print(f'\n{Colors.BLUE}{parsed_name}{Colors.RESET}')
        _print_colored_bindings(clean_bindings)


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


def align_keymap_with_layout(keymap_file, layout_file, output_file=None, debug=False):
    layout = load_layout(layout_file)
    if layout is None:
        return False

    try:
        keymap_content = Path(keymap_file).read_text()
    except FileNotFoundError:
        print(f"Error: Keymap file '{keymap_file}' not found.")
        return False

    layers = extract_all_layers(keymap_content)
    if not layers:
        print('Error: No layers found in keymap file.')
        return False

    print(f'Found layers: {list(layers.keys())}')
    structured_layers = build_layer_structure(layers, layout)
    column_widths = calculate_column_widths(structured_layers, layout)

    if debug:
        visual_debug_print_layout(layout)
        visual_debug_print_layer_bindings(layers, layout, column_widths)
        visual_debug_print_formatted_layers(structured_layers, column_widths)
        return True

    # Parse original file to find keymap section boundaries
    lines = keymap_content.split('\n')
    keymap_start_idx = None
    keymap_end_idx = None

    # Find keymap section start
    for i, line in enumerate(lines):
        if 'keymap {' in line:
            keymap_start_idx = i
            break

    if keymap_start_idx is None:
        print("Error: Could not find 'keymap {' in the file.")
        return False

    # Find keymap section end by counting braces
    brace_count = 0
    for i in range(keymap_start_idx, len(lines)):
        line = lines[i]
        # Count opening and closing braces
        brace_count += line.count('{') - line.count('}')
        if brace_count == 0 and i > keymap_start_idx:
            keymap_end_idx = i
            break

    if keymap_end_idx is None:
        print('Error: Could not find end of keymap section.')
        return False

    # Extract pre-keymap and post-keymap content
    pre_keymap_content = '\n'.join(lines[:keymap_start_idx])
    post_keymap_content = '\n'.join(lines[keymap_end_idx + 1 :])

    # Generate new keymap section content
    keymap_lines = ['    keymap {', '        compatible = "zmk,keymap";']
    for layer_name, layer_data in structured_layers.items():
        formatted_layer = format_layer(layer_name, layer_data, column_widths)
        keymap_lines.append(formatted_layer)
        layer_rows = layer_data['rows']
        binding_count = sum(1 for row in layer_rows for binding in row if binding is not None)
        print(f'Formatted {layer_name}: {binding_count} bindings')

    keymap_lines.append('    };')
    keymap_section = '\n'.join(keymap_lines)

    # Combine all parts
    output_content = pre_keymap_content + '\n' + keymap_section + '\n' + post_keymap_content

    # Determine output destination
    target_file = output_file or keymap_file

    try:
        Path(target_file).write_text(output_content)

        if output_file:
            print(f'Output written to: {output_file}')
        else:
            print(f'Keymap formatted in place: {keymap_file}')

    except OSError as e:
        print(f"Error writing to file '{target_file}': {e}")
        return False

    print(f'Keymap aligned using layout: {layout_file}')
    print('Alignment completed successfully!')
    return True
