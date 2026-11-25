"""Espelho de sal (montagem B): Δn pelo ângulo-limite medido com a rampa LEGO.

Uso:  python espelho.py                         (lê fotos/espelho_de_sal/ensaios.csv e registo.txt)
      python espelho.py --pasta ../../fotos/espelho_calor   (outro tanque, por exemplo o do calor)
      python espelho.py --teste                 (ensaios sintéticos com Δn conhecido)
Ver LEIA-ME.txt.

Física: um raio lançado na camada de baixo (índice n_b) com ângulo φ acima da horizontal volta para
baixo se encontrar a altura onde n = n_b·cos φ. O último ângulo que ainda volta é φ_c:
    cos φ_c = n_cima / n_b          ->   Δn = n_b − n_cima = n_b·(1 − cos φ_c)
Fora do tanque, ao entrar por uma parede vertical:  sin θ_ar = n_b·sin φ_c.
A rampa de k placas dá θ_ar:  tan θ = k·placa / base.
"""
import os
import sys
import csv
import math
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import comum as C  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
AZUL, LARANJA, VERDE, CINZA = '#2a78d6', '#eb6834', '#2e9e5b', '#777'


def angulo_rampa(k, placa, base, geom='tan'):
    h = k * placa
    return math.atan(h / base) if geom == 'tan' else math.asin(min(h / base, 1))


def dn_de_theta(theta, n_cima):
    """Δn a partir do ângulo-limite no ar; n_b = n_cima + Δn (iterado, converge logo)."""
    dn = 0.0
    for _ in range(20):
        n_b = n_cima + dn
        phi = math.asin(math.sin(theta) / n_b)
        dn = n_b * (1 - math.cos(phi))
    return dn, phi


def theta_de_dn(dn, n_cima):
    n_b = n_cima + dn
    phi = math.acos(n_cima / n_b)
    return math.asin(n_b * math.sin(phi)), phi


def ler_ensaios(caminho):
    with open(caminho, encoding='utf-8-sig') as f:
        txt = f.read()
    linhas = [l for l in txt.splitlines() if l.strip() and not l.lstrip().startswith('#')]
    sep = ';' if ';' in linhas[0] else ','
    out = []
    for row in csv.DictReader(linhas, delimiter=sep):
        row = {k.strip().lower(): (v or '').strip() for k, v in row.items()}
        if not row.get('k_refletido') or not row.get('k_atravessa'):
            continue
        out.append(dict(tempo=float(row.get('tempo_min', '0').replace(',', '.') or 0),
                        kr=float(row['k_refletido'].replace(',', '.')),
                        ka=float(row['k_atravessa'].replace(',', '.')),
                        sentido=row.get('sentido', ''), obs=row.get('observador', ''),
                        notas=row.get('notas', '')))
    return out


def analisar(ensaios, reg):
    placa = C.num(reg, 'placa_mm', C.PLACA_MM)
    u_placa = C.num(reg, 'u_placa_mm', 0.02)
    base = C.num(reg, 'base_mm', 32 * C.ESPIGA_MM)
    u_base = C.num(reg, 'u_base_mm', 0.5)
    geom = reg.get('geometria', 'tan').lower()
    tipo = reg.get('tipo', 'sal').lower()
    if tipo == 'calor':
        Tc, Tb = C.num(reg, 't_cima', 50.0), C.num(reg, 't_baixo', 20.0)
        n_cima = C.n_agua(Tc)
        dn_ref = C.n_agua(Tb) - n_cima
        txt_ref = f'T_cima = {Tc:.1f} °C, T_baixo = {Tb:.1f} °C'
    else:
        T = C.num(reg, 't', 21.0)
        n_cima = C.n_agua(T)
        w = C.fracao_sal(reg)
        dn_ref = C.DN_DW_SAL * w if w is not None else None
        txt_ref = f'T = {T:.1f} °C' + (f', sal a {w:.2f} %' if w is not None else '')

    for e in ensaios:
        t1, t2 = angulo_rampa(e['kr'], placa, base, geom), angulo_rampa(e['ka'], placa, base, geom)
        e['theta'] = (t1 + t2) / 2
        e['meio'] = abs(t2 - t1) / 2
        e['dn'], e['phi'] = dn_de_theta(e['theta'], n_cima)
        if e['ka'] <= e['kr']:
            e['aviso'] = 'k_atravessa ≤ k_refletido'

    th = np.array([e['theta'] for e in ensaios])
    meio = np.array([e['meio'] for e in ensaios])
    n = len(th)
    th_m = float(th.mean())
    u_A = float(th.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0
    u_B = float(meio.mean() / math.sqrt(3))          # resolução da rampa: distribuição uniforme
    # placa e base: tan θ = k·placa/base
    k_ef = math.tan(th_m) * base / placa
    dth_dplaca = k_ef / base * math.cos(th_m) ** 2
    dth_dbase = -k_ef * placa / base ** 2 * math.cos(th_m) ** 2
    u_geo = math.hypot(dth_dplaca * u_placa, dth_dbase * u_base)
    u_th = math.sqrt(u_A ** 2 + u_B ** 2 + u_geo ** 2)
    dn_m, phi_m = dn_de_theta(th_m, n_cima)
    h = 1e-5
    ddn = (dn_de_theta(th_m + h, n_cima)[0] - dn_de_theta(th_m - h, n_cima)[0]) / (2 * h)
    u_dn = abs(ddn) * u_th
    u_dn_conserv = abs(ddn) * float(meio.mean())     # "meia divisão" do plano (mais conservador)

    # o ângulo muda com o tempo? (previsão: não)
    tempos = np.array([e['tempo'] for e in ensaios])
    teste_t = None
    if len(set(tempos)) >= 2:
        u_i = np.full(n, math.sqrt(max(u_A * math.sqrt(n), 1e-12) ** 2 + u_B ** 2))
        r = C.reta_ponderada(tempos, th, u_i)
        dec, u_dec = r['a'], math.sqrt(r['cov'][0, 0])
        teste_t = dict(declive_grau_por_min=math.degrees(dec), u=math.degrees(u_dec), z=dec / u_dec)
    grupos = {}
    for e in ensaios:
        grupos.setdefault(e['tempo'], []).append(e['theta'])
    sentidos = {}
    for e in ensaios:
        if e['sentido']:
            sentidos.setdefault(e['sentido'].lower(), []).append(e['theta'])

    return dict(tipo=tipo, n=n, theta=th_m, u_theta=u_th, u_A=u_A, u_B=u_B, u_geo=u_geo,
                phi=phi_m, Dn=dn_m, u_Dn=u_dn, u_Dn_meia_divisao=u_dn_conserv, Dn_ref=dn_ref,
                n_cima=n_cima, texto_ref=txt_ref, teste_tempo=teste_t, grupos=grupos, sentidos=sentidos,
                placa=placa, base=base, geom=geom, ensaios=ensaios)


def imprimir(R):
    print(f"\nRampa: placa = {R['placa']:.3f} mm, base = {R['base']:.1f} mm ({R['geom']} θ = k·placa/base)")
    print(f"{'tempo':>6} {'k ref':>6} {'k atr':>6}  {'θ_ar (°)':>9} {'φ_c (°)':>8} {'Δn':>9}  sentido  observador")
    for e in R['ensaios']:
        print(f"{e['tempo']:6.0f} {e['kr']:6g} {e['ka']:6g}  {math.degrees(e['theta']):9.2f} "
              f"{math.degrees(e['phi']):8.2f} {e['dn']:9.5f}  {e['sentido']:<8} {e['obs']}"
              + (f"   AVISO: {e['aviso']}" if 'aviso' in e else ''))
    print(f"\nθ_ar = {math.degrees(R['theta']):.2f} ± {math.degrees(R['u_theta']):.2f}°  "
          f"(entre ensaios ± {math.degrees(R['u_A']):.2f}°, resolução da rampa ± {math.degrees(R['u_B']):.2f}°, "
          f"placa/base ± {math.degrees(R['u_geo']):.3f}°)")
    print(f"φ_c (na água) = {math.degrees(R['phi']):.2f}°")
    print(f"Δn = {R['Dn']:.5f} ± {R['u_Dn']:.5f}   ({100 * R['u_Dn'] / R['Dn']:.0f} %; "
          f"com a meia divisão inteira como no plano: ± {R['u_Dn_meia_divisao']:.5f})")
    if R['Dn_ref'] is not None:
        print(f"   tabela ≈ {R['Dn_ref']:.5f} ({R['texto_ref']})  ->  z = "
              f"{C.z_score(R['Dn'], R['u_Dn'], R['Dn_ref']):+.1f}")
    if R['teste_tempo']:
        tt = R['teste_tempo']
        print(f"\nO ângulo muda com o tempo? declive = {tt['declive_grau_por_min']:+.4f} ± {tt['u']:.4f} °/min "
              f"(z = {tt['z']:+.1f}; |z| < 2: compatível com 'não muda', como prevê a teoria)")
        for t, v in sorted(R['grupos'].items()):
            print(f"   t = {t:4.0f} min: θ = {math.degrees(np.mean(v)):.2f}°  ({len(v)} ensaios)")
    if len(R['sentidos']) >= 2:
        print('\nA subir vs a descer (histerese do critério):')
        for s, v in R['sentidos'].items():
            print(f"   {s:<8} θ = {math.degrees(np.mean(v)):.2f}°  ({len(v)})")


def figura(R, nome_fig):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    a = ax[0]
    cores = {}
    for e in R['ensaios']:
        c = cores.setdefault(e['sentido'] or '-', [AZUL, LARANJA, VERDE, CINZA][len(cores) % 4])
        a.errorbar(e['tempo'], math.degrees(e['theta']), yerr=math.degrees(e['meio']), fmt='o', color=c,
                   capsize=3, alpha=0.8)
    for s, c in cores.items():
        a.plot([], [], 'o', color=c, label=s)
    a.axhspan(math.degrees(R['theta'] - R['u_theta']), math.degrees(R['theta'] + R['u_theta']),
              color=AZUL, alpha=0.12, label='média ± u')
    if R['Dn_ref'] is not None:
        a.axhline(math.degrees(theta_de_dn(R['Dn_ref'], R['n_cima'])[0]), color=CINZA, ls='--',
                  label='previsto pela tabela')
    a.set_xlabel('tempo desde o enchimento (min)')
    a.set_ylabel('ângulo-limite no ar θ (°)')
    a.set_title('(a) o ângulo-limite não deve mudar com o tempo')
    a.legend(fontsize=8)

    a = ax[1]
    dns = np.linspace(0.001, 0.016, 200)
    a.plot(dns * 1e3, [math.degrees(theta_de_dn(d, R['n_cima'])[0]) for d in dns], color=AZUL,
           label='θ_ar(Δn)')
    for k in range(1, 30):
        thk = math.degrees(angulo_rampa(k, R['placa'], R['base'], R['geom']))
        if thk > 15:
            break
        a.axhline(thk, color=CINZA, lw=0.5, alpha=0.6)
        a.text(16.2, thk, f'{k}', fontsize=6, va='center', color=CINZA)
    a.errorbar(R['Dn'] * 1e3, math.degrees(R['theta']), xerr=R['u_Dn'] * 1e3, yerr=math.degrees(R['u_theta']),
               fmt='o', color=LARANJA, label='medido')
    a.set_xlabel('Δn (×10⁻³)')
    a.set_ylabel('θ_ar (°)')
    a.set_title('(b) da rampa (linhas = k placas) a Δn')
    a.legend(fontsize=8, loc='upper left')
    fig.suptitle(f"Espelho ({R['tipo']}): Δn = {R['Dn']:.5f} ± {R['u_Dn']:.5f}")
    fig.tight_layout()
    C.virgulas(fig)
    fig.savefig(nome_fig, dpi=150)
    print(f'\nFigura: {os.path.basename(nome_fig)}')


def ensaios_sinteticos():
    rng = np.random.default_rng(3)
    reg = {'tipo': 'sal', 't': '21', 'sal_g': '5.0', 'agua_g': '95.0'}
    dn = C.DN_DW_SAL * 5.0
    th, _ = theta_de_dn(dn, C.n_agua(21))
    k_ver = math.tan(th) * 256 / 3.2
    ens = []
    for t in (30, 60, 90):
        for sentido in ('sobe', 'desce', 'sobe', 'desce'):
            k = k_ver + rng.normal(0, 0.35)            # o critério 'atravessa' tem alguma dispersão
            kr = math.floor(k)
            ens.append(dict(tempo=t, kr=kr, ka=kr + 1, sentido=sentido, obs='A' if rng.random() < .5 else 'B',
                            notas=''))
    return ens, reg, dn, k_ver


def main():
    ap = argparse.ArgumentParser(description='Espelho de sal: Δn pelo ângulo-limite')
    ap.add_argument('--pasta', default=os.path.join(C.PASTA_FOTOS, 'espelho_de_sal'),
                    help='pasta com ensaios.csv e registo.txt')
    ap.add_argument('--teste', action='store_true')
    ap.add_argument('--nao-mostrar', action='store_true')
    args = ap.parse_args()
    if args.nao_mostrar:
        matplotlib.use('Agg')
    if args.teste:
        ens, reg, dn, k_ver = ensaios_sinteticos()
        print(f'TESTE: Δn = {dn:.5f} (5 % de sal), k verdadeiro = {k_ver:.2f} placas')
        R = analisar(ens, reg)
        imprimir(R)
        figura(R, os.path.join(AQUI, 'espelho_teste.png'))
        print(f"\nTESTE: recuperado Δn = {R['Dn']:.5f} ± {R['u_Dn']:.5f} (verdadeiro {dn:.5f})")
    else:
        f = os.path.join(args.pasta, 'ensaios.csv')
        if not os.path.exists(f):
            raise SystemExit(f'Não existe {f} (ver o modelo em fotos/espelho_de_sal/ e o LEIA-ME).')
        reg = C.ler_registo(os.path.join(args.pasta, 'registo.txt'))
        ens = ler_ensaios(f)
        if not ens:
            raise SystemExit(f'{f} não tem ensaios preenchidos.')
        R = analisar(ens, reg)
        imprimir(R)
        nome = os.path.basename(os.path.normpath(args.pasta))
        figura(R, os.path.join(AQUI, f'{nome}.png'))
        out = {k: v for k, v in R.items() if k not in ('ensaios', 'grupos', 'sentidos')}
        out['ensaios'] = [{k: v for k, v in e.items()} for e in R['ensaios']]
        destino = os.path.join(AQUI, f'resultados_{nome}.json')
        C.guardar_json(destino, out)
        print(f'Resultados: {os.path.relpath(destino, C.RAIZ)}')
    if not args.nao_mostrar:
        plt.show()


if __name__ == '__main__':
    main()
