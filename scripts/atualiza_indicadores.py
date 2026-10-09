"""Atualiza indicadores.json com dados oficiais do Banco Central.

- CDI anualizado (base 252) ........ SGS 4389
- IPCA acumulado em 12 meses ....... SGS 13522
- Selic Focus (fim do ano corrente)  Expectativas de Mercado Anuais
- IPCA Focus próximos 12 meses ..... Expectativas de Mercado Inflação 12 meses (suavizada)

Se alguma consulta falhar, mantém o valor anterior do arquivo.
"""
import json
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ARQ = pathlib.Path(__file__).resolve().parent.parent / "indicadores.json"
BRT = timezone(timedelta(hours=-3))
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados/ultimos/1?formato=json"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/"


def get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def sgs(codigo):
    ult = get_json(SGS.format(codigo))[-1]
    return {"valor": round(float(str(ult["valor"]).replace(",", ".")), 4), "data": ult["data"], "fonte": f"BCB/SGS {codigo}"}


def focus(entidade, filtro, campos):
    # A API Olinda exige os nomes "$top", "$filter"... sem codificar o "$"
    params = [("$top", "1"), ("$filter", filtro), ("$orderby", "Data desc"), ("$format", "json"), ("$select", campos)]
    qs = "&".join(k + "=" + urllib.parse.quote(v, safe=",") for k, v in params)
    dados = get_json(OLINDA + entidade + "?" + qs)["value"]
    if not dados:
        raise ValueError("consulta do Focus sem resultados")
    return dados[0]


def main():
    try:
        atual = json.loads(ARQ.read_text(encoding="utf-8"))
    except Exception:
        atual = {}
    novo = dict(atual)
    erros = []
    ano = datetime.now(BRT).year

    def tenta(chave, fn):
        try:
            novo[chave] = fn()
        except Exception as e:  # mantém o valor anterior
            erros.append(f"{chave}: {e}")

    tenta("cdi", lambda: sgs(4389))
    tenta("ipca_12m", lambda: sgs(13522))

    def selic():
        v = focus("ExpectativasMercadoAnuais",
                  f"Indicador eq 'Selic' and DataReferencia eq '{ano}' and baseCalculo eq 0",
                  "Indicador,Data,DataReferencia,Mediana,baseCalculo")
        return {"valor": round(float(v["Mediana"]), 4), "data": v["Data"], "ano": ano, "fonte": "BCB/Focus"}

    def ipca_focus():
        v = focus("ExpectativasMercadoInflacao12Meses",
                  "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0",
                  "Indicador,Data,Suavizada,Mediana,baseCalculo")
        return {"valor": round(float(v["Mediana"]), 4), "data": v["Data"], "fonte": "BCB/Focus"}

    tenta("selic_focus", selic)
    tenta("ipca_focus_12m", ipca_focus)

    if novo != atual:
        novo["atualizado_em"] = datetime.now(BRT).isoformat(timespec="minutes")
    ARQ.write_text(json.dumps(novo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(novo, ensure_ascii=False, indent=2))
    if erros:
        print("Falhas (valores anteriores mantidos):", *erros, sep="\n- ")
    if len(erros) == 4:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
