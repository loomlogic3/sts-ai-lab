# STS AI Governance

STS AI Lab follows a license-aware and replaceable-model architecture.

## Principles

- Open architecture.
- Replaceable model providers.
- License-aware model selection.
- No production deployment without reviewing model terms.
- Prefer safe, auditable, modular systems.

## Current Development Models

| Model | Use | Status |
|---|---|---|
| llama3.2:1b | Local development experiments | Development only until license review |
| sts-fast | Local optimized profile based on llama3.2:1b | Development only until license review |

## Production Rule

Before any STS AI product is used commercially or deployed for clients:

1. Review the model license.
2. Record approved use cases.
3. Record restrictions.
4. Confirm commercial permission.
5. Confirm data privacy requirements.
6. Keep model/provider replaceable.

## Architecture Rule

STS AI Engine must not depend permanently on one model provider.

The engine should support:

- Local models
- Cloud APIs
- Future STS-trained models
- Replaceable inference backends

## Long-Term Direction

STS should gradually move toward:

1. Local AI experimentation.
2. License-reviewed production models.
3. Domain-specific datasets.
4. Fine-tuning or adapters where legally allowed.
5. Future STS-owned small models for narrow tasks.
