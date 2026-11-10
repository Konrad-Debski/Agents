# Konfiguracja lokalna i MCP

## Ustawienia lokalne i sekrety

Opcjonalny plik `${XDG_CONFIG_HOME:-~/.config}/agents/local.json` pozostaje poza repozytorium:

```json
{
  "harnesses": ["codex", "claude-code", "cursor", "opencode", "vscode"],
  "disabled_servers": [],
  "disabled_servers_by_harness": {}
}
```

Brak `harnesses` oznacza automatyczne wykrywanie. Pusta lista wyłącza integracje. Usunięcie harnessu z jawnej listy usuwa wyłącznie jego wcześniej zarządzane wpisy i dowiązania. `disabled_servers` pozwala wyłączyć serwer na konkretnej maszynie bez zmiany wspólnej definicji.

`disabled_servers_by_harness` wyłącza wspólny wpis tylko w wybranych harnessach. Na przykład `{"vscode": ["context7"], "opencode": ["context7"]}` pozwala zachować własne serwery Context7 HTTP z ich autoryzacją, bez dodawania drugiego połączenia. Nie wyłącza osobistych wpisów o innych nazwach. Ręcznie usunięty zarządzany wpis JSON lub JSONC zostanie odtworzony przez `apply`, jeśli nadal wynika z rejestru i ustawień lokalnych.

Stan własności wpisów, blokada wdrażania i lokalne kopie zapasowe znajdują się w `${XDG_STATE_HOME:-~/.local/state}/agents`. Nie usuwaj `managed.json`, jeśli chcesz nadal automatycznie aktualizować istniejące wpisy. Utrata stanu powoduje wykrycie kolizji zamiast przejęcia obcej konfiguracji. Kopie zapasowe mają uprawnienia `600` i przechowują także zawartość zastępowanych plików lokalnych. Chroń je tak samo jak konfigurację harnessów.

Klucze API dostarczaj w środowisku uruchamianego harnessu. Zmienne ustawione tylko w terminalu mogą nie być dostępne w aplikacji graficznej lub usłudze systemd. Tokeny OAuth zapisuje lokalnie odpowiedni harness. Logowanie wykonujemy oddzielnie na każdym komputerze. Repozytorium nie przenosi sesji logowania, historii rozmów ani danych konektorów.

## Definicje MCP

Rejestr obejmuje zdalne serwery Context7 pod `https://mcp.context7.com/mcp` i Figma pod `https://mcp.figma.com/mcp` oraz publiczny serwer dokumentacji OpenAI. Figma loguje przez OAuth w każdym harnessie osobno i nie wymaga sekretu. Serwer OpenAI jest przypisany wyłącznie do Codex (`"harnesses": ["codex"]`). Context7 korzysta ze Streamable HTTP i nie wymaga lokalnego Node.js ani `npx`. Pozostałe MCP dodawaj do `mcp/servers.json`, po przeniesieniu sekretów do środowiska.

Domyślna konfiguracja Context7 łączy się bez klucza API. Dzięki temu brak zmiennej autoryzacji nie blokuje startu MCP. Klucz pozwala uzyskać [wyższe limity zapytań](https://github.com/upstash/context7/blob/master/docs/resources/troubleshooting.mdx). Własne połączenia z autoryzacją można zachować i wyłączyć wspólny wpis przez `disabled_servers_by_harness`.

Jeśli chcesz wymagać autoryzacji we wspólnej definicji Context7, dodaj `"header_env": {"Authorization": "CONTEXT7_AUTHORIZATION"}` i ustaw zmienną `CONTEXT7_AUTHORIZATION` na pełną wartość `Bearer <klucz API Context7>`. Adaptery zapisują odwołania do środowiska, a `doctor` sprawdza obecność zmiennej. Wartość klucza pozostaje poza repozytorium.

Po zmianie rejestru uruchom `bash ~/.agents/scripts/apply.sh`. Adaptery aktualizują zarządzane wpisy, zachowując osobiste serwery. Pola `gallery` i `version` nie należą do wspólnego rejestru.

Przykład formatu:

```json
{
  "version": 1,
  "servers": {
    "local-tool": {
      "transport": "stdio",
      "command": "my-mcp-server",
      "args": ["serve"],
      "env_vars": ["MY_TOOL_API_KEY"],
      "requires_env": ["MY_TOOL_API_KEY"]
    },
    "remote-tool": {
      "transport": "http",
      "url": "https://example.com/mcp",
      "header_env": {"X-API-Key": "MY_TOOL_API_KEY"},
      "harnesses": ["codex", "claude-code"]
    }
  }
}
```

Obsługujemy `stdio` i Streamable HTTP. `env_vars` przekazuje zmienne do procesu, `header_env` wskazuje zmienne z wartościami nagłówków, a `requires_env` dodaje wymagania do diagnostyki. Wygenerowana konfiguracja zawiera odwołania do zmiennych, nigdy odczytane wartości. `harnesses` opcjonalnie ogranicza integrację do wskazanych narzędzi.

Nie umieszczaj sekretów w argumentach, URL ani plikach źródłowych. Wspólny rejestr nie przyjmuje dowolnych pól `env` lub `headers` ze stałymi wartościami. Polecenia powinny być dostępne w `PATH`, bez ścieżek `/home/...`. Zależności MCP instalujesz lokalnie. Jeśli potrzebujesz powtarzalnej wersji paczki, przypnij jej wersję w argumentach polecenia.
