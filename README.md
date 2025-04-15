# MiASI-Lang



### Autorzy: Jakub Ogrodowczyk - TBA, Jakub Jaśków - 268416, Justyna Ziemichód - TBA

---

## Opis
Projekt prostego języka imperatywnego do tworzenia animacji 2D, oraz implementacja jego
interpretera napisana w języku [Python](https://www.python.org/), przy użyciu narzędzia
[ANTLR](https://www.antlr.org/) oraz biblioteki [Arcade](https://api.arcade.academy/en/latest/).

Projekt ten został napisany na potrzeby kursu MiASI (Modelowanie i Analiza Systemów Informatycznych)
pod opieką 
**[dr inż. Tomasza Babczyńskiego](https://wit.pwr.edu.pl/wydzial/struktura-organizacyjna/pracownicy/tomasz-babczynski)**.

---

## Instrukcje
### Instalacja

Projekt został przystosowany pod środowisko 
**[PyCharm Professional](https://www.jetbrains.com/pycharm/)**. Użycie tego środowiska
jest zalecane, ale nie wymagane. W tej instrukcji zostaną opisane tylko kroki umożliwiające
konfigurację projektu w tym środowisku.

##### 1. Instalacja środowiska PyCharm Professional
Środowisko to jest darmowe dla wszystkich pracowników akademickich. Więcej informacji
na stronie firmy [JetBrains](https://www.jetbrains.com/).

##### 2. Sklonowanie repozytorium
Projekt może zostać sklonowany lokalnie poprzez komendę
```git clone https://github.com/Grubre/miasi-lang```
lub poprzez PyCharma: w zakładce **File->Project from Version Control** podajemy URL
z poprzedniej komendy.

##### 3. Instalacja narzędzia ANTLR
Narzędzie ANTLR został dodane jako przymusowa zależność dla tego projektu, w postaci pluginu.
Po otworzeniu projektu powinno ono zostać pobrane automatycznie. W przeciwnym wypadku może
zostać zainstalowane w **File->Settings->Plugins**. W polu wyszukiwanie należy wpisać ```ANTLR```
a następnie przycisk ```zainstaluj```.

##### 4. Instalacja biblioteki Arcade
Aby zainstalować bibliotekę Arcade wystarczy najechać na jej instancję w kodzie
(np. **src/graphics.py:7**) rozwinąć okno dialogowe i kliknąć opcję ```instaluj```.

##### 5. Generowanie plików ANTLR

Po zainstalowaniu wszystkich potrzebnych bibiliotek i narzędzi należy wygenerować pliki
leksykalne. Aby tego dokonać należy z poziomu projektu najechać na plik **src/Grammar.g4**,
kliknąć na niego prawym przyciskiem myszy i wybrać opcję ```Generate ANTLR Recognizer```.

##### 5. Uruchomienie przykładu działania
W projekcie znajdują się skonfigurowane pliki startowe, umożliwiające uruchomienie przykładu
działania aplikacji za jednym kliknięciem. Scenariusze te znajdują się w prawym górnym
rogu środowiska. Należy kliknąć na skierowaną w dół strzałkę, wybrać odpowiedni scenariusz a
następnie uruchomić go za pomocą zielonej strzałki.

### Development

TBA.