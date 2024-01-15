Zrobione:
- wszystko oprocz niezrobionego :)
- wjezdzanie do stacji oddelegowane do celery, skoro to long running task... Response requesta zwraca id taska, ktorego status mozna sledzic.
  Mozna jeszcze podac notify_url, i jak task sie skonczy, to powiadomienie zostanie wyslane

Nie zrobione:
 - Wyjeżdżanie lokomotywą ze stacji - poniewaz jest analogiczne do wjezdzania, nie chciało mi się już.

Problemy:
 - dużo czasu zmarnowałem probując użyć SQLModel do walidacji danych request/response.
   Klasa ta dziedziczy po pydanticu, ale jest coś mocno namieszane i niestety trzeba było dużo kombinować z dodatkowymi modelami :(
   Skopali akcje.

Testy:
 - aby uruchomic testy:
   $ docker-compose up -d  # uruchamia apke
   $ docker-compose exec web /bin/bash -c "cd app && pytest tests/tests.py"  # uruchamia testy w contenerze apki
