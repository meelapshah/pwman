#!/usr/bin/env python3

import argparse
from contextlib import contextmanager
import os.path
import sqlite3
import sys
from textwrap import wrap

from sqlalchemy import Column, Integer, String, create_engine, inspect, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from terminaltables import SingleTable


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
    except e:
      print(e)
      self._sess.rollback()

  @contextmanager
  def reading(self):
    try:
      yield self._sess
      self._sess.expunge_all()
    except e:
      print(e)
      self._sess.rollback()

  def upsert(self, **kwargs):
    secret_id = kwargs.pop('id', None)
    if secret_id:
      s = self._sess.query(Secret).get(secret_id)
      for k, v in kwargs.items():
        setattr(s, k, v)
      self._sess.merge(s)
    else:
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

def print_secrets(secrets):
  data = [ ["id", "name", "website", "user", "password", "notes" ] ]
  for s in secrets:
    data = Secret.todict(s).items()
    table = SingleTable(data)
    table.inner_heading_row_border = False
    print(table.table)

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
  print_secrets(secrets)

def listall(args):
  sm = SecretManager(args.dbfile)
  with sm, sm.reading():
    secrets = sm.listall()
  print_secrets(secrets)

def main(argv=sys.argv[1:]):
  parser = argparse.ArgumentParser('Password Manager')
  parser.add_argument('-d', '--dbfile', default=os.path.expanduser('~/encrypted/pw.sqlite'))

  subparsers = parser.add_subparsers()

  upsert_parser = subparsers.add_parser('upsert', aliases=['u'])
  upsert_parser.add_argument('-i', '--id')
  upsert_parser.add_argument('-n', '--name')
  upsert_parser.add_argument('-w', '--website')
  upsert_parser.add_argument('-u', '--user')
  upsert_parser.add_argument('-p', '--password')
  upsert_parser.add_argument('-t', '--notes')
  upsert_parser.set_defaults(func=upsert)

  query_parser = subparsers.add_parser('query', aliases=['q'])
  query_parser.add_argument('query')
  query_parser.set_defaults(func=query)

  list_parser = subparsers.add_parser('list', aliases=['l'])
  list_parser.set_defaults(func=listall)

  cfg = parser.parse_args(argv)
  if not os.path.exists(cfg.dbfile):
    print('db file does not exist')
    sys.exit(-1)
  cfg.func(cfg)

if __name__ == '__main__':
  main(sys.argv[1:])
