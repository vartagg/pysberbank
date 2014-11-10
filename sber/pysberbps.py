#coding=utf8
# pysberbank 10.11.14 8:32 by mnach #
import datetime
from enum import Enum
import json
import logging
import urllib.request
import urllib.parse
logger = logging.getLogger(__name__)

class SberError(Exception): pass

class SberNetworkError(SberError): pass

class SberRequestError(SberError):
    def __init__(self, request, code, desc):
        self.request = request
        self.code = code
        self.desc = desc
        super(SberRequestError, self).__init__('{0.request} error {0.code}: {0.desc}'.format(self))


class SberWrapper(object):
    """
    Sberbank acquiring API wrapper
    """
    class PageType(Enum):
        DESKTOP = 1
        MOBILE = 2

    rest_urls = dict(
        # register order in sberbank
        register='https://3dsec.sberbank.ru/payment/rest/register.do',
        # get order status
        status='https://3dsec.sberbank.ru/payment/rest/getOrderStatus.do',
    )
    soap_urls = dict(

    )

    def __init__(self, username: str, password: str, soap: bool=False, post: bool=True, urls: dict=None):
        """
        :param username: Store username
        :param password: Store password
        :param use_soap: use soap api instead of REST
        :param post: use POST request not GET
        :param urls: dict of urls where requests will be sent
        """
        self._username = username
        self._password = password

        self.soap = soap
        self.post = post
        if self.soap and not self.post:
            raise ValueError("Soap request must be send by POST request")
        self.urls = urls or (self.soap_urls if self.soap else self.rest_urls)

    def _request(self, url, params):
        if self.soap:
            # todo: Soap implementation
            raise NotImplementedError("SOAP haven't implemented yet")
        logger.debug('Request  is {0!r}'.format(params))
        # todo: exception handling
        if self.post:
            request = urllib.request.Request(url)
            # adding charset parameter to the Content-Type header.
            request.add_header("Content-Type","application/x-www-form-urlencoded;charset=utf-8")
            data = urllib.parse.urlencode(params)
            data = data.encode('utf-8')
            response = urllib.request.urlopen(request, data)
        else:
            response = urllib.request.urlopen('{0}?{1}'.format(url, urllib.parse.urlencode(params)))
        logger.debug('Response is {0.status} {0._method} {0.reason} {headers}'.format(response, headers=response.getheaders()))
        assert response.status == 200
        response_body = response.read()
        logger.debug('Response body is {0!r}'.format(response_body))
        assert response_body is not None
        response_dict = json.loads(response_body.decode('utf8'), encoding='utf8')
        logger.debug('Unmarshaled response  is {0!r}'.format(response_dict))
        return response_dict

    def register(self, order: str, amount: int, success_url: str, currency: int=643, fail_url: str=None,
                 description: str='', language: str='RU', page_type: PageType=PageType.DESKTOP, clinet_id: str=None,
                 session_timeout: int=1200, expiration: datetime.date=None, extra: dict=None):
        """
        Register request in acquiring system
        :param order: order id in the store
        :param amount: Order amount in minimal unit of currency(penny / kopeck)
        :param success_url: Send user to this URL after success of payment
        :param currency: Currency code in ISO 4217
        :param fail_url: Send user to this URL after failure of payment
        :param description: order description in free text format
        :param language: Acquiring page language
        :param page_type: Is it mobile or desctop user ?
        :param clinet_id: Client id in the store
        :param session_timeout: The duration of the session, in seconds
        :param expiration: Order lifetime. It will be (<now>+session_timeout) if None
        :param extra: some extra params to store in the system
        :return: (order_id, form_url)
        """
        url = self.urls['register']
        request = dict(
            # Логин магазина, полученный при подключении
            userName=self._username,
            # Пароль магазина, полученный при подключении
            password=self._password,
            # Номер (идентификатор) заказа в системе магазина
            orderNumber=order,
            # Сумма платежа в минимальных единицах валюты(копейки).
            amount=amount,
            # *Код валюты платежа ISO 4217.
            currency=currency,
            # Адрес, на который надо перенаправить пользователя в случае успешной оплаты
            returnUrl=success_url,
            # *Язык в кодировке ISO 639-1.
            language=language,
             # В pageView передаётся признак - мобильное устройство: MOBILE или DESKTOP
            pageView=page_type.name,
            # *Продолжительность сессии в секундах. default=1200
            sessionTimeoutSecs=session_timeout,
        )
        if fail_url:
            # *Адрес, на который надо перенаправить пользователя в случае неуспешной оплаты
            request['failUrl'] = fail_url
        if description:
             # *Описание заказа в свободной форме
            request['description'] = description
        if clinet_id:
            # *Номер (идентификатор) клиента в системе магазина
            request['clientId'] = clinet_id
        if extra:
            # *Поля дополнительной информации для последующего хранения
            request['jsonParams'] = extra
        if expiration:
            # *Время жизни заказа. Если не задано вычисляется по sessionTimeoutSecs
            request['expirationDate'] = expiration.isoformat().split('.')[0]
        response = self._request(url, request)
        if 'errorCode' in response and response.get('errorCode') != '0':
            raise SberRequestError('register', response['errorCode'],
                                   response.get('errorMessage', 'Description not presented'))
        if 'orderId' not in response or 'formUrl' not in response:
            raise SberNetworkError('Service temporary unavailable')
        return response['orderId'], response['formUrl']
