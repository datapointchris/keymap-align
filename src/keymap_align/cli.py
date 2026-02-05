import argparse
import sys
from pathlib import Path

from keymap_align.align import align_keymap_with_layout
from keymap_align.config import find_config_file
from keymap_align.config import load_config
from keymap_align.config import resolve_config_layout
from keymap_align.layout_resolver import get_bundled_layout_names
from keymap_align.layout_resolver import resolve_layout


def main():
    parser = argparse.ArgumentParser(
        description='Align ZMK keymap using keyboard layout',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -k keymap.keymap --layout corne42
  %(prog)s -k keymap.keymap --layout-file layout.json
  %(prog)s -k keymap.keymap  # uses keymap_align.toml config
  %(prog)s --list-layouts
        """,
    )

    parser.add_argument('-k', '--keymap', help='Input keymap file')
    parser.add_argument(
        '-l',
        '--layout-file',
        help='Custom layout JSON file path',
    )
    parser.add_argument(
        '--layout',
        help='Bundled layout name (e.g., corne42, piantor, glove80)',
    )
    parser.add_argument(
        '--list-layouts',
        action='store_true',
        help='List bundled layouts and exit',
    )
    parser.add_argument('-o', '--output', help='Output keymap file (default: modify in place)')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed visualization',
    )

    args = parser.parse_args()

    # Handle --list-layouts
    if args.list_layouts:
        for name in get_bundled_layout_names():
            print(name)
        return 0

    # Keymap is required for alignment
    if not args.keymap:
        parser.error('the following arguments are required: -k/--keymap')

    # Find and load config file
    keymap_path = Path(args.keymap).resolve()
    config = {}
    config_path = find_config_file(keymap_path.parent)
    if config_path:
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f'Warning: Failed to load config from {config_path}: {e}', file=sys.stderr)

    # Resolve layout
    config_layout = resolve_config_layout(config, config_path) if config_path else None
    try:
        layout_path = resolve_layout(args.layout, args.layout_file, config_layout)
    except ValueError as e:
        print(f'Error: {e}', file=sys.stderr)
        return 1

    success = align_keymap_with_layout(args.keymap, layout_path, args.output, args.debug)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
