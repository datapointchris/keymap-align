# keymap-align

A CLI that rewrites a ZMK `.keymap` file so each layer's bindings sit in columns matching the
keyboard's physical shape. A JSON layout marks each grid cell as a key (`"X"`) or a gap (`"-"`),
and that grid is all the tool knows about the board.

## The rewrite regenerates the whole `keymap` node and keeps only what it parsed

`align_keymap_with_layout` (`align.py`) replaces everything from the first line containing
`keymap {` through its matching close brace. It rebuilds that span from what `extract_all_layers`
captured for each layer: the node name, an optional `display-name`, and the bindings. Lines outside
the span are kept unchanged. Inside it, a run drops the following and still exits 0 with a success
message:

- comments and blank lines between layers;
- any property after `bindings`, such as `sensor-bindings`;
- a whole layer whose node holds a property other than `display-name` before `bindings`;
- bindings beyond the layout's key count. A layer with too few gets a blank cell for each one
  missing.

A layer node name is matched as `\w+`, so `nav-layer` is written back as `layer`. The test fixtures
hold nothing in the node but layers, so no test catches a loss there.

## A binding ends at the next `&`, so a behavior-valued parameter must be declared

ZMK's `bindings = < … >` is a flat token list. Nothing separates one binding from the next, so the
tokenizer starts a new binding at each token beginning with `&`. A parameter that is itself a
behavior, as in `&hmr &caps_word RALT`, would become its own binding. Every later binding in the
layer would then shift one key along.

`MULTI_PARAM_BEHAVIORS` names the behaviors whose parameters may be behaviors. Inside
`_handle_multi_param_behavior`, `behavior_param_rules` holds each one's parameter count, and a
tuple names the ones that take a behavior in second position. The set and both tables describe one
fact and must agree. The names in them are user-defined hold-taps, not ZMK built-ins. A keymap whose
own hold-tap takes a behavior parameter under another name misparses without an error.

`DIMMED_BEHAVIORS`, `KEYPRESS_BEHAVIORS` and `STOCK_ZMK_BEHAVIORS` only color `--debug` output.

## Column widths are shared by every layer

Each column's width is its widest binding across all layers, plus `padding`. A key therefore sits
in the same column on every layer. Binding rows are indented one level, shallower than the
`bindings = <` line above them, because a wide board's rows are long already. Every indent is a
multiple of `indent_size`.

## The layout is found from the keymap's directory, not the working directory

The layout comes from `--layout-file`, then `--layout`, then the `layout` key of the nearest
`keymap_align.toml`. The config search starts in the keymap file's directory and walks up to the
git root, or to the filesystem root outside a repository. That lets an editor formatter such as
conform.nvim pass nothing but `-k`, from whatever directory the editor runs in.

- A `--layout` or config value is a path when it contains `/` or `\` or ends in `.json`, and a
  bundled board name otherwise. The rule is written in both `config.py` and `layout_resolver.py`,
  and the two copies must agree.
- A path in the config file resolves against the config file's directory. A path on the command
  line resolves against the working directory.
- `indent_size` and `padding` come only from the config file. No flag sets them.
- A config file that fails to parse prints a warning to stderr, and the run continues without it.

## A bundled board is a file, and nothing else registers it

Each JSON file in `src/keymap_align/layouts/` is one board, named by its file stem. `--layout` and
`--list-layouts` read that directory through `importlib.resources`, so adding a file adds a board.
The aligner reads `layout`, and reads `name` only for `--debug`. The `key_positions` grid in the
bundled files is read by nothing.

## The golden tests compare bytes, and the suite rewrites one of their inputs

- pytest is in the `test` dependency group, which a plain `uv sync` leaves out.
  `uv sync --all-groups` installs it. CI supplies it with `uv run --with pytest`.
- The exact-match tests compare output byte for byte against `tests/test_keymaps/correct/`, at the
  default `indent_size` and `padding`. A change to either default, or to any output formatting,
  means regenerating those references. Test output lands in the gitignored
  `tests/test_keymaps/test_output/`, which is where to diff a failing match.
- `test_cli_execution` aligns `misaligned/glove80_input_badly_aligned.keymap` in place, with no
  `-o`. That input is therefore identical to its reference, and the exact-match test on it checks
  only that aligned input stays unchanged. After a formatting change, the next test run rewrites
  it, and the diff looks like a fixture update. `glove80_input_cramped_no_spacing.keymap` is the
  input the suite actually realigns.
- `test_cli_execution` runs whichever `keymap-align` is first on `PATH`. Under `uv run` that is
  this checkout. Run any other way, it can be an installed release.
- `get_test_file` skips a test whose fixture is missing, so a renamed fixture turns its tests into
  skips rather than failures.

## The lint, hook and CI configuration is generated outside this repo

A file whose first line marks it managed or stamps a toolchain version is generated from a template
kept outside this repo. `.pre-commit-config.yaml` and `.github/workflows/validate.yml` are two. A
hand edit there is overwritten by the next regeneration. A repo-specific hook goes in a section
marked `# > custom:`, which regeneration keeps.

In `pyproject.toml`, the tool keys in the `managed` record at the bottom belong to the same
template, and a key absent from that record is this project's. The ruff dev pin is held to the
release the ruff hook runs.
