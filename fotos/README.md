# Fotos e registos

As fotos e os vídeos não vão para o GitHub, porque são pesados (cerca de 3 MB por foto e centenas de fotos). Os `registo.txt` e os `.csv` vão.

**Link para as fotos:** _(a acrescentar)_

Depois de descarregar as fotos, põe cada uma na pasta do ensaio a que pertence. Os scripts leem daqui.

## Estrutura

```
fotos/
  calibracao/<montagem>/     uma pasta por montagem e sessão (ex.: es1_calor, es3_sal)
      referencia.jpg         tanque com água homogénea: traço sem bossa
      pente.jpg              o mesmo, com o pente LEGO encostado à parede de entrada
      registo.txt            Z, L e incertezas
  calor/<ensaio>/            uma pasta por ensaio (ex.: es1_e1, es1_e2, es2_e1)
      IMG_xxxx.jpg ...       fotos do ecrã de 30 em 30 s
      registo.txt            calibração usada, t0, temperaturas, fotos a excluir
  sal/<ensaio>/              igual, fotos de 5 em 5 min
  espelho_de_sal/
      ensaios.csv            uma linha por subida/descida da rampa
      registo.txt            sal, temperatura, medidas da rampa
  teste_copo/                fotos do teste no copo (só para o relatório e o vídeo)
```

As pastas que começam por `_` (como `_modelo`) são ignoradas pelos scripts. Para começar um ensaio novo, copia a pasta `_modelo`, muda-lhe o nome e preenche o `registo.txt`.

## Regras para as fotos

- O telemóvel fica sempre na mesma posição (batente LEGO), com o mesmo zoom e com a **focagem e a exposição bloqueadas** (no iPhone: carregar no ecrã até aparecer "AE/AF bloqueado").
- A exposição tem de ser baixa o suficiente para o traço sair **vermelho**, não branco.
- A hora de cada foto vem do próprio ficheiro (EXIF). Não se pode enviar as fotos pelo WhatsApp, porque o WhatsApp apaga essa informação. Passa-as por cabo, Google Drive ou AirDrop.
- Fotos HEIC do iPhone precisam de `pip install pillow-heif`. Em alternativa, põe a câmara em JPG (Definições > Câmara > Formatos > Mais compatível).
- Nunca se apagam fotos falhadas. Para as tirar da análise, escreve-as em `excluir` no `registo.txt` e explica porquê nas `notas`.
