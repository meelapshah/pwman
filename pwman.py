import argparse
from contextlib import contextmanager
import os.path
import pprint
import sqlite3
import sys

from sqlalchemy import Column, Integer, String, create_engine, inspect, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


Session = sessionmaker()
Base = declarative_base()

class Secret(Base):
  __tablename__ = 'pw'
  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String)
  website = Column(String)
  user = Column(String)
  password = Column(String)
  notes = Column(String)

  @classmethod
  def todict(cls, secret):
    cols = inspect(cls).columns.keys()
    return {col: getattr(secret, col, '') for col in cols}

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

  @contextmanager
  def reading(self):
    try:
      yield self._sess
      self._sess.expunge_all()
    except:
      self._sess.rollback()

  def upsert(self, **kwargs):
    self._sess.add(Secret(**kwargs))

  def listall(self):
    return self._sess.query(Secret).all()

  def query(self, q):
    return self._sess.query(Secret).filter(
      or_(
        Secret.name.ilike('%{q}%'.format(q=q)),
        Secret.website.ilike('%{q}%'.format(q=q))
      )
    ).all()



def upsert(args):
  upsert_kwargs = {}
  cols = inspect(Secret).columns.keys()
  for col in cols:
    colval = getattr(args, col, None)
    if colval:
      upsert_kwargs[col] = colval
  sm = SecretManager(args.dbfile)
  with sm, sm.transaction():
    sm.upsert(**upsert_kwargs)

def query(args):
  sm = SecretManager(args.dbfile)
  with sm, sm.reading():
    secrets = sm.query(args.query)  
  secrets = list(map(Secret.todict, secrets))
  pprint.pprint(secrets)

def listall(args):
  sm = SecretManager(args.dbfile)
  with sm, sm.reading():
    secrets = sm.listall()
  secrets = map(Secret.todict, secrets)
  pprint.pprint(secrets)

def main(argv):
  parser = argparse.ArgumentParser('Password Manager')
  parser.add_argument('dbfile')

  subparsers = parser.add_subparsers()

  upsert_parser = subparsers.add_parser('upsert')
  upsert_parser.add_argument('-i', '--id')
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
  list_parser.set_defaults(func=listall)

  cfg = parser.parse_args(argv)
  cfg.func(cfg)

if __name__ == '__main__':
  main(sys.argv[1:])
