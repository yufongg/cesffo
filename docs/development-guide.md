# Development Contribution Guide & Workflow Documentation

This guide outlines how to configure your local environment, manage Git branches, implement testing frameworks, and execute automated quality gating scripts used in Github Actions workflow.

---

## 1. Running the Application in Development

The project utilizes isolated container orchestration configurations to manage structural infrastructure between engineering sandboxes and cloud releases.

### Configuration Strategy

* **`docker-compose.override.yml` (Development):** Loaded automatically by Docker Compose locally. It bind mounts read-write volumes for code hot-reloading, exposes auxiliary debug ports ($5000$, $5432$, etc.), and injects sandbox environmental variable stubs.
* **`docker-compose.yml` (Production):** Used natively in CI/CD cloud native configurations. It enforces strict immutable read-only source paths and keeps ports internal to the virtual mesh network topology.

### Bootstrapping the Local Stack

To build your base local images and launch your isolated runtime dependencies, execute:

```bash
docker compose up --build -d

```

> **Note:** The `-d` (detached) flag releases your active terminal input stream, allowing the services to execute as persistent background system processes.

---

## 2. Git Branch Management Workflow

To protect the production release cycle, engineers must adhere to the following branch topology:

```
[ main ]  ════════════════════════════════════ (Production Deployments)
            ▲
            │ (Major Version Release)
[ dev ]   ════════════════════════════════════ (Staging / Integration Testing)
            ▲                     │
            │ (Merge Feature)     │ (Branch Off)
[ feature/* ] ════════════════════╩═══════════ 

```

* **`main`:** The absolute source of truth. Contains only fully stabilized, production-ready source states. TODO: Automated pipelines deploy code landing here straight to cloud tiers.
* **`dev`:** The central integration branch. Feature tracks aggregate here to be vetted as an integrated stack before generating a major version release into `main`.
* **`feature/<feature-name>`:** Isolated scratchpads for functional updates. Engineers branch off `dev` and open descriptive pull requests back to `dev` upon feature completion.

---

## 3. Writing Backend Python Tests

All Python test modules reside within the `./backend/tests/` directory structure.

### Implementation Rules

1. **Naming Requirements:** File names must utilize the `test_*.py` or  `*_test.py` pattern. Testing functions within these files must start with the `test_` prefix string.

2. **Execution Strategy:** Leverage `unittest.mock.patch` configurations to simulate database mutations without persisting side effects to the database.

### Blueprint Example (`./backend/tests/test_auth.py`)

```python
import pytest
from unittest.mock import patch, Mock
from user.auth import register, ExistingUserError

@pytest.mark.asyncio
@patch("user.auth.get_db_session")
async def test_registration_flow_success(mock_get_db_session):
    """Verifies that registration handles unique credentials cleanly."""
    # Patch internal functions
    mock_session = Mock()
    mock_session.scalar.return_value = None  # Simulates return value when unique account parameters provided
    mock_get_db_session.return_value.__enter__.return_value = mock_session
    
    # Use side effect for function behaviour within that do not return values.
    def mock_refresh_side_effect(target_obj):
        # Assigns userid parameter to the object passed into refresh function.
        target_obj.user_id = uuid4()
        return None
    mock_session.refresh.side_effect = mock_refresh_side_effect 
    # get_db_session().refresh(user1) user1 will now be assigned a new userid in the above mock

    # Initialize test entrypoint
    token, user_id = await register(
        email="dev@test.internal",
        username="testuser1234",
        password="SecurePassword123!",
        password_confirm="SecurePassword123!"
    )
    
    # Assertions
    assert token == ""
    assert isinstance(user_id, str)
    mock_session.add.assert_called_once()

```

---

## 4. Code Quality Gates & Automated Validation

Before pushing mutations upstream, engineers are required to execute local quality gates inside the active `backend` and `frontend` operational contexts.

### Pushing to Feature Branches (`feature/*`)

Run syntax compilation sanity and low-impact static vulnerability analytics for Python:

```bash
# 1. Run Ruff Structural Syntax Checks
docker compose exec -T backend ruff check . --no-cache

# 2. Run Bandit Security Check
docker compose exec -T backend bandit -c ./bandit.yaml -r . -x ./tests

```

### Gate B: Pushing or Merging to Development (`dev`)

Prior to merging a feature track into `dev`, you must pass the full verification matrix (Linters, Security Scans, and Multi-Tier Test Suites):

```bash
# 1. Structural and Security Quality Checks
docker compose exec -T backend ruff check . --no-cache
docker compose exec -T backend bandit -c ./bandit.yaml -r . -x ./tests

# 2. Execute Backend Unit & Integration Tests
docker compose exec -T backend pytest ./tests

# 3. Execute Frontend Vitest Engines
docker compose exec -T frontend npm run test:ci

```

---

## 5. Controlling Code Security Scans via `bandit.yaml`

To avoid alerting on intentional testing scripts or standard infrastructure requirements (like binding to `0.0.0.0` inside localized Docker definitions), maintain an operational `bandit.yaml` ruleset configuration file in your python project root.

### Using `bandit.yaml` to Ignore Alerts

You can selectively silence false positives by tracking specific **Plugin IDs** (e.g., `B104` for hardcoded bind addresses, or `B101` for functional asset testing assertions) inside the profiles array space.

```yaml
# bandit.yaml Configuration Blueprint
# Ref: https://bandit.readthedocs.io/

# Exclude legacy file paths from vulnerability auditing metrics
skips:
  - B101 # Allow standard 'assert' validation expressions inside testing scopes
  - B104 # Allow hardcoded binding mappings to 0.0.0.0 inside secure containers

# Explicit fine-grained behavioral overrides
exclude_dirs:
  - ./tests
  - ./.venv

```

> **Pro-Tip:** If a necessary individual code line triggers an invalid security flag, you can append a native `# nosec` comment modifier inline to instantly skip analysis for that statement:
> ```python
> encryption_key = "debug_key_do_not_use_in_prod"  # nosec (Silences B105 alert string)
> 
> ```
> 
>