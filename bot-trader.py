import pandas as pd
import os 
import time 
import logging
from datetime import datetime
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
import ta  # Biblioteca para indicadores técnicos
import numpy as np
from typing import Tuple, Dict, Any

# Configuração inicial
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.api_key = os.getenv("KEY_BINANCE")
        self.secret_key = os.getenv("SECRET_BINANCE")
        self.client = Client(self.api_key, self.secret_key)
        
        # Configurações do bot
        self.symbol = "SOLBRL"
        self.base_asset = "SOL"
        self.quote_asset = "BRL"
        self.timeframe = Client.KLINE_INTERVAL_1HOUR
        self.risk_per_trade = 0.01  # 1% do capital por operação
        self.fast_ma_period = 7
        self.slow_ma_period = 40
        self.rsi_period = 14
        self.stop_loss_pct = 0.03  # 3%
        self.take_profit_pct = 0.06  # 6%
        
        # Estado do bot
        self.position = False
        self.entry_price = 0
        self.current_order = None
        self.equity = []
        
        # Verifica conexão
        try:
            self.client.get_account()
            logger.info("Conexão com Binance estabelecida com sucesso")
        except Exception as e:
            logger.error(f"Erro ao conectar com Binance: {e}")
            raise

    def get_candles(self, limit: int = 1000) -> pd.DataFrame:
        """Obtém dados históricos de candles"""
        try:
            candles = self.client.get_klines(
                symbol=self.symbol,
                interval=self.timeframe,
                limit=limit
            )
            
            df = pd.DataFrame(candles, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base", "taker_buy_quote", "ignore"
            ])
            
            # Convertendo tipos e timezone
            numeric_cols = ["open", "high", "low", "close", "volume"]
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, axis=1)
            df["close_time"] = pd.to_datetime(df["close_time"], unit="ms").dt.tz_localize("UTC").dt.tz_convert("America/Sao_Paulo")
            
            return df[["close_time", "open", "high", "low", "close", "volume"]]
            
        except Exception as e:
            logger.error(f"Erro ao obter candles: {e}")
            raise

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula indicadores técnicos"""
        try:
            # Médias móveis
            df['fast_ma'] = ta.trend.sma_indicator(df['close'], window=self.fast_ma_period)
            df['slow_ma'] = ta.trend.sma_indicator(df['close'], window=self.slow_ma_period)
            
            # RSI
            df['rsi'] = ta.momentum.rsi(df['close'], window=self.rsi_period)
            
            # Bollinger Bands
            indicator_bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
            df['bb_upper'] = indicator_bb.bollinger_hband()
            df['bb_middle'] = indicator_bb.bollinger_mavg()
            df['bb_lower'] = indicator_bb.bollinger_lband()
            
            return df
            
        except Exception as e:
            logger.error(f"Erro ao calcular indicadores: {e}")
            raise

    def get_account_balance(self, asset: str) -> float:
        """Obtém saldo disponível de um ativo"""
        try:
            account = self.client.get_account()
            for balance in account['balances']:
                if balance['asset'] == asset:
                    return float(balance['free'])
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao obter saldo: {e}")
            raise

    def calculate_position_size(self, last_price: float) -> float:
        """Calcula tamanho da posição baseado no risco"""
        try:
            balance = self.get_account_balance(self.quote_asset)
            risk_amount = balance * self.risk_per_trade
            stop_loss_amount = last_price * self.stop_loss_pct
            position_size = risk_amount / stop_loss_amount
            
            # Obtém informações do símbolo para quantidade mínima
            symbol_info = self.client.get_symbol_info(self.symbol)
            lot_size_filter = next(f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE')
            min_qty = float(lot_size_filter['minQty'])
            step_size = float(lot_size_filter['stepSize'])
            
            # Ajusta para o step size permitido
            position_size = max(min_qty, position_size)
            position_size = round(position_size / step_size) * step_size
            
            logger.info(f"Tamanho da posição calculado: {position_size}")
            return position_size
            
        except Exception as e:
            logger.error(f"Erro ao calcular tamanho da posição: {e}")
            raise

    def check_buy_conditions(self, df: pd.DataFrame) -> bool:
        """Verifica condições para entrada em compra"""
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Condição básica: média rápida cruzou acima da lenta
        ma_cross = (last_row['fast_ma'] > last_row['slow_ma']) and (prev_row['fast_ma'] <= prev_row['slow_ma'])
        
        # Confirmação com RSI não sobrecomprado
        rsi_ok = last_row['rsi'] < 70
        
        # Preço próximo à banda inferior de Bollinger
        bb_ok = last_row['close'] < last_row['bb_lower']
        
        return ma_cross and rsi_ok and bb_ok

    def check_sell_conditions(self, df: pd.DataFrame) -> bool:
        """Verifica condições para venda"""
        if not self.position:
            return False
            
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Condição básica: média rápida cruzou abaixo da lenta
        ma_cross = (last_row['fast_ma'] < last_row['slow_ma']) and (prev_row['fast_ma'] >= prev_row['slow_ma'])
        
        # Stop-loss ou take-profit
        current_price = last_row['close']
        stop_loss_trigger = current_price <= self.entry_price * (1 - self.stop_loss_pct)
        take_profit_trigger = current_price >= self.entry_price * (1 + self.take_profit_pct)
        
        # Confirmação com RSI sobrecomprado
        rsi_ok = last_row['rsi'] > 70
        
        return ma_cross or stop_loss_trigger or take_profit_trigger or rsi_ok

    def place_order(self, side: str, quantity: float) -> Dict[str, Any]:
        """Executa uma ordem na exchange"""
        try:
            order_type = ORDER_TYPE_MARKET
            order = self.client.create_order(
                symbol=self.symbol,
                side=side,
                type=order_type,
                quantity=quantity
            )
            
            logger.info(f"Ordem {side} executada: {order}")
            return order
            
        except Exception as e:
            logger.error(f"Erro ao executar ordem {side}: {e}")
            raise

    def run_strategy(self):
        """Executa a estratégia principal"""
        try:
            logger.info("Iniciando ciclo de trading...")
            
            # Obtém dados e calcula indicadores
            df = self.get_candles()
            df = self.calculate_indicators(df)
            
            # Verifica condições de compra/venda
            if not self.position and self.check_buy_conditions(df):
                last_price = df.iloc[-1]['close']
                position_size = self.calculate_position_size(last_price)
                
                if position_size > 0:
                    order = self.place_order(SIDE_BUY, position_size)
                    self.position = True
                    self.entry_price = last_price
                    self.current_order = order
                    
            elif self.position and self.check_sell_conditions(df):
                current_balance = self.get_account_balance(self.base_asset)
                if current_balance > 0:
                    order = self.place_order(SIDE_SELL, current_balance)
                    self.position = False
                    self.entry_price = 0
                    self.current_order = order
                    
            # Registra equity (para acompanhamento de performance)
            balance = self.get_account_balance(self.quote_asset)
            self.equity.append({
                'timestamp': datetime.now(),
                'balance': balance,
                'position': self.position
            })
            
            logger.info(f"Status: Posição={'ABERTA' if self.position else 'FECHADA'} | Saldo {self.quote_asset}: {balance:.2f}")
            
        except Exception as e:
            logger.error(f"Erro durante execução da estratégia: {e}")

    def run(self):
        """Loop principal do bot"""
        logger.info("Iniciando Trading Bot...")
        try:
            while True:
                self.run_strategy()
                
                # Aguarda até o próximo candle (com tratamento para evitar chamadas muito rápidas)
                now = datetime.now()
                next_run = now.replace(minute=0, second=0, microsecond=0) + pd.Timedelta(hours=1)
                sleep_time = (next_run - now).total_seconds()
                
                if sleep_time > 0:
                    logger.info(f"Aguardando próximo ciclo em {sleep_time/60:.1f} minutos...")
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            logger.info("Bot interrompido pelo usuário")
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
        finally:
            logger.info("Bot finalizado")

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()