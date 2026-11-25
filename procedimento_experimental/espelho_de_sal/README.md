# Espelho de sal (montagem B)

**O que mede:** Δn pelo ângulo-limite do espelho. A rampa LEGO de k placas inclina o laser, e regista-se o último k em que o feixe ainda volta para baixo e o primeiro em que atravessa. Testa também a previsão de que o ângulo não muda com o tempo.

**Script:** `espelho.py`. Lê `fotos/espelho_de_sal/ensaios.csv` e `registo.txt` e gera `espelho_de_sal.png`, com θ contra o tempo e a passagem de k placas para Δn. Escreve `resultados_espelho_de_sal.json`.
- `--pasta` aponta para outro tanque, por exemplo `fotos/espelho_calor/` com `tipo = calor` no registo.
- `--teste` corre com ensaios sintéticos (Δn de 5 % de sal).

**Aulas:** 3 (aos 30, 60 e 90 min) e 4 (opcional: espelho com o calor).

Detalhes em `LEIA-ME.txt`.
