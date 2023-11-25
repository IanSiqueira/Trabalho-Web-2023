# Importando as bibliotecas necessárias
from fastapi import FastAPI, HTTPException, Path, Depends
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlmodel import SQLModel, create_session
from datetime import datetime
from typing import List

# Configuração do banco de dados
DATABASE_URL = "postgresql://ian:123@localhost/postgres_trabalhoAPI"
engine = create_engine(DATABASE_URL)
SQLModel.metadata.create_all(engine)

# Definindo modelos SQLModel
class Prova(SQLModel, table=True):
    id: int = None
    descricao: str
    data_realizacao: datetime
    q1: str
    q2: str
    q3: str
    q4: str
    q5: str
    q6: str
    q7: str
    q8: str
    q9: str
    q10: str

class ResultadoProva(SQLModel, table=True):
    id: int = None
    prova_id: int
    nome_aluno: str
    q1: str
    q2: str
    q3: str
    q4: str
    q5: str
    q6: str
    q7: str
    q8: str
    q9: str
    q10: str
    nota_final: float = None

# Inicializando o aplicativo FastAPI
app = FastAPI()

# Dependência para obter a sessão do banco de dados
def get_session():
    with create_session(engine) as session:
        yield session

# Rota para criar uma prova
@app.post("/provas", response_model=Prova)
def criar_prova(prova: Prova, session: Session = Depends(get_session)):
    # Verifica se a prova já existe
    prova_existente = session.execute(
        select(Prova).where(
            (Prova.descricao == prova.descricao) &
            (Prova.data_realizacao == prova.data_realizacao)
        )
    ).first()
    if prova_existente:
        raise HTTPException(status_code=400, detail="Prova já cadastrada.")

    session.add(prova)
    session.commit()
    session.refresh(prova)
    return prova

# Rota para criar um resultado de prova
@app.post("/resultados_provas", response_model=ResultadoProva)
def criar_resultado_prova(resultado: ResultadoProva, session: Session = Depends(get_session)):
    # Verifica se a prova existe
    prova_existente = session.execute(select(Prova).where(Prova.id == resultado.prova_id)).first()
    if not prova_existente:
        raise HTTPException(status_code=404, detail="Prova não cadastrada.")

    # Validação das alternativas fornecidas pelo aluno
    alternativas_validas = {'a', 'b', 'c', 'd'}
    for i in range(1, 11):
        if getattr(resultado, f'q{i}') not in alternativas_validas:
            raise HTTPException(status_code=400, detail=f"Alternativa inválida para a questão {i}.")

    # Corrige automaticamente e calcula a nota final
    nota_final = sum(1 for i in range(1, 11) if getattr(prova_existente, f'q{i}') == getattr(resultado, f'q{i}'))
    resultado.nota_final = nota_final

    session.add(resultado)
    session.commit()
    session.refresh(resultado)
    return resultado

# Rota para obter os resultados de uma prova
@app.get("/resultados_provas/{prova_id}", response_model=List[ResultadoProva])
def obter_resultados_prova(prova_id: int = Path(..., title="ID da Prova"), session: Session = Depends(get_session)):
    prova = session.execute(select(Prova).where(Prova.id == prova_id)).first()
    if not prova:
        raise HTTPException(status_code=404, detail="Prova não encontrada.")

    resultados = session.execute(select(ResultadoProva).where(ResultadoProva.prova_id == prova_id)).all()

    # Processa os resultados para retornar a descrição da prova, data de aplicação e dados por aluno
    dados_prova = {
        "descricao": prova.descricao,
        "data_aplicacao": prova.data_realizacao,
        "resultados_alunos": []
    }

    for resultado in resultados:
        resultado_final = "aprovado" if resultado.nota_final >= 7 else \
                          "recuperacao" if 5 <= resultado.nota_final < 7 else "reprovado"
        dados_aluno = {
            "nome_aluno": resultado.nome_aluno,
            "nota_final": resultado.nota_final,
            "resultado_final": resultado_final
        }
        dados_prova["resultados_alunos"].append(dados_aluno)

    return dados_prova

# Rota para alterar as respostas de uma prova já realizada
@app.put("/resultados_provas/{id}/alterar_respostas", response_model=ResultadoProva)
def alterar_respostas_prova(
    id: int = Path(..., title="ID do Resultado Prova"),
    resultado: ResultadoProva,  # Adiciona o modelo ResultadoProva como parâmetro
    session: Session = Depends(get_session)
):
    resultado_existente = session.get(ResultadoProva, id)
    if not resultado_existente:
        raise HTTPException(status_code=404, detail="Resultado Prova não encontrado.")

    # Validação das alternativas fornecidas na alteração
    alternativas_validas = {'a', 'b', 'c', 'd'}
    for i in range(1, 11):
        if getattr(resultado, f'q{i}') not in alternativas_validas:
            raise HTTPException(status_code=400, detail=f"Alternativa inválida para a questão {i}.")

    # Atualiza as respostas do resultado da prova
    for i in range(1, 11):
        setattr(resultado_existente, f'q{i}', getattr(resultado, f'q{i}'))

    # Recalcula a nota final
    nota_final = sum(
        1 for i in range(1, 11) if getattr(resultado_existente.prova, f'q{i}') == getattr(resultado, f'q{i}')
    )
    resultado_existente.nota_final = nota_final

    session.commit()
    session.refresh(resultado_existente)
    return resultado_existente
