#!/usr/bin/env python3
"""Single background-removal entry point: choose the method, cut out, clean,
validate, and — for photos — switch models automatically when the result looks
poor. Minimal output (do not expose the internal method/model to the user).

Usage: python3 run.py INPUT [OUTPUT]
                    [--method auto|solid|photo] [--model NAME]
                    [--keep-largest] [--no-fallback]

Print 3 lines: final path | PREVIEW <path> | STATUS WxH
STATUS = OK or one or more flags (CHECAR_CANTOS, CHECAR_RESIDUO,
OBJETO_QUASE_VAZIO, FUNDO_NAO_REMOVIDO)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import numpy as np
from PIL import Image
import common

HERE = os.path.dirname(os.path.abspath(__file__))
# Model trial order for photos. u2net_human_seg is excluded (people only) — use it
# manually when you know the subject is a person.
PHOTO_MODELS = ['birefnet-general-lite', 'isnet-general-use']


def fail(script, stderr):
    sys.stderr.write(f'[{script}] failed:\n{(stderr or "").strip()[-800:]}\n')
    sys.exit(1)


def run_script(name, args):
    return subprocess.run([sys.executable, os.path.join(HERE, name), *args],
                          stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def alpha_of(path):
    return np.asarray(Image.open(path).convert('RGBA'))[:, :, 3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--method', choices=['auto', 'solid', 'photo'], default='auto')
    ap.add_argument('--model', help='force a photo model (disable fallback)')
    ap.add_argument('--keep-largest', action='store_true',
                    help='keep only the largest connected component (discard distractors)')
    ap.add_argument('--no-fallback', action='store_true')
    a = ap.parse_args()

    dst = a.dst or os.path.splitext(a.src)[0] + '-sem-fundo.png'
    method = a.method if a.method != 'auto' else common.decide_method(common.load_rgb(a.src))

    if method == 'solid':
        p = run_script('remove_bg_solid.py', [a.src, dst])
        if p.returncode != 0:
            fail('remove_bg_solid.py', p.stderr)
    else:
        if a.model:
            models = [a.model]
        elif a.no_fallback:
            models = PHOTO_MODELS[:1]
        else:
            models = PHOTO_MODELS
        extra = ['--keep-largest'] if a.keep_largest else []
        best = None  # (score, tmp_path, metrics)
        for m in models:
            fd, tmp = tempfile.mkstemp(suffix='.png')
            os.close(fd)
            p = run_script('remove_bg_photo.py', [a.src, tmp, m, *extra])
            if p.returncode != 0 or not os.path.exists(tmp) or os.path.getsize(tmp) == 0:
                os.path.exists(tmp) and os.remove(tmp)
                continue
            mt = common.assess_alpha(alpha_of(tmp))
            score = (len(mt['flags']), -mt['largest_frac'])  # fewer flags, more cohesive
            if best is None or score < best[0]:
                best and os.path.exists(best[1]) and os.remove(best[1])
                best = (score, tmp, mt)
            else:
                os.remove(tmp)
            if not mt['flags']:
                break  # already clean; no need to test more models
        if best is None:
            fail('remove_bg_photo.py',
                 'all models failed (RAM/download?). Try manually: '
                 'python3 remove_bg_photo.py INPUT OUTPUT isnet-general-use')
        shutil.move(best[1], dst)

    preview = '/tmp/bg_preview_' + os.path.splitext(os.path.basename(dst))[0] + '.png'
    common.save_preview(dst, preview)
    m = common.assess_alpha(alpha_of(dst))
    W, H = m['WxH']
    print(dst)
    print('PREVIEW', preview)
    print('OK' if not m['flags'] else ' '.join(m['flags']), f'{W}x{H}')


if __name__ == '__main__':
    main()
