#!/usr/bin/env python3
"""Call V2 CRM API with fixed table_key and normalized output."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
import urllib.error
import urllib.request

TABLE_KEY = 'customer_profiles'
DEFAULT_URL = 'https://veon-api-vercel.vercel.app/api'
DEFAULT_ACCESS_CODE = '888'
ALLOWED_ACTIONS = {
    'create_one',
    'get_one',
    'list',
    'update_one',
    'delete_one',
    'upsert_one',
}


def make_result(ok: bool, status: int | None, data: Any = None, error: Any = None) -> dict[str, Any]:
    result: dict[str, Any] = {'type': 'API_RESULT', 'ok': ok}
    if status is not None:
        result['status'] = status
    if ok:
        result['data'] = data
    else:
        result['error'] = error
    return result


def load_json_object(json_text: str | None, json_file: str | None, field_name: str) -> dict[str, Any] | None:
    if json_text and json_file:
        raise ValueError(f'Use either --{field_name}-json or --{field_name}-file, not both')

    if json_text:
        parsed = json.loads(json_text)
        if not isinstance(parsed, dict):
            raise ValueError(f'--{field_name}-json must be a JSON object')
        return parsed

    if json_file:
        with open(json_file, 'r', encoding='utf-8-sig') as f:
            parsed = json.load(f)
        if not isinstance(parsed, dict):
            raise ValueError(f'--{field_name}-file must contain a JSON object')
        return parsed

    return None


def build_request_body(args: argparse.Namespace) -> dict[str, Any]:
    action = (args.action or '').strip().lower()
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f'Unsupported action: {action}')

    payload = load_json_object(args.payload_json, args.payload_file, 'payload')
    filter_obj = load_json_object(args.filter_json, args.filter_file, 'filter')
    pagination = load_json_object(args.pagination_json, args.pagination_file, 'pagination')

    sort = None
    if args.sort_json and args.sort_file:
        raise ValueError('Use either --sort-json or --sort-file, not both')
    if args.sort_json:
        parsed = json.loads(args.sort_json)
        if not isinstance(parsed, list):
            raise ValueError('--sort-json must be a JSON array')
        sort = parsed
    if args.sort_file:
        with open(args.sort_file, 'r', encoding='utf-8-sig') as f:
            parsed = json.load(f)
        if not isinstance(parsed, list):
            raise ValueError('--sort-file must contain a JSON array')
        sort = parsed

    body: dict[str, Any] = {
        'action': action,
        'table_key': TABLE_KEY,
        'access_code': args.access_code,
    }

    if payload is not None:
        body['payload'] = payload
    if filter_obj is not None:
        body['filter'] = filter_obj
    if pagination is not None:
        body['pagination'] = pagination
    if sort is not None:
        body['sort'] = sort
    if args.request_id:
        body['request_id'] = args.request_id

    if action in {'create_one', 'update_one', 'upsert_one'} and 'payload' not in body:
        raise ValueError(f'action={action} requires payload')

    if action in {'get_one', 'delete_one', 'update_one'} and 'filter' not in body:
        raise ValueError(f'action={action} requires filter')

    if action in {'update_one', 'upsert_one'}:
        payload_obj = body.get('payload')
        if not isinstance(payload_obj, dict) or 'summary' not in payload_obj:
            raise ValueError(f'action={action} requires payload.summary (full text overwrite each update)')

    return body


def main() -> int:
    parser = argparse.ArgumentParser(description='Call V2 CRM API (fixed table_key)')
    parser.add_argument('--action', required=True, help='V2 action name')
    parser.add_argument('--payload-json', help='JSON object string for payload')
    parser.add_argument('--payload-file', help='Path to payload JSON object file')
    parser.add_argument('--filter-json', help='JSON object string for filter')
    parser.add_argument('--filter-file', help='Path to filter JSON object file')
    parser.add_argument('--pagination-json', help='JSON object string for pagination')
    parser.add_argument('--pagination-file', help='Path to pagination JSON object file')
    parser.add_argument('--sort-json', help='JSON array string for sort')
    parser.add_argument('--sort-file', help='Path to sort JSON array file')
    parser.add_argument('--request-id', help='Optional request_id for tracing')
    parser.add_argument('--access-code', default=DEFAULT_ACCESS_CODE, help=f'access_code (default: {DEFAULT_ACCESS_CODE})')
    parser.add_argument('--url', default=DEFAULT_URL, help=f'API URL (default: {DEFAULT_URL})')
    parser.add_argument(
        '--strict-exit-code',
        action='store_true',
        help='Return non-zero when request fails (default keeps exit code 0 for easy piping)',
    )
    args = parser.parse_args()

    try:
        body_obj = build_request_body(args)
    except Exception as e:
        print(json.dumps(make_result(False, None, error=f'Invalid arguments: {e}'), ensure_ascii=False))
        return 2

    req_body = json.dumps(body_obj).encode('utf-8')
    req = urllib.request.Request(
        args.url,
        data=req_body,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode('utf-8')
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {'raw': raw}
            print(json.dumps(make_result(True, resp.status, data=parsed), ensure_ascii=False))
            return 0
    except urllib.error.HTTPError as e:
        raw = e.read().decode('utf-8', errors='replace')
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {'raw': raw}
        print(json.dumps(make_result(False, e.code, error=parsed), ensure_ascii=False))
        return 1 if args.strict_exit_code else 0
    except Exception as e:  # pragma: no cover
        print(json.dumps(make_result(False, None, error=str(e)), ensure_ascii=False))
        return 2 if args.strict_exit_code else 0


if __name__ == '__main__':
    sys.exit(main())
