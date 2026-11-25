# Calibração da montagem A

**O que mede:** as duas escalas que convertem píxeis em milímetros. O pente LEGO dá m, os píxeis por mm de altura no tanque, a partir das sombras a cada 6,4 mm. A grelha do papel milimétrico dá p, os píxeis por mm no ecrã. Também guarda o traço de referência, que se subtrai a todas as fotos.

**Script:** `calibrar.py`. Lê `fotos/calibracao/<montagem>/` (`referencia.jpg`, `pente.jpg`, `registo.txt`) e gera `calibracao_<montagem>.png`, com o traço encontrado, as sombras do pente, a reta da escala e a autocorrelação da grelha.
- `--montagem es1_calor` faz só essa montagem.
- `--teste` corre com fotos sintéticas (m = 6,3 e p = 6,0 px/mm).

**Aulas:** no início de cada sessão e sempre que se mexe no recipiente, no ecrã ou no telemóvel. Os scripts do calor e do sal fazem esta calibração sozinhos. Este faz a figura, para a confirmarem antes de analisar.

Detalhes em `LEIA-ME.txt`.
