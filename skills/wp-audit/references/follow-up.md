# Awaria strony, nie infekcja

Gdy strona nie działa, a plików nie trzeba skanować: sprawdzić obecność `.maintenance` w katalogu głównym (po nim zostaje biały ekran z komunikatem "Briefly unavailable for scheduled maintenance"), zawartość `wp-content/debug.log`, flagi `WP_DEBUG` i `WP_DEBUG_LOG` w `wp-config.php`, włączone `mu-plugins` i ostatnio zmienione wtyczki.

## Po analizie - hardening

Gdy użytkownik poprosi o zalecenia zabezpieczeń: rotacja haseł (FTP, baza, konta WP), zmiana saltów w `wp-config.php`, zmiana adresu logowania (WPS Hide Login), 2FA albo blokada `wp-admin` w `.htaccess`, wtyczka zabezpieczająca, SSL, skan zewnętrzny (VirusTotal, Google Transparency Report, securityscan.getastra.com).
