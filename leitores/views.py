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
            id_funcionario_logado = request.session.get('funcionario_logado_id')

            if not id_funcionario_logado:
                messages.error(request, 'Sua sessão expirou. Por favor, faça login novamente.')
                return redirect('login')

            # --- VALIDAÇÃO DE CPF ÚNICO (CADASTRO) ---
            with connection.cursor() as cursor:
                cursor.execute("SELECT id_leitor FROM Leitor WHERE cpf = %s", [dados['cpf']])
                if cursor.fetchone():
                    # Se encontrou alguém, adiciona erro no form e para tudo
                    form.add_error('cpf', 'Este CPF já está cadastrado no sistema.')
                    return render(request, 'leitor/cadastrar_leitor.html', {'form': form})
            
            # Se passou da validação, prossegue com o cadastro
            try:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO Leitor (nome, email, telefone, cpf, dt_nascimento, endereco, id_funcionario)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
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
        sql = "SELECT id_leitor AS pk, nome, email, telefone, cpf FROM Leitor"
        params = []

        if query:
            sql += " WHERE nome ILIKE %s OR email ILIKE %s OR cpf ILIKE %s"
            params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
        else:
            sql += " ORDER BY nome"
            
        cursor.execute(sql, params)
        leitores = dictfetchall(cursor)

    return render(request, 'leitor/consultar_leitor.html', {'leitores': leitores})

# UPDATE (Atualizar Leitor)
def atualizar_leitor_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Leitor WHERE id_leitor = %s", [pk])
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Leitor não encontrado.')
            return redirect('leitores:leitor_list')
        
        # CORREÇÃO AQUI: Formatando a data
        data_nascimento_banco = row[6] # Pega o objeto date do banco
        
        # Se existir data, converte para string 'dd/mm/aaaa'
        if data_nascimento_banco:
            data_nascimento_formatada = data_nascimento_banco.strftime('%d/%m/%Y')
        else:
            data_nascimento_formatada = None

        leitor_data = {
            'pk': row[0], 
            'nome': row[1], 
            'cpf': row[2], 
            'telefone': row[3],
            'email': row[4], 
            'data_nascimento': data_nascimento_formatada, # Passamos a string formatada
            'endereco': row[7]
        }

    if request.method == 'POST':
        form = LeitorForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            # --- VALIDAÇÃO DE CPF ÚNICO (ATUALIZAÇÃO) ---
            with connection.cursor() as cursor:
                # Verifica se existe ALGUM OUTRO leitor (id diferente do atual) com esse CPF
                cursor.execute(
                    "SELECT id_leitor FROM Leitor WHERE cpf = %s AND id_leitor != %s", 
                    [dados['cpf'], pk]
                )
                if cursor.fetchone():
                    form.add_error('cpf', 'Este CPF já pertence a outro leitor cadastrado.')
                    # Precisamos renderizar a página novamente com os dados do contexto
                    context = {
                        'form': form,
                        'leitor': leitor_data, # Mantém os dados originais para o cabeçalho/título se necessário
                        'editando': True
                    }
                    return render(request, 'leitor/cadastrar_leitor.html', context)

            # Se passou, atualiza
            try:
                with connection.cursor() as cursor:
                    sql_query = """
                        UPDATE Leitor
                        SET nome=%s, email=%s, telefone=%s, cpf=%s, dt_nascimento=%s, endereco=%s
                        WHERE id_leitor = %s
                    """
                    params = [
                        dados['nome'], dados['email'], dados['telefone'],
                        dados['cpf'], dados['data_nascimento'], dados['endereco'], pk
                    ]
                    cursor.execute(sql_query, params)
                messages.success(request, 'Leitor atualizado com sucesso!')
                return redirect('leitores:leitor_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = LeitorForm(initial=leitor_data)

    context = {
        'form': form,
        'leitor': leitor_data,
        'editando': True
    }
    return render(request, 'leitor/cadastrar_leitor.html', context)

# DELETE (Excluir Leitor)
def excluir_leitor_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [pk])
        leitor = cursor.fetchone()
    
    if not leitor:
        messages.error(request, 'Leitor não encontrado.')
        return redirect('leitores:leitor_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Leitor WHERE id_leitor = %s", [pk])
            
            messages.success(request, f'Leitor "{leitor[0]}" excluído com sucesso.')
            return redirect('leitores:leitor_list')
            
        except IntegrityError:
            # AQUI ESTÁ A MÁGICA: Captura o erro do banco
            messages.error(request, f'Não é possível excluir o leitor "{leitor[0]}", pois ele possui empréstimos vinculados. Realize a devolução ou exclua o histórico primeiro.')
            return redirect('leitores:leitor_list')
            
        except Exception as e:
            # Captura outros erros genéricos
            messages.error(request, f'Ocorreu um erro inesperado ao excluir: {e}')
            return redirect('leitores:leitor_list')

    return render(request, 'leitor/excluir_leitor.html', {'leitor': {'nome': leitor[0]}})