import logging
import colorlog

class ColorLogger:
    def __init__(self, name='minha_app'):
        # 1. Pega o logger e evita adicionar handlers duplicados em recargas
        self.log = logging.getLogger(name)
        self.log.setLevel(logging.DEBUG) # Define o nível de log mais baixo

        # Se o logger já tiver handlers, limpe-os para evitar logs duplicados
        if self.log.hasHandlers():
            self.log.handlers.clear()

        # 2. Cria um handler do colorlog
        handler = colorlog.StreamHandler()

        # 3. Cria um formatter com cores
        formatter = colorlog.ColoredFormatter(
            '%(log_color)s%(levelname)-8s%(reset)s %(purple)s[%(name)s]%(reset)s %(message)s',
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            }
        )

        # 4. CONFIGURAÇÃO ESSENCIAL QUE FALTAVA
        handler.setFormatter(formatter)
        self.log.addHandler(handler)

        # 5. A SOLUÇÃO: Desativa a propagação para o logger raiz
        self.log.propagate = False

    # 6. MÉTODOS PARA FAZER O LOG
    def info(self, message):
        self.log.info(message)

    def warning(self, message):
        self.log.warning(message)

    def error(self, message):
        self.log.error(message)

    def debug(self, message):
        self.log.debug(message)
    
    def critical(self, message):
        self.log.critical(message)
