# Advanced Features

## Conditional Dependencies

```yaml
tasks:
  - id: security-scan
    prompt: "Run security scan"
    depends_on: []

  - id: deploy-staging
    prompt: "Deploy to staging"
    depends_on: [security-scan]
    condition: "security-scan.verdict == 'PASS'"  # Only if scan passes
```

## Retry Logic

```yaml
tasks:
  - id: flaky-api-call
    prompt: "Call external API"
    depends_on: []
    retry:
      max_attempts: 3
      backoff: "exponential"  # 1s, 2s, 4s
```

## Timeout Control

```yaml
tasks:
  - id: long-running-task
    prompt: "Process large dataset"
    depends_on: []
    timeout: 600000  # 10 minutes in milliseconds
```
