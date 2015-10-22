# coding: utf-8

from collections import namedtuple



import pytest
import testing.postgresql


# test targets
import time

from cdic_project import cdic


@pytest.yield_fixture(scope="session", autouse=True)
def pg(request):
    postgresql = testing.postgresql.Postgresql()
    yield postgresql
    postgresql.stop()


@pytest.yield_fixture()
def app(pg, request):
    cdic.app.config.update({
        "SQLALCHEMY_DATABASE_URI": pg.url()
    })
    client = cdic.app.test_client()
    app = cdic.app
    app.testing = True
    db = cdic.db

    with app.app_context():
        db_session = db.create_scoped_session()
        db.create_all()
        db.session.commit()

        ctx = namedtuple("ctx", ["app", "client", "db", "session"])
        yield ctx(app, client, db, db_session)

        db.session.rollback()
        for tbl in reversed(db.metadata.sorted_tables):
            db.engine.execute(tbl.delete())

        db.session.close_all()
