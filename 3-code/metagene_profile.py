#!/usr/bin/env python3
"""
Metagene / composite profile of nascent-transcription signal (PRO-seq, NET-seq, TT-seq)
for a gene set versus a matched control set, in two conditions.

Why this figure: the pausing index is a *ratio* (promoter density / gene-body density).
A change in that ratio cannot tell you whether the promoter numerator fell, the body
denominator rose, or the pause site moved. The metagene decomposes the ratio along the
gene axis and shows which of those actually happened.

Three panels:
  A  TSS-anchored composite, bp resolution (default -1000 .. +2000)
  B  Scaled gene body, TSS -> TES (default 100 bins) with flanks
  C  Positional log2(treated / untreated), gene set vs matched control, with
     bootstrap ribbons.  Panel C is the one that carries a small effect: a ~10%
     pausing-index change is invisible in A and B but explicit in C.

Usage (real data):
  python3 metagene_profile.py \
      --sample Untreated:untr_plus.bw,untr_minus.bw \
      --sample MS023:ms023_plus.bw,ms023_minus.bw \
      --genes genes.bed6 \
      --group E2F1-bound:e2f1_bound_ids.txt \
      --group matched-control:matched_control_ids.txt \
      --treated MS023 --untreated Untreated \
      --out ../5-figures/metagene_MS023.pdf

Usage (design mock, simulated data, watermarked):
  python3 metagene_profile.py --demo --out ../5-figures/MOCK_metagene.pdf

Unstranded / single-bigwig samples: give one path instead of two.
Scale factors (spike-in, or reads-in-peaks) go in with --scale NAME:FACTOR.
"""

import argparse
import os
import sys

import numpy as np

# --- house style, matched to the existing figure set -------------------------
# orange = focal gene set, slate = matched control. Linestyle encodes treatment,
# so identity never rests on color alone.
C_SET = "#C2571A"
C_CTL = "#6B7380"
C_RULE = "#C9C9C4"
C_INK = "#1F2328"
C_MUTED = "#6B7380"


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 7,
        "axes.linewidth": 0.8,
        "axes.edgecolor": C_INK,
        "axes.labelcolor": C_INK,
        "xtick.color": C_INK,
        "ytick.color": C_INK,
        "xtick.major.width": 0.8,
        "ytick.major.width": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "pdf.fonttype": 42,   # keep text editable in Illustrator
        "ps.fonttype": 42,
    })
    return plt


# =============================================================================
# signal extraction
# =============================================================================

def load_bed6(path):
    """Return list of (chrom, start, end, name, score, strand)."""
    genes = []
    with open(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith(("#", "track", "browser")):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 6:
                raise ValueError(f"{path}: need BED6 (chrom start end name score strand), got {len(f)} cols")
            genes.append((f[0], int(f[1]), int(f[2]), f[3], f[4], f[5]))
    return genes


def load_ids(path):
    with open(path) as fh:
        return {ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")}


class Sample:
    """One condition. PRO-seq is stranded: plus/minus bigwigs are read separately
    and the strand matching the gene is used, so antisense signal never leaks in."""

    def __init__(self, name, paths, scale=1.0):
        import pyBigWig
        self.name = name
        self.scale = scale
        self.bw_plus = pyBigWig.open(paths[0])
        self.bw_minus = pyBigWig.open(paths[1]) if len(paths) > 1 else None

    def values(self, chrom, start, end, strand):
        bw = self.bw_minus if (strand == "-" and self.bw_minus is not None) else self.bw_plus
        if chrom not in bw.chroms():
            return None
        clen = bw.chroms()[chrom]
        if start < 0 or end > clen or end <= start:
            return None
        v = np.array(bw.values(chrom, start, end), dtype=float)
        v = np.nan_to_num(v, nan=0.0)
        # minus-strand bigwigs are conventionally negative-valued
        v = np.abs(v) * self.scale
        return v[::-1] if strand == "-" else v


def tss_matrix(sample, genes, upstream, downstream, binsize):
    """Genes x bins, bp-resolution around the TSS, oriented 5'->3'."""
    nbin = (upstream + downstream) // binsize
    out = np.full((len(genes), nbin), np.nan)
    for i, (chrom, start, end, _n, _s, strand) in enumerate(genes):
        tss = start if strand == "+" else end
        lo, hi = (tss - upstream, tss + downstream) if strand == "+" else (tss - downstream, tss + upstream)
        v = sample.values(chrom, lo, hi, strand)
        if v is None or v.size != upstream + downstream:
            continue
        out[i] = v.reshape(nbin, binsize).mean(axis=1)
    return out


def scaled_matrix(sample, genes, nbody, flank, flank_bins, min_len):
    """Genes x bins, gene body linearly rescaled to `nbody` bins, plus flanks."""
    out = np.full((len(genes), flank_bins + nbody + flank_bins), np.nan)
    for i, (chrom, start, end, _n, _s, strand) in enumerate(genes):
        if end - start < min_len:
            continue
        v = sample.values(chrom, start - flank, end + flank, strand)
        if v is None:
            continue
        up, body, dn = v[:flank], v[flank:-flank], v[-flank:]
        idx = np.linspace(0, len(body), nbody + 1).astype(int)
        body_b = np.array([body[a:b].mean() if b > a else 0.0 for a, b in zip(idx[:-1], idx[1:])])
        up_b = up.reshape(flank_bins, flank // flank_bins).mean(axis=1)
        dn_b = dn.reshape(flank_bins, flank // flank_bins).mean(axis=1)
        out[i] = np.concatenate([up_b, body_b, dn_b])
    return out


# =============================================================================
# aggregation
# =============================================================================

def _boot_weights(n, boot, rng):
    """Bootstrap resampling as multinomial counts.

    A bootstrap mean is a count-weighted mean, so the whole bootstrap is one
    (boot x n) @ (n x bins) matmul. Fancy-indexing instead would materialize a
    (boot, n, bins) array -- 6 GB at n=8,500 genes, 300 bins, 1,000 reps.
    """
    return rng.multinomial(n, np.full(n, 1.0 / n), size=boot).astype(np.float32)


def composite(mat, boot=1000, seed=0, trim=0.0):
    """Mean profile + bootstrap 95% CI over genes (rows).

    Bootstrapping over *genes* gives a gene-level interval. It is not a
    replicate-level interval -- with >=2 biological replicates, run this per
    replicate and bootstrap the replicate means instead.
    """
    m = mat[~np.all(np.isnan(mat), axis=1)]
    m = np.nan_to_num(m, nan=0.0).astype(np.float32)
    if trim > 0:
        hi_c = np.quantile(m, 1 - trim, axis=0, keepdims=True)
        m = np.minimum(m, hi_c)
    mean = m.mean(axis=0)
    n = m.shape[0]
    w = _boot_weights(n, boot, np.random.default_rng(seed))
    bs = (w @ m) / n
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return mean, lo, hi, n


def positional_lfc(treated, untreated, boot=1000, seed=0, pseudo=None):
    """Per-position log2(treated/untreated) with a bootstrap CI, paired by gene.

    Genes are resampled once and the same resample is applied to both conditions,
    which preserves the pairing -- the same gene contributes to numerator and
    denominator together.
    """
    t = np.nan_to_num(treated, nan=0.0).astype(np.float32)
    u = np.nan_to_num(untreated, nan=0.0).astype(np.float32)
    keep = (t.sum(axis=1) > 0) & (u.sum(axis=1) > 0)
    t, u = t[keep], u[keep]
    if t.shape[0] == 0:
        raise ValueError("no genes with signal in both conditions")
    if pseudo is None:
        # 2% of the reference profile's mean level. A pseudocount tied to the
        # smallest positive value leaves read-free positions (far upstream) with
        # a wildly noisy ratio; this damps them toward 0 without touching the
        # promoter or gene body, where signal is orders of magnitude higher.
        pseudo = float(max(0.02 * u.mean(), 1e-9))
    n = t.shape[0]
    w = _boot_weights(n, boot, np.random.default_rng(seed))
    bs = np.log2(((w @ t) / n + pseudo) / ((w @ u) / n + pseudo))
    lfc = np.log2((t.mean(axis=0) + pseudo) / (u.mean(axis=0) + pseudo))
    lo, hi = np.percentile(bs, [2.5, 97.5], axis=0)
    return lfc, lo, hi, n


# =============================================================================
# plotting
# =============================================================================

def draw(profiles, lfcs, x_tss, x_scaled, labels, out, title, nbody, flank_bins, demo=False):
    plt = _mpl()
    fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.5))
    ax_a, ax_b, ax_c = axes

    # -- A: TSS-anchored ------------------------------------------------------
    for (grp, cond), (mean, lo, hi, _n) in profiles["tss"].items():
        col = C_SET if grp == labels["set"] else C_CTL
        ls = "-" if cond == labels["untreated"] else "--"
        ax_a.fill_between(x_tss, lo, hi, color=col, alpha=0.16, lw=0)
        ax_a.plot(x_tss, mean, color=col, ls=ls, lw=1.4,
                  label=f"{grp}, {cond}", solid_capstyle="round")
    ax_a.axvline(0, color=C_RULE, lw=0.8, zorder=0)
    ax_a.set_xlabel("distance from TSS (bp)")
    ax_a.set_ylabel("normalized signal")
    ax_a.set_title("A  TSS-anchored", loc="left", fontsize=7.5, color=C_INK, pad=6)

    # -- B: scaled gene body --------------------------------------------------
    for (grp, cond), (mean, lo, hi, _n) in profiles["scaled"].items():
        col = C_SET if grp == labels["set"] else C_CTL
        ls = "-" if cond == labels["untreated"] else "--"
        ax_b.fill_between(x_scaled, lo, hi, color=col, alpha=0.16, lw=0)
        ax_b.plot(x_scaled, mean, color=col, ls=ls, lw=1.4, solid_capstyle="round")
    for v in (flank_bins, flank_bins + nbody):
        ax_b.axvline(v, color=C_RULE, lw=0.8, zorder=0)
    ax_b.set_xticks([flank_bins, flank_bins + nbody])
    ax_b.set_xticklabels(["TSS", "TES"])
    ax_b.set_xlabel("scaled gene body")
    ax_b.set_title("B  metagene, scaled", loc="left", fontsize=7.5, color=C_INK, pad=6)

    # -- C: positional log2 fold change --------------------------------------
    for grp, (lfc, lo, hi, n) in lfcs.items():
        col = C_SET if grp == labels["set"] else C_CTL
        ax_c.fill_between(x_tss, lo, hi, color=col, alpha=0.16, lw=0)
        ax_c.plot(x_tss, lfc, color=col, lw=1.4, solid_capstyle="round")
        j = int(len(x_tss) * 0.72)
        ax_c.annotate(f"{grp}  (n={n:,})", (x_tss[j], lfc[j]), textcoords="offset points",
                      xytext=(4, 7 if grp == labels["set"] else -11),
                      color=col, fontsize=6.5, fontweight="bold")
    ax_c.axhline(0, color=C_RULE, lw=0.8, zorder=0)
    ax_c.axvline(0, color=C_RULE, lw=0.8, zorder=0)
    ax_c.set_xlabel("distance from TSS (bp)")
    ax_c.set_ylabel(f"log$_2$ ({labels['treated']} / {labels['untreated']})")
    ax_c.set_title("C  positional change", loc="left", fontsize=7.5, color=C_INK, pad=6)

    leg = ax_a.legend(frameon=False, fontsize=5.8, loc="upper right",
                      handlelength=1.6, borderaxespad=0.2, labelspacing=0.25)
    for t in leg.get_texts():
        t.set_color(C_INK)

    fig.suptitle(title, x=0.01, ha="left", fontsize=9, color=C_INK)
    fig.tight_layout(rect=(0, 0, 1, 0.93))

    if demo:
        for ax in axes:
            ax.text(0.5, 0.5, "SIMULATED", transform=ax.transAxes, fontsize=17,
                    color="#D8433A", alpha=0.20, ha="center", va="center",
                    rotation=28, fontweight="bold", zorder=99)
        fig.text(0.01, 0.005,
                 "DESIGN MOCK - simulated data, not measurements. Generated by "
                 "metagene_profile.py --demo",
                 fontsize=6, color="#D8433A")

    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    png = os.path.splitext(out)[0] + ".png"
    fig.savefig(png, dpi=220, bbox_inches="tight")
    print(f"wrote {out}\nwrote {png}")
    return fig

# =============================================================================
# demo / design mock
# =============================================================================

def _simulate(n, x, amp, body, seed):
    """Per-gene PRO-seq-like profiles: divergent upstream peak, promoter-proximal
    pause peak just downstream of the TSS, then a gene-body plateau. Per-gene
    expression is lognormal, which is what makes the bootstrap ribbons realistic."""
    rng = np.random.default_rng(seed)
    shape = (amp * np.exp(-(((x - 50.0) / 70.0) ** 2))
             + 0.07 * amp * np.exp(-(((x + 180.0) / 90.0) ** 2))
             + body / (1.0 + np.exp(-(x - 350.0) / 150.0)))
    expr = rng.lognormal(0.0, 0.85, size=(n, 1))
    m = shape[None, :] * expr
    return (m + rng.normal(0.0, 0.12 * np.sqrt(m + 1e-9))).clip(0).astype(np.float32)


def _simulate_scaled(n, nb, fb, amp, body, seed):
    """Same generator as _simulate but on the scaled axis: flank bins, then the
    pause peak at the TSS boundary, the body plateau, and a 3' bump before TES."""
    rng = np.random.default_rng(seed)
    i = np.arange(fb * 2 + nb, dtype=float)
    tss, tes = float(fb), float(fb + nb)
    shape = (amp * np.exp(-(((i - tss - 0.6) / 1.1) ** 2))
             + 0.07 * amp * np.exp(-(((i - tss + 2.2) / 1.4) ** 2))
             + body / (1.0 + np.exp(-(i - tss - 4.0) / 2.0)) * (i < tes)
             + 0.25 * body * np.exp(-(((i - tes + 3.0) / 4.0) ** 2))
             + body * 0.30 * np.exp(-(((i - tes) / 6.0) ** 2)) * (i >= tes))
    expr = rng.lognormal(0.0, 0.85, size=(n, 1))
    m = shape[None, :] * expr
    return (m + rng.normal(0.0, 0.12 * np.sqrt(m + 1e-9))).clip(0).astype(np.float32)


def run_demo(out, boot=600):
    """Effect sizes are calibrated to the *measured* result (-0.16 log2 pausing
    index on E2F1-bound genes, ~-0.01 on matched controls) so the mock shows how
    legible that effect actually is on a metagene -- not an inflated cartoon."""
    x = np.arange(-1000, 2000, 10) + 5.0
    nb, fb = 100, 20
    xs = np.arange(fb * 2 + nb)

    # amplitude / body pairs -> pausing-index change of -0.161 (set), -0.012 (control)
    cfg = {
        ("E2F1-bound", "Untreated"): (1.00, 0.110, 1),
        ("E2F1-bound", "MS023 2d"):  (0.928, 0.1142, 2),
        ("matched control", "Untreated"): (0.88, 0.110, 3),
        ("matched control", "MS023 2d"):  (0.8765, 0.1104, 4),
    }
    n = 8518

    tss_mats, scaled_mats = {}, {}
    for key, (a, b, sd) in cfg.items():
        tss_mats[key] = _simulate(n, x, a, b, sd)
        scaled_mats[key] = _simulate_scaled(n, nb, fb, a, b, sd + 10)

    profiles = {
        "tss": {k: composite(v, boot=boot) for k, v in tss_mats.items()},
        "scaled": {k: composite(v, boot=boot) for k, v in scaled_mats.items()},
    }
    lfcs = {
        g: positional_lfc(tss_mats[(g, "MS023 2d")], tss_mats[(g, "Untreated")], boot=boot)
        for g in ("E2F1-bound", "matched control")
    }

    # report the pausing index the simulation actually produced, as a self-check
    pause = (x >= -50) & (x <= 300)
    gb = (x >= 1000)
    for g in ("E2F1-bound", "matched control"):
        pi = {}
        for c in ("Untreated", "MS023 2d"):
            m = tss_mats[(g, c)]
            pi[c] = m[:, pause].mean() / m[:, gb].mean()
        print(f"  simulated {g:16s} dlog2 PI = {np.log2(pi['MS023 2d'] / pi['Untreated']):+.3f}")

    labels = {"set": "E2F1-bound", "control": "matched control",
              "treated": "MS023 2d", "untreated": "Untreated"}
    draw(profiles, lfcs, x, xs, labels, out,
         "Proposed metagene panel - MS023 2d vs Untreated",
         nb, fb, demo=True)


# =============================================================================
# CLI
# =============================================================================

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--demo", action="store_true",
                   help="generate a watermarked design mock from simulated data")
    p.add_argument("--sample", action="append", default=[], metavar="NAME:plus.bw[,minus.bw]",
                   help="condition name and bigwig(s); repeat once per condition")
    p.add_argument("--scale", action="append", default=[], metavar="NAME:FACTOR",
                   help="per-condition normalization factor (spike-in etc.)")
    p.add_argument("--genes", metavar="BED6", help="gene annotation, BED6, one row per gene")
    p.add_argument("--group", action="append", default=[], metavar="NAME:ids.txt",
                   help="gene-set membership; give exactly two (focal set, matched control)")
    p.add_argument("--treated", help="condition name plotted as treated")
    p.add_argument("--untreated", help="condition name plotted as reference")
    p.add_argument("--upstream", type=int, default=1000)
    p.add_argument("--downstream", type=int, default=2000)
    p.add_argument("--binsize", type=int, default=10)
    p.add_argument("--body-bins", type=int, default=100)
    p.add_argument("--flank", type=int, default=2000)
    p.add_argument("--flank-bins", type=int, default=20)
    p.add_argument("--min-length", type=int, default=2000,
                   help="skip genes shorter than this in the scaled panel")
    p.add_argument("--trim", type=float, default=0.0,
                   help="winsorize the top fraction per position, e.g. 0.01")
    p.add_argument("--boot", type=int, default=1000)
    p.add_argument("--title", default="")
    p.add_argument("--out", default="../5-figures/metagene.pdf")
    a = p.parse_args(argv)

    if a.demo:
        run_demo(a.out)
        return 0

    missing = [f for f in ("genes", "treated", "untreated") if not getattr(a, f)]
    if missing or len(a.sample) < 2 or len(a.group) != 2:
        p.error("real mode needs --genes, --treated, --untreated, >=2 --sample and exactly 2 --group "
                f"(missing: {', '.join(missing) or 'none'}; "
                f"{len(a.sample)} sample(s), {len(a.group)} group(s))")

    if a.upstream % a.binsize or a.downstream % a.binsize:
        p.error("--upstream and --downstream must be multiples of --binsize")
    if a.flank % a.flank_bins:
        p.error("--flank must be a multiple of --flank-bins")

    try:
        import pyBigWig  # noqa: F401
    except ImportError:
        p.error("real mode needs pyBigWig  (pip install pyBigWig)")

    scales = dict(s.split(":", 1) for s in a.scale)
    samples = {}
    for spec in a.sample:
        name, paths = spec.split(":", 1)
        samples[name] = Sample(name, paths.split(","), float(scales.get(name, 1.0)))
    for need in (a.treated, a.untreated):
        if need not in samples:
            p.error(f"--sample for {need!r} not given (have: {', '.join(samples)})")

    genes = load_bed6(a.genes)
    by_name = {g[3]: g for g in genes}
    groups, order = {}, []
    for spec in a.group:
        name, path = spec.split(":", 1)
        ids = load_ids(path)
        sel = [by_name[i] for i in ids if i in by_name]
        if not sel:
            p.error(f"group {name!r}: none of its {len(ids):,} ids matched column 4 of {a.genes}")
        if len(sel) < len(ids):
            print(f"  note: group {name}: {len(ids) - len(sel):,}/{len(ids):,} ids absent from {a.genes}",
                  file=sys.stderr)
        groups[name] = sel
        order.append(name)

    profiles = {"tss": {}, "scaled": {}}
    tss_raw = {}
    for gname in order:
        for cname in (a.untreated, a.treated):
            s, gl = samples[cname], groups[gname]
            mt = tss_matrix(s, gl, a.upstream, a.downstream, a.binsize)
            ms = scaled_matrix(s, gl, a.body_bins, a.flank, a.flank_bins, a.min_length)
            tss_raw[(gname, cname)] = mt
            profiles["tss"][(gname, cname)] = composite(mt, boot=a.boot, trim=a.trim)
            profiles["scaled"][(gname, cname)] = composite(ms, boot=a.boot, trim=a.trim)
            print(f"  {gname:20s} {cname:14s} n={profiles['tss'][(gname, cname)][3]:,}")

    lfcs = {g: positional_lfc(tss_raw[(g, a.treated)], tss_raw[(g, a.untreated)], boot=a.boot)
            for g in order}

    x_tss = np.arange(-a.upstream, a.downstream, a.binsize) + a.binsize / 2.0
    x_scaled = np.arange(a.flank_bins * 2 + a.body_bins)
    labels = {"set": order[0], "control": order[1],
              "treated": a.treated, "untreated": a.untreated}
    draw(profiles, lfcs, x_tss, x_scaled, labels, a.out,
         a.title or f"{a.treated} vs {a.untreated}", a.body_bins, a.flank_bins)

    tsv = os.path.splitext(a.out)[0] + "_values.tsv"
    with open(tsv, "w") as fh:
        fh.write("panel\tgroup\tcondition\tposition\tmean\tci_lo\tci_hi\tn\n")
        for panel, xs in (("tss", x_tss), ("scaled", x_scaled)):
            for (g, c), (mean, lo, hi, n) in profiles[panel].items():
                for xi, mi, li, hi_ in zip(xs, mean, lo, hi):
                    fh.write(f"{panel}\t{g}\t{c}\t{xi:g}\t{mi:.6g}\t{li:.6g}\t{hi_:.6g}\t{n}\n")
        for g, (lfc, lo, hi, n) in lfcs.items():
            for xi, mi, li, hi_ in zip(x_tss, lfc, lo, hi):
                fh.write(f"lfc\t{g}\t{a.treated}/{a.untreated}\t{xi:g}\t{mi:.6g}\t{li:.6g}\t{hi_:.6g}\t{n}\n")
    print(f"wrote {tsv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
