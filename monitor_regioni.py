"""Controlla l'elenco delle regioni nel modulo di candidatura di Affari Tuoi
e manda un messaggio Telegram quando cambia."""

import json
import os
import pathlib
import sys

import requests
from bs4 import BeautifulSoup

URL = "https://www.giocherai.it/giochistudio/nuovo_gioco/registrati.php"
STATE_FILE = pathlib.Path("regioni.json")

TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def leggi_regioni() -> list[str]:
    r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # Il primo <select> della pagina è quello delle regioni.
    # Se il sito cambia struttura, qui puoi sostituirlo con
    # soup.find("select", {"id": "..."}) o {"name": "..."}.
    select = soup.find("select")
    if select is None:
        raise RuntimeError("Nessun <select> trovato: la pagina è cambiata?")

    regioni = [
        o.get_text(strip=True)
        for o in select.find_all("option")
        if o.get_text(strip=True) and not o.get_text(strip=True).startswith("Seleziona")
    ]
    if not regioni:
        raise RuntimeError("Elenco regioni vuoto: controlla il selettore.")
    return sorted(regioni)


def invia_telegram(testo: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHAT_ID, "text": testo, "disable_web_page_preview": True},
        timeout=30,
    )
    r.raise_for_status()


def main() -> None:
    regioni = leggi_regioni()
    vecchie = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else None

    if vecchie is None:
        # Primo avvio: salvo lo stato e mando un messaggio di prova
        invia_telegram(
            "Monitoraggio attivo ✅\nRegioni attuali: " + ", ".join(regioni) + f"\n{URL}"
        )
    elif regioni != vecchie:
        nuove = sorted(set(regioni) - set(vecchie))
        rimosse = sorted(set(vecchie) - set(regioni))
        righe = ["Aggiornamento candidature Affari Tuoi! 🎉"]
        if nuove:
            righe.append("Nuove regioni: " + ", ".join(nuove))
        if rimosse:
            righe.append("Regioni rimosse: " + ", ".join(rimosse))
        righe.append(URL)
        invia_telegram("\n".join(righe))
    else:
        print("Nessuna modifica.")

    STATE_FILE.write_text(json.dumps(regioni, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # l'errore fa fallire il job e GitHub ti avvisa
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)
