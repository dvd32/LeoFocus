# Piano di pulizia pre-pubblicazione

Analisi di fattibilità fatta il 2026-08-04, aggiornata dopo `ponytail-audit`
e `flutter analyze`. Repo piccolo (~2.800 righe Dart, ~1.600 righe Python,
51 commit, 5 contributor) — stima totale: **un pomeriggio di lavoro mirato**,
non una riscrittura.

**Risultato chiave dell'audit: ~1.175 righe eliminabili (≈27% del codice) e
10 dipendenze rimovibili, senza toccare una sola feature.** Il codice non è
"scritto male" tanto quanto è *pieno di roba morta* — vecchie iterazioni Gemini
mai ripulite. Questo è il tipo di sporcizia più facile da togliere.

## ✅ Compilazione — RISOLTO (2026-08-04)

Partenza: `flutter analyze` → 111 problemi, di cui 5 error. Ora: **0 error,
99 info/warning**, `flutter test` verde, `flutter build macos` riuscito.

- [x] I 5 error erano tutti causati dalla **pub-cache vuota**, non da pacchetti
      rimossi: il progetto è stato spostato sull'SSD esterno e
      `.dart_tool/package_config.json` puntava a
      `/Users/filippo/.pub-cache/...` che non esiste più. `flutter pub get` ha
      risolto tutto in un colpo.
      Nota: `flutter_markdown` **risulta discontinued ma si installa e funziona
      ancora** — non serve sostituirlo per compilare (smentisce l'analisi
      iniziale). Resta un debito da valutare a parte, vedi sotto.
- [x] `test/widget_test.dart` era il test contatore di default di Flutter con
      la classe rinominata a metà (`LeonardoApp` invece di `LeoFocusApp`) e
      verificava un contatore inesistente. Sostituito con uno smoke test vero:
      l'app si avvia e mostra la schermata di setup. **Passa.**
      (Serve il wrapper `ChangeNotifierProvider`, e niente `pumpAndSettle`:
      `HomeScreen` ha un `AnimationController` in `repeat()` infinito.)
- [x] `requirements.txt` — aggiunti `groq` e `requests`, che il codice importa
      ma non erano dichiarati: chi clonava da zero non riusciva ad avviare il
      backend. (La rimozione dei ~2GB inutili resta allo step di pulizia.)

### Debito residuo, non bloccante

- [ ] `flutter_markdown` è discontinued: migrare a `flutter_markdown_plus`
      prima o poi, ma non urge.
- [ ] `flutter clean` — in `frontend/build/` ci sono artefatti stale che
      puntano a due vecchi percorsi del progetto
      (`~/Documents/PoliMI/...` e `.../Esami Fatti/Creativity Science and
      Innovation/...`), che generano warning a ogni build.

## 🔴 Sicurezza / history git

- [ ] ~~Verificare API key~~ — chiavi ritenute scadute dal team (progetto
      vecchio). Resta comunque da togliere il pattern hardcoded, vedi
      `get_groq_llm()` nella sezione codice morto.
- [ ] **Ripulire la history di git dai file grossi committati per errore**:
      - `frontend/.dart_tool/flutter_build/.../app.dill` (52MB, artefatto di build)
      - `leonardo_backend/trackers/debug_leonardo.jsonl` (184KB, log di sessione reale)
      Usare `git filter-repo` (o BFG Repo-Cleaner) per rimuoverli da tutta la
      history, non solo dal working tree — altrimenti restano nei blob passati
      e il `.git` resta a 124MB.
      ⚠️ Riscrive gli hash dei commit: coordinarsi con David/Pau prima di farlo,
      chi ha già clonato dovrà ri-clonare.

## 🧹 Codice morto — il grosso del lavoro (da ponytail-audit)

Ordinato per righe risparmiate. Nessuno di questi punti cambia il
comportamento dell'app.

### Frontend (Dart)

- [ ] **`frontend/lib/initial_advice_view.dart` — 816 righe, interamente morte.**
      Nessun file lo importa. Duplica `HomeScreen` (la vera è in
      `home_page_view.dart`, quella importata da `main.dart`) e `GlassCard`
      (la vera è in `widgets/glass_card_widget.dart`). È il monolite
      pre-split mai cancellato. **Da solo è il 18% del codebase.**
- [ ] `process_service.dart:150-271` — 5 `case` mai emessi da Python
      (`heartbeat`, `llm_update`, `critical_alert`, `achievement`, `error`).
      Python manda solo `update`, `leo_comment`, `initial_advice`, `status`,
      `report`. ~55 righe.
- [ ] `process_service.dart:2-4` — `universal_io` importato accanto a
      `dart:io` in un'app desktop che lancia subprocess Python: sul web non
      può funzionare comunque. Tenere solo `dart:io`, togliere la dipendenza.
- [ ] `process_service.dart:43,49` — guardie `kIsWeb` in `pythonExec` e
      `backendPath`: l'app spawna un processo Python, sul web non girerà mai.
- [ ] `process_service.dart:31,238-251` — `reportStats` "manteniamo per
      compatibilità" accanto a `finalStats`: stessi dati, e fuori dal service
      non lo legge nessuno.
- [ ] `process_service.dart:361-374` — getter `currentFocusScore`,
      `currentEmotion`, `hasStats`, `formattedTime`: zero usi fuori dal service.
- [ ] `frontend/pubspec.yaml` — `fl_chart` e `cupertino_icons` dichiarati,
      zero occorrenze in `lib/`.

### Backend (Python)

- [ ] `requirements.txt` — **`torch`, `transformers`, `accelerate`,
      `sentencepiece`, `protobuf` hanno zero import nel codice** (~2GB di
      dipendenze per niente: il backend usa solo l'API Groq). Anche `pytest`
      e `black` sono inutilizzati. **Mancano invece `groq` e `requests`, che
      servono davvero** — chi segue il README oggi non riesce a far partire
      il backend.
- [ ] `local_summarizer.py` — `summarize_activity_with_llm` + `build_prompt`
      + `sanitize_title`, ~104 righe su 150: importate in `trackers.py:11` ma
      mai chiamate. Sopravvive solo `get_start_session_advice`.
- [ ] `llm_client_2.py:44-111` — `ask_llm_huggingface` + `ask_llm_ollama` +
      dispatcher `provider`: ~60 righe per 3 provider di cui 1 usato (sempre
      `groq`). Ridurre a chiamata diretta.
- [ ] `trackers.py:372-402` — `get_all_windows()` lancia un subprocess
      `osascript` **ogni 0.5 secondi** e scrive `all_open_windows`, che
      nessuno legge mai. Lavoro sprecato a runtime, non solo righe morte.
- [ ] `trackers.py:205-233` — 12 chiavi di `activity_state` scritte e mai
      lette: `scroll_events`, `key_combinations`, `reading_time`,
      `window_background_time`, `window_log`, `hourly_activity`,
      `click_per_app`, `switch_sequence`, `productive_switches`,
      `window_open_count`, `all_open_windows`.
- [ ] `trackers.py:824,842` — `get_start_session_advice` chiamata **due volte
      di fila con lo stesso input**: due chiamate LLM identiche a ogni avvio,
      latenza e costo doppi. Una chiamata, due `print`.
- [ ] `trackers.py:193-200,512-522` — `categorize_app()` mai chiamata, e
      `APP_CATEGORIES` esiste solo per lei.
- [ ] `llm_client_2.py:17-27` — `get_groq_llm()`: la riga 18 assegna `_client`
      incondizionatamente, quindi il fallback su `GROQ_API_KEY` sotto è
      **irraggiungibile**. È anche il punto della chiave hardcoded: leggere
      sempre da `os.getenv`.
- [ ] `llm_client_2.py:175-176` — **il modulo importa se stesso**
      (`from llm_client_2 import ask_llm`) e ri-importa `json`, già importato
      a riga 3.
- [ ] `trackers.py:9-10` — `import tkinter` / `messagebox` in cima: tkinter
      serve solo dentro la stringa `POPUP_SCRIPT_CODE`, che gira in un altro
      processo.

### Duplicazione cross-linguaggio

- [ ] La scala dei voti `A+/A/A-/…/D` è **triplicata**:
      `trackers.py:765`, `llm_client_2.py:325-342`, `process_service.dart:285-295`.
      Tenerne una sola in Python — il Dart la riceve già nel pacchetto report.

## 🟡 Igiene file

- [ ] Rimuovere `leonardo_backend/trackers/angry.png` duplicato
      (già presente in `frontend/assets/angry.png`), ~1MB risparmiato.
- [ ] Rinominare `llm_client_2.py` → `llm_client.py` (nessun `llm_client.py`
      esiste più, il nome `_2` è un residuo di iterazione). Aggiornare i 3
      import che lo referenziano.
- [ ] Decidere su `frontend/assets/leo_quadrato.png` (927KB, non referenziato
      in nessun `.dart`/`.yaml`) — tenuto per ora su richiesta utente.
- [ ] Aggiungere `LICENSE` (repo attualmente senza licenza).
- [ ] `.gitignore` aggiornato il 2026-08-04 (pattern `frontend/.dart_tool/`
      invece di ~50 path letterali per singolo hash di build). Verificare che
      copra anche `__pycache__/`, `*.pyc`, `debug_leonardo.jsonl`.

## 🟢 Code quality automatica

- [ ] `dart fix --apply` — risolve la maggior parte dei ~90 warning
      `withOpacity` deprecato (→ `withValues`). Fix meccanico, zero rischio.
- [ ] `dart format .` su `frontend/`.
- [ ] `ruff format` + `ruff check` su `leonardo_backend/`.
- [ ] Rimuovere/convertire i `print()` di debug (13 in `llm_client_2.py`,
      15 in `trackers.py`, 3 in `local_summarizer.py`, 1 in `running_view.dart`
      già segnalato da `avoid_print`) in `logging` o toglierli.
- [ ] `trackers.py` — pattern `d[k] = d.get(k, 0) + 1` ripetuto ~10 volte:
      `collections.Counter` / `defaultdict(int)` (Counter è già importato).
- [ ] Risolvere il TODO in `frontend/lib/report_view.dart:446`
      (share functionality) — o implementarlo o toglierlo se non previsto.

## ⚪️ Opzionale

- [ ] `gitleaks` o `git-secrets` come scan storico completo, per conferma
      oltre alla API key già individuata.
- [ ] Test reali (dopo aver sistemato `widget_test.dart`, che oggi è rotto).
- [ ] CI GitHub Actions con `flutter analyze` + `ruff check`, se il repo
      resta mantenuto attivamente.

## Ordine consigliato

1. ~~Sistemare la compilazione~~ ✅ fatto il 2026-08-04.
2. **Cancellare `initial_advice_view.dart`** — 816 righe via in un colpo,
   zero rischio, e riduce subito il rumore per tutti i passi successivi.
3. **Ripulire `requirements.txt`** — togliere i 7 pacchetti inutili
   (`groq`/`requests` già aggiunti).
4. Pulizia history git (`app.dill`, `debug_leonardo.jsonl`) — coordinarsi
   col team, riscrive gli hash.
5. Resto del codice morto (Python e Dart) seguendo la lista sopra.
6. Igiene file (duplicati, rename, LICENSE).
7. `dart fix --apply` + format/lint automatico su entrambi i linguaggi.
8. Opzionali (test, CI) solo se il repo resta mantenuto attivamente.
