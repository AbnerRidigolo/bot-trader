# 🤖 Bot Trader Automatizado – Binance (SOL/BRL)

Este projeto é um bot de trading automatizado para operar o par **SOL/BRL** na **Binance**, utilizando análise técnica e gestão de risco. Ele foi desenvolvido com foco educacional e demonstra o uso de APIs, indicadores financeiros e automação de operações em tempo real.

---

## ⚙️ Funcionalidades

- 📈 Coleta de dados históricos de candles via API da Binance
- 📊 Cálculo de indicadores técnicos:
  - Médias móveis (SMA)
  - RSI (Índice de Força Relativa)
  - Bandas de Bollinger
- 📥 Estratégia de compra baseada em cruzamento de médias + RSI + bandas
- 📤 Estratégia de venda com take profit, stop loss e sobrecompra
- 💰 Cálculo automático de tamanho da posição com base no risco
- 📜 Logging completo das execuções
- 🔒 Uso de variáveis de ambiente via `.env` para segurança das chaves

---

## 🧠 Estratégia Implementada

### Compra
- Cruzamento de média rápida acima da lenta
- RSI abaixo de 70 (não sobrecomprado)
- Preço próximo da banda inferior de Bollinger

### Venda
- Cruzamento de média rápida abaixo da lenta **ou**
- Alvo de lucro (6%) **ou**
- Stop loss (3%) **ou**
- RSI acima de 70 (sobrecomprado)

---

## 🛠️ Tecnologias Usadas

- Python 3.10+
- [Binance API](https://binance-docs.github.io/apidocs/spot/en/)
- `pandas`, `ta`, `numpy`, `python-dotenv`
- `logging` para registro de execução

---

## 🚀 Como Executar

1. Clone o repositório:

```bash
git clone https://github.com/seu-usuario/bot-trader-binance.git
cd bot-trader-binance
```

2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Crie um arquivo `.env` com suas chaves da Binance:

```
KEY_BINANCE=xxx
SECRET_BINANCE=yyy
```

4. Execute o bot:

```bash
python bot-trader.py
```

---

## ⚠️ Aviso Legal

> Este projeto é **exclusivamente educacional**. Operar com criptomoedas envolve risco. O autor **não se responsabiliza por quaisquer perdas financeiras** resultantes do uso deste código.

**Nunca opere com valores reais sem testar exaustivamente com dados históricos e ambientes simulados.**

---

## 🧾 Arquivos Importantes

- `bot-trader.py` – Código principal do bot
- `.env` – Variáveis de ambiente (NÃO subir no GitHub)
- `trading_bot.log` – Logs de execução
- `requirements.txt` – Dependências do projeto
- `README.md` – Documentação

---

## 📈 Próximas Melhorias (Sugeridas)

- Interface web com Streamlit ou Dash
- Backtest com dados históricos
- Exportação de ordens para CSV
- Curva de capital (equity curve)