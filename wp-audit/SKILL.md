---
name: wp-audit
description: Analyze WordPress files and SQL dumps downloaded from a server for signs of infection - modified core files, backdoors, injected scripts, suspicious DB accounts. Use when asked to audit, scan or inspect a WordPress folder or database dump after a hack, or when the user says "sprawdź pliki", "włam", "malware", "zainfekowana strona", "audyt bezpieczeństwa WordPress". Read-only analysis producing a findings report.
---

# Analiza pobranych plików WordPress

Cel: znaleźć ślady infekcji w lokalnej kopii plików WordPressa i w zrzucie bazy danych.

Zasady pracy:
- Tylko odczyt. Nie usuwać, nie poprawiać, nie edytować plików bez wyraźnej zgody użytkownika.
- Nie wyciskać sekretów z `wp-config.php` (hasła, klucze, salty) do odpowiedzi ani do raportu. Wzmiankować sam fakt problemu, nie wartość sekretu.
- Każde podejrzenie potwierdzać dowodem: ścieżka, numer linii, fragment kodu.

## Krok 1. Inwentarz i wersje

Ustalić, co jest w kopii:
- wersja WordPressa z `wp-includes/version.php` (`$wp_version`),
- obecność `wp-config.php`, `.htaccess`, `.maintenance`, `wp-content/debug.log`, `wp-content/mu-plugins/`,
- struktura katalogów: `wp-admin`, `wp-includes`, `wp-content` (motywy, wtyczki, `uploads`),
- czy jest zrzut bazy danych (`.sql`, `.sql.gz`).

Kryterium zakończenia: lista wersji i katalogów zapisana, znane wszystkie pliki w katalogu głównym.

## Krok 2. Integralność jądra WordPressa

Sprawdzić, czy pliki jądra nie zostały zmodyfikowane. Sposoby, w kolejności:
1. WP-CLI w katalogu z kopią: `wp core verify-checksums --skip-plugins`. Wynik wylistuje pliki zmodyfikowane, dodane i usunięte.
2. Brak WP-CLI: pobrać czystą paczkę WordPressa w tej samej wersji z wordpress.org i porównać katalogi `wp-includes`, `wp-admin` oraz pliki z katalogu głównego komendą `diff -rq` albo `git diff --no-index`.
3. Jeśli różnice wchodzą w fragmenty kodu (patrz krok 4), wskazać je jako zmodyfikowane.

Pominąć w ocenie różnice w `wp-config.php`, `wp-content` i plikach dodanych przez właściciela strony, ale odnotować je osobno.

Kryterium zakończenia: każdy plik jądra oceniony jako oryginalny albo zmodyfikowany z dowodem.

## Krok 3. Pliki spoza struktury WordPressa

Przejrzeć pełną listę plików (`file_search` + `list_dir`) i wychwycić:
- pliki o nazwach podszywających się pod jądro, np. `options.php`, `wp-blog.php`, `wp-steam.php` w katalogu głównym (WordPress ich nie ma domyślnie),
- losowe krótkie nazwy, podwójne rozszerzenia (`plik.php.jpg`), pliki `.php` w `wp-content/uploads/`,
- pozostałości wcześniejszego czyszczenia, np. `*.php.VIRUS`,
- pliki z nietypowymi uprawnieniami lub datami spoza zakresu reszty kopii (daty w `ls -la`),
- dodatki do `.htaccess`, np. `php_value auto_prepend_file`, przepisania na obce domeny, blokady dostępu do logowania.

Kryterium zakończenia: każdy plik spoza czystej paczki WP i poza znanymi plikami właściciela wpisany na listę znalezisk.

## Krok 4. Wzorce backdoorów w kodzie

Przeszukać wszystkie pliki PHP (także `wp-content/uploads`, motywy, wtyczki, katalog główny) pod kątem wzorców z sekcji "Wzorce do wyszukania". Używać `grep_search` (regexp, bez rozróżniania wielkości liter) po jednym wzorcu na zapytanie.

Każdy traf ocenić:
- fałszywy alarm: kod zgodny z oryginałem z czystej paczki albo jawna logika wtyczki (np. biblioteka z własnym `eval` w nazwie funkcji),
- podejrzany: nietypowa lokacja, obfuskacja, brak związku z resztą pliku,
- backdoor: wykonanie kodu z danych wejściowych, łączenie zdalne, tworzenie konta admina, wstrzykiwanie `<script>`.

Kryterium zakończenia: każde trafienie ma ocenę i uzasadnienie, backdoory mają ścieżkę i numer linii.

## Krok 5. Zrzut bazy danych

Jeśli w kopii jest `.sql` (spakowany - rozpakować do pliku tymczasowego poza katalogiem strony):
- przeszukać dump komendą `grep -n -i -E 'eval|base64_decode|gzinflate|preg_replace|str_replace|iframe|<script'`, wyniki filtrować ręcznie (serializacja PHP w `wp_options` generuje szum),
- sprawdzić konta i uprawnienia zapytaniami z sekcji "Zapytania SQL",
- sprawdzić wpisy `wp_posts` na wstrzyknięty kod w `post_content` i w `post_excerpt`,
- sprawdzić opcje `siteurl`, `home`, `active_plugins`, `template`, `stylesheet`, `cron` pod kątem obcych wartości,
- widgety i ustawienia motywu (`widget_*`, `theme_mods_*`) na wstrzyknięte skrypty.

Uwaga: wartości serializanej PHP nie edytować tekstem, długość prefiksu `s:` przestaje się zgadzać i dane się psują. Odnotować tylko znalezisko.

Kryterium zakończenia: konta, opcje, wpisy i payloady w dumpie sprawdzone, znaleziska opisane.

## Krok 6. Raport

Zakończyć raportem, jedna linia na znalezisko: `ścieżka:linia` + problem + proponowane działanie. Grupować: jądro zmodyfikowane, backdoory, wstrzyknięte JS, pliki obce, baza danych, konta użytkowników. Na końcu podsumowanie liczbą znalezisk w każdej grupie i rekomendowaną kolejnością naprawy: przywrócić jądro z czystej paczki, usunąć backdoory, wyczyścić bazę, skasować podejrzane konta, przekazać listę haseł i saltów do zmiany.

## Referencja

### Wzorce do wyszukania

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

### Zapytania SQL

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

### Fałszywe alarmy

- WordPress trzyma w jądrze własny base64 (obrazki, certyfikaty) i `preg_replace` bez `/e`. Porównywać z czystą paczką, nie kasować na podstawie samego słowa kluczowego.
- Wtyczki cache i optymalizacji generują minifikowany JS w `wp-content/cache` i `uploads`. Minifikowany kod to nie dowód infekcji.
- Nazwy typu `wp-` w `wp-content` to normalne katalogi wtyczek i motywów.

### Awaria strony, nie infekcja

Gdy strona nie działa, a plików nie trzeba skanować: sprawdzić obecność `.maintenance` w katalogu głównym (po nim zostaje biały ekran z komunikatem "Briefly unavailable for scheduled maintenance"), zawartość `wp-content/debug.log`, flagi `WP_DEBUG` i `WP_DEBUG_LOG` w `wp-config.php`, włączone `mu-plugins` i ostatnio zmienione wtyczki.

### Po analizie - hardening

Gdy użytkownik poprosi o zalecenia zabezpieczeń: rotacja haseł (FTP, baza, konta WP), zmiana saltów w `wp-config.php`, zmiana adresu logowania (WPS Hide Login), 2FA albo blokada `wp-admin` w `.htaccess`, wtyczka zabezpieczająca, SSL, skan zewnętrzny (VirusTotal, Google Transparency Report, securityscan.getastra.com).
