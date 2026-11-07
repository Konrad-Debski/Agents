# Database inspection examples

Use the real table prefix instead of `wp_`. These are query examples for an isolated inspection database. In a dump, locate the corresponding records directly. Session-token values are sensitive. Inspect their presence and metadata without printing the tokens.

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
WHERE meta_key LIKE '%capabilities%';

SELECT user_id, meta_key
FROM wp_usermeta
WHERE meta_key = 'session_tokens';

SELECT option_name, LEFT(option_value, 200)
FROM wp_options
WHERE option_name IN ('siteurl','home','active_plugins','template','stylesheet','cron','admin_email');
```

For a local dump, inspect the matching `INSERT INTO` records instead of importing it.
