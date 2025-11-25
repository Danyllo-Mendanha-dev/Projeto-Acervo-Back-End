from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
# Importe o formulário do app local, e não do app antigo!
# (Vamos criar este arquivo no Passo 2)
from .forms import FuncionarioForm 

# --- CRUD DE FUNCIONÁRIOS ---
def dictfetchall(cursor):
     columns = [col[0] for col in cursor.description]
     return [dict(zip(columns, row)) for row in cursor.fetchall()]

#Listar usuario
def listar_funcionarios(request): 
    # (Note que esta view não está sendo usada nas suas URLs, 
    # mas corrigi um bug de 'ORDERBY' para 'ORDER BY')
    with connection.cursor() as cursor:
            cursor.execute("SELECT id_funcionario, nome, email, telefone FROM funcionario ORDER BY nome")
            funcionarios = dictfetchall(cursor)
    return render(request, 'funcionario/consultar_funcionario.html', {'funcionarios': funcionarios})

# CREATE (Cadastrar)
def cadastrar_funcionario_view(request):
    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            senha_digitada = dados['senha']
            
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO Funcionario (nome, email, senha, telefone, cpf, dt_nascimento, endereco, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'Ativo')
                    """,
                    [dados['nome'], dados['email'], senha_digitada, dados['telefone'], dados['cpf'], dados['data_nascimento'], dados['endereco']]
                )
            
            messages.success(request, 'Funcionário cadastrado com sucesso!')
            return redirect('funcionarios:funcionario_list') # ATENÇÃO AQUI!
    else:
        form = FuncionarioForm()

    return render(request, 'funcionario/cadastrar_funcionario.html', {'form': form})

# READ (Consultar / Listar)
def consultar_funcionarios_view(request):
    query = request.GET.get('q', '') 
    
    with connection.cursor() as cursor:
        sql = "SELECT id_funcionario, nome, email, telefone FROM Funcionario"
        params = []
        
        if query:
            sql += " WHERE nome ILIKE %s OR email ILIKE %s ORDER BY nome"
            params.extend([f'%{query}%', f'%{query}%'])
        else:
            sql += " ORDER BY nome"

        cursor.execute(sql, params)
        funcionarios = []
        for row in cursor.fetchall():
            funcionarios.append({
                'pk': row[0],
                'nome': row[1],
                'email': row[2],
                'telefone': row[3]
            })

    return render(request, 'funcionario/consultar_funcionario.html', {'funcionarios': funcionarios})

# UPDATE (Atualizar)
def atualizar_funcionario_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM Funcionario WHERE id_funcionario = %s", [pk])
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Funcionário não encontrado.')
            return redirect('funcionarios:funcionario_list') # ATENÇÃO AQUI!
        
        funcionario_data = {
            'pk': row[0], 'nome': row[1], 'telefone': row[2], 
            'endereco': row[3], 'data_nascimento': row[4], 
            'email': row[5], 'cpf': row[6]
        }

    if request.method == 'POST':
        form = FuncionarioForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            try:
                with connection.cursor() as cursor:
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
                    
                    cursor.execute(sql_query, params)

                messages.success(request, 'Funcionário atualizado com sucesso!')
                return redirect('funcionarios:funcionario_list') # ATENÇÃO AQUI!

            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao atualizar: {e}')
    else:
        form = FuncionarioForm(initial=funcionario_data)

    context = {
        'form': form,
        'funcionario': funcionario_data,
        'editando': True
    }
    return render(request, 'funcionario/cadastrar_funcionario.html', context)

# DELETE (Excluir)
def excluir_funcionario_view(request, pk):
    with connection.cursor() as cursor:
        cursor.execute("SELECT nome FROM Funcionario WHERE id_funcionario = %s", [pk])
        funcionario = cursor.fetchone()
    
    if not funcionario:
        messages.error(request, 'Funcionário não encontrado.')
        return redirect('funcionarios:funcionario_list') # ATENÇÃO AQUI!

    if request.method == 'POST':
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM Funcionario WHERE id_funcionario = %s", [pk])
        
        messages.success(request, f'Funcionário "{funcionario[0]}" excluído com sucesso.')
        return redirect('funcionarios:funcionario_list') # ATENÇÃO AQUI!

    return render(request, 'funcionario/excluir_funcionario.html', {'funcionario': {'nome': funcionario[0]}})