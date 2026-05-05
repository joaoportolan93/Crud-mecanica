-- ============================================================
-- SCHEMA: Sistema de Gestão de Mecânica
-- Engine:  SQLite 3
-- Versão:  1.0
-- Data:    2026-05-02
-- ============================================================
-- IMPORTANTE: Executar na ordem exata (respeita FKs).
-- ============================================================

-- Habilitar foreign keys (obrigatório no SQLite)
PRAGMA foreign_keys = ON;

-- WAL mode: melhor performance para leitura concorrente
PRAGMA journal_mode = WAL;

-- ============================================================
-- 1. CLIENTES
-- ============================================================
-- Suporta PF (pessoa física) e PJ (pessoa jurídica/empresa).
-- "Agrupamento por empresa" = filtrar clientes WHERE tipo = 'PJ'.
-- Endereço em campo único: normalizar em rua/bairro/número seria
-- overengineering para app local de 1 usuário.
-- ============================================================
CREATE TABLE clientes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo        TEXT    NOT NULL DEFAULT 'PF'
                        CHECK (tipo IN ('PF', 'PJ')),
    nome        TEXT    NOT NULL,
    cpf_cnpj    TEXT,                                   -- opcional: muitos clientes não informam
    telefone    TEXT,
    telefone2   TEXT,                                   -- mecânicos sempre pedem um segundo contato
    email       TEXT,
    endereco    TEXT,                                   -- campo livre, sem normalização
    cidade      TEXT,
    uf          TEXT    CHECK (length(uf) = 2 OR uf IS NULL),
    cep         TEXT,
    observacoes TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at  TEXT    DEFAULT NULL                     -- soft delete
);

-- ============================================================
-- 2. VEÍCULOS
-- ============================================================
-- Placa nullable: veículos novos podem não ter emplacamento.
-- ano_fabricacao e ano_modelo separados: padrão brasileiro (ex: 2024/2025).
-- km_atual atualizado a cada visita do veículo à oficina.
-- ============================================================
CREATE TABLE veiculos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id      INTEGER NOT NULL,
    placa           TEXT,                                -- nullable: veículo pode não ter placa
    marca           TEXT,
    modelo          TEXT    NOT NULL,                    -- campo mínimo obrigatório para identificação
    ano_fabricacao  INTEGER,
    ano_modelo      INTEGER,                            -- pode diferir do ano de fabricação
    cor             TEXT,
    chassi          TEXT,                                -- usado em orçamentos de seguradoras
    km_atual        INTEGER DEFAULT 0,
    observacoes     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at      TEXT    DEFAULT NULL,

    FOREIGN KEY (cliente_id)
        REFERENCES clientes (id)
        ON DELETE RESTRICT                              -- não deletar cliente com veículos
        ON UPDATE CASCADE
);

-- ============================================================
-- 3. PEÇAS (Estoque)
-- ============================================================
-- quantidade é REAL: suporta frações (litros de óleo, kg de massa).
-- CHECK(quantidade >= 0): o banco impede estoque negativo.
-- unidade: UN (unidade), PAR, JG (jogo), LT (litro), KG, MT (metro).
-- Decisão debatida: REAL vs INTEGER para valores monetários.
-- Conclusão: REAL com round() no Python — centavos seria overengineering.
-- ============================================================
CREATE TABLE pecas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo          TEXT,                                -- código do fabricante (opcional)
    descricao       TEXT    NOT NULL,
    unidade         TEXT    NOT NULL DEFAULT 'UN'
                            CHECK (unidade IN ('UN', 'PAR', 'JG', 'LT', 'KG', 'MT')),
    quantidade      REAL    NOT NULL DEFAULT 0
                            CHECK (quantidade >= 0),     -- IMPEDE estoque negativo
    preco_custo     REAL    NOT NULL DEFAULT 0
                            CHECK (preco_custo >= 0),
    preco_venda     REAL    NOT NULL DEFAULT 0
                            CHECK (preco_venda >= 0),
    estoque_minimo  REAL    DEFAULT 0,                   -- alerta visual no frontend
    localizacao     TEXT,                                -- ex: "prateleira A3", "gaveta 2"
    observacoes     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at      TEXT    DEFAULT NULL
);

-- ============================================================
-- 4. SERVIÇOS (Catálogo)
-- ============================================================
-- Catálogo para autocomplete na tela de nota.
-- Evita que "troca de óleo" seja digitado de 50 formas diferentes.
-- preco_padrao pode ser sobrescrito na nota (mão de obra varia).
-- ============================================================
CREATE TABLE servicos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    descricao       TEXT    NOT NULL,
    preco_padrao    REAL    NOT NULL DEFAULT 0
                            CHECK (preco_padrao >= 0),
    observacoes     TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at      TEXT    DEFAULT NULL
);

-- ============================================================
-- 5. NOTAS DE SERVIÇO (Cabeçalho da OS)
-- ============================================================
-- Equivale ao bloquinho Tilibra. numero = número sequencial da OS.
-- Subtotais desnormalizados: debatido e aceito para evitar
-- JOIN + SUM em toda listagem de notas. Python recalcula ao salvar.
-- forma_pagamento preenchida no fechamento (pode ser NULL em rascunho).
-- ============================================================
CREATE TABLE notas_servico (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    numero              INTEGER NOT NULL UNIQUE,         -- número sequencial da OS (como bloquinho)
    cliente_id          INTEGER NOT NULL,
    veiculo_id          INTEGER NOT NULL,
    status              TEXT    NOT NULL DEFAULT 'ABERTA'
                                CHECK (status IN ('ABERTA', 'EM_ANDAMENTO', 'CONCLUIDA', 'CANCELADA')),
    data_abertura       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    data_conclusao      TEXT,                            -- preenchido ao concluir/fechar
    km_entrada          INTEGER,                         -- km do veículo na entrada
    subtotal_pecas      REAL    NOT NULL DEFAULT 0,      -- desnormalizado: soma de nota_pecas.valor_total
    subtotal_servicos   REAL    NOT NULL DEFAULT 0,      -- desnormalizado: soma de nota_servicos.valor_total
    desconto            REAL    NOT NULL DEFAULT 0
                                CHECK (desconto >= 0),
    valor_total         REAL    NOT NULL DEFAULT 0,      -- subtotal_pecas + subtotal_servicos - desconto
    forma_pagamento     TEXT    CHECK (
                                    forma_pagamento IN (
                                        'DINHEIRO', 'PIX', 'CARTAO_CREDITO',
                                        'CARTAO_DEBITO', 'BOLETO',
                                        'TRANSFERENCIA', 'OUTRO'
                                    ) OR forma_pagamento IS NULL
                                ),
    observacoes         TEXT,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at          TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    deleted_at          TEXT    DEFAULT NULL,

    FOREIGN KEY (cliente_id)
        REFERENCES clientes (id)
        ON DELETE RESTRICT                               -- não deletar cliente com notas
        ON UPDATE CASCADE,
    FOREIGN KEY (veiculo_id)
        REFERENCES veiculos (id)
        ON DELETE RESTRICT                               -- não deletar veículo com notas
        ON UPDATE CASCADE
);

-- ============================================================
-- 6. NOTA_PECAS (Itens de peça na nota)
-- ============================================================
-- Cada linha = uma peça usada na OS.
-- descricao é SNAPSHOT: congela o nome da peça no momento da emissão.
-- Se o cadastro da peça mudar depois, notas antigas não são afetadas.
-- Sem updated_at: itens não são editados, são deletados e recriados.
-- ============================================================
CREATE TABLE nota_pecas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_id         INTEGER NOT NULL,
    peca_id         INTEGER NOT NULL,
    descricao       TEXT    NOT NULL,                     -- SNAPSHOT do nome da peça
    quantidade      REAL    NOT NULL
                            CHECK (quantidade > 0),      -- sempre positivo
    valor_unitario  REAL    NOT NULL
                            CHECK (valor_unitario >= 0),
    valor_total     REAL    NOT NULL
                            CHECK (valor_total >= 0),    -- quantidade × valor_unitario
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),

    FOREIGN KEY (nota_id)
        REFERENCES notas_servico (id)
        ON DELETE CASCADE                                -- deletar nota remove seus itens
        ON UPDATE CASCADE,
    FOREIGN KEY (peca_id)
        REFERENCES pecas (id)
        ON DELETE RESTRICT                               -- não deletar peça referenciada
        ON UPDATE CASCADE
);

-- ============================================================
-- 7. NOTA_SERVICOS (Itens de serviço na nota)
-- ============================================================
-- servico_id é NULLABLE: permite serviços ad-hoc (sem catálogo).
-- ON DELETE SET NULL: se o serviço do catálogo for removido,
-- o item da nota continua com a descricao (snapshot).
-- ============================================================
CREATE TABLE nota_servicos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    nota_id         INTEGER NOT NULL,
    servico_id      INTEGER,                             -- NULL = serviço ad-hoc (digitado livre)
    descricao       TEXT    NOT NULL,                     -- SNAPSHOT ou descrição livre
    quantidade      REAL    NOT NULL DEFAULT 1
                            CHECK (quantidade > 0),
    valor_unitario  REAL    NOT NULL
                            CHECK (valor_unitario >= 0),
    valor_total     REAL    NOT NULL
                            CHECK (valor_total >= 0),
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),

    FOREIGN KEY (nota_id)
        REFERENCES notas_servico (id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (servico_id)
        REFERENCES servicos (id)
        ON DELETE SET NULL                               -- catálogo removido → item vira ad-hoc
        ON UPDATE CASCADE
);


-- ============================================================
-- ÍNDICES
-- ============================================================

-- Busca por nome do cliente (case-insensitive)
CREATE INDEX idx_clientes_nome
    ON clientes (nome COLLATE NOCASE);

-- CPF/CNPJ único APENAS entre registros ativos (índice parcial)
-- Permite que soft-deleted "libere" o CPF/CNPJ para reutilização
CREATE UNIQUE INDEX idx_clientes_cpf_cnpj_active
    ON clientes (cpf_cnpj)
    WHERE cpf_cnpj IS NOT NULL AND deleted_at IS NULL;

-- Placa única APENAS entre veículos ativos (índice parcial)
CREATE UNIQUE INDEX idx_veiculos_placa_active
    ON veiculos (placa)
    WHERE placa IS NOT NULL AND deleted_at IS NULL;

-- Veículos de um cliente (FK index)
CREATE INDEX idx_veiculos_cliente
    ON veiculos (cliente_id);

-- Busca por modelo (case-insensitive)
CREATE INDEX idx_veiculos_modelo
    ON veiculos (modelo COLLATE NOCASE);

-- Notas por data de abertura (range queries)
CREATE INDEX idx_notas_data_abertura
    ON notas_servico (data_abertura);

-- Notas por cliente (FK index)
CREATE INDEX idx_notas_cliente
    ON notas_servico (cliente_id);

-- Notas por veículo (FK index)
CREATE INDEX idx_notas_veiculo
    ON notas_servico (veiculo_id);

-- Itens por nota (FK indexes para JOINs)
CREATE INDEX idx_nota_pecas_nota
    ON nota_pecas (nota_id);

CREATE INDEX idx_nota_servicos_nota
    ON nota_servicos (nota_id);

-- Peça por código do fabricante
CREATE INDEX idx_pecas_codigo
    ON pecas (codigo)
    WHERE codigo IS NOT NULL;

-- Peça por descrição (case-insensitive)
CREATE INDEX idx_pecas_descricao
    ON pecas (descricao COLLATE NOCASE);


-- ============================================================
-- TRIGGERS: Atualização automática de updated_at
-- ============================================================

CREATE TRIGGER trg_clientes_updated_at
    AFTER UPDATE ON clientes
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at  -- evita loop infinito
BEGIN
    UPDATE clientes
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_veiculos_updated_at
    AFTER UPDATE ON veiculos
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE veiculos
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_pecas_updated_at
    AFTER UPDATE ON pecas
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE pecas
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_servicos_updated_at
    AFTER UPDATE ON servicos
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE servicos
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

CREATE TRIGGER trg_notas_servico_updated_at
    AFTER UPDATE ON notas_servico
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE notas_servico
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

-- ============================================================
-- 8. MOVIMENTAÇÕES DE ESTOQUE (Histórico / Auditoria)
-- ============================================================
-- Registra TODA alteração em pecas.quantidade: saídas automáticas
-- ao fechar nota, entradas manuais e ajustes de inventário.
-- nota_id é nullable: NULL indica operação manual (não vinculada a OS).
-- quantidade_anterior/posterior: snapshot para rastreabilidade total.
-- ============================================================
CREATE TABLE movimentacoes_estoque (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    peca_id                 INTEGER NOT NULL,
    nota_id                 INTEGER,                             -- NULL = operação manual
    tipo                    TEXT    NOT NULL
                                    CHECK (tipo IN ('ENTRADA', 'SAIDA', 'AJUSTE')),
    quantidade              REAL    NOT NULL,                    -- qtd movimentada (sempre positiva)
    quantidade_anterior     REAL    NOT NULL,                    -- snapshot antes
    quantidade_posterior    REAL    NOT NULL,                    -- snapshot depois
    motivo                  TEXT,
    created_at              TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),

    FOREIGN KEY (peca_id)
        REFERENCES pecas (id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    FOREIGN KEY (nota_id)
        REFERENCES notas_servico (id)
        ON DELETE SET NULL                                       -- log sobrevive se nota for removida
        ON UPDATE CASCADE
);

CREATE INDEX idx_mov_estoque_peca ON movimentacoes_estoque (peca_id);
CREATE INDEX idx_mov_estoque_nota ON movimentacoes_estoque (nota_id) WHERE nota_id IS NOT NULL;

-- ============================================================
-- 9. CONFIGURAÇÕES (Estado global chave-valor)
-- ============================================================
-- Armazena parâmetros do sistema: dados da oficina para PDF,
-- número sequencial da OS, versão do schema.
-- ============================================================
CREATE TABLE configuracoes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chave       TEXT    NOT NULL UNIQUE,
    valor       TEXT,
    descricao   TEXT,
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TRIGGER trg_configuracoes_updated_at
    AFTER UPDATE ON configuracoes
    FOR EACH ROW
    WHEN NEW.updated_at = OLD.updated_at
BEGIN
    UPDATE configuracoes
    SET updated_at = datetime('now', 'localtime')
    WHERE id = NEW.id;
END;

-- Registros iniciais obrigatórios
INSERT OR IGNORE INTO configuracoes (chave, valor, descricao) VALUES
    ('proximo_numero_os', '1', 'Próximo número sequencial da OS'),
    ('nome_oficina', '', 'Nome da oficina para impressão em PDF'),
    ('telefone_oficina', '', 'Telefone da oficina para impressão em PDF'),
    ('endereco_oficina', '', 'Endereço da oficina para impressão em PDF'),
    ('cnpj_oficina', '', 'CNPJ da oficina para impressão em PDF'),
    ('schema_version', '1', 'Versão do schema do banco de dados');

-- ============================================================
-- FIM DO SCHEMA
-- ============================================================
-- Total: 9 tabelas, 14 índices, 6 triggers
-- Todas as constraints, FKs, CHECKs e defaults definidos.
-- Pronto para uso com Python + SQLite.
-- ============================================================
