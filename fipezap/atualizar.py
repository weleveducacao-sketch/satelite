"""Baixa o Raio-X FipeZAP mais recente, acha a página do percentual médio de desconto
em transações (acumulado em 12 meses), grava a imagem da página e o percentual de
todas as transações (com e sem desconto) para a Ficha do Laudo."""
import datetime
import json
import os
import re
import sys

import fitz
import requests

BASE = "https://downloads.fipe.org.br/indices/fipezap/raiox/raio-x-fipezap-{}t{}.pdf"
AQUI = os.path.dirname(os.path.abspath(__file__))
H = {"User-Agent": "Mozilla/5.0"}

hoje = datetime.date.today()
ano, tri = hoje.year, (hoje.month - 1) // 3 + 1
pdf = url = None
for _ in range(12):
    url = BASE.format(ano, tri)
    r = requests.get(url, headers=H, timeout=120, allow_redirects=False)
    if r.status_code == 200 and r.content[:4] == b"%PDF":
        pdf = r.content
        break
    tri -= 1
    if tri == 0:
        tri, ano = 4, ano - 1
if not pdf:
    sys.exit("Nenhum relatório Raio-X FipeZAP encontrado.")

doc = fitz.open(stream=pdf, filetype="pdf")
pagina = None
for p in doc:
    if re.search(r"PERCENTUAL M[ÉE]DIO DE DESCONTO EM TRANSA", p.get_text(), re.I):
        pagina = p
        break
if pagina is None:
    sys.exit("Página do percentual médio de desconto não encontrada.")

texto = " ".join(pagina.get_text().split())
m = re.search(r"encerrado em ([a-zç]+ de \d{4}).{0,160}?atingiram (\d+(?:,\d+)?)\s*% considerando todas as transa",
              texto, re.I)
if not m:
    sys.exit("Percentual de todas as transações não encontrado no texto da página.")
periodo, pct = m.group(1).lower(), float(m.group(2).replace(",", "."))

# página inteira, sem a faixa roxa do rodapé
r = pagina.rect
pix = pagina.get_pixmap(dpi=200, clip=fitz.Rect(0, 0, r.width, r.height * 0.915))
pix.save(os.path.join(AQUI, "desconto.png"))

dados = {
    "ref": f"{ano}t{tri}",
    "trimestre": f"{tri}º trimestre de {ano}",
    "periodo": periodo,
    "pct": pct,
    "pagina": pagina.number + 1,
    "url": url,
    "verificado": hoje.isoformat(),
}
caminho = os.path.join(AQUI, "dados.json")
antigo = {}
if os.path.exists(caminho):
    with open(caminho, encoding="utf-8") as f:
        antigo = json.load(f)
# só regrava quando muda o relatório ou o percentual, para não gerar commit todo dia
if {k: v for k, v in antigo.items() if k != "verificado"} != {k: v for k, v in dados.items() if k != "verificado"}:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
print(json.dumps(dados, ensure_ascii=False))
