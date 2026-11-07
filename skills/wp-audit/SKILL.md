---
name: wp-audit
description: Read-only malware audit of downloaded WordPress files and SQL dumps after a suspected hack. Use for infection scans and evidence reports, not routine updates.
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

Wczytać [references/patterns.md](references/patterns.md), a następnie przeszukać wszystkie pliki PHP (także `wp-content/uploads`, motywy, wtyczki, katalog główny) pod kątem opisanych wzorców i fałszywych alarmów. Używać `grep_search` (regexp, bez rozróżniania wielkości liter) po jednym wzorcu na zapytanie.

Każdy traf ocenić:
- fałszywy alarm: kod zgodny z oryginałem z czystej paczki albo jawna logika wtyczki (np. biblioteka z własnym `eval` w nazwie funkcji),
- podejrzany: nietypowa lokacja, obfuskacja, brak związku z resztą pliku,
- backdoor: wykonanie kodu z danych wejściowych, łączenie zdalne, tworzenie konta admina, wstrzykiwanie `<script>`.

Kryterium zakończenia: każde trafienie ma ocenę i uzasadnienie, backdoory mają ścieżkę i numer linii.

## Krok 5. Zrzut bazy danych

Jeśli w kopii jest `.sql`, wczytać [references/database.md](references/database.md) oraz wzorce SQL w [references/patterns.md](references/patterns.md). Spakowany dump rozpakować do pliku tymczasowego poza katalogiem strony. Następnie:
- przeszukać dump komendą `grep -n -i -E 'eval|base64_decode|gzinflate|preg_replace|str_replace|iframe|<script'`, wyniki filtrować ręcznie (serializacja PHP w `wp_options` generuje szum),
- sprawdzić konta i uprawnienia zapytaniami z tej referencji,
- sprawdzić wpisy `wp_posts` na wstrzyknięty kod w `post_content` i w `post_excerpt`,
- sprawdzić opcje `siteurl`, `home`, `active_plugins`, `template`, `stylesheet`, `cron` pod kątem obcych wartości,
- widgety i ustawienia motywu (`widget_*`, `theme_mods_*`) na wstrzyknięte skrypty.

Uwaga: wartości serializanej PHP nie edytować tekstem, długość prefiksu `s:` przestaje się zgadzać i dane się psują. Odnotować tylko znalezisko.

Kryterium zakończenia: konta, opcje, wpisy i payloady w dumpie sprawdzone, znaleziska opisane.

## Krok 6. Raport

Zakończyć raportem, jedna linia na znalezisko: `ścieżka:linia` + problem + proponowane działanie. Grupować: jądro zmodyfikowane, backdoory, wstrzyknięte JS, pliki obce, baza danych, konta użytkowników. Na końcu podsumowanie liczbą znalezisk w każdej grupie i rekomendowaną kolejnością naprawy: przywrócić jądro z czystej paczki, usunąć backdoory, wyczyścić bazę, skasować podejrzane konta, przekazać listę haseł i saltów do zmiany.

## Dalsze zadania

Gdy użytkownik prosi o diagnostykę awarii bez skanowania lub zalecenia zabezpieczeń po analizie, wczytać odpowiednią sekcję [references/follow-up.md](references/follow-up.md). Sam raport nie upoważnia do naprawy.
