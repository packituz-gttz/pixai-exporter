from time import sleep
from typing import Any, Final

import click
from prometheus_client import start_http_server, Gauge

import requests


class PixAiExporter:
    PIXAI_URL: Final[str] = "https://api.pixai.art/graphql"

    def __init__(self, api_token: str, port: int, interval: int, timeout: int):
        self._api_token: str = api_token
        self._timeout: int = timeout
        self._metrics: dict = {
            'pixai_available_tokens_total': Gauge('pixai_available_tokens_total', 'Total amount of tokens available')
        }
        start_http_server(port=port)
        while True:
            self.metrics = self.get_metrics()
            print('Scraping metrics...')
            sleep(interval)

    @property
    def metrics(self) -> dict:
        return self._metrics

    @metrics.setter
    def metrics(self, metrics: dict[str, int]) -> None:
        for metric_name, metric_value in metrics.items():
            self._metrics[metric_name].set(metric_value)

    def get_metrics(self) -> dict[str, Any]:
        new_metrics: dict = {'pixai_available_tokens_total': self._get_available_tokens()}
        return new_metrics

    def _get_available_tokens(self) -> int:
        headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': f'Bearer {self._api_token}',
            'Content-Type': 'application/json',
        }
        payload = "{\"query\":\"\\n    query getMyQuota {\\n  me {\\n    quotaAmount\\n  }\\n}\\n    \",\"variables\":{}}"

        response = requests.request("POST", self.PIXAI_URL, headers=headers, data=payload, timeout=self._timeout).json()
        return response['data']['me']['quotaAmount']


CONTEXT_SETTINGS: dict = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
def main() -> None:
    """Executes cli for PixAiExporter"""


@main.command(hidden=True)
@click.pass_context
def help(ctx):
    click.echo(ctx.parent.get_help)


@main.command()
@click.option('--api-token', type=str, required=True)
@click.option('--port', default=9865, type=int)
@click.option('--interval', default=600, type=int)
@click.option('--timeout', default=25, type=int)
def start(api_token: str, port: int, interval: int, timeout: int):
    PixAiExporter(api_token=api_token, port=port, interval=interval, timeout=timeout)


if __name__ == '__main__':
    main()
