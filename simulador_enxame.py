import concurrent.futures
from agno.agent import Agent
from agno.models.groq import Groq

def consultar_persona(agente, prompt):
    """Função auxiliar para rodar a IA em paralelo"""
    try:
        resposta = agente.run(prompt)
        if resposta and resposta.content:
            return resposta.content
        return "O cliente ficou em silêncio (Erro de resposta vazia)."
    except Exception as e:
        return f"Erro ao consultar cliente: {e}"

def executar_simulacao_enxame(ticket_atual, novo_ticket):
    """
    Orquestra o Mini-Enxame: 3 clientes reagem ao novo preço e o CFO avalia.
    """
    # 1. Definindo o modelo base para os clientes (Modelo hiper-rápido da Groq)
    modelo_base = Groq(id="llama-3.1-8b-instant")

    cliente_pechincha = Agent(
        model=modelo_base,
        instructions=["Você é um cliente rigoroso com as finanças. Só compra se tiver vantagem financeira. Odeia aumentos de preço injustificados. Responda em primeira pessoa, de forma curta e direta (1 parágrafo)."]
    )

    cliente_fiel = Agent(
        model=modelo_base,
        instructions=["Você é um cliente fiel à marca. O preço não é o principal para você, você busca qualidade e confiança. Você aceita pagar mais caro se a qualidade se mantiver. Responda em primeira pessoa, de forma curta e direta (1 parágrafo)."]
    )

    cliente_impulsivo = Agent(
        model=modelo_base,
        instructions=["Você compra por impulso e emoção. Se o produto parece bom, exclusivo ou urgente, você paga o preço sem pensar muito. Responda em primeira pessoa, de forma curta (1 parágrafo)."]
    )

    # 2. O Estímulo (A Pergunta que todos vão ouvir)
    pergunta = f"Você costuma comprar nossos produtos por cerca de R$ {ticket_atual:.2f}. Estamos simulando um ajuste no nosso preço médio para R$ {novo_ticket:.2f}. Qual a sua reação honesta? Você continua comprando de nós?"

    agentes = [cliente_pechincha, cliente_fiel, cliente_impulsivo]
    
    # 3. Execução Paralela (A mágica do tempo)
    respostas = []
    # Dispara as chamadas simultaneamente para a API do Groq
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futuros = [executor.submit(consultar_persona, agente, pergunta) for agente in agentes]
        for futuro in concurrent.futures.as_completed(futuros):
            respostas.append(futuro.result())

    # 4. O Juiz (Nosso CFO com o modelo mais pesado e analítico)
    cfo_juiz = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        instructions=[
            "Você é o Diretor Financeiro (CFO) do AxiQuant SaaS.",
            "Sua tarefa é ler a transcrição de um Focus Group (3 clientes simulados) reagindo a uma proposta de aumento de preço.",
            "Faça uma síntese do sentimento do mercado e dê um veredito claro: O aumento de preço vale o risco da evasão de clientes?",
            "Use formatação Markdown limpa, com bullet points para os principais riscos."
        ]
    )

    prompt_cfo = f"""
    Cenário Simulado: Aumento de ticket de R$ {ticket_atual:.2f} para R$ {novo_ticket:.2f}.
    
    Respostas brutas do Focus Group:
    - Cliente A: {respostas[0]}
    - Cliente B: {respostas[1]}
    - Cliente C: {respostas[2]}
    
    Sintetize essas reações e me dê o laudo final sobre o risco dessa precificação.
    """
    
    try:
        veredito = cfo_juiz.run(prompt_cfo)
        texto_final = veredito.content if veredito and veredito.content else "Não foi possível extrair o veredito do CFO."
    except Exception as e:
        texto_final = f"Erro na análise do CFO: {e}"
    
    return {
        "reacoes": respostas,
        "veredito_cfo": texto_final
    }