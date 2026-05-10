class AnonymousSurvey:
    """收集匿名调查问卷的答案"""

    def __init__(self, question):
        """存储一个问题，并为存储答案做准备"""
        self.question = question
        self.responses = []

    def show_question(self):
        """显示调查问卷"""
        print(self.question)

    def store_response(self, new_response):
        """存储单份调查问卷"""
        self.responses.append(new_response)

    def show_results(self):
        """显示收集到的所有答案"""
        print("Survey results:")
        for response in self.responses:
            print("- " + response)


if __name__ == "__main__":
    """测试AnonymousSurvey类"""
    question = "What language did you first learn to speak?"
    my_survey = AnonymousSurvey(question)
    my_survey.show_question()
    my_survey.store_response("Chinese")
    my_survey.store_response("English")
    my_survey.show_results()

    while True:
        response = input("Language: ")
        if response == "q":
            break
        my_survey.store_response(response)
    my_survey.show_results()
