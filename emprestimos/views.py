from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
from .forms import DevolucaoForm, EmprestimoForm, get_emprestimos_ativos_choices 
from datetime import date, timedelta

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _get_emprestimo_detalhes(pk):
    """
    Busca detalhes de um empréstimo SEM JOIN.
    Faz consultas sequenciais para montar o objeto completo.
    """
    with connection.cursor() as cursor:
        # 1. Busca dados do Empréstimo
        cursor.execute(
            """
            SELECT id_emprestimo, id_exemplar, id_leitor, dt_emprestimo, dt_prevista_devolucao
            FROM Emprestimo
            WHERE id_emprestimo = %s
            """,
            [pk]
        )
        emprestimo_row = cursor.fetchone()
        
        if not emprestimo_row:
            return None

        # Dados base
        emprestimo = {
            'id_emprestimo': emprestimo_row[0],
            'id_exemplar': emprestimo_row[1],
            'id_leitor': emprestimo_row[2],
            'dt_emprestimo': emprestimo_row[3],
            'dt_prevista_devolucao': emprestimo_row[4],
        }

        # 2. Busca dados do Leitor (usando id_leitor)
        cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [emprestimo['id_leitor']])
        leitor_row = cursor.fetchone()
        emprestimo['leitor_nome'] = leitor_row[0] if leitor_row else "Leitor Desconhecido"

        # 3. Busca dados do Exemplar (usando id_exemplar) para pegar o patrimônio e id_livro
        cursor.execute("SELECT numero_patrimonio, id_livro FROM Exemplar WHERE id_exemplar = %s", [emprestimo['id_exemplar']])
        exemplar_row = cursor.fetchone()
        
        if exemplar_row:
            emprestimo['numero_patrimonio'] = exemplar_row[0]
            id_livro = exemplar_row[1]
            
            # 4. Busca dados do Livro (usando id_livro obtido do exemplar)
            cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [id_livro])
            livro_row = cursor.fetchone()
            emprestimo['livro_nome'] = livro_row[0] if livro_row else "Livro Desconhecido"
        else:
            emprestimo['numero_patrimonio'] = "N/A"
            emprestimo['livro_nome'] = "Desconhecido"

        return emprestimo

# --- CRUD DE EMPRÉSTIMO ---

# CREATE (Cadastrar Empréstimo)
def cadastrar_emprestimo_view(request):
    if request.method == 'POST':
        form = EmprestimoForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            
            # Auditoria: Captura qual funcionário está realizando a operação
            id_funcionario_logado = request.session.get('funcionario_logado_id')
            if not id_funcionario_logado:
                return redirect('login')

            try:
                with connection.cursor() as cursor:
                    # Regra de Negócio: Definição de prazos via Python
                    data_hoje = date.today()
                    data_prevista = data_hoje + timedelta(days=14) 
                    
                    # Persistência com Status Inicial
                    cursor.execute(
                        """
                        INSERT INTO Emprestimo 
                        (id_exemplar, id_leitor, id_funcionario, dt_emprestimo, dt_prevista_devolucao, status)
                        VALUES (%s, %s, %s, %s, %s, 'Em Andamento')
                        """,
                        [dados['exemplar'], dados['leitor'], id_funcionario_logado, data_hoje, data_prevista]
                    )
                messages.success(request, 'Empréstimo registrado com sucesso!')
                return redirect('emprestimos:emprestimo_list')
            except Exception as e:
                messages.error(request, f'Erro: {e}')
    else:
        form = EmprestimoForm()
    return render(request, 'emprestimo/cadastrar_emprestimo.html', {'form': form})

# READ (Consultar Empréstimos - SEM JOIN)
def consultar_emprestimos_view(request):
    query = request.GET.get('q', '') 
    
    contexto = { 'query': query }
    
    try:
        with connection.cursor() as cursor:
            # 1. CORREÇÃO DA DATA: Adicionado 'dt_emprestimo' ao SELECT
            sql = """
                SELECT 
                    id_emprestimo AS pk,
                    dt_emprestimo,          
                    dt_prevista_devolucao,
                    status,
                    id_exemplar,
                    id_leitor
                FROM Emprestimo 
                WHERE status = 'Em Andamento'
            """
            
            params = [] 
            
            if query:
                # 2. Filtros complexos via Subqueries (WHERE IN)
                sql += """
                    AND (
                        id_leitor IN (SELECT id_leitor FROM Leitor WHERE nome ILIKE %s)
                        OR 
                        id_exemplar IN (SELECT id_exemplar FROM Exemplar WHERE numero_patrimonio::text ILIKE %s)
                        OR
                        id_exemplar IN (
                            SELECT id_exemplar FROM Exemplar 
                            WHERE id_livro IN (SELECT id_livro FROM Livro WHERE nome ILIKE %s)
                        )
                    )
                """
                params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
            
            # 3. CORREÇÃO DA ORDENAÇÃO: Ordena pelo NOME do livro usando Sub-queries
            sql += """
                ORDER BY (
                    SELECT nome FROM Livro WHERE id_livro = (
                        SELECT id_livro FROM Exemplar WHERE id_exemplar = Emprestimo.id_exemplar
                    )
                ) ASC, dt_prevista_devolucao ASC
            """
            
            cursor.execute(sql, params)
            emprestimos = dictfetchall(cursor)

            # 4. Enriquecimento de dados (Loop para buscar nomes)
            hoje = date.today()
            for emp in emprestimos:
                # Busca Nome Leitor
                cursor.execute("SELECT nome FROM Leitor WHERE id_leitor = %s", [emp['id_leitor']])
                row = cursor.fetchone()
                emp['leitor_nome'] = row[0] if row else "Desconhecido"

                # Busca Dados Exemplar e Livro
                cursor.execute("SELECT numero_patrimonio, id_livro FROM Exemplar WHERE id_exemplar = %s", [emp['id_exemplar']])
                row_ex = cursor.fetchone()
                
                if row_ex:
                    emp['numero_patrimonio'] = row_ex[0]
                    id_livro = row_ex[1]
                    
                    cursor.execute("SELECT nome FROM Livro WHERE id_livro = %s", [id_livro])
                    row_livro = cursor.fetchone()
                    emp['livro_nome'] = row_livro[0] if row_livro else "Desconhecido"
                else:
                    emp['numero_patrimonio'] = "?"
                    emp['livro_nome'] = "?"

                # Lógica de Atraso
                if emp['dt_prevista_devolucao'] < hoje:
                    emp['is_atrasado'] = True
                    emp['dias_atraso'] = (hoje - emp['dt_prevista_devolucao']).days
                else:
                    emp['is_atrasado'] = False
            
            contexto['emprestimos'] = emprestimos
            contexto['total_ativos'] = len(emprestimos)

        return render(request, 'emprestimo/consultar_emprestimos.html', contexto)
    
    except Exception as e:
        messages.error(request, f"Erro ao listar empréstimos: {e}")
        return redirect('home')

# UPDATE (Registrar Devolução)
def registrar_devolucao_view(request):
    contexto = {}
    contexto['lista_emprestimos_ativos'] = get_emprestimos_ativos_choices()

    emprestimo_id = request.GET.get('emprestimo_id') or request.POST.get('emprestimo_id')

    if not emprestimo_id:
        return render(request, 'emprestimo/devolver_emprestimo.html', contexto)

    # Helper function busca todos os dados necessários
    emprestimo = _get_emprestimo_detalhes(emprestimo_id)
    
    if not emprestimo:
        messages.error(request, 'Empréstimo não encontrado ou já devolvido.')
        return redirect('emprestimos:registrar_devolucao')

    contexto['emprestimo'] = emprestimo
    contexto['emprestimo_id_selecionado'] = int(emprestimo_id)

    # Cálculo de Multa (Regra de Negócio)
    # A lógica de "quanto cobrar" fica no código, não no banco.
    data_prevista = emprestimo['dt_prevista_devolucao']
    hoje = date.today()
    dias_atraso = (hoje - data_prevista).days
    is_late = dias_atraso > 0
    
    contexto['is_late'] = is_late
    contexto['dias_atraso'] = dias_atraso if is_late else 0

    if request.method == 'POST':
        form = DevolucaoForm(request.POST, is_late=is_late)

        if form.is_valid():
            dados = form.cleaned_data
            valor_multa = dados.get('multa') or 0.00 
            texto_ocorrencia = dados.get('ocorrencia') or ''

            try:
                # Transação de Encerramento
                # Atualiza Status, Data Real, Multa e Ocorrência em um único comando
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE Emprestimo
                        SET status = 'Devolvido', 
                            dt_devolucao = %s,
                            multa = %s,
                            ocorrencia = %s
                        WHERE id_emprestimo = %s
                        """,
                        [hoje, valor_multa, texto_ocorrencia, emprestimo_id]
                    )
                
                messages.success(request, f"Devolução do livro '{emprestimo['livro_nome']}' registrada com sucesso!")
                return redirect('emprestimos:emprestimo_list')
            except Exception as e:
                messages.error(request, f'Erro no banco de dados: {e}')
        else:
            messages.warning(request, 'Verifique os erros no formulário abaixo.')
    else:
        initial_data = {}
        if is_late:
            multa_calculada = dias_atraso * 1.00
            initial_data['multa'] = f"{multa_calculada:.2f}"
        form = DevolucaoForm(initial=initial_data, is_late=is_late)

    contexto['form'] = form
    return render(request, 'emprestimo/devolver_emprestimo.html', contexto)

# DELETE (Excluir Registro de Empréstimo)
def excluir_emprestimo_view(request, pk):
    # Busca detalhes para mostrar na mensagem de confirmação/erro (usando helper sem JOIN)
    try:
        emprestimo_detalhes = _get_emprestimo_detalhes(pk)
    except Exception:
        messages.error(request, 'Empréstimo não encontrado.')
        return redirect('emprestimos:emprestimo_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM Emprestimo WHERE id_emprestimo = %s", [pk])
            
            messages.success(request, 'Registro de empréstimo excluído com sucesso.')
            return redirect('emprestimos:emprestimo_list')
        except IntegrityError:
            messages.error(request, 'Não é possível excluir este registro.')
            return redirect('emprestimos:emprestimo_list')
        except Exception as e:
            messages.error(request, f'Ocorreu um erro ao excluir: {e}')
            return redirect('emprestimos:emprestimo_list')

    return render(request, 'emprestimo/excluir_emprestimo.html', {'emprestimo': emprestimo_detalhes})