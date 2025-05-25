from nodetool.nodes.apple.notes import escape_for_applescript


def test_escape_quotes_and_backslashes():
    text = 'Hello "World" \\ Test'
    expected = 'Hello \\"World\\" \\\\ Test'
    assert escape_for_applescript(text) == expected


def test_escape_newlines():
    text = "line1\nline2"
    assert escape_for_applescript(text) == "line1\\nline2"
