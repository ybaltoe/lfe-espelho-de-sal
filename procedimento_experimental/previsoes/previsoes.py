"""Previsões antes de medir: largura σ da bossa, desvio máximo no ecrã, aproximação de tanque fino,
tamanho de traço necessário e ângulo do espelho (em placas da rampa).

Uso:  python previsoes.py
      python previsoes.py --Z-calor 1500 --Tq 45 --sal-pct 3
Ver LEIA-ME.txt. Os valores de tabela são aproximados (comum.py).
"""
import os
import sys
import math
import argparse
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import comum as C  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'espelho_de_sal'))
from espelho import theta_de_dn, angulo_rampa  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
AZUL, LARANJA, VERDE, CINZA = '#2a78d6', '#eb6834', '#2e9e5b', '#777'


def tabela(nome, D, dn, Z, L, tempos_min, t0, n=1.333):
    Zef = Z + L / (2 * n)
    print(f"\n{nome}: D = {D:.2e} m²/s, Δn = {dn:.5f}, Z = {Z:.0f} mm, L = {L:.0f} mm (Z_ef = {Zef:.0f} mm), "
          f"t0 = {t0:.0f} s")
    print(f"{'t':>8} {'σ (mm)':>8} {'δ máx (mm)':>11} {'tanque fino':>12} {'traço ±3σ (mm)':>15}")
    linhas = []
    for tm in tempos_min:
        s = math.sqrt(2 * D * 1e6 * (tm * 60 + t0))
        A = Zef * L * dn / (s * math.sqrt(2 * math.pi))
        fino = L * A / (2 * n * Zef * s)
        print(f"{tm:6g} min {s:8.2f} {A:11.1f} {fino:12.3f}{' (!)' if fino > 0.2 else '':4} {6 * s:11.0f}")
        linhas.append((tm, s, A))
    print("   tanque fino = L·A/(2nZσ): tem de ser ≪ 1 (o código põe de parte fotos acima de 0,2).")
    print("   traço ±3σ: comprimento de altura no tanque que a folha tem de cobrir para o ajuste ter asas.")
    return linhas


def main():
    ap = argparse.ArgumentParser(description='Previsões do espelho de sal')
    ap.add_argument('--Tq', type=float, default=50.0, help='água quente (°C)')
    ap.add_argument('--Tf', type=float, default=20.0, help='água fria / sala (°C)')
    ap.add_argument('--sal-pct', type=float, default=5.0, help='sal em %% de massa')
    ap.add_argument('--Z-calor', type=float, default=2000.0)
    ap.add_argument('--L-calor', type=float, default=50.0)
    ap.add_argument('--Z-sal', type=float, default=1000.0)
    ap.add_argument('--L-sal', type=float, default=10.0)
    ap.add_argument('--t0-calor', type=float, default=0.0, help='t0 (s), atraso por o enchimento não ser instantâneo')
    ap.add_argument('--t0-sal', type=float, default=0.0)
    ap.add_argument('--placa', type=float, default=C.PLACA_MM)
    ap.add_argument('--base', type=float, default=32 * C.ESPIGA_MM)
    ap.add_argument('--nao-mostrar', action='store_true')
    args = ap.parse_args()
    if args.nao_mostrar:
        matplotlib.use('Agg')

    dn_calor = C.n_agua(args.Tf) - C.n_agua(args.Tq)
    kappa = C.kappa_agua((args.Tf + args.Tq) / 2)
    dn_sal = C.DN_DW_SAL * args.sal_pct
    D = C.D_sal(args.Tf)
    print('Valores de tabela APROXIMADOS (confirmar na bibliografia):')
    print(f"   n_água({args.Tf:.0f} °C) − n_água({args.Tq:.0f} °C) = {dn_calor:.5f};  κ({(args.Tf + args.Tq) / 2:.0f} °C) = {kappa:.2e} m²/s")
    print(f"   Δn do sal a {args.sal_pct:g} % = {dn_sal:.5f};  D_NaCl({args.Tf:.0f} °C) = {D:.2e} m²/s;  κ/D = {kappa / D:.0f}")

    lc = tabela('CALOR', kappa, dn_calor, args.Z_calor, args.L_calor, [0.5, 1, 2, 5, 10, 15], args.t0_calor)
    ls = tabela('SAL', D, dn_sal, args.Z_sal, args.L_sal, [5, 10, 20, 30, 45, 60, 90], args.t0_sal)

    print(f"\nESPELHO (rampa de {args.base:.0f} mm, placas de {args.placa} mm; tan θ = k·placa/base):")
    for nome, dn, T in (('sal', dn_sal, args.Tf), ('calor', dn_calor, args.Tq)):
        th, phi = theta_de_dn(dn, C.n_agua(T))
        k = math.tan(th) * args.base / args.placa
        k0 = math.floor(k)
        print(f"   {nome:<6} Δn = {dn:.5f}: φ_c = {math.degrees(phi):.2f}° na água, θ = {math.degrees(th):.2f}° no ar "
              f"-> entre {k0} placas ({math.degrees(angulo_rampa(k0, args.placa, args.base)):.2f}°) e "
              f"{k0 + 1} ({math.degrees(angulo_rampa(k0 + 1, args.placa, args.base)):.2f}°)  [k = {k:.2f}]")
    passo = math.degrees(angulo_rampa(13, args.placa, args.base) - angulo_rampa(12, args.placa, args.base))
    print(f"   cada placa ≈ {passo:.2f}° -> ± {passo / 2:.2f}°; em Δn ≈ ± {100 * passo / math.degrees(theta_de_dn(dn_sal, C.n_agua(args.Tf))[0]):.0f} % "
          "(Δn ∝ θ²)")

    # figura: o traço previsto no ecrã (calor) e σ²(t)
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.6))
    a = ax[0]
    y = np.linspace(-60, 60, 600)
    for (tm, s, A), c in zip([lc[1], lc[3], lc[5]], (AZUL, LARANJA, VERDE)):
        a.plot(y, -y - A * np.exp(-y ** 2 / (2 * s ** 2)), color=c, label=f't = {tm:g} min: σ = {s:.1f} mm, δ máx = {A:.0f} mm')
    a.plot(y, -y, '--', color=CINZA, label='referência (sem gradiente)')
    a.set_aspect('equal')
    a.set_xlabel('ecrã, horizontal (mm)')
    a.set_ylabel('ecrã, vertical (mm)')
    a.set_title(f'(a) calor: traço previsto no ecrã (Z = {args.Z_calor / 1000:g} m, L = {args.L_calor / 10:g} cm)')
    a.legend(fontsize=7, loc='lower left')
    a = ax[1]
    tc = np.linspace(0, 15, 100)
    a.plot(tc, 2 * kappa * 1e6 * (tc * 60 + args.t0_calor), color=LARANJA, label='calor (κ)')
    ts = np.linspace(0, 90, 100)
    a.plot(ts / 6, 2 * D * 1e6 * (ts * 60 + args.t0_sal), color=AZUL, label='sal (D), eixo do tempo ÷ 6')
    a.set_xlabel('t (min) [sal: t/6]')
    a.set_ylabel('σ² (mm²)')
    a.set_title('(b) σ² = 2D(t + t0): retas a medir')
    a.legend(fontsize=8)
    fig.tight_layout()
    C.virgulas(fig)
    nome = os.path.join(AQUI, 'previsoes.png')
    fig.savefig(nome, dpi=150)
    print(f'\nFigura: {os.path.basename(nome)}')
    if not args.nao_mostrar:
        plt.show()


if __name__ == '__main__':
    main()
