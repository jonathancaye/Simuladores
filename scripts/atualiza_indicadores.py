"""Atualiza indicadores.json com dados oficiais do Banco Central.

- CDI anualizado (base 252) ........ SGS 4389
- IPCA acumulado em 12 meses ....... SGS 13522
- Selic Focus (fim do ano corrente)  Expectativas de Mercado Anuais
- IPCA Focus próximos 12 meses ..... Expectativas de Mercado Inflação 12 meses (suavizada)

Se alguma consulta falhar, mantém o valor anterior do arquivo.
"""
import json
import pathlib
import urllib.error
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


def _detalhe(e):
    """Mensagem de erro com o corpo da resposta HTTP, quando houver."""
    if isinstance(e, urllib.error.HTTPError):
        try:
            corpo = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            corpo = ""
        return f"HTTP {e.code} {e.reason} {corpo}".strip()
    return f"{type(e).__name__}: {e}"


def focus(entidade, filtro, campos, conferir):
    """Consulta o Focus (API Olinda). Tenta a consulta filtrada; se falhar,
    baixa os registros mais recentes e filtra aqui mesmo."""
    tentativas = [
        [("$top", "1"), ("$filter", filtro), ("$orderby", "Data desc"), ("$format", "json"), ("$select", campos)],
        [("$top", "300"), ("$orderby", "Data desc"), ("$format", "json")],
    ]
    falhas = []
    for params in tentativas:
        # A API Olinda exige os nomes "$top", "$filter"... sem codificar o "$"
        qs = "&".join(k + "=" + urllib.parse.quote(v, safe=",") for k, v in params)
        try:
            dados = [d for d in get_json(OLINDA + entidade + "?" + qs)["value"] if conferir(d)]
            if dados:
                return dados[0]
            falhas.append("sem resultados")
        except Exception as e:
            falhas.append(_detalhe(e))
    raise ValueError(" | ".join(falhas))


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
            erros.append(f"{chave}: {_detalhe(e)}")

    tenta("cdi", lambda: sgs(4389))
    tenta("ipca_12m", lambda: sgs(13522))

    def selic():
        v = focus("ExpectativasMercadoAnuais",
                  f"Indicador eq 'Selic' and DataReferencia eq '{ano}' and baseCalculo eq 0",
                  "Indicador,Data,DataReferencia,Mediana,baseCalculo",
                  lambda d: d.get("Indicador") == "Selic" and str(d.get("DataReferencia")) == str(ano)
                  and d.get("baseCalculo") in (0, "0") and d.get("Mediana") is not None)
        return {"valor": round(float(v["Mediana"]), 4), "data": v["Data"], "ano": ano, "fonte": "BCB/Focus"}

    def ipca_focus():
        v = focus("ExpectativasMercadoInflacao12Meses",
                  "Indicador eq 'IPCA' and Suavizada eq 'S' and baseCalculo eq 0",
                  "Indicador,Data,Suavizada,Mediana,baseCalculo",
                  lambda d: d.get("Indicador") == "IPCA" and d.get("Suavizada") == "S"
                  and d.get("baseCalculo") in (0, "0") and d.get("Mediana") is not None)
        return {"valor": round(float(v["Mediana"]), 4), "data": v["Data"], "fonte": "BCB/Focus"}

    tenta("selic_focus", selic)
    tenta("ipca_focus_12m", ipca_focus)

    # registra as falhas no próprio arquivo para facilitar o diagnóstico
    if erros:
        novo["erros"] = erros
    else:
        novo.pop("erros", None)
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
