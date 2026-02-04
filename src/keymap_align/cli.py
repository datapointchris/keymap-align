#!/usr/bin/env python3

import argparse
import sys

from keymap_align.align import align_keymap_with_layout


def main():
    parser = argparse.ArgumentParser(
        description='Align ZMK keymap using keyboard layout',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -k keymap.keymap -l layout.json -o aligned.keymap
  %(prog)s -k keymap.keymap -l layout.json --debug
        """,
    )

    parser.add_argument('-k', '--keymap', required=True, help='Input keymap file')
    parser.add_argument('-l', '--layout', required=True, help='Keyboard layout JSON file')
    parser.add_argument('-o', '--output', help='Output keymap file (default: modify in place)')
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug output with detailed visualization',
    )

    args = parser.parse_args()

    success = align_keymap_with_layout(args.keymap, args.layout, args.output, args.debug)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
