# Simulador bancário · Renda fixa

Página estática (GitHub Pages) com Simulador de aplicação, Gross-up e Equivalência de taxas.

## Indicadores automáticos
`indicadores.json` é atualizado pela GitHub Action `.github/workflows/indicadores.yml`
(dias úteis, 09:20 e 12:20 de Brasília) com dados do Banco Central:

| Campo | Fonte |
|---|---|
| `cdi` | SGS 4389 – CDI anualizado base 252 |
| `ipca_12m` | SGS 13522 – IPCA acumulado 12 meses |
| `selic_focus` | Focus – mediana da Selic no fim do ano corrente |
| `ipca_focus_12m` | Focus – mediana do IPCA para os próximos 12 meses (suavizada) |

Na página, o CDI projetado usa `cdi` e o IPCA projetado usa `ipca_focus_12m`.
Se você digitar outro valor, a página entra em "Projeção manual"; o botão "usar oficiais" volta aos dados do BCB.

## Como publicar
1. Suba estes arquivos na raiz de um repositório (mantendo as pastas `.github/workflows` e `scripts`).
2. Settings → Pages → Source: *Deploy from a branch* → branch `main`, pasta `/ (root)`.
3. Settings → Actions → General → Workflow permissions: *Read and write permissions*.
4. Actions → "Atualiza indicadores" → **Run workflow** para preencher o `indicadores.json` pela primeira vez.
