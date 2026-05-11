# 🎱 Gestão de Bingo 2026

Um sistema completo, automatizado e intuitivo para o gerenciamento financeiro e controle de vendas de cartelas em eventos de Bingo. Construído com **Python**, **Streamlit** e **SQLite**.

---

## 🌟 Funcionalidades Principais

- **Segurança Integrada**: Proteção de acesso via senha utilizando `st.secrets` e gerenciamento de sessão (`st.session_state`).
- **Suporte a Múltiplos Eventos**: Permite criar e gerenciar diferentes dias de evento (Ex: Sábado, Domingo, Semana 1, etc.) de forma isolada, sem misturar os caixas.
- **Gestão de Vendedores**: 
  - Cadastro global de vendedores (reutilizável entre eventos).
  - Ativação diária de vendedores e controle rigoroso de "Troco Enviado" e "Troco Devolvido".
- **Controle de Rodadas**: 
  - Criação de rodadas por tipo (Geral, Extra, Dinheiro) e valores customizados.
  - Painel de distribuição de cartelas por vendedor (Recebidas, Adicionais, Devolvidas).
  - Lançamento de pagamentos detalhados (Dinheiro, PIX, Santa Ficha, Débito).
  - Validação em tempo real (Falta vs. Sobra) por vendedor.
- **Sangria de Caixa**: Registro de retiradas de dinheiro ao longo do evento para envio ao caixa central.
- **Fechamento Financeiro Automático**:
  - Cálculo inteligente da **Receita Bruta (Teórica)** baseada nas cartelas.
  - Cálculo de **Quebra de Caixa** (identificando se faltou ou sobrou dinheiro no evento).
  - Resumo detalhado por forma de pagamento.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
Certifique-se de ter o Python instalado na sua máquina e as dependências do projeto.

1. **Instale as bibliotecas necessárias:**
   ```bash
   pip install -r requirements.txt
   ```
   *(Dependências principais: `streamlit`, `pandas`)*

2. **Configuração de Senha:**
   Crie uma pasta chamada `.streamlit` na raiz do projeto e adicione um arquivo `secrets.toml` com a sua senha de acesso:
   ```toml
   # .streamlit/secrets.toml
   [auth]
   access_password = "sua_senha_aqui"
   ```

3. **Inicie o Servidor Streamlit:**
   Execute o comando abaixo no terminal:
   ```bash
   streamlit run app.py
   ```

O sistema abrirá automaticamente no seu navegador padrão.

---

## 📂 Estrutura do Banco de Dados
O sistema utiliza o `SQLite` (`bingo_2026.db`) para persistência local sem necessidade de configurações complexas de servidores. O banco é criado automaticamente na primeira execução e contém as tabelas:
- `events`: Histórico de dias/eventos criados.
- `settings`: Configurações de caixa inicial e final atreladas a cada evento.
- `vendors`: Lista global de vendedores.
- `event_vendors`: Status de atividade e troco por vendedor em cada evento.
- `rounds` & `vendor_rounds`: Configuração das rodadas e as vendas efetuadas por cada vendedor na rodada.
- `sangrias`: Retiradas de caixa por evento.

---

## 🛠️ Tecnologias Utilizadas
- **Linguagem**: Python 3.x
- **Interface Web**: Streamlit
- **Manipulação de Dados**: Pandas
- **Banco de Dados**: SQLite (nativo do Python)
