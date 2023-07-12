import os
import time
import requests
import telegram
import logging
import sys

from http import HTTPStatus
from dotenv import load_dotenv

from exceptions import HTTPStatusException, ConnectinError

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        logging.info('Готовится отправить сообщение в Telegram')
        bot.send_message(
            TELEGRAM_CHAT_ID,
            message
        )
    except Exception as error:
        logging.error(f'Сообщение НЕ отправлено в Telegram: {error}')
    logging.debug(
        f'Сообщение отправлено в Telegram {TELEGRAM_CHAT_ID}: {message}'
    )


def get_api_answer(timestamp):
    """Опрос API сервиса Практикум.Домашка."""
    try:
        logging.info('Начал запрос к API.')
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})
    except Exception as error:
        raise ConnectinError(
            f'Сервер не отвечает. Ошибка:{error}'
        )
    if response.status_code != HTTPStatus.OK:
        raise HTTPStatusException(
            f'Не удалось получить ответ от API по причине {response.reason}',
            f'код состояния: {response.status_code}')
    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие сервиса Практикум.Домашка."""
    logging.info('Начал проверку ответа сервера')
    if not isinstance(response, dict):
        raise TypeError('Ответ сервера не является словарем')

    if 'current_date' not in response and 'homeworks' not in response:
        raise KeyError('В ответе сервера нет ключей current_date и homeworks')

    homeworks = response.get('homeworks')

    if not isinstance(homeworks, list):
        raise TypeError(
            f'Ответ сервера "JSON" не удалось преобразован в словарь.'
            f'Тип ответа: {type(homeworks)}'
        )
    return homeworks[0]


def parse_status(homework):
    """Извлекает статус домашней работы."""
    logging.info('Извлекаю статус домашней работы')
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('В ответе отсутсвует ключ status')
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы - {homework_status}')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.info('Бот начал работу')
    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные')
        sys.exit('Отсутствуют обязательные переменные окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            if check_response(response):
                message = parse_status(check_response(response))
                send_message(bot, message)
        except IndexError:
            logging.debug('Новых статусов нет')
            continue

        except Exception as error:
            logging.info(f'Сбой в работе программы: {error}')
        finally:
            logging.info('Бот ждет 10 минут')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='main.log',
        filemode='w',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    main()
