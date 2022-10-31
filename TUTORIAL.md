# Spyctl Tutorial

## Examples

Get container fingerprints for all pods in all clusters
```
spyctl get pods | spyctl get fingerprints container --pods
```
Get pods from 2 hours in the past
```
spyctl get pods --time 2h > pods.txt
```
Find all machines in a cluster
```
spyctl get machines --cluster mycluster1
```
Merge contianer fingerprints of all "test-pod-*" pods within the last day
```
spyctl get pods --within 1d --filter "name=test-pod-" > pods.txt
spyctl get fingerprints container --within 1d --pods pods.txt | spyctl merge
```

## General argument details

- `--help` can be used for all commands to list subcommands or available arguments.
- Object inputs can be given as files, regular text, or piped
  - `spyctl get fingerprints --pods file_with_pods.txt`
  - `spyctl get fingerprints --pods my-pod-fsd23`
  - `spyctl get pods --namespace default | spyctl get fingerprints --pods`
- Time inputs are minutes back if not specified, but other formats can be given
  - `-t 15`: 15 minutes ago
  - `-t 2h`: 2 hours ago
  - `-t 15:30`: 3:30 PM today
  - `-t 01-01-2022`: Jan 1, 2022 (12:00 AM)
- Outputs can be filtered because tools like grep are difficult with multiline outputs
  - `-f "kube"`: matches any object with a value containing "kube"
  - `-f "name=aws-"`: matches any object with a global name field containing "aws-"
  - `-f "metadata.name=cont"`: matches any object with a name field inside a metadata field containing "cont"
