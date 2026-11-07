# Separate follow-up requests

## Failure diagnosis without an infection scan

Check `.maintenance`, `wp-content/debug.log`, debug flags, enabled mu-plugins and recently changed plugins. Redact configuration secrets. Keep the outcome separate from malware findings.

## Hardening advice after analysis

When requested, recommend rotating affected FTP, database and WordPress credentials and salts, reviewing account access and adding appropriate login protection such as 2FA. Match recommendations to the confirmed compromise and hosting setup. External scans can supplement the local evidence. Advice does not authorize configuration changes, uploads or deployment.
