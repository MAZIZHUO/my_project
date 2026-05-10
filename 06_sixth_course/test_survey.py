from survey import AnonymousSurvey


def test_store_single_response():
    """测试store_response()方法可以正确地存储单个答案"""
    question = "What language did you first learn to speak?"
    my_survey = AnonymousSurvey(question)
    my_survey.store_response("English")
    assert "English" in my_survey.responses


def test_store_multiple_responses():
    """测试store_response()方法可以正确地存储多个答案"""
    question = "What language did you first learn to speak?"
    my_survey = AnonymousSurvey(question)
    responses = ["English", "Chinese", "Spanish"]
    for response in responses:
        my_survey.store_response(response)
    for response in responses:
        assert response in my_survey.responses


if __name__ == "__main__":
    test_store_single_response()
    test_store_multiple_responses()
    print("All tests passed!")
