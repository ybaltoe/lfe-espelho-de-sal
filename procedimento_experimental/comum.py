"""Funções comuns do espelho de sal: ler fotos e registos, extrair o traço do laser, calibrar com o
pente LEGO e a grelha do papel milimétrico, ajustar a bossa, ajustar retas e gerar fotos sintéticas
para os testes.

Convenções (iguais em todos os scripts):
  x, linha   píxeis da foto (x para a direita, linha para baixo)
  y          altura no tanque (mm), medida ao longo do traço; origem na primeira sombra do pente
  δ          desvio do traço no ecrã (mm do ecrã), positivo para baixo (para o lado de n maior)
  m          escala do pente: píxeis por mm de altura no tanque
  p          escala do ecrã: píxeis por mm de papel milimétrico
"""
import os
import re
import sys
import json
import math
import datetime as dt
import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.optimize import curve_fit
from scipy.signal import find_peaks

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

PASTA_PE = os.path.dirname(os.path.abspath(__file__))           # procedimento_experimental/
RAIZ = os.path.dirname(PASTA_PE)
PASTA_FOTOS = os.path.join(RAIZ, 'fotos')
EXT_IMAGEM = ('.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.heif')

# ---------- LEGO (nominal; confirmar com paquímetro: 10 placas empilhadas / 10) ----------
PLACA_MM = 3.2
ESPIGA_MM = 8.0
PASSO_PENTE_MM = 2 * PLACA_MM     # uma sombra a cada duas placas (1×4 que sobressai, 1×2 recuada)

# ---------- Valores de tabela (APROXIMADOS: confirmar na bibliografia antes do relatório) ----------
# Índice da água a 589 nm (tabelas usuais). A 633 nm (He-Ne) é ~0,0019 menor, mas as diferenças entre
# temperaturas, que são o que conta aqui, quase não mudam.
_T_N = np.array([10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60], float)
_N_AGUA = np.array([1.33369, 1.33339, 1.33299, 1.33250, 1.33194, 1.33131,
                    1.33061, 1.32985, 1.32904, 1.32817, 1.32725])
# Difusividade térmica da água, κ = k/(ρ c_p) (m²/s)
_T_K = np.array([10, 20, 30, 40, 50, 60], float)
_KAPPA = np.array([1.39e-7, 1.43e-7, 1.48e-7, 1.52e-7, 1.56e-7, 1.59e-7])
# Viscosidade da água (mPa·s), para corrigir D do sal com a temperatura (Stokes-Einstein, D ∝ T/η)
_T_ETA = np.array([10, 15, 20, 25, 30, 35, 40], float)
_ETA = np.array([1.306, 1.138, 1.002, 0.890, 0.797, 0.719, 0.653])
D_SAL_25 = 1.48e-9        # NaCl em água a 25 °C, ~1 mol/L (m²/s)
DN_DW_SAL = 1.76e-3       # aumento do índice por cada 1 % (massa) de NaCl
N_AGUA_633_DESVIO = -0.0019


def n_agua(T):
    """Índice da água pura a T (°C), 633 nm (aproximado)."""
    return float(np.interp(T, _T_N, _N_AGUA)) + N_AGUA_633_DESVIO


def kappa_agua(T):
    return float(np.interp(T, _T_K, _KAPPA))


def D_sal(T):
    """D do NaCl a T (°C), corrigido de 25 °C com D ∝ T/η."""
    eta = np.interp(T, _T_ETA, _ETA)
    return D_SAL_25 * (T + 273.15) / 298.15 * 0.890 / eta


def fracao_sal(reg):
    """Percentagem em massa de sal a partir do registo (sal_g, agua_g) ou de sal_pct."""
    if 'sal_pct' in reg:
        return num(reg, 'sal_pct')
    s, a = num(reg, 'sal_g'), num(reg, 'agua_g')
    if s is None or a is None:
        return None
    return 100 * s / (s + a)


# ---------- Registos ----------
def ler_registo(caminho):
    """Ficheiro 'chave = valor', uma por linha; '#' começa um comentário. Chaves em minúsculas."""
    d = {}
    if not os.path.exists(caminho):
        return d
    with open(caminho, encoding='utf-8-sig') as f:
        for linha in f:
            linha = linha.split('#', 1)[0].strip()
            if '=' in linha:
                k, v = linha.split('=', 1)
                d[k.strip().lower()] = v.strip()
    return d


def num(reg, chave, padrao=None):
    """Número do registo; aceita vírgula decimal."""
    v = reg.get(chave)
    if v is None or v == '':
        return padrao
    return float(v.replace(',', '.'))


def lista(reg, chave):
    v = reg.get(chave, '')
    return [s.strip() for s in re.split(r'[;,]', v) if s.strip()]


# ---------- Imagens ----------
_HEIC = None


def _registar_heic():
    global _HEIC
    if _HEIC is None:
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            _HEIC = True
        except ImportError:
            _HEIC = False


def e_imagem(nome):
    return nome.lower().endswith(EXT_IMAGEM)


def tamanho_imagem(caminho):
    from PIL import Image, ImageOps
    _registar_heic()
    with Image.open(caminho) as im:
        return ImageOps.exif_transpose(im).size


def ler_imagem(caminho, reduzir=1):
    """RGB em [0, 1] (float32), já rodada como o telemóvel a mostra, reduzida por um fator inteiro."""
    from PIL import Image, ImageOps
    _registar_heic()
    if caminho.lower().endswith(('.heic', '.heif')) and not _HEIC:
        raise SystemExit(f'{caminho}: fotos HEIC precisam de "pip install pillow-heif" '
                         '(ou pôr o iPhone a tirar JPG: Definições > Câmara > Formatos > Mais compatível)')
    with Image.open(caminho) as im:
        im = ImageOps.exif_transpose(im).convert('RGB')
        if reduzir > 1:
            im = im.reduce(reduzir)
        return np.asarray(im, dtype=np.float32) / 255.0


def hora_foto(caminho):
    """Hora a que a foto foi tirada (EXIF DateTimeOriginal), ou None."""
    from PIL import Image
    _registar_heic()
    try:
        with Image.open(caminho) as im:
            ex = im.getexif()
            s = ex.get_ifd(0x8769).get(36867) or ex.get(306)
    except Exception:
        return None
    if not s:
        return None
    try:
        return dt.datetime.strptime(str(s).strip('\x00 '), '%Y:%m:%d %H:%M:%S')
    except ValueError:
        return None


def fator_reducao(caminho, max_lado=2000):
    """Fator inteiro para a foto ficar com o lado maior ≤ max_lado píxeis (mais rápido, quase sem perda:
    o centro do traço é calculado com precisão sub-píxel)."""
    w, h = tamanho_imagem(caminho)
    return max(1, int(math.ceil(max(w, h) / max_lado)))


# ---------- Traço do laser ----------
def mapa_vermelho(img):
    """Quanto cada píxel é 'vermelho de laser': R − max(G, B), sem o fundo.
    Tira-se a mediana de cada linha e de cada coluna: as linhas do papel milimétrico (mesmo cor de
    laranja) ocupam linhas e colunas inteiras e desaparecem; o traço do laser é diagonal e fica."""
    r = img[..., 0] - np.maximum(img[..., 1], img[..., 2])
    r = r - np.median(r, axis=1, keepdims=True)
    r = r - np.median(r, axis=0, keepdims=True)
    return np.clip(r, 0, None)


def extrair_traco(img, recorte=None, limiar=0.35):
    """Em cada coluna, a linha (sub-píxel) onde está o traço: centroide do vermelho à volta do máximo.
    recorte = (x0, x1, y0, y1) em píxeis desta imagem: fora dele ignora-se tudo.
    Devolve dict com x, linha (NaN onde não há traço), pico, valido, fwhm (px) e frac_saturado."""
    r = mapa_vermelho(img)
    if recorte is not None:
        x0, x1, y0, y1 = [int(v) for v in recorte]
        mask = np.zeros_like(r, bool)
        mask[max(y0, 0):y1, max(x0, 0):x1] = True
        r = np.where(mask, r, 0)
    r = gaussian_filter1d(r, 1.0, axis=0)
    H, W = r.shape
    cols = np.arange(W)
    i = np.argmax(r, axis=0)
    pico = r[i, cols]
    ref = np.percentile(pico, 95)
    valido = pico > limiar * ref if ref > 0 else np.zeros(W, bool)

    # largura do traço (FWHM, px) para escolher a janela do centroide
    j = np.arange(-40, 41)
    linhas = np.clip(i[None, :] + j[:, None], 0, H - 1)
    perf = r[linhas, cols]
    acima = (perf > 0.5 * pico[None, :]).sum(axis=0)
    fwhm = float(np.median(acima[valido])) if valido.any() else 5.0
    w = int(max(4, round(1.5 * fwhm)))

    j = np.arange(-w, w + 1)
    linhas = np.clip(i[None, :] + j[:, None], 0, H - 1)
    perf = r[linhas, cols]
    peso = np.clip(perf - 0.2 * pico[None, :], 0, None)
    soma = peso.sum(axis=0)
    linha = np.where(soma > 0, (peso * linhas).sum(axis=0) / np.where(soma > 0, soma, 1), np.nan)
    linha[~valido] = np.nan

    # traço "branco" (sobre-exposto): o centro fica R = G = B e deixa de ser vermelho
    g_pico = img[np.clip(np.round(np.nan_to_num(linha)).astype(int), 0, H - 1), cols, 1]
    frac_sat = float(np.mean(g_pico[valido] > 0.95)) if valido.any() else 0.0
    return dict(x=cols.astype(float), linha=linha, pico=pico, valido=valido, fwhm=fwhm,
                frac_saturado=frac_sat)


# ---------- Escala do ecrã: grelha do papel milimétrico ----------
def _periodo_autocorr(perfis):
    """Período (px) comum a vários perfis 1D: média das autocorrelações, primeiro pico, afinado pelos
    múltiplos (o pico k está em k·P)."""
    acs = []
    for p in perfis:
        p = p - gaussian_filter1d(p, 40)
        n = len(p)
        if np.std(p) == 0:
            continue
        f = np.fft.rfft(p, 2 * n)
        ac = np.fft.irfft(f * np.conj(f))[:n]
        acs.append(ac / ac[0])
    if not acs:
        return None
    ac = np.mean(acs, axis=0)
    n = len(ac)
    pk, _ = find_peaks(ac[:n // 3], prominence=0.03)
    pk = pk[pk >= 3]
    if len(pk) == 0:
        return None
    P = float(pk[0])
    ks, lags = [], []
    for k in range(1, 60):
        c = k * P
        if c > n // 3 - 3:
            break
        a, b = int(c - max(1, P / 4)), int(c + max(1, P / 4)) + 1
        jj = a + int(np.argmax(ac[a:b]))
        if 0 < jj < n - 1:
            y0, y1, y2 = ac[jj - 1], ac[jj], ac[jj + 1]
            den = y0 - 2 * y1 + y2
            jj = jj + (0.5 * (y0 - y2) / den if den != 0 else 0)
        ks.append(k)
        lags.append(jj)
        P = lags[-1] / k
    ks, lags = np.array(ks, float), np.array(lags)
    if len(ks) >= 3:
        P = float(np.sum(ks * lags) / np.sum(ks * ks))
        res = lags - P * ks
        uP = float(np.sqrt(np.sum(res ** 2) / (len(ks) - 1) / np.sum(ks * ks)))
    else:
        uP = P * 0.02
    return dict(P=P, uP=uP, ac=ac, ks=ks, lags=lags)


def escala_grelha(img, faixa=150):
    """Píxeis por mm do papel milimétrico, pelas linhas horizontais e verticais da grelha.
    Usa faixas estreitas (para a grelha poder estar ligeiramente rodada) e a mediana em cada faixa
    (para o traço do laser não contar)."""
    L = img.mean(axis=2)
    H, W = L.shape
    hor = [np.median(L[:, a:a + faixa], axis=1) for a in range(0, W - faixa + 1, faixa)]
    ver = [np.median(L[a:a + faixa, :], axis=0) for a in range(0, H - faixa + 1, faixa)]
    rh, rv = _periodo_autocorr(hor), _periodo_autocorr(ver)
    vals = [r for r in (rh, rv) if r is not None]
    if not vals:
        return None
    P = float(np.mean([r['P'] for r in vals]))
    u = float(np.sqrt(np.mean([r['uP'] ** 2 for r in vals])))
    if len(vals) == 2:
        u = max(u, abs(rh['P'] - rv['P']) / 2)
    return dict(p=P, u_p=u, linhas=rh, colunas=rv)


# ---------- Pente LEGO ----------
def sombras_pente(tr, passo_mm=PASSO_PENTE_MM):
    """Centros (px, ao longo de x) das sombras do pente no traço, e a reta x = x0 + m·y.
    Devolve m (px por mm de altura no tanque), u_m, x0 e os pontos usados."""
    I = gaussian_filter1d(tr['pico'], 1.0)
    aceso = I > 0.5 * np.percentile(I, 90)
    idx = np.flatnonzero(aceso)
    if len(idx) < 10:
        return None
    a, b = idx[0], idx[-1]
    escuro = ~aceso[a:b + 1]
    runs, ini = [], None
    for k, e in enumerate(escuro):
        if e and ini is None:
            ini = k
        if (not e or k == len(escuro) - 1) and ini is not None:
            fim = k if e else k - 1
            runs.append((a + ini, a + fim))
            ini = None
    centros = np.array([(r0 + r1) / 2 for r0, r1 in runs if r1 - r0 + 1 >= 2])
    larg = np.array([r1 - r0 + 1 for r0, r1 in runs if r1 - r0 + 1 >= 2])
    if len(centros) < 3:
        return None
    esp = float(np.median(np.diff(centros)))
    # só sombras com largura de ~meio passo (tira o menisco, a parede, as pontas do traço)
    ok = (larg > 0.25 * esp) & (larg < 0.8 * esp)
    c = centros[ok]
    if len(c) < 3:
        return None
    esp = float(np.median(np.diff(c)))
    k = np.round((c - c[0]) / esp)
    for _ in range(3):        # tira sombras a mais de 1/4 de passo da reta e reajusta
        A = np.vstack([k * passo_mm, np.ones_like(k)]).T
        (mm, x0), *_ = np.linalg.lstsq(A, c, rcond=None)
        res = c - (x0 + mm * k * passo_mm)
        bom = np.abs(res) < 0.25 * esp
        if bom.all():
            break
        c, k = c[bom], k[bom]
    n = len(c)
    if n < 3:
        return None
    A = np.vstack([k * passo_mm, np.ones_like(k)]).T
    (mm, x0), *_ = np.linalg.lstsq(A, c, rcond=None)
    res = c - (x0 + mm * k * passo_mm)
    s2 = np.sum(res ** 2) / max(n - 2, 1)
    cov = s2 * np.linalg.inv(A.T @ A)
    quad = None
    if n >= 5:                # curvatura: a folha diverge de forma não linear?
        cq = np.polyfit(k * passo_mm, c, 2)
        quad = float(cq[0])
    return dict(m=float(mm), u_m=float(np.sqrt(cov[0, 0])), x0=float(x0), centros=c, k=k,
                residuo_mm=float(np.sqrt(s2) / abs(mm)), n=n, quad=quad)


# ---------- Calibração de uma montagem ----------
def _ficheiro(pasta, base):
    for f in sorted(os.listdir(pasta)):
        if os.path.splitext(f)[0].lower() == base and e_imagem(f):
            return os.path.join(pasta, f)
    return None


def calibrar(img_ref, img_pente, reg, reduzir=1):
    """Calibração a partir das duas fotos (arrays) e do registo da montagem."""
    rec = None
    if reg.get('recorte'):
        rec = [float(v) / reduzir for v in re.split(r'[;\s]+', reg['recorte'].strip()) if v]
    tr_ref = extrair_traco(img_ref, rec)
    tr_pen = extrair_traco(img_pente, rec)
    pente = sombras_pente(tr_pen)
    if pente is None:
        raise SystemExit('Não encontrei as sombras do pente (precisa de ≥ 3). Ver a figura da calibração '
                         'e o LEIA-ME (pente encostado à parede de entrada, sombras nítidas).')
    if num(reg, 'px_por_mm_ecra') is not None:
        p = num(reg, 'px_por_mm_ecra') / reduzir
        u_p = num(reg, 'u_px_por_mm_ecra', 0.01 * p * reduzir) / reduzir
        grelha = None
    else:
        grelha = escala_grelha(img_ref)
        if grelha is None:
            raise SystemExit('Não encontrei a grelha do papel milimétrico. Pôr px_por_mm_ecra no registo.')
        p, u_p = grelha['p'], grelha['u_p']
    Z = num(reg, 'z_mm')
    L = num(reg, 'l_mm')
    if Z is None or L is None:
        raise SystemExit('Faltam Z_mm e L_mm no registo da montagem.')
    n_meio = num(reg, 'n_meio', 1.333)
    return dict(m=abs(pente['m']), u_m=pente['u_m'], x0=pente['x0'], pente=pente,
                p=p, u_p=u_p, grelha=grelha,
                ref_linha=tr_ref['linha'], ref_valido=tr_ref['valido'], tr_ref=tr_ref, tr_pente=tr_pen,
                recorte=rec, reduzir=reduzir, forma=img_ref.shape[:2],
                Z=Z, u_Z=num(reg, 'u_z_mm', 3.0), L=L, u_L=num(reg, 'u_l_mm', 0.05), n_meio=n_meio,
                Z_ef=Z + L / (2 * n_meio))


_CACHE_CAL = {}


def carregar_calibracao(nome, max_lado=2000):
    """Calibra a montagem fotos/calibracao/<nome>/ (referencia.*, pente.*, registo.txt)."""
    if nome in _CACHE_CAL:
        return _CACHE_CAL[nome]
    pasta = os.path.join(PASTA_FOTOS, 'calibracao', nome)
    if not os.path.isdir(pasta):
        raise SystemExit(f'Não existe a pasta de calibração {pasta}')
    f_ref, f_pen = _ficheiro(pasta, 'referencia'), _ficheiro(pasta, 'pente')
    if not f_ref or not f_pen:
        raise SystemExit(f'{pasta}: faltam as fotos referencia.jpg e/ou pente.jpg')
    red = fator_reducao(f_ref, max_lado)
    cal = calibrar(ler_imagem(f_ref, red), ler_imagem(f_pen, red),
                   ler_registo(os.path.join(pasta, 'registo.txt')), red)
    cal['nome'] = nome
    _CACHE_CAL[nome] = cal
    return cal


def resumo_calibracao(cal):
    linhas = [f"pente: m = {cal['m']:.3f} ± {cal['u_m']:.3f} px/mm (tanque), {cal['pente']['n']} sombras, "
              f"resíduo {cal['pente']['residuo_mm']:.2f} mm",
              f"ecrã:  p = {cal['p']:.3f} ± {cal['u_p']:.3f} px/mm (papel)"
              + ('' if cal['grelha'] else '  [do registo]'),
              f"ampliação da folha M = m/p = {cal['m'] / cal['p']:.3f}  (≈ 1 com a folha paralela)",
              f"Z = {cal['Z']:.0f} ± {cal['u_Z']:.0f} mm, L = {cal['L']:.2f} ± {cal['u_L']:.2f} mm, "
              f"Z_ef = Z + L/2n = {cal['Z_ef']:.1f} mm"]
    av = []
    M = cal['m'] / cal['p']
    if not 0.5 < M < 2:
        av.append('AVISO: M longe de 1. Ou a folha diverge muito, ou a grelha apanhou as linhas de 5/10 mm '
                  '(ver figura; pode-se pôr px_por_mm_ecra no registo).')
    if cal['tr_ref']['frac_saturado'] > 0.3:
        av.append('AVISO: o traço está sobre-exposto (branco no centro). Baixar a exposição do telemóvel.')
    if cal['pente']['quad'] is not None and abs(cal['pente']['quad']) * (30 ** 2) > 0.5 * cal['m']:
        av.append('AVISO: as sombras do pente não estão igualmente espaçadas (folha a divergir?).')
    return linhas + av


# ---------- Perfil da bossa numa foto ----------
def perfil_bossa(img, cal):
    """(y no tanque em mm, δ no ecrã em mm) a partir de uma foto e da calibração."""
    if img.shape[:2] != tuple(cal['forma']):
        raise SystemExit(f"A foto tem {img.shape[1]}×{img.shape[0]} px e a referência "
                         f"{cal['forma'][1]}×{cal['forma'][0]}: têm de ser do mesmo telemóvel, na mesma "
                         "posição e com o mesmo zoom.")
    tr = extrair_traco(img, cal['recorte'])
    d_px = tr['linha'] - cal['ref_linha']
    ok = tr['valido'] & cal['ref_valido'] & np.isfinite(d_px)
    y = (tr['x'][ok] - cal['x0']) / cal['m']
    d = d_px[ok] / cal['p']
    return y, d, tr


# ---------- Ajustes ----------
def gauss(y, A, yc, s, c0):
    return A * np.exp(-(y - yc) ** 2 / (2 * s ** 2)) + c0


def gauss_reta(y, A, yc, s, c0, c1):
    return A * np.exp(-(y - yc) ** 2 / (2 * s ** 2)) + c0 + c1 * y


def ajustar_bossa(y, d, com_reta=False):
    """Gaussiana (+ constante, + reta se com_reta) ao desvio δ(y).
    Devolve A, yc, σ, área = A·σ·√(2π), com incertezas, ou None se o ajuste falhar."""
    if len(y) < 10:
        return None
    o = np.argsort(y)
    y, d = y[o], d[o]
    ds = gaussian_filter1d(d, 2)
    base = np.median(d)
    j = int(np.argmax(np.abs(ds - base)))
    A0 = ds[j] - base
    meio = np.abs(ds - base) > abs(A0) / 2
    s0 = max((y[meio].max() - y[meio].min()) / 2.355, 3 * np.median(np.diff(y))) if meio.any() else 2.0
    p0 = [A0, y[j], s0, base] + ([0.0] if com_reta else [])
    f = gauss_reta if com_reta else gauss
    lo = [-np.inf, y[0], 0.5 * np.median(np.diff(y)), -np.inf] + ([-np.inf] if com_reta else [])
    hi = [np.inf, y[-1], y[-1] - y[0], np.inf] + ([np.inf] if com_reta else [])
    try:
        p, cov = curve_fit(f, y, d, p0=p0, bounds=(lo, hi), maxfev=20000)
    except (RuntimeError, ValueError):
        return None
    if not np.all(np.isfinite(cov)):
        return None
    A, yc, s = p[0], p[1], abs(p[2])
    uA, us = np.sqrt(cov[0, 0]), np.sqrt(cov[2, 2])
    r2pi = np.sqrt(2 * np.pi)
    area = A * s * r2pi
    g = np.array([s * r2pi, A * r2pi])
    u_area = float(np.sqrt(g @ cov[np.ix_([0, 2], [0, 2])] @ g))
    res = d - f(y, *p)
    margem = min(yc - y[0], y[-1] - yc) / s       # quantos σ de asa há de cada lado
    return dict(A=float(A), u_A=float(uA), yc=float(yc), u_yc=float(np.sqrt(cov[1, 1])),
                s=float(s), u_s=float(us), area=float(area), u_area=u_area, p=p, f=f,
                rms=float(np.std(res)), margem=float(margem), y=y, d=d)


def reta_ponderada(x, y, u):
    """y = a·x + b com pesos 1/u². Devolve a, b, cov (escalada por χ²/ν se > 1), χ²/ν."""
    x, y, u = map(np.asarray, (x, y, u))
    w = 1 / u ** 2
    A = np.vstack([x, np.ones_like(x)]).T
    cov = np.linalg.inv(A.T @ (A * w[:, None]))
    a, b = cov @ (A.T @ (w * y))
    res = y - (a * x + b)
    nu = len(x) - 2
    chi2 = float(np.sum(w * res ** 2))
    cr = chi2 / nu if nu > 0 else np.nan
    cov_e = cov * max(1.0, cr) if nu > 0 else cov
    return dict(a=float(a), b=float(b), cov=cov_e, cov_bruta=cov, chi2nu=cr, nu=nu, res=res)


def media_ponderada(v, u):
    v, u = np.asarray(v, float), np.asarray(u, float)
    w = 1 / u ** 2
    m = float(np.sum(w * v) / np.sum(w))
    return m, float(1 / np.sqrt(np.sum(w)))


def z_score(a, ua, b, ub=0.0):
    return (a - b) / math.hypot(ua, ub) if math.hypot(ua, ub) > 0 else float('nan')


# ---------- Figuras ----------
def virgulas(fig):
    """Vírgula decimal em toda a figura, como no texto do relatório. Chamar mesmo antes de guardar."""
    from matplotlib.ticker import FuncFormatter
    from matplotlib.text import Text
    pt = FuncFormatter(lambda v, _: f'{v:g}'.replace('.', ',').replace('-', '−'))
    for ax in fig.axes:
        for eixo in (ax.xaxis, ax.yaxis):
            if eixo.get_scale() == 'linear':
                eixo.set_major_formatter(pt)
    for t in fig.findobj(Text):
        s = t.get_text()
        novo = re.sub(r'(?<=\d)\.(?=\d)', ',', s)
        if novo != s:
            t.set_text(novo)


def guardar_json(caminho, dados):
    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2, default=conv)


# ---------- Fotos sintéticas (para os testes) ----------
def imagem_sintetica(W=1200, H=1200, p=6.0, m=6.3, x0=250.0, delta_mm=None, pente=False,
                     ruido=0.01, rng=None, larg_px=2.0, xa=60, xb=1140, n_sombras=10):
    """Papel milimétrico (p px/mm, linhas cor de laranja) com o traço do laser a 45°.
    A coluna x corresponde à altura y = (x − x0)/m no tanque; delta_mm(y) é o desvio no ecrã (mm,
    para baixo). Com pente=True, sombras de 3,2 mm a cada 6,4 mm a partir de y = 0."""
    rng = rng or np.random.default_rng(0)
    img = np.empty((H, W, 3), np.float32)
    img[:] = (0.92, 0.91, 0.88)
    lin = np.arange(H)[:, None]
    col = np.arange(W)[None, :]
    for eixo in (lin, col):
        q = eixo / p
        dist = np.abs(q - np.round(q)) * p
        forte = (np.abs(np.round(q) % 10) < 0.5)
        k = np.exp(-dist ** 2 / (2 * 0.6 ** 2)) * np.where(forte, 0.45, 0.25)
        img = img * (1 - k[..., None] * np.array([0.05, 0.35, 0.6], np.float32))
    x = np.arange(W, dtype=float)
    y = (x - x0) / m
    linha = H / 2 + (x - W / 2)                       # 45°
    if delta_mm is not None:
        linha = linha + delta_mm(y) * p
    incl = np.gradient(linha)
    wcol = larg_px * np.sqrt(1 + incl ** 2)
    amp = 1 / np.sqrt(1 + incl ** 2) ** 0.5
    I = amp[None, :] * np.exp(-(lin - linha[None, :]) ** 2 / (2 * wcol[None, :] ** 2))
    I[:, (x < xa) | (x > xb)] = 0
    if pente:
        fr = y / PASSO_PENTE_MM
        sombra = (np.abs(fr - np.round(fr)) < 0.25) & (fr > -0.3) & (fr < n_sombras - 0.7)
        I[:, sombra] = 0
    I = np.clip(I, 0, 1)[..., None]
    img = img * (1 - 0.9 * I) + 0.9 * I * np.array([1.0, 0.12, 0.10], np.float32)
    img = img + rng.normal(0, ruido, img.shape).astype(np.float32)
    return np.clip(img, 0, 1)


def calibracao_sintetica(Z=2000.0, L=50.0, p=6.0, m=6.3, rng=None):
    rng = rng or np.random.default_rng(1)
    ref = imagem_sintetica(p=p, m=m, rng=rng)
    pen = imagem_sintetica(p=p, m=m, pente=True, rng=rng)
    reg = {'z_mm': str(Z), 'l_mm': str(L), 'u_z_mm': '3', 'u_l_mm': '0.05'}
    cal = calibrar(ref, pen, reg)
    cal['nome'] = 'sintetica'
    return cal
