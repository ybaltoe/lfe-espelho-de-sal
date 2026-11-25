"""Tabela final de resultados e orçamento de incertezas (aula 4 / relatório).

Junta o que os outros scripts guardaram:
  ../calor/resultados_calor.json                  κ e Δn do calor (área)
  ../sal/resultados_sal.json                      D e Δn do sal (área)
  ../espelho_de_sal/resultados_espelho_de_sal.json    Δn do sal (espelho)
  ../espelho_de_sal/resultados_espelho_calor.json     Δn do calor (espelho, opcional)
e escreve a tabela no terminal, em tabela_resultados.md e em tabela_resultados.tex.

Uso:  python tabela_final.py
"""
import os
import re
import sys
import json
import math

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import comum as C  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))


def ler(rel):
    f = os.path.join(C.PASTA_PE, rel)
    if not os.path.exists(f):
        return None
    with open(f, encoding='utf-8') as fh:
        return json.load(fh)


def fmt(v, u, exp=None):
    if v is None:
        return '(por medir)'
    if exp is None:
        casas = max(0, -int(math.floor(math.log10(u))) + 1) if u > 0 else 5
        return f'{v:.{casas}f} ± {u:.{casas}f}'
    e = 10 ** exp
    casas = max(0, -int(math.floor(math.log10(u / e))) + 1) if u > 0 else 2
    return f'({v / e:.{casas}f} ± {u / e:.{casas}f}) × 10^{exp}'


def main():
    calor, sal = ler('calor/resultados_calor.json'), ler('sal/resultados_sal.json')
    esp, espc = ler('espelho_de_sal/resultados_espelho_de_sal.json'), ler('espelho_de_sal/resultados_espelho_calor.json')

    linhas = []   # grandeza, método, valor, referência, z

    def junta(gr, met, v, u, ref, exp=None, ref_txt=None):
        z = C.z_score(v, u, ref) if (v is not None and ref is not None) else None
        rt = ref_txt or ('sem valor' if ref is None else (fmt(ref, 0, exp).split(' ±')[0] if exp is None else
                                                    f'{ref / 10 ** exp:.2f} × 10^{exp}'))
        linhas.append((gr, met, fmt(v, u, exp) if v is not None else '(por medir)', rt,
                       '' if z is None else f'{z:+.1f}'))

    junta('κ (calor)', 'largura da bossa', calor and calor['D'], calor and calor['u_D'], calor and calor['D_ref'], -7)
    junta('D (sal)', 'largura da bossa', sal and sal['D'], sal and sal['u_D'], sal and sal['D_ref'], -9)
    if calor and sal:
        r = calor['D'] / sal['D']
        ur = r * math.hypot(calor['u_D'] / calor['D'], sal['u_D'] / sal['D'])
        junta('κ / D', 'razão (n.º de Lewis)', r, ur, calor['D_ref'] / sal['D_ref'])
    else:
        junta('κ / D', 'razão (n.º de Lewis)', None, None, None, ref_txt='≈ 100')
    junta('Δn (calor)', 'área da bossa', calor and calor['Dn'], calor and calor['u_Dn'], calor and calor['Dn_ref'])
    if espc:
        junta('Δn (calor)', 'espelho', espc['Dn'], espc['u_Dn'], espc['Dn_ref'])
    junta('Δn (sal)', 'área da bossa', sal and sal['Dn'], sal and sal['u_Dn'], sal and sal['Dn_ref'])
    junta('Δn (sal)', 'espelho de sal', esp and esp['Dn'], esp and esp['u_Dn'], esp and esp['Dn_ref'])

    cab = ('Grandeza', 'Método', 'Valor medido ± u', 'Referência (aprox.)', 'z')
    larg = [max(len(str(l[i])) for l in linhas + [cab]) for i in range(5)]
    print('TABELA FINAL DE RESULTADOS\n')
    for l in [cab] + linhas:
        print('  '.join(str(c).ljust(w) for c, w in zip(l, larg)))
    print('\nz = (medido − referência)/u. Os valores de referência são aproximados (comum.py): confirmar.')

    if sal and esp:
        z = C.z_score(sal['Dn'], sal['u_Dn'], esp['Dn'], esp['u_Dn'])
        print(f"\nOs dois Δn do sal concordam? área {sal['Dn']:.5f} ± {sal['u_Dn']:.5f} vs espelho "
              f"{esp['Dn']:.5f} ± {esp['u_Dn']:.5f}  ->  z = {z:+.1f}  "
              f"({'compatíveis' if abs(z) < 2 else 'NÃO compatíveis: discutir no relatório'})")
    if esp and esp.get('teste_tempo'):
        tt = esp['teste_tempo']
        print(f"Ângulo do espelho vs tempo: {tt['declive_grau_por_min']:+.4f} ± {tt['u']:.4f} °/min (z = {tt['z']:+.1f})")

    print('\nORÇAMENTO DE INCERTEZAS (relativas)')
    for nome, R, simb in (('calor', calor, 'κ'), ('sal', sal, 'D')):
        if not R:
            continue
        print(f"  {simb} ({nome}): ajuste {100 * R['u_D_ajuste'] / R['D']:.1f} %, entre ensaios "
              f"{100 * R['u_D_entre'] / R['D'] if R['u_D_entre'] == R['u_D_entre'] else float('nan'):.1f} %, "
              f"escala do pente {100 * R['u_D_escala'] / R['D']:.1f} %  ->  total {100 * R['u_D'] / R['D']:.1f} %")
        print(f"  Δn ({nome}, área): ajuste/ensaios {100 * R['u_Dn_ajuste'] / R['Dn']:.1f} %, Z "
              f"{100 * R['u_Dn_Z'] / R['Dn']:.1f} %, L {100 * R['u_Dn_L'] / R['Dn']:.1f} %, escalas "
              f"{100 * R['u_Dn_escalas'] / R['Dn']:.1f} %  ->  total {100 * R['u_Dn'] / R['Dn']:.1f} %")
    if esp:
        print(f"  Δn (espelho): θ entre ensaios ± {math.degrees(esp['u_A']):.2f}°, rampa ± {math.degrees(esp['u_B']):.2f}°, "
              f"placa/base ± {math.degrees(esp['u_geo']):.3f}°  ->  Δn ± {100 * esp['u_Dn'] / esp['Dn']:.1f} %")
    if sal:
        print('  Temperatura no sal: D muda ~2 %/°C; conta na comparação com a tabela, não na medida.')

    with open(os.path.join(AQUI, 'tabela_resultados.md'), 'w', encoding='utf-8') as f:
        f.write('| ' + ' | '.join(cab) + ' |\n|' + '---|' * 5 + '\n')
        for l in linhas:
            f.write('| ' + ' | '.join(str(c) for c in l) + ' |\n')
    with open(os.path.join(AQUI, 'tabela_resultados.tex'), 'w', encoding='utf-8') as f:
        f.write('\\begin{tabular}{llllr}\n\\hline\n' + ' & '.join(cab) + ' \\\\\n\\hline\n')
        for l in linhas:
            cel = [str(c).replace('±', '$\\pm$').replace('× 10^', '$\\times 10^{').replace('Δn', '$\\Delta n$')
                   .replace('κ', '$\\kappa$') for c in l]
            cel = [c + '}$' if '10^{' in c else c for c in cel]
            cel = [re.sub(r'(?<=\d)\.(?=\d)', '{,}', c) for c in cel]       # vírgula decimal
            f.write(' & '.join(cel) + ' \\\\\n')
        f.write('\\hline\n\\end{tabular}\n')
    print('\nEscrito: tabela_resultados.md e tabela_resultados.tex')


if __name__ == '__main__':
    main()
