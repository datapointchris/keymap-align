"""Tests for display-name preservation in keymap_align."""

import json

import pytest

from keymap_align.align import align_keymap_with_layout
from keymap_align.align import build_layer_structure
from keymap_align.align import extract_all_layers


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

    def test_alignment_keeps_each_display_name_line(self, keymap_with_display_names, simple_layout, tmp_path):
        """Aligning leaves each display-name line where it was, and adds none."""
        keymap = tmp_path / 'display_names.keymap'
        keymap.write_text(keymap_with_display_names)
        layout = tmp_path / 'layout.json'
        layout.write_text(json.dumps(simple_layout))

        assert align_keymap_with_layout(str(keymap), str(layout))

        aligned = keymap.read_text()
        assert '            display-name = "BASE";\n' in aligned
        assert '            display-name = "DEV";\n' in aligned
        assert aligned.count('display-name') == 2
