"""
Gerenciamento de conexão, inicialização e migrations do banco SQLite.

Decisões de projeto (debatidas pelo painel de especialistas):
  - Singleton: uma única instância de Database por execução do app.
    App desktop local com 1 usuário não precisa de pool de conexões.
  - Row factory: sqlite3.Row para acesso por nome de coluna (row["nome"]).
  - Schema via .sql: lê o arquivo schema_mecanica.sql na primeira execução.
    Verificação de inicialização via sqlite_master (se 'clientes' existe).
  - PRAGMAs: foreign_keys=ON (obrigatório), journal_mode=WAL (performance).
  - Migrations: funções sequenciais (migration_1_para_2, etc.) aplicadas
    automaticamente na inicialização, controladas pela chave
    'schema_version' na tabela configuracoes.
"""

import sqlite3
import logging
import shutil
from datetime import datetime
from pathlib import Path

from constants import DB_PATH, BACKUP_DIR, APP_VERSION, get_asset_path, get_legacy_db_paths

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════
# MIGRATIONS
# ════════════════════════════════════════════════════════════
# Cada migration é uma função que recebe a conexão e executa
# as alterações de schema necessárias. A transação é gerenciada
# externamente por aplicar_migrations() — não faça commit/rollback
# dentro das funções de migration.
#
# Para adicionar uma nova migration:
#   1. Crie a função migration_N_para_N+1(conn)
#   2. Adicione-a à lista MIGRATIONS abaixo
#   3. O sistema aplica automaticamente na próxima execução do app
# ════════════════════════════════════════════════════════════

def _migration_1_para_2(conn: sqlite3.Connection) -> None:
    """Exemplo de migration futura (placeholder).

    Quando for necessário alterar o schema, substitua o 'pass'
    pelo DDL real. Exemplo:

        conn.execute(
            "ALTER TABLE clientes ADD COLUMN inscricao_estadual TEXT"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_clientes_ie "
            "ON clientes(inscricao_estadual) "
            "WHERE inscricao_estadual IS NOT NULL"
        )
    """
    # Nenhuma alteração necessária ainda — schema já está na v1.
    # Descomente e edite quando a v2 for necessária.
    pass


# Lista ordenada de migrations. Cada entrada é (versao_alvo, funcao).
# A versão alvo é o valor que schema_version terá APÓS a migration.
# Importante: manter na ordem correta — são aplicadas sequencialmente.
MIGRATIONS: list[tuple[int, callable]] = [
    # (2, _migration_1_para_2),  # Descomente quando a v2 for criada
]


def aplicar_migrations(conn: sqlite3.Connection) -> None:
    """Aplica todas as migrations pendentes ao banco de dados.

    Lê a chave 'schema_version' da tabela configuracoes, identifica
    quais migrations ainda não foram aplicadas, e executa cada uma
    dentro de sua própria transação. Se uma migration falhar, faz
    rollback APENAS dessa migration e interrompe o processo.

    Args:
        conn: Conexão ativa com o banco SQLite.

    Raises:
        RuntimeError: Se uma migration falhar (banco fica na última
            versão bem-sucedida).
    """
    if not MIGRATIONS:
        return

    # Ler versão atual do schema
    row = conn.execute(
        "SELECT valor FROM configuracoes WHERE chave = 'schema_version'"
    ).fetchone()

    if row is None:
        # Tabela configuracoes existe mas falta a chave — criar
        conn.execute(
            "INSERT INTO configuracoes (chave, valor, descricao) "
            "VALUES ('schema_version', '1', 'Versão do schema do banco de dados')"
        )
        conn.commit()
        versao_atual = 1
    else:
        versao_atual = int(row["valor"])

    logger.info(f"Versão atual do schema: {versao_atual}")

    for versao_alvo, migration_fn in MIGRATIONS:
        if versao_atual >= versao_alvo:
            continue  # Já aplicada

        logger.info(
            f"Aplicando migration: v{versao_atual} → v{versao_alvo} "
            f"({migration_fn.__name__})"
        )

        try:
            # Cada migration roda em sua própria transação
            with conn:
                migration_fn(conn)
                conn.execute(
                    "UPDATE configuracoes SET valor = ? "
                    "WHERE chave = 'schema_version'",
                    (str(versao_alvo),),
                )
            versao_atual = versao_alvo
            logger.info(f"Migration para v{versao_alvo} aplicada com sucesso.")

        except Exception as e:
            # Rollback automático pelo context manager (with conn)
            logger.error(
                f"Falha na migration para v{versao_alvo}: {e}. "
                f"Banco permanece na v{versao_atual}."
            )
            raise RuntimeError(
                f"Migration para v{versao_alvo} falhou: {e}"
            ) from e

    logger.info(f"Schema atualizado para v{versao_atual}.")


# ════════════════════════════════════════════════════════════
# DATABASE (Singleton)
# ════════════════════════════════════════════════════════════

def _migrar_banco_legado_se_necessario(destino: Path) -> None:
    """Procura por um banco mecanica.db antigo em caminhos conhecidos se o atual não existir."""
    if destino.exists() and destino.stat().st_size > 0:
        return

    for legacy_path in get_legacy_db_paths():
        if legacy_path.resolve() == destino.resolve():
            continue
        if legacy_path.exists() and legacy_path.is_file() and legacy_path.stat().st_size > 0:
            logger.info(f"Banco legado encontrado em '{legacy_path}'. Migrando para '{destino}'...")
            try:
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_path, destino)
                logger.info("Migração do banco de dados concluída com sucesso.")
                return
            except Exception as e:
                logger.error(f"Falha ao migrar banco legado de '{legacy_path}': {e}")


def _fazer_backup_rotativo(db_path: Path) -> None:
    """Cria uma cópia de segurança do banco de dados na pasta de backups."""
    if not db_path.exists() or db_path.stat().st_size == 0:
        return

    try:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        nome_backup = f"mecanica_{APP_VERSION.replace('.', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        caminho_backup = BACKUP_DIR / nome_backup
        shutil.copy2(db_path, caminho_backup)
        logger.info(f"Backup automático criado em '{caminho_backup}'.")

        # Manter apenas os 5 backups mais recentes
        backups = sorted(BACKUP_DIR.glob("mecanica_*.db"), key=lambda f: f.stat().st_mtime, reverse=True)
        for backup_antigo in backups[5:]:
            try:
                backup_antigo.unlink()
                logger.info(f"Backup antigo removido: '{backup_antigo.name}'.")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Não foi possível criar o backup automático do banco: {e}")


class Database:
    """Gerencia a conexão única com o banco SQLite."""

    _instance: "Database | None" = None

    def __new__(cls, db_path: str | None = None) -> "Database":
        """Singleton: garante uma única instância do Database."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: str | None = None) -> None:
        if self._initialized:
            return
        self._db_path = Path(db_path) if db_path else DB_PATH
        self._connection: sqlite3.Connection | None = None
        self._initialized = True

    @property
    def connection(self) -> sqlite3.Connection:
        """Retorna a conexão ativa, criando-a se necessário."""
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            _migrar_banco_legado_se_necessario(self._db_path)
            self._connection = sqlite3.connect(str(self._db_path))
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
        return self._connection

    # ── Inicialização do schema ─────────────────────────────

    def _is_initialized(self) -> bool:
        """Verifica se o banco já tem as tabelas criadas."""
        cursor = self.connection.execute(
            "SELECT count(*) FROM sqlite_master "
            "WHERE type='table' AND name='clientes'"
        )
        return cursor.fetchone()[0] > 0

    def initialize(self) -> None:
        """Cria todas as tabelas se o banco estiver vazio e aplica migrations.

        Fluxo:
          1. Tenta migrar banco legado se necessário
          2. Se banco novo → executa schema_mecanica.sql completo
          3. Se banco existente → faz backup preventivo e aplica migrations pendentes
        Seguro para chamar em toda inicialização do app.
        """
        _migrar_banco_legado_se_necessario(self._db_path)

        if not self._is_initialized():
            schema_path = get_asset_path("schema_mecanica.sql")
            if not schema_path.exists():
                raise FileNotFoundError(
                    f"Arquivo de schema não encontrado: {schema_path}"
                )
            with open(schema_path, encoding="utf-8") as f:
                self.connection.executescript(f.read())
            logger.info("Schema inicial criado com sucesso.")
        else:
            # Criar backup preventivo antes de aplicar migrations
            _fazer_backup_rotativo(self._db_path)

        # Aplicar migrations pendentes (se houver)
        aplicar_migrations(self.connection)

    # ── Lifecycle ───────────────────────────────────────────

    def close(self) -> None:
        """Fecha a conexão com o banco."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @classmethod
    def reset(cls) -> None:
        """Reseta o singleton (útil para testes)."""
        if cls._instance:
            cls._instance.close()
        cls._instance = None

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *args) -> None:
        self.close()
