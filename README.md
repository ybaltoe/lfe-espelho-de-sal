# LFE Ótica: espelho de sal

Código do projeto de Ótica do LFE: medir a difusão do calor e do sal na água pelo desvio de um laser num meio de índice gradiente (GRIN).

## O que se mede

1. **Calor.** Água quente sobre água fria. A largura da bossa no ecrã dá a difusividade térmica κ.
2. **Sal.** Água salgada sob água pura. Dá D_sal, cerca de 100 vezes menor que κ.
3. **Espelho de sal.** O ângulo-limite medido com uma rampa LEGO dá Δn.

## Análise

De cada fotografia do ecrã tira-se o traço do laser, subtrai-se a referência e ajusta-se uma gaussiana δ(y) = A·exp(−(y − y_c)²/2σ²). O declive da reta σ² contra t é 2D. A área da bossa dá Δn = área / (Z·L).

## Estrutura

Pastas a criar à medida que o código aparece.
