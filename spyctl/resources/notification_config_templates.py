TEMPLATES = [
    {
        "display_name": "Nano Agent Offline",
        "description": "This will send a notification to your desired destination when Spyderbat detects it is no longer receiving data from a Nano Agent.",
        "config": {
            "schema": "event_opsflag",
            "condition": 'schema ~= "*agent_offline*" AND ephemeral = false',
            "title": "Spyderbat Nano Agent Detected Offline",
            "message": 'Agent id "{{ ref }}" went offline at {{ __hr_time__ }}.\n\nDetails:\n\tMachine uid: {{ muid }}\n\t{{ __source__ }}',
            "additional_fields": {
                "slack_icon": ":red_circle:",
                "linkback_url": "{{ __linkback__ }}",
                "linkback_text": "View in Spyderbat",
            },
        },
    },
    {
        "display_name": "Nano Agent Online",
        "description": "This will send a notification to your desired destination when Spyderbat detects that a Nano Agent has come back online and is sending data.",
        "config": {
            "schema": "event_opsflag",
            "condition": 'schema ~= "*agent_online*" AND ephemeral = false',
            "title": "Spyderbat Nano Agent Back Online",
            "message": 'Agent id "{{ ref }}" came back online at {{ __hr_time__ }}.\n\nDetails:\n\tMachine uid: {{ muid }}\n\t{{ __source__ }}',
            "additional_fields": {
                "slack_icon": ":large_green_circle:",
                "linkback_url": "{{ __linkback__ }}",
                "linkback_text": "View in Spyderbat",
            },
        },
    },
    {
        "display_name": "Ephemeral Nano Agent Offline",
        "description": "This will send a notification to your desired destination when Spyderbat detects it is no longer receiving data from an ephemeral Nano Agent (This is typically for Nano Agents on Kubernetes Nodes).",
        "config": {
            "schema": "event_opsflag",
            "condition": 'schema ~= "*agent_offline*" AND ephemeral = true',
            "title": "Ephemeral Spyderbat NanoAgent Detected Offline",
            "message": 'Ephemeral Agent id "{{ ref }}" went offline at {{ __hr_time__ }}.\n\nDetails:\n\tMachine uid: {{ muid }}\n\t{{ __source__ }}',
            "additional_fields": {
                "slack_icon": ":large_yellow_circle:",
                "linkback_url": "{{ __linkback__ }}",
                "linkback_text": "View in Spyderbat",
            },
        },
    },
]
