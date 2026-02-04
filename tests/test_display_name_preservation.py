"""Tests for display-name preservation in keymap_align."""

import pytest

from keymap_align.align import build_layer_structure
from keymap_align.align import calculate_column_widths
from keymap_align.align import extract_all_layers
from keymap_align.align import format_layer


class TestDisplayNamePreservation:
    """Tests for display-name property preservation."""

    @pytest.fixture
    def keymap_with_display_names(self):
        """Sample keymap content with display-name properties."""
        return """
#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>

/ {
    keymap {
        compatible = "zmk,keymap";

        BASE {
            display-name = "BASE";
            bindings = <
                &kp Q  &kp W  &kp E  &kp R
                &kp A  &kp S  &kp D  &kp F
                       &kp Z  &kp X
            >;
        };

        DEV {
            display-name = "DEV";
            bindings = <
                &kp N1 &kp N2 &kp N3 &kp N4
                &kp N5 &kp N6 &kp N7 &kp N8
                       &kp N9 &kp N0
            >;
        };

        LAYER_NO_DISPLAY {
            bindings = <
                &kp F1 &kp F2 &kp F3 &kp F4
                &kp F5 &kp F6 &kp F7 &kp F8
                       &kp F9 &kp F10
            >;
        };
    };
};
"""

    @pytest.fixture
    def simple_layout(self):
        """Simple layout for testing."""
        return {'layout': [['X', 'X', 'X', 'X'], ['X', 'X', 'X', 'X'], ['-', 'X', 'X', '-']], 'name': 'Test Layout'}

    def test_extract_all_layers_with_display_names(self, keymap_with_display_names):
        """Test that display-name properties are extracted correctly."""
        layers = extract_all_layers(keymap_with_display_names)

        assert len(layers) == 3
        assert 'BASE' in layers
        assert 'DEV' in layers
        assert 'LAYER_NO_DISPLAY' in layers

        # Check BASE layer
        base_layer = layers['BASE']
        assert isinstance(base_layer, dict)
        assert 'bindings' in base_layer
        assert 'display_name' in base_layer
        assert base_layer['display_name'] == 'BASE'
        assert len(base_layer['bindings']) == 10
        assert base_layer['bindings'][0] == '&kp Q'

        # Check DEV layer
        dev_layer = layers['DEV']
        assert isinstance(dev_layer, dict)
        assert dev_layer['display_name'] == 'DEV'
        assert len(dev_layer['bindings']) == 10
        assert dev_layer['bindings'][0] == '&kp N1'

        # Check layer without display-name
        no_display_layer = layers['LAYER_NO_DISPLAY']
        assert isinstance(no_display_layer, dict)
        assert no_display_layer['display_name'] is None
        assert len(no_display_layer['bindings']) == 10
        assert no_display_layer['bindings'][0] == '&kp F1'

    def test_build_layer_structure_preserves_display_names(self, keymap_with_display_names, simple_layout):
        """Test that build_layer_structure preserves display-name information."""
        layers = extract_all_layers(keymap_with_display_names)
        structured = build_layer_structure(layers, simple_layout)

        assert len(structured) == 3

        # Check BASE layer structure
        base_structure = structured['BASE']
        assert isinstance(base_structure, dict)
        assert 'rows' in base_structure
        assert 'display_name' in base_structure
        assert base_structure['display_name'] == 'BASE'
        assert len(base_structure['rows']) == 3  # 3 rows in layout

        # Check DEV layer structure
        dev_structure = structured['DEV']
        assert dev_structure['display_name'] == 'DEV'

        # Check layer without display-name
        no_display_structure = structured['LAYER_NO_DISPLAY']
        assert no_display_structure['display_name'] is None

    def test_format_layer_includes_display_names(self, keymap_with_display_names, simple_layout):
        """Test that format_layer includes display-name in output."""
        layers = extract_all_layers(keymap_with_display_names)
        structured = build_layer_structure(layers, simple_layout)
        column_widths = calculate_column_widths(structured, simple_layout)

        # Test layer with display-name
        base_formatted = format_layer('BASE', structured['BASE'], column_widths)
        assert 'display-name = "BASE";' in base_formatted
        assert 'BASE {' in base_formatted
        assert 'bindings = <' in base_formatted

        # Test layer without display-name
        no_display_formatted = format_layer('LAYER_NO_DISPLAY', structured['LAYER_NO_DISPLAY'], column_widths)
        assert 'display-name' not in no_display_formatted
        assert 'LAYER_NO_DISPLAY {' in no_display_formatted
        assert 'bindings = <' in no_display_formatted

    def test_display_name_with_special_characters(self):
        """Test display-name with special characters and spaces."""
        keymap_content = """
/ {
    keymap {
        compatible = "zmk,keymap";

        LAYER_1 {
            display-name = "My Layer!";
            bindings = <&kp A &kp B>;
        };

        LAYER_2 {
            display-name = "Layer with spaces & symbols";
            bindings = <&kp C &kp D>;
        };
    };
};
"""
        layers = extract_all_layers(keymap_content)

        assert layers['LAYER_1']['display_name'] == 'My Layer!'
        assert layers['LAYER_2']['display_name'] == 'Layer with spaces & symbols'

    def test_display_name_edge_cases(self):
        """Test edge cases for display-name parsing."""
        keymap_content = """
/ {
    keymap {
        compatible = "zmk,keymap";

        LAYER_1 {
            display-name = "";
            bindings = <&kp A &kp B>;
        };

        LAYER_2 {
            display-name = "Single";
            bindings = <&kp C &kp D>;
        };

        LAYER_3 {
            display-name="NoSpaces";
            bindings = <&kp E &kp F>;
        };
    };
};
"""
        layers = extract_all_layers(keymap_content)

        assert layers['LAYER_1']['display_name'] == ''
        assert layers['LAYER_2']['display_name'] == 'Single'
        assert layers['LAYER_3']['display_name'] == 'NoSpaces'

    def test_mixed_layers_with_and_without_display_names(self):
        """Test parsing keymap with mix of layers with and without display-name."""
        keymap_content = """
/ {
    keymap {
        compatible = "zmk,keymap";

        BASE {
            display-name = "Base Layer";
            bindings = <&kp A &kp B &kp C &kp D>;
        };

        LAYER_2 {
            bindings = <&kp E &kp F &kp G &kp H>;
        };

        LAYER_3 {
            display-name = "Third";
            bindings = <&kp I &kp J &kp K &kp L>;
        };
    };
};
"""
        layers = extract_all_layers(keymap_content)

        assert len(layers) == 3
        assert layers['BASE']['display_name'] == 'Base Layer'
        assert layers['LAYER_2']['display_name'] is None
        assert layers['LAYER_3']['display_name'] == 'Third'

    def test_full_workflow_preserves_display_names(self, keymap_with_display_names, simple_layout):
        """Test that the full alignment workflow preserves display-name properties."""
        # Extract layers
        layers = extract_all_layers(keymap_with_display_names)

        # Build structure
        structured = build_layer_structure(layers, simple_layout)

        # Calculate widths
        column_widths = calculate_column_widths(structured, simple_layout)

        # Format each layer
        formatted_layers = {}
        for layer_name, layer_data in structured.items():
            formatted_layers[layer_name] = format_layer(layer_name, layer_data, column_widths)

        # Verify display-names are preserved
        assert 'display-name = "BASE";' in formatted_layers['BASE']
        assert 'display-name = "DEV";' in formatted_layers['DEV']
        assert 'display-name' not in formatted_layers['LAYER_NO_DISPLAY']

        # Verify bindings are still present
        for layer_formatted in formatted_layers.values():
            assert 'bindings = <' in layer_formatted
            assert '>;' in layer_formatted
