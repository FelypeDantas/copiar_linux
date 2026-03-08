#!/usr/bin/env python3

import argparse
import hashlib
import time
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

BUF_SIZE = 1024 * 1024


# -------------------------
# UTIL
# -------------------------

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


# -------------------------
# PROGRESS BAR
# -------------------------

def progress_bar(done,total,start):

    percent = done/total if total else 0
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


# -------------------------
# COPY FILE
# -------------------------

def copy_file(src,dst,progress=False,resume=False):

    src = Path(src)
    dst = Path(dst)

    total = src.stat().st_size
    start = time.time()

    copied = 0
    mode = "wb"

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
                progress_bar(copied,total,start)

    if progress:
        print()


# -------------------------
# DIRECTORY COPY
# -------------------------

def copy_directory(src,dst,threads,progress):

    src = Path(src)
    dst = Path(dst)

    tasks = []

    for path in src.rglob("*"):

        if path.is_file():

            rel = path.relative_to(src)
            target = dst / rel

            target.parent.mkdir(parents=True,exist_ok=True)

            tasks.append((path,target))

    with ThreadPoolExecutor(max_workers=threads) as ex:

        futures = []

        for s,d in tasks:
            futures.append(
                ex.submit(copy_file,s,d,progress)
            )

        for f in futures:
            f.result()


# -------------------------
# SYNC
# -------------------------

def needs_update(src,dst):

    if not dst.exists():
        return True

    s = src.stat()
    d = dst.stat()

    if s.st_size != d.st_size:
        return True

    if int(s.st_mtime) != int(d.st_mtime):
        return True

    return False


def sync_directories(src,dst,threads,progress):

    src = Path(src)
    dst = Path(dst)

    dst.mkdir(parents=True,exist_ok=True)

    tasks=[]

    for path in src.rglob("*"):

        if path.is_file():

            rel = path.relative_to(src)
            target = dst / rel

            if needs_update(path,target):

                target.parent.mkdir(parents=True,exist_ok=True)

                tasks.append((path,target))

    print(f"{len(tasks)} arquivos precisam ser sincronizados")

    with ThreadPoolExecutor(max_workers=threads) as ex:

        futures=[]

        for s,d in tasks:
            futures.append(
                ex.submit(copy_file,s,d,progress)
            )

        for f in futures:
            f.result()


# -------------------------
# VERIFY
# -------------------------

def verify(src,dst):

    print("Verificando integridade...")

    h1 = sha256sum(src)
    h2 = sha256sum(dst)

    if h1 == h2:
        print("✔ arquivos idênticos")
    else:
        print("✖ arquivos diferentes")


# -------------------------
# CLI
# -------------------------

def main():

    parser = argparse.ArgumentParser(
        description="pycp_pro - advanced cross-platform copy tool"
    )

    sub = parser.add_subparsers(dest="command")

    copy_cmd = sub.add_parser("copy")
    copy_cmd.add_argument("source")
    copy_cmd.add_argument("dest")

    sync_cmd = sub.add_parser("sync")
    sync_cmd.add_argument("source")
    sync_cmd.add_argument("dest")

    parser.add_argument("-t","--threads",type=int,default=4)
    parser.add_argument("-p","--progress",action="store_true")
    parser.add_argument("--hash",action="store_true")

    args = parser.parse_args()

    if args.command == "copy":

        src = Path(args.source)
        dst = Path(args.dest)

        if src.is_dir():
            copy_directory(src,dst,args.threads,args.progress)
        else:
            copy_file(src,dst,args.progress)

            if args.hash:
                verify(src,dst)

    elif args.command == "sync":

        sync_directories(
            args.source,
            args.dest,
            args.threads,
            args.progress
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
