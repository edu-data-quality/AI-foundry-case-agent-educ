import threading
from dataclasses import dataclass, field
from itertools import count


@dataclass
class Pendencia:
    id: int
    tipo: str
    motivo: str
    contexto: dict = field(default_factory=dict)
    resolvida: bool = False
    aprovada: bool | None = None


_pendencias: dict[int, Pendencia] = {}
_seq = count(1)
_lock = threading.Lock()


def registrar_pendencia(tipo: str, motivo: str, contexto: dict) -> Pendencia:
    with _lock:
        pendencia = Pendencia(id=next(_seq), tipo=tipo, motivo=motivo, contexto=contexto)
        _pendencias[pendencia.id] = pendencia
    return pendencia


def listar_pendencias() -> list[Pendencia]:
    return list(_pendencias.values())


def obter_pendencia(pendencia_id: int) -> Pendencia | None:
    return _pendencias.get(pendencia_id)


def resolver_pendencia(pendencia_id: int, aprovado: bool) -> Pendencia:
    pendencia = _pendencias.get(pendencia_id)
    if pendencia is None:
        raise KeyError(f"Pendência {pendencia_id} não encontrada")
    pendencia.resolvida = True
    pendencia.aprovada = aprovado
    return pendencia
