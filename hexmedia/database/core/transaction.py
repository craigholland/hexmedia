# hexmedia/common/db/transaction.py
from contextlib import contextmanager
from sqlalchemy.orm import Session

@contextmanager
def transactional(db: Session):
    with db.begin():
        yield db
