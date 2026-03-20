"""is_white_monitor() 단위 테스트 — 다나와 검색 기반 화이트 모니터 판별"""
import pytest
from unittest.mock import patch, MagicMock
from main import is_white_monitor


def _mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    return resp


# 화이트 모델: prod_name 블록에 모델명 포함
WHITE_HTML = '''
<p class="prod_name">
<a href="...">LG전자 MyView 스마트 27SR75U</a>
</p>
'''

# 비화이트: 검색결과 없음
NO_RESULT_HTML = '<div>검색된 상품이 없습니다</div>'

# 비화이트: 연관 상품만 노출 (모델명 불일치)
RELATED_ONLY_HTML = '''
<p class="prod_name">
<a href="...">LG전자 울트라HD 27US500</a>
</p>
'''


@patch('main.requests.get')
def test_화이트_모델_판별(mock_get):
    mock_get.return_value = _mock_response(WHITE_HTML)
    assert is_white_monitor('27SR75U.AKRG') is True


@patch('main.requests.get')
def test_검색결과_없으면_비화이트(mock_get):
    mock_get.return_value = _mock_response(NO_RESULT_HTML)
    assert is_white_monitor('27BR400.AKRG') is False


@patch('main.requests.get')
def test_연관상품만_있으면_비화이트(mock_get):
    # 27MS500 검색 시 27US500 등 연관 상품만 나오는 케이스
    mock_get.return_value = _mock_response(RELATED_ONLY_HTML)
    assert is_white_monitor('27MS500.AKRG') is False


@patch('main.requests.get')
def test_한국유통suffix_제거후_판별(mock_get):
    # .AKRG suffix 제거 후 base 모델명으로 검색하는지 확인
    mock_get.return_value = _mock_response(WHITE_HTML)
    is_white_monitor('27SR75U.AKRG')
    call_params = mock_get.call_args
    assert call_params[1]['params']['query'] == '27SR75U'


@patch('main.requests.get')
def test_네트워크_오류시_비화이트(mock_get):
    mock_get.side_effect = Exception('connection error')
    assert is_white_monitor('27SR75U.AKRG') is False
