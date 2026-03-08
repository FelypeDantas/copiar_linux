#!/usr/bin/env python3

import sys
import time
import argparse
import hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

BUF_SIZE = 1024 * 1024


def format_size(size):
    for unit in ["B","KB","MB","GB","TB"]:
        if size < 1024:
            return f"{size:.1f}{unit}"
        size /= 1024
    return f"{size:.1f}PB"


def sha256sum(path):
    h = hashlib.sha256()
    with open(path,"rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def progress_bar(done,total,start):

    percent = done/total
    width = 30
    filled = int(percent*width)

    bar = "#"*filled + "-"*(width-filled)

    elapsed = time.time() - start
    speed = done/elapsed if elapsed else 0
    eta = (total-done)/speed if speed else 0

    sys.stdout.write(
        f"\r[{bar}] {percent*100:5.1f}% "
        f"{format_size(done)}/{format_size(total)} "
        f"{format_size(speed)}/s "
        f"ETA {eta:5.1f}s"
    )
    sys.stdout.flush()


def copy_file(src,dst,resume=False,progress=False):

    src = Path(src)
    dst = Path(dst)

    total = src.stat().st_size
    start_time = time.time()

    mode = "wb"
    copied = 0

    if resume and dst.exists():
        copied = dst.stat().st_size
        mode = "ab"

    with open(src,"rb") as fsrc, open(dst,mode) as fdst:

        fsrc.seek(copied)

        while True:
            data = fsrc.read(BUF_SIZE)
            if not data:
                break

            fdst.write(data)
            copied += len(data)

            if progress:
                progress_bar(copied,total,start_time)

    if progress:
        print()


def copy_directory(src,dst,args):

    src = Path(src)
    dst = Path(dst)

    dst.mkdir(parents=True,exist_ok=True)

    tasks=[]

    for path in src.rglob("*"):

        if path.is_file():

            rel = path.relative_to(src)
            target = dst / rel

            target.parent.mkdir(parents=True,exist_ok=True)

            tasks.append((path,target))

    with ThreadPoolExecutor(max_workers=args.threads) as ex:

        futures=[]

        for s,d in tasks:
            futures.append(
                ex.submit(copy_file,s,d,args.resume,args.progress)
            )

        for f in futures:
            f.result()


def verify(src,dst):

    print("Verificando integridade...")

    h1 = sha256sum(src)
    h2 = sha256sum(dst)

    if h1 == h2:
        print("✔ Arquivos idênticos")
    else:
        print("✖ Arquivos diferentes")


def main():

    parser = argparse.ArgumentParser(description="pycp advanced copy tool")

    parser.add_argument("source")
    parser.add_argument("dest")

    parser.add_argument("-p","--progress",action="store_true")
    parser.add_argument("-r","--recursive",action="store_true")
    parser.add_argument("-t","--threads",type=int,default=1)
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--hash",action="store_true")

    args = parser.parse_args()

    src = Path(args.source)
    dst = Path(args.dest)

    if not src.exists():
        print("Arquivo origem não existe")
        sys.exit(1)

    if src.is_dir():

        if not args.recursive:
            print("Use -r para copiar diretórios")
            sys.exit(1)

        copy_directory(src,dst,args)

    else:

        copy_file(src,dst,args.resume,args.progress)

        if args.hash:
            verify(src,dst)


if __name__ == "__main__":
    main()
