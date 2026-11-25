"""Calor: difusividade térmica κ e Δn pela bossa (montagem A, tanque de 5 cm).

Uso:  python analisar_calor.py                  (todos os ensaios em fotos/calor/)
      python analisar_calor.py --ensaio es1_e1  (só um)
      python analisar_calor.py --teste          (fotos sintéticas com κ conhecido)
Ver LEIA-ME.txt.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import serie  # noqa: E402

if __name__ == '__main__':
    serie.principal('calor')
