# Sal: coeficiente de difusão D do NaCl

**O que mede:** D do sal na água, pela largura da bossa (σ² = 2D(t + t0)), e Δn pela área da bossa, que no sal deve ficar constante. Solução de sal a 5 % sob água pura, cuvete de 10 mm, Z ≈ 1 m, uma foto a cada 5 min durante 45 a 60 min.

**Script:** `analisar_sal.py`. Faz o mesmo que o do calor, com os ensaios de `fotos/sal/<ensaio>/`, e gera `sal_<ensaio>.png`, `sal_<ensaio>.csv` e `resultados_sal.json`.
- `--teste` corre com fotos sintéticas de D conhecido.
- Plano B, sem vareta: δ medido à mão ponto a ponto num `perfis.csv`.

**Aulas:** 2 (primeira série, em paralelo com o calor) e 3 (duas séries, D_sal e Δn).

Detalhes em `LEIA-ME.txt`.
