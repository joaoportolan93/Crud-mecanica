"""
Exceções customizadas do Sistema de Gestão de Mecânica.

Hierarquia:
  MecanicaError (base)
  ├── NotFoundError
  │   ├── ClienteNotFoundError
  │   ├── VeiculoNotFoundError
  │   ├── PecaNotFoundError
  │   ├── ServicoNotFoundError
  │   └── NotaNotFoundError
  ├── EstoqueInsuficienteError
  ├── NotaStatusError
  ├── NotaSemItensError
  ├── RegistroDuplicadoError
  └── IntegridadeError
"""


class MecanicaError(Exception):
    """Exceção base para todos os erros do sistema."""
    pass


# ── Erros de busca ──────────────────────────────────────────

class NotFoundError(MecanicaError):
    """Registro não encontrado no banco de dados."""
    pass


class ClienteNotFoundError(NotFoundError):
    """Cliente não encontrado ou foi excluído."""
    pass


class VeiculoNotFoundError(NotFoundError):
    """Veículo não encontrado ou foi excluído."""
    pass


class PecaNotFoundError(NotFoundError):
    """Peça não encontrada ou foi excluída."""
    pass


class ServicoNotFoundError(NotFoundError):
    """Serviço do catálogo não encontrado ou foi excluído."""
    pass


class NotaNotFoundError(NotFoundError):
    """Nota de serviço não encontrada ou foi excluída."""
    pass


# ── Erros de regra de negócio ───────────────────────────────

class EstoqueInsuficienteError(MecanicaError):
    """Tentativa de baixar mais peças do que o estoque disponível."""
    pass


class NotaStatusError(MecanicaError):
    """Operação inválida para o status atual da nota."""
    pass


class NotaSemItensError(MecanicaError):
    """Tentativa de fechar nota sem nenhum item (peça ou serviço)."""
    pass


class RegistroDuplicadoError(MecanicaError):
    """Violação de unicidade (ex: CPF/CNPJ ou placa duplicada)."""
    pass


class IntegridadeError(MecanicaError):
    """Violação de integridade referencial ou constraint do banco."""
    pass
