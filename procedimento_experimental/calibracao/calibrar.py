"""Calibração de uma montagem A: escala do pente LEGO (px por mm de altura no tanque), escala do ecrã
(px por mm de papel milimétrico) e traço de referência.

Uso:  python calibrar.py                       (todas as montagens em fotos/calibracao/)
      python calibrar.py --montagem es1_calor  (só uma)
      python calibrar.py --teste               (fotos sintéticas)
Ver LEIA-ME.txt. Os scripts do calor e do sal fazem esta mesma calibração sozinhos; este faz a figura,
para a VER e confirmar antes de analisar os ensaios.
"""
import os
import sys
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import comum as C  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
AZUL, LARANJA, VERDE, CINZA = '#2a78d6', '#eb6834', '#2e9e5b', '#777'


def figura(cal, img_ref, nome_fig):
    fig, ax = plt.subplots(2, 2, figsize=(12, 9))
    a = ax[0, 0]
    a.imshow(np.clip(img_ref, 0, 1))
    tr = cal['tr_ref']
    a.plot(tr['x'], tr['linha'], color='cyan', lw=0.8, label='traço encontrado')
    if cal['recorte']:
        x0, x1, y0, y1 = cal['recorte']
        a.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color='yellow', lw=1, label='recorte')
    a.set_title('(a) referência: traço encontrado')
    a.legend(fontsize=8, loc='lower left')
    a.axis('off')

    a = ax[0, 1]
    tp = cal['tr_pente']
    a.plot(tp['x'], tp['pico'], color=LARANJA, lw=0.8, label='intensidade do traço (pente)')
    pe = cal['pente']
    for c in pe['centros']:
        a.axvline(c, color=AZUL, lw=0.8, alpha=0.7)
    a.set_xlabel('x (px)')
    a.set_ylabel('vermelho no traço')
    a.set_title(f"(b) sombras do pente: {pe['n']} encontradas (linhas azuis)")
    a.legend(fontsize=8)

    a = ax[1, 0]
    y = pe['k'] * C.PASSO_PENTE_MM
    a.plot(y, pe['centros'], 'o', color=AZUL)
    yy = np.linspace(0, y.max(), 10)
    a.plot(yy, pe['x0'] + cal['m'] * yy, color=LARANJA, label=f"m = {cal['m']:.3f} ± {cal['u_m']:.3f} px/mm")
    a.set_xlabel('altura da sombra no tanque (mm), a 6,4 mm umas das outras')
    a.set_ylabel('posição no traço x (px)')
    a.set_title(f"(c) escala do tanque (resíduo {pe['residuo_mm']:.2f} mm)")
    a.legend(fontsize=8)
    ins = a.inset_axes([0.6, 0.1, 0.36, 0.28])
    ins.axhline(0, color=CINZA, lw=0.8)
    ins.plot(y, (pe['centros'] - pe['x0'] - cal['m'] * y) / cal['m'], 'o', ms=3, color=AZUL)
    ins.set_title('resíduos (mm)', fontsize=7)
    ins.tick_params(labelsize=6)

    a = ax[1, 1]
    g = cal['grelha']
    if g:
        for r, c, nome in ((g['linhas'], AZUL, 'linhas horizontais'), (g['colunas'], VERDE, 'linhas verticais')):
            if r is None:
                continue
            n = min(len(r['ac']), int(12 * r['P']) + 5)
            a.plot(np.arange(n), r['ac'][:n], color=c, lw=0.8, label=f"{nome}: {r['P']:.3f} px/mm")
            a.plot(r['lags'][:12], np.interp(r['lags'][:12], np.arange(len(r['ac'])), r['ac']), 'o', ms=3, color=c)
        a.set_xlabel('desfasamento (px)')
        a.set_ylabel('autocorrelação')
        a.set_title(f"(d) grelha do papel: p = {cal['p']:.3f} ± {cal['u_p']:.3f} px/mm\n"
                    'os pontos têm de cair nos picos 1, 2, 3, … (1 mm cada)', fontsize=10)
        a.legend(fontsize=8)
    else:
        a.text(0.5, 0.5, f"p = {cal['p']:.3f} px/mm (do registo)", ha='center', transform=a.transAxes)
        a.axis('off')
    fig.suptitle(f"Calibração da montagem {cal['nome']}  ·  M = m/p = {cal['m'] / cal['p']:.3f}")
    fig.tight_layout()
    C.virgulas(fig)
    fig.savefig(nome_fig, dpi=130)
    print(f'   Figura: {os.path.basename(nome_fig)}')


def main():
    ap = argparse.ArgumentParser(description='Calibração da montagem A (pente LEGO e papel milimétrico)')
    ap.add_argument('--montagem', action='append', help='pasta em fotos/calibracao/; pode repetir')
    ap.add_argument('--teste', action='store_true', help='fotos sintéticas (m = 6,3 e p = 6,0 px/mm)')
    ap.add_argument('--nao-mostrar', action='store_true')
    args = ap.parse_args()
    if args.nao_mostrar:
        matplotlib.use('Agg')

    if args.teste:
        rng = np.random.default_rng(1)
        ref = C.imagem_sintetica(p=6.0, m=6.3, rng=rng)
        pen = C.imagem_sintetica(p=6.0, m=6.3, pente=True, rng=rng)
        cal = C.calibrar(ref, pen, {'z_mm': '2000', 'l_mm': '50'})
        cal['nome'] = 'teste'
        print('TESTE (verdadeiro: m = 6,300 px/mm, p = 6,000 px/mm, x0 = 250 px)')
        print('\n'.join('   ' + l for l in C.resumo_calibracao(cal)))
        print(f"   x0 = {cal['x0']:.1f} px")
        figura(cal, ref, os.path.join(AQUI, 'calibracao_teste.png'))
    else:
        base = os.path.join(C.PASTA_FOTOS, 'calibracao')
        nomes = args.montagem or sorted(d for d in os.listdir(base)
                                        if os.path.isdir(os.path.join(base, d)) and not d.startswith('_'))
        if not nomes:
            raise SystemExit(f'Não há montagens em {base} (ver fotos/README.md).')
        for nome in nomes:
            print(f'\n{nome}:')
            cal = C.carregar_calibracao(nome)
            print('\n'.join('   ' + l for l in C.resumo_calibracao(cal)))
            pasta = os.path.join(base, nome)
            ref = C.ler_imagem(C._ficheiro(pasta, 'referencia'), cal['reduzir'])
            figura(cal, ref, os.path.join(AQUI, f'calibracao_{nome}.png'))
    if not args.nao_mostrar:
        plt.show()


if __name__ == '__main__':
    main()
