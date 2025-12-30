from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Date,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import date
import os

DB_NAME = "sentinela_alagoas.db"
DATABASE_URL = os.environ.get("DATABASE_URL") or f"sqlite:///{DB_NAME}"
engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
    ),
)
Session = sessionmaker(bind=engine)
Base = declarative_base()


class Funcionario(Base):
    __tablename__ = "historico_folha"

    id = Column(Integer, primary_key=True)
    nome = Column(String, index=True)
    cargo = Column(String, index=True)

    rendimento_liquido = Column(Float)
    total_creditos = Column(Float)
    total_debitos = Column(Float)

    mes_referencia = Column(Integer, index=True)
    ano_referencia = Column(Integer, index=True)

    data_coleta = Column(Date, default=date.today)
    # A URL passa a ser obrigatória e única
    url_origem = Column(String, nullable=False, unique=True)

    # REMOVEMOS a restrição antiga de nomes duplicados
    # Agora a única restrição é não repetir a mesma URL (mesmo contracheque)
    __table_args__ = (UniqueConstraint("url_origem", name="unico_por_url"),)


def init_db():
    Base.metadata.create_all(engine)
    print(f"Banco de dados '{DB_NAME}' pronto (Versão Anti-Homônimos)!")


if __name__ == "__main__":
    init_db()
