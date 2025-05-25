import pytest
from nodetool.nodes.apple import calendar, notes, messages, speech, dictionary

CASES = [
    (calendar.CreateCalendarEvent, False),
    (calendar.ListCalendarEvents, False),
    (notes.CreateNote, False),
    (notes.ReadNotes, False),
    (messages.SendMessage, False),
    (speech.SayText, False),
    (dictionary.SearchDictionary, True),
]


@pytest.mark.parametrize("node_cls,expected", CASES)
def test_node_is_cacheable(node_cls, expected):
    assert node_cls.is_cacheable() is expected
