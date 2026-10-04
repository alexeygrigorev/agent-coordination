from adapters.aplexer_ssh import main


def test_devices_lists_allowlist(capsys):
    code = main(["--registry", "examples/devices.example.json", "devices"])
    assert code == 0
    out = capsys.readouterr().out
    assert "hetzner-rmthz" in out
    assert "windows-desktop" in out
    assert "ssh-client-host" in out
