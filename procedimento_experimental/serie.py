"""Análise de uma série de fotos da bossa (montagem A), comum ao calor e ao sal.

Para cada ensaio (uma pasta em fotos/<tipo>/<ensaio>/):
  1. cada foto -> perfil δ(y) -> gaussiana: A, σ, área
  2. σ² contra t (reta ponderada): declive = 2D, t0 = ordenada/declive
  3. 1/A² contra t: também tem de ser reta (verificação independente)
  4. Δn = área / (Z_ef·L): constante no sal; no calor desce com as perdas
Depois junta os ensaios (média ponderada e dispersão entre ensaios) e escreve resultados_<tipo>.json.
"""
import os
import re
import csv
import math
import argparse
import datetime as dt
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

import comum as C

AZUL, LARANJA, VERDE, CINZA = '#2a78d6', '#eb6834', '#2e9e5b', '#777'

CONFIG = {
    'calor': dict(nome='calor', simbolo='κ', titulo='Calor: água quente sobre água fria',
                  pasta=os.path.join(C.PASTA_FOTOS, 'calor'), unidade_t='s'),
    'sal': dict(nome='sal', simbolo='D', titulo='Sal: água salgada sob água pura',
                pasta=os.path.join(C.PASTA_FOTOS, 'sal'), unidade_t='min'),
}


# ---------- Ler um ensaio ----------
def _hora(texto, data):
    m = re.fullmatch(r'(\d{1,2})[:h](\d{2})(?::(\d{2}))?', texto.strip())
    if not m:
        return None
    return dt.datetime.combine(data, dt.time(int(m[1]), int(m[2]), int(m[3] or 0)))


def fontes_ensaio(pasta):
    """Lista de fotos (ou perfis do plano B) de um ensaio, com o tempo em s desde t0."""
    reg = C.ler_registo(os.path.join(pasta, 'registo.txt'))
    excluir = {s.lower() for s in C.lista(reg, 'excluir')}
    fontes, fora = [], []

    f_perfis = os.path.join(pasta, 'perfis.csv')
    if os.path.exists(f_perfis):                       # plano B: δ medido ponto a ponto
        dados = {}
        with open(f_perfis, encoding='utf-8-sig') as f:
            txt = f.read()
        sep = ';' if ';' in txt.splitlines()[0] else ','
        for row in csv.DictReader(txt.splitlines(), delimiter=sep):
            t = float(row['t_s'].replace(',', '.'))
            dados.setdefault(t, []).append((float(row['y_mm'].replace(',', '.')),
                                            float(row['delta_mm'].replace(',', '.'))))
        for t in sorted(dados):
            y, d = np.array(dados[t]).T
            fontes.append(dict(nome=f't={t:g} s', t=t, perfil=(y, d)))
        return fontes, fora, reg

    imgs = sorted(f for f in os.listdir(pasta) if C.e_imagem(f)
                  and not f.lower().startswith(('referencia', 'pente')))
    tempos = {}
    f_tempos = os.path.join(pasta, 'tempos.csv')
    if os.path.exists(f_tempos):
        with open(f_tempos, encoding='utf-8-sig') as f:
            for linha in f:
                partes = [s.strip() for s in re.split(r'[;,\t]', linha) if s.strip()]
                if len(partes) >= 2 and C.e_imagem(partes[0]):
                    tempos[partes[0].lower()] = float(partes[1].replace(',', '.'))
    horas = {}
    if not tempos:
        for f in imgs:
            h = C.hora_foto(os.path.join(pasta, f))
            if h is None:
                raise SystemExit(f'{pasta}/{f}: a foto não tem hora (EXIF). Fazer tempos.csv '
                                 '(ficheiro;t_s), ver LEIA-ME.')
            horas[f] = h
        t0_txt = reg.get('t0', '')
        h0 = None
        if t0_txt:
            if t0_txt.lower() in {f.lower() for f in imgs}:
                h0 = horas[next(f for f in imgs if f.lower() == t0_txt.lower())]
            else:
                h0 = _hora(t0_txt, min(horas.values()).date())
                if h0 is None:
                    raise SystemExit(f'{pasta}: t0 = "{t0_txt}" não é uma hora (14:32:10) nem uma foto.')
        if h0 is None:
            h0 = min(horas.values())
            print(f'   (sem t0 no registo: t = 0 na primeira foto; o t0 do ajuste corrige isto)')
        for f in imgs:
            tempos[f.lower()] = (horas[f] - h0).total_seconds()
    for f in imgs:
        if f.lower() in excluir:
            fora.append((f, 'excluída no registo'))
            continue
        if f.lower() not in tempos:
            fora.append((f, 'sem tempo em tempos.csv'))
            continue
        caminho = os.path.join(pasta, f)
        fontes.append(dict(nome=f, t=tempos[f.lower()], caminho=caminho))
    fontes.sort(key=lambda s: s['t'])
    return fontes, fora, reg


# ---------- Analisar um ensaio ----------
def analisar_ensaio(nome, fontes, cal, reg, tipo, com_reta=False, lim_fino=0.2, carregar=None):
    pts = []
    for s in fontes:
        if 'perfil' in s:
            y, d = s['perfil']
        else:
            img = carregar(s) if carregar else C.ler_imagem(s['caminho'], cal['reduzir'])
            y, d, _ = C.perfil_bossa(img, cal)
        aj = C.ajustar_bossa(y, d, com_reta)
        p = dict(nome=s['nome'], t=s['t'], aj=aj, usar=False, motivo='')
        if aj is None:
            p['motivo'] = 'ajuste falhou'
        else:
            A = abs(aj['A'])
            p['fino'] = cal['L'] * A / (2 * cal['n_meio'] * cal['Z_ef'] * aj['s'])
            if aj['A'] < 0:
                p['motivo'] = 'bossa para cima (foto invertida?) '
            if aj['margem'] < 1.5:
                p['motivo'] += 'bossa cortada (pouca asa)'
            elif p['fino'] > lim_fino:
                p['motivo'] += f"tanque fino falha ({p['fino']:.2f} > {lim_fino})"
            elif aj['A'] >= 0:
                p['usar'] = True
        pts.append(p)

    bons = [p for p in pts if p['usar']]
    if len(bons) < 3:
        print(f'   {nome}: só {len(bons)} fotos utilizáveis; não dá para ajustar a reta.')
        return dict(nome=nome, pts=pts, ok=False)

    t = np.array([p['t'] for p in bons])
    s = np.array([p['aj']['s'] for p in bons])
    us = np.array([max(p['aj']['u_s'], 1e-4) for p in bons])
    A = np.array([p['aj']['A'] for p in bons])
    uA = np.array([max(p['aj']['u_A'], 1e-4) for p in bons])
    area = np.array([p['aj']['area'] for p in bons])
    uarea = np.array([max(p['aj']['u_area'], 1e-4) for p in bons])

    # σ² = 2D (t + t0)
    r = C.reta_ponderada(t, s ** 2, 2 * s * us)
    D = r['a'] / 2 * 1e-6                                   # mm²/s -> m²/s
    uD_aj = math.sqrt(r['cov'][0, 0]) / 2 * 1e-6
    t0 = r['b'] / r['a']
    g = np.array([-r['b'] / r['a'] ** 2, 1 / r['a']])
    ut0 = float(math.sqrt(g @ r['cov'] @ g))
    uD_esc = D * 2 * cal['u_m'] / cal['m']                 # σ ∝ 1/m, D ∝ 1/m²

    # Δn pela área
    ZL = cal['Z_ef'] * cal['L']
    dn = area / ZL
    udn = uarea / ZL
    rdn = C.reta_ponderada(t, dn, udn)

    # 1/A² = (2π·2D/(Z L Δn)²)·(t + t0): outra reta, outro t0. No calor o Δn desce (perdas) e A desce
    # com ele; corrige-se A pela reta do Δn (não pela área de cada foto, para não reutilizar o σ).
    if tipo == 'calor' and rdn['b'] > 0:
        fator = (rdn['a'] * t + rdn['b']) / rdn['b']
        A, uA = A / fator, uA / fator
    rA = C.reta_ponderada(t, 1 / A ** 2, 2 * uA / A ** 3)
    t0_A = rA['b'] / rA['a'] if rA['a'] != 0 else float('nan')
    if tipo == 'calor':           # perdas: Δn desce; o valor do ensaio é o do início (t = 0)
        Dn, uDn_aj = rdn['b'], math.sqrt(rdn['cov'][1, 1])
    else:
        Dn, uDn_aj = C.media_ponderada(dn, udn)
        uDn_aj = max(uDn_aj, float(np.std(dn, ddof=1) / math.sqrt(len(dn))))
    queda_pct_min = 100 * rdn['a'] * 60 / Dn if Dn else float('nan')
    rel_esc = math.hypot(cal['u_m'] / cal['m'], cal['u_p'] / cal['p'])
    uDn_Z = Dn * cal['u_Z'] / cal['Z_ef']
    uDn_L = Dn * cal['u_L'] / cal['L']
    uDn_esc = Dn * rel_esc

    return dict(nome=nome, ok=True, pts=pts, n=len(bons), t=t, s=s, us=us, A=A, uA=uA, dn=dn, udn=udn,
                ajuste=r, ajuste_A=rA, ajuste_dn=rdn,
                D=D, uD_aj=uD_aj, uD_esc=uD_esc, t0=t0, ut0=ut0, t0_A=t0_A,
                Dn=Dn, uDn_aj=uDn_aj, uDn_Z=uDn_Z, uDn_L=uDn_L, uDn_esc=uDn_esc,
                queda_pct_min=queda_pct_min, reg=reg, cal=cal['nome'])


def referencias(tipo, reg):
    """Valores de tabela para comparar (aproximados)."""
    if tipo == 'calor':
        Tc, Tb = C.num(reg, 't_cima'), C.num(reg, 't_baixo')
        if Tc is None or Tb is None:
            return dict(D=C.kappa_agua(25), Dn=None, texto='sem T_cima/T_baixo no registo: κ a 25 °C')
        return dict(D=C.kappa_agua((Tc + Tb) / 2), Dn=C.n_agua(Tb) - C.n_agua(Tc),
                    texto=f'T_cima = {Tc:.1f} °C, T_baixo = {Tb:.1f} °C')
    w = C.fracao_sal(reg)
    T = C.num(reg, 't', C.num(reg, 't_baixo', 22.0))
    return dict(D=C.D_sal(T), Dn=C.DN_DW_SAL * w if w is not None else None,
                texto=f'T = {T:.1f} °C' + (f', sal a {w:.2f} % (massa)' if w is not None else ', sem sal_g/agua_g'))


# ---------- Escrever ----------
def imprimir_ensaio(R, tipo):
    simb = CONFIG[tipo]['simbolo']
    for p in R['pts']:
        aj = p['aj']
        if aj is None:
            print(f"      {p['nome']:<22} t = {p['t']:7.0f} s   ajuste falhou")
            continue
        print(f"      {p['nome']:<22} t = {p['t']:7.0f} s   σ = {aj['s']:6.2f} ± {aj['u_s']:.2f} mm   "
              f"A = {aj['A']:6.2f} mm   área = {aj['area']:7.2f}   "
              f"fino = {p.get('fino', float('nan')):.3f}   {'' if p['usar'] else 'FORA: ' + p['motivo']}")
    if not R['ok']:
        return
    r = R['ajuste']
    print(f"   {simb} = {R['D']:.3e} ± {R['uD_aj']:.1e} (ajuste) ± {R['uD_esc']:.1e} (escala m) m²/s   "
          f"[{R['n']} fotos, χ²/ν = {r['chi2nu']:.2f}]")
    print(f"   t0 = {R['t0']:.0f} ± {R['ut0']:.0f} s pelo σ²;  {R['t0_A']:.0f} s pelo 1/A²  "
          "(têm de ser parecidos; t0 grande = fronteira misturada no enchimento)")
    lab = 'Δn(t = 0)' if tipo == 'calor' else 'Δn (média)'
    print(f"   {lab} = {R['Dn']:.5f} ± {R['uDn_aj']:.5f} (ajuste) ± {R['uDn_Z']:.5f} (Z) "
          f"± {R['uDn_L']:.5f} (L) ± {R['uDn_esc']:.5f} (escalas)")
    print(f"   Δn varia {R['queda_pct_min']:+.2f} %/min" +
          ('  (perdas de calor)' if tipo == 'calor' else '  (no sal devia ser ~0)'))


def figura_ensaio(R, tipo, nome_fig, mostrar_t='s'):
    fig, ax = plt.subplots(2, 2, figsize=(12, 8.5))
    fs = 60 if mostrar_t == 'min' else 1
    ut = 'min' if mostrar_t == 'min' else 's'
    # (a) três perfis
    a = ax[0, 0]
    bons = [p for p in R['pts'] if p['usar']]
    esc = [bons[0], bons[len(bons) // 2], bons[-1]] if len(bons) >= 3 else bons
    for p, c in zip(esc, (AZUL, LARANJA, VERDE)):
        aj = p['aj']
        a.plot(aj['y'], aj['d'], '.', ms=2, color=c, alpha=0.5)
        yy = np.linspace(aj['y'][0], aj['y'][-1], 400)
        a.plot(yy, aj['f'](yy, *aj['p']), color=c, lw=1.5,
               label=f"t = {p['t'] / fs:.1f} {ut}: σ = {aj['s']:.2f} mm")
    a.set_xlabel('altura no tanque y (mm)')
    a.set_ylabel('desvio no ecrã δ (mm)')
    a.set_title('(a) bossa e ajuste gaussiano')
    a.legend(fontsize=8)
    # (b) σ² vs t
    a = ax[0, 1]
    t, s, us = R['t'], R['s'], R['us']
    r = R['ajuste']
    a.errorbar(t / fs, s ** 2, yerr=2 * s * us, fmt='o', ms=4, color=AZUL, label='fotos usadas')
    fora = [p for p in R['pts'] if not p['usar'] and p['aj'] is not None]
    if fora:
        a.plot([p['t'] / fs for p in fora], [p['aj']['s'] ** 2 for p in fora], 'x', color=CINZA,
               label='fotos fora')
    tt = np.linspace(min(0, t.min()), t.max(), 100)
    a.plot(tt / fs, r['a'] * tt + r['b'], color=LARANJA,
           label=f"{CONFIG[tipo]['simbolo']} = {R['D']:.3e} m²/s")
    a.set_xlabel(f't ({ut})')
    a.set_ylabel('σ² (mm²)')
    a.set_title(f"(b) σ² = 2{CONFIG[tipo]['simbolo']}(t + t0),  t0 = {R['t0']:.0f} s")
    a.legend(fontsize=8)
    ins = a.inset_axes([0.58, 0.08, 0.38, 0.25])
    ins.axhline(0, color=CINZA, lw=0.8)
    ins.plot(t / fs, r['res'], 'o', ms=2.5, color=AZUL)
    ins.set_title('resíduos (mm²)', fontsize=7)
    ins.tick_params(labelsize=6)
    # (c) Δn(t)
    a = ax[1, 0]
    a.errorbar(t / fs, R['dn'] * 1e3, yerr=R['udn'] * 1e3, fmt='o', ms=4, color=VERDE)
    rd = R['ajuste_dn']
    a.plot(tt / fs, (rd['a'] * tt + rd['b']) * 1e3, color=CINZA, lw=1)
    a.set_xlabel(f't ({ut})')
    a.set_ylabel('Δn = área/(Z·L)  (×10⁻³)')
    a.set_title(f"(c) Δn pela área: {R['queda_pct_min']:+.2f} %/min")
    # (d) 1/A²
    a = ax[1, 1]
    rA = R['ajuste_A']
    a.errorbar(t / fs, 1 / R['A'] ** 2, yerr=2 * R['uA'] / R['A'] ** 3, fmt='o', ms=4, color=LARANJA)
    a.plot(tt / fs, rA['a'] * tt + rA['b'], color=CINZA, lw=1)
    a.set_xlabel(f't ({ut})')
    a.set_ylabel('1/A² (mm⁻²)' + (', A corrigido das perdas' if tipo == 'calor' else ''))
    a.set_title(f"(d) verificação: 1/A² também é reta (t0 = {R['t0_A']:.0f} s)")
    fig.suptitle(f"{CONFIG[tipo]['titulo']} · ensaio {R['nome']} (calibração {R['cal']})")
    fig.tight_layout()
    C.virgulas(fig)
    fig.savefig(nome_fig, dpi=150)
    print(f'   Figura: {os.path.basename(nome_fig)}')


def guardar_csv(R, caminho):
    with open(caminho, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['foto', 't_s', 'sigma_mm', 'u_sigma_mm', 'A_mm', 'u_A_mm', 'yc_mm', 'area_mm2',
                    'u_area_mm2', 'tanque_fino', 'usada', 'motivo'])
        for p in R['pts']:
            aj = p['aj'] or {}
            w.writerow([p['nome'], f"{p['t']:.1f}"] +
                       [f"{aj[k]:.4f}" if aj else '' for k in ('s', 'u_s', 'A', 'u_A', 'yc', 'area', 'u_area')] +
                       [f"{p.get('fino', float('nan')):.4f}", 'sim' if p['usar'] else 'não', p['motivo']])


def combinar(ens, tipo, saida_json):
    ok = [R for R in ens if R['ok']]
    if not ok:
        print('\nNenhum ensaio com ajuste.')
        return None
    simb = CONFIG[tipo]['simbolo']
    D = np.array([R['D'] for R in ok])
    uD = np.array([R['uD_aj'] for R in ok])
    Dm, uDm = C.media_ponderada(D, uD)
    u_rep = float(np.std(D, ddof=1) / math.sqrt(len(D))) if len(D) > 1 else float('nan')
    u_A = max(uDm, u_rep) if len(D) > 1 else uDm
    u_esc = float(np.mean([R['uD_esc'] / R['D'] for R in ok])) * Dm
    uD_tot = math.hypot(u_A, u_esc)

    Dn = np.array([R['Dn'] for R in ok])
    uDn = np.array([R['uDn_aj'] for R in ok])
    Dnm, uDnm = C.media_ponderada(Dn, uDn)
    u_rep_dn = float(np.std(Dn, ddof=1) / math.sqrt(len(Dn))) if len(Dn) > 1 else float('nan')
    uA_dn = max(uDnm, u_rep_dn) if len(Dn) > 1 else uDnm
    rel = lambda k: float(np.mean([R[k] / R['Dn'] for R in ok]))
    uDn_Z, uDn_L, uDn_esc = rel('uDn_Z') * Dnm, rel('uDn_L') * Dnm, rel('uDn_esc') * Dnm
    uDn_tot = math.sqrt(uA_dn ** 2 + uDn_Z ** 2 + uDn_L ** 2 + uDn_esc ** 2)

    refs = [referencias(tipo, R['reg']) for R in ok]
    D_ref = float(np.mean([r['D'] for r in refs]))
    dn_refs = [r['Dn'] for r in refs if r['Dn'] is not None]
    Dn_ref = float(np.mean(dn_refs)) if dn_refs else None

    print(f"\n===== {CONFIG[tipo]['titulo']}: {len(ok)} ensaio(s) =====")
    for R, rf in zip(ok, refs):
        print(f"   {R['nome']:<14} {simb} = {R['D']:.3e} ± {R['uD_aj']:.1e}   Δn = {R['Dn']:.5f} ± "
              f"{R['uDn_aj']:.5f}   t0 = {R['t0']:.0f} s   ({rf['texto']})")
    print(f"\n{simb} = {Dm:.3e} ± {uD_tot:.1e} m²/s")
    print(f"   ajuste (média ponderada) ± {uDm:.1e}; entre ensaios ± {u_rep:.1e}; escala do pente ± {u_esc:.1e}")
    print(f"   tabela ≈ {D_ref:.2e} m²/s  ->  z = {C.z_score(Dm, uD_tot, D_ref):+.1f} "
          "(tabela aproximada: confirmar o valor e a temperatura)")
    print(f"Δn = {Dnm:.5f} ± {uDn_tot:.5f}")
    print(f"   ajuste/entre ensaios ± {uA_dn:.5f}; Z ± {uDn_Z:.5f}; L ± {uDn_L:.5f}; escalas ± {uDn_esc:.5f}")
    if Dn_ref is not None:
        print(f"   tabela ≈ {Dn_ref:.5f}  ->  z = {C.z_score(Dnm, uDn_tot, Dn_ref):+.1f}")

    res = dict(tipo=tipo, n_ensaios=len(ok), D=Dm, u_D=uD_tot, u_D_ajuste=uDm, u_D_entre=u_rep,
               u_D_escala=u_esc, D_ref=D_ref, Dn=Dnm, u_Dn=uDn_tot, u_Dn_ajuste=uA_dn, u_Dn_Z=uDn_Z,
               u_Dn_L=uDn_L, u_Dn_escalas=uDn_esc, Dn_ref=Dn_ref,
               ensaios=[dict(nome=R['nome'], calibracao=R['cal'], D=R['D'], u_D=R['uD_aj'], t0=R['t0'],
                             u_t0=R['ut0'], t0_A=R['t0_A'], Dn=R['Dn'], u_Dn=R['uDn_aj'],
                             queda_pct_min=R['queda_pct_min'], chi2nu=R['ajuste']['chi2nu'], n_fotos=R['n'],
                             T=refs[i]['texto'])
                        for i, R in enumerate(ok)])
    if saida_json:
        C.guardar_json(saida_json, res)
        print(f'\nResultados: {os.path.relpath(saida_json, C.RAIZ)}')
    return res


def figura_resumo(ens, tipo, res, nome_fig):
    ok = [R for R in ens if R['ok']]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(ok))
    ax[0].errorbar(x, [R['D'] for R in ok], yerr=[R['uD_aj'] for R in ok], fmt='o', color=AZUL)
    ax[0].axhspan(res['D'] - res['u_D'], res['D'] + res['u_D'], color=AZUL, alpha=0.15, label='média ± u')
    ax[0].axhline(res['D_ref'], color=CINZA, ls='--', label='tabela (aprox.)')
    ax[0].set_ylabel(f"{CONFIG[tipo]['simbolo']} (m²/s)")
    ax[1].errorbar(x, [R['Dn'] for R in ok], yerr=[R['uDn_aj'] for R in ok], fmt='o', color=VERDE)
    ax[1].axhspan(res['Dn'] - res['u_Dn'], res['Dn'] + res['u_Dn'], color=VERDE, alpha=0.15)
    if res['Dn_ref']:
        ax[1].axhline(res['Dn_ref'], color=CINZA, ls='--')
    ax[1].set_ylabel('Δn (área)')
    for a in ax:
        a.set_xticks(x, [R['nome'] for R in ok], rotation=30, fontsize=8)
    ax[0].legend(fontsize=8)
    fig.suptitle(f"{CONFIG[tipo]['titulo']}: todos os ensaios")
    fig.tight_layout()
    C.virgulas(fig)
    fig.savefig(nome_fig, dpi=150)
    print(f'Figura: {os.path.basename(nome_fig)}')


# ---------- Teste com fotos sintéticas ----------
def ensaios_sinteticos(tipo):
    rng = np.random.default_rng(7)
    if tipo == 'calor':
        Z, L, Dv, dn0, perda = 2000.0, 50.0, 1.4e-7, 0.0035, 0.01     # perda: 1 %/min
        tempos = np.arange(30, 901, 30.0)
        t0s = (40.0, 70.0)
    else:
        Z, L, Dv, dn0, perda = 1000.0, 10.0, 1.5e-9, 0.009, 0.0
        tempos = np.arange(300, 3601, 300.0)
        t0s = (200.0, 400.0)
    cal = C.calibracao_sintetica(Z=Z, L=L, rng=rng)
    Dmm = Dv * 1e6
    ens = []
    for i, t0 in enumerate(t0s):
        fontes = []
        for t in tempos:
            s = math.sqrt(2 * Dmm * (t + t0))
            dn = dn0 * (1 - perda * t / 60)
            A = cal['Z_ef'] * L * dn / (s * math.sqrt(2 * math.pi))
            yc = 60 + rng.normal(0, 0.3)
            ond = rng.normal(0, 0.15, 6)
            f = (lambda y, A=A, s=s, yc=yc, ond=ond:
                 A * np.exp(-(y - yc) ** 2 / (2 * s ** 2)) + 0.3 * np.sin(y / 7 + ond[0]) * ond[1])
            fontes.append(dict(nome=f'sint_{int(t)}s', t=float(t), f=f))
        ens.append((f'teste_{i + 1}', fontes))
    verdade = dict(D=Dv, Dn=dn0, t0s=t0s)
    return cal, ens, verdade


# ---------- Programa ----------
def principal(tipo):
    cfg = CONFIG[tipo]
    pasta_script = os.path.join(C.PASTA_PE, tipo)
    ap = argparse.ArgumentParser(description=f"{cfg['titulo']}: {cfg['simbolo']} e Δn pela bossa")
    ap.add_argument('--ensaio', action='append', help='só este ensaio (pasta em fotos/%s/); pode repetir' % tipo)
    ap.add_argument('--pasta', default=cfg['pasta'], help='pasta com as pastas dos ensaios')
    ap.add_argument('--reta', action='store_true', help='ajusta também uma reta de fundo (se a referência mexeu)')
    ap.add_argument('--lim-fino', type=float, default=0.2,
                    help='tira fotos com L·A/(2nZσ) acima disto (aproximação de tanque fino), por omissão 0,2')
    ap.add_argument('--teste', action='store_true', help='corre com fotos sintéticas de valores conhecidos')
    ap.add_argument('--nao-mostrar', action='store_true', help='só guarda as figuras')
    args = ap.parse_args()
    if args.nao_mostrar:
        matplotlib.use('Agg')

    resultados = []
    if args.teste:
        cal, ens, verdade = ensaios_sinteticos(tipo)
        print(f"TESTE com fotos sintéticas: {cfg['simbolo']} = {verdade['D']:.2e} m²/s, Δn = {verdade['Dn']}, "
              f"t0 = {verdade['t0s']} s")
        print('\n'.join('   ' + l for l in C.resumo_calibracao(cal)))
        for nome, fontes in ens:
            print(f'\n{nome}: {len(fontes)} fotos')
            R = analisar_ensaio(nome, fontes, cal, {}, tipo, args.reta, args.lim_fino,
                                carregar=lambda s: C.imagem_sintetica(delta_mm=s['f'],
                                                                      rng=np.random.default_rng(int(s['t']))))
            imprimir_ensaio(R, tipo)
            if R['ok']:
                figura_ensaio(R, tipo, os.path.join(pasta_script, f'{tipo}_{nome}.png'), cfg['unidade_t'])
            resultados.append(R)
        res = combinar(resultados, tipo, None)
        print(f"\nTESTE: recuperado {cfg['simbolo']} = {res['D']:.3e} (verdadeiro {verdade['D']:.3e}), "
              f"Δn = {res['Dn']:.5f} (verdadeiro {verdade['Dn']}), "
              f"t0 = {[round(R['t0']) for R in resultados]} (verdadeiro {list(verdade['t0s'])})")
        if not args.nao_mostrar:
            plt.show()
        return

    if not os.path.isdir(args.pasta):
        raise SystemExit(f'Não existe {args.pasta}')
    nomes = args.ensaio or sorted(d for d in os.listdir(args.pasta)
                                  if os.path.isdir(os.path.join(args.pasta, d)) and not d.startswith('_'))
    if not nomes:
        raise SystemExit(f'Não há ensaios em {args.pasta} (uma pasta por ensaio; ver fotos/README.md).')
    for nome in nomes:
        pasta = os.path.join(args.pasta, nome)
        fontes, fora, reg = fontes_ensaio(pasta)
        print(f'\n{nome}: {len(fontes)} fotos' + (f', {len(fora)} postas de parte' if fora else ''))
        for f, mot in fora:
            print(f'      {f}: {mot}')
        if 'calibracao' not in reg and not any('perfil' in s for s in fontes):
            raise SystemExit(f'{pasta}/registo.txt: falta "calibracao = <pasta em fotos/calibracao/>"')
        if any('perfil' in s for s in fontes):        # plano B: as unidades já vêm em mm
            cal = dict(nome='plano B', m=1.0, u_m=0.0, p=1.0, u_p=0.0,
                       Z=C.num(reg, 'z_mm'), u_Z=C.num(reg, 'u_z_mm', 3.0), L=C.num(reg, 'l_mm'),
                       u_L=C.num(reg, 'u_l_mm', 0.05), n_meio=C.num(reg, 'n_meio', 1.333))
            if cal['Z'] is None or cal['L'] is None:
                raise SystemExit(f'{pasta}/registo.txt: no plano B o registo do ensaio tem de ter Z_mm e L_mm')
            cal['Z_ef'] = cal['Z'] + cal['L'] / (2 * cal['n_meio'])
            cal['u_m'] = C.num(reg, 'u_escala_rel', 0.01)    # régua da plataforma
        else:
            cal = C.carregar_calibracao(reg['calibracao'])
            print(f"   calibração {cal['nome']}:")
            print('\n'.join('      ' + l for l in C.resumo_calibracao(cal)))
        R = analisar_ensaio(nome, fontes, cal, reg, tipo, args.reta, args.lim_fino)
        imprimir_ensaio(R, tipo)
        guardar_csv(R, os.path.join(pasta_script, f'{tipo}_{nome}.csv'))
        if R['ok']:
            figura_ensaio(R, tipo, os.path.join(pasta_script, f'{tipo}_{nome}.png'), cfg['unidade_t'])
        resultados.append(R)
    res = combinar(resultados, tipo, os.path.join(pasta_script, f'resultados_{tipo}.json'))
    if res and res['n_ensaios'] > 1:
        figura_resumo(resultados, tipo, res, os.path.join(pasta_script, f'{tipo}_resumo.png'))
    if not args.nao_mostrar:
        plt.show()
