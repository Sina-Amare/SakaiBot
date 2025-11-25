# Prioritized Action Plan

## High Priority (Deployment Blockers)

### 1. Create `.env.example` Template File

**Status**: ⚠️ **BLOCKER**

**Impact**: Prevents easy onboarding and deployment

**Action Items**:
1. Create `.env.example` file in project root
2. Include all required and optional environment variables
3. Add comments explaining each variable
4. Provide example values (non-sensitive)
5. Document default values

**File Structure**:
```env
# Telegram API Credentials (REQUIRED)
# Get from https://my.telegram.org
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE_NUMBER=+1234567890

# LLM Provider Selection (REQUIRED)
# Options: 'gemini' or 'openrouter'
LLM_PROVIDER=gemini

# AI Provider API Key (REQUIRED - set the one matching your LLM_PROVIDER)
# For Gemini: Get from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here
# OR for OpenRouter: Get from https://openrouter.ai/
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Optional Configuration
TELEGRAM_SESSION_NAME=sakaibot_session
GEMINI_API_KEY_TTS=your_tts_specific_key  # Optional: Separate TTS key
GEMINI_MODEL=gemini-2.5-flash
OPENROUTER_MODEL=google/gemini-2.5-flash
USERBOT_MAX_ANALYZE_MESSAGES=10000
PATHS_FFMPEG_EXECUTABLE=/usr/local/bin/ffmpeg
ENVIRONMENT=production
DEBUG=false
```

**Estimated Effort**: 30 minutes

**Dependencies**: None

---

### 2. Add Docker Configuration

**Status**: ⚠️ **BLOCKER** (for containerized deployments)

**Impact**: Limits deployment options, prevents modern deployment practices

**Action Items**:
1. Create `Dockerfile`:
   - Base image: `python:3.10-slim`
   - Install FFmpeg
   - Copy requirements and install dependencies
   - Copy application code
   - Set up data directories
   - Configure entry point

2. Create `docker-compose.yml`:
   - Service definition
   - Volume mounts for data, cache, logs
   - Environment variable file
   - Restart policy

3. Create `.dockerignore`:
   - Exclude unnecessary files
   - Exclude virtual environments
   - Exclude test files

4. Update README with Docker instructions

**Estimated Effort**: 2-3 hours

**Dependencies**: None

**Files to Create**:
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`

---

### 3. Document Deployment Process

**Status**: ⚠️ **BLOCKER** (for production deployments)

**Impact**: Users must figure out deployment themselves

**Action Items**:
1. Create `docs/DEPLOYMENT.md` (or add to existing docs)
2. Document VPS deployment steps
3. Document Docker deployment (after Docker config is added)
4. Include systemd service file example
5. Include log rotation configuration
6. Add troubleshooting section

**Estimated Effort**: 2-3 hours

**Dependencies**: Docker configuration (for Docker deployment docs)

---

## Medium Priority (Technical Debt & Optimization)

### 4. Extract Hardcoded Persian Error Messages

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: Cannot easily change language or customize messages

**Action Items**:
1. Create `src/core/messages.py` or `src/utils/messages.py`
2. Extract all hardcoded Persian strings to constants/dictionary
3. Create message formatting functions
4. Update all handlers to use centralized messages
5. Consider i18n system for future multi-language support

**Files to Modify**:
- `src/utils/error_handler.py`
- `src/telegram/handlers/ai_handler.py`
- Other handlers with hardcoded messages

**Estimated Effort**: 4-6 hours

**Dependencies**: None

---

### 5. Set Up CI/CD Pipeline

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: Manual testing and deployment, no automated quality checks

**Action Items**:
1. Create `.github/workflows/ci.yml`:
   - Run tests on push/PR
   - Code quality checks (Black, Ruff, MyPy)
   - Test coverage reporting
   - Upload coverage to service (Codecov, Coveralls)

2. Create `.github/workflows/release.yml` (optional):
   - Automated releases on tag
   - Build and publish to PyPI (if applicable)

3. Set up branch protection rules:
   - Require CI to pass
   - Require code review

**Estimated Effort**: 3-4 hours

**Dependencies**: None

**Example CI Workflow**:
```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov-report=xml
      - run: black --check src tests
      - run: ruff check src tests
      - run: mypy src
```

---

### 6. Add Retry Logic to STT Processing

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: STT failures are not retried, reducing reliability

**Action Items**:
1. Review STT error handling in `src/ai/stt.py`
2. Add retry logic similar to AI providers
3. Use exponential backoff
4. Handle specific error types appropriately
5. Add logging for retry attempts

**Estimated Effort**: 2-3 hours

**Dependencies**: None

**Reference**: See retry logic in `src/ai/providers/gemini.py` or `src/utils/retry.py`

---

### 7. Make Rate Limits Configurable

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: Rate limits are hardcoded, cannot adjust for different use cases

**Action Items**:
1. Add rate limit configuration to `src/core/config.py`:
   - `RATE_LIMIT_MAX_REQUESTS` (default: 10)
   - `RATE_LIMIT_WINDOW_SECONDS` (default: 60)

2. Update `src/utils/rate_limiter.py` to accept configuration

3. Update handlers to use configured rate limits

4. Document in `.env.example`

**Estimated Effort**: 2-3 hours

**Dependencies**: None

---

### 8. Standardize Message Sending

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: Inconsistent message sending patterns

**Action Items**:
1. Audit all message sending locations
2. Identify handlers using `client.send_message()` directly
3. Replace with `MessageSender` class
4. Ensure consistent error handling
5. Update tests if needed

**Estimated Effort**: 3-4 hours

**Dependencies**: None

---

### 9. Extract Command Parsing Logic

**Status**: 🔧 **TECHNICAL DEBT**

**Impact**: Duplicate code, maintenance burden

**Action Items**:
1. Review command parsing in handlers
2. Identify common patterns
3. Create shared parsing utilities in `src/utils/command_parser.py`
4. Refactor handlers to use shared utilities
5. Add tests for parsing utilities

**Estimated Effort**: 4-5 hours

**Dependencies**: None

---

### 10. Add Health Check Endpoint

**Status**: 💡 **OPTIMIZATION**

**Impact**: No way to monitor bot health programmatically

**Action Items**:
1. Enhance `src/core/health.py`:
   - Check Telegram connection
   - Check AI provider availability
   - Check cache status
   - Return JSON health status

2. Add CLI command: `sakaibot health`

3. Consider HTTP endpoint (if adding web interface)

**Estimated Effort**: 2-3 hours

**Dependencies**: None

---

## Low Priority (Nice-to-Haves & Future Enhancements)

### 11. Add Metrics Dashboard

**Status**: 💡 **OPTIMIZATION**

**Impact**: Metrics collected but not visualized

**Action Items**:
1. Export metrics in Prometheus format
2. Set up Grafana dashboard (or simpler alternative)
3. Visualize key metrics:
   - Request counts
   - Error rates
   - Response times
   - Queue sizes

**Estimated Effort**: 4-6 hours

**Dependencies**: None (or Prometheus/Grafana if using)

---

### 12. Implement Database Persistence Option

**Status**: 💡 **FUTURE ENHANCEMENT**

**Impact**: File-based JSON may not scale

**Action Items**:
1. Evaluate database options (SQLite for simplicity, PostgreSQL for scale)
2. Create database abstraction layer
3. Implement migration system
4. Add configuration option to choose storage backend
5. Maintain backward compatibility with JSON files

**Estimated Effort**: 8-12 hours

**Dependencies**: None

**Consideration**: May be over-engineering for current use case

---

### 13. Add Request Deduplication

**Status**: 💡 **OPTIMIZATION**

**Impact**: Same command could be processed multiple times

**Action Items**:
1. Add request ID generation
2. Track recent requests (in-memory cache with TTL)
3. Skip duplicate requests within time window
4. Return cached response for duplicates

**Estimated Effort**: 3-4 hours

**Dependencies**: None

---

### 14. Create Architecture Decision Records (ADRs)

**Status**: 💡 **DOCUMENTATION**

**Impact**: No record of why decisions were made

**Action Items**:
1. Create `docs/adr/` directory
2. Document key architectural decisions:
   - Why Pydantic for configuration?
   - Why provider abstraction pattern?
   - Why file-based persistence?
   - Why Telethon over Pyrogram?
3. Use standard ADR format

**Estimated Effort**: 4-6 hours

**Dependencies**: None

---

### 15. Add Pre-commit Hooks

**Status**: 💡 **DEVELOPER EXPERIENCE**

**Impact**: Developers must manually run quality checks

**Action Items**:
1. Create `.pre-commit-config.yaml`
2. Configure hooks:
   - Black (formatting)
   - Ruff (linting)
   - MyPy (type checking)
   - Trailing whitespace removal
3. Document installation in README
4. Test hooks work correctly

**Estimated Effort**: 1-2 hours

**Dependencies**: None

---

### 16. Enhance Error Tracking

**Status**: 💡 **MONITORING**

**Impact**: Errors logged but not tracked/alerted

**Action Items**:
1. Integrate error tracking service (Sentry, Rollbar)
2. Configure error reporting
3. Set up alerting rules
4. Document in deployment guide

**Estimated Effort**: 2-3 hours

**Dependencies**: Error tracking service account

---

### 17. Add Dependency Lock File

**Status**: 💡 **REPRODUCIBILITY**

**Impact**: Dependencies not locked, builds not reproducible

**Action Items**:
1. Choose approach (pip-tools, poetry, or manual)
2. Generate lock file
3. Update installation instructions
4. Add to CI/CD pipeline

**Estimated Effort**: 1-2 hours

**Dependencies**: None

---

### 18. Create Contributing Guide

**Status**: 💡 **DOCUMENTATION**

**Impact**: No clear contribution guidelines

**Action Items**:
1. Create `CONTRIBUTING.md`
2. Document:
   - Development setup
   - Code style guidelines
   - Testing requirements
   - PR process
   - Commit message format

**Estimated Effort**: 2-3 hours

**Dependencies**: None

---

## Implementation Timeline

### Phase 1: Deployment Readiness (Week 1)
- ✅ Create `.env.example` (30 min)
- ✅ Add Docker configuration (2-3 hours)
- ✅ Document deployment process (2-3 hours)
- **Total**: ~1 day

### Phase 2: Technical Debt (Week 2-3)
- Extract hardcoded messages (4-6 hours)
- Set up CI/CD (3-4 hours)
- Add STT retry logic (2-3 hours)
- Make rate limits configurable (2-3 hours)
- Standardize message sending (3-4 hours)
- **Total**: ~2-3 days

### Phase 3: Optimization (Week 4+)
- Extract command parsing (4-5 hours)
- Add health check endpoint (2-3 hours)
- Add metrics dashboard (4-6 hours)
- Other low-priority items as needed

## Success Criteria

### Deployment Readiness
- [ ] `.env.example` file exists
- [ ] Docker configuration works
- [ ] Deployment documentation complete
- [ ] Can deploy to VPS following docs

### Code Quality
- [ ] No hardcoded error messages
- [ ] CI/CD pipeline passing
- [ ] Test coverage maintained/improved
- [ ] All technical debt items addressed

### Monitoring
- [ ] Health checks working
- [ ] Metrics visible (dashboard or logs)
- [ ] Error tracking configured

## Notes

- **Priority levels** are relative and may change based on project needs
- **Estimated effort** is approximate and may vary
- **Dependencies** should be considered when planning work
- Some items may be combined (e.g., CI/CD and pre-commit hooks)

---

**End of Documentation**

For questions or clarifications, refer to:
- `00_EXECUTIVE_SUMMARY.md` - Overview and priorities
- `01_PROJECT_OVERVIEW.md` - Purpose and technology stack
- `02_ARCHITECTURE.md` - System design
- `03_FEATURES.md` - Feature inventory
- `04_CODE_QUALITY.md` - Technical debt assessment
- `05_DEPLOYMENT.md` - Deployment guide
- `06_DEVELOPMENT.md` - Development context

