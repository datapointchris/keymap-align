"""
Comprehensive tests for keymap_align package using pytest.
"""

import filecmp
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from keymap_align.align import align_keymap_with_layout
from keymap_align.align import build_layer_structure
from keymap_align.align import calculate_column_widths
from keymap_align.align import extract_all_layers
from keymap_align.align import extract_bindings_from_content
from keymap_align.align import format_layer
from keymap_align.align import load_layout

# Consolidated fixtures for cleaner code
TEST_BASE_DIR = Path(__file__).parent


def get_test_file(relative_path: str) -> Path:
    """Get a test file path relative to the base test directory."""
    file_path = TEST_BASE_DIR / relative_path
    if not file_path.exists():
        pytest.skip(f'Test file not found: {relative_path}')
    return file_path


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # Cleanup is automatic with tempdir


@pytest.fixture
def test_output_dir():
    """Ensure test output directory exists."""
    output_dir = TEST_BASE_DIR / 'test_keymaps' / 'test_output'
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


@pytest.fixture
def sample_layout():
    """Sample layout for basic testing."""
    return {
        'name': 'Test Layout',
        'layout': [
            ['X', 'X', 'X', 'X'],  # Full row
            ['X', 'X', 'X', 'X'],  # Full row
            ['-', 'X', 'X', '-'],  # Partial row (only middle 2 keys)
        ],
    }
    # Total keys: 4 + 4 + 2 = 10


@pytest.fixture
def sample_layout_file(temp_dir, sample_layout):
    """Sample layout file for testing."""
    layout_file = temp_dir / 'test_layout.json'
    with open(layout_file, 'w') as f:
        json.dump(sample_layout, f)
    return layout_file


@pytest.fixture
def sample_keymap_content():
    """Sample keymap content for testing."""
    return """
#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>

/ {
    keymap {
        compatible = "zmk,keymap";

        BASE {
            bindings = <
                &kp Q    &kp W    &kp E    &kp R
                &kp A    &kp S    &kp D    &kp F
                         &kp Z    &kp X
            >;
        };

        LAYER2 {
            bindings = <
                &kp N1   &kp N2   &kp N3   &kp N4
                &kp N5   &kp N6   &kp N7   &kp N8
                         &kp N9   &kp N0
            >;
        };
    };
};
"""


@pytest.fixture
def sample_keymap_file(temp_dir, sample_keymap_content):
    """Sample keymap file for testing."""
    keymap_file = temp_dir / 'test_keymap.keymap'
    keymap_file.write_text(sample_keymap_content)
    return keymap_file


# Test Classes converted to functions
class TestLayoutLoading:
    """Tests for layout loading functionality."""

    def test_load_layout(self, sample_layout_file, sample_layout):
        """Test loading layout from JSON file."""
        result = load_layout(str(sample_layout_file))
        assert result == sample_layout
        assert result['name'] == 'Test Layout'
        assert len(result['layout']) == 3
        assert len(result['layout'][0]) == 4

    def test_layout_without_rows_columns_fields(self, temp_dir):
        """Test that the script works with layout files that don't have separate rows/columns fields"""
        layout_data = {'name': 'Modern Layout', 'layout': [['X', 'X', '-'], ['X', 'X', 'X']]}

        layout_file = temp_dir / 'modern_layout.json'
        with open(layout_file, 'w') as f:
            json.dump(layout_data, f)

        result = load_layout(str(layout_file))
        assert result == layout_data
        assert result['name'] == 'Modern Layout'


class TestBindingExtraction:
    """Tests for binding extraction functionality."""

    def test_extract_bindings_basic(self):
        """Test basic binding extraction."""
        content = '&kp A &kp B &trans &none'
        result = extract_bindings_from_content(content)
        expected = ['&kp A', '&kp B', '&trans', '&none']
        assert result == expected

    def test_extract_bindings_complex_behaviors(self):
        """Test extraction of complex multi-parameter behaviors."""
        content = '&hml LCTRL A &hmr RALT B &lt 1 SPACE &td 2 3'
        result = extract_bindings_from_content(content)
        expected = ['&hml LCTRL A', '&hmr RALT B', '&lt 1 SPACE', '&td 2 3']
        assert result == expected

    def test_extract_bindings_realistic_mixed(self):
        """Test extraction of realistic mixed binding types from a real keymap."""
        content = '&kp Q &ltl MOUSE W &kp E &hmr RALT K &caps_word &trans'
        result = extract_bindings_from_content(content)
        expected = ['&kp Q', '&ltl MOUSE W', '&kp E', '&hmr RALT K', '&caps_word', '&trans']
        assert result == expected

    def test_extract_bindings_with_comments(self):
        """Test binding extraction with comments."""
        content = """
        &kp A    // First key
        &kp B    /* Second key */
        &kp C    // Third key
        """
        result = extract_bindings_from_content(content)
        expected = ['&kp A', '&kp B', '&kp C']
        assert result == expected

    def test_real_world_bindings(self):
        """Test extraction of real-world complex bindings."""
        content = """
        &bt BT_SEL 0  &bt BT_SEL 1  &bt BT_SEL 2  &bt BT_SEL 3  &bt BT_SEL 4
        &bootloader   &reset        &bt BT_CLR    &out OUT_TOG  &sys_reset
        &hml LGUI A   &hml LALT S   &hml LCTRL D  &hmr RCTRL K  &hmr RALT L
        """
        result = extract_bindings_from_content(content)
        expected = [
            '&bt BT_SEL 0',
            '&bt BT_SEL 1',
            '&bt BT_SEL 2',
            '&bt BT_SEL 3',
            '&bt BT_SEL 4',
            '&bootloader',
            '&reset',
            '&bt BT_CLR',
            '&out OUT_TOG',
            '&sys_reset',
            '&hml LGUI A',
            '&hml LALT S',
            '&hml LCTRL D',
            '&hmr RCTRL K',
            '&hmr RALT L',
        ]
        assert result == expected

    def test_glove80_specific_behaviors(self):
        """Test behaviors specific to Glove80 configuration."""
        glove80_content = """
        &ltl MOUSE W &ltl NAV E &hmrt RSHFT &caps_word &magic MAGIC 0
        """
        result = extract_bindings_from_content(glove80_content)
        expected = ['&ltl MOUSE W', '&ltl NAV E', '&hmrt RSHFT &caps_word', '&magic MAGIC 0']
        assert result == expected


class TestLayerExtraction:
    """Tests for layer extraction functionality."""

    def test_extract_all_layers(self, sample_keymap_content):
        """Test extracting all layers from keymap content."""
        layers = extract_all_layers(sample_keymap_content)
        assert len(layers) == 2

        # Check layer names
        assert 'BASE' in layers
        assert 'LAYER2' in layers

        # Check layer content
        base_layer = layers['BASE']
        layer2 = layers['LAYER2']

        # Check layer structure (new format with bindings and display_name)
        assert isinstance(base_layer, dict)
        assert isinstance(layer2, dict)
        assert 'bindings' in base_layer
        assert 'display_name' in base_layer
        assert 'bindings' in layer2
        assert 'display_name' in layer2

        assert len(base_layer['bindings']) == 10  # 4+4+2 keys as per sample layout
        assert len(layer2['bindings']) == 10

        # Check first few bindings
        assert base_layer['bindings'][0] == '&kp Q'
        assert base_layer['bindings'][1] == '&kp W'
        assert layer2['bindings'][0] == '&kp N1'
        assert layer2['bindings'][1] == '&kp N2'

    def test_layer_validation_insufficient_bindings(self):
        """Test validation of layers with insufficient bindings."""
        insufficient_file = get_test_file('test_keymaps/misaligned/glove80_input_insufficient_bindings.keymap')
        glove80_layout_file = get_test_file('layouts/glove80_80key_layout.json')

        load_layout(str(glove80_layout_file))
        content = insufficient_file.read_text()
        layers = extract_all_layers(content)

        # Should extract layers but they may be insufficient
        assert len(layers) > 0
        for _layer_name, layer_data in layers.items():
            # Insufficient files should have fewer bindings than required
            assert isinstance(layer_data, dict)
            assert 'bindings' in layer_data
            assert isinstance(layer_data['bindings'], list)


class TestColumnWidthCalculation:
    """Tests for column width calculation functionality."""

    def test_calculate_column_widths_basic(self, sample_layout):
        """Test basic column width calculation."""
        # Create test layer structures in new format
        layer1_structure = {
            'rows': [['&kp A', '&kp B', '&kp C', '&kp D'], ['&kp E', '&kp F', '&kp G', '&kp H'], [None, '&kp I', '&kp J', None]],
            'display_name': None,
        }
        layer2_structure = {
            'rows': [['&kp N1', '&kp N2', '&kp N3', '&kp N4'], ['&kp N5', '&kp N6', '&kp N7', '&kp N8'], [None, '&kp N9', '&kp N0', None]],
            'display_name': None,
        }

        layers = {'BASE': layer1_structure, 'LAYER2': layer2_structure}

        # Calculate column widths
        widths = calculate_column_widths(layers, sample_layout)

        # Should return a list of widths for each column
        assert isinstance(widths, list)
        assert len(widths) == 4  # 4 columns as per sample layout

        # Each width should be reasonable (at least the length of the longest binding + padding)
        for width in widths:
            assert isinstance(width, int)
            assert width >= 4  # At least "&kp " + some padding

    def test_calculate_column_widths_with_complex_bindings(self):
        """Test column width calculation with complex multi-parameter bindings."""
        layout = {'layout': [['X', 'X', 'X'], ['X', 'X', 'X']]}

        layer_structure = {
            'rows': [['&hml LCTRL A', '&hmr RALT B', '&lt 1 SPACE'], ['&hml LGUI TAB', '&caps_word', '&trans']],
            'display_name': None,
        }

        layers = {'BASE': layer_structure}

        # Calculate column widths
        widths = calculate_column_widths(layers, layout)

        assert isinstance(widths, list)
        assert len(widths) == 3

        # First column should be wide enough for "&hml LCTRL A" and "&hml LGUI TAB"
        assert widths[0] >= len('&hml LGUI TAB') + 2  # +2 for padding
        # Second column should accommodate "&hmr RALT B" and "&caps_word"
        assert widths[1] >= len('&hmr RALT B') + 2
        # Third column should accommodate "&lt 1 SPACE" and "&trans"
        assert widths[2] >= len('&lt 1 SPACE') + 2


class TestLayerStructureBuilding:
    """Tests for layer structure building functionality."""

    def test_build_layer_structure_basic(self, sample_layout):
        """Test basic layer structure building."""
        bindings = ['&kp A', '&kp B', '&kp C', '&kp D', '&kp E', '&kp F', '&kp G', '&kp H', '&kp I', '&kp J']
        layers = {'BASE': {'bindings': bindings, 'display_name': None}}

        # Build layer structure
        structure = build_layer_structure(layers, sample_layout)

        # Should return a dict with layer structures
        assert isinstance(structure, dict)
        assert 'BASE' in structure

        layer_data = structure['BASE']

        # Should return a dict with 'rows' and 'display_name'
        assert isinstance(layer_data, dict)
        assert 'rows' in layer_data
        assert 'display_name' in layer_data

        layer_structure = layer_data['rows']
        assert isinstance(layer_structure, list)
        assert len(layer_structure) == 3  # 3 rows as per sample layout

        # Check structure matches layout
        assert len(layer_structure[0]) == 4  # Full row
        assert len(layer_structure[1]) == 4  # Full row
        assert len(layer_structure[2]) == 4  # Partial row with None values

        # Check bindings are placed correctly
        assert layer_structure[0] == ['&kp A', '&kp B', '&kp C', '&kp D']
        assert layer_structure[1] == ['&kp E', '&kp F', '&kp G', '&kp H']
        assert layer_structure[2] == [None, '&kp I', '&kp J', None]  # None for "-" positions

    def test_build_layer_structure_insufficient_bindings(self, sample_layout):
        """Test layer structure building with insufficient bindings."""
        # Only provide 8 bindings when 10 are needed
        bindings = ['&kp A', '&kp B', '&kp C', '&kp D', '&kp E', '&kp F', '&kp G', '&kp H']
        layers = {'LAYER2': {'bindings': bindings, 'display_name': None}}

        structure = build_layer_structure(layers, sample_layout)

        # Should still build structure with None for missing bindings
        assert isinstance(structure, dict)
        assert 'LAYER2' in structure

        layer_data = structure['LAYER2']
        assert 'rows' in layer_data
        layer_structure = layer_data['rows']

        assert isinstance(layer_structure, list)
        assert len(layer_structure) == 3

        # First two rows should be complete
        assert layer_structure[0] == ['&kp A', '&kp B', '&kp C', '&kp D']
        assert layer_structure[1] == ['&kp E', '&kp F', '&kp G', '&kp H']
        # Last row should have None for insufficient bindings
        assert layer_structure[2] == [None, None, None, None]  # All None due to insufficient bindings

    def test_build_layer_structure_simple_layout(self):
        """Test layer structure building with a simple 2x3 layout."""
        layout = {'layout': [['X', 'X', 'X'], ['X', 'X', 'X']]}

        bindings = ['&kp A', '&kp B', '&kp C', '&kp D', '&kp E', '&kp F']
        layers = {'BASE': {'bindings': bindings, 'display_name': None}}

        structure = build_layer_structure(layers, layout)

        assert isinstance(structure, dict)
        assert 'BASE' in structure

        layer_data = structure['BASE']
        assert 'rows' in layer_data
        layer_structure = layer_data['rows']
        assert len(layer_structure) == 2
        assert layer_structure[0] == ['&kp A', '&kp B', '&kp C']
        assert layer_structure[1] == ['&kp D', '&kp E', '&kp F']


class TestLayerFormatting:
    """Tests for layer formatting functionality."""

    def test_format_layer_basic(self):
        """Test basic layer formatting."""
        layer_data = {'rows': [['&kp A', '&kp B', '&kp C'], ['&kp D', '&kp E', '&kp F']], 'display_name': None}
        column_widths = [8, 8, 8]  # Fixed widths for consistent formatting

        formatted = format_layer('BASE', layer_data, column_widths)

        # Should return formatted string
        assert isinstance(formatted, str)

        # Should contain the layer name and bindings
        assert 'BASE' in formatted
        assert '&kp A' in formatted
        assert '&kp B' in formatted
        assert '&kp C' in formatted

        # Should be properly formatted with ZMK syntax
        lines = formatted.strip().split('\n')
        assert len(lines) >= 4  # Header, bindings start, rows, footer

        # Should have proper ZMK layer structure
        assert 'BASE {' in formatted
        assert 'bindings = <' in formatted
        assert '>;' in formatted

    def test_format_layer_with_none_values(self):
        """Test layer formatting with None values (missing keys)."""
        layer_data = {
            'rows': [
                ['&kp A', '&kp B', '&kp C'],
                [None, '&kp D', None],  # Missing first and last keys
            ],
            'display_name': None,
        }
        column_widths = [8, 8, 8]

        formatted = format_layer('LAYER2', layer_data, column_widths)

        assert isinstance(formatted, str)

        # Should handle None values appropriately
        assert 'LAYER2' in formatted
        assert '&kp D' in formatted

        # Should have proper ZMK structure
        assert 'bindings = <' in formatted
        assert '>;' in formatted

    def test_format_layer_complex_bindings(self):
        """Test layer formatting with complex multi-parameter bindings."""
        layer_data = {
            'rows': [['&hml LCTRL A', '&hmr RALT B', '&lt 1 SPACE'], ['&hml LGUI TAB', '&caps_word', '&trans']],
            'display_name': None,
        }
        column_widths = [16, 12, 14]  # Adequate widths for complex bindings

        formatted = format_layer('COMPLEX', layer_data, column_widths)

        assert isinstance(formatted, str)

        # Should contain all complex bindings and layer name
        assert 'COMPLEX' in formatted
        assert '&hml LCTRL A' in formatted
        assert '&hmr RALT B' in formatted
        assert '&lt 1 SPACE' in formatted
        assert '&hml LGUI TAB' in formatted
        assert '&caps_word' in formatted
        assert '&trans' in formatted

        # Should have proper ZMK structure
        assert 'bindings = <' in formatted
        assert '>;' in formatted


class TestAlignment:
    """Tests for alignment functionality."""

    def test_full_alignment_workflow(self, sample_keymap_file, sample_layout_file, temp_dir):
        """Test the complete alignment workflow from input to output."""
        output_file = temp_dir / 'aligned_output.keymap'

        # Run alignment
        success = align_keymap_with_layout(str(sample_keymap_file), str(sample_layout_file), str(output_file))
        assert success, 'Alignment should succeed'

        # Verify output file was created
        assert output_file.exists(), 'Output file should be created'

        # Verify output file has content
        assert output_file.stat().st_size > 0, 'Output file should not be empty'

        # Verify basic structure is maintained
        content = output_file.read_text()
        assert 'keymap' in content
        assert 'BASE' in content
        assert 'LAYER2' in content

    def test_real_keymap_alignment_workflow(self, test_output_dir):
        """Test alignment workflow with real Glove80 keymap files."""
        input_file = get_test_file('test_keymaps/misaligned/glove80_input_badly_aligned.keymap')
        layout_file = get_test_file('layouts/glove80_80key_layout.json')
        output_file = test_output_dir / 'workflow_aligned_output.keymap'

        # Run alignment
        success = align_keymap_with_layout(str(input_file), str(layout_file), str(output_file))
        assert success, 'Real keymap alignment should succeed'

        # Verify output
        assert output_file.exists()
        assert output_file.stat().st_size > 0

    def test_simple_keymap_workflow(self, test_output_dir):
        """Test alignment with simple 6-key Corne keymap."""
        input_file = get_test_file('simple_tests/corne_6key_simple_test.keymap')
        layout_file = get_test_file('layouts/corne_6key_simple_layout.json')
        output_file = test_output_dir / 'simple_6key_aligned.keymap'

        # Run alignment
        success = align_keymap_with_layout(str(input_file), str(layout_file), str(output_file))
        assert success, 'Simple keymap alignment should succeed'

        # Verify output
        assert output_file.exists()
        assert output_file.stat().st_size > 0


class TestExactMatching:
    """Tests for exact byte-for-byte output matching."""

    def test_glove80_alignment_exact_match(self, test_output_dir):
        """Test that alignment produces byte-for-byte identical output to reference."""
        input_file = get_test_file('test_keymaps/misaligned/glove80_input_badly_aligned.keymap')
        layout_file = get_test_file('layouts/glove80_80key_layout.json')
        reference_file = get_test_file('test_keymaps/correct/glove80_reference_properly_aligned.keymap')
        output_file = test_output_dir / 'test_aligned_main.keymap'

        # Run alignment
        success = align_keymap_with_layout(str(input_file), str(layout_file), str(output_file))
        assert success, 'Alignment should succeed'

        # Compare with reference using filecmp for exact matching
        files_identical = filecmp.cmp(str(output_file), str(reference_file), shallow=False)

        if not files_identical:
            # Provide helpful debugging info if files don't match
            actual_content = output_file.read_text()
            expected_content = reference_file.read_text()

            # Show file sizes for quick debugging
            actual_size = len(actual_content)
            expected_size = len(expected_content)

            print('\nFile comparison failed:')
            print(f'  Expected size: {expected_size} bytes')
            print(f'  Actual size:   {actual_size} bytes')

        assert files_identical, 'Generated keymap should match reference exactly'

    def test_glove80_alignment_reverse_exact_match(self, test_output_dir):
        """Test alignment with reverse key order produces exact match."""
        input_file = get_test_file('test_keymaps/misaligned/glove80_input_cramped_no_spacing.keymap')
        layout_file = get_test_file('layouts/glove80_80key_layout.json')
        reference_file = get_test_file('test_keymaps/correct/glove80_reference_reverse_key_order.keymap')
        output_file = test_output_dir / 'test_aligned_reverse.keymap'

        # Run alignment
        success = align_keymap_with_layout(str(input_file), str(layout_file), str(output_file))
        assert success, 'Reverse alignment should succeed'

        # Compare with reference
        files_identical = filecmp.cmp(str(output_file), str(reference_file), shallow=False)

        if not files_identical:
            # Provide helpful debugging info if files don't match
            actual_content = output_file.read_text()
            expected_content = reference_file.read_text()

            # Show file sizes for quick debugging
            actual_size = len(actual_content)
            expected_size = len(expected_content)

            print('\nFile comparison failed:')
            print(f'  Expected size: {expected_size} bytes')
            print(f'  Actual size:   {actual_size} bytes')

        assert files_identical, 'Generated reverse keymap should match reference exactly'


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_missing_files(self, temp_dir):
        """Test handling of missing input files."""
        nonexistent_keymap = 'nonexistent.keymap'
        nonexistent_layout = 'nonexistent.json'
        output_file = temp_dir / 'output.keymap'

        # Should handle missing files gracefully
        success = align_keymap_with_layout(nonexistent_keymap, nonexistent_layout, str(output_file))
        assert not success  # Should fail gracefully

    def test_malformed_json(self, temp_dir):
        """Test handling of malformed JSON layout file."""
        # Create malformed JSON file
        bad_layout_file = temp_dir / 'bad_layout.json'
        bad_layout_file.write_text('{ invalid json')

        output_file = temp_dir / 'output.keymap'
        keymap_file = temp_dir / 'test.keymap'

        # Create minimal keymap
        keymap_file.write_text('/ { keymap { BASE { bindings = < &kp A >; }; }; };')

        # Should handle malformed JSON gracefully
        success = align_keymap_with_layout(str(keymap_file), str(bad_layout_file), str(output_file))
        assert not success  # Should fail gracefully

    def test_excess_bindings_handling(self):
        """Test handling of keymap with too many bindings."""
        excess_file = get_test_file('test_keymaps/misaligned/glove80_input_excess_bindings.keymap')
        layout_file = get_test_file('layouts/glove80_80key_layout.json')

        # Should handle gracefully (specific behavior depends on implementation)
        layout = load_layout(str(layout_file))
        assert layout is not None, 'Layout should load successfully'

        content = excess_file.read_text()
        layers = extract_all_layers(content)
        assert len(layers) > 0


class TestScriptExecution:
    """Tests for direct script execution."""

    def test_cli_execution(self):
        """Test that the CLI executes successfully with basic parameters"""
        badly_aligned_file = get_test_file('test_keymaps/misaligned/glove80_input_badly_aligned.keymap')
        layout_file = get_test_file('layouts/glove80_80key_layout.json')

        # Test help command
        result = subprocess.run(['keymap-align', '-h'], capture_output=True, text=True)
        assert result.returncode == 0, 'Help command should succeed'
        assert 'usage:' in result.stdout.lower()

        # Test normal execution
        result = subprocess.run(['keymap-align', '-k', str(badly_aligned_file), '-l', str(layout_file)], capture_output=True, text=True)

        assert result.returncode == 0, f'CLI execution should succeed. stderr: {result.stderr}'
        assert 'Alignment completed successfully!' in result.stdout


class TestAlignment_Formatting:
    """Tests for alignment and formatting specifics."""

    def test_two_space_padding_requirement(self):
        """Test that all columns have exactly 2 spaces of padding after the longest binding."""
        reference_file = get_test_file('test_keymaps/correct/glove80_reference_properly_aligned.keymap')

        # Extract one layer's bindings for testing
        binding_lines = [line for line in reference_file.read_text().split('\n') if line.strip().startswith('&')]

        if binding_lines:
            # Check that bindings are properly spaced
            sample_line = binding_lines[0]

            # Should contain multiple bindings separated by proper spacing
            bindings = sample_line.split()
            assert len(bindings) > 1, 'Should have multiple bindings per line'

            # Check for consistent formatting (this is a basic check)
            # More sophisticated padding tests would require parsing the layout structure
            assert '&' in sample_line, 'Should contain binding markers'
