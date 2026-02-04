# Test configuration and fixtures

# Test data for various binding types
COMPLEX_BINDINGS_TEST_DATA = {
    'simple_keys': [
        '&kp Q', '&kp W', '&kp E', '&kp R', '&kp T',
        '&kp A', '&kp S', '&kp D', '&kp F', '&kp G'
    ],

    'home_row_mods': [
        '&hml LGUI A', '&hml LALT S', '&hml LCTRL D', '&hml LSHFT F',
        '&hmr RSHFT J', '&hmr RCTRL K', '&hmr RALT L', '&hmr RGUI SEMI'
    ],

    'layer_taps': [
        '&ltl LAYER1 G', '&ltr LAYER2 H', '&lt 1 SPACE', '&lt 2 TAB'
    ],

    'complex_behaviors': [
        '&hmr &caps_word RALT', '&magic MAGIC 0',
        '&td TAP_DANCE_0', '&sk LSHIFT'
    ],

    'bluetooth': [
        '&bt BT_CLR', '&bt BT_SEL 0', '&bt BT_SEL 1', '&bt BT_SEL 2',
        '&bt BT_DISC 0', '&out OUT_TOG', '&out OUT_USB', '&out OUT_BLE'
    ],

    'media_keys': [
        '&kp C_VOL_UP', '&kp C_VOL_DN', '&kp C_MUTE', '&kp C_PLAY_PAUSE',
        '&kp C_NEXT', '&kp C_PREV', '&kp C_BRI_UP', '&kp C_BRI_DN'
    ],

    'rgb_controls': [
        '&rgb_ug RGB_TOG', '&rgb_ug RGB_BRI', '&rgb_ug RGB_BRD',
        '&rgb_ug RGB_SPI', '&rgb_ug RGB_SPD', '&rgb_ug RGB_EFF'
    ],

    'mouse_keys': [
        '&mkp LCLK', '&mkp RCLK', '&mkp MCLK', '&mkp MB4', '&mkp MB5',
        '&mmv MOVE_UP', '&mmv MOVE_DOWN', '&mmv MOVE_LEFT', '&mmv MOVE_RIGHT',
        '&msc SCRL_UP', '&msc SCRL_DOWN', '&msc SCRL_LEFT', '&msc SCRL_RIGHT'
    ],

    'system_keys': [
        '&sys_reset', '&bootloader', '&kp PSCRN', '&kp SLCK', '&kp PAUSE_BREAK'
    ],

    'modifiers': [
        '&kp LSHIFT', '&kp RSHIFT', '&kp LCTRL', '&kp RCTRL',
        '&kp LALT', '&kp RALT', '&kp LGUI', '&kp RGUI'
    ],

    'special_keys': [
        '&trans', '&none', '&tog 1', '&to 0', '&mo 2'
    ]
}

# Layouts for testing different keyboard sizes
TEST_LAYOUTS = {
    'small_3x3': {
        "name": "Small 3x3 Test Layout",
        "rows": 3,
        "columns": 3,
        "layout": [
            [True, True, True],
            [True, True, True],
            [True, True, True]
        ]
    },

    'split_4x5': {
        "name": "Split 4x5 Test Layout",
        "rows": 4,
        "columns": 10,
        "layout": [
            [True, True, True, True, True, False, False, True, True, True],
            [True, True, True, True, True, False, False, True, True, True],
            [True, True, True, True, True, False, False, True, True, True],
            [False, False, True, True, False, False, False, False, True, True]
        ]
    }
}
