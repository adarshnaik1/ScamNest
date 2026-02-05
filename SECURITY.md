# Security Policy

## Overview

ScamNest takes security seriously. This document outlines our security practices, how to report vulnerabilities, and guidelines for secure deployment.

## 🔒 Security Standards

This project adheres to:
- **GitGuardian** secret detection standards
- **OWASP** security best practices
- **CWE Top 25** vulnerability prevention
- **Zero Trust** architecture principles

---

## 🚨 Reporting Security Vulnerabilities

### Do NOT:
- Open public GitHub issues for security vulnerabilities
- Disclose vulnerabilities publicly before patch is available
- Test vulnerabilities on production systems

### DO:
1. **Email**: Contact the maintainer through GitHub (create a security advisory)
2. **GitHub Security Advisories**: Use the "Security" tab in the repository
3. **Provide Details**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline
- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity (Critical: 7 days, High: 14 days, Medium: 30 days)

---

## 🛡️ Security Best Practices

### 1. Secrets Management

#### ❌ NEVER:
- Commit `.env` files
- Hardcode API keys, passwords, or tokens
- Share credentials in documentation or comments
- Use default or weak credentials

#### ✅ ALWAYS:
- Use `.env` files (git-ignored)
- Store secrets in environment variables
- Use `.env.example` as a template
- Rotate credentials regularly
- Use strong, unique API keys

**Generate Strong API Keys:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. API Security

#### Authentication
- **Mandatory** `x-api-key` header for all requests
- Implement rate limiting in production
- Log failed authentication attempts
- Monitor for unusual patterns

#### Input Validation
- Validate all incoming data
- Sanitize user inputs
- Implement request size limits
- Use Pydantic for schema validation

#### Example Secure Configuration:
```python
# config/security.py
import secrets

class SecurityConfig:
    API_KEY_MIN_LENGTH = 32
    MAX_REQUEST_SIZE = 10_000  # characters
    RATE_LIMIT_PER_MINUTE = 30
    ENABLE_REQUEST_LOGGING = True
    
    @staticmethod
    def generate_api_key() -> str:
        return secrets.token_urlsafe(32)
```

### 3. OpenAI API Security

- **Never** log or store OpenAI API keys
- Use environment variables only
- Set timeout limits for API calls
- Implement retry with exponential backoff
- Monitor usage and costs

#### Example Usage:
```python
from app.config import get_settings

settings = get_settings()
# API key is loaded but never logged
openai_client = OpenAI(api_key=settings.openai_api_key)
```

### 4. Data Masking and De-masking

#### Masking for PII Protection
- **Automatic masking** in logs, debug output, and public APIs
- **Three masking levels**: FULL, PARTIAL, MINIMAL
- **Context-aware**: Different masking for logs vs callbacks
- **GDPR/CCPA compliant**: Protects sensitive personal data

#### Supported Data Types:
```python
from app.services.data_masker import DataMasker

# API keys: sk-proj-abc123...xyz789 -> sk-proj-***...xyz789
DataMasker.mask_api_key("sk-proj-abc123xyz789")

# Phone: +91-9876543210 -> +91-98***43210
DataMasker.mask_phone_number("+91-9876543210")

# UPI: user@paytm -> u***@paytm
DataMasker.mask_upi_id("user@paytm")

# Bank: 123456789012 -> ****6789012
DataMasker.mask_bank_account("123456789012")

# Email: john.doe@example.com -> j***@example.com
DataMasker.mask_email("john.doe@example.com")
```

#### When to Use Masking:
✅ **DO mask** in:
- Log files and debug output
- API responses (non-callback)
- Error messages
- Monitoring dashboards
- Public displays

❌ **DON'T mask** in:
- Callback payloads to GUVI endpoint
- Internal processing (ML models)
- Session state (in-memory)
- Database storage (if encrypted)

#### De-masking:
```python
from app.services.data_masker import DemaskedData

# Create de-masked container
sensitive = DemaskedData(original_data)

# Access only when needed
actual_data = sensitive.get()  # Logs access for audit

# Safe logging (automatically redacted)
logger.info(f"Processing: {sensitive}")  # Logs: [REDACTED]
```

### 5. Session Security

- Don't store sensitive data in sessions
- Implement session timeouts
- Clear expired sessions regularly
- Consider encryption for session data

### 5. Dependency Security

#### Scan Dependencies:
```bash
# Install safety
pip install safety

# Scan for vulnerabilities
safety check

# Or use pip-audit
pip install pip-audit
pip-audit
```

#### Keep Dependencies Updated:
```bash
pip list --outdated
pip install --upgrade package-name
```

### 6. Production Deployment Security

#### Environment Configuration:
```env
ENV=production
DEBUG=false
LOG_LEVEL=WARNING
ENABLE_RATE_LIMITING=true
```

#### Checklist:
- [ ] All secrets in environment variables
- [ ] Debug mode disabled
- [ ] Rate limiting enabled
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Logging and monitoring active
- [ ] Regular security audits scheduled

### 7. Data Protection

#### Extracted Intelligence:
- Sanitize before logging
- Don't store beyond necessary retention period
- Consider encryption at rest
- Comply with data protection regulations (GDPR, CCPA)

#### PII Handling:
- Minimize collection
- Anonymize when possible
- Secure transmission (HTTPS)
- Document retention policies

---

## 🔍 Security Scanning

### Pre-commit Checks

Install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/gitguardian/ggshield
    rev: v1.14.5
    hooks:
      - id: ggshield
        name: GitGuardian Shield
        entry: ggshield secret scan pre-commit
        language: python
        stages: [commit]
```

### CI/CD Security

Add to GitHub Actions:
```yaml
- name: GitGuardian scan
  uses: GitGuardian/ggshield-action@v1
  env:
    GITHUB_PUSH_BEFORE_SHA: ${{ github.event.before }}
    GITHUB_PUSH_BASE_SHA: ${{ github.event.base }}
    GITHUB_DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}
    GITGUARDIAN_API_KEY: ${{ secrets.GITGUARDIAN_API_KEY }}
```

---

## 🚩 Known Security Considerations

### Current Limitations:
1. **In-Memory Sessions**: Data lost on restart (acceptable for honeypot)
2. **No Authentication on Callback**: GUVI endpoint doesn't require auth
3. **Rate Limiting**: Not enforced by default (enable in production)

### Mitigations:
- Document clearly in README
- Provide production configuration examples
- Recommend external rate limiting (e.g., API Gateway)

---

## 📋 Security Checklist for Contributors

Before submitting a PR:
- [ ] No hardcoded secrets or credentials
- [ ] All new dependencies scanned for vulnerabilities
- [ ] Input validation implemented
- [ ] Error handling doesn't leak sensitive info
- [ ] Security tests added (if applicable)
- [ ] Documentation updated

---

## 🔐 Encryption & Data At Rest

### Recommendations:
- Use encrypted volumes for production
- Consider database encryption if persisting data
- Encrypt backups
- Use TLS/SSL for all network communication

---

## 🎯 Security Testing

### Manual Testing:
```bash
# Test authentication
curl -X POST http://localhost:8000/honeypot \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Should return 401 Unauthorized

# Test with invalid API key
curl -X POST http://localhost:8000/honeypot \
  -H "x-api-key: invalid" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
# Should return 401 Unauthorized
```

### Automated Testing:
- Include security tests in test suite
- Test authentication failures
- Test input validation
- Test rate limiting (if enabled)

---

## 📚 Security Resources

### Tools:
- [GitGuardian](https://www.gitguardian.com/) - Secret detection
- [Safety](https://pyup.io/safety/) - Dependency vulnerability scanner
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [pip-audit](https://github.com/pypa/pip-audit) - Dependency auditing

### Best Practices:
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

## 📝 Security Updates

Security updates will be announced via:
- GitHub Security Advisories
- Release notes (CHANGELOG.md)
- Repository README

---

## ⚖️ Responsible Disclosure

We appreciate the security research community's efforts. Researchers who responsibly disclose vulnerabilities will be:
- Acknowledged in release notes (if desired)
- Given reasonable time for testing
- Kept informed of fix progress

---

## 🔄 Policy Updates

This security policy is reviewed and updated quarterly or as needed.

**Last Updated**: February 5, 2026  
**Version**: 1.0

---

**Remember**: Security is everyone's responsibility. When in doubt, ask before committing.
