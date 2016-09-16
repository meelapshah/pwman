import argparse
from contextlib import contextmanager
import os.path
from sqlalchemy import Column, String, create_engine, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import sqlite3
import sys


Session = sessionmaker()
Base = declarative_base()

class Secret(Base):
  __tablename__ = 'pw'
  name = Column(String, primary_key=True)
  website = Column(String)
  user = Column(String)
  password = Column(String)
  notes = Column(String)


class SecretManager(object):
  def __init__(self, dbfile):
    self.dbfile = os.path.abspath(dbfile)
    self.engine = create_engine('sqlite:///{dbfile}'.format(dbfile=dbfile))

  def __enter__(self):
    self._conn = self.engine.connect()
    self._sess = Session(bind=self._conn)
    return self

  def __exit__(self, *exc):
    self._sess.close()
    self._conn.close()

  @contextmanager
  def transaction(self):
    try:
      yield self._sess
      self._sess.commit()
    except:
      self._sess.rollback()

  def upsert(self, **kwargs):
    self._sess.add(Secret(**kwargs))


def upsert(args):
  upsert_kwargs = {}
  columns = inspect(Secret).columns.keys()
  for col in columns:
    colval = getattr(args, col, None)
    if colval:
      upsert_kwargs[col] = colval
  sm = SecretManager(args.dbfile)
  with sm, sm.transaction():
    sm.upsert(**upsert_kwargs)

def query(args):
  pass

def listall(args):
  pass

def main(argv):
  parser = argparse.ArgumentParser('Password Manager')
  parser.add_argument('dbfile')

  subparsers = parser.add_subparsers()

  upsert_parser = subparsers.add_parser('upsert')
  upsert_parser.add_argument('-n', '--name')
  upsert_parser.add_argument('-w', '--website')
  upsert_parser.add_argument('-u', '--user')
  upsert_parser.add_argument('-p', '--password')
  upsert_parser.add_argument('-t', '--note')
  upsert_parser.set_defaults(func=upsert)

  query_parser = subparsers.add_parser('query')
  query_parser.add_argument('query')
  query_parser.set_defaults(func=query)

  list_parser = subparsers.add_parser('list')
  list_parser.set_defaults(func=list)

  cfg = parser.parse_args(argv)
  cfg.func(cfg)

if __name__ == '__main__':
  main(sys.argv[1:])
