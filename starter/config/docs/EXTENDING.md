# Extending The Config Subsystem

This subsystem is the shared configuration core for future starter subsystems.

## Rules

1. Add new subsystem defaults as a new config group under `conf/`.
2. Keep subsystem-owned schema inside the subsystem package itself.
3. Expose the subsystem in `AppConfig` as a section passed through to the owning subsystem.
4. Keep secrets out of YAML. Use `oc.env` and validate presence in the subsystem validation layer.
5. Register only generic resolvers in `resolvers.py`. Avoid business logic there.
6. Keep cross-cutting validation in `starter.config`, and backend-specific validation in the owning subsystem.
7. Add tests for:
   - default composition
   - group override
   - invalid configuration
   - secret redaction if the subsystem carries credentials

## Integration Pattern

The current architecture is intentionally decoupled:

- `starter.config` composes the full config
- downstream subsystems receive only their own config section
- downstream subsystems parse and validate their own section
- bootstrap code wires subsystems together

## Example Pattern For A New Subsystem

For a subsystem such as `artifacts`:

1. add `conf/artifacts/default.yaml`
2. update [`conf/config.yaml`](../../../conf/config.yaml) with `- artifacts: default`
3. add `starter/artifacts/core/schema.py`
4. add `starter/artifacts/core/validate.py`
5. add `starter/artifacts/core/factory.py`
6. add `starter/artifacts/README.md`
7. expose `artifacts` in `AppConfig` (in `starter.config.core.schema`)
8. validate artifacts-specific constraints inside `starter.artifacts`

## Stability Boundary

The config core owns:

- composition
- schema
- validation
- secret redaction
- root config discovery

Individual subsystems should only contribute:

- their own config groups
- their own schema section
- their own validation rules

They should not replace the config loading mechanism itself.
