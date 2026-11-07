# Indicators and false positives

Read before the code scan. Indicators require contextual review and comparison with clean distributions.

## PHP indicators

- Chained `base64_decode`, `gzinflate`, `gzuncompress`, `str_rot13` or `rawurldecode` calls.
- `eval(`, `assert(`, `create_function(` or legacy `preg_replace` with `/e`.
- Variable `include`/`require` targets or encoded path characters such as `\057`.
- `shell_exec`, `system(`, `passthru`, `exec(` or `popen(` with untrusted inputs.
- Long encoded blobs, for example `[A-Za-z0-9+/]{300,}={0,2}`.
- Foreign-host `wp_remote_get`, `curl_exec` or `file_get_contents`, especially followed by execution or output.
- Unexplained scripts inserted through `wp_head`, `wp_footer` or `wp_enqueue_script`.
- Unauthorized `wp_insert_user`, `add_role` or admin-email changes.
- `$_GET`, `$_POST`, `$_REQUEST` or `$_COOKIE` reaching code execution, includes or shell commands.

## SQL indicators

Search unexpected fields for `eval`, `base64_decode`, `gzinflate`, `preg_replace`, `iframe`, `<script`, `JavaScript`, `wp_remote` and foreign URLs. Domain suffixes or plain HTTP alone are not evidence of infection.

## False positives

WordPress and libraries legitimately contain encoding functions and regex replacements. Cache and optimization plugins generate minified JavaScript in cache/uploads. Ordinary plugin directories use `wp-` names. Compare with originals and explain the actual data flow before classifying a finding.
