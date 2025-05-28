import requests
import time

from airless.core.service import CaptchaService


class Solver2CaptchaService(CaptchaService):
    """Service for solving captchas using 2Captcha."""

    def __init__(self, credentials: dict) -> None:
        """Initializes the Solver2CaptchaService.

        Args:
            credentials (dict): The credentials for the 2Captcha API.
        """
        super().__init__()
        self.api_url = '2captcha.com'
        self.request_endpoint = '/in.php'
        self.response_endpoint = '/res.php'
        self.captcha_id = None
        self.credentials = credentials

    def _send_request(self, params: dict) -> None:
        """Sends a request to the 2Captcha API.

        Args:
            params (dict): The parameters for the request.

        Raises:
            requests.HTTPError: If the request fails.
        """
        response = requests.post(
            f'http://{self.api_url}{self.request_endpoint}',
            params=params,
            timeout=10
        )
        response.raise_for_status()
        self.captcha_id = response.json()['request']

    def _request_recaptcha_v2(self, page_url: str, google_key: str) -> None:
        """Requests solving of a reCAPTCHA v2.

        Args:
            page_url (str): The URL of the page with the captcha.
            google_key (str): The Google reCAPTCHA key.
        """
        params = {
            'key': self.credentials['apikey'],
            'method': 'userrecaptcha',
            'googlekey': google_key,
            'pageurl': page_url,
            'json': 1,
            'invisible': 1,
            'enterprise': 0
        }
        self._send_request(params)

    def _request_recaptcha_v3(self, page_url: str, google_key: str, action: str = 'verify') -> None:
        """Requests solving of a reCAPTCHA v3.

        Args:
            page_url (str): The URL of the page with the captcha.
            google_key (str): The Google reCAPTCHA key.
            action (str, optional): The action to perform. Defaults to 'verify'.
        """
        params = {
            'key': self.credentials['apikey'],
            'method': 'userrecaptcha',
            'version': 'v3',
            'googlekey': google_key,
            'pageurl': page_url,
            'json': 1,
            'enterprise': 0,
            'min_score': 0.9,
            'action': action
        }
        self._send_request(params)

    def _send_response_request(self, action: str) -> dict:
        """Sends a request to get the response of the captcha.

        Args:
            action (str): The action to perform (e.g., 'get', 'reportgood', 'reportbad').

        Returns:
            dict: The response from the 2Captcha API.

        Raises:
            requests.HTTPError: If the request fails.
        """
        params = {
            'key': self.credentials['apikey'],
            'action': action,
            'json': 1,
            'id': self.captcha_id
        }

        response = requests.get(
            f'http://{self.api_url}{self.response_endpoint}',
            params=params,
            timeout=10
        )
        response.raise_for_status()
        return response.json()

    def report_good_captcha(self) -> None:
        """Reports a captcha as solved successfully to the 2Captcha API.

        This method should be called when a captcha provided by 2Captcha
        was accepted by the target website.
        """
        self._send_response_request('reportgood')

    def report_bad_captcha(self) -> None:
        """Reports a captcha as unsolvable to the 2Captcha API.

        This method should be called when a captcha provided by 2Captcha
        was rejected by the target website.
        """
        self._send_response_request('reportbad')

    def solve(self, version: str, page_url: str, google_key: str, action: str = 'verify') -> str:
        """Solves a captcha using the specified version.

        Args:
            version (str): The version of the captcha (e.g., 'v2' or 'v3').
            page_url (str): The URL of the page with the captcha.
            google_key (str): The Google reCAPTCHA key.
            action (str, optional): The action to perform. Defaults to 'verify'.

        Raises:
            Exception: If the captcha version is not implemented or if solving fails.

        Returns:
            str: The solution to the captcha.
        """
        if version == 'v2':
            self._request_recaptcha_v2(page_url, google_key)
        elif version == 'v3':
            self._request_recaptcha_v3(page_url, google_key, action)
        else:
            raise Exception(f'Recaptcha version {version} not implemented')

        for _ in range(100):
            response = self._send_response_request('get')
            if response['status'] == 1:
                return response['request']
            elif response['request'] == 'CAPCHA_NOT_READY':
                time.sleep(3)
            elif response['request'] == 'ERROR_CAPTCHA_UNSOLVABLE':
                raise Exception('2Captcha was not able to solve captcha: ERROR_CAPTCHA_UNSOLVABLE')
            else:
                raise Exception(f'2Captcha was not able to solve captcha: {response["request"]}')

        raise Exception('2Captcha did not solve recaptcha in time')
