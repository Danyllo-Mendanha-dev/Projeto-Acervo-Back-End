# Em leitores/views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError

# O import do LeitorForm
from .forms import LeitorForm 

# --- Helper Function ---
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# --- CRUD DE LEITOR ---

# Listar
def listar_leitores(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT id_leitor AS pk, nome, email, telefone, cpf FROM Leitor ORDER BY nome")
        leitores = dictfetchall(cursor)
    return render(request, 'leitor/consultar_leitor.html', {'leitores': leitores})

# CREATE (Cadastrar Leitor)
def cadastrar_leitor_view(request):
    if request.method == 'POST':
        form = LeitorForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            # 1. Rastreabilidade (Foreign Key)
            # Recupera quem está logado para salvar no banco quem realizou o cadastro (id_funcionario).
            id_funcionario_logado = request.session.get('funcionario_logado_id')

            if not id_funcionario_logado:
                messages.error(request, 'Sua sessão expirou. Por favor, faça login novamente.')
                return redirect('login')

            # 2. Validação Manual de Unicidade (Regra de Negócio)
            # Faz um SELECT antes do INSERT para verificar se o CPF já existe.
            with connection.cursor() as cursor:
                cursor.execute("SELECT id_leitor FROM Leitor WHERE cpf = %s", [dados['cpf']])
                if cursor.fetchone():
                    # Injeta erro específico no campo CPF do formulário
                    form.add_error('cpf', 'Este CPF já está cadastrado no sistema.')
                    return render(request, 'leitor/cadastrar_leitor.html', {'form': form})
            
            # 3. Persistência com Chave Estrangeira
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO Leitor (nome, email, telefone, cpf, dt_nascimento, endereco, id_funcionario)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        # Lista inclui os dados do formulário E o ID do funcionário da sessão
                        [
                            dados['nome'], dados['email'], dados['telefone'], dados['cpf'], 
                            dados['data_nascimento'], dados['endereco'], id_funcionario_logado
                        ]
                    )
                messages.success(request, 'Leitor cadastrado com sucesso!')
                return redirect('leitores:leitor_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao cadastrar: {e}')
    else:
        form = LeitorForm()

    return render(request, 'leitor/cadastrar_leitor.html', {'form': form})

# READ (Consultar Leitores)
def consultar_leitores_view(request):
    query = request.GET.get('q', '')
    
    with connection.cursor() as cursor:
        # SQL com Alias: 'id_leitor AS pk' padroniza o ID para o template
        sql = "SELECT id_leitor AS pk, nome, email, telefone, cpf FROM Leitor"
        params = []

        if query:
            # Busca Abrangente: Procura o termo em Nome, Email OU CPF ao mesmo tempo
            sql += " WHERE nome ILIKE %s OR email ILIKE %s OR cpf ILIKE %s"
            params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
        else:
            sql += " ORDER BY nome"
            
        cursor.execute(sql, params)
        
        # OTIMIZAÇÃO: Uso de função auxiliar 'dictfetchall'.
        # Ao invés de fazer o loop manual (como no Funcionario), essa função
        # converte as tuplas do banco em dicionários automaticamente.
        leitores = dictfetchall(cursor)

    return render(request, 'leitor/consultar_leitor.html', {'leitores': leitores})

# UPDATE (Atualizar Leitor)
def atualizar_leitor_view(request, pk):
    # --- ETAPA 1: CARREGAMENTO DE DADOS ---
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Leitor WHERE id_leitor = %s", [pk])
        row = cursor.fetchone()
        
        if not row:
            messages.error(request, 'Leitor não encontrado.')
            return redirect('leitores:leitor_list')
        
        # Conversão de Tipo: Data (Objeto do Banco) -> String (Para o HTML)
        # Necessário para que o campo de data apareça preenchido corretamente no formulário ('dd/mm/aaaa')
        data_nascimento_banco = row[6] 
        data_nascimento_formatada = data_nascimento_banco.strftime('%d/%m/%Y') if data_nascimento_banco else None

        leitor_data = {
            'pk': row[0], 'nome': row[1], 'cpf': row[2], 'telefone': row[3],
            'email': row[4], 'data_nascimento': data_nascimento_formatada, 'endereco': row[7]
        }

    # --- ETAPA 2: VALIDAÇÃO E ATUALIZAÇÃO ---
    if request.method == 'POST':
        form = LeitorForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            # VALIDAÇÃO DE CPF (Lógica de Exclusão Mútua)
            # Verifica se o CPF existe em OUTRO registro (id != pk atual).
            # Isso impede duplicidade, mas permite que o próprio usuário mantenha seu CPF atual.
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id_leitor FROM Leitor WHERE cpf = %s AND id_leitor != %s", 
                    [dados['cpf'], pk]
                )
                if cursor.fetchone():
                    form.add_error('cpf', 'Este CPF já pertence a outro leitor cadastrado.')
                    # Recarrega a página mantendo os dados digitados e o contexto de edição
                    return render(request, 'leitor/cadastrar_leitor.html', {
                        'form': form, 'leitor': leitor_data, 'editando': True
                    })

            # Execução do UPDATE
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE Leitor
                        SET nome=%s, email=%s, telefone=%s, cpf=%s, dt_nascimento=%s, endereco=%s
                        WHERE id_leitor = %s
                        """,
                        [
                            dados['nome'], dados['email'], dados['telefone'],
                            dados['cpf'], dados['data_nascimento'], dados['endereco'], pk
                        ]
                    )
                messages.success(request, 'Leitor atualizado com sucesso!')
                return redirect('leitores:leitor_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        # GET: Renderiza o formulário populado com os dados formatados
        form = LeitorForm(initial=leitor_data)

    context = {
        'form': form,
        'leitor': leitor_data,
        'editando': True
    }
    return render(request, 'leitor/cadastrar_leitor.html', context)

# DELETE (Excluir Leitor)
def excluir_leitor_view(request, pk):
    # 1. Busca prévia para confirmação e validação de existência
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [pk])
        leitor = cursor.fetchone()
    
    if not leitor:
        messages.error(request, 'Leitor não encontrado.')
        return redirect('leitores:leitor_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # 2. Tentativa de Exclusão Física (Hard Delete)
                # Tenta apagar o registro definitivamente.
                cursor.execute("DELETE FROM Leitor WHERE id_leitor = %s", [pk])
            
            messages.success(request, f'Leitor "{leitor[0]}" excluído com sucesso.')
            return redirect('leitores:leitor_list')
            
        except IntegrityError:
            # 3. Proteção do Banco de Dados (Foreign Key Constraint)
            # Se o leitor tiver empréstimos, o banco BLOQUEIA a exclusão e lança este erro.
            # Aqui traduzimos o erro técnico para uma mensagem útil ao usuário.
            messages.error(request, f'Não é possível excluir o leitor "{leitor[0]}", pois ele possui empréstimos vinculados. Realize a devolução ou exclua o histórico primeiro.')
            return redirect('leitores:leitor_list')
            
        except Exception as e:
            # Captura erros genéricos de conexão ou sintaxe
            messages.error(request, f'Ocorreu um erro inesperado ao excluir: {e}')
            return redirect('leitores:leitor_list')

    # Renderiza a tela de confirmação (GET)
    return render(request, 'leitor/excluir_leitor.html', {'leitor': {'nome': leitor[0]}})