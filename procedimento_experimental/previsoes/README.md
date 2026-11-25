# Previsões (antes de medir)

**O que faz:** calcula, com os valores de tabela, o que se espera ver: a largura σ da bossa e o desvio máximo no ecrã ao longo do tempo, se a aproximação de tanque fino vale, quanto traço é preciso para o ajuste ter asas, e o ângulo do espelho em placas da rampa.

**Script:** `previsoes.py`. Não lê dados. Escreve as tabelas no terminal e gera `previsoes.png` (o traço previsto no ecrã para o calor e as retas σ²(t)).
- `--Z-calor`, `--L-calor`, `--Z-sal`, `--L-sal` mudam a montagem (mm).
- `--Tq`, `--Tf` e `--sal-pct` mudam as temperaturas e a concentração.

**Aula:** 1 (e sempre que se mudar a montagem). Os números entram na evidência de viabilidade.

Detalhes em `LEIA-ME.txt`.
