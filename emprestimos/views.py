from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, IntegrityError
# Certifique-se de que o import do EmprestimoForm está correto
# (deve ser 'from .forms import EmprestimoForm')
from .forms import DevolucaoForm, EmprestimoForm, get_emprestimos_ativos_choices 
from datetime import date, timedelta

# --- Helper Function ---
def dictfetchall(cursor):
    """Retorna todas as linhas de um cursor como um dict."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def _get_emprestimo_detalhes(pk):
    """Busca detalhes de um empréstimo para as páginas de confirmação."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 
                l.nome AS livro_nome,
                e.numero_patrimonio,
                le.nome AS leitor_nome,
                emp.dt_emprestimo,          -- ADICIONADO
                emp.dt_prevista_devolucao   -- ADICIONADO
            FROM Emprestimo emp
            JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
            JOIN Livro l ON e.id_livro = l.id_livro
            JOIN Leitor le ON emp.id_leitor = le.id_leitor
            WHERE emp.id_emprestimo = %s
            """,
            [pk]
        )
        result = dictfetchall(cursor)
        return result[0] if result else None

# --- CRUD DE EMPRÉSTIMO ---

# CREATE (Cadastrar Empréstimo)
def cadastrar_emprestimo_view(request):
    if request.method == 'POST':
        form = EmprestimoForm(request.POST)
        if form.is_valid():
            dados = form.cleaned_data
            id_funcionario_logado = request.session.get('funcionario_logado_id')
            
            if not id_funcionario_logado:
                messages.error(request, 'Sua sessão expirou. Por favor, faça login novamente.')
                return redirect('login')

            try:
                with connection.cursor() as cursor:
                    data_hoje = date.today()
                    data_prevista = data_hoje + timedelta(days=14) # Regra: 14 dias
                    
                    # CORREÇÃO: Usando os nomes de coluna corretos do seu banco
                    cursor.execute(
                        """
                        INSERT INTO Emprestimo 
                        (id_exemplar, id_leitor, id_funcionario, dt_emprestimo, dt_prevista_devolucao, status)
                        VALUES (%s, %s, %s, %s, %s, 'Em Andamento')
                        """,
                        [dados['exemplar'], dados['leitor'], id_funcionario_logado, data_hoje, data_prevista]
                    )
                    
                    # Como a tabela Exemplar não tem status, não precisamos atualizá-la.
                    # O exemplar fica indisponível automaticamente pela lógica no forms.py.
                    
                messages.success(request, 'Empréstimo registrado com sucesso!')
                return redirect('emprestimos:emprestimo_list')
            except Exception as e:
                messages.error(request, f'Ocorreu um erro ao cadastrar: {e}')
    else:
        form = EmprestimoForm()

    return render(request, 'emprestimo/cadastrar_emprestimo.html', {'form': form})

# READ (Consultar Empréstimos)
def consultar_emprestimos_view(request):
    # Captura o termo de busca, se houver
    query = request.GET.get('q', '') 
    
    contexto = {
        'query': query 
    }
    
    try:
        with connection.cursor() as cursor:
            # SELECT Focado apenas em dados ativos
            sql_base = """
                SELECT 
                    emp.id_emprestimo AS pk,
                    emp.dt_emprestimo,
                    emp.dt_prevista_devolucao,
                    emp.status,
                    l.nome AS livro_nome,
                    e.numero_patrimonio,
                    le.nome AS leitor_nome
                FROM Emprestimo emp
                JOIN Exemplar e ON emp.id_exemplar = e.id_exemplar
                JOIN Livro l ON e.id_livro = l.id_livro
                JOIN Leitor le ON emp.id_leitor = le.id_leitor
                WHERE emp.status = 'Em Andamento'
            """
            
            params = [] 
            
            # Se houver busca, adiciona os filtros
            if query:
                sql_base += " AND (l.nome ILIKE %s OR le.nome ILIKE %s OR e.numero_patrimonio::text ILIKE %s)"
                params.extend([f'%{query}%', f'%{query}%', f'%{query}%'])
            
            # Ordenação: Primeiro os que vencem mais cedo (ou já venceram)
            cursor.execute(sql_base + " ORDER BY emp.dt_prevista_devolucao ASC", params)
            emprestimos = dictfetchall(cursor)

            # Lógica Python para marcar visualmente os atrasados
            hoje = date.today()
            for emp in emprestimos:
                # Se a data prevista for menor que hoje, está atrasado
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
    
    # 1. Sempre carrega o dropdown para o usuário poder selecionar/trocar
    # Usamos a função que movemos para o forms.py para manter organizado
    contexto['lista_emprestimos_ativos'] = get_emprestimos_ativos_choices()

    # Tenta pegar o ID tanto da URL (GET - seleção inicial) quanto do Form (POST - confirmação)
    emprestimo_id = request.GET.get('emprestimo_id') or request.POST.get('emprestimo_id')

    # SE NÃO TIVER ID: É o acesso inicial à página, mostra só o dropdown
    if not emprestimo_id:
        return render(request, 'emprestimo/devolver_emprestimo.html', contexto)

    # SE TIVER ID: Buscamos os detalhes para processar
    emprestimo = _get_emprestimo_detalhes(emprestimo_id)
    
    if not emprestimo:
        messages.error(request, 'Empréstimo não encontrado ou já devolvido.')
        return redirect('emprestimos:registrar_devolucao') # Reseta a tela

    # Passa os dados para o template exibir (Read-Only)
    contexto['emprestimo'] = emprestimo
    contexto['emprestimo_id_selecionado'] = int(emprestimo_id)

    # --- CÁLCULO DE ATRASO ---
    data_prevista = emprestimo['dt_prevista_devolucao']
    hoje = date.today()
    
    # Diferença em dias
    dias_atraso = (hoje - data_prevista).days
    
    # Define a flag booleana para controlar a UI e o Form
    is_late = dias_atraso > 0
    
    contexto['is_late'] = is_late
    contexto['dias_atraso'] = dias_atraso if is_late else 0

    # --- PROCESSAMENTO DO POST (Confirmar Devolução) ---
    if request.method == 'POST':
        # Instancia o form passando 'is_late'. 
        # Se is_late=True, o form torna a multa obrigatória.
        # Se is_late=False, o form ignora a multa.
        form = DevolucaoForm(request.POST, is_late=is_late)

        if form.is_valid():
            dados = form.cleaned_data
            
            # Se o campo estava oculto (não atrasado), multa vem como None ou 0
            valor_multa = dados.get('multa') or 0.00 
            texto_ocorrencia = dados.get('ocorrencia') or ''

            try:
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
    
    # --- PREPARAÇÃO DO GET (Exibir Formulário) ---
    else:
        # Cria os dados iniciais
        initial_data = {}
        
        if is_late:
            # LÓGICA DA MULTA: R$ 1,00 por dia de atraso (Exemplo)
            # Você pode alterar esse multiplicador conforme a regra da biblioteca
            multa_calculada = dias_atraso * 1.00
            initial_data['multa'] = f"{multa_calculada:.2f}"
        
        # Instancia o form com os valores iniciais e a flag de atraso
        form = DevolucaoForm(initial=initial_data, is_late=is_late)

    contexto['form'] = form
    return render(request, 'emprestimo/devolver_emprestimo.html', contexto)

# DELETE (Excluir Registro de Empréstimo)
def excluir_emprestimo_view(request, pk):
    try:
        emprestimo_detalhes = _get_emprestimo_detalhes(pk)
    except Exception:
        messages.error(request, 'Empréstimo não encontrado.')
        return redirect('emprestimos:emprestimo_list')

    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                # O exemplar ficará disponível automaticamente após a exclusão
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
