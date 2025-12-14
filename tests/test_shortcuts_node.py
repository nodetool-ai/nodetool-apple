from nodetool.nodes.apple.shortcuts import ListShortcuts, RunShortcut


def test_parse_shortcuts_list_strips_and_filters():
    output = "\n  One  \n\nTwo\n   \nThree\n"
    assert ListShortcuts._parse_shortcuts_list(output) == ["One", "Two", "Three"]


def test_build_command_includes_inputs_output_and_type():
    cmd = RunShortcut._build_command(
        shortcut="My Shortcut",
        input_paths=["/tmp/a.txt", "/tmp/b.pdf"],
        output_path="/tmp/out",
        output_type="public.plain-text",
    )
    assert cmd == [
        "shortcuts",
        "run",
        "My Shortcut",
        "--output-path",
        "/tmp/out",
        "--output-type",
        "public.plain-text",
        "--input-path",
        "/tmp/a.txt",
        "--input-path",
        "/tmp/b.pdf",
    ]
