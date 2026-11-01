"""Entrypoint de orquestração da triagem de solicitações.

Uso:
    python agente_triagem.py                 # demo com casos de exemplo
    python agente_triagem.py -i              # modo interativo
    python agente_triagem.py --aluno ALU-99999 --texto "preciso da 2a via do boleto"
    python agente_triagem.py --pendentes     # lista pendências humanas
    python agente_triagem.py --aprovar 1 --negado   # decide ação sensível
"""
import argparse
import json

from dotenv import load_dotenv

from triagem import human_review
from triagem.workflow import decidir_acao_sensivel, processar

load_dotenv()

CASOS_DEMO = [
    ("ALU-12345", "Gostaria da segunda via do boleto da mensalidade deste mês, urgente."),
    ("ALU-99999", "Preciso do meu histórico escolar e das notas do semestre."),
    ("ALU-88888", "Não sei bem o que aconteceu, me ajuda com isso por favor."),
    ("ALU-00000-ERRO", "Quero a segunda via do boleto."),
]


def _imprimir(resultado) -> None:
    print(json.dumps(resultado.model_dump(exclude_none=True), ensure_ascii=False, indent=2))


def modo_interativo() -> None:
    print("Modo interativo (Ctrl+C para sair).")
    while True:
        aluno_id = input("aluno_id: ").strip()
        texto = input("texto: ").strip()
        _imprimir(processar(texto, aluno_id))


def modo_demo() -> None:
    for aluno_id, texto in CASOS_DEMO:
        print(f"\n=== {aluno_id} :: {texto}")
        _imprimir(processar(texto, aluno_id))

    for pendencia in human_review.listar_pendencias():
        print(f"\n[pendencia {pendencia.id}] {pendencia.tipo}: {pendencia.motivo}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Orquestrador de triagem de solicitações")
    parser.add_argument("--aluno", dest="aluno_id", help="ID do aluno")
    parser.add_argument("--texto", help="Texto da solicitação")
    parser.add_argument("-i", "--interativo", action="store_true", help="Modo interativo")
    parser.add_argument("--pendentes", action="store_true", help="Lista pendências humanas")
    parser.add_argument("--aprovar", type=int, metavar="ID", help="Aprova ação sensível pendente")
    parser.add_argument("--negar", type=int, metavar="ID", help="Nega ação sensível pendente")
    args = parser.parse_args()

    if args.pendentes:
        for p in human_review.listar_pendencias():
            print(json.dumps({"id": p.id, "tipo": p.tipo, "motivo": p.motivo, "resolvida": p.resolvida}, ensure_ascii=False))
        return

    if args.aprovar is not None or args.negar is not None:
        pendencia_id = args.aprovar if args.aprovar is not None else args.negar
        _imprimir(decidir_acao_sensivel(pendencia_id, args.aprovar is not None))
        return

    if args.aluno_id and args.texto:
        _imprimir(processar(args.texto, args.aluno_id))
        return

    if args.interativo:
        modo_interativo()
        return

    modo_demo()


if __name__ == "__main__":
    main()
