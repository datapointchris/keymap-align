"""`keymap-align update` and the update notice share one pyselfupdate config."""

from typer.testing import CliRunner

from keymap_align import cli


def test_update_installs_this_tool_and_skips_the_notice_it_would_duplicate(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, 'run_update', lambda config, **kwargs: calls.append((config, kwargs)))
    notices = []
    monkeypatch.setattr(cli, 'notify', notices.append)

    result = CliRunner().invoke(cli.app, ['update', '--check'])
    CliRunner().invoke(cli.app, ['layouts', 'list'])

    assert result.exit_code == 0
    assert [((config.tool, config.owner), kwargs) for config, kwargs in calls] == [
        (('keymap-align', 'datapointchris'), {'check_only': True})
    ]
    assert notices == [cli.UPDATE_CONFIG]
