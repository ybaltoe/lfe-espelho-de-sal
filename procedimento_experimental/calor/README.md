# Calor: difusividade térmica κ

**O que mede:** κ da água, pela largura da bossa (σ² = 2κ(t + t0)), e Δn entre as camadas, pela área da bossa. Água quente (~50 °C) sobre água fria, recipiente de 5 cm, Z ≈ 2 m, uma foto a cada 30 s durante 15 min.

**Script:** `analisar_calor.py`. Lê cada ensaio em `fotos/calor/<ensaio>/` e, para cada um, gera:
- `calor_<ensaio>.png` com quatro painéis: a bossa em três instantes, σ²(t) com resíduos, Δn(t) e 1/A²(t);
- `calor_<ensaio>.csv` com σ, A e a área de cada foto.

Depois junta os ensaios e escreve `resultados_calor.json`, que a tabela final usa, e `calor_resumo.png`.
- `--ensaio es1_e1` analisa só esse ensaio.
- `--reta` ajusta também uma reta de fundo, se a referência mexeu.
- `--teste` corre com fotos sintéticas de κ conhecido.

**Aulas:** 1 (dois primeiros ensaios) e 2 (três ou mais ensaios e κ com incerteza).

Detalhes em `LEIA-ME.txt`.
