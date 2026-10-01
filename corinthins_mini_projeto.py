import csv
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL_BASE = "https://www.cnnbrasil.com.br/tudo-sobre/gavioes-da-fiel/"
PAGINAS = 2
MAX_NOTICIAS = 10
PASTA_SAIDA = Path("noticias_cnn_gavioes")
PAUSA_SEGUNDOS = 1.5
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    )
}


def baixar_html(url: str) -> BeautifulSoup:
    resposta = requests.get(url, headers=HEADERS, timeout=15)
    resposta.raise_for_status()
    return BeautifulSoup(resposta.text, "html.parser")


def url_da_pagina(numero: int) -> str:
    return URL_BASE if numero == 1 else f"{URL_BASE}pagina/{numero}/"


def coletar_noticias() -> list[dict]:
    noticias, vistos = [], set()

    for numero in range(1, PAGINAS + 1):
        url = url_da_pagina(numero)
        print(f"Lendo listagem: {url}")
        soup = baixar_html(url)

        for h2 in soup.select("h2 a[href]"):
            link = urljoin(url, h2["href"])
            if link in vistos:
                continue
            vistos.add(link)

            bloco = h2.find_parent("li") or h2.parent
            achou = re.search(r"\d{2}/\d{2}/\d{4}", bloco.get_text(" "))
            noticias.append({
                "titulo": h2.get_text(strip=True),
                "link": link,
                "data": achou.group() if achou else "",
            })

        time.sleep(PAUSA_SEGUNDOS)

    return noticias[:MAX_NOTICIAS]


def meta(soup: BeautifulSoup, propriedade: str) -> str | None:
    tag = soup.find("meta", property=propriedade)
    return tag["content"].strip() if tag and tag.get("content") else None


def slugify(texto: str) -> str:
    texto = re.sub(r"[^\w\s-]", "", texto.lower())
    return re.sub(r"[\s_-]+", "-", texto).strip("-")[:80]


def baixar_imagem(url_imagem: str, destino: Path) -> None:
    resposta = requests.get(url_imagem, headers=HEADERS, timeout=15)
    resposta.raise_for_status()
    destino.write_bytes(resposta.content)


def main() -> None:
    PASTA_SAIDA.mkdir(exist_ok=True)
    noticias = coletar_noticias()
    print(f"\n{len(noticias)} notícias encontradas.\n")

    registros = []
    for i, noticia in enumerate(noticias, start=1):
        try:
            soup = baixar_html(noticia["link"])
            imagem = meta(soup, "og:image")

            if not imagem:
                print(f"[{i}] sem imagem: {noticia['titulo']}")
                continue

            extensao = Path(imagem.split("?")[0]).suffix or ".jpg"
            arquivo = PASTA_SAIDA / f"{i:02d}-{slugify(noticia['titulo'])}{extensao}"
            baixar_imagem(imagem, arquivo)

            noticia["arquivo"] = arquivo.name
            registros.append(noticia)
            print(f"[{i}] OK: {noticia['titulo']}")
        except Exception as erro:
            print(f"[{i}] erro em {noticia['link']}: {erro}")

        time.sleep(PAUSA_SEGUNDOS)

    with open(PASTA_SAIDA / "noticias.csv", "w", newline="", encoding="utf-8") as f:
        escritor = csv.DictWriter(f, fieldnames=["data", "titulo", "link", "arquivo"])
        escritor.writeheader()
        escritor.writerows(registros)

    print(f"\nPronto! {len(registros)} imagens salvas em '{PASTA_SAIDA}/'.")


if __name__ == "__main__":
    main()
