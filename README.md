# Espelho de sal: difusão medida com luz (GRIN)

Análise das medições do projeto de Ótica. Duas camadas de água num tanque, com o índice de refração maior em baixo, porque a água de baixo é mais fria ou tem sal. A fronteira esbate-se por difusão e o tanque passa a ser um meio de índice gradiente. Uma folha de laser a 45° atravessa-o e desenha no ecrã uma bossa com a forma do gradiente: a largura da bossa dá o coeficiente de difusão e a área dá Δn. Num tanque comprido, o mesmo gradiente devolve o feixe para baixo como um espelho, abaixo de um ângulo-limite que se mede com uma rampa LEGO.

**Autoras:** _(a preencher)_

**Disciplina:** Laboratório de Física Experimental (LFE), projeto de Ótica, IST, 2026

## Pastas

| Pasta | Experiência | Aula |
|---|---|---|
| `procedimento_experimental/previsoes/` | O que se espera ver: σ, desvio no ecrã, tanque fino, placas da rampa | 1 |
| `procedimento_experimental/calibracao/` | Escalas do pente LEGO e do papel milimétrico, traço de referência | todas |
| `procedimento_experimental/calor/` | Difusividade térmica κ e Δn, água quente sobre fria | 1 e 2 |
| `procedimento_experimental/sal/` | Coeficiente de difusão D do NaCl e Δn | 2 e 3 |
| `procedimento_experimental/espelho_de_sal/` | Δn pelo ângulo-limite e teste de que não muda com o tempo | 3 (e 4) |
| `procedimento_experimental/resultados_finais/` | Tabela final, κ/D, os dois Δn e o orçamento de incertezas | 4 |
| `fotos/` | Fotos, vídeos e registos de cada ensaio | todas |

`procedimento_experimental/comum.py` tem o que todos os scripts usam: ler as fotos e os registos, encontrar o traço do laser, calibrar, ajustar a bossa e os valores de tabela. `procedimento_experimental/serie.py` tem a análise de uma série de fotos, que é igual no calor e no sal.

Cada pasta tem um `README.md` curto e um `LEIA-ME.txt` com o protocolo e o passo a passo do código.

## Dependências

Python 3.10 ou mais recente.

```
pip install -r requirements.txt
```

## Dados

As fotos não estão no repositório porque são pesadas. Os registos (`registo.txt`, `.csv`) estão. A organização das fotos e as regras para as tirar (exposição bloqueada, não passar pelo WhatsApp) estão em `fotos/README.md`.

## Como correr

Dentro da pasta da experiência:

```
cd procedimento_experimental/calor
python analisar_calor.py
```

Cada script escreve os resultados no terminal e guarda as figuras `.png` na mesma pasta. Todos aceitam `--teste`, que corre com fotos sintéticas de valores conhecidos para confirmar que o código funciona antes de haver dados, e `--nao-mostrar`, que só guarda as figuras.

Ordem numa sessão: `calibracao/calibrar.py` para confirmar a montagem, depois `calor/` ou `sal/`, e no fim `resultados_finais/tabela_final.py`.

Os valores de tabela em `comum.py` (n da água, κ, D do NaCl, dn/dc) são aproximados. Têm de ser confirmados na bibliografia antes do relatório.
