# Wzorce i fałszywe alarmy

## Wzorce do wyszukania

W PHP (krok 4):
- `base64_decode`, `gzinflate`, `gzuncompress`, `str_rot13`, `rawurldecode` w łańcuchu wywołań,
- `eval(`, `assert(`, `create_function(`, `preg_replace` z modyfikatorem `/e`,
- `include "`, `include_once "`, `require` ze zmienną zamiast stałej, `\057` (ukryty ukośnik),
- `shell_exec`, `system(`, `passthru`, `exec(`, `popen(`,
- `base64` jako blob: `[A-Za-z0-9+/]{300,}={0,2}`,
- `wp_remote_get`, `curl_exec`, `file_get_contents` z obcego hosta, zwłaszcza w połączeniu z `eval` albo `echo`,
- `add_action('wp_head'` / `add_action('wp_footer'` wstawiające `<script` albo `wp_enqueue_script` z obcego URL,
- tworzenie użytkownika: `wp_insert_user`, `add_role`, `update_option('admin_email'`,
- `$_GET`, `$_POST`, `$_REQUEST`, `$_COOKIE` przekazywane wprost do `eval`, `include`, `system`.

W dumpie SQL (krok 5): `eval`, `base64_decode`, `gzinflate`, `preg_replace`, `iframe`, `<script`, `JavaScript`, `wp_remote`, `.ru/`, `http://` w polach, które hostować kodu zewnętrznego nie powinny.

## Fałszywe alarmy

- WordPress trzyma w jądrze własny base64 (obrazki, certyfikaty) i `preg_replace` bez `/e`. Porównywać z czystą paczką, nie kasować na podstawie samego słowa kluczowego.
- Wtyczki cache i optymalizacji generują minifikowany JS w `wp-content/cache` i `uploads`. Minifikowany kod to nie dowód infekcji.
- Nazwy typu `wp-` w `wp-content` to normalne katalogi wtyczek i motywów.
