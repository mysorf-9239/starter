# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Security vulnerabilities must not be reported through public GitHub issues.

Report vulnerabilities privately by emailing:

**uydanh214@gmail.com** (Nguyen Duc Danh)

Include the following in the report:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- Affected versions.

A response will be provided within 72 hours. Confirmed vulnerabilities will be
patched as soon as possible. Reporters will be credited unless anonymity is
requested.

## Security Considerations

### Secrets and Credentials

- API keys and credentials must not be committed to `conf/` YAML files.
- Use `oc.env` interpolation to read secrets from environment variables at
  runtime.
- The `redact_secrets()` function masks known secret paths before rendering
  config output.

### Known Secret Paths

| Path | Masked by |
|---|---|
| `tracking.wandb.api_key` | `redact_secrets()` |

### Dependency Security

- All dependencies are pinned with upper bounds in `pyproject.toml`.
- `bandit` runs as part of the pre-commit pipeline to detect common security
  issues in source code.
- Run `pip audit` periodically to check for known vulnerabilities in
  installed dependencies.
