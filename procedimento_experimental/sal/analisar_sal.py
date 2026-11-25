"""Sal: coeficiente de difusão D do NaCl e Δn pela bossa (montagem A, cuvete de 10 mm).

Uso:  python analisar_sal.py                  (todos os ensaios em fotos/sal/)
      python analisar_sal.py --ensaio es2_s1  (só um)
      python analisar_sal.py --teste          (fotos sintéticas com D conhecido)
Ver LEIA-ME.txt.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import serie  # noqa: E402

if __name__ == '__main__':
    serie.principal('sal')
