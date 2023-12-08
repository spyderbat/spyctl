TEMPLATES = [
    {
        "display_name": "Agent Offline",
        "id": "nc_tmpl:000000001",
        "description": "Send a notification when Spyderbat detects it is no longer receiving data from an Agent (Nano Agent or Clustermonitor, ephemeral or not).",
        "type": "agent_health",
        "config": {
            "schema_type": "event_opsflag",
            "sub_schema": "agent_offline",
            "condition": "",
            "title": "Spyderbat Agent Detected Offline",
            "message": "{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Hostname": "{{ hostname }}",
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Cluster": "{{ __cluster__ }}",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":red_circle:",
            },
        },
    },
    {
        "display_name": "Agent Back Online",
        "id": "nc_tmpl:000000002",
        "description": "Send a notification when Spyderbat detects that an Agent has come back online and is sending data.",
        "type": "agent_health",
        "config": {
            "schema_type": "event_opsflag",
            "sub_schema": "agent_online",
            "condition": "",
            "title": "Spyderbat Agent Back Online",
            "message": "{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Hostname": "{{ hostname }}",
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Cluster": "{{ __cluster__ }}",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":large_green_circle:",
            },
        },
    },
    {
        "display_name": "Agent CPU Usage Over Threshold",
        "id": "nc_tmpl:000000003",
        "description": "Send a notification when an Agent's total CPU usage is over 4% for 2 minutes. (30 minute cooldown)",
        "type": "agent_health",
        "config": {
            "schema_type": "event_metric",
            "sub_schema": "agent",
            "condition": "cpu_1min_P.agent > 0.04",
            "for_duration": 120,
            "cooldown": 1800,
            "title": "Spyderbat Agent CPU Over Threshold For 2 Minutes",
            "message": "{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Hostname": "{{ hostname }}",
                    "Cluster": "{{ __cluster__ }}",
                    "CPU Used (%)": "{{ __percent__ | cpu_1min_P.agent }} (Threshold: 4%)",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":large_yellow_circle:",
            },
        },
    },
    {
        "display_name": "Agent Memory Over Threshold",
        "id": "nc_tmpl:000000004",
        "description": "Send a notification when an Agent's memory usage is over 3.5GB for 2 minutes. (30 minute cooldown)",
        "type": "agent_health",
        "config": {
            "schema_type": "event_metric",
            "sub_schema": "agent",
            "condition": "mem_1min_B.agent > 3758096384",
            "for_duration": 120,
            "cooldown": 1800,
            "title": "Spyderbat Agent Memory Usage Over Threshold For 2 Minutes",
            "message": "{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Hostname": "{{ hostname }}",
                    "Cluster": "{{ __cluster__ }}",
                    "Memory Used (%)": "{{ __percent__ | mem_1min_P.agent }}",
                    "Memory Used (bytes)": "{{ mem_1min_B.agent }}B (Threshold: 3.5GB)",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":large_yellow_circle:",
            },
        },
    },
    {
        "display_name": "Agent Bandwidth Over Threshold",
        "id": "nc_tmpl:000000005",
        "description": "Send a notification when an Agent's bandwidth usage is over 125 KBps for 2 minutes. (30 minute cooldown)",
        "type": "agent_health",
        "config": {
            "schema_type": "event_metric",
            "sub_schema": "agent",
            "condition": "bandwidth_1min_Bps > 125000",
            "for_duration": 120,
            "cooldown": 1800,
            "title": "Spyderbat Agent Bandwidth Usage Over Threshold For 2 Minutes",
            "message": "{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Hostname": "{{ hostname }}",
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Cluster": "{{ __cluster__ }}",
                    "Bandwidth Used (Bps)": "{{ bandwidth_1min_Bps }} Bps (Threshold: 125,000 Bps)",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":large_yellow_circle:",
            },
        },
    },
    {
        "display_name": "Bat Offline",
        "id": "nc_tmpl:000000006",
        "description": "Send a notification when a Bat goes offline.",
        "type": "agent_health",
        "config": {
            "schema_type": "event_opsflag",
            "sub_schema": "bat_offline",
            "condition": "",
            "title": "Spyderbat Bat Offline",
            "message": "{{ description }}\n\n{{ __origin__ }}",
            "cooldown": 900,
            "additional_fields": {
                "details": {
                    "Hostname": "{{ hostname }}",
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Bat": "{{ bat_name }}",
                    "Severity": "{{ severity }}",
                    "Cluster": "{{ __cluster__ }}",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":red_circle:",
            },
        },
    },
    {
        "display_name": "Bat Online",
        "id": "nc_tmpl:000000007",
        "description": "Send a notification when a Bat comes back online.",
        "type": "agent_health",
        "config": {
            "schema_type": "event_opsflag",
            "sub_schema": "bat_online",
            "condition": "",
            "title": "Spyderbat Bat Back Online",
            "message": "{{ description }}\n\n{{ __origin__ }}",
            "cooldown": 900,
            "additional_fields": {
                "details": {
                    "Hostname": "{{ hostname }}",
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Bat": "{{ bat_name }}",
                    "Severity": "{{ severity }}",
                    "Cluster": "{{ __cluster__ }}",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":large_green_circle:",
            },
        },
    },
    {
        "display_name": "SSH Login Detection",
        "id": "nc_tmpl:00000008",
        "description": "Send a notification when Spyderbat detects an interactive SSH login.",
        "type": "security",
        "config": {
            "schema_type": "event_redflag",
            "sub_schema": "remote_access",
            "condition": 'description ~= "*ssh*"',
            "title": "SSH Login Detected",
            "message": "{{ description }}\n\n{{ __origin__ }}",
            "additional_fields": {
                "details": {
                    "Time": "{{ __hr_time__ }}",
                    "Source UID": "{{ muid }}",
                    "Cluster": "{{ __cluster__ }}",
                    "Logged In As": "{{ euser }}",
                    "From IP": "{{ remote_ip }}",
                },
                "linkback_text": "View in Spyderbat",
                "linkback_url": "{{ __linkback__ }}",
                "slack_icon": ":triangular_flag_on_post:",
            },
        },
    },
]