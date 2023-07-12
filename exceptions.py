class HTTPStatusException(Exception):
    """Код ответа HTTPStatus не равен 200"""
    pass

class ConnectinError(Exception):
    """Ошибка сервера"""
    pass
