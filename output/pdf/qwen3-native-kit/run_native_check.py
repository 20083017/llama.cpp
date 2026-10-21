#!/usr/bin/env python3
"""Run the existing native llama.cpp example and compare its generated text."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def compare(raw, prompt, expected):
    if not raw.startswith(prompt):
        raise ValueError('Native stdout does not start with the exact prompt; inspect native.stdout.bin and native.stderr.log.')
    answer = raw[len(prompt):]
    if answer.endswith(b'\n'):
        answer = answer[:-1]
    return answer, answer == expected.removesuffix(b'\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', required=True, type=Path)
    parser.add_argument('--model', required=True, type=Path)
    parser.add_argument('--library-dir', required=True, type=Path)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).resolve().parent / 'fixtures')
    parser.add_argument('--out', type=Path, default=Path('native-check'))
    parser.add_argument('--gpu-layers', type=int, default=0)
    args = parser.parse_args()
    for path in [args.exe, args.model, args.fixtures / 'rendered-prompt.txt', args.fixtures / 'expected.txt']:
        if not path.is_file():
            parser.error(f'Missing file: {path}')
    if not args.library_dir.is_dir():
        parser.error(f'Missing library directory: {args.library_dir}')
    prompt = (args.fixtures / 'rendered-prompt.txt').read_bytes()
    expected = (args.fixtures / 'expected.txt').read_bytes()
    args.out.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    previous = env.get('LD_LIBRARY_PATH', '')
    env['LD_LIBRARY_PATH'] = str(args.library_dir.resolve()) + (os.pathsep + previous if previous else '')
    command = [str(args.exe.resolve()), '-m', str(args.model.resolve()), '-n', '128',
               '-ngl', str(args.gpu_layers), prompt.decode('utf-8')]
    with (args.out / 'native.stdout.bin').open('wb') as stdout:
        with (args.out / 'native.stderr.log').open('wb') as stderr:
            process = subprocess.run(command, stdout=stdout, stderr=stderr, env=env, check=False)
    if process.returncode:
        print(f'NATIVE_EXIT={process.returncode}; inspect {args.out / "native.stderr.log"}', file=sys.stderr)
        return 2
    try:
        answer, exact = compare((args.out / 'native.stdout.bin').read_bytes(), prompt, expected)
        (args.out / 'answer.txt').write_bytes(answer)
        print(f'EXACT_MATCH={exact}')
        print('ANSWER=' + repr(answer.decode('utf-8')))
        return 0 if exact else 1
    except (ValueError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
