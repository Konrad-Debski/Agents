# Zapytania SQL

```sql
SELECT ID, post_title, post_status, post_type
FROM wp_posts
WHERE post_content LIKE '%iframe%'
   OR post_content LIKE '%<script%'
   OR post_content LIKE '%base64_decode%';

SELECT ID, user_login, user_email, user_registered, user_status
FROM wp_users;

SELECT user_id, meta_key, meta_value
FROM wp_usermeta
WHERE meta_key LIKE '%capabilities%' OR meta_key = 'session_tokens';

SELECT option_name, LEFT(option_value, 200)
FROM wp_options
WHERE option_name IN ('siteurl','home','active_plugins','template','stylesheet','cron','admin_email');
```

Przy dumpie lokalnym te same zapytania zastępuje `grep -n -A2` po nawiasach `INSERT INTO \`wp_users\`` i `INSERT INTO \`wp_options\``.
