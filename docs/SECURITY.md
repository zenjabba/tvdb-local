# Security Guidelines

## Environment Variables

**🔒 NEVER commit sensitive data to version control!**

### Protected Files
The following files are automatically ignored by Git:
- `.env` - Main environment configuration
- `.env.local` - Local overrides
- `.env.*.local` - Environment-specific local configs
- `*.key` - Any key files
- `*.pem` - Certificate files
- `secrets.txt` - Any secrets file

### Required Environment Variables

Before deployment, ensure these are set:

```bash
# Required - Get from thetvdb.com
TVDB_API_KEY=your_tvdb_api_key_here

# Required - Generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=your_secure_secret_key_here

# Optional
TVDB_PIN=your_optional_pin
```

### Production Security Checklist

- [ ] `.env` file is not committed to Git
- [ ] Secret key is randomly generated (32+ characters)
- [ ] TVDB API key is from your account
- [ ] Default demo API keys are changed
- [ ] Rate limits are configured appropriately
- [ ] Database passwords are changed from defaults
- [ ] Redis is not exposed publicly
- [ ] API is behind HTTPS in production
- [ ] Log levels don't expose sensitive data

### GitLab CI/CD Variables

For GitLab deployment, set these as **protected variables**:
- `TVDB_API_KEY`
- `SECRET_KEY` 
- `DATABASE_URL` (production)
- `REDIS_URL` (production)

### Local Development

1. Copy `.env.example` to `.env`
2. Add your actual TVDB API key
3. Generate a secure secret key
4. Never commit the `.env` file

### API Key Management

- Each client should have their own API key
- Rotate keys regularly
- Monitor usage in logs
- Implement rate limiting per key
- Disable compromised keys immediately

### Incident Response

If secrets are accidentally committed:
1. **Immediately rotate** all exposed credentials
2. Update `.env` with new values
3. Redeploy all services
4. Review Git history and remove sensitive data
5. Contact TVDB support if API key was exposed

---

**Remember**: Security is everyone's responsibility! 🛡️