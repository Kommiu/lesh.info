from pathlib import Path
import click
import sqlite3
import pandas as pd
from sqlite3 import Error


def update_table(conn, file_path):
    df = pd.read_csv(file_path)
    table_name = file_path.stem
    df.to_sql(table_name, conn, if_exists='append', index=False)


@click.command()
@click.argument('tables', nargs=-1, type=click.Path(exists=True))
@click.argument('db_path', nargs=1, type=click.Path())
def fill_db(tables, db_path):
    tables = [Path(table) for table in tables]
    if len(tables) == 1:
        if tables[0].is_dir():
            tables = tables[0].iterdir()
    with sqlite3.connect(db_path) as conn:
        for table in tables:
            update_table(conn, table)

if __name__ == '__main__':
    fill_db()
