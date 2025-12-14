import platform

IS_MACOS = platform.system() == "Darwin"

if IS_MACOS:
    # macOS specific imports
    import nodetool.nodes.apple.calendar
    import nodetool.nodes.apple.clipboard
    import nodetool.nodes.apple.contacts
    import nodetool.nodes.apple.dictionary
    import nodetool.nodes.apple.messages
    import nodetool.nodes.apple.notifications
    import nodetool.nodes.apple.notes
    import nodetool.nodes.apple.reminders
    import nodetool.nodes.apple.safari
    import nodetool.nodes.apple.screen
    import nodetool.nodes.apple.spotlight
    import nodetool.nodes.apple.shortcuts
    import nodetool.nodes.apple.speech
    import nodetool.nodes.apple.vision
