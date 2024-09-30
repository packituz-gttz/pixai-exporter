from dataclasses import dataclass, field
from time import sleep
from typing import Any, Final, Optional
import datetime as dt

import click
from prometheus_client import start_http_server, Gauge

import requests


@dataclass
class Metric:
    value: Any
    labels: Optional[dict[str, Any]] = field(default_factory=dict)


def should_continue() -> bool:
    return True


class PixAiExporter:
    PIXAI_URL: Final[str] = "https://api.pixai.art/graphql"

    def __init__(self, api_token: str, port: int, interval: int, timeout: int):
        self._api_token: str = api_token
        self._timeout: int = timeout
        self.headers = {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Authorization': f'Bearer {self._api_token}',
            'Content-Type': 'application/json',
        }
        self._metrics: dict = {
            'pixai_available_tokens_total': Gauge('pixai_available_tokens_total', 'Total amount of tokens available'),
            'pixai_token_days_until_expiration': Gauge('pixai_token_days_until_expiration',
                                                       'Number of days until token expires', ['token'])
        }
        start_http_server(port=port)
        while should_continue():
            print('Scraping metrics...')
            self.metrics = self.get_metrics()
            sleep(interval)

    @property
    def metrics(self) -> dict:
        return self._metrics

    @metrics.setter
    def metrics(self, metrics: dict[str, list[Metric]]) -> None:
        for metric_name, metric_obj in metrics.items():
            for metric in metric_obj:
                if metric.labels:
                    self._metrics[metric_name].labels(**metric.labels).set(metric.value)
                else:
                    self._metrics[metric_name].set(metric.value)

    def get_metrics(self) -> dict[str, list[Metric]]:
        new_metrics: dict = {
            'pixai_available_tokens_total': self._get_available_tokens(),
            'pixai_token_days_until_expiration': self._get_tokens_days_until_expiration(),
        }
        return new_metrics

    def _get_available_tokens(self) -> list[Metric]:
        payload = ("{\"query\":\"\\n    query getMyQuota {\\n  me {\\n"
                   "    quotaAmount\\n  }\\n}\\n    \",\"variables\":{}}")
        response = requests.request("POST", self.PIXAI_URL, headers=self.headers, data=payload,
                                    timeout=self._timeout).json()
        return [Metric(value=response['data']['me']['quotaAmount'])]

    def _get_tokens_days_until_expiration(self) -> list[Metric]:
        payload = ("{\"query\":\"\\n    query listMyAccessTokens($before: String, $after: String,"
                   " $first: Int, $last: Int) {\\n  me {\\n    accessTokens(before: $before, after: $after,"
                   " first: $first, last: $last)"
                   " {\\n      edges {\\n        node {\\n          ...AccessTokenBase\\n        }"
                   "\\n        cursor\\n      }\\n      pageInfo {\\n        hasNextPage\\n        hasPreviousPage"
                   "\\n        endCursor\\n        startCursor\\n      }\\n      totalCount\\n    }\\n  }\\n}"
                   "\\n    \\n    fragment AccessTokenBase on AccessToken {\\n  id\\n  userId\\n  name\\n  "
                   "secret\\n  expireTime\\n  lastUsedAt\\n  createdAt\\n}\\n    \",\"variables\":"
                   "{\"first\":10}}")
        response = requests.request("POST", self.PIXAI_URL, headers=self.headers, data=payload,
                                    timeout=self._timeout).json()
        tokens: list[Metric] = []
        for token in response['data']['me']['accessTokens']['edges']:
            tokens.append(Metric(value=self._calculate_expiration_days(token['node']['expireTime']), labels={
                'token': token['node']['name']
            }))
        return tokens

    @staticmethod
    def _calculate_expiration_days(expiration_date: str) -> int:
        utc_tz = dt.timezone.utc
        expiration_date_utc = dt.datetime.strptime(expiration_date, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=utc_tz)
        utc_now_date = dt.datetime.now(utc_tz)
        return (expiration_date_utc - utc_now_date).days


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
