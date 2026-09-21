"""Consistent SQLite backup, including committed WAL data. Keep output private."""
import argparse
from pathlib import Path
import sqlite3


def backup(source, destination):
    source, destination = Path(source), Path(destination)
    if not source.is_file():
        raise ValueError('Source database does not exist')
    if destination.exists():
        raise ValueError('Refusing to overwrite an existing backup')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup integrity check failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    backup(args.db, args.out)
    print('Backup completed; protect it with the same access controls as the source database.')


if __name__ == '__main__':
    main()
