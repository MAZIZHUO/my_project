import pytest
from survey import AnonymousSurvey


# 这个 fixture 的作用是创建一个 AnonymousSurvey 实例。任何测试函数如果想要这个实例，只需在参数中写上 language_survey 即可：
@pytest.fixture
def language_survey():
    question = "What language did you first learn to speak?"
    return AnonymousSurvey(question)


def test_store_single_response(language_survey):
    """测试store_response()方法可以正确地存储单个答案"""
    language_survey.store_response("English")
    assert "English" in language_survey.responses


def test_store_multiple_responses(language_survey):
    """测试store_response()方法可以正确地存储多个答案"""
    responses = ["English", "Chinese", "Spanish"]
    for response in responses:
        language_survey.store_response(response)
    for response in responses:
        assert response in language_survey.responses
