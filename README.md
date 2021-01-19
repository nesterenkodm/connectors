# Connectors
JIRA, Gitlab, Slack connectors on python

# Usage

```python
from connector import JIRAConnector

jira = JIRAConnector(jira_url, jira_username, jira_password, debug)
result = jira.user(jira.username)

print(json.dumps(result, indent=4, ensure_ascii=False))
```
