from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
# Importe o formulário do app local, e não do app antigo!
# (Vamos criar este arquivo no Passo 2)
from .forms import FuncionarioForm 

# --- CRUD DE FUNCIONÁRIOS ---
def dictfetchall(cursor):
     columns = [col[0] for col in cursor.description]
     return [dict(zip(columns, row)) for row in cursor.fetchall()]

#Listar usuario
def listar_funcionarios(request): 
    with connection.cursor() as cursor:
            cursor.execute("SELECT id_funcionario, nome, email, telefone, status FROM funcionario ORDER BY nome")
            funcionarios = dictfetchall(cursor)
    return render(request, 'funcionario/consultar_funcionario.html', {'funcionarios': funcionarios})

# CREATE (Cadastrar)
def cadastrar_funcionario_view(request):
    # Verifica se é uma submissão de formulário
    if request.method == 'POST':
        # Preenche o formulário Django com os dados recebidos
        form = FuncionarioForm(request.POST)
        
        # Valida os dados (tipos, campos obrigatórios, formatos)
        if form.is_valid():
            dados = form.cleaned_data # Dicionário com dados sanitizados
            senha_digitada = dados['senha']
            
            # Abre conexão para comando SQL direto
            with connection.cursor() as cursor:
                # Executa o INSERT usando parâmetros (%s) para segurança
                cursor.execute(
                    """
                    INSERT INTO Funcionario (nome, email, senha, telefone, cpf, dt_nascimento, endereco, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo')
                    """,
                    # Lista de valores na ordem exata das colunas
                    [dados['nome'], dados['email'], senha_digitada, dados['telefone'], dados['cpf'], dados['data_nascimento'], dados['endereco']]
                )
            
            # Feedback visual e redirecionamento para a lista
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('funcionarios:funcionario_list') 
    else:
        # Cria formulário vazio para o primeiro acesso (GET)
        form = FuncionarioForm()

    return render(request, 'funcionario/cadastrar_funcionario.html', {'form': form})

# READ (Consultar / Listar)
def consultar_funcionarios_view(request):
    # Captura o termo de busca da URL (ex: ?q=maria)
    query = request.GET.get('q', '') 
    
    with connection.cursor() as cursor:
        # SQL Base: seleciona colunas específicas
        sql = "SELECT id_funcionario, nome, email, telefone, status FROM Funcionario"
        params = []

        # Construção Dinâmica da Query (Filtro)
        if query:
            # Concatena cláusula WHERE se houver busca.
            # ILIKE: Busca 'case-insensitive' (específico do PostgreSQL).
            sql += " WHERE nome ILIKE %s OR email ILIKE %s ORDER BY nome"
            
            # Adiciona os coringas (%) para a busca parcial
            params.extend([f'%{query}%', f'%{query}%'])
        else:
            # Sem filtro, apenas ordena por nome
            sql += " ORDER BY nome"

        # Executa o SQL (com ou sem filtro) passando os parâmetros seguros
        cursor.execute(sql, params)
        
        # Mapeamento Manual (Tupla -> Dicionário)
        funcionarios = []
        for row in cursor.fetchall():
            # O banco retorna tuplas (índices numéricos), convertemos
            # para dicionário para facilitar o uso no Template HTML.
            funcionarios.append({
                'pk': row[0],
                'nome': row[1],
                'email': row[2],
                'telefone': row[3],
                'status': row[4] 
            })

    return render(request, 'funcionario/consultar_funcionario.html', {'funcionarios': funcionarios})

# UPDATE (Atualizar)
def atualizar_funcionario_view(request, pk):
    # --- ETAPA 1: BUSCAR DADOS ATUAIS ---
    with connection.cursor() as cursor:
        # Busca o funcionário pelo ID para preencher o formulário
        cursor.execute("SELECT * FROM Funcionario WHERE id_funcionario = %s", [pk])
        row = cursor.fetchone()
        
        # Validação se o ID existe
        if not row:
            messages.error(request, 'Funcionário não encontrado.')
            return redirect('funcionarios:funcionario_list')
        
        # Formatação de Data: O banco retorna um objeto 'date', mas o 
        # input HTML precisa de uma string 'dd/mm/aaaa'.
        dt_nascimento_banco = row[4] 
        if dt_nascimento_banco:
            dt_nascimento_formatada = dt_nascimento_banco.strftime('%d/%m/%Y')
        else:
            dt_nascimento_formatada = None

        # Cria dicionário para pré-popular o formulário
        funcionario_data = {
            'pk': row[0], 'nome': row[1], 'telefone': row[2], 
            'endereco': row[3], 'data_nascimento': dt_nascimento_formatada, 
            'email': row[5], 'cpf': row[6]
        }

    # --- ETAPA 2: PROCESSAR A ATUALIZAÇÃO ---
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            try:
                with connection.cursor() as cursor:
                    # Lógica Condicional de SQL:
                    # Se o usuário digitou uma nova senha, incluímos a coluna 'senha' no UPDATE.
                    if dados['senha']:
                        sql_query = """
                            UPDATE Funcionario 
                            SET nome=%s, email=%s, senha=%s, telefone=%s, cpf=%s, dt_nascimento=%s, endereco=%s
                            WHERE id_funcionario = %s
                        """
                        params = [
                            dados['nome'], dados['email'], dados['senha'], dados['telefone'],
                            dados['cpf'], dados['data_nascimento'], dados['endereco'], pk
                        ]
                    # Se a senha está vazia, mantemos a antiga (não incluímos no UPDATE).
                    else:
                        sql_query = """
                            UPDATE Funcionario
                            SET nome=%s, email=%s, telefone=%s, cpf=%s, dt_nascimento=%s, endereco=%s
                            WHERE id_funcionario = %s
                        """
                        params = [
                            dados['nome'], dados['email'], dados['telefone'],
                            dados['cpf'], dados['data_nascimento'], dados['endereco'], pk
                        ]
                    
                    # Executa o comando escolhido
                    cursor.execute(sql_query, params)

                messages.success(request, 'Funcionário atualizado com sucesso!')
                return redirect('funcionarios:funcionario_list')

            except Exception as e:
                # Captura erros do banco (ex: violação de unique no email/cpf)
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        # GET: Renderiza o formulário preenchido com os dados do banco
        form = FuncionarioForm(initial=funcionario_data)

    context = {
        'form': form,
        'funcionario': funcionario_data,
        'editando': True
    }
    return render(request, 'funcionario/cadastrar_funcionario.html', context)

from django.db import IntegrityError

# DELETE (Excluir / Desativar)
def excluir_funcionario_view(request, pk):
    # 1. Busca prévia para confirmação visual
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome, status FROM Funcionario WHERE id_funcionario = %s", [pk])
        funcionario = cursor.fetchone()
    
    if not funcionario:
        messages.error(request, 'Funcionário não encontrado.')
        return redirect('funcionarios:funcionario_list')

    nome_func = funcionario[0]

    if request.method == 'POST':
        try:
            # 2. Tentativa de Exclusão FÍSICA (Hard Delete)
            # Tenta remover o registro definitivamente do banco.
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Funcionario WHERE id_funcionario = %s", [pk])
            
            messages.success(request, f'Funcionário "{nome_func}" excluído permanentemente.')
            return redirect('funcionarios:funcionario_list')

        except IntegrityError:
            # 3. Tratamento de Erro de Banco (Constraint Violation)
            # Se o funcionário tiver vínculos (ex: realizou empréstimos), o banco bloqueia o DELETE
            # e lança um IntegrityError. Capturamos isso aqui.

            # 4. Fallback para Exclusão LÓGICA (Soft Delete)
            # Em vez de apagar, fazemos um UPDATE mudando o status para 'Inativo'.
            # Isso preserva o histórico de ações desse funcionário no sistema.
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE Funcionario SET status = 'Inativo' WHERE id_funcionario = %s", 
                        [pk]
                    )
                
                messages.warning(request, f'O funcionário possui vínculos e foi apenas DESATIVADO (Soft Delete).')
                return redirect('funcionarios:funcionario_list')
            
            except Exception as e:
                messages.error(request, f'Erro ao tentar desativar: {e}')
                return redirect('funcionarios:funcionario_list')

    return render(request, 'funcionario/excluir_funcionario.html', {'funcionario': {'nome': nome_func}})

# --- REATIVAR ---
def reativar_funcionario_view(request, pk):
    # Apenas processa se for um POST (segurança) ou GET se preferir simplificar
    # Vamos fazer via GET para facilitar o link, mas POST seria o ideal semanticamente
    
    try:
        with connection.cursor() as cursor:
            # Verifica se o funcionário existe
            cursor.execute("SELECT nome FROM Funcionario WHERE id_funcionario = %s", [pk])
            row = cursor.fetchone()
            
            # Funcionario nao encontrado
            if not row:
                messages.error(request, 'Funcionário não encontrado.')
                return redirect('funcionarios:funcionario_list')
            
            nome = row[0]

            # Executa a reativação
            cursor.execute(
                "UPDATE Funcionario SET status = 'Ativo' WHERE id_funcionario = %s", 
                [pk]
            )
        
        messages.success(request, f'O funcionário "{nome}" foi reativado com sucesso!')
        
    except Exception as e:
        messages.error(request, f'Erro ao reativar: {e}')

    return redirect('funcionarios:funcionario_list')